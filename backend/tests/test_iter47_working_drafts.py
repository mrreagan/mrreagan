"""Iteration 47 — Legal working-draft (WORKING VERSION) workflow.

Modules under test:
  - backend/routers/legal.py
      POST /api/legal/docs/{slug}/upload            (now writes working draft)
      GET  /api/legal/working-drafts
      GET  /api/legal/working-drafts/{slug}
      GET  /api/legal/working-drafts/{slug}/download
      POST /api/legal/working-drafts/{slug}/mark-ready
      POST /api/legal/working-drafts/{slug}/release   (admin only)
      POST /api/legal/working-drafts/{slug}/discard   (admin only)
      POST /api/legal/comments/{slug}/apply-roundtrip (writes working draft)
      helpers: _bump_minor / _next_version
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
HUB_SLUG = "01-terms-of-service"   # request said "birthright-hub" but no such source .md exists
LEGAL_DIR = Path("/app/backend/legal_docs")
SOURCE = LEGAL_DIR / f"{SLUG}.md"
HUB_SOURCE = LEGAL_DIR / f"{HUB_SLUG}.md"
SNAP_DIR = Path("/tmp/iter47_snapshots")

MARKER = "TEST_iter47 working draft body"
UPLOAD_MD = f"# Cookie Notice (TEST_iter47)\n\n{MARKER}\n\n## Section A\n\n- bullet one\n- bullet two\n"


# ---------------------------------------------------------------- helpers
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


def _upload(session, slug, content: bytes, filename="draft.md"):
    return session.post(
        f"{BASE_URL}/api/legal/docs/{slug}/upload",
        files={"file": (filename, io.BytesIO(content), "text/markdown")},
        timeout=120,
    )


@pytest.fixture(scope="module")
def counsel():
    return _session(COUNSEL, "readonly_admin")


@pytest.fixture(scope="module")
def admin():
    return _session(ADMIN, "admin")


@pytest.fixture(scope="module")
def mongo():
    if not MONGO_URL or not DB_NAME:
        pytest.skip("MONGO_URL / DB_NAME unavailable")
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module", autouse=True)
def protect_sources(mongo, admin):
    """Snapshot every legal source file + note pre-existing DB rows, then
    restore everything afterwards so no test data survives."""
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    files = list(LEGAL_DIR.glob("*.md")) + list(LEGAL_DIR.glob("*.docx"))
    for f in files:
        shutil.copy2(f, SNAP_DIR / f.name)

    pre_wd = {d["id"] for d in mongo.legal_doc_working_drafts.find({}, {"id": 1})}
    pre_rat = {d["id"] for d in mongo.legal_doc_ratifications.find({}, {"id": 1})}
    pre_rt = {d["id"] for d in mongo.legal_doc_roundtrips.find({}, {"id": 1})}
    pre_cm = {d["id"] for d in mongo.legal_doc_comments.find({}, {"id": 1})}

    yield

    # DB cleanup — only rows created by this module
    mongo.legal_doc_working_drafts.delete_many({"id": {"$nin": list(pre_wd)}})
    mongo.legal_doc_ratifications.delete_many({"id": {"$nin": list(pre_rat)}})
    mongo.legal_doc_roundtrips.delete_many({"id": {"$nin": list(pre_rt)}})
    mongo.legal_doc_comments.delete_many({"id": {"$nin": list(pre_cm)}})

    # File restore
    for f in SNAP_DIR.iterdir():
        shutil.copy2(f, LEGAL_DIR / f.name)
    shutil.rmtree(SNAP_DIR, ignore_errors=True)

    # Re-sync the built bundle with the restored sources
    try:
        admin.post(f"{BASE_URL}/api/legal/rebuild-docx", json={}, timeout=180)
    except Exception as exc:  # pragma: no cover
        print(f"rebuild-docx after restore failed: {exc}")


def _clear_open_draft(mongo, slug):
    mongo.legal_doc_working_drafts.update_many(
        {"source_slug": slug, "state": {"$in": ["draft", "awaiting_admin"]}},
        {"$set": {"state": "discarded"}},
    )


# ================================================================
# Working-draft happy path (counsel upload → admin release)
# ================================================================
class TestWorkingDraftHappyPath:
    def test_01_counsel_upload_creates_working_draft(self, counsel, mongo):
        _clear_open_draft(mongo, SLUG)
        before = SOURCE.read_text(encoding="utf-8")
        pytest.released_before = before

        r = _upload(counsel, SLUG, UPLOAD_MD.encode("utf-8"), "iter47-cookie.md")
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        assert data["source_slug"] == SLUG
        assert isinstance(data.get("working_draft_id"), str) and data["working_draft_id"]
        assert data["state"] == "draft"
        assert data["bytes_written"] == len(UPLOAD_MD.encode("utf-8"))
        assert "rebuilt_docx" not in data
        pytest.wd_id = data["working_draft_id"]

        # released .md untouched
        assert SOURCE.read_text(encoding="utf-8") == before, "released .md was modified by upload"

    def test_02_list_working_drafts_contains_row(self, counsel):
        r = counsel.get(f"{BASE_URL}/api/legal/working-drafts", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert isinstance(rows, list)
        match = [x for x in rows if x["id"] == pytest.wd_id]
        assert match, f"working draft {pytest.wd_id} missing from list"
        assert match[0]["source_slug"] == SLUG
        assert match[0]["state"] == "draft"
        assert "content_md" not in match[0], "list view should omit content_md"
        assert "_id" not in match[0]

    def test_03_working_draft_detail(self, counsel):
        r = counsel.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["content_md"] == UPLOAD_MD
        assert d["released_md"] == pytest.released_before
        assert isinstance(d["released_body_hash"], str) and d["released_body_hash"]
        assert d["is_stale"] is False
        assert isinstance(d["change_log"], list) and len(d["change_log"]) >= 1
        assert d["change_log"][-1]["action"] == "upload_full"
        assert d["change_log"][-1]["by_email"] == COUNSEL[0]
        assert "_id" not in d

    def test_04_download_working_draft_docx(self, counsel):
        r = counsel.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/download", timeout=120)
        assert r.status_code == 200, r.text[:300]
        assert r.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ), r.headers.get("content-type")
        assert f'filename="{SLUG}.working-draft.docx"' in r.headers.get("content-disposition", "")
        assert len(r.content) > 1000
        assert r.content[:2] == b"PK"

    def test_05_mark_ready(self, counsel):
        r = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/mark-ready", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["state"] == "awaiting_admin"
        d = counsel.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}", timeout=60).json()
        assert d["state"] == "awaiting_admin"

    def test_06_counsel_cannot_release(self, counsel):
        r = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                         json={}, timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:300]}"
        assert "Only admin can release" in r.text

    def test_07_admin_release_promotes_to_md(self, admin, mongo):
        prior = mongo.legal_doc_ratifications.count_documents({"source_slug": SLUG})
        latest = mongo.legal_doc_ratifications.find_one(
            {"source_slug": SLUG}, sort=[("ratified_at", -1)])
        prior_version = (latest or {}).get("version", "")

        r = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                       json={}, timeout=180)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        assert data["state"] == "released"
        assert data["working_draft_id"] == pytest.wd_id
        assert data["rebuilt_docx"] is True, f"docx rebuild failed: {data}"
        assert isinstance(data["ratification_id"], str) and data["ratification_id"]

        from routers.legal import _bump_minor  # noqa: E402
        expected = _bump_minor(prior_version) if prior_version else "1.0"
        assert data["released_as_version"] == expected, (
            f"expected auto-bump {expected} from prior {prior_version!r}, "
            f"got {data['released_as_version']}")

        # .md now carries the uploaded content. NOTE: the release step runs
        # scripts/eu_compliance_and_docx.py which APPENDS the EU/UK compliance
        # addendum, so the file is a superset of the uploaded bytes.
        released_now = SOURCE.read_text(encoding="utf-8")
        assert released_now.startswith(UPLOAD_MD), (
            "released .md does not start with the uploaded working-draft body:\n"
            + released_now[:400])
        assert MARKER in released_now
        assert pytest.released_before not in released_now
        # ratification row created
        assert mongo.legal_doc_ratifications.count_documents({"source_slug": SLUG}) == prior + 1
        rat = mongo.legal_doc_ratifications.find_one({"id": data["ratification_id"]})
        assert rat is not None
        assert rat["released_from_working_draft_id"] == pytest.wd_id
        assert rat["version"] == expected
        # no more open working draft
        assert admin.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}",
                         timeout=60).status_code == 404


# ================================================================
# Upload validation edge cases
# ================================================================
class TestUploadValidation:
    def test_size_cap(self, counsel):
        blob = b"# big\n" + (b"x" * (2 * 1024 * 1024 + 10))
        r = _upload(counsel, SLUG, blob, "huge.md")
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
        assert "2 MB cap" in r.text

    def test_unknown_slug(self, counsel):
        r = _upload(counsel, "nonexistent-slug", b"# nope\n", "x.md")
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_empty_file(self, counsel):
        r = _upload(counsel, SLUG, b"", "empty.md")
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_unsupported_extension(self, counsel):
        r = _upload(counsel, SLUG, b"nope", "evil.pdf")
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
        assert "Unsupported file type" in r.text

    def test_anonymous_upload_rejected(self):
        r = requests.post(
            f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
            files={"file": ("x.md", io.BytesIO(b"# hi"), "text/markdown")},
            timeout=60,
        )
        assert r.status_code in (401, 403), f"{r.status_code} {r.text[:200]}"


# ================================================================
# Discard
# ================================================================
class TestDiscard:
    def test_discard_flow(self, counsel, admin, mongo):
        _clear_open_draft(mongo, SLUG)
        before = SOURCE.read_text(encoding="utf-8")
        r = _upload(counsel, SLUG, b"# discard me TEST_iter47\n", "d.md")
        assert r.status_code == 200, r.text[:300]
        wd_id = r.json()["working_draft_id"]

        # counsel cannot discard
        bad = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
                           json={"reason": "testing"}, timeout=60)
        assert bad.status_code == 403, f"{bad.status_code} {bad.text[:200]}"
        assert "Only admin can discard" in bad.text

        ok = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
                        json={"reason": "testing"}, timeout=60)
        assert ok.status_code == 200, ok.text[:300]
        assert ok.json()["state"] == "discarded"
        assert ok.json()["working_draft_id"] == wd_id

        row = mongo.legal_doc_working_drafts.find_one({"id": wd_id})
        assert row["state"] == "discarded"
        assert row["discard_reason"] == "testing"
        # released .md untouched by discard
        assert SOURCE.read_text(encoding="utf-8") == before
        # no open draft anymore
        assert admin.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}",
                         timeout=60).status_code == 404
        assert admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
                          json={}, timeout=60).status_code == 404


# ================================================================
# Version bump logic
# ================================================================
class TestVersionBump:
    def test_bump_minor_unit(self):
        from routers.legal import _bump_minor
        assert _bump_minor("1.2") == "1.3"
        assert _bump_minor("2") == "2.1"
        assert _bump_minor("") == "1.0"
        assert _bump_minor("1.2.9") == "1.2.10"
        assert _bump_minor("v1-alpha") == "v1-alpha.1"

    def test_version_override_wins(self, counsel, admin, mongo):
        _clear_open_draft(mongo, SLUG)
        r = _upload(counsel, SLUG, b"# override TEST_iter47\n", "o.md")
        assert r.status_code == 200, r.text[:300]
        rel = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                         json={"version": "2.0", "notes": "TEST_iter47 override"},
                         timeout=180)
        assert rel.status_code == 200, rel.text[:300]
        assert rel.json()["released_as_version"] == "2.0"
        rat = mongo.legal_doc_ratifications.find_one({"id": rel.json()["ratification_id"]})
        assert rat["version"] == "2.0"
        assert rat["notes"] == "TEST_iter47 override"

    def test_auto_bump_after_prior(self, counsel, admin, mongo):
        """Prior ratification is now 2.0 → next auto-bump must be 2.1."""
        _clear_open_draft(mongo, SLUG)
        r = _upload(counsel, SLUG, b"# bump TEST_iter47\n", "b.md")
        assert r.status_code == 200, r.text[:300]
        rel = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                         json={}, timeout=180)
        assert rel.status_code == 200, rel.text[:300]
        assert rel.json()["released_as_version"] == "2.1", rel.json()


# ================================================================
# apply-roundtrip writes to the working draft, not the released .md
# ================================================================
class TestApplyRoundtripWorkingDraft:
    def test_roundtrip_targets_working_draft(self, counsel, admin, mongo):
        _clear_open_draft(mongo, HUB_SLUG)
        original = HUB_SOURCE.read_text(encoding="utf-8")
        # pick a real phrase from the doc so the replace actually lands
        quoted = next((ln.strip() for ln in original.splitlines()
                       if len(ln.strip()) > 25 and not ln.strip().startswith("#")), None)
        assert quoted, "could not find a quotable line in the hub source .md"
        replacement = quoted + " TEST_iter47_REDLINE"

        c = counsel.post(f"{BASE_URL}/api/legal/comments/{HUB_SLUG}", json={
            "body": "TEST_iter47 redline",
            "kind": "redline",
            "quoted_text": quoted,
            "suggested_replacement": replacement,
        }, timeout=60)
        assert c.status_code == 200, c.text[:300]
        cid = c.json()["id"]

        rt = admin.post(f"{BASE_URL}/api/legal/comments/{HUB_SLUG}/apply-roundtrip",
                        json={"decisions": [{"comment_id": cid, "action": "accept"}]},
                        timeout=120)
        assert rt.status_code == 200, f"{rt.status_code} {rt.text[:400]}"
        d = rt.json()
        assert d["applied"] == 1, d
        assert d["state"] == "draft"
        assert isinstance(d.get("working_draft_id"), str) and d["working_draft_id"]

        # released .md UNCHANGED
        assert HUB_SOURCE.read_text(encoding="utf-8") == original, \
            "apply-roundtrip modified the released source .md"

        # working draft holds the redlined body
        row = mongo.legal_doc_working_drafts.find_one({"id": d["working_draft_id"]})
        assert row is not None
        assert "TEST_iter47_REDLINE" in row["content_md"]
        assert row["state"] == "draft"
        assert row["change_log"][-1]["action"] == "apply_roundtrip"
