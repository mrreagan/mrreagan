"""Backend tests for AI Studio Phase 4 — Off-site referral mode.

Covers:
  - Vendor can create off-site drafts via /studio/generate (seeded via DB to avoid AI spend)
  - Validation: off_site requires valid http(s) URL
  - Validation: only vendors can create off-site (admin cannot, defends against UI mistakes)
  - Approved off-site product appears in public /products listing
  - /api/out/{slug}?product_id=X redirects to vendor URL with ?via=birthright_<slug> stamp
  - Click logged in outbound_clicks with product_id
  - Off-site product cannot be checked out via /checkout/products
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

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.org"
VENDOR_EMAIL = "demo@birthright.org"
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
async def vendor_token() -> str:
    return await _login(VENDOR_EMAIL)


@pytest_asyncio.fixture
async def off_site_product():
    """Seed an approved off-site product directly via DB so tests stay fast + cheap."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    from models import gen_id, now_iso  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    vp = await db.partner_profiles.find_one({"partner_type": "vendor", "status": "active"})
    pid = gen_id()
    doc = {
        "id": pid,
        "slug": f"test-offsite-{uuid.uuid4().hex[:8]}",
        "name": "Test Off-Site Product",
        "description": "Vendor's own store, listed here as a referral.",
        "price": 75.0,
        "type": "merch",
        "image_url": "/api/static/products/studio-cap-3cb34801.png",
        "image_gallery": [],
        "inventory": 0,
        "category": "poster",
        "is_vendor_product": True,
        "vendor_user_id": vp["user_id"],
        "vendor_partner_id": vp["id"],
        "vendor_name": vp.get("display_name"),
        "vendor_slug": vp.get("slug"),
        "is_off_site": True,
        "external_url": "https://democrafts.example.com/products/oak-stool",
        "moderation_status": "active",
        "studio_draft": False,
        "created_at": now_iso(),
        "created_by": vp["user_id"],
    }
    await db.products.insert_one(dict(doc))
    try:
        yield {"id": pid, "vendor_slug": vp["slug"], "external_url": doc["external_url"]}
    finally:
        await db.products.delete_one({"id": pid})
        client.close()


@pytest.mark.asyncio
async def test_off_site_requires_valid_url(vendor_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as client:
        r = await client.post("/studio/generate", json={
            "brief": "test off site product brief", "category": "poster",
            "audiences": ["general_equip"], "image_count": 1,
            "is_off_site": True, "external_url": "notaurl",
        })
        assert r.status_code == 400
        assert "external_url" in r.json()["detail"]


@pytest.mark.asyncio
async def test_off_site_admin_cannot_create(admin_token: str) -> None:
    """Admin cannot create off-site products — only vendors can."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/studio/generate", json={
            "brief": "test off site admin attempt", "category": "poster",
            "audiences": ["general_equip"], "image_count": 1,
            "is_off_site": True, "external_url": "https://example.com/x",
        })
        assert r.status_code == 400
        assert "Off-site mode is only available to vendor partners" in r.json()["detail"]


@pytest.mark.asyncio
async def test_off_site_appears_in_public_products(off_site_product) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.get("/products?type=merch")
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()}
        assert off_site_product["id"] in ids


@pytest.mark.asyncio
async def test_outbound_redirect_product_scoped(off_site_product) -> None:
    """GET /api/out/{slug}?product_id=X should 302 to external_url with ?via= appended."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0, follow_redirects=False) as client:
        r = await client.get(f"/out/{off_site_product['vendor_slug']}?product_id={off_site_product['id']}")
        assert r.status_code == 302
        loc = r.headers["location"]
        assert loc.startswith(off_site_product["external_url"])
        assert "via=birthright_" in loc
        assert off_site_product["vendor_slug"] in loc


@pytest.mark.asyncio
async def test_outbound_logs_click_with_product_id(off_site_product, admin_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0, follow_redirects=False) as client:
        await client.get(f"/out/{off_site_product['vendor_slug']}?product_id={off_site_product['id']}")
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.get(f"/admin/outbound-clicks?partner_slug={off_site_product['vendor_slug']}")
        assert r.status_code == 200
        rows = r.json()
        scoped = [row for row in rows if row.get("product_id") == off_site_product["id"]]
        assert len(scoped) >= 1


@pytest.mark.asyncio
async def test_off_site_blocked_at_checkout(off_site_product, vendor_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as client:
        r = await client.post("/checkout/products", json={
            "items": [{"product_id": off_site_product["id"], "quantity": 1}],
            "origin_url": "https://x.com",
            "success_url": "https://x.com/s",
            "cancel_url": "https://x.com/c",
        })
        assert r.status_code == 400
        assert "vendor's own site" in r.json()["detail"]


@pytest.mark.asyncio
async def test_outbound_fallback_when_product_missing(off_site_product) -> None:
    """Unknown product_id should fall back to partner's external_site_url (or /partners/{slug})."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0, follow_redirects=False) as client:
        r = await client.get(f"/out/{off_site_product['vendor_slug']}?product_id=does-not-exist")
        # Either redirects to fallback URL or to /partners/{slug}
        assert r.status_code == 302
        loc = r.headers["location"]
        # Should NOT redirect to the off-site product (since product_id is invalid)
        assert "oak-stool" not in loc
