"""Backend tests for Phase 6 — Lulu webhook handler.

Covers:
  - _extract_lulu_tracking pulls tracking_id / tracking_urls / carrier_name
  - apply_lulu_webhook finds the order, updates fulfillment status + tracking
  - apply_lulu_webhook is a no-op (and audit-logs) when no order matches
  - HTTP POST /api/lulu/webhook/<token> rejects bad tokens
  - HTTP POST /api/lulu/webhook/<token> with bad token returns 401
  - End-to-end: POST a real payload, dashboard/me reflects new status + tracking
"""
from __future__ import annotations

import os
import pathlib
import sys
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.live"
PASSWORD = "birthright2026"


async def _login(email: str) -> str:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
        r.raise_for_status()
        return r.json()["token"]


@pytest_asyncio.fixture
async def admin_token() -> str:
    return await _login(ADMIN_EMAIL)


@pytest_asyncio.fixture
async def db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


# ============ Pure unit tests ============
def test_extract_lulu_tracking_shipped_single_item():
    from utils.order_dispatch import _extract_lulu_tracking
    line_items = [{
        "messages": {
            "tracking_id": "1Z999",
            "tracking_urls": ["https://ups.com/track?n=1Z999"],
            "carrier_name": "UPS",
        },
    }]
    tr = _extract_lulu_tracking(line_items)
    assert tr["tracking_id"] == "1Z999"
    assert tr["tracking_url"] == "https://ups.com/track?n=1Z999"
    assert tr["carrier_name"] == "UPS"


def test_extract_lulu_tracking_skips_missing():
    from utils.order_dispatch import _extract_lulu_tracking
    line_items = [{"messages": {}}, {"messages": {"tracking_id": "X", "tracking_urls": []}}]
    tr = _extract_lulu_tracking(line_items)
    assert tr["tracking_id"] == "X"
    assert tr["tracking_url"] is None


def test_extract_lulu_tracking_multiple_shipments():
    from utils.order_dispatch import _extract_lulu_tracking
    line_items = [
        {"messages": {"tracking_id": "A", "tracking_urls": ["https://a"]}},
        {"messages": {"tracking_id": "B", "tracking_urls": ["https://b"]}},
    ]
    tr = _extract_lulu_tracking(line_items)
    assert tr["tracking_id"] == "A"
    assert len(tr["extra_shipments"]) == 1
    assert tr["extra_shipments"][0]["tracking_id"] == "B"


def test_extract_lulu_tracking_empty():
    from utils.order_dispatch import _extract_lulu_tracking
    assert _extract_lulu_tracking([]) == {}
    assert _extract_lulu_tracking([{"messages": None}]) == {}


# ============ Webhook applier — DB integration ============
@pytest.mark.asyncio
async def test_apply_lulu_webhook_updates_order(db):
    """Insert a fake order with a lulu fulfillment, fire a webhook payload,
    confirm the order's fulfillment status + tracking are updated."""
    from utils.order_dispatch import apply_lulu_webhook
    print_job_id = 91000000 + (uuid.uuid4().int % 9000000)
    order_id = f"test-order-{uuid.uuid4().hex[:8]}"
    await db.orders.insert_one({
        "id": order_id,
        "user_id": None,
        "items": [{"product_id": "p1", "name": "Test Journal", "price": 28.0, "quantity": 1}],
        "total": 28.0,
        "payment_session_id": "cs_test_xxx",
        "status": "paid",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fulfillments": [{
            "product_id": "p1",
            "quantity": 1,
            "provider": "lulu",
            "provider_order_id": str(print_job_id),
            "status": "CREATED",
        }],
    })

    payload = {
        "id": print_job_id,
        "status": {"name": "SHIPPED"},
        "line_item_statuses": [{
            "messages": {
                "tracking_id": "1Z-WEBHOOK-TEST",
                "tracking_urls": ["https://ups.com/track?n=1Z-WEBHOOK-TEST"],
                "carrier_name": "UPS",
            },
        }],
    }
    result = await apply_lulu_webhook(db, payload)
    try:
        assert result["matched"] is True
        assert result["status"] == "SHIPPED"
        assert result["tracking"]["tracking_id"] == "1Z-WEBHOOK-TEST"

        updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
        assert updated["fulfillments"][0]["status"] == "SHIPPED"
        assert updated["fulfillments"][0]["customer_status"] == "Shipped"
        assert updated["fulfillments"][0]["tracking"]["tracking_id"] == "1Z-WEBHOOK-TEST"
        # Audit row got persisted
        evt = await db.lulu_webhook_events.find_one(
            {"lulu_print_job_id": str(print_job_id)}, {"_id": 0},
        )
        assert evt is not None
        assert evt["status"] == "SHIPPED"
    finally:
        await db.orders.delete_one({"id": order_id})
        await db.lulu_webhook_events.delete_many({"lulu_print_job_id": str(print_job_id)})


@pytest.mark.asyncio
async def test_apply_lulu_webhook_no_match(db):
    """Webhook for an unknown print job → matched=False, no DB writes."""
    from utils.order_dispatch import apply_lulu_webhook
    payload = {"id": 1, "status": {"name": "IN_PRODUCTION"}, "line_item_statuses": []}
    # The id=1 might collide with real orders; use a guaranteed-not-present one.
    payload["id"] = -99999999
    result = await apply_lulu_webhook(db, payload)
    assert result["matched"] is False


@pytest.mark.asyncio
async def test_apply_lulu_webhook_missing_id(db):
    from utils.order_dispatch import apply_lulu_webhook
    result = await apply_lulu_webhook(db, {})
    assert result["matched"] is False
    assert "missing" in result["reason"].lower()


# ============ HTTP receiver ============
@pytest.mark.asyncio
async def test_webhook_endpoint_rejects_bad_token():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.post("/lulu/webhook/not-the-real-token", json={"id": 1})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_webhook_endpoint_rejects_non_json():
    token = os.environ["LULU_WEBHOOK_TOKEN"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.post(
            f"/lulu/webhook/{token}",
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_webhook_endpoint_e2e_updates_dashboard(db, admin_token):
    """Insert order tied to admin user, hit the public endpoint with a real
    payload shape, then call /api/foundation/dashboard/me and confirm the
    status + tracking surface to the user."""
    token = os.environ["LULU_WEBHOOK_TOKEN"]
    admin = await db.users.find_one({"email": ADMIN_EMAIL}, {"_id": 0, "id": 1})
    assert admin, "admin user must exist"
    print_job_id = 92000000 + (uuid.uuid4().int % 9000000)
    order_id = f"test-order-{uuid.uuid4().hex[:8]}"

    await db.orders.insert_one({
        "id": order_id,
        "user_id": admin["id"],
        "items": [{"product_id": "p1", "name": "Webhook E2E Journal", "price": 28.0, "quantity": 1}],
        "total": 28.0,
        "payment_session_id": f"cs_test_{uuid.uuid4().hex[:8]}",
        "status": "paid",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fulfillments": [{
            "product_id": "p1",
            "quantity": 1,
            "provider": "lulu",
            "provider_order_id": str(print_job_id),
            "status": "CREATED",
        }],
    })

    payload = {
        "id": print_job_id,
        "status": {"name": "IN_PRODUCTION"},
        "line_item_statuses": [],
    }
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0) as client:
            r = await client.post(f"/lulu/webhook/{token}", json=payload)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["received"] is True
            assert body["matched"] is True

        # Customer dashboard should show "Being printed"
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {admin_token}"}) as client:
            r = await client.get("/dashboard/me")
            assert r.status_code == 200
            orders = r.json()["orders"]
            mine = next((o for o in orders if o["id"] == order_id), None)
            assert mine is not None
            assert mine["fulfillments"][0]["status"] == "IN_PRODUCTION"
            assert mine["fulfillments"][0]["customer_status"] == "Being printed"

        # Now ship it with tracking
        ship_payload = {
            "id": print_job_id,
            "status": {"name": "SHIPPED"},
            "line_item_statuses": [{
                "messages": {
                    "tracking_id": "E2E-TRACK",
                    "tracking_urls": ["https://ups.com/track?n=E2E-TRACK"],
                    "carrier_name": "UPS",
                },
            }],
        }
        async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0) as client:
            r = await client.post(f"/lulu/webhook/{token}", json=ship_payload)
            assert r.status_code == 200

        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {admin_token}"}) as client:
            r = await client.get("/dashboard/me")
            mine = next(o for o in r.json()["orders"] if o["id"] == order_id)
            assert mine["fulfillments"][0]["customer_status"] == "Shipped"
            assert mine["fulfillments"][0]["tracking"]["tracking_id"] == "E2E-TRACK"
            assert mine["fulfillments"][0]["tracking"]["tracking_url"].startswith("https://")
    finally:
        await db.orders.delete_one({"id": order_id})
        await db.lulu_webhook_events.delete_many({"lulu_print_job_id": str(print_job_id)})
