"""Iteration 48 — Working-draft mark-ready email fanout + diff payload.

Modules under test:
  - backend/routers/legal.py
      POST /api/legal/docs/{slug}/upload               (creates working draft)
      POST /api/legal/working-drafts/{slug}/mark-ready (emails all admins)
      GET  /api/legal/working-drafts/{slug}            (diff-modal payload)
      helper _email_working_draft_ready (in-process, failure path)
  - backend/utils/mailer.send_email (email_log / outbound_emails rows)
"""
import asyncio
import io
import os
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
# NOTE: the review request mentions slug "birthright-hub" — no such legal
# source doc exists. Terms of Service is used as the second slug.
SLUG2 = "01-terms-of-service"

TEST_ADMIN_EMAIL = "test_iter48_admin@birthright.live"

UPLOAD_MD = (
    "# Cookie Notice (TEST_iter48)\n\n"
    "TEST_iter48 body v1\n\n## Section A\n\n- bullet one\n- bullet two\n"
)
UPLOAD_MD_V2 = (
    "# Cookie Notice (TEST_iter48)\n\n"
    "TEST_iter48 body v2 edited\n\n## Section A\n\n- bullet one\n- bullet two\n- bullet three\n"
)


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


def _upload(session, slug, content: str, filename="draft.md"):
    return session.post(
        f"{BASE_URL}/api/legal/docs/{slug}/upload",
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/markdown")},
        timeout=120,
    )


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def counsel():
    return _session(COUNSEL, "readonly_admin")


@pytest.fixture(scope="module")
def admin():
    return _session(ADMIN, "admin")


@pytest.fixture(scope="module")
def source_snapshots():
    """Snapshot released .md/.docx so nothing leaks into the repo."""
    legal_dir = Path("/app/backend/legal_docs")
    keep = {}
    for slug in (SLUG, SLUG2):
        for ext in (".md", ".docx"):
            p = legal_dir / f"{slug}{ext}"
            if p.exists():
                keep[p] = p.read_bytes()
    yield keep
    for p, raw in keep.items():
        if p.read_bytes() != raw:
            p.write_bytes(raw)


@pytest.fixture(scope="module", autouse=True)
def cleanup(mongo, admin, source_snapshots):
    """Remove working drafts + email rows this module creates."""
    yield
    for slug in (SLUG, SLUG2):
        try:
            admin.post(f"{BASE_URL}/api/legal/working-drafts/{slug}/discard",
                       json={"reason": "TEST_iter48 cleanup"}, timeout=60)
        except Exception:
            pass
    mongo.legal_doc_working_drafts.delete_many(
        {"source_slug": {"$in": [SLUG, SLUG2]},
         "content_md": {"$regex": "TEST_iter48"}}
    )
    mongo.email_log.delete_many({"template": "legal_working_draft_ready",
                                 "metadata.source_slug": {"$in": [SLUG, SLUG2]}})
    mongo.outbound_emails.delete_many({"template": "legal_working_draft_ready",
                                       "metadata.source_slug": {"$in": [SLUG, SLUG2]}})
    mongo.users.delete_many({"email": TEST_ADMIN_EMAIL})


def _latest_email_row(mongo, slug):
    rows = []
    for coll in (mongo.email_log, mongo.outbound_emails):
        rows.extend(list(coll.find(
            {"template": "legal_working_draft_ready",
             "metadata.source_slug": slug},
            {"_id": 0},
        )))
    if not rows:
        return None
    rows.sort(key=lambda r: r.get("created_at") or r.get("queued_at") or "")
    return rows[-1]


def _admin_emails(mongo):
    return sorted({u["email"] for u in mongo.users.find({"role": "admin"}, {"email": 1})
                   if u.get("email")})


# ------------------------------------------------- mark-ready email dispatch
class TestMarkReadyEmail:
    def test_upload_creates_working_draft(self, counsel):
        r = _upload(counsel, SLUG, UPLOAD_MD)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body.get("state") in ("draft", "awaiting_admin")
        assert body.get("bytes_written", 0) > 0

    def test_mark_ready_returns_email_id(self, counsel, mongo):
        r = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/mark-ready", timeout=120)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["state"] == "awaiting_admin"
        assert isinstance(body.get("working_draft_id"), str) and body["working_draft_id"]
        assert "email_id" in body
        # Row must be logged regardless of send outcome
        row = _latest_email_row(mongo, SLUG)
        assert row is not None, "no legal_working_draft_ready email row logged"
        assert row["template"] == "legal_working_draft_ready"
        assert row.get("status") in ("sent", "queued_dry_run", "failed")
        if row.get("status") == "failed":
            pytest.fail(f"email send failed: {row.get('error')}")
        assert body["email_id"], "email_id empty although send did not fail"

    def test_recipients_are_all_admins_and_exclude_counsel(self, mongo):
        row = _latest_email_row(mongo, SLUG)
        assert row is not None
        recipients = sorted(row.get("to") or [])
        admins = _admin_emails(mongo)
        assert recipients == admins, f"recipients {recipients} != admins {admins}"
        assert COUNSEL[0] not in recipients, "counsel must not receive the admin notification"

    def test_idempotent_second_mark_ready(self, counsel):
        r1 = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/mark-ready", timeout=120)
        assert r1.status_code == 200, r1.text[:300]
        r2 = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/mark-ready", timeout=120)
        assert r2.status_code == 200, r2.text[:300]
        assert r2.json()["state"] == "awaiting_admin"
        assert r2.json()["working_draft_id"] == r1.json()["working_draft_id"]

    def test_fanout_to_two_admins(self, counsel, mongo):
        """Seed a second admin, mark ready again, expect both addressed."""
        existing = mongo.users.find_one({"email": ADMIN[0]}, {"_id": 0})
        assert existing, "primary admin user missing"
        seeded = False
        if TEST_ADMIN_EMAIL not in _admin_emails(mongo):
            doc = dict(existing)
            doc["id"] = "test-iter48-admin"
            doc["email"] = TEST_ADMIN_EMAIL
            doc["name"] = "TEST_iter48 Second Admin"
            mongo.users.insert_one(doc)
            seeded = True
        try:
            admins = _admin_emails(mongo)
            assert len(admins) >= 2
            # Re-edit so mark-ready is meaningful, then mark ready
            up = _upload(counsel, SLUG, UPLOAD_MD_V2)
            assert up.status_code == 200, up.text[:300]
            r = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/mark-ready", timeout=120)
            assert r.status_code == 200, r.text[:300]
            row = _latest_email_row(mongo, SLUG)
            recipients = sorted(row.get("to") or [])
            assert recipients == admins, f"fanout {recipients} != admins {admins}"
            assert len(recipients) == len(admins) >= 2
        finally:
            if seeded:
                mongo.users.delete_many({"email": TEST_ADMIN_EMAIL})


# -------------------------------------------- email failure must not break
class TestEmailFailureIsolation:
    def test_helper_returns_none_when_send_raises(self):
        import utils.mailer as mailer
        import routers.legal as legal

        async def boom(*a, **k):
            raise RuntimeError("TEST_iter48 forced send failure")

        original = mailer.send_email
        mailer.send_email = boom
        try:
            result = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
                legal._email_working_draft_ready(
                    source_slug=SLUG,
                    wd={"id": "test-iter48-wd", "change_log": [], "content_md": "x"},
                    marker={"email": COUNSEL[0], "role": "readonly_admin"},
                )
            )
            assert result is None, f"expected None on send failure, got {result}"
        finally:
            mailer.send_email = original


# ---------------------------------------------------- diff modal GET payload
class TestDiffPayload:
    def test_fresh_working_draft_payload(self, counsel):
        up = _upload(counsel, SLUG2, UPLOAD_MD)
        assert up.status_code == 200, up.text[:300]
        r = counsel.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG2}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "_id" not in d
        for field in ("released_md", "content_md", "change_log", "is_stale",
                      "released_body_hash", "state", "source_slug"):
            assert field in d, f"missing {field}"
        assert isinstance(d["released_md"], str) and len(d["released_md"]) > 100
        assert "TEST_iter48" in d["content_md"]
        assert isinstance(d["change_log"], list) and len(d["change_log"]) >= 1
        assert isinstance(d["is_stale"], bool)

    def test_payload_after_multiple_edits(self, counsel):
        assert _upload(counsel, SLUG2, UPLOAD_MD_V2).status_code == 200
        assert _upload(counsel, SLUG2, UPLOAD_MD).status_code == 200
        r = counsel.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG2}", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert len(d["change_log"]) >= 3, d["change_log"]
        assert d["released_md"] and d["content_md"]
        assert d["is_stale"] is False

    def test_identical_working_draft_diff_payload(self, counsel):
        """Upload the released body verbatim → diff should be empty."""
        r0 = counsel.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG2}", timeout=60)
        released = r0.json()["released_md"]
        up = _upload(counsel, SLUG2, released)
        assert up.status_code == 200, up.text[:300]
        r = counsel.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG2}", timeout=60)
        d = r.json()
        assert d["content_md"].strip() == released.strip(), "identical upload should round-trip"

    def test_missing_working_draft_returns_404(self, counsel):
        r = counsel.get(f"{BASE_URL}/api/legal/working-drafts/12-volunteer-agreement", timeout=60)
        assert r.status_code == 404, r.status_code

    def test_mark_ready_without_draft_returns_404(self, counsel):
        r = counsel.post(f"{BASE_URL}/api/legal/working-drafts/12-volunteer-agreement/mark-ready",
                         timeout=60)
        assert r.status_code == 404, r.status_code
