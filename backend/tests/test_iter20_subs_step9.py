"""Iter 20 — v1.11.0 Step 9 backend tests.

Covers:
  - POST /api/subscriptions/{id}/cancel (partner)
  - GET  /api/subscriptions/{id}/change-preview
  - POST /api/subscriptions/{id}/change-plan (free upgrade path)
  - GET  /api/admin/subscriptions (filters)
  - POST /api/admin/subscriptions/{id}/revoke (with + without refund)
  - Regression: iter19 endpoints (shares.log via=community-code cookie,
    bookmarks, ready-to-pay, research cite, workshop ics).
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@birthright.live", "birthright2026")
DEMO = ("demo@birthright.live", "birthright2026")


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def demo_token():
    return _login(*DEMO)


@pytest.fixture(scope="module")
def demo_user(demo_token):
    r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {demo_token}"}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def loop():
    lp = asyncio.new_event_loop()
    yield lp
    lp.close()


_MODULE_LOOP = None


def _run(coro):
    global _MODULE_LOOP
    if _MODULE_LOOP is None:
        _MODULE_LOOP = asyncio.new_event_loop()
    return _MODULE_LOOP.run_until_complete(coro)


@pytest.fixture(scope="module")
def db():
    """Direct mongo handle for seeding subscriptions (bound to module loop)."""
    from motor.motor_asyncio import AsyncIOMotorClient
    load_dotenv("/app/backend/.env")

    async def make():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        return client[os.environ["DB_NAME"]]

    return _run(make())


@pytest.fixture(scope="module")
def seeded_subs(demo_user, db):
    """Seed a community partner subscription doc for demo + capture plan ids."""
    async def setup():
        # find profile
        profile = await db.partner_profiles.find_one({
            "user_id": demo_user["id"], "partner_type": "community", "status": "active"
        })
        assert profile, "demo user is expected to have a community partner profile"
        plans = await db.subscription_plans.find({"partner_type": "community", "active": True}, {"_id": 0}).sort("duration_months", 1).to_list(10)
        assert len(plans) >= 2, "need at least two community plans"
        short_plan = plans[0]
        long_plan = plans[-1]
        # Use the longest-duration plan as the current sub so credit is large enough to free-upgrade to the short plan
        now_dt = datetime.now(timezone.utc)
        sub_id = f"TEST_SUB_{uuid.uuid4().hex[:10]}"
        await db.partner_subscriptions.insert_one({
            "id": sub_id,
            "user_id": demo_user["id"],
            "partner_profile_id": profile["id"],
            "plan_id": long_plan["id"],
            "partner_type": "community",
            "status": "active",
            "started_at": now_dt.isoformat(),
            "expires_at": (now_dt + timedelta(days=30 * int(long_plan["duration_months"]))).isoformat(),
            "duration_months": long_plan["duration_months"],
            "amount_paid": float(long_plan["price_usd"]),
            "payment_session_id": f"TEST_SESSION_{uuid.uuid4().hex[:8]}",
            "cancelled_at": None,
            "created_at": now_dt.isoformat(),
        })
        # second sub used for cancel test
        sub_id_cancel = f"TEST_SUB_{uuid.uuid4().hex[:10]}"
        await db.partner_subscriptions.insert_one({
            "id": sub_id_cancel,
            "user_id": demo_user["id"],
            "partner_profile_id": profile["id"],
            "plan_id": short_plan["id"],
            "partner_type": "community",
            "status": "active",
            "started_at": now_dt.isoformat(),
            "expires_at": (now_dt + timedelta(days=30 * int(short_plan["duration_months"]))).isoformat(),
            "duration_months": short_plan["duration_months"],
            "amount_paid": float(short_plan["price_usd"]),
            "payment_session_id": f"TEST_SESSION_{uuid.uuid4().hex[:8]}",
            "cancelled_at": None,
            "created_at": now_dt.isoformat(),
        })
        # third sub used for revoke test
        sub_id_revoke = f"TEST_SUB_{uuid.uuid4().hex[:10]}"
        await db.partner_subscriptions.insert_one({
            "id": sub_id_revoke,
            "user_id": demo_user["id"],
            "partner_profile_id": profile["id"],
            "plan_id": short_plan["id"],
            "partner_type": "community",
            "status": "active",
            "started_at": now_dt.isoformat(),
            "expires_at": (now_dt + timedelta(days=30 * int(short_plan["duration_months"]))).isoformat(),
            "duration_months": short_plan["duration_months"],
            "amount_paid": float(short_plan["price_usd"]),
            "payment_session_id": f"TEST_SESSION_{uuid.uuid4().hex[:8]}",
            "cancelled_at": None,
            "created_at": now_dt.isoformat(),
        })
        return {
            "main_sub_id": sub_id,
            "cancel_sub_id": sub_id_cancel,
            "revoke_sub_id": sub_id_revoke,
            "short_plan": short_plan,
            "long_plan": long_plan,
        }

    data = _run(setup())
    yield data

    async def teardown():
        await db.partner_subscriptions.delete_many({"id": {"$regex": "^TEST_SUB_"}})
        await db.payment_transactions.delete_many({"session_id": {"$regex": "^(TEST_SESSION_|comp_change_TEST_SUB_)"}})

    _run(teardown())


# ---------------- Step 9 cancel ----------------

class TestCancel:
    def test_cancel_subscription(self, demo_token, seeded_subs):
        sid = seeded_subs["cancel_sub_id"]
        r = requests.post(
            f"{API}/subscriptions/{sid}/cancel",
            json={"reason": "no longer needed"},
            headers={"Authorization": f"Bearer {demo_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "cancelled"
        assert data["cancelled_at"]
        assert data["cancel_reason"] == "no longer needed"
        assert data["cancelled_by"] == "partner"

    def test_cancel_idempotent_rejection(self, demo_token, seeded_subs):
        sid = seeded_subs["cancel_sub_id"]
        r = requests.post(
            f"{API}/subscriptions/{sid}/cancel",
            json={"reason": "again"},
            headers={"Authorization": f"Bearer {demo_token}"},
            timeout=20,
        )
        assert r.status_code == 400, r.text


# ---------------- Step 9 change-preview ----------------

class TestChangePreview:
    def test_preview_returns_expected_shape(self, demo_token, seeded_subs):
        sid = seeded_subs["main_sub_id"]
        new_plan = seeded_subs["short_plan"]
        r = requests.get(
            f"{API}/subscriptions/{sid}/change-preview",
            params={"new_plan_id": new_plan["id"]},
            headers={"Authorization": f"Bearer {demo_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        for key in ["current_plan_id", "new_plan_id", "new_plan_name", "new_plan_price_usd", "prorated_credit_usd", "amount_due_usd", "current_expires_at"]:
            assert key in d, f"missing {key}"
        assert d["new_plan_id"] == new_plan["id"]
        # credit should be substantial since main_sub started "now"
        assert d["prorated_credit_usd"] > 0
        assert d["amount_due_usd"] >= 0

    def test_cross_partner_type_rejected(self, demo_token, seeded_subs, db):
        sid = seeded_subs["main_sub_id"]

        async def get_other():
            return await db.subscription_plans.find_one(
                {"partner_type": {"$ne": "community"}, "active": True}, {"_id": 0}
            )

        other = _run(get_other())
        if not other:
            pytest.skip("no non-community plan available")
        r = requests.get(
            f"{API}/subscriptions/{sid}/change-preview",
            params={"new_plan_id": other["id"]},
            headers={"Authorization": f"Bearer {demo_token}"},
            timeout=20,
        )
        assert r.status_code == 400, r.text


# ---------------- Step 9 change-plan (free) ----------------

class TestChangePlanFree:
    def test_free_upgrade_when_credit_covers(self, demo_token, seeded_subs, db):
        sid = seeded_subs["main_sub_id"]
        short_plan = seeded_subs["short_plan"]
        long_plan = seeded_subs["long_plan"]
        # We expect long_plan -> short_plan to be free (credit >= short price)
        if float(long_plan["price_usd"]) < float(short_plan["price_usd"]):
            pytest.skip("long_plan cheaper than short_plan, can't guarantee free upgrade")
        r = requests.post(
            f"{API}/subscriptions/{sid}/change-plan",
            json={"new_plan_id": short_plan["id"], "origin_url": BASE_URL},
            headers={"Authorization": f"Bearer {demo_token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["checkout_required"] is False
        assert d["amount_due_usd"] == 0.0
        # verify old sub superseded, new sub active
        async def verify():
            old = await db.partner_subscriptions.find_one({"id": sid}, {"_id": 0})
            assert old["status"] == "superseded"
            new = await db.partner_subscriptions.find_one(
                {"supersedes_subscription_id": sid}, {"_id": 0}
            )
            assert new and new["status"] == "active"
            assert new["plan_id"] == short_plan["id"]
            return new
        new_sub = _run(verify())
        # Clean up the synthetic successor too
        async def cleanup():
            await db.partner_subscriptions.delete_one({"id": new_sub["id"]})
        _run(cleanup())


# ---------------- Step 9 admin list + revoke ----------------

class TestAdminSubscriptions:
    def test_admin_list_returns_array(self, admin_token):
        r = requests.get(
            f"{API}/admin/subscriptions",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        if rows:
            row = rows[0]
            assert "partner_name" in row and "partner_email" in row and "plan" in row and "is_active" in row

    def test_admin_list_filtered(self, admin_token, seeded_subs):
        r = requests.get(
            f"{API}/admin/subscriptions",
            params={"status": "active", "partner_type": "community"},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        rows = r.json()
        assert all(row["status"] == "active" for row in rows)
        assert all(row["partner_type"] == "community" for row in rows)

    def test_non_admin_cant_list(self, demo_token):
        r = requests.get(
            f"{API}/admin/subscriptions",
            headers={"Authorization": f"Bearer {demo_token}"},
            timeout=20,
        )
        assert r.status_code in (401, 403)

    def test_revoke_requires_reason(self, admin_token, seeded_subs):
        sid = seeded_subs["revoke_sub_id"]
        r = requests.post(
            f"{API}/admin/subscriptions/{sid}/revoke",
            json={"reason": "ab"},  # too short (<3 chars)
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 422, r.text

    def test_revoke_without_refund(self, admin_token, seeded_subs, db):
        sid = seeded_subs["revoke_sub_id"]
        r = requests.post(
            f"{API}/admin/subscriptions/{sid}/revoke",
            json={"reason": "policy violation", "refund": False},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "revoked"
        assert d["revoke_reason"] == "policy violation"
        assert d["expires_at"]  # set to now

    def test_revoke_with_refund_records_result(self, admin_token, seeded_subs, db):
        # Insert a fresh sub with a fake payment_session_id, then revoke with refund=True
        async def setup():
            profile = await db.partner_profiles.find_one({
                "user_id": (await db.users.find_one({"email": DEMO[0]}))["id"],
                "partner_type": "community",
                "status": "active",
            })
            plan = await db.subscription_plans.find_one({"partner_type": "community", "active": True}, {"_id": 0})
            sid = f"TEST_SUB_{uuid.uuid4().hex[:10]}"
            now_dt = datetime.now(timezone.utc)
            await db.partner_subscriptions.insert_one({
                "id": sid,
                "user_id": profile["user_id"],
                "partner_profile_id": profile["id"],
                "plan_id": plan["id"],
                "partner_type": "community",
                "status": "active",
                "started_at": now_dt.isoformat(),
                "expires_at": (now_dt + timedelta(days=90)).isoformat(),
                "duration_months": plan["duration_months"],
                "amount_paid": float(plan["price_usd"]),
                "payment_session_id": f"TEST_SESSION_REFUND_{uuid.uuid4().hex[:8]}",
                "created_at": now_dt.isoformat(),
            })
            return sid

        sid = _run(setup())
        r = requests.post(
            f"{API}/admin/subscriptions/{sid}/revoke",
            json={"reason": "test refund path", "refund": True},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "revoked"
        # refund may be None (no method), {"status": "ok"}, or {"status": "error"} — must not raise
        assert "refund" in d


# ---------------- Regression: iter 19 endpoints ----------------

class TestIter19Regression:
    def test_shares_log_via_community_code_sets_cookie(self):
        sess = requests.Session()
        # demo user's referral code is TBMBHKHR
        r = sess.post(
            f"{API}/shares/log",
            json={
                "surface": "workshop",
                "target_id": "regression-test",
                "via": "TBMBHKHR",
                "channel": "copy_link",
            },
            timeout=20,
        )
        assert r.status_code in (200, 201), r.text
        assert "birthright_ref" in sess.cookies, "cookie not set"

    def test_my_bookmarks(self, demo_token):
        r = requests.get(
            f"{API}/me/bookmarks",
            headers={"Authorization": f"Bearer {demo_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_admin_ready_to_pay(self, admin_token):
        r = requests.get(
            f"{API}/admin/payouts/ready-to-pay",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Endpoint returns a dict with ready/blocked arrays + totals
        assert isinstance(body, dict)
        assert "ready" in body and "blocked" in body
        assert isinstance(body["ready"], list)
        assert isinstance(body["blocked"], list)

    def test_research_cite(self):
        artifacts = requests.get(f"{API}/research", timeout=20)
        assert artifacts.status_code == 200
        items = artifacts.json()
        if not items:
            pytest.skip("no research artifacts seeded")
        r = requests.get(
            f"{API}/research/{items[0]['id']}/cite",
            params={"format": "apa7"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        # endpoint returns a citation string
        assert "citation" in d or "text" in d or "apa7" in d or any(isinstance(v, str) and len(v) > 5 for v in d.values())

    def test_workshop_ics(self):
        ws = requests.get(f"{API}/workshops", timeout=20)
        assert ws.status_code == 200
        items = ws.json()
        if not items:
            pytest.skip("no workshops seeded")
        r = requests.get(f"{API}/workshops/{items[0]['id']}/ics", timeout=20)
        assert r.status_code == 200, r.text
        assert "BEGIN:VCALENDAR" in r.text
