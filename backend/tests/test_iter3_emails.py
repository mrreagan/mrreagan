"""Iteration 3 - Emails, password reset, registration cancel/release, image regen contract,
admin email log, scheduler. All emails should land in db.outbound_emails (dry-run)."""
import os
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://birthright-hub.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN = ("admin@birthright.org", "birthright2026")
DEMO = ("demo@birthright.org", "birthright2026")
FAC = ("elena@birthright.org", "birthright2026")


@pytest.fixture(scope="session")
def mongo():
    return MongoClient(MONGO_URL)[DB_NAME]


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="session")
def admin_session():
    return _login(*ADMIN)


@pytest.fixture(scope="session")
def demo_session():
    return _login(*DEMO)


@pytest.fixture(scope="session")
def fac_session():
    return _login(*FAC)


# --- Health & root ---
def test_health():
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# --- Contact: 2 emails queued ---
def test_contact_queues_two_emails(mongo):
    before = mongo.outbound_emails.count_documents({})
    r = requests.post(f"{BASE_URL}/api/contact", json={
        "first_name": "TEST_Contact",
        "last_name": "Tester",
        "email": "TEST_contact@example.com",
        "phone": "555-0000",
        "subject": "Iteration 3 test",
        "message": "This is a backend test message.",
        "newsletter_opt_in": False,
    })
    assert r.status_code == 200, r.text
    time.sleep(1.0)
    after = mongo.outbound_emails.count_documents({})
    assert after - before >= 2, f"expected 2+ emails queued, got {after-before}"

    admin_notify = mongo.outbound_emails.find_one(
        {"template": "contact_admin_notify", "to": "support@birthright.live"},
        sort=[("created_at", -1)],
    )
    autoreply = mongo.outbound_emails.find_one(
        {"template": "contact_autoreply", "to": "TEST_contact@example.com"},
        sort=[("created_at", -1)],
    )
    assert admin_notify, "admin_notify not queued"
    assert admin_notify["status"] == "queued_dry_run"
    assert autoreply, "autoreply not queued"
    assert autoreply["status"] == "queued_dry_run"


# --- Password reset request: existing user ---
def test_request_password_reset_existing(mongo):
    before_tokens = mongo.password_reset_tokens.count_documents({"email": "demo@birthright.org"})
    before_emails = mongo.outbound_emails.count_documents({"template": "password_reset"})
    r = requests.post(f"{BASE_URL}/api/auth/request-password-reset", json={"email": "demo@birthright.org"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    assert "reset link" in body.get("message", "").lower()
    time.sleep(0.5)
    after_tokens = mongo.password_reset_tokens.count_documents({"email": "demo@birthright.org"})
    after_emails = mongo.outbound_emails.count_documents({"template": "password_reset"})
    assert after_tokens == before_tokens + 1
    assert after_emails == before_emails + 1
    tok = mongo.password_reset_tokens.find_one(
        {"email": "demo@birthright.org"}, sort=[("created_at", -1)]
    )
    assert tok["used"] is False
    assert tok.get("expires_at")


# --- Password reset request: nonexistent user (no leak) ---
def test_request_password_reset_nonexistent(mongo):
    fake = "TEST_nobody_iter3@example.com"
    before_tokens = mongo.password_reset_tokens.count_documents({})
    before_emails = mongo.outbound_emails.count_documents({"template": "password_reset"})
    r = requests.post(f"{BASE_URL}/api/auth/request-password-reset", json={"email": fake})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "reset link" in body.get("message", "").lower()
    time.sleep(0.5)
    assert mongo.password_reset_tokens.count_documents({}) == before_tokens
    assert mongo.outbound_emails.count_documents({"template": "password_reset"}) == before_emails


# --- Reset password with valid token, then restore original ---
def test_reset_password_with_valid_token(mongo):
    # request fresh token
    requests.post(f"{BASE_URL}/api/auth/request-password-reset", json={"email": "demo@birthright.org"})
    time.sleep(0.3)
    tok_doc = mongo.password_reset_tokens.find_one(
        {"email": "demo@birthright.org", "used": False}, sort=[("created_at", -1)]
    )
    assert tok_doc, "no fresh token found"
    token = tok_doc["token"]
    new_pw = "TempTestPw_2026!"

    r = requests.post(f"{BASE_URL}/api/auth/reset-password", json={"token": token, "new_password": new_pw})
    assert r.status_code == 200, r.text

    # token should be marked used
    used = mongo.password_reset_tokens.find_one({"id": tok_doc["id"]})
    assert used["used"] is True

    # login with NEW password
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "demo@birthright.org", "password": new_pw})
    assert r.status_code == 200, "login with new password should succeed"

    # already-used token rejected
    r2 = requests.post(f"{BASE_URL}/api/auth/reset-password", json={"token": token, "new_password": "AnotherPw_2026!"})
    assert r2.status_code == 400

    # RESTORE original password using fresh token
    requests.post(f"{BASE_URL}/api/auth/request-password-reset", json={"email": "demo@birthright.org"})
    time.sleep(0.3)
    tok2 = mongo.password_reset_tokens.find_one(
        {"email": "demo@birthright.org", "used": False}, sort=[("created_at", -1)]
    )
    assert tok2
    r3 = requests.post(f"{BASE_URL}/api/auth/reset-password", json={"token": tok2["token"], "new_password": "birthright2026"})
    assert r3.status_code == 200

    # verify restore worked
    s2 = requests.Session()
    r = s2.post(f"{BASE_URL}/api/auth/login", json={"email": "demo@birthright.org", "password": "birthright2026"})
    assert r.status_code == 200, "original password should be restored"


def test_reset_password_invalidates_other_outstanding_tokens(mongo):
    # create two outstanding tokens
    requests.post(f"{BASE_URL}/api/auth/request-password-reset", json={"email": "demo@birthright.org"})
    time.sleep(0.2)
    requests.post(f"{BASE_URL}/api/auth/request-password-reset", json={"email": "demo@birthright.org"})
    time.sleep(0.2)
    tokens = list(
        mongo.password_reset_tokens.find({"email": "demo@birthright.org", "used": False}).sort("created_at", -1)
    )
    assert len(tokens) >= 2

    # use the latest, set pw back to current
    latest = tokens[0]
    r = requests.post(f"{BASE_URL}/api/auth/reset-password", json={"token": latest["token"], "new_password": "birthright2026"})
    assert r.status_code == 200

    # other(s) should be invalidated
    others_unused = mongo.password_reset_tokens.count_documents({"email": "demo@birthright.org", "used": False})
    assert others_unused == 0, "other outstanding tokens should be invalidated"


# --- Newsletter: queues welcome email + inserts subscriber ---
def test_newsletter_subscribe(mongo):
    email = f"test_newsletter_iter3_{int(time.time())}@example.com"
    before = mongo.outbound_emails.count_documents({"template": "newsletter_welcome"})
    r = requests.post(f"{BASE_URL}/api/newsletter", json={"email": email, "name": "TEST Newsletter"})
    assert r.status_code == 200
    time.sleep(0.5)
    sub = mongo.newsletter_subscribers.find_one({"email": email.lower()})
    assert sub
    after = mongo.outbound_emails.count_documents({"template": "newsletter_welcome"})
    assert after == before + 1


# --- Registration cancel by owner + waitlist promotion email ---
def test_cancel_registration_promotes_waitlist(mongo, admin_session, demo_session):
    # find demo participant
    demo_user = mongo.users.find_one({"email": "demo@birthright.org"})

    # Get or create a registration for demo for an upcoming workshop
    upcoming = mongo.workshops.find_one({"status": "upcoming"})
    assert upcoming, "no upcoming workshop seeded"

    reg = mongo.registrations.find_one(
        {"user_id": demo_user["id"], "workshop_id": upcoming["id"], "payment_status": "paid"}
    )
    if not reg or reg.get("checked_in"):
        # Insert one for the test
        import uuid
        from datetime import datetime, timezone
        reg = {
            "id": str(uuid.uuid4()),
            "user_id": demo_user["id"],
            "workshop_id": upcoming["id"],
            "payment_status": "paid",
            "checked_in": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        mongo.registrations.insert_one(reg)

    # seed a waitlist entry (must be a different user from demo)
    other_user = mongo.users.find_one({"role": "participant", "id": {"$ne": demo_user["id"]}})
    if not other_user:
        # use facilitator as waitlister fallback
        other_user = mongo.users.find_one({"email": "elena@birthright.org"})
    # remove any existing waitlist row for that user+workshop to ensure clean
    mongo.waitlist.delete_many({"workshop_id": upcoming["id"], "user_id": other_user["id"]})
    import uuid
    from datetime import datetime, timezone
    wl_id = str(uuid.uuid4())
    mongo.waitlist.insert_one({
        "id": wl_id,
        "workshop_id": upcoming["id"],
        "user_id": other_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notified": False,
    })

    before_promo = mongo.outbound_emails.count_documents({"template": "waitlist_promotion"})

    # demo cancels
    r = demo_session.delete(f"{BASE_URL}/api/registrations/{reg['id']}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True

    # registration marked cancelled
    updated = mongo.registrations.find_one({"id": reg["id"]})
    assert updated["payment_status"] == "cancelled"

    # waitlist promotion email queued + entry marked notified
    time.sleep(0.5)
    after_promo = mongo.outbound_emails.count_documents({"template": "waitlist_promotion"})
    assert after_promo == before_promo + 1
    wl = mongo.waitlist.find_one({"id": wl_id})
    assert wl["notified"] is True


def test_cancel_registration_wrong_user_forbidden(mongo, fac_session):
    # find a paid registration not belonging to facilitator elena
    elena = mongo.users.find_one({"email": "elena@birthright.org"})
    reg = mongo.registrations.find_one(
        {"payment_status": "paid", "user_id": {"$ne": elena["id"]}, "checked_in": {"$ne": True}}
    )
    if not reg:
        # create a participant + reg
        demo = mongo.users.find_one({"email": "demo@birthright.org"})
        upcoming = mongo.workshops.find_one({"status": "upcoming"})
        import uuid
        from datetime import datetime, timezone
        reg = {
            "id": str(uuid.uuid4()),
            "user_id": demo["id"],
            "workshop_id": upcoming["id"],
            "payment_status": "paid",
            "checked_in": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        mongo.registrations.insert_one(reg)

    r = fac_session.delete(f"{BASE_URL}/api/registrations/{reg['id']}")
    assert r.status_code == 403


def test_release_seat_participant_forbidden(mongo, demo_session):
    reg = mongo.registrations.find_one({"payment_status": "paid"})
    if not reg:
        pytest.skip("no paid registration available")
    r = demo_session.post(f"{BASE_URL}/api/registrations/{reg['id']}/release")
    assert r.status_code == 403


def test_release_seat_admin_works(mongo, admin_session):
    # Create a paid reg to release
    demo = mongo.users.find_one({"email": "demo@birthright.org"})
    upcoming = mongo.workshops.find_one({"status": "upcoming"})
    import uuid
    from datetime import datetime, timezone
    reg = {
        "id": str(uuid.uuid4()),
        "user_id": demo["id"],
        "workshop_id": upcoming["id"],
        "payment_status": "paid",
        "checked_in": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    mongo.registrations.insert_one(reg)
    r = admin_session.post(f"{BASE_URL}/api/registrations/{reg['id']}/release")
    assert r.status_code == 200
    updated = mongo.registrations.find_one({"id": reg["id"]})
    assert updated["payment_status"] == "cancelled"


# --- Regenerate image endpoint contract (auth+validation only, no real LLM call) ---
def test_regenerate_image_participant_forbidden(mongo, demo_session):
    p = mongo.products.find_one({})
    assert p
    r = demo_session.post(f"{BASE_URL}/api/products/{p['id']}/regenerate-image", json={"prompt": "x" * 20})
    assert r.status_code == 403


def test_regenerate_image_short_prompt_422(mongo, admin_session):
    p = mongo.products.find_one({})
    assert p
    r = admin_session.post(f"{BASE_URL}/api/products/{p['id']}/regenerate-image", json={"prompt": "short"})
    assert r.status_code == 422


# --- Email log endpoint ---
def test_admin_email_log(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/email-log")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert body.get("real_send_enabled") is False
    assert len(body["items"]) > 0  # we queued several in earlier tests


def test_email_log_participant_forbidden(demo_session):
    r = demo_session.get(f"{BASE_URL}/api/admin/email-log")
    assert r.status_code == 403


# --- Scheduler job registered ---
def test_scheduler_started():
    # We can't introspect the scheduler over HTTP; check supervisor backend log for the startup message.
    log_paths = [
        "/var/log/supervisor/backend.err.log",
        "/var/log/supervisor/backend.out.log",
    ]
    found = False
    for p in log_paths:
        try:
            with open(p) as f:
                content = f.read()
            if "scheduler started" in content or "workshop_reminders" in content:
                found = True
                break
        except FileNotFoundError:
            continue
    assert found, "scheduler startup log line not found in backend logs"
