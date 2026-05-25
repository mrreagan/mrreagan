"""Iter 22 — Phase 6C.2 (Ombudsman queue) + 6C.3 (Disputes) backend tests.

Covers:
- POST /api/disputes (validations: self-dispute, missing respondent, bad txn/thread, body length)
- GET /api/me/disputes (role filter all|filed|against)
- GET /api/me/disputes/{id} (403 for non-participant)
- GET /api/admin/disputes (admin OR is_ombudsman; status + assigned_to filters)
- POST /api/admin/disputes/{id}/assign (rejects non-ombudsman target)
- POST /api/admin/disputes/{id}/status (rejects terminal statuses)
- POST /api/admin/disputes/{id}/resolve (sets dismissed or resolved; financial_credit_usd persists; rejects double-resolve)
- Audit log entries (events array)
- GET /api/admin/ombudsman/queue (counts + flagged threads from iter21)
- GET /api/admin/ombudsman/users (list)
- Iter 21 DM regression (smoke)
"""
import os
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
DEMO = {"email": "demo@birthright.org", "password": "birthright2026"}
ADMIN = {"email": "admin@birthright.org", "password": "birthright2026"}
ELENA = {"email": "elena@birthright.org", "password": "birthright2026"}
MARCUS = {"email": "marcus@birthright.org", "password": "birthright2026"}
ELENA_ID = "dc79aee7-2043-433f-a2c2-f4cdc7339c29"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ---------- helpers ----------

def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    return s, r.json()["user"]


@pytest.fixture(scope="module", autouse=True)
def _reset_disputes_state():
    """Wipe disputes and mark elena as ombudsman so we can test assign + ombudsman-only access."""
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    db.disputes.delete_many({})
    # Mark Elena as ombudsman (non-admin). Admin is already is_ombudsman=true per problem statement.
    db.users.update_one({"email": ELENA["email"]}, {"$set": {"is_ombudsman": True}})
    yield
    # Cleanup: leave admin alone, unset Elena flag so we don't pollute other tests
    db.users.update_one({"email": ELENA["email"]}, {"$set": {"is_ombudsman": False}})
    db.disputes.delete_many({})
    cli.close()


@pytest.fixture(scope="module")
def demo_client():
    return _login(DEMO)


@pytest.fixture(scope="module")
def admin_client():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def elena_client():
    return _login(ELENA)


@pytest.fixture(scope="module")
def marcus_client():
    return _login(MARCUS)


# ---------- 1. file dispute validations ----------

class TestFileDispute:
    def test_file_dispute_success(self, demo_client):
        s, _ = demo_client
        payload = {
            "against_user_id": ELENA_ID,
            "category": "conduct",
            "title": "TEST_Dispute basic flow",
            "description": "This is a long-enough description to satisfy 20-char min requirement.",
        }
        r = s.post(f"{BASE_URL}/api/disputes", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "open"
        assert d["category"] == "conduct"
        assert d["against_user_id"] == ELENA_ID
        assert d["filed_by_user"]["email"] == DEMO["email"]
        assert d["against_user"]["id"] == ELENA_ID
        assert isinstance(d["events"], list) and d["events"][0]["type"] == "filed"
        pytest.dispute_id = d["id"]  # type: ignore[attr-defined]

    def test_reject_self_dispute(self, demo_client):
        s, user = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": user["id"],
            "category": "conduct",
            "title": "TEST_Self",
            "description": "Attempting to file against self should be rejected.",
        }, timeout=15)
        assert r.status_code == 400
        assert "yourself" in r.json()["detail"].lower()

    def test_reject_missing_respondent(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": "non-existent-user-id-zzzz",
            "category": "other",
            "title": "TEST_Missing respondent",
            "description": "Should 404 when respondent id does not exist anywhere in users.",
        }, timeout=15)
        assert r.status_code == 404

    def test_reject_bad_transaction(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": ELENA_ID,
            "category": "payment",
            "title": "TEST_Bad txn",
            "description": "Linking to a transaction that does not belong to me should fail.",
            "transaction_id": "txn-does-not-exist",
        }, timeout=15)
        assert r.status_code == 404

    def test_reject_bad_thread(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": ELENA_ID,
            "category": "conduct",
            "title": "TEST_Bad thread",
            "description": "Linking a thread I'm not a participant of should fail with 404.",
            "thread_id": "thread-does-not-exist",
        }, timeout=15)
        assert r.status_code == 404

    def test_validation_title_too_short(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": ELENA_ID,
            "category": "conduct",
            "title": "abc",  # < 5
            "description": "Long enough description placed here to satisfy 20-char min.",
        }, timeout=15)
        assert r.status_code == 422

    def test_validation_description_too_short(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": ELENA_ID,
            "category": "conduct",
            "title": "TEST_short desc",
            "description": "short",
        }, timeout=15)
        assert r.status_code == 422


# ---------- 2. my disputes (filer-side) ----------

class TestMyDisputes:
    def test_my_disputes_role_all(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/me/disputes?role=all", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert any(d["id"] == pytest.dispute_id for d in rows)

    def test_my_disputes_role_filed(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/me/disputes?role=filed", timeout=15)
        assert r.status_code == 200
        assert all(d["filed_by"] == demo_client[1]["id"] for d in r.json())

    def test_my_disputes_role_against(self, elena_client):
        s, _ = elena_client
        r = s.get(f"{BASE_URL}/api/me/disputes?role=against", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert any(d["id"] == pytest.dispute_id for d in rows)

    def test_my_dispute_detail_as_filer(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/me/disputes/{pytest.dispute_id}", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == pytest.dispute_id

    def test_my_dispute_detail_as_respondent(self, elena_client):
        s, _ = elena_client
        r = s.get(f"{BASE_URL}/api/me/disputes/{pytest.dispute_id}", timeout=15)
        assert r.status_code == 200

    def test_my_dispute_detail_forbidden_for_outsider(self, marcus_client):
        s, _ = marcus_client
        r = s.get(f"{BASE_URL}/api/me/disputes/{pytest.dispute_id}", timeout=15)
        assert r.status_code == 403


# ---------- 3. admin / ombudsman listing ----------

class TestAdminList:
    def test_admin_list_all(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/disputes", timeout=15)
        assert r.status_code == 200
        assert any(d["id"] == pytest.dispute_id for d in r.json())

    def test_admin_list_status_filter(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/disputes?status=open", timeout=15)
        assert r.status_code == 200
        assert all(d["status"] == "open" for d in r.json())

    def test_admin_list_unassigned(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/disputes?assigned_to=unassigned", timeout=15)
        assert r.status_code == 200
        assert all(d.get("assigned_ombudsman_id") in (None,) for d in r.json())

    def test_non_admin_non_ombuds_forbidden(self, marcus_client):
        s, _ = marcus_client
        r = s.get(f"{BASE_URL}/api/admin/disputes", timeout=15)
        assert r.status_code == 403

    def test_ombudsman_can_list(self, elena_client):
        s, _ = elena_client
        r = s.get(f"{BASE_URL}/api/admin/disputes", timeout=15)
        assert r.status_code == 200


# ---------- 4. assign ----------

class TestAssign:
    def test_assign_rejects_non_ombudsman(self, admin_client, marcus_client):
        s, _ = admin_client
        _, marcus_user = marcus_client
        r = s.post(
            f"{BASE_URL}/api/admin/disputes/{pytest.dispute_id}/assign",
            json={"ombudsman_user_id": marcus_user["id"]},
            timeout=15,
        )
        assert r.status_code == 400
        assert "ombudsman" in r.json()["detail"].lower()

    def test_assign_to_elena(self, admin_client, elena_client):
        s, _ = admin_client
        _, elena_user = elena_client
        r = s.post(
            f"{BASE_URL}/api/admin/disputes/{pytest.dispute_id}/assign",
            json={"ombudsman_user_id": elena_user["id"]},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["assigned_ombudsman_id"] == elena_user["id"]
        assert any(e["type"] == "assigned" for e in d["events"])


# ---------- 5. status update ----------

class TestStatusUpdate:
    def test_status_to_under_review(self, elena_client):
        s, _ = elena_client
        r = s.post(
            f"{BASE_URL}/api/admin/disputes/{pytest.dispute_id}/status",
            json={"status": "under_review", "note": "Reviewing now."},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "under_review"
        assert any(e["type"] == "status_change" for e in d["events"])

    def test_status_rejects_terminal(self, elena_client):
        s, _ = elena_client
        r = s.post(
            f"{BASE_URL}/api/admin/disputes/{pytest.dispute_id}/status",
            json={"status": "resolved", "note": "Try terminal"},
            timeout=15,
        )
        assert r.status_code == 400
        assert "resolve" in r.json()["detail"].lower()

    def test_status_note_too_short(self, elena_client):
        s, _ = elena_client
        r = s.post(
            f"{BASE_URL}/api/admin/disputes/{pytest.dispute_id}/status",
            json={"status": "under_review", "note": "ab"},  # <3
            timeout=15,
        )
        assert r.status_code == 422


# ---------- 6. resolve ----------

class TestResolve:
    def test_resolve_with_credit(self, elena_client):
        s, _ = elena_client
        r = s.post(
            f"{BASE_URL}/api/admin/disputes/{pytest.dispute_id}/resolve",
            json={
                "outcome": "partial",
                "resolution_note": "Partial credit issued after review.",
                "financial_credit_usd": 25.50,
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "resolved"
        assert d["resolution"]["outcome"] == "partial"
        assert d["resolution"]["financial_credit_usd"] == 25.50
        assert d["resolution"]["resolved_by"]
        assert any(e["type"] == "resolved" for e in d["events"])

    def test_resolve_rejects_already_terminal(self, elena_client):
        s, _ = elena_client
        r = s.post(
            f"{BASE_URL}/api/admin/disputes/{pytest.dispute_id}/resolve",
            json={"outcome": "dismissed", "resolution_note": "Second attempt should fail."},
            timeout=15,
        )
        assert r.status_code == 400

    def test_resolve_dismissed_path(self, demo_client, admin_client, elena_client):
        # Create a fresh dispute and dismiss it
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": ELENA_ID,
            "category": "other",
            "title": "TEST_Dismiss flow",
            "description": "This dispute will be dismissed to test the dismissed status path.",
        }, timeout=15)
        assert r.status_code == 200
        new_id = r.json()["id"]

        es, _ = elena_client
        r2 = es.post(
            f"{BASE_URL}/api/admin/disputes/{new_id}/resolve",
            json={"outcome": "dismissed", "resolution_note": "No merit found upon review."},
            timeout=15,
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "dismissed"

    def test_resolve_note_too_short(self, demo_client, elena_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": ELENA_ID,
            "category": "conduct",
            "title": "TEST_Short note",
            "description": "Dispute to test short resolution note rejection path here.",
        }, timeout=15)
        new_id = r.json()["id"]
        es, _ = elena_client
        r2 = es.post(
            f"{BASE_URL}/api/admin/disputes/{new_id}/resolve",
            json={"outcome": "upheld", "resolution_note": "tooShort"},
            timeout=15,
        )
        assert r2.status_code == 422

    def test_resolve_negative_credit_rejected(self, demo_client, elena_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": ELENA_ID,
            "category": "payment",
            "title": "TEST_Negative credit",
            "description": "Dispute used to verify ge=0 validation on financial_credit_usd field.",
        }, timeout=15)
        new_id = r.json()["id"]
        es, _ = elena_client
        r2 = es.post(
            f"{BASE_URL}/api/admin/disputes/{new_id}/resolve",
            json={"outcome": "upheld", "resolution_note": "Long enough note here.",
                  "financial_credit_usd": -5},
            timeout=15,
        )
        assert r2.status_code == 422


# ---------- 7. ombudsman queue ----------

class TestOmbudsmanQueue:
    def test_queue_as_admin(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/ombudsman/queue", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "disputes" in body and "flagged_threads" in body and "counts" in body
        assert "open_disputes" in body["counts"]
        assert "under_review_disputes" in body["counts"]
        assert "flagged_threads" in body["counts"]
        # Counts must be ints
        for k, v in body["counts"].items():
            assert isinstance(v, int)

    def test_queue_as_ombudsman(self, elena_client):
        s, _ = elena_client
        r = s.get(f"{BASE_URL}/api/admin/ombudsman/queue", timeout=15)
        assert r.status_code == 200

    def test_queue_forbidden_to_regular_user(self, marcus_client):
        s, _ = marcus_client
        r = s.get(f"{BASE_URL}/api/admin/ombudsman/queue", timeout=15)
        assert r.status_code == 403

    def test_ombudsman_users_list(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/ombudsman/users", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert any(u["email"] == ELENA["email"] for u in rows)
        # Marcus should NOT appear (is_ombudsman=false)
        assert not any(u["email"] == MARCUS["email"] for u in rows)


# ---------- 8. iter21 regression smoke ----------

class TestIter21Regression:
    def test_dm_preferences_get(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/me/dm/preferences", timeout=15)
        assert r.status_code == 200

    def test_admin_dm_threads_list(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/admin/dm/threads", timeout=15)
        assert r.status_code == 200
