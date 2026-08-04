"""Iteration 51 — @mention email dispatch + rollback preview.

Modules under test:
  - backend/routers/legal.py
      POST /api/legal/working-drafts/{slug}/comments   (mentions parsing + email)
      GET  /api/legal/history/{slug}/rollback-preview/{ratification_id}
      _parse_mentions / _email_comment_mentions (unit)
"""
import asyncio
import io
import os
import re
import sys
import time

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
MENTION_SUBJECT_RX = re.compile(r"You were mentioned in a .* comment")

MD_A = "# Cookie Notice (TEST_iter51 A)\n\nTEST_iter51 alpha line\n\n## Section A\n\n- one\n- two\n"
MD_B = "# Cookie Notice (TEST_iter51 B)\n\nTEST_iter51 beta line changed\n\n## Section B\n\n- three\n"


# ------------------------------------------------------------------ helpers
def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    b = r.json()
    return b["token"], b["user"]


def _session(creds, expected_role):
    token, user = _login(*creds)
    assert user["role"] == expected_role, f"expected {expected_role}, got {user['role']}"
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    s.user = user
    return s


def _upload(session, slug, content):
    return session.post(
        f"{BASE_URL}/api/legal/docs/{slug}/upload",
        files={"file": ("draft.md", io.BytesIO(content.encode("utf-8")), "text/markdown")},
        timeout=120,
    )


def _post_comment(session, slug=SLUG, **payload):
    return session.post(f"{BASE_URL}/api/legal/working-drafts/{slug}/comments",
                        json=payload, timeout=60)


def _mention_emails(mongo, since_iso):
    """All mention emails (sent or dry-run) created at/after since_iso."""
    rows = []
    for coll in ("email_log", "outbound_emails"):
        rows += list(mongo[coll].find(
            {"subject": {"$regex": "You were mentioned in a"},
             "created_at": {"$gte": since_iso}}, {"_id": 0}))
    return rows


def _wait_for_mention_email(mongo, since_iso, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = _mention_emails(mongo, since_iso)
        if rows:
            return rows
        time.sleep(1.5)
    return []


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def admin():
    return _session(ADMIN, "admin")


@pytest.fixture(scope="module")
def counsel():
    return _session(COUNSEL, "readonly_admin")


@pytest.fixture(scope="module")
def source_snapshot():
    from pathlib import Path
    keep = {}
    for ext in (".md", ".docx"):
        p = Path("/app/backend/legal_docs") / f"{SLUG}{ext}"
        if p.exists():
            keep[p] = p.read_bytes()
    yield keep
    for p, raw in keep.items():
        if p.read_bytes() != raw:
            p.write_bytes(raw)


@pytest.fixture(scope="module", autouse=True)
def cleanup(mongo, admin, source_snapshot):
    started = _now_iso_utc()
    yield
    try:
        admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
                   json={"reason": "TEST_iter51 cleanup"}, timeout=60)
    except Exception:
        pass
    wd_ids = [w["id"] for w in mongo.legal_doc_working_drafts.find(
        {"source_slug": SLUG}, {"id": 1})]
    mongo.legal_working_draft_comments.delete_many({"working_draft_id": {"$in": wd_ids}})
    mongo.legal_working_draft_comments.delete_many({"source_slug": SLUG})
    mongo.legal_doc_working_drafts.delete_many({"source_slug": SLUG})
    mongo.legal_doc_ratifications.delete_many(
        {"source_slug": SLUG, "created_at": {"$gte": started}})
    mongo.legal_doc_ratifications.delete_many(
        {"source_slug": SLUG, "notes": {"$regex": "TEST_iter51"}})
    for coll in ("email_log", "outbound_emails"):
        mongo[coll].delete_many({"subject": {"$regex": "You were mentioned in a"},
                                 "created_at": {"$gte": started}})


def _now_iso_utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@pytest.fixture(scope="module")
def wd(admin, counsel):
    """One open working draft on SLUG (created by counsel)."""
    admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
               json={"reason": "TEST_iter51 pre-clean"}, timeout=60)
    r = _upload(counsel, SLUG, MD_A)
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:400]}"
    d = admin.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}", timeout=60)
    assert d.status_code == 200, d.text[:300]
    return d.json()


# ================================================= mention parsing (API)
class TestMentionParsing:
    @pytest.mark.parametrize("body,expected", [
        ("TEST_iter51 hey @admin and @counsel please look", ["admin", "counsel"]),
        ("TEST_iter51 @Admin @COUNSEL mixed case", ["admin", "counsel"]),
        ("TEST_iter51 @counsel first then @admin", ["counsel", "admin"]),
        ("TEST_iter51 @adminfoo is not a mention", []),
        ("TEST_iter51 @counsellor not matched either", []),
        ("TEST_iter51 @dev @support @legalteam ignored", []),
        ("TEST_iter51 plain body no mentions", []),
        ("TEST_iter51 dedup @admin @admin @admin", ["admin"]),
        ("TEST_iter51 punctuation @admin, and @counsel.", ["admin", "counsel"]),
        ("TEST_iter51 email like foo@admin.com", ["admin"]),
    ])
    def test_mentions_field(self, counsel, wd, body, expected):
        r = _post_comment(counsel, body=body, side="general")
        assert r.status_code in (200, 201), r.text[:300]
        c = r.json()
        assert "mentions" in c, "response missing `mentions`"
        assert c["mentions"] == expected, f"body={body!r} -> {c['mentions']}"
        assert "_id" not in c

    def test_mentions_persisted_on_get(self, counsel, admin, wd):
        r = _post_comment(counsel, body="TEST_iter51 persist @admin check", line_number=2,
                          side="working")
        cid = r.json()["id"]
        rows = admin.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments",
                         timeout=60).json()
        row = next((x for x in rows if x["id"] == cid), None)
        assert row is not None, "comment not persisted"
        assert row.get("mentions") == ["admin"]


# ================================================= email dispatch (API)
class TestMentionEmails:
    def test_counsel_mentions_admin_emails_admin(self, counsel, mongo, wd):
        since = _now_iso_utc()
        r = _post_comment(counsel, body="TEST_iter51 @admin please review line 3",
                          line_number=3, side="working")
        assert r.status_code in (200, 201), r.text[:300]
        rows = _wait_for_mention_email(mongo, since)
        assert rows, "no mention email recorded in email_log/outbound_emails"
        row = rows[0]
        assert ADMIN[0] in row["to"], row["to"]
        assert COUNSEL[0] not in row["to"], "author must be suppressed"
        assert MENTION_SUBJECT_RX.search(row["subject"]), row["subject"]
        assert "line 3" in row["subject"], row["subject"]
        assert "Cookie" in row["subject"], row["subject"]

    def test_general_note_anchor_in_subject(self, counsel, mongo, wd):
        since = _now_iso_utc()
        r = _post_comment(counsel, body="TEST_iter51 @admin general ping", side="general")
        assert r.status_code in (200, 201)
        rows = _wait_for_mention_email(mongo, since)
        assert rows, "no mention email for general note"
        assert "general note" in rows[0]["subject"], rows[0]["subject"]

    def test_admin_mentions_counsel_emails_counsel(self, admin, mongo, wd):
        since = _now_iso_utc()
        r = _post_comment(admin, body="TEST_iter51 @counsel over to you", line_number=5,
                          side="working")
        assert r.status_code in (200, 201), r.text[:300]
        rows = _wait_for_mention_email(mongo, since)
        assert rows, "no mention email for @counsel"
        assert COUNSEL[0] in rows[0]["to"], rows[0]["to"]
        assert ADMIN[0] not in rows[0]["to"], "author admin must be suppressed"

    def test_admin_mentions_both_roles(self, admin, mongo, wd):
        since = _now_iso_utc()
        r = _post_comment(admin, body="TEST_iter51 @admin @counsel both roles",
                          line_number=1, side="working")
        assert r.status_code in (200, 201)
        assert r.json()["mentions"] == ["admin", "counsel"]
        rows = _wait_for_mention_email(mongo, since)
        assert rows, "no mention email when both roles mentioned"
        all_to = sorted({e for row in rows for e in row["to"]})
        assert COUNSEL[0] in all_to
        assert ADMIN[0] not in all_to, "self-mention (author) not suppressed"
        # dedup: each recipient appears at most once overall
        flat = [e for row in rows for e in row["to"]]
        assert len(flat) == len(set(flat)), f"duplicate recipients: {flat}"

    def test_self_mention_only_recipient_sends_nothing(self, counsel, mongo, wd):
        """counsel posts @counsel; counsel is the only readonly_admin -> no email."""
        since = _now_iso_utc()
        r = _post_comment(counsel, body="TEST_iter51 @counsel self note", line_number=4,
                          side="working")
        assert r.status_code in (200, 201)
        assert r.json()["mentions"] == ["counsel"]
        time.sleep(6)
        rows = _mention_emails(mongo, since)
        assert rows == [], f"email sent despite self-suppression: {rows}"

    def test_no_mentions_sends_no_email(self, counsel, mongo, wd):
        since = _now_iso_utc()
        r = _post_comment(counsel, body="TEST_iter51 quiet comment no ping", side="general")
        assert r.status_code in (200, 201)
        assert r.json()["mentions"] == []
        time.sleep(4)
        assert _mention_emails(mongo, since) == []


# ================================================= unit: no matching users
class TestMentionUnit:
    def test_parse_mentions_unit(self):
        from routers.legal import _parse_mentions
        assert _parse_mentions("@admin") == ["admin"]
        assert _parse_mentions("@ADMIN @Counsel") == ["admin", "counsel"]
        assert _parse_mentions("@administrator") == []
        assert _parse_mentions("") == []
        assert _parse_mentions(None) == []

    def test_email_mentions_with_no_matching_users(self, monkeypatch):
        """db.users.find yields nothing -> must return cleanly, no send."""
        import database
        import routers.legal as legal
        import utils.mailer as mailer

        class _EmptyCursor:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        class _Users:
            def find(self, *a, **k):
                return _EmptyCursor()

        class _FakeDB:
            users = _Users()

        sent = []

        async def _fake_send(*a, **k):
            sent.append((a, k))
            return "fake"

        monkeypatch.setattr(database, "db", _FakeDB())
        monkeypatch.setattr(mailer, "send_email", _fake_send)

        comment = {"mentions": ["admin", "counsel"], "line_number": 2, "body": "x @admin"}
        asyncio.run(legal._email_comment_mentions(
            SLUG, {"id": "wd1"}, comment, {"id": "u1", "email": "a@b.c", "role": "admin"}))
        assert sent == [], "send_email called despite zero recipients"


# ================================================= rollback preview
@pytest.fixture(scope="module")
def two_releases(admin, counsel, source_snapshot):
    """Create two releases on SLUG; returns (older_rat, newer_rat) dicts."""
    made = []
    for md in (MD_A, MD_B):
        admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
                   json={"reason": "TEST_iter51 rel pre-clean"}, timeout=60)
        up = _upload(counsel, SLUG, md)
        assert up.status_code == 200, up.text[:300]
        rel = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                         json={"notes": "TEST_iter51 release"}, timeout=180)
        assert rel.status_code in (200, 201), f"release failed: {rel.status_code} {rel.text[:400]}"
        made.append(rel.json())
    t = admin.get(f"{BASE_URL}/api/legal/history-timeline/{SLUG}",
                  params={"limit": 10}, timeout=60)
    assert t.status_code == 200, t.text[:300]
    versions = t.json()["versions"]
    assert len(versions) >= 2, versions
    return versions[1], versions[0]  # older, newer(current)


class TestRollbackPreview:
    def test_shape_and_values(self, admin, two_releases):
        older, current = two_releases
        r = admin.get(f"{BASE_URL}/api/legal/history/{SLUG}/rollback-preview/{older['id']}",
                      timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for k in ("source_slug", "target_version", "target_ratified_at", "target_ratified_by",
                  "target_md", "current_version", "current_ratified_at", "current_md"):
            assert k in d, f"missing {k}"
        assert d["source_slug"] == SLUG
        assert d["target_version"] == older["version"]
        assert d["current_version"] == current["version"]
        assert d["target_ratified_by"] == older["ratified_by"]
        assert isinstance(d["target_md"], str) and len(d["target_md"]) > 20
        assert isinstance(d["current_md"], str) and len(d["current_md"]) > 20
        assert d["target_md"] != d["current_md"], "test setup: snapshots should differ"
        assert "TEST_iter51 alpha" in d["target_md"]
        assert "TEST_iter51 beta" in d["current_md"]
        assert "_id" not in d

    def test_counsel_can_read_preview(self, counsel, two_releases):
        older, _ = two_releases
        r = counsel.get(f"{BASE_URL}/api/legal/history/{SLUG}/rollback-preview/{older['id']}",
                        timeout=60)
        assert r.status_code == 200, f"counsel blocked: {r.status_code} {r.text[:300]}"

    def test_requires_auth(self, two_releases):
        older, _ = two_releases
        r = requests.get(
            f"{BASE_URL}/api/legal/history/{SLUG}/rollback-preview/{older['id']}", timeout=60)
        assert r.status_code in (401, 403), r.status_code

    def test_unknown_ratification_404(self, admin, two_releases):
        r = admin.get(f"{BASE_URL}/api/legal/history/{SLUG}/rollback-preview/does-not-exist",
                      timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_unknown_slug_404(self, admin, two_releases):
        older, _ = two_releases
        r = admin.get(
            f"{BASE_URL}/api/legal/history/99-not-a-doc/rollback-preview/{older['id']}",
            timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_ratification_of_other_slug_404(self, admin, mongo, two_releases):
        other = mongo.legal_doc_ratifications.find_one(
            {"source_slug": {"$ne": SLUG}}, {"_id": 0, "id": 1})
        if not other:
            pytest.skip("no ratification for another slug available")
        r = admin.get(
            f"{BASE_URL}/api/legal/history/{SLUG}/rollback-preview/{other['id']}", timeout=60)
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_missing_snapshot_400(self, admin, mongo, two_releases):
        older, _ = two_releases
        mongo.legal_doc_ratifications.update_one(
            {"id": older["id"]}, {"$unset": {"content_md_snapshot": ""}})
        try:
            r = admin.get(
                f"{BASE_URL}/api/legal/history/{SLUG}/rollback-preview/{older['id']}", timeout=60)
            assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
            assert "snapshot" in r.json().get("detail", "").lower(), r.text[:200]
        finally:
            snap = MD_A
            mongo.legal_doc_ratifications.update_one(
                {"id": older["id"]}, {"$set": {"content_md_snapshot": snap}})

    def test_preview_has_no_side_effects(self, admin, two_releases, mongo):
        older, _ = two_releases
        before = mongo.legal_doc_ratifications.count_documents({"source_slug": SLUG})
        admin.get(f"{BASE_URL}/api/legal/history/{SLUG}/rollback-preview/{older['id']}",
                  timeout=60)
        after = mongo.legal_doc_ratifications.count_documents({"source_slug": SLUG})
        assert before == after, "preview mutated ratifications"

    def test_identical_snapshot_preview_matches_current(self, admin, two_releases):
        """Preview of the CURRENT release should return target_md == current_md."""
        _, current = two_releases
        r = admin.get(f"{BASE_URL}/api/legal/history/{SLUG}/rollback-preview/{current['id']}",
                      timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["target_version"] == d["current_version"]
        assert d["target_md"] == d["current_md"], (
            "current release snapshot differs from on-disk .md "
            f"({len(d['target_md'])} vs {len(d['current_md'])} bytes)")
