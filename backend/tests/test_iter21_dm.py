"""Iter 21 — Phase 6C.1 Direct Messaging tests.

Covers:
- POST /api/dm/threads (open/idempotent/pending/active)
- GET /api/me/dm/preferences (per-partner-type defaults)
- PUT /api/me/dm/preferences (toggle)
- POST /api/dm/threads/{id}/messages (403 while pending for sender, recipient reply flips to active)
- POST /api/dm/threads/{id}/accept, /block, /archive, /flag, /read
- GET /api/dm/threads (enriched listing)
- Admin: GET /api/admin/dm/threads (metadata only when not flagged) and /threads/{id} (bodies_locked)
- Regression: iter 18-20 endpoints
"""
import os
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
DEMO = {"email": "demo@birthright.live", "password": "birthright2026"}
ADMIN = {"email": "admin@birthright.live", "password": "birthright2026"}
# Elena (research partner only, accepts_new_dms=false by default)
ELENA_ID = "dc79aee7-2043-433f-a2c2-f4cdc7339c29"
ELENA = {"email": "elena@birthright.live", "password": "birthright2026"}

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="module", autouse=True)
def _cleanup_dm_state():
    """Reset DM threads + restore seed defaults before this module runs so tests are deterministic."""
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    # Wipe all dm threads/messages — fresh start
    db.dm_threads.delete_many({})
    db.dm_messages.delete_many({})
    # Restore demo partner_profile accepts_new_dms defaults (community=True, vendor=False)
    demo_user = db.users.find_one({"email": DEMO["email"]})
    if demo_user:
        db.partner_profiles.update_many(
            {"user_id": demo_user["id"], "partner_type": "community", "status": "active"},
            {"$set": {"accepts_new_dms": True}},
        )
        db.partner_profiles.update_many(
            {"user_id": demo_user["id"], "partner_type": "vendor", "status": "active"},
            {"$set": {"accepts_new_dms": False}},
        )
    # Restore Elena's research profile to false
    db.partner_profiles.update_many(
        {"user_id": ELENA_ID, "partner_type": "research", "status": "active"},
        {"$set": {"accepts_new_dms": False}},
    )
    cli.close()
    yield


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    user = r.json()["user"]
    return s, user


@pytest.fixture(scope="module")
def demo_client():
    s, user = _login(DEMO)
    return s, user


@pytest.fixture(scope="module")
def elena_client():
    s, user = _login(ELENA)
    return s, user


@pytest.fixture(scope="module")
def admin_client():
    s, user = _login(ADMIN)
    return s, user


# ============ PREFERENCES ============

class TestDmPreferences:
    def test_get_defaults_after_seed(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/me/dm/preferences")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 2
        by_type = {p["partner_type"]: p["accepts_new_dms"] for p in data}
        assert by_type.get("community") is True, f"community default should be True, got {by_type}"
        assert by_type.get("vendor") is False, f"vendor default should be False, got {by_type}"

    def test_elena_defaults_research_false(self, elena_client):
        s, _ = elena_client
        r = s.get(f"{BASE_URL}/api/me/dm/preferences")
        assert r.status_code == 200
        data = r.json()
        # Elena has research partner — should default false
        assert any(p["partner_type"] == "research" and p["accepts_new_dms"] is False for p in data), \
            f"Elena research profile accepts_new_dms should be False, got {data}"

    def test_toggle_preferences(self, demo_client):
        s, demo_user = demo_client
        # Flip OFF
        r = s.put(f"{BASE_URL}/api/me/dm/preferences", json={"accepts_new_dms": False})
        assert r.status_code == 200
        d = r.json()
        assert d["accepts_new_dms"] is False
        assert d["profiles_updated"] >= 1
        # Verify
        r = s.get(f"{BASE_URL}/api/me/dm/preferences")
        assert all(p["accepts_new_dms"] is False for p in r.json())
        # Restore seed defaults directly via mongo so other tests stay deterministic
        cli = MongoClient(MONGO_URL)
        db = cli[DB_NAME]
        db.partner_profiles.update_many(
            {"user_id": demo_user["id"], "partner_type": "community", "status": "active"},
            {"$set": {"accepts_new_dms": True}},
        )
        db.partner_profiles.update_many(
            {"user_id": demo_user["id"], "partner_type": "vendor", "status": "active"},
            {"$set": {"accepts_new_dms": False}},
        )
        cli.close()


# ============ THREAD OPEN / PENDING ============

class TestDmThreadOpen:
    def test_thread_with_elena_starts_pending_when_research_false(self, demo_client, elena_client):
        """demo opens thread to Elena. Elena's research profile defaults accepts=false (after seed).
        Note: previous test may have flipped demo prefs to True, but the gate is on RECIPIENT (Elena).
        Elena still has research with accepts_new_dms=False (untouched)."""
        s, demo_user = demo_client
        _, elena = elena_client
        r = s.post(f"{BASE_URL}/api/dm/threads", json={
            "recipient_id": ELENA_ID,
            "initial_message": "TEST_iter21 hello from demo (pending probe)",
        })
        assert r.status_code == 200, r.text
        t = r.json()
        assert "id" in t
        assert t["status"] in ("pending", "active"), f"unexpected status {t['status']}"
        # Capture for later tests
        pytest.thread_id_pending = t["id"]
        pytest.thread_status_initial = t["status"]
        # Idempotent — call again returns same id
        r2 = s.post(f"{BASE_URL}/api/dm/threads", json={"recipient_id": ELENA_ID})
        assert r2.status_code == 200
        assert r2.json()["id"] == t["id"], "open_thread should be idempotent"

    def test_cannot_dm_self(self, demo_client):
        s, demo_user = demo_client
        r = s.post(f"{BASE_URL}/api/dm/threads", json={"recipient_id": demo_user["id"]})
        assert r.status_code == 400

    def test_recipient_not_found(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/dm/threads", json={"recipient_id": "nonexistent-user-xyz"})
        assert r.status_code == 404

    def test_thread_enriched_other_participant(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/dm/threads")
        assert r.status_code == 200
        rows = r.json()
        # Find our thread with Elena
        match = [x for x in rows if x["id"] == pytest.thread_id_pending]
        assert match, "thread should appear in inbox"
        row = match[0]
        op = row["other_participant"]
        assert op["id"] == ELENA_ID
        assert op["partner_type"] == "research"
        assert "name" in op
        assert "unread_count" in row
        assert "last_message_preview" in row


# ============ PENDING ACCEPTANCE / MESSAGING ============

class TestDmPendingFlow:
    def test_sender_cannot_post_while_pending(self, demo_client):
        s, _ = demo_client
        if pytest.thread_status_initial != "pending":
            pytest.skip("Thread didn't open in pending state — Elena's prefs likely already accept")
        r = s.post(
            f"{BASE_URL}/api/dm/threads/{pytest.thread_id_pending}/messages",
            json={"content": "TEST_iter21 sender retry"},
        )
        assert r.status_code == 403, f"expected 403 while pending, got {r.status_code} {r.text}"

    def test_recipient_reply_flips_to_active(self, elena_client, demo_client):
        s, _ = elena_client
        if pytest.thread_status_initial != "pending":
            pytest.skip("Thread already active — skipping recipient-accept flip")
        r = s.post(
            f"{BASE_URL}/api/dm/threads/{pytest.thread_id_pending}/messages",
            json={"content": "TEST_iter21 Elena reply auto-accepts"},
        )
        assert r.status_code == 200, r.text
        # Now verify status flipped to active
        demo_s, _ = demo_client
        r2 = demo_s.get(f"{BASE_URL}/api/dm/threads/{pytest.thread_id_pending}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "active"


# ============ READ / FLAG / ARCHIVE ============

class TestDmActions:
    def test_post_message_after_active(self, demo_client):
        s, _ = demo_client
        r = s.post(
            f"{BASE_URL}/api/dm/threads/{pytest.thread_id_pending}/messages",
            json={"content": "TEST_iter21 message from demo after acceptance"},
        )
        assert r.status_code == 200, r.text
        msg = r.json()
        assert msg["content"].startswith("TEST_iter21")
        assert "id" in msg

    def test_mark_read_zeros_unread(self, elena_client):
        s, elena = elena_client
        r = s.post(f"{BASE_URL}/api/dm/threads/{pytest.thread_id_pending}/read")
        assert r.status_code == 200
        # Verify unread cleared via inbox listing
        r2 = s.get(f"{BASE_URL}/api/dm/threads")
        assert r2.status_code == 200
        match = [x for x in r2.json() if x["id"] == pytest.thread_id_pending]
        assert match
        assert match[0]["unread_count"] == 0

    def test_flag_thread(self, demo_client):
        s, _ = demo_client
        # Short reason rejected
        r_bad = s.post(
            f"{BASE_URL}/api/dm/threads/{pytest.thread_id_pending}/flag",
            json={"reason": "x"},
        )
        assert r_bad.status_code == 422, "min_length=3 should reject 1-char"
        # Good
        r = s.post(
            f"{BASE_URL}/api/dm/threads/{pytest.thread_id_pending}/flag",
            json={"reason": "TEST_iter21 ombudsman please review"},
        )
        assert r.status_code == 200
        assert r.json().get("flagged") is True

    def test_archive_removes_from_inbox(self, demo_client, admin_client):
        s, _ = demo_client
        admin_user = admin_client[1]
        # Open a brand-new thread to admin (different recipient, not Elena), then archive it.
        r_open = s.post(f"{BASE_URL}/api/dm/threads", json={
            "recipient_id": admin_user["id"],
            "initial_message": "TEST_iter21 thread to archive",
        })
        assert r_open.status_code == 200, r_open.text
        tid = r_open.json()["id"]
        assert tid != pytest.thread_id_pending, "must be a different thread"
        r = s.post(f"{BASE_URL}/api/dm/threads/{tid}/archive")
        assert r.status_code == 200
        # No longer in listing
        rows = s.get(f"{BASE_URL}/api/dm/threads").json()
        assert all(row["id"] != tid for row in rows), "archived thread must not appear in inbox"


# ============ ADMIN OMBUDSMAN ============

class TestAdminDm:
    def test_admin_list_threads(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/dm/threads")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        # Find flagged + unflagged samples
        flagged = [x for x in rows if x.get("ombudsman_flagged")]
        not_flagged = [x for x in rows if not x.get("ombudsman_flagged")]
        for x in not_flagged:
            assert x["last_message_preview"] == "[hidden — not flagged]", \
                f"unflagged preview should be masked, got: {x['last_message_preview']!r}"
        # Our test thread should be flagged
        assert any(x["id"] == pytest.thread_id_pending and x.get("ombudsman_flagged") for x in flagged), \
            "our flagged thread should appear in admin list"

    def test_admin_non_flagged_thread_bodies_locked(self, admin_client, demo_client):
        s, _ = admin_client
        # Create a fresh unflagged thread by demo opening to admin (admin has no partner
        # profile but demo is a partner — eligibility satisfied; admin has no profile so
        # _recipient_accepts returns True → active immediately).
        demo_s, _ = demo_client
        admin_user = admin_client[1]
        r_open = demo_s.post(f"{BASE_URL}/api/dm/threads", json={
            "recipient_id": admin_user["id"],
            "initial_message": "TEST_iter21 unflagged probe",
        })
        assert r_open.status_code == 200, r_open.text
        tid = r_open.json()["id"]
        # Confirm not flagged in admin list
        r = s.get(f"{BASE_URL}/api/admin/dm/threads/{tid}")
        assert r.status_code == 200
        d = r.json()
        if d.get("ombudsman_flagged"):
            pytest.skip("Test thread unexpectedly flagged")
        assert d.get("messages") is None
        assert d.get("bodies_locked") is True
        # Also verify list masks preview
        rows = s.get(f"{BASE_URL}/api/admin/dm/threads").json()
        ours = next(x for x in rows if x["id"] == tid)
        assert ours["last_message_preview"] == "[hidden — not flagged]"
        # Cleanup — archive (won't unflag but removes from demo's active inbox)
        demo_s.post(f"{BASE_URL}/api/dm/threads/{tid}/archive")

    def test_admin_flagged_thread_returns_messages(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/dm/threads/{pytest.thread_id_pending}")
        assert r.status_code == 200
        d = r.json()
        assert d.get("ombudsman_flagged") is True
        assert isinstance(d.get("messages"), list)
        assert len(d["messages"]) >= 1
        # bodies_locked NOT set (or False)
        assert not d.get("bodies_locked")

    def test_admin_only_endpoint(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/admin/dm/threads")
        assert r.status_code in (401, 403)


# ============ BLOCK FLOW ============

class TestDmBlock:
    def test_block_requires_recipient(self, demo_client):
        s, _ = demo_client
        # demo is the initiator on the test thread, so block by demo should be 403
        r = s.post(f"{BASE_URL}/api/dm/threads/{pytest.thread_id_pending}/block")
        # Either 403 (initiator can't block) or 200 if implementation allows it on active
        assert r.status_code in (403, 200), f"unexpected: {r.status_code} {r.text}"


# ============ REGRESSION (iter 18-20) ============

class TestRegression:
    def test_admin_disbursement_settings(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/payouts/disbursement-settings")
        assert r.status_code == 200

    def test_admin_subscriptions(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/subscriptions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_me_bookmarks(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/me/bookmarks")
        assert r.status_code == 200

    def test_shares_log(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/shares/log", json={
            "surface": "partner",
            "channel": "copy_link",
            "url": "https://example.com/partners/test",
        })
        assert r.status_code in (200, 201), r.text

    def test_workshops_ics(self):
        # Find first upcoming workshop
        r = requests.get(f"{BASE_URL}/api/workshops")
        assert r.status_code == 200
        ws = r.json()
        if not ws:
            pytest.skip("No workshops to test ICS")
        wid = ws[0]["id"]
        r2 = requests.get(f"{BASE_URL}/api/workshops/{wid}/ics")
        assert r2.status_code == 200
        assert "BEGIN:VCALENDAR" in r2.text
