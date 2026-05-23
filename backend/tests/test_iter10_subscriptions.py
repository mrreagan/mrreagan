"""Iter 10 — Phase 6B.2 Partner Subscriptions, Auto-Licensing, Dual-Tier Rev-Share.

Covers:
- GET /api/subscriptions/plans (filters + invalid)
- POST /api/subscriptions/checkout (auth, plan validity, profile gating)
- create_subscription_from_txn idempotent fulfilment
- GET /api/subscriptions/my
- GET /api/partners/my-rev-share/{type} (global_default vs subscription)
- Regression on prior endpoints
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

import pytest
import requests

# Ensure backend imports work
sys.path.insert(0, "/app/backend")


def _load_backend_url() -> str:
    val = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not val:
        try:
            with open("/app/frontend/.env", "r") as fh:
                for line in fh:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        val = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            pass
    return val.rstrip("/")


BASE_URL = _load_backend_url()
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

ADMIN = ("admin@birthright.org", "birthright2026")
ELENA = ("elena@birthright.org", "birthright2026")
DEMO = ("demo@birthright.org", "birthright2026")


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def tokens() -> dict:
    return {
        "admin": _login(*ADMIN),
        "elena": _login(*ELENA),
        "demo": _login(*DEMO),
    }


@pytest.fixture(scope="session")
def plans() -> dict:
    """Index plans by (partner_type, duration_months)."""
    r = requests.get(f"{API}/subscriptions/plans", timeout=20)
    assert r.status_code == 200
    out = {}
    for p in r.json():
        out[(p["partner_type"], p["duration_months"])] = p
    return out


# ===================== PLANS =====================
class TestPlans:
    def test_list_all_no_filter_returns_12(self):
        r = requests.get(f"{API}/subscriptions/plans", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) == 12, f"expected 12 plans, got {len(body)}"
        # mongo _id must not leak
        for p in body:
            assert "_id" not in p

    def test_filter_facilitator(self):
        r = requests.get(f"{API}/subscriptions/plans", params={"partner_type": "facilitator"}, timeout=20)
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 3
        for p in plans:
            assert p["partner_type"] == "facilitator"
            assert "birthright_ip_pct" in p
            assert "other_content_pct" in p
            assert p["birthright_ip_pct"] > p["other_content_pct"]

    def test_filter_community(self):
        r = requests.get(f"{API}/subscriptions/plans", params={"partner_type": "community"}, timeout=20)
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 3
        for p in plans:
            assert p["partner_type"] == "community"
            assert "default_pct" in p
        # Verify rev-share inverse to length
        by_dur = {p["duration_months"]: p for p in plans}
        assert by_dur[1]["default_pct"] > by_dur[12]["default_pct"] > by_dur[24]["default_pct"]

    def test_invalid_partner_type_400(self):
        r = requests.get(f"{API}/subscriptions/plans", params={"partner_type": "wizard"}, timeout=20)
        assert r.status_code == 400


# ===================== CHECKOUT =====================
class TestCheckout:
    def test_checkout_anonymous_401(self, plans):
        plan = plans[("community", 12)]
        r = requests.post(f"{API}/subscriptions/checkout",
                          json={"plan_id": plan["id"], "origin_url": "https://example.com"}, timeout=20)
        assert r.status_code in (401, 403)

    def test_checkout_unknown_plan_404(self, tokens):
        r = requests.post(f"{API}/subscriptions/checkout", headers=_h(tokens["demo"]),
                          json={"plan_id": "no-such-plan", "origin_url": "https://example.com"}, timeout=20)
        assert r.status_code == 404

    def test_checkout_demo_facilitator_forbidden(self, tokens, plans):
        plan = plans[("facilitator", 12)]
        r = requests.post(f"{API}/subscriptions/checkout", headers=_h(tokens["demo"]),
                          json={"plan_id": plan["id"], "origin_url": "https://example.com"}, timeout=20)
        assert r.status_code == 403, r.text

    def test_checkout_demo_community_succeeds(self, tokens, plans):
        plan = plans[("community", 12)]
        r = requests.post(f"{API}/subscriptions/checkout", headers=_h(tokens["demo"]),
                          json={"plan_id": plan["id"], "origin_url": "https://example.com"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("url", "").startswith("https://")
        assert body.get("session_id")
        TestCheckout.session_id = body["session_id"]
        TestCheckout.plan_id = plan["id"]

    def test_payment_transaction_row_created(self):
        """Verify a payment_transactions row was inserted with type=subscription."""
        session_id = getattr(TestCheckout, "session_id", None)
        if not session_id:
            pytest.skip("no checkout session created")
        import motor.motor_asyncio

        async def _check():
            client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
            db = client["test_database"]
            doc = await db.payment_transactions.find_one({"session_id": session_id})
            client.close()
            return doc

        doc = asyncio.get_event_loop().run_until_complete(_check()) if False else asyncio.new_event_loop().run_until_complete(_check())
        assert doc is not None
        assert doc["type"] == "subscription"
        assert doc["payment_status"] == "initiated"
        assert doc["metadata"]["plan_id"] == TestCheckout.plan_id
        assert doc["metadata"]["duration_months"] == "12"
        assert doc["metadata"]["partner_profile_id"]


# ===================== FULFILMENT (idempotent) =====================
class TestFulfilment:
    def test_create_subscription_from_txn_and_idempotent(self, tokens, plans):
        """Simulate paid txn -> call create_subscription_from_txn directly."""
        from routers.subscriptions import create_subscription_from_txn
        import motor.motor_asyncio

        async def _run():
            client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
            db = client["test_database"]
            # use the prior checkout session if available; otherwise construct synthetic
            session_id = getattr(TestCheckout, "session_id", None)
            if session_id:
                txn = await db.payment_transactions.find_one({"session_id": session_id})
                # simulate stripe webhook marking it paid
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {"payment_status": "paid", "status": "complete"}},
                )
                txn["payment_status"] = "paid"
            else:
                # synthesize
                plan = plans[("community", 12)]
                # Find demo profile id
                user = await db.users.find_one({"email": "demo@birthright.org"})
                profile = await db.partner_profiles.find_one(
                    {"user_id": user["id"], "partner_type": "community", "status": "active"}
                )
                fake_session = f"TEST_SESS_{uuid.uuid4().hex[:12]}"
                txn = {
                    "id": "txn-test",
                    "session_id": fake_session,
                    "user_id": user["id"],
                    "type": "subscription",
                    "amount": plan["price_usd"],
                    "currency": "usd",
                    "metadata": {
                        "type": "subscription",
                        "plan_id": plan["id"],
                        "partner_type": "community",
                        "duration_months": str(plan["duration_months"]),
                        "partner_profile_id": profile["id"],
                        "user_id": user["id"],
                    },
                    "payment_status": "paid",
                    "status": "complete",
                }
                await db.payment_transactions.insert_one(dict(txn))

            # First call -> creates
            await create_subscription_from_txn(db, txn)
            subs_after_1 = await db.partner_subscriptions.find(
                {"payment_session_id": txn["session_id"]}
            ).to_list(10)
            assert len(subs_after_1) == 1, f"expected 1 sub, got {len(subs_after_1)}"
            sub = subs_after_1[0]
            assert sub["status"] == "active"
            assert sub["partner_type"] == "community"
            assert sub["duration_months"] == 12
            assert sub["expires_at"] > sub["started_at"]

            # Second call -> idempotent
            await create_subscription_from_txn(db, txn)
            subs_after_2 = await db.partner_subscriptions.find(
                {"payment_session_id": txn["session_id"]}
            ).to_list(10)
            assert len(subs_after_2) == 1, "idempotency violated"

            # Verify audit log
            audit = await db.audit_log.find_one({"action": "subscription.activate", "target_id": sub["id"]})
            assert audit is not None, "audit log entry missing"

            TestFulfilment.sub_id = sub["id"]
            TestFulfilment.session_id = txn["session_id"]
            client.close()

        asyncio.new_event_loop().run_until_complete(_run())


# ===================== MY SUBSCRIPTIONS =====================
class TestMySubscriptions:
    def test_my_subscriptions_after_fulfilment(self, tokens):
        r = requests.get(f"{API}/subscriptions/my", headers=_h(tokens["demo"]), timeout=20)
        assert r.status_code == 200
        subs = r.json()
        active = [s for s in subs if s.get("is_active")]
        assert active, f"expected at least one active sub, got {subs}"
        s = active[0]
        assert s.get("plan") is not None
        assert s["plan"]["partner_type"] in ("facilitator", "community", "research", "vendor")
        assert s.get("expires_at")


# ===================== REV-SHARE =====================
class TestRevShare:
    def test_invalid_partner_type_400(self, tokens):
        r = requests.get(f"{API}/partners/my-rev-share/invalid_type", headers=_h(tokens["demo"]), timeout=20)
        assert r.status_code == 400

    def test_demo_community_after_fulfilment_is_subscription(self, tokens, plans):
        r = requests.get(f"{API}/partners/my-rev-share/community", headers=_h(tokens["demo"]), timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        # After fulfilment the source must be subscription
        assert body["source"] == "subscription", f"expected subscription source, got {body}"
        expected_pct = plans[("community", 12)]["default_pct"]
        assert body["pct"] == expected_pct
        assert body["plan_id"] == plans[("community", 12)]["id"]
        assert body["expires_at"]

    def test_elena_facilitator_no_sub_uses_global_default(self, tokens):
        # Elena has no facilitator partner_profile / no facilitator sub -> global_default
        r_true = requests.get(f"{API}/partners/my-rev-share/facilitator",
                              params={"presents_birthright_ip": "true"},
                              headers=_h(tokens["elena"]), timeout=20)
        r_false = requests.get(f"{API}/partners/my-rev-share/facilitator",
                               params={"presents_birthright_ip": "false"},
                               headers=_h(tokens["elena"]), timeout=20)
        assert r_true.status_code == 200, r_true.text
        assert r_false.status_code == 200, r_false.text
        b_true, b_false = r_true.json(), r_false.json()
        assert b_true["source"] == "global_default"
        assert b_false["source"] == "global_default"
        # global default for facilitator is 72.5 per seeded foundation_settings
        assert b_true["pct"] == b_false["pct"]


# ===================== REGRESSION =====================
class TestRegression:
    def test_partners_listing(self):
        r = requests.get(f"{API}/partners", timeout=20)
        assert r.status_code == 200

    def test_sam_rivera_slug(self):
        r = requests.get(f"{API}/partners/sam-rivera-community", timeout=20)
        assert r.status_code == 200
        assert r.json()["slug"] == "sam-rivera-community"

    def test_governance_proposals(self):
        r = requests.get(f"{API}/governance/proposals", timeout=20)
        assert r.status_code == 200

    def test_workshops(self):
        r = requests.get(f"{API}/workshops", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_reviews_search(self):
        r = requests.get(f"{API}/reviews/search", timeout=20)
        assert r.status_code == 200


# ===================== CLEANUP =====================
@pytest.fixture(scope="session", autouse=True)
def _cleanup_after():
    yield
    import motor.motor_asyncio

    async def _clean():
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
        db = client["test_database"]
        sub_id = getattr(TestFulfilment, "sub_id", None)
        session_id = getattr(TestFulfilment, "session_id", None) or getattr(TestCheckout, "session_id", None)
        if sub_id:
            await db.partner_subscriptions.delete_many({"id": sub_id})
        if session_id:
            await db.partner_subscriptions.delete_many({"payment_session_id": session_id})
            await db.payment_transactions.delete_many({"session_id": session_id})
            await db.audit_log.delete_many({"action": "subscription.activate"})
        client.close()

    try:
        asyncio.new_event_loop().run_until_complete(_clean())
    except Exception as e:
        print(f"cleanup error: {e}")
