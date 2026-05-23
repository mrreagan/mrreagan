"""Phase 6B.3 — Community Referrals + Reporting MVP tests."""
import os
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

ADMIN_EMAIL = "admin@birthright.org"
DEMO_EMAIL = "demo@birthright.org"
ELENA_EMAIL = "elena@birthright.org"
MARCUS_EMAIL = "marcus@birthright.org"
# Default matches the documented seed password in /app/memory/test_credentials.md.
# Override via TEST_USER_PASSWORD env var when running tests against a non-seed env.
PASSWORD = os.environ.get("TEST_USER_PASSWORD", "birthright2026")  # noqa: S105  # pragma: allowlist secret


# ============ FIXTURES ============

@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def demo_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": DEMO_EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def elena_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ELENA_EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def marcus_token():
    """Facilitator with NO partner profile — used for partner-null cases."""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": MARCUS_EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def db():
    """Direct mongo client for seeding/teardown."""
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Helper to run async coroutines in sync tests
def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ============ PUBLIC REDIRECT /api/r/{code} ============

class TestReferralRedirect:
    def test_invalid_code_redirects_home(self):
        r = requests.get(f"{BASE_URL}/api/r/NOTREAL1", allow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    def test_valid_code_redirects_to_partner_page(self, demo_token):
        # demo has community partner profile sam-rivera-community
        # Get demo's referral code via my-link
        r = requests.get(f"{BASE_URL}/api/referrals/my-link/community", headers=h(demo_token))
        assert r.status_code == 200, r.text
        code = r.json()["code"]
        assert len(code) == 8

        rr = requests.get(f"{BASE_URL}/api/r/{code}", allow_redirects=False)
        assert rr.status_code == 302
        # default destination = /partners/{slug}
        assert rr.headers["location"].startswith("/partners/")
        # cookie set
        assert "birthright_ref" in rr.headers.get("set-cookie", "").lower()

    def test_valid_code_with_workshop_param(self, demo_token):
        r = requests.get(f"{BASE_URL}/api/referrals/my-link/community", headers=h(demo_token))
        code = r.json()["code"]
        rr = requests.get(f"{BASE_URL}/api/r/{code}?workshop=birthright-hub", allow_redirects=False)
        assert rr.status_code == 302
        assert rr.headers["location"] == "/workshops/birthright-hub"


# ============ PARTNER ENDPOINTS ============

class TestPartnerEndpoints:
    def test_my_link_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/referrals/my-link/community")
        assert r.status_code in (401, 403)

    def test_my_link_returns_code_and_base_path(self, demo_token):
        r = requests.get(f"{BASE_URL}/api/referrals/my-link/community", headers=h(demo_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "code" in data and len(data["code"]) == 8
        assert data["base_path"] == f"/api/r/{data['code']}"

    def test_my_link_404_when_no_profile(self, elena_token):
        r = requests.get(f"{BASE_URL}/api/referrals/my-link/community", headers=h(elena_token))
        assert r.status_code == 404

    def test_my_earnings_returns_summary(self, demo_token):
        r = requests.get(f"{BASE_URL}/api/referrals/my-earnings", headers=h(demo_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "summary" in data and "recent" in data
        s = data["summary"]
        for key in ("pending_payout", "lifetime_total", "paid_to_date", "count", "by_subject_type"):
            assert key in s, f"missing {key} in summary"
        assert isinstance(s["by_subject_type"], dict)


# ============ ADMIN REFERRAL ENDPOINTS ============

class TestAdminReferrals:
    def test_admin_referrals_requires_admin(self, demo_token):
        r = requests.get(f"{BASE_URL}/api/admin/referrals", headers=h(demo_token))
        assert r.status_code == 403

    def test_admin_referrals_earned(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/admin/referrals?status=earned", headers=h(admin_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_referrals_paid(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/admin/referrals?status=paid", headers=h(admin_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_payout_summary_requires_admin(self, demo_token):
        r = requests.get(f"{BASE_URL}/api/admin/referrals/payout-summary", headers=h(demo_token))
        assert r.status_code == 403

    def test_payout_summary_shape(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/admin/referrals/payout-summary", headers=h(admin_token))
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        for row in rows:
            for k in ("partner_name", "partner_email", "earned", "paid", "count"):
                assert k in row


# ============ END-TO-END: SEED REFERRAL & MARK PAID ============

@pytest.fixture(scope="module")
def seeded_referral_id(db):
    """Insert a TEST_ referral row directly into mongo (demo is community partner)."""
    async def _seed():
        # Find demo user
        u = await db.users.find_one({"email": DEMO_EMAIL}, {"_id": 0})
        assert u, "demo user not found"
        # Find demo partner profile
        p = await db.partner_profiles.find_one({"user_id": u["id"], "partner_type": "community"}, {"_id": 0})
        assert p, "demo community partner profile not found"
        from uuid import uuid4
        rid = f"TEST_{uuid4().hex[:12]}"
        doc = {
            "id": rid,
            "payment_session_id": f"TEST_sess_{uuid4().hex[:10]}",
            "referral_code": p.get("referral_code") or "TESTCODE",
            "partner_profile_id": p["id"],
            "partner_user_id": u["id"],
            "buyer_user_id": "test-buyer",
            "subject_type": "workshop",
            "subject_id": "test-workshop",
            "subject_label": "TEST Workshop",
            "order_total": 200.0,
            "rev_share_pct": 10.0,
            "payout_amount": 20.0,
            "status": "earned",
            "earned_at": "2026-01-01T00:00:00+00:00",
            "paid_at": None,
            "payout_method": None,
            "payout_reference": None,
            "payout_note": None,
        }
        await db.referrals.insert_one(doc)
        return rid

    rid = run(_seed())
    yield rid
    # Teardown
    run(db.referrals.delete_one({"id": rid}))


class TestMarkPaid:
    def test_mark_paid_requires_admin(self, demo_token, seeded_referral_id):
        r = requests.post(
            f"{BASE_URL}/api/admin/referrals/{seeded_referral_id}/mark-paid",
            json={"method": "manual", "reference": "X1", "note": ""},
            headers=h(demo_token),
        )
        assert r.status_code == 403

    def test_mark_paid_changes_status(self, admin_token, seeded_referral_id):
        r = requests.post(
            f"{BASE_URL}/api/admin/referrals/{seeded_referral_id}/mark-paid",
            json={"method": "manual", "reference": "TEST_PAYOUT_REF", "note": "test"},
            headers=h(admin_token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "paid"
        assert data["payout_reference"] == "TEST_PAYOUT_REF"

    def test_mark_paid_idempotent_second_call_400(self, admin_token, seeded_referral_id):
        # second call should reject (already paid)
        r = requests.post(
            f"{BASE_URL}/api/admin/referrals/{seeded_referral_id}/mark-paid",
            json={"method": "manual", "reference": "x", "note": ""},
            headers=h(admin_token),
        )
        assert r.status_code == 400

    def test_mark_paid_404_for_unknown(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/admin/referrals/does-not-exist/mark-paid",
            json={"method": "manual"},
            headers=h(admin_token),
        )
        assert r.status_code == 404


# ============ REPORTS ============

class TestMyReports:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/me/reports")
        assert r.status_code in (401, 403)

    def test_demo_reports_shape(self, demo_token):
        r = requests.get(f"{BASE_URL}/api/me/reports", headers=h(demo_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert set(data.keys()) >= {"engagement", "finance", "partner"}
        eng = data["engagement"]
        for k in ("registrations", "workshops_attended", "reviews_written", "impact_statements", "discussions_posted"):
            assert k in eng
        fin = data["finance"]
        assert "lifetime_spend" in fin
        assert set(fin["by_category"].keys()) == {"workshops", "shop", "sponsorship", "donations"}
        # demo has community partner profile → partner block populated
        assert data["partner"] is not None

    def test_marcus_reports_partner_null(self, marcus_token):
        # marcus has facilitator role but no partner_profile
        r = requests.get(f"{BASE_URL}/api/me/reports", headers=h(marcus_token))
        assert r.status_code == 200
        data = r.json()
        assert data["partner"] is None


class TestAdminReports:
    def test_requires_admin(self, demo_token):
        r = requests.get(f"{BASE_URL}/api/admin/reports", headers=h(demo_token))
        assert r.status_code == 403

    def test_admin_reports_shape(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/admin/reports", headers=h(admin_token))
        assert r.status_code == 200
        data = r.json()
        for k in ("engagement", "revenue", "payouts", "top_partners", "top_workshops"):
            assert k in data, f"missing {k}"
        rev = data["revenue"]
        for k in ("workshops", "shop", "subscriptions", "sponsorship", "donations", "gross_total"):
            assert k in rev, f"missing revenue.{k}"
        assert isinstance(data["top_partners"], list)
        assert isinstance(data["top_workshops"], list)


# ============ COOKIE CAPTURE ON CHECKOUT ============

class TestCookieCapture:
    def test_workshop_checkout_captures_referral_cookie(self, demo_token, db):
        """POST /api/checkout/workshop with birthright_ref cookie → metadata.referral_code recorded."""
        # Get a partner's referral code (demo is the community partner)
        rcode = requests.get(f"{BASE_URL}/api/referrals/my-link/community", headers=h(demo_token)).json()["code"]

        # Find an upcoming workshop that demo isn't registered in
        async def _find_w():
            regs = await db.registrations.find(
                {"user_id": (await db.users.find_one({"email": DEMO_EMAIL}))["id"], "payment_status": "paid"}
            ).to_list(50)
            registered_ids = {r["workshop_id"] for r in regs}
            workshops = await db.workshops.find({"status": {"$ne": "completed"}}).to_list(20)
            for w in workshops:
                if w["id"] not in registered_ids:
                    return w["id"], w.get("slug")
            return None, None

        wid, slug = run(_find_w())
        if not wid:
            pytest.skip("No available workshop for demo to checkout")

        cookies = {"birthright_ref": rcode}
        r = requests.post(
            f"{BASE_URL}/api/checkout/workshop",
            json={"workshop_id": wid, "origin_url": BASE_URL},
            headers=h(demo_token),
            cookies=cookies,
        )
        # Note: demo IS the partner, so attribution skipped on fulfilment.
        # But we just need to verify the cookie is captured in payment_transactions metadata.
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]

        async def _check():
            txn = await db.payment_transactions.find_one({"session_id": sid}, {"_id": 0})
            return txn

        txn = run(_check())
        assert txn is not None
        assert txn["metadata"].get("referral_code") == rcode

        # Cleanup
        run(db.payment_transactions.delete_one({"session_id": sid}))


# ============ REGRESSION: PHASE 6B.2 ============

class TestRegression6B2:
    def test_subscription_plans_returns_12(self):
        r = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 12

    def test_partners_list(self):
        r = requests.get(f"{BASE_URL}/api/partners")
        assert r.status_code == 200

    def test_workshops_list(self):
        r = requests.get(f"{BASE_URL}/api/workshops")
        assert r.status_code == 200
