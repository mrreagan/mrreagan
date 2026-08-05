"""Iteration 52 — daily @mention digest (replaces per-comment mention emails).

Modules under test:
  - backend/routers/legal.py
      POST /api/legal/working-drafts/{slug}/comments   (no per-comment email now)
      POST /api/legal/admin/mention-digest/send-now    (admin-only manual digest)
      _send_legal_mention_digests()                    (grouping / skip rules)
  - backend/utils/scheduler.py  (legal_mention_digest job registration)
"""
import io
import os
import sys
import time
from datetime import datetime, timezone
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
MD_A = "# Cookie Notice (TEST_iter52 A)\n\nTEST_iter52 alpha line\n\n## Section A\n\n- one\n- two\n"


# ------------------------------------------------------------------ helpers
def _now_iso_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _trigger(session):
    return session.post(f"{BASE_URL}/api/legal/admin/mention-digest/send-now", timeout=120)


def _emails(mongo, since_iso, subject_rx):
    rows = []
    for coll in ("email_log", "outbound_emails"):
        rows += list(mongo[coll].find(
            {"subject": {"$regex": subject_rx}, "created_at": {"$gte": since_iso}},
            {"_id": 0}))
    return rows


def _wait_emails(mongo, since_iso, subject_rx, timeout=20, minimum=1):
    deadline = time.time() + timeout
    rows = []
    while time.time() < deadline:
        rows = _emails(mongo, since_iso, subject_rx)
        if len(rows) >= minimum:
            return rows
        time.sleep(1.0)
    return rows


# ------------------------------------------------------------------ fixtures
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
                   json={"reason": "TEST_iter52 cleanup"}, timeout=60)
    except Exception:
        pass
    wd_ids = [w["id"] for w in mongo.legal_doc_working_drafts.find({"source_slug": SLUG}, {"id": 1})]
    mongo.legal_working_draft_comments.delete_many({"working_draft_id": {"$in": wd_ids}})
    mongo.legal_working_draft_comments.delete_many({"source_slug": SLUG})
    mongo.legal_doc_working_drafts.delete_many({"source_slug": SLUG})
    mongo.legal_doc_ratifications.delete_many({"source_slug": SLUG, "created_at": {"$gte": started}})
    mongo.legal_doc_ratifications.delete_many({"source_slug": SLUG, "notes": {"$regex": "TEST_iter52"}})
    for coll in ("email_log", "outbound_emails"):
        mongo[coll].delete_many({"template": "legal_mention_digest", "created_at": {"$gte": started}})
        mongo[coll].delete_many({"subject": {"$regex": "You were mentioned in a"},
                                 "created_at": {"$gte": started}})


@pytest.fixture(scope="module")
def wd(admin, counsel, mongo):
    """One open working draft on SLUG (created by counsel) + a flushed digest queue."""
    admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
               json={"reason": "TEST_iter52 pre-clean"}, timeout=60)
    # remove stale pending mentions from any earlier iteration so counters are clean
    mongo.legal_working_draft_comments.update_many(
        {"mention_digest_sent_at": None}, {"$set": {"mention_digest_sent_at": _now_iso_utc()}})
    r = _upload(counsel, SLUG, MD_A)
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:400]}"
    d = admin.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}", timeout=60)
    assert d.status_code == 200, d.text[:300]
    return d.json()


# ============================================ 1. no per-comment mention email
class TestNoPerCommentEmail:
    def test_comment_with_mention_creates_no_email(self, counsel, mongo, wd):
        since = _now_iso_utc()
        r = _post_comment(counsel, body="TEST_iter52 @admin no instant email please",
                          line_number=3, side="working")
        assert r.status_code in (200, 201), r.text[:300]
        c = r.json()
        assert c["mentions"] == ["admin"], c.get("mentions")
        assert c.get("mention_digest_sent_at") is None, c.get("mention_digest_sent_at")
        assert "_id" not in c
        # give any (removed) background task a chance to fire
        time.sleep(6)
        rows = _emails(mongo, since, "You were mentioned")
        assert rows == [], f"per-comment mention email still fired: {[r_['subject'] for r_ in rows]}"

    def test_mention_digest_field_persisted_on_get(self, admin, mongo, wd):
        rows = admin.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments", timeout=60).json()
        assert rows, "no comments returned"
        target = [x for x in rows if "no instant email" in x["body"]]
        assert target, "comment not persisted"
        assert "mention_digest_sent_at" in target[0]
        assert target[0]["mention_digest_sent_at"] is None


# ============================================ 2. digest happy path
class TestDigestFlow:
    def test_digest_groups_and_marks(self, admin, counsel, mongo, wd):
        # Clear anything pending from the previous class so counters are exact.
        _trigger(admin)
        time.sleep(1)

        # 3 pending comments: 2 x @admin, 1 x @counsel
        ids = []
        for body, line in (("TEST_iter52 digest one @admin", 1),
                           ("TEST_iter52 digest two @admin", 2),
                           ("TEST_iter52 digest three @counsel", 3)):
            r = _post_comment(counsel, body=body, line_number=line, side="working")
            assert r.status_code in (200, 201), r.text[:300]
            ids.append(r.json()["id"])

        # resolved comment with @admin — must NOT be included
        r = _post_comment(counsel, body="TEST_iter52 resolved @admin skip", side="general")
        resolved_id = r.json()["id"]
        rr = admin.post(
            f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{resolved_id}/resolve",
            json={}, timeout=60)
        assert rr.status_code in (200, 201), rr.text[:300]

        # already-digested comment with @admin — must NOT be re-included
        r = _post_comment(counsel, body="TEST_iter52 already digested @admin skip", side="general")
        digested_id = r.json()["id"]
        mongo.legal_working_draft_comments.update_one(
            {"id": digested_id}, {"$set": {"mention_digest_sent_at": _now_iso_utc()}})

        since = _now_iso_utc()
        resp = _trigger(admin)
        assert resp.status_code == 200, resp.text[:400]
        data = resp.json()
        assert data["pending"] == 3, f"expected pending=3, got {data}"
        assert data["sent"] == 2, f"expected sent=2 (admin+counsel), got {data}"
        assert set(data["notified_comment_ids"]) == set(ids), data["notified_comment_ids"]
        assert data["recipients_by_role"].get("admin", 0) >= 1, data["recipients_by_role"]
        assert data["recipients_by_role"].get("counsel", 0) >= 1, data["recipients_by_role"]

        # digest timestamps set on the 3 notified comments only
        for cid in ids:
            row = mongo.legal_working_draft_comments.find_one({"id": cid}, {"_id": 0})
            assert row["mention_digest_sent_at"], f"{cid} not marked digested"
        assert mongo.legal_working_draft_comments.find_one(
            {"id": resolved_id})["mention_digest_sent_at"] is None, "resolved comment digested"

        # ---- email content assertions
        rows = _wait_emails(mongo, since, "Legal review digest", minimum=2)
        assert len(rows) >= 2, f"expected 2 digest emails, got {[x['subject'] for x in rows]}"
        by_role = {x.get("metadata", {}).get("role"): x for x in rows}
        assert set(by_role) == {"admin", "counsel"}, list(by_role)
        assert "Legal review digest" in by_role["admin"]["subject"]
        assert by_role["admin"]["metadata"]["count"] == 2, by_role["admin"]["metadata"]
        assert by_role["counsel"]["metadata"]["count"] == 1, by_role["counsel"]["metadata"]

        admin_emails = {u["email"] for u in mongo.users.find({"role": "admin"}, {"email": 1})}
        counsel_emails = {u["email"] for u in mongo.users.find({"role": "readonly_admin"}, {"email": 1})}
        assert set(by_role["admin"]["to"]) == admin_emails, by_role["admin"]["to"]
        assert set(by_role["counsel"]["to"]) == counsel_emails, by_role["counsel"]["to"]
        # author suppression must NOT apply at digest time (counsel authored the @counsel comment)
        assert COUNSEL[0] in by_role["counsel"]["to"], by_role["counsel"]["to"]

    def test_second_trigger_is_noop(self, admin):
        resp = _trigger(admin)
        assert resp.status_code == 200, resp.text[:300]
        data = resp.json()
        assert data["pending"] == 0, data
        assert data["sent"] == 0, data

    def test_comments_without_mentions_never_pending(self, counsel, admin, wd):
        r = _post_comment(counsel, body="TEST_iter52 plain body no mention", side="general")
        assert r.status_code in (200, 201)
        assert r.json()["mentions"] == []
        data = _trigger(admin).json()
        assert data["pending"] == 0, data


# ============================================ 3. permissions
class TestDigestPermissions:
    def test_counsel_forbidden(self, counsel):
        resp = _trigger(counsel)
        assert resp.status_code == 403, f"{resp.status_code} {resp.text[:300]}"
        detail = (resp.json() or {}).get("detail") or resp.text
        assert "admin" in str(detail).lower(), detail

    def test_anonymous_unauthorized(self):
        resp = requests.post(f"{BASE_URL}/api/legal/admin/mention-digest/send-now", timeout=60)
        assert resp.status_code in (401, 403), resp.status_code


# ============================================ 4. closed working drafts skipped
class TestClosedDraftSkipped:
    def test_discarded_wd_mentions_skipped(self, admin, counsel, mongo, wd):
        _trigger(admin)
        r = _post_comment(counsel, body="TEST_iter52 discard-me @admin ping", line_number=1,
                          side="working")
        assert r.status_code in (200, 201), r.text[:300]
        cid = r.json()["id"]

        d = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
                       json={"reason": "TEST_iter52 discard for digest skip"}, timeout=60)
        assert d.status_code in (200, 201), d.text[:300]

        data = _trigger(admin).json()
        assert data["pending"] == 0, f"discarded WD mention still pending: {data}"
        row = mongo.legal_working_draft_comments.find_one({"id": cid}, {"_id": 0})
        assert row["mention_digest_sent_at"] is None, "comment on discarded WD was digested"


# ============================================ 5. scheduler registration
class TestSchedulerRegistration:
    def test_job_registered_in_module(self):
        src = Path("/app/backend/utils/scheduler.py").read_text()
        assert 'id="legal_mention_digest"' in src
        assert "hours=24" in src
        assert "legal_mention_digest every 24h" in src

    def test_scheduler_started_log_mentions_job(self):
        found = False
        for p in Path("/var/log/supervisor").glob("backend*.log"):
            try:
                txt = p.read_text(errors="ignore")
            except Exception:
                continue
            for line in txt.splitlines():
                if "scheduler started" in line and "legal_mention_digest" in line:
                    found = True
        assert found, "no 'scheduler started ... legal_mention_digest' line in backend logs"
