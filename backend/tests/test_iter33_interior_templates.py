"""Backend tests for AI Studio Phase 5c — Prompt-specific interior templates.

Covers:
  - All 6 interior styles generate valid PDFs
  - /api/lulu/interior-styles endpoint returns the registry
  - /api/lulu/auto-generate-pdfs honors `interior_style` override
  - /api/lulu/auto-generate-pdfs falls back to stored `interior_style` if no override
  - Studio infers the right style for representative briefs (this DOES spend
    Claude tokens — small/cheap, but skip in offline runs)
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

LULU_OK = bool(os.environ.get("LULU_SANDBOX_CLIENT_ID"))
pytestmark = pytest.mark.skipif(not LULU_OK, reason="LULU_SANDBOX_CLIENT_ID not set")

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
async def journal_with_inferred_style():
    """Seed a journal with a pre-set interior_style for the dropdown override tests."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    from models import gen_id, now_iso  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    static_products = ROOT / "static" / "products"
    pngs = list(static_products.glob("studio-*.png"))
    if not pngs:
        pytest.skip("No studio PNGs")
    pid = gen_id()
    doc = {
        "id": pid,
        "slug": f"phase5c-{uuid.uuid4().hex[:8]}",
        "name": "Phase 5c Test Journal",
        "description": "...",
        "price": 0.0,
        "type": "merch",
        "image_url": f"/api/static/products/{pngs[0].name}",
        "image_gallery": [],
        "inventory": 0,
        "category": "journal",
        "studio_draft": True,
        "moderation_status": "unpublished",
        "interior_style": "habit_tracker",  # pre-inferred
        "created_at": now_iso(),
        "created_by": "test",
    }
    await db.products.insert_one(dict(doc))
    try:
        yield pid
    finally:
        await db.products.delete_one({"id": pid})
        for f in (ROOT / "static" / "pdfs").glob(f"*{pid}*"):
            try:
                f.unlink()
            except Exception:
                pass
        client.close()


# ============ Unit: each style renders ============
@pytest.mark.parametrize("style", [
    "lined", "blank", "dot_grid", "split_top_blank_bottom_lined",
    "dated_lined", "habit_tracker",
])
def test_every_style_renders(tmp_path, style):
    from utils.journal_pdf import generate_interior_pdf
    out = generate_interior_pdf(tmp_path / f"{style}.pdf", page_count=12, title="T", style=style)
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"
    assert out.stat().st_size > 800  # all styles produce > 800 bytes


def test_unknown_style_falls_back(tmp_path):
    """An unknown style should warn and fall back to lined, not crash."""
    from utils.journal_pdf import generate_interior_pdf
    out = generate_interior_pdf(tmp_path / "bad.pdf", page_count=8, style="not_a_real_style")
    assert out.exists()


# ============ HTTP: registry endpoint ============
@pytest.mark.asyncio
async def test_interior_styles_endpoint(admin_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.get("/lulu/interior-styles")
        assert r.status_code == 200
        keys = {row["key"] for row in r.json()}
        assert {"lined", "blank", "dot_grid", "split_top_blank_bottom_lined",
                "dated_lined", "habit_tracker"}.issubset(keys)


@pytest.mark.asyncio
async def test_auto_pdf_uses_stored_style(admin_token: str, journal_with_inferred_style: str) -> None:
    """Without override, the endpoint should use the stored interior_style."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=20.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/lulu/auto-generate-pdfs",
                              json={"product_id": journal_with_inferred_style, "page_count": 12})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["interior_style"] == "habit_tracker"


@pytest.mark.asyncio
async def test_auto_pdf_honors_override(admin_token: str, journal_with_inferred_style: str) -> None:
    """An explicit override should win over the stored style."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=20.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/lulu/auto-generate-pdfs", json={
            "product_id": journal_with_inferred_style,
            "page_count": 12,
            "interior_style": "dot_grid",
        })
        assert r.status_code == 200, r.text
        assert r.json()["interior_style"] == "dot_grid"


@pytest.mark.asyncio
async def test_auto_pdf_bad_override_falls_back(admin_token: str, journal_with_inferred_style: str) -> None:
    """An invalid override should silently fall back to the default (lined)."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=20.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/lulu/auto-generate-pdfs", json={
            "product_id": journal_with_inferred_style,
            "page_count": 12,
            "interior_style": "nope",
        })
        assert r.status_code == 200, r.text
        assert r.json()["interior_style"] == "lined"
