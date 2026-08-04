"""Iteration 4 backend tests: Workshop CRUD extras (duplicate/cancel/revenue),
Workshop Photos (upload/moderate/list/delete), email queueing for cancellation.
"""
import io
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://birthright-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
_mongo = MongoClient(MONGO_URL)
_db = _mongo[DB_NAME]

ADMIN = {"email": "admin@birthright.live", "password": "birthright2026"}
FAC = {"email": "elena@birthright.live", "password": "birthright2026"}
FAC2 = {"email": "marcus@birthright.live", "password": "birthright2026"}
DEMO = {"email": "demo@birthright.live", "password": "birthright2026"}


def _login(s, creds):
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _client(creds):
    """Return a dedicated session pre-logged-in as this user (cookie set)."""
    s = requests.Session()
    data = _login(s, creds)
    data["session"] = s
    return data


def H(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def s():
    # Anonymous session (no cookie). Used for cross-user header-based tests where we
    # explicitly provide Authorization headers and want NO leftover cookie.
    return requests.Session()


@pytest.fixture(scope="module")
def admin():
    return _client(ADMIN)


@pytest.fixture(scope="module")
def fac():
    return _client(FAC)


@pytest.fixture(scope="module")
def fac2():
    return _client(FAC2)


@pytest.fixture(scope="module")
def demo():
    return _client(DEMO)


def _make_image_bytes(size=(800, 600), fmt="JPEG", color=(120, 80, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt, quality=85)
    return buf.getvalue()


def _new_workshop(admin_user, slug_prefix="test-iter4", facilitator_id=None, status="upcoming"):
    """Create a workshop via API for testing. admin_user is the dict returned by _client()."""
    slug = f"{slug_prefix}-{uuid.uuid4().hex[:8]}"
    payload = {
        "title": "TEST Iter4 Workshop",
        "slug": slug,
        "short_description": "test short",
        "full_description": "test full description",
        "facilitator_id": facilitator_id or "",
        "location_name": "Online",
        "location_address": "n/a",
        "early_bird_price": 100,
        "regular_price": 150,
        "early_bird_until": "2026-03-01T00:00:00Z",
        "start_date": "2026-04-01T17:00:00Z",
        "end_date": "2026-04-01T19:00:00Z",
        "capacity": 25,
        "status": status,
    }
    r = admin_user["session"].post(f"{API}/workshops", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


# --------------- Create workshop: check_in_code generation + facilitator auto-assign ---------------
class TestCreateWorkshop:
    def test_admin_create_omits_check_in_code_gets_generated(self, s, admin):
        w = _new_workshop(admin)
        try:
            # Response should include check_in_code (creator/admin gets full doc back)
            assert "check_in_code" in w
            code = w["check_in_code"]
            assert isinstance(code, str) and len(code) == 6
        finally:
            _db.workshops.delete_one({"id": w["id"]})

    def test_facilitator_create_self_assigns(self, s, fac, admin):
        # Facilitator tries to assign someone else; server must override to themselves.
        slug = f"test-iter4-fac-{uuid.uuid4().hex[:8]}"
        payload = {
            "title": "TEST fac assign",
            "slug": slug,
            "short_description": "x",
            "full_description": "x",
            "facilitator_id": admin["user"]["id"],
            "location_name": "Online",
            "location_address": "n/a",
            "early_bird_price": 50, "regular_price": 75,
            "early_bird_until": "2026-03-01T00:00:00Z",
            "start_date": "2026-04-01T17:00:00Z",
            "end_date": "2026-04-01T19:00:00Z",
            "capacity": 10,
            "status": "draft",
        }
        r = fac["session"].post(f"{API}/workshops", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        w = r.json()
        try:
            assert w["facilitator_id"] == fac["user"]["id"]
        finally:
            _db.workshops.delete_one({"id": w["id"]})


# --------------- Duplicate ---------------
class TestDuplicate:
    def test_admin_duplicate(self, s, admin, fac):
        src = _new_workshop(admin, facilitator_id=fac["user"]["id"])
        try:
            r = admin["session"].post(f"{API}/workshops/{src['id']}/duplicate", timeout=20)
            assert r.status_code == 200, r.text
            dup = r.json()
            try:
                assert dup["slug"].endswith("-copy") or "-copy-" in dup["slug"]
                assert dup["status"] == "draft"
                assert dup["check_in_code"] != src["check_in_code"]
                assert len(dup["check_in_code"]) == 6
                # dates shifted ~30 days; just ensure they're different
                assert dup["start_date"] != src["start_date"]
                assert dup["id"] != src["id"]
            finally:
                _db.workshops.delete_one({"id": dup["id"]})
        finally:
            _db.workshops.delete_one({"id": src["id"]})

    def test_facilitator_duplicate_someone_elses_403(self, s, admin, fac, fac2):
        # workshop owned by fac
        src = _new_workshop(admin, facilitator_id=fac["user"]["id"])
        try:
            r = fac2["session"].post(f"{API}/workshops/{src['id']}/duplicate", timeout=20)
            assert r.status_code == 403, r.text
        finally:
            _db.workshops.delete_one({"id": src["id"]})


# --------------- Cancel ---------------
class TestCancel:
    def test_admin_cancel_with_seed_demo_registrations(self, s, admin, fac):
        # Create workshop + 2 paid seed_demo registrations
        w = _new_workshop(admin, facilitator_id=fac["user"]["id"])
        wid = w["id"]
        # create two participant users + registrations
        user_emails = []
        user_ids = []
        for i in range(2):
            email = f"test_cancel_{uuid.uuid4().hex[:8]}@birthright-test.com"
            reg = requests.Session().post(f"{API}/auth/register", json={
                "email": email, "password": "P@ss12345",
                "first_name": f"Test{i}", "last_name": "User"
            }, timeout=30).json()
            user_emails.append(email)
            user_ids.append(reg["user"]["id"])
            _db.registrations.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": reg["user"]["id"],
                "workshop_id": wid,
                "payment_status": "paid",
                "payment_session_id": "seed_demo",
                "amount_paid": 100.0,
                "pricing_tier": "early_bird",
                "created_at": "2026-01-01T00:00:00Z",
            })
        # baseline: count outbound emails
        before_email_count = _db.outbound_emails.count_documents(
            {"template": "workshop_cancelled", "metadata.workshop_id": wid}
        )
        try:
            r = admin["session"].post(f"{API}/workshops/{wid}/cancel", timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            for k in ("refunds_attempted", "refunds_succeeded", "refunds_pending",
                      "refunds_failed", "results"):
                assert k in data
            assert data["refunds_attempted"] == 2
            # workshop now cancelled
            wdoc = _db.workshops.find_one({"id": wid})
            assert wdoc["status"] == "cancelled"
            # each reg cancelled + refund metadata; seed_demo → status='manual'
            for uid in user_ids:
                regdoc = _db.registrations.find_one({"workshop_id": wid, "user_id": uid})
                assert regdoc["payment_status"] == "cancelled"
                assert regdoc["refund_status"] == "manual"
                assert regdoc["refund_amount"] == 100.0
            # email queued
            after_email_count = _db.outbound_emails.count_documents(
                {"template": "workshop_cancelled", "metadata.workshop_id": wid}
            )
            assert after_email_count - before_email_count == 2

            # Cancelling again → 400
            r2 = admin["session"].post(f"{API}/workshops/{wid}/cancel", timeout=15)
            assert r2.status_code == 400
        finally:
            _db.registrations.delete_many({"workshop_id": wid})
            _db.workshops.delete_one({"id": wid})
            _db.outbound_emails.delete_many({"metadata.workshop_id": wid})
            for e in user_emails:
                _db.users.delete_one({"email": e})


# --------------- Revenue ---------------
class TestRevenue:
    def test_revenue_admin_ok(self, s, admin, fac):
        w = _new_workshop(admin, facilitator_id=fac["user"]["id"])
        try:
            r = admin["session"].get(f"{API}/workshops/{w['id']}/revenue", timeout=15)
            assert r.status_code == 200, r.text
            d = r.json()
            for k in ("paid_count", "cancelled_count", "checked_in_count",
                      "gross_revenue", "refunded", "net_revenue"):
                assert k in d
            assert d["paid_count"] == 0
            assert d["gross_revenue"] == 0
        finally:
            _db.workshops.delete_one({"id": w["id"]})

    def test_revenue_facilitator_other_403(self, s, admin, fac, fac2):
        w = _new_workshop(admin, facilitator_id=fac["user"]["id"])
        try:
            r = fac2["session"].get(f"{API}/workshops/{w['id']}/revenue", timeout=15)
            assert r.status_code == 403
        finally:
            _db.workshops.delete_one({"id": w["id"]})

    def test_revenue_anonymous_unauthorized(self, s, admin, fac):
        w = _new_workshop(admin, facilitator_id=fac["user"]["id"])
        try:
            r = s.get(f"{API}/workshops/{w['id']}/revenue", timeout=15)
            assert r.status_code in (401, 403)
        finally:
            _db.workshops.delete_one({"id": w["id"]})


# --------------- Workshop Photos: upload, list, moderate, delete ---------------
class TestWorkshopPhotos:
    @pytest.fixture(scope="class")
    def setup_workshop(self, s, admin, fac, demo):
        """Create a workshop owned by fac, with demo as paid participant and a stranger user."""
        w = _new_workshop(admin, facilitator_id=fac["user"]["id"])
        wid = w["id"]
        # paid registration for demo
        paid_reg = {
            "id": str(uuid.uuid4()),
            "user_id": demo["user"]["id"],
            "workshop_id": wid,
            "payment_status": "paid",
            "payment_session_id": "seed_demo",
            "amount_paid": 100.0,
            "pricing_tier": "early_bird",
            "created_at": "2026-01-01T00:00:00Z",
        }
        _db.registrations.insert_one(paid_reg)

        # unpaid registered user (own session)
        unpaid_session = requests.Session()
        unpaid_email = f"test_unpaid_{uuid.uuid4().hex[:8]}@birthright-test.com"
        unpaid_reg_resp = unpaid_session.post(f"{API}/auth/register", json={
            "email": unpaid_email, "password": "P@ss12345",
            "first_name": "Unpaid", "last_name": "User"
        }, timeout=30).json()
        _db.registrations.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": unpaid_reg_resp["user"]["id"],
            "workshop_id": wid,
            "payment_status": "initiated",
            "payment_session_id": "seed_demo",
            "amount_paid": 0.0,
            "pricing_tier": "early_bird",
            "created_at": "2026-01-01T00:00:00Z",
        })

        # stranger user (no registration, own session)
        stranger_session = requests.Session()
        stranger_email = f"test_stranger_{uuid.uuid4().hex[:8]}@birthright-test.com"
        stranger_session.post(f"{API}/auth/register", json={
            "email": stranger_email, "password": "P@ss12345",
            "first_name": "Stranger", "last_name": "User"
        }, timeout=30)

        yield {
            "workshop": w,
            "wid": wid,
            "unpaid_session": unpaid_session,
            "unpaid_email": unpaid_email,
            "stranger_session": stranger_session,
            "stranger_email": stranger_email,
        }

        # cleanup
        _db.workshop_photos.delete_many({"workshop_id": wid})
        _db.registrations.delete_many({"workshop_id": wid})
        _db.workshops.delete_one({"id": wid})
        _db.users.delete_one({"email": unpaid_email})
        _db.users.delete_one({"email": stranger_email})

    def test_paid_participant_upload_pending(self, s, demo, setup_workshop):
        wid = setup_workshop["wid"]
        img = _make_image_bytes()
        files = {"file": ("test.jpg", img, "image/jpeg")}
        data = {"caption": "TEST_pending"}
        r = demo["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data=data, timeout=30)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["status"] == "pending"
        assert p["uploader_role"] == "participant"
        assert p["image_url"].startswith(f"/api/static/workshop_photos/{wid}/")
        assert p["thumb_url"]
        # store id for static fetch test via direct mongo lookup later

    def test_facilitator_upload_approved(self, s, fac, setup_workshop):
        wid = setup_workshop["wid"]
        files = {"file": ("test.jpg", _make_image_bytes(), "image/jpeg")}
        r = fac["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "TEST_approved"}, timeout=30)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["status"] == "approved"
        assert p["uploader_role"] == "facilitator"

    def test_admin_upload_approved(self, s, admin, setup_workshop):
        wid = setup_workshop["wid"]
        files = {"file": ("test.jpg", _make_image_bytes(), "image/jpeg")}
        r = admin["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "TEST_admin"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    def test_unpaid_registered_user_blocked(self, s, setup_workshop):
        wid = setup_workshop["wid"]
        files = {"file": ("test.jpg", _make_image_bytes(), "image/jpeg")}
        r = setup_workshop["unpaid_session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "x"}, timeout=30)
        assert r.status_code == 403

    def test_stranger_blocked(self, s, setup_workshop):
        wid = setup_workshop["wid"]
        files = {"file": ("test.jpg", _make_image_bytes(), "image/jpeg")}
        r = setup_workshop["stranger_session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "x"}, timeout=30)
        assert r.status_code == 403

    def test_oversize_413(self, s, fac, setup_workshop):
        wid = setup_workshop["wid"]
        # raw bytes > 8MB regardless of content
        big = b"\xff\xd8\xff\xe0" + (b"A" * (9 * 1024 * 1024))
        files = {"file": ("big.jpg", big, "image/jpeg")}
        r = fac["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "x"}, timeout=30)
        assert r.status_code == 413

    def test_non_image_400(self, s, fac, setup_workshop):
        wid = setup_workshop["wid"]
        files = {"file": ("foo.txt", b"hello", "text/plain")}
        r = fac["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "x"}, timeout=30)
        assert r.status_code == 400

    def test_list_anonymous_returns_only_approved(self, s, setup_workshop):
        wid = setup_workshop["wid"]
        r = s.get(f"{API}/workshop-photos/{wid}", timeout=15)
        assert r.status_code == 200
        photos = r.json()
        assert all(p["status"] == "approved" for p in photos)
        assert len(photos) >= 2  # facilitator + admin uploads from prior tests

    def test_cross_workshop_pending_admin(self, s, admin):
        r = admin["session"].get(f"{API}/workshop-photos", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_cross_workshop_pending_facilitator_only_theirs(self, s, fac, setup_workshop):
        r = fac["session"].get(f"{API}/workshop-photos", timeout=15)
        assert r.status_code == 200
        # All returned photos should belong to fac's workshops; our test wid is owned by fac
        # so any pending photo for setup_workshop wid should appear here
        photos = r.json()
        if photos:
            assert all(p["status"] == "pending" for p in photos)

    def test_cross_workshop_pending_participant_403(self, s, demo):
        r = demo["session"].get(f"{API}/workshop-photos", timeout=15)
        assert r.status_code == 403

    def test_approve_and_reject_flow(self, s, fac, demo, setup_workshop):
        wid = setup_workshop["wid"]
        # find a pending photo (one uploaded by demo)
        p = _db.workshop_photos.find_one({"workshop_id": wid, "status": "pending"})
        assert p, "no pending photo to moderate"
        # approve
        r = fac["session"].post(f"{API}/workshop-photos/{p['id']}/approve", timeout=15)
        assert r.status_code == 200
        doc = _db.workshop_photos.find_one({"id": p["id"]})
        assert doc["status"] == "approved"

        # Upload another pending one as demo, then reject
        demo_login = demo
        files = {"file": ("a.jpg", _make_image_bytes(), "image/jpeg")}
        r2 = demo_login["session"].post(f"{API}/workshop-photos/{wid}",
                    files=files, data={"caption": "to-reject"}, timeout=30)
        pid2 = r2.json()["id"]
        r3 = fac["session"].post(f"{API}/workshop-photos/{pid2}/reject",
                    json={"reason": "off-topic"}, timeout=15)
        assert r3.status_code == 200
        doc2 = _db.workshop_photos.find_one({"id": pid2})
        assert doc2["status"] == "rejected"
        assert doc2["rejection_reason"] == "off-topic"

    def test_stranger_cannot_moderate(self, s, setup_workshop):
        p = _db.workshop_photos.find_one({"workshop_id": setup_workshop["wid"]})
        assert p
        r = setup_workshop["stranger_session"].post(f"{API}/workshop-photos/{p['id']}/approve", timeout=15)
        # require_roles facilitator/admin → 403
        assert r.status_code == 403

    def test_uploader_can_delete_own_pending(self, s, demo, setup_workshop):
        wid = setup_workshop["wid"]
        # upload a fresh one as demo
        files = {"file": ("p.jpg", _make_image_bytes(), "image/jpeg")}
        r = demo["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "delete-me"}, timeout=30)
        pid = r.json()["id"]
        rd = demo["session"].delete(f"{API}/workshop-photos/{pid}", timeout=15)
        assert rd.status_code == 200
        assert _db.workshop_photos.find_one({"id": pid}) is None

    def test_uploader_cannot_delete_own_approved(self, s, fac, demo, setup_workshop):
        wid = setup_workshop["wid"]
        files = {"file": ("p.jpg", _make_image_bytes(), "image/jpeg")}
        r = demo["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "ok"}, timeout=30)
        pid = r.json()["id"]
        # approve it via fac
        fac["session"].post(f"{API}/workshop-photos/{pid}/approve", timeout=15)
        # demo tries to delete approved
        rd = demo["session"].delete(f"{API}/workshop-photos/{pid}", timeout=15)
        assert rd.status_code == 403

    def test_admin_can_delete_any(self, s, admin, demo, setup_workshop):
        wid = setup_workshop["wid"]
        files = {"file": ("p.jpg", _make_image_bytes(), "image/jpeg")}
        r = demo["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "ok"}, timeout=30)
        pid = r.json()["id"]
        rd = admin["session"].delete(f"{API}/workshop-photos/{pid}", timeout=15)
        assert rd.status_code == 200

    def test_static_serve_image(self, s, fac, setup_workshop):
        wid = setup_workshop["wid"]
        files = {"file": ("static.jpg", _make_image_bytes(), "image/jpeg")}
        r = fac["session"].post(f"{API}/workshop-photos/{wid}",
                   files=files, data={"caption": "static-check"}, timeout=30)
        assert r.status_code == 200
        url_path = r.json()["image_url"]  # /api/static/workshop_photos/<wid>/<file>
        rr = s.get(f"{BASE_URL}{url_path}", timeout=20)
        assert rr.status_code == 200, f"{rr.status_code}: {url_path}"
        assert "image/jpeg" in rr.headers.get("content-type", "").lower()
