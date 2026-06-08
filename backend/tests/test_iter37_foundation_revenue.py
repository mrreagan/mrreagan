"""Backend tests for the Foundation Revenue POD-margin tile.

Validates:
  • Endpoint requires admin auth (401 unauth, 403 non-admin).
  • Math is correct for synthetic Printful + Lulu line items.
  • Missing-base-cost SKUs surface in `missing_cost_skus`.
  • Window filter (`days=N`) excludes older orders.
"""
from __future__ import annotations

import os
import pathlib
import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.org"
ADMIN_PASSWORD = "birthright2026"
NON_ADMIN_EMAIL = "demo@birthright.org"


async def _login(email: str, password: str = "birthright2026") -> str:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.post(
            "/auth/login", json={"email": email, "password": password},
        )
        r.raise_for_status()
        return r.json()["token"]


@pytest_asyncio.fixture
async def admin_token():
    return await _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest_asyncio.fixture
async def db_handle():
    from database import db
    return db


@pytest_asyncio.fixture
async def seeded_pod_data(db_handle):
    """Insert two POD products (1 Printful, 1 Lulu) + one paid order with
    line items for each. Also a Printful SKU with NO base cost to exercise
    the missing-cost flag. Cleans up after the test."""
    db = db_handle
    prod_pf = {
        "id": f"test-pf-{uuid.uuid4().hex[:6]}",
        "name": "Test Printful Mug",
        "price": 24.99,
        "fulfillable_via": "printful",
        "printful_base_cost_usd": 8.50,
    }
    prod_lulu = {
        "id": f"test-lulu-{uuid.uuid4().hex[:6]}",
        "name": "Test Lulu Pocket Journal",
        "price": 14.99,
        "fulfillable_via": "lulu",
        "lulu_base_cost_usd": 5.20,
    }
    prod_pf_no_cost = {
        "id": f"test-pf-nocost-{uuid.uuid4().hex[:6]}",
        "name": "Test Printful Patch (no cost)",
        "price": 9.99,
        "fulfillable_via": "printful",
        # no printful_base_cost_usd → should land in missing_cost_skus
    }
    await db.products.insert_many([prod_pf, prod_lulu, prod_pf_no_cost])

    order = {
        "id": f"test-order-{uuid.uuid4().hex[:6]}",
        "status": "paid",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total": prod_pf["price"] * 2 + prod_lulu["price"] * 1
                  + prod_pf_no_cost["price"] * 3,
        "items": [
            {"product_id": prod_pf["id"], "name": prod_pf["name"],
             "price": prod_pf["price"], "quantity": 2},
            {"product_id": prod_lulu["id"], "name": prod_lulu["name"],
             "price": prod_lulu["price"], "quantity": 1},
            {"product_id": prod_pf_no_cost["id"],
             "name": prod_pf_no_cost["name"],
             "price": prod_pf_no_cost["price"], "quantity": 3},
        ],
    }
    await db.orders.insert_one(order)

    yield {
        "prod_pf": prod_pf, "prod_lulu": prod_lulu,
        "prod_pf_no_cost": prod_pf_no_cost, "order": order,
    }

    # Teardown.
    await db.orders.delete_one({"id": order["id"]})
    await db.products.delete_many({"id": {"$in": [
        prod_pf["id"], prod_lulu["id"], prod_pf_no_cost["id"],
    ]}})


# ---------- Auth gates ---------------------------------------------------
@pytest.mark.asyncio
async def test_unauth_rejected():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.get("/admin/foundation/revenue/pod-margin")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_non_admin_rejected():
    token = await _login(NON_ADMIN_EMAIL)
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.get(
            "/admin/foundation/revenue/pod-margin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403


# ---------- Shape -------------------------------------------------------
@pytest.mark.asyncio
async def test_shape_for_admin(admin_token):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.get(
            "/admin/foundation/revenue/pod-margin",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        body = r.json()
        for k in ("printful", "lulu", "combined",
                   "missing_cost_skus", "window_days", "order_count"):
            assert k in body, f"missing key: {k}"
        for bucket in (body["printful"], body["lulu"]):
            for k in ("revenue", "cost", "margin", "margin_pct",
                       "units", "sku_count"):
                assert k in bucket


# ---------- Math --------------------------------------------------------
@pytest.mark.asyncio
async def test_margin_math(admin_token, seeded_pod_data):
    pf = seeded_pod_data["prod_pf"]          # $24.99 retail, $8.50 cost, qty 2
    lulu = seeded_pod_data["prod_lulu"]      # $14.99 retail, $5.20 cost, qty 1
    nc = seeded_pod_data["prod_pf_no_cost"]  # $9.99 retail, no cost, qty 3

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.get(
            "/admin/foundation/revenue/pod-margin",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        body = r.json()

    pf_rev = round(pf["price"] * 2 + nc["price"] * 3, 2)
    pf_cost = round(pf["printful_base_cost_usd"] * 2, 2)   # nc has no cost
    pf_margin = round(pf_rev - pf_cost, 2)
    lulu_rev = round(lulu["price"] * 1, 2)
    lulu_cost = round(lulu["lulu_base_cost_usd"] * 1, 2)
    lulu_margin = round(lulu_rev - lulu_cost, 2)

    # Allow other paid orders in the DB to also contribute, so assert >=
    # for revenue/units and verify our synthetic data is included.
    assert body["printful"]["revenue"] >= pf_rev
    assert body["printful"]["cost"] >= pf_cost
    assert body["printful"]["margin"] >= pf_margin
    assert body["printful"]["units"] >= 5            # 2 + 3 from our items
    assert body["lulu"]["revenue"] >= lulu_rev
    assert body["lulu"]["cost"] >= lulu_cost
    assert body["lulu"]["margin"] >= lulu_margin
    assert body["lulu"]["units"] >= 1

    assert (body["combined"]["revenue"]
            >= round(pf_rev + lulu_rev, 2))
    assert (body["combined"]["units"]
            >= 5 + 1)

    # The no-cost SKU must be flagged.
    assert nc["name"] in body["missing_cost_skus"]

    # ---- Windowing: backdate the order and re-query with days=30 ----
    from database import db
    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    await db.orders.update_one(
        {"id": seeded_pod_data["order"]["id"]},
        {"$set": {"created_at": old}},
    )
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r2 = await client.get(
            "/admin/foundation/revenue/pod-margin?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        body2 = r2.json()
    # The 400-day-old order is now excluded by the 30-day window, so the
    # no-cost SKU should no longer be flagged.
    assert nc["name"] not in body2["missing_cost_skus"]


# ---------- (windowing covered above inside test_margin_math) -----------
