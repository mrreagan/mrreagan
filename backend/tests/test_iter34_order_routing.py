"""Backend tests for Phase 6 — POD order routing.

Covers:
  - Address adapters for Printful + Lulu shapes
  - customer_friendly_status mapping
  - dispatch_order routes printful + lulu items to the right provider
  - dispatch_order tolerates missing shipping_address (records failed_to_dispatch)
  - Cart checkout requires shipping_address when POD items present (HTTP)
"""
from __future__ import annotations

import os
import pathlib
import sys
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.org"
PASSWORD = "birthright2026"


async def _login(email: str) -> str:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
        r.raise_for_status()
        return r.json()["token"]


@pytest_asyncio.fixture
async def admin_token() -> str:
    return await _login(ADMIN_EMAIL)


# ============ Pure unit tests ============
def test_address_to_printful_maps_correctly():
    from utils.order_dispatch import _address_to_printful
    addr = {
        "name": "Test", "address1": "1 Main", "city": "Asheville",
        "state_code": "NC", "postcode": "28801", "country_code": "US",
    }
    r = _address_to_printful(addr, "test@x.com")
    assert r["name"] == "Test"
    assert r["zip"] == "28801"
    assert r["email"] == "test@x.com"
    assert r["country_code"] == "US"


def test_address_to_lulu_maps_correctly():
    from utils.order_dispatch import _address_to_lulu
    addr = {
        "name": "Test", "address1": "1 Main", "city": "Asheville",
        "state_code": "NC", "postcode": "28801", "country_code": "US",
    }
    r = _address_to_lulu(addr)
    assert r["street1"] == "1 Main"
    assert r["postcode"] == "28801"
    assert r["phone_number"]  # has a default


def test_customer_friendly_status():
    from utils.order_dispatch import customer_friendly_status
    assert customer_friendly_status("SHIPPED") == "Shipped"
    assert customer_friendly_status("inprocess") == "Being printed"
    assert customer_friendly_status("CREATED") == "Preparing for printing"
    assert customer_friendly_status("fulfilled_by_birthright") == "Preparing"
    assert customer_friendly_status(None) == "Preparing"
    # Unknown status falls back to titlecased version
    assert customer_friendly_status("weird_thing") == "Weird Thing"


# ============ Dispatch logic (mocked providers) ============
@pytest.mark.asyncio
async def test_dispatch_skips_non_pod_items():
    """A Birthright-fulfilled item should record fulfilled_by_birthright with no provider call."""
    from utils.order_dispatch import dispatch_order

    class FakeProducts:
        async def find_one(self, q, _proj=None):
            return {"id": q["id"], "name": "Mug", "fulfillable_via": None}

    class FakeDB:
        products = FakeProducts()

    order = {
        "id": "o1",
        "items": [{"product_id": "p1", "quantity": 1}],
        "shipping_address": {"address1": "1 Main"},
        "contact_email": "c@x.com",
    }
    fulfillments = await dispatch_order(FakeDB(), order)
    assert len(fulfillments) == 1
    assert fulfillments[0]["status"] == "fulfilled_by_birthright"
    assert fulfillments[0]["provider"] is None


@pytest.mark.asyncio
async def test_dispatch_fails_when_no_shipping_address():
    """POD items in an order without shipping_address record failed_to_dispatch."""
    from utils.order_dispatch import dispatch_order

    class FakeProducts:
        async def find_one(self, q, _proj=None):
            return {"id": q["id"], "name": "Cap", "fulfillable_via": "printful",
                     "printful_sync_variant_id": 999}

    class FakeDB:
        products = FakeProducts()

    order = {
        "id": "o2",
        "items": [{"product_id": "p1", "quantity": 1}],
        "shipping_address": {},
        "contact_email": "c@x.com",
    }
    fulfillments = await dispatch_order(FakeDB(), order)
    assert fulfillments[0]["status"] == "failed_to_dispatch"
    assert "shipping address" in fulfillments[0]["error"].lower()


@pytest.mark.asyncio
async def test_dispatch_routes_to_printful():
    """A printful item should call printful.create_order."""
    from utils import order_dispatch

    class FakeProducts:
        async def find_one(self, q, _proj=None):
            return {"id": q["id"], "name": "Cap", "fulfillable_via": "printful",
                     "printful_sync_variant_id": 5331424994}

    class FakeDB:
        products = FakeProducts()

    order = {
        "id": "o3",
        "items": [{"product_id": "p1", "quantity": 2}],
        "shipping_address": {"name": "Q", "address1": "1 Main", "city": "A",
                              "state_code": "NC", "postcode": "28801", "country_code": "US"},
        "contact_email": "c@x.com",
    }
    fake_resp = {"id": 12345, "status": "draft"}
    with patch.object(order_dispatch.printful, "create_order", new=AsyncMock(return_value=fake_resp)) as mock:
        fulfillments = await order_dispatch.dispatch_order(FakeDB(), order)
    assert mock.await_count == 1
    assert fulfillments[0]["provider"] == "printful"
    assert fulfillments[0]["provider_order_id"] == "12345"
    assert fulfillments[0]["status"] == "draft"
    # Check that quantity was passed through
    args = mock.await_args
    assert args.kwargs["items"][0]["quantity"] == 2


@pytest.mark.asyncio
async def test_dispatch_routes_to_lulu():
    """A lulu item should call lulu.create_print_job."""
    from utils import order_dispatch

    class FakeProducts:
        async def find_one(self, q, _proj=None):
            return {
                "id": q["id"], "name": "Journal", "fulfillable_via": "lulu",
                "lulu_pod_package_id": "0550X0850BWSTDPB060UW444MXX",
                "lulu_page_count": 144,
                "lulu_interior_pdf_url": "https://x.com/i.pdf",
                "lulu_cover_pdf_url": "https://x.com/c.pdf",
            }

    class FakeDB:
        products = FakeProducts()

    order = {
        "id": "o4",
        "items": [{"product_id": "p1", "quantity": 1}],
        "shipping_address": {"name": "Q", "address1": "1 Main", "city": "A",
                              "state_code": "NC", "postcode": "28801", "country_code": "US"},
        "contact_email": "c@x.com",
    }
    fake_resp = {"id": 99999, "status": {"name": "CREATED"}}
    with patch.object(order_dispatch.lulu, "create_print_job", new=AsyncMock(return_value=fake_resp)) as mock:
        fulfillments = await order_dispatch.dispatch_order(FakeDB(), order)
    assert mock.await_count == 1
    assert fulfillments[0]["provider"] == "lulu"
    assert fulfillments[0]["provider_order_id"] == "99999"
    assert fulfillments[0]["status"] == "CREATED"


@pytest.mark.asyncio
async def test_dispatch_records_provider_failure():
    """A raised PrintfulError should land as failed_to_dispatch with the message."""
    from utils import order_dispatch
    from utils.printful_client import PrintfulError

    class FakeProducts:
        async def find_one(self, q, _proj=None):
            return {"id": q["id"], "name": "Cap", "fulfillable_via": "printful",
                     "printful_sync_variant_id": 999}

    class FakeDB:
        products = FakeProducts()

    order = {
        "id": "o5",
        "items": [{"product_id": "p1", "quantity": 1}],
        "shipping_address": {"name": "Q", "address1": "1 Main", "city": "A",
                              "state_code": "NC", "postcode": "28801", "country_code": "US"},
        "contact_email": "c@x.com",
    }
    with patch.object(order_dispatch.printful, "create_order",
                      new=AsyncMock(side_effect=PrintfulError("Printful 400: Invalid variant"))):
        fulfillments = await order_dispatch.dispatch_order(FakeDB(), order)
    assert fulfillments[0]["status"] == "failed_to_dispatch"
    assert "invalid variant" in fulfillments[0]["error"].lower()


# ============ HTTP integration: cart guard ============
@pytest.mark.asyncio
async def test_checkout_requires_shipping_for_pod(admin_token: str) -> None:
    """Adding a POD-fulfilled product to a cart without shipping_address → 400."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    cur = db.products.find(
        {"fulfillable_via": {"$in": ["printful", "lulu"]}, "moderation_status": "active"},
        {"_id": 0, "id": 1},
    ).limit(1)
    rows = await cur.to_list(1)
    client.close()
    if not rows:
        pytest.skip("No POD-fulfilled active product in DB")
    pid = rows[0]["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as http:
        r = await http.post("/checkout/products", json={
            "items": [{"product_id": pid, "quantity": 1}],
            "origin_url": "https://x.com",
        })
        assert r.status_code == 400
        assert "Shipping address is required" in r.json()["detail"]


@pytest.mark.asyncio
async def test_checkout_accepts_when_shipping_provided(admin_token: str) -> None:
    """Same cart with shipping_address → 200 + Stripe session URL."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    cur = db.products.find(
        {"fulfillable_via": {"$in": ["printful", "lulu"]}, "moderation_status": "active"},
        {"_id": 0, "id": 1},
    ).limit(1)
    rows = await cur.to_list(1)
    client.close()
    if not rows:
        pytest.skip("No POD-fulfilled active product in DB")
    pid = rows[0]["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as http:
        r = await http.post("/checkout/products", json={
            "items": [{"product_id": pid, "quantity": 1}],
            "origin_url": "https://x.com",
            "shipping_address": {
                "name": "QA", "address1": "100 Mission St", "city": "Asheville",
                "state_code": "NC", "postcode": "28801", "country_code": "US",
            },
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "url" in body
        assert body["url"].startswith("http")
