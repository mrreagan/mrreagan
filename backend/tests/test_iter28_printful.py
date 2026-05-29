"""Backend tests for Phase 2 Printful "Make fulfillable" integration.

These are integration tests — they require:
  - PRINTFUL_API_TOKEN set in backend/.env
  - The seeded admin (admin@birthright.org / birthright2026) to exist
  - PRINTFUL_PUBLIC_IMAGE_BASE pointing to a publicly-reachable URL

Skipped automatically if PRINTFUL_API_TOKEN is missing.
"""
from __future__ import annotations

import os
import pathlib
import sys

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

PRINTFUL_TOKEN = os.environ.get("PRINTFUL_API_TOKEN", "")
pytestmark = pytest.mark.skipif(not PRINTFUL_TOKEN, reason="PRINTFUL_API_TOKEN not set")

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.org"
ADMIN_PASSWORD = "birthright2026"


async def _login() -> str:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        r.raise_for_status()
        return r.json()["token"]


@pytest_asyncio.fixture
async def admin_token() -> str:
    return await _login()


@pytest_asyncio.fixture
async def studio_draft(admin_token: str) -> dict:
    """Get the most recent admin studio draft (created by prior test run)."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.get("/studio/drafts")
        r.raise_for_status()
        drafts = r.json()
        if not drafts:
            pytest.skip("No studio drafts available for Printful test")
        # Find a cap draft (Printful-supported); fall back to first
        for d in drafts:
            if d.get("category") == "cap":
                return d
        return drafts[0]


@pytest.mark.asyncio
async def test_categories_endpoint(admin_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.get("/printful/categories")
        assert r.status_code == 200
        rows = r.json()
        cats = {row["category"] for row in rows}
        assert {"cap", "tee", "hoodie", "mug"}.issubset(cats)


@pytest.mark.asyncio
async def test_categories_admin_only() -> None:
    """Anonymous request should be rejected."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.get("/printful/categories")
        # Either 401 (no auth) or 403 (admin only) is acceptable
        assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_make_fulfillable_then_detach(admin_token: str, studio_draft: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    pid = studio_draft["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=60.0, headers=headers) as client:
        # 0) Pre-detach if already linked (cleanup from prior runs)
        if studio_draft.get("printful_sync_product_id"):
            await client.delete(f"/printful/sync-products/{pid}")

        # 1) Make fulfillable
        r = await client.post("/printful/make-fulfillable",
                              json={"product_id": pid, "markup_multiplier": 2.0})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["sync_product_id"] > 0
        assert body["retail_price_usd"] > 0

        # 2) Duplicate request should 400
        r = await client.post("/printful/make-fulfillable",
                              json={"product_id": pid, "markup_multiplier": 2.0})
        assert r.status_code == 400
        assert "already" in r.json()["detail"].lower()

        # 3) Product should expose the printful fields
        r = await client.get(f"/products/{pid}")
        assert r.status_code == 200
        prod = r.json()
        assert prod["printful_sync_product_id"] == body["sync_product_id"]
        assert prod["fulfillable_via"] == "printful"

        # 4) Detach
        r = await client.delete(f"/printful/sync-products/{pid}")
        assert r.status_code == 200
        assert r.json()["ok"] is True

        # 5) After detach, fields should be gone
        r = await client.get(f"/products/{pid}")
        assert r.status_code == 200
        prod = r.json()
        assert prod.get("printful_sync_product_id") is None
        assert prod.get("fulfillable_via") is None


@pytest.mark.asyncio
async def test_make_fulfillable_rejects_unsupported_category(admin_token: str) -> None:
    """A foundation product with a non-supported category must be rejected."""
    from database import db  # type: ignore  # noqa: PLC0415
    # Pick any seeded foundation product whose category isn't in our supported set.
    cur = db.products.find({
        "category": {"$nin": ["cap", "tee", "hoodie", "mug"]},
        "studio_draft": {"$ne": True},
    }, {"_id": 0, "id": 1, "category": 1}).limit(1)
    prods = await cur.to_list(1)
    if not prods:
        pytest.skip("No non-supported foundation products in DB to test rejection")
    pid = prods[0]["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/printful/make-fulfillable",
                              json={"product_id": pid, "markup_multiplier": 2.0})
        assert r.status_code == 400
        assert "not yet supported" in r.json()["detail"].lower()
