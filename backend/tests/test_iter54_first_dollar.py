"""iter-54 · First-Dollar Wall public feed.

Covers `GET /api/first-dollar/recent` — the redacted first-purchase feed
consumed by the homepage marquee. Verifies redaction (first name + last
initial only), first-purchase-per-user dedupe, and PII containment
(no email / address / user_id ever leaks through).
"""
import os
import requests
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import dotenv_values

ENV = dotenv_values("/app/backend/.env")
FRONTEND_ENV = dotenv_values("/app/frontend/.env")
BASE = FRONTEND_ENV["REACT_APP_BACKEND_URL"].rstrip("/")


@pytest.fixture(scope="module")
def mongo():
    return AsyncIOMotorClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]


def _now_iso(offset_sec=0):
    from datetime import datetime, timezone, timedelta
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_sec)).isoformat()


@pytest.fixture(scope="module")
def seed(mongo):
    """Seed two users + three orders (one user has two orders → only earliest
    should show in the feed)."""
    async def _go():
        # Clean any prior test artefacts.
        await mongo.users.delete_many({"email": {"$in": ["fdw_a@birthright.live",
                                                          "fdw_b@birthright.live"]}})
        await mongo.orders.delete_many({"contact_email": {"$in": ["fdw_a@birthright.live",
                                                                    "fdw_b@birthright.live"]}})
        u_a = {"id": "fdw-user-a", "email": "fdw_a@birthright.live",
               "first_name": "Ada", "last_name": "Lovelace",
               "role": "member", "created_at": _now_iso(-10000)}
        u_b = {"id": "fdw-user-b", "email": "fdw_b@birthright.live",
               "first_name": "Bertrand", "last_name": "Russell",
               "role": "member", "created_at": _now_iso(-10000)}
        await mongo.users.insert_many([u_a, u_b])
        # Ada has TWO orders — only her earliest counts as her "first dollar".
        await mongo.orders.insert_many([
            {"id": "fdw-order-a1", "user_id": "fdw-user-a",
             "items": [{"product_id": "px", "name": "Reflection Workbook", "quantity": 1}],
             "total": 2400, "status": "paid",
             "contact_email": "fdw_a@birthright.live",
             "created_at": _now_iso(-3000)},   # OLDER — this is Ada's first
            {"id": "fdw-order-a2", "user_id": "fdw-user-a",
             "items": [{"product_id": "py", "name": "Follow-up Print", "quantity": 1}],
             "total": 3200, "status": "paid",
             "contact_email": "fdw_a@birthright.live",
             "created_at": _now_iso(-1000)},
            {"id": "fdw-order-b1", "user_id": "fdw-user-b",
             "items": [{"product_id": "pz", "name": "Workshop Registration", "quantity": 1}],
             "total": 5000, "status": "paid",
             "contact_email": "fdw_b@birthright.live",
             "created_at": _now_iso(-500)},    # Bertrand's first + only
        ])
        return u_a, u_b
    yield asyncio.new_event_loop().run_until_complete(_go())
    async def _cleanup(m):
        await m.users.delete_many({"email": {"$in": ["fdw_a@birthright.live",
                                                       "fdw_b@birthright.live"]}})
        await m.orders.delete_many({"contact_email": {"$in": ["fdw_a@birthright.live",
                                                                 "fdw_b@birthright.live"]}})
    # Fresh client + loop for teardown so we don't cross-attach futures.
    _m2 = AsyncIOMotorClient(ENV["MONGO_URL"])[ENV["DB_NAME"]]
    _l = asyncio.new_event_loop()
    try:
        _l.run_until_complete(_cleanup(_m2))
    finally:
        _l.close()


class TestFirstDollarPublicFeed:
    def test_endpoint_returns_200_without_auth(self):
        r = requests.get(f"{BASE}/api/first-dollar/recent?limit=5", timeout=15)
        assert r.status_code == 200, r.text[:300]
        assert isinstance(r.json(), list)

    def test_seeded_users_appear_first_purchase_only(self, seed):
        r = requests.get(f"{BASE}/api/first-dollar/recent?limit=50", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        # Find our seeded rows by display_name.
        ada_rows = [x for x in rows if x["display_name"] == "Ada L."]
        bert_rows = [x for x in rows if x["display_name"] == "Bertrand R."]
        assert len(ada_rows) == 1, f"expected Ada exactly once, got {len(ada_rows)}"
        assert len(bert_rows) == 1
        # Ada's first purchase was the workbook, NOT the follow-up print.
        assert ada_rows[0]["item_label"] == "Reflection Workbook"
        assert bert_rows[0]["item_label"] == "Workshop Registration"

    def test_no_pii_leaks_in_payload(self, seed):
        r = requests.get(f"{BASE}/api/first-dollar/recent?limit=50", timeout=15)
        payload_text = r.text
        # Redaction check — full last name should NEVER appear.
        assert "Lovelace" not in payload_text
        assert "Russell" not in payload_text
        # Email addresses should never appear either.
        assert "fdw_a@birthright.live" not in payload_text
        assert "fdw_b@birthright.live" not in payload_text
        # user_id must not leak (internal identifier).
        assert "fdw-user-a" not in payload_text
        assert "fdw-user-b" not in payload_text

    def test_limit_query_param_respected(self):
        r = requests.get(f"{BASE}/api/first-dollar/recent?limit=1", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) <= 1

    def test_limit_bounds(self):
        # < 1 -> 422, > 50 -> 422
        assert requests.get(f"{BASE}/api/first-dollar/recent?limit=0", timeout=15).status_code == 422
        assert requests.get(f"{BASE}/api/first-dollar/recent?limit=51", timeout=15).status_code == 422
