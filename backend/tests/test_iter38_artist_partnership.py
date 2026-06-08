"""Backend tests for the artist partnership module:
   - tier resolver math (boundary cases + marginal outbound brackets)
   - patronage payout creation on paid orders
   - public tier-table endpoint shape
   - artist inbound referral 'first-purchase only' guard
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

from utils.artist_tier import (  # noqa: E402
    TIERS, marginal_outbound_owed, tier_for_basis,
)
from routers.artist_partnership import record_patronage_payouts  # noqa: E402

API_BASE = "http://localhost:8001/api"


# ---------- Pure-math tier resolver -------------------------------------
def test_tier_for_basis_boundaries():
    assert tier_for_basis(0)["key"] == "emerging"
    assert tier_for_basis(5_000)["key"] == "emerging"
    assert tier_for_basis(5_001)["key"] == "sustaining"
    assert tier_for_basis(15_000)["key"] == "sustaining"
    assert tier_for_basis(15_001)["key"] == "established"
    assert tier_for_basis(40_000)["key"] == "established"
    assert tier_for_basis(40_001)["key"] == "thriving"
    assert tier_for_basis(100_000)["key"] == "thriving"
    assert tier_for_basis(100_001)["key"] == "flourishing"
    assert tier_for_basis(1_000_000)["key"] == "flourishing"


def test_marginal_outbound_emerging_is_zero():
    assert marginal_outbound_owed(0) == 0.0
    assert marginal_outbound_owed(4_999) == 0.0
    assert marginal_outbound_owed(5_000) == 0.0


def test_marginal_outbound_sustaining():
    # $5,001 → first dollar of sustaining; ~$0.02 owed
    assert marginal_outbound_owed(5_001) == pytest.approx(0.02, abs=0.01)
    # $12,000 → 0% on $5K + 2% on $7K = $140
    assert marginal_outbound_owed(12_000) == pytest.approx(140.0, abs=0.5)


def test_marginal_outbound_flourishing_example():
    # User-supplied example: $250,000 → $16,800
    # 0% * 5K + 2% * 10K + 4% * 25K + 6% * 60K + 8% * 150K
    # = 0 + 200 + 1000 + 3600 + 12000 = 16,800
    assert marginal_outbound_owed(250_000) == pytest.approx(16_800.0, abs=1.0)


# ---------- Public tier table endpoint ----------------------------------
@pytest.mark.asyncio
async def test_public_tier_table():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/partner/artist/tier-table")
        assert r.status_code == 200
        body = r.json()
        assert body["on_site_patronage_markup_pct"] == 20.0
        assert len(body["tiers"]) == 5
        keys = [t["key"] for t in body["tiers"]]
        assert keys == ["emerging", "sustaining", "established",
                         "thriving", "flourishing"]
        # First tier is starving-friendly.
        emerging = body["tiers"][0]
        assert emerging["inbound_pct"] == 10.0
        assert emerging["outbound_pct"] == 0.0
        # Attribution windows present.
        attr = body["attribution"]
        assert attr["inbound"]["cookie_days"] == 30
        assert attr["inbound"]["scope"] == "first_purchase_only"
        assert attr["outbound"]["scope"] == "first_purchase_only"


# ---------- Patronage payout creation -----------------------------------
@pytest_asyncio.fixture
async def db_handle():
    from database import db
    return db


@pytest_asyncio.fixture
async def seeded_patronage(db_handle):
    """A gallery artwork + a paid order for it."""
    db = db_handle
    artist_id = f"test-artist-{uuid.uuid4().hex[:6]}"
    product = {
        "id": f"test-art-{uuid.uuid4().hex[:6]}",
        "name": "Test artwork — Patronage payout fixture",
        "image_url": "https://example.com/art.jpg",
        "price": 400.0,
        "is_gallery_artwork": True,
        "gallery_artist_user_id": artist_id,
        "gallery_artist_name": "Test Artist",
        "edition": "1/1",
        "medium": "Oil on canvas",
        "dimensions": "24 × 36 in",
    }
    await db.products.insert_one(dict(product))
    order = {
        "id": f"test-order-{uuid.uuid4().hex[:6]}",
        "user_id": f"test-buyer-{uuid.uuid4().hex[:6]}",
        "email": "buyer@example.com",
        "status": "paid",
        "total": 480.0,
        "items": [{"product_id": product["id"],
                    "name": product["name"], "price": 400.0,
                    "quantity": 1}],
        "shipping_address": {"line1": "1 Test St", "city": "Asheville",
                              "state": "NC", "postal_code": "28801",
                              "country": "US"},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.orders.insert_one(dict(order))
    yield {"product": product, "order": order, "artist_id": artist_id}
    await db.products.delete_one({"id": product["id"]})
    await db.orders.delete_one({"id": order["id"]})
    await db.artist_sale_payouts.delete_many(
        {"order_id": order["id"]},
    )


@pytest.mark.asyncio
async def test_patronage_payout_created_and_idempotent(
    db_handle, seeded_patronage,
):
    db = db_handle
    order = seeded_patronage["order"]
    product = seeded_patronage["product"]
    artist_id = seeded_patronage["artist_id"]

    inserted = await record_patronage_payouts(db, order)
    assert len(inserted) == 1
    p = await db.artist_sale_payouts.find_one(
        {"order_id": order["id"]}, {"_id": 0},
    )
    assert p is not None
    assert p["artist_user_id"] == artist_id
    assert p["list_price"] == 400.0          # 1 × $400
    assert p["foundation_markup"] == 80.0    # 20% on top
    assert p["total_paid_by_buyer"] == 480.0
    assert p["status"] == "pending"
    assert p["shipping_address"]["city"] == "Asheville"
    assert p["buyer_email"] == "buyer@example.com"

    # Idempotency — re-running adds nothing.
    inserted2 = await record_patronage_payouts(db, order)
    assert inserted2 == []
    count = await db.artist_sale_payouts.count_documents(
        {"order_id": order["id"]},
    )
    assert count == 1
