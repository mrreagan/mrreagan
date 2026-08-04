"""Iteration 49 — Release History Timeline + admin rollback.

Modules under test:
  - backend/routers/legal.py
      GET  /api/legal/history-timeline/{slug}?limit=N
      POST /api/legal/history/{slug}/rollback/{ratification_id}
      POST /api/legal/working-drafts/{slug}/release  (now stores
           content_md_snapshot + change_summary on the ratification row)
      helper _summarise_wd_change_log

Cleanup: every legal_doc_ratifications / legal_doc_working_drafts row this
module creates for 03-cookie-notice is deleted at session teardown, the
physical .md is restored from a snapshot and the docx bundle is rebuilt.
"""
import io
import os
import shutil
import sys
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

if "/app/backend" not in sys.path:
    sys.path.insert(0, "/app/backend")

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")

backend_env = dotenv_values("/app/backend/.env")
MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")

COUNSEL = ("counsel@birthright.live", "counsel-review-2026")
ADMIN = ("admin@birthright.live", "birthright2026")

SLUG = "03-cookie-notice"
DOC_PATH = Path("/app/backend/legal_docs") / f"{SLUG}.md"
BACKUP_PATH = Path("/tmp/iter49/03-cookie-notice.md.bak")

LEGACY_RAT_ID = "TEST_iter49_legacy_rat"


# ------------------------------------------------------------------ helpers
def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    body = r.json()
    return body["token"], body["user"]


def _session(creds, expected_role):
    token, user = _login(*creds)
    assert user["role"] == expected_role, f"expected {expected_role}, got {user['role']}"
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def mongo():
    if not MONGO_URL or not DB_NAME:
        pytest.fail("MONGO_URL / DB_NAME missing from /app/backend/.env")
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="session")
def counsel():
    return _session(COUNSEL, "readonly_admin")


@pytest.fixture(scope="session")
def admin():
    return _session(ADMIN, "admin")


@pytest.fixture(scope="session", autouse=True)
def cleanup(mongo, request):
    """Snapshot the .md, then wipe everything this module creates."""
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP_PATH.exists():
        shutil.copy(DOC_PATH, BACKUP_PATH)
    pre_rats = {r["id"] for r in mongo.legal_doc_ratifications.find(
        {"source_slug": SLUG}, {"id": 1, "_id": 0})}
    pre_wds = {w["id"] for w in mongo.legal_doc_working_drafts.find(
        {"source_slug": SLUG}, {"id": 1, "_id": 0})}
    yield
    mongo.legal_doc_ratifications.delete_many(
        {"source_slug": SLUG, "id": {"$nin": list(pre_rats)}})
    mongo.legal_doc_working_drafts.delete_many(
        {"source_slug": SLUG, "id": {"$nin": list(pre_wds)}})
    shutil.copy(BACKUP_PATH, DOC_PATH)
    try:
        token, _ = _login(*ADMIN)
        requests.post(f"{BASE_URL}/api/legal/rebuild-docx",
                      headers={"Authorization": f"Bearer {token}"}, timeout=180)
    except Exception as exc:  # pragma: no cover
        print(f"cleanup rebuild failed: {exc}")


def _upload(session, content, filename="draft.md"):
    return session.post(
        f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/markdown")},
        timeout=120,
    )


def _release(session, notes=None):
    return session.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                        json={"notes": notes} if notes else {}, timeout=180)


def _timeline(session, **params):
    return session.get(f"{BASE_URL}/api/legal/history-timeline/{SLUG}",
                       params=params, timeout=90)


# =============================================== 1. Seed 3 released versions
@pytest.fixture(scope="session")
def released(counsel, admin, cleanup):
    """Create 3 releases (v1.0, v1.1, v1.2) with distinct content + edits."""
    out = []
    for i in range(1, 4):
        body = (f"# Cookie Notice (TEST_iter49 v{i})\n\n"
                f"TEST_iter49 unique marker BODY-{i}\n\n## Section {i}\n\n- one\n- two\n")
        r = _upload(counsel, body, filename=f"iter49-v{i}.md")
        assert r.status_code == 200, f"upload {i} failed: {r.status_code} {r.text[:300]}"
        # second edit in the same working draft to make edits == 2
        r2 = _upload(counsel, body + f"\n- extra edit {i}\n", filename=f"iter49-v{i}b.md")
        assert r2.status_code == 200, r2.text[:300]
        rel = _release(admin, notes=f"TEST_iter49 release pass {i}")
        assert rel.status_code == 200, f"release {i} failed: {rel.status_code} {rel.text[:400]}"
        d = rel.json()
        out.append({"version": d["released_as_version"],
                    "ratification_id": d["ratification_id"],
                    "marker": f"BODY-{i}"})
    return out


class TestReleaseStoresSnapshot:
    """Release now persists content_md_snapshot + change_summary."""

    def test_release_row_has_snapshot_and_summary(self, released, mongo):
        assert len(released) == 3
        assert [r["version"] for r in released] == ["1.0", "1.1", "1.2"], released
        for rel in released:
            row = mongo.legal_doc_ratifications.find_one({"id": rel["ratification_id"]})
            assert row, f"ratification {rel['ratification_id']} not persisted"
            snap = row.get("content_md_snapshot")
            assert isinstance(snap, str) and snap.strip(), "content_md_snapshot missing/empty"
            assert rel["marker"] in snap, "snapshot does not contain the released body"
            cs = row.get("change_summary")
            assert isinstance(cs, dict), "change_summary missing"
            # 2 uploads per working draft, mark_ready/release excluded
            assert cs["edits"] == 2, f"expected 2 edits, got {cs['edits']} ({cs})"
            assert COUNSEL[0] in cs["authors"], cs
            assert cs["actions"] == {"upload_full": 2}, cs
            assert cs["first_edit_at"] and cs["last_edit_at"]

    def test_change_log_edit_count_matches_summary(self, released, mongo):
        wd = mongo.legal_doc_working_drafts.find_one(
            {"source_slug": SLUG, "released_as_version": "1.2"})
        assert wd, "released working draft row not found"
        expected = len([e for e in (wd.get("change_log") or [])
                        if e.get("action") not in {"mark_ready", "release"}])
        row = mongo.legal_doc_ratifications.find_one({"source_slug": SLUG, "version": "1.2"})
        assert row["change_summary"]["edits"] == expected


# ============================================== 2. GET /history-timeline
class TestHistoryTimeline:
    def test_shape_and_ordering_as_admin(self, admin, released):
        r = _timeline(admin)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["source_slug"] == SLUG
        assert d["total_versions"] >= 3
        assert d["current_version"] == "1.2"
        assert isinstance(d["current_body_hash"], str) and d["current_body_hash"]
        versions = d["versions"]
        assert len(versions) == min(5, d["total_versions"])
        # newest first
        ats = [v["ratified_at"] for v in versions]
        assert ats == sorted(ats, reverse=True), ats
        assert [v["version"] for v in versions[:3]] == ["1.2", "1.1", "1.0"]
        for v in versions:
            for key in ("id", "version", "ratified_at", "ratified_by", "notes",
                        "change_summary", "can_rollback"):
                assert key in v, f"missing {key} in {v}"
            assert "_id" not in v
            assert "content_md_snapshot" not in v, "heavy field leaked into list"
            assert v["can_rollback"] is True

    def test_counsel_can_read_timeline(self, counsel, released):
        r = _timeline(counsel)
        assert r.status_code == 200, f"counsel read blocked: {r.status_code} {r.text[:300]}"
        assert r.json()["current_version"] == "1.2"

    def test_limit_one(self, admin, released):
        r = _timeline(admin, limit=1)
        assert r.status_code == 200
        d = r.json()
        assert len(d["versions"]) == 1
        assert d["versions"][0]["version"] == "1.2"
        assert d["total_versions"] >= 3

    def test_limit_clamped_to_50(self, admin, released):
        r = _timeline(admin, limit=500)
        assert r.status_code == 200
        assert len(r.json()["versions"]) <= 50

    def test_limit_zero_falls_back_to_default(self, admin, released):
        # `int(limit or 5)` treats 0 as "unset" → default 5 (documented behaviour)
        r = _timeline(admin, limit=0)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        d = r.json()
        assert len(d["versions"]) == min(5, d["total_versions"])

    def test_negative_limit_clamped_to_one(self, admin, released):
        r = _timeline(admin, limit=-3)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert len(r.json()["versions"]) == 1

    def test_unknown_slug_returns_empty(self, admin):
        r = admin.get(f"{BASE_URL}/api/legal/history-timeline/TEST_iter49-no-such-doc",
                      timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["total_versions"] == 0
        assert d["versions"] == []
        assert d["current_version"] is None

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/legal/history-timeline/{SLUG}", timeout=60)
        assert r.status_code in (401, 403), r.status_code


# ============================================== 3. Legacy row → no rollback
class TestLegacyRowNoRollback:
    def test_legacy_row_can_rollback_false_and_400(self, admin, mongo, released):
        mongo.legal_doc_ratifications.delete_one({"id": LEGACY_RAT_ID})
        mongo.legal_doc_ratifications.insert_one({
            "id": LEGACY_RAT_ID,
            "source_slug": SLUG,
            "version": "0.9",
            "body_hash": "TEST_iter49legacyhash",
            "notes": "TEST_iter49 legacy row without snapshot",
            "ratified_by": "legacy@birthright.live",
            # older than all seeded rows so it lands last
            "ratified_at": "2020-01-01T00:00:00+00:00",
        })
        r = _timeline(admin, limit=10)
        assert r.status_code == 200
        rows = {v["version"]: v for v in r.json()["versions"]}
        assert "0.9" in rows, "legacy row not returned"
        assert rows["0.9"]["can_rollback"] is False, "legacy row must not offer rollback"

        rb = admin.post(
            f"{BASE_URL}/api/legal/history/{SLUG}/rollback/{LEGACY_RAT_ID}",
            json={}, timeout=120)
        assert rb.status_code == 400, f"expected 400, got {rb.status_code} {rb.text[:300]}"
        assert "no content snapshot" in rb.json().get("detail", "").lower(), rb.text[:300]
        mongo.legal_doc_ratifications.delete_one({"id": LEGACY_RAT_ID})


# ============================================== 4. Rollback authz + behaviour
class TestRollback:
    def test_counsel_forbidden(self, counsel, released):
        target = released[0]  # v1.0
        r = counsel.post(
            f"{BASE_URL}/api/legal/history/{SLUG}/rollback/{target['ratification_id']}",
            json={"reason": "TEST_iter49 counsel attempt"}, timeout=120)
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:300]}"

    def test_unknown_ratification_404(self, admin):
        r = admin.post(f"{BASE_URL}/api/legal/history/{SLUG}/rollback/TEST_iter49_nope",
                       json={}, timeout=120)
        assert r.status_code == 404, r.status_code

    def test_rollback_restores_content_and_discards_wd(self, admin, counsel, mongo, released):
        target = released[0]  # v1.0 / BODY-1
        target_row = mongo.legal_doc_ratifications.find_one({"id": target["ratification_id"]})
        target_snapshot = target_row["content_md_snapshot"]

        # open a working draft that must be discarded by the rollback
        up = _upload(counsel, "# Cookie Notice (TEST_iter49 open WIP)\n\nTEST_iter49 wip body\n",
                     filename="iter49-wip.md")
        assert up.status_code == 200, up.text[:300]
        wd_id = up.json().get("working_draft_id")
        assert wd_id

        r = admin.post(
            f"{BASE_URL}/api/legal/history/{SLUG}/rollback/{target['ratification_id']}",
            json={"reason": "TEST_iter49 rollback reason"}, timeout=180)
        assert r.status_code == 200, f"rollback failed: {r.status_code} {r.text[:400]}"
        d = r.json()
        assert d["rolled_back_from_version"] == "1.0"
        assert d["version"] == "1.3", f"version not auto-bumped: {d}"
        assert d["working_draft_discarded"] is True

        new_row = mongo.legal_doc_ratifications.find_one({"id": d["ratification_id"]})
        assert new_row["rolled_back_from_ratification_id"] == target["ratification_id"]
        assert new_row["change_summary"]["rolled_back_from_version"] == "1.0"
        assert new_row["change_summary"]["actions"] == {"rollback": 1}
        assert "TEST_iter49 rollback reason" in new_row["notes"], new_row["notes"]
        assert "Rollback to v1.0" in new_row["notes"]

        # physical file matches the target snapshot after rebuild
        on_disk = DOC_PATH.read_text(encoding="utf-8")
        assert on_disk == target_snapshot, "on-disk .md does not match target snapshot"
        assert "BODY-1" in on_disk
        assert new_row["content_md_snapshot"] == on_disk

        # working draft discarded
        wd = mongo.legal_doc_working_drafts.find_one({"id": wd_id})
        assert wd["state"] == "discarded", f"WD state={wd.get('state')}"

        # timeline reflects the new current version + rollback badge data
        tl = _timeline(admin, limit=5).json()
        assert tl["current_version"] == "1.3"
        newest = tl["versions"][0]
        assert newest["version"] == "1.3"
        assert newest["rolled_back_from_ratification_id"] == target["ratification_id"]
        assert newest["can_rollback"] is True

    def test_rollback_without_reason_still_works(self, admin, mongo, released):
        target = released[1]  # v1.1 / BODY-2
        r = admin.post(
            f"{BASE_URL}/api/legal/history/{SLUG}/rollback/{target['ratification_id']}",
            json={}, timeout=180)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["rolled_back_from_version"] == "1.1"
        row = mongo.legal_doc_ratifications.find_one({"id": d["ratification_id"]})
        assert "Reason:" not in row["notes"], row["notes"]
        assert "BODY-2" in DOC_PATH.read_text(encoding="utf-8")

    def test_rollback_no_open_wd_reports_false(self, admin, mongo, released):
        target = released[2]  # v1.2
        r = admin.post(
            f"{BASE_URL}/api/legal/history/{SLUG}/rollback/{target['ratification_id']}",
            json={"reason": "TEST_iter49 no wd"}, timeout=180)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["working_draft_discarded"] is False
