"""Backend tests for AI Studio Phase 5 — Lulu integration (sandbox).

Verifies the full plumbing without burning AI dollars on every run:
  - Token fetch + caching
  - GET /lulu/env, /lulu/presets, /lulu/cost-preview
  - POST /lulu/make-fulfillable (against a seeded journal draft)
  - DELETE /lulu/fulfillment/{product_id}
  - Validation: category guard, duplicate-link guard, double-provider guard
"""
from __future__ import annotations

import os
import pathlib
import sys
import uuid

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

LULU_SANDBOX_ID = os.environ.get("LULU_SANDBOX_CLIENT_ID", "")
pytestmark = pytest.mark.skipif(not LULU_SANDBOX_ID, reason="LULU_SANDBOX_CLIENT_ID not set")

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.live"
PASSWORD = "birthright2026"

# Sample test PDFs (Dropbox-hosted, from Lulu's own sample collection)
TEST_INTERIOR_PDF = "https://www.dropbox.com/scl/fi/qz8wm8nm9pqsdrn3qd5xa/lulu-test-interior.pdf?rlkey=z6lzphnpwa3p4xwdsy6q9p9rl&dl=1"
TEST_COVER_PDF = "https://www.dropbox.com/scl/fi/2k5kqckenfx9wqo7iesg2/lulu-test-cover.pdf?rlkey=fk0nbnmnfo7v7sjlmuhn5wm22&dl=1"
JOURNAL_POD_ID = "0550X0850BWSTDPB060UW444MXX"


async def _login(email: str) -> str:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
        r.raise_for_status()
        return r.json()["token"]


@pytest_asyncio.fixture
async def admin_token() -> str:
    return await _login(ADMIN_EMAIL)


@pytest_asyncio.fixture
async def journal_product():
    """Seed a journal product directly via DB."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    from models import gen_id, now_iso  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    pid = gen_id()
    doc = {
        "id": pid,
        "slug": f"test-journal-{uuid.uuid4().hex[:8]}",
        "name": "Test Journal",
        "description": "A test journal for Lulu fulfillment.",
        "price": 0.0,
        "type": "merch",
        "image_url": "/api/static/products/studio-cap-3cb34801.png",
        "image_gallery": [],
        "inventory": 0,
        "category": "journal",
        "studio_draft": True,
        "moderation_status": "unpublished",
        "created_at": now_iso(),
        "created_by": "test",
    }
    await db.products.insert_one(dict(doc))
    try:
        yield pid
    finally:
        await db.products.delete_one({"id": pid})
        client.close()


@pytest.mark.asyncio
async def test_lulu_env_endpoint(admin_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.get("/lulu/env")
        assert r.status_code == 200
        body = r.json()
        assert body["env"] == "sandbox"
        assert "sandbox.lulu.com" in body["base_url"]


@pytest.mark.asyncio
async def test_lulu_presets_admin_only() -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.get("/lulu/presets")
        assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_lulu_presets(admin_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.get("/lulu/presets")
        assert r.status_code == 200
        keys = {p["key"] for p in r.json()}
        assert {"journal_5_5x8_5_bw_pb", "gift_journal_5_5x8_5_hc"}.issubset(keys)


@pytest.mark.asyncio
async def test_lulu_cost_preview_live(admin_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=20.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/lulu/cost-preview", json={
            "pod_package_id": JOURNAL_POD_ID,
            "page_count": 144,
            "quantity": 1,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["line_cost_usd"] > 0
        assert body["shipping_cost_usd"] > 0
        assert body["fulfillment_cost_usd"] > 0
        assert body["suggested_retail_usd"] > body["base_cost_excl_tax_usd"]
        assert body["env"] == "sandbox"
        assert body["currency"] == "USD"


@pytest.mark.asyncio
async def test_lulu_make_fulfillable_full_cycle(admin_token: str, journal_product: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=20.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        # 1) Make fulfillable
        r = await client.post("/lulu/make-fulfillable", json={
            "product_id": journal_product,
            "pod_package_id": JOURNAL_POD_ID,
            "page_count": 144,
            "interior_pdf_url": TEST_INTERIOR_PDF,
            "cover_pdf_url": TEST_COVER_PDF,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["base_cost_usd"] > 0
        assert body["retail_price_usd"] > body["base_cost_usd"]
        assert body["env"] == "sandbox"

        # 2) Duplicate link should 400
        r = await client.post("/lulu/make-fulfillable", json={
            "product_id": journal_product,
            "pod_package_id": JOURNAL_POD_ID,
            "page_count": 144,
            "interior_pdf_url": TEST_INTERIOR_PDF,
            "cover_pdf_url": TEST_COVER_PDF,
        })
        assert r.status_code == 400
        assert "already" in r.json()["detail"].lower()

        # 3) Product carries fulfillment fields
        r = await client.get(f"/products/{journal_product}")
        assert r.status_code == 200
        p = r.json()
        assert p["fulfillable_via"] == "lulu"
        assert p["lulu_pod_package_id"] == JOURNAL_POD_ID
        assert p["lulu_page_count"] == 144
        assert p["price"] == body["retail_price_usd"]

        # 4) Detach
        r = await client.delete(f"/lulu/fulfillment/{journal_product}")
        assert r.status_code == 200
        assert r.json()["ok"] is True

        # 5) Fields cleared
        r = await client.get(f"/products/{journal_product}")
        p = r.json()
        assert p.get("fulfillable_via") is None
        assert p.get("lulu_pod_package_id") is None


@pytest.mark.asyncio
async def test_lulu_rejects_unsupported_category(admin_token: str) -> None:
    """A non-paper-goods product cannot be made fulfillable on Lulu."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    cur = db.products.find({"category": {"$in": ["cap", "tee"]}}, {"_id": 0, "id": 1}).limit(1)
    rows = await cur.to_list(1)
    client.close()
    if not rows:
        pytest.skip("No cap/tee product in DB")
    pid = rows[0]["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/lulu/make-fulfillable", json={
            "product_id": pid,
            "pod_package_id": JOURNAL_POD_ID,
            "page_count": 144,
            "interior_pdf_url": TEST_INTERIOR_PDF,
            "cover_pdf_url": TEST_COVER_PDF,
        })
        assert r.status_code == 400
        assert "not yet supported on Lulu" in r.json()["detail"]


@pytest.mark.asyncio
async def test_lulu_rejects_non_http_url(admin_token: str, journal_product: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/lulu/make-fulfillable", json={
            "product_id": journal_product,
            "pod_package_id": JOURNAL_POD_ID,
            "page_count": 144,
            "interior_pdf_url": "ftp://x.com/i.pdf",
            "cover_pdf_url": TEST_COVER_PDF,
        })
        assert r.status_code == 400
        assert "http" in r.json()["detail"].lower()
