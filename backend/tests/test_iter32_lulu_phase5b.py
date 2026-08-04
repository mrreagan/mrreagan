"""Backend tests for AI Studio Phase 5b — Auto-generated journal PDFs.

Confirms:
  - reportlab is callable and produces sized PDFs at expected dimensions
  - Cover spine width formula stays in Lulu's accepted window
  - /api/lulu/auto-generate-pdfs creates both files + returns public URLs
  - End-to-end: auto-generate → make-fulfillable using the generated URLs
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
async def journal_with_cover_image():
    """Seed a journal product whose image_url points at an actual on-disk PNG."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    from models import gen_id, now_iso  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    # Find any existing studio png we can reuse for cover bg
    static_products = ROOT / "static" / "products"
    pngs = list(static_products.glob("studio-*.png"))
    if not pngs:
        pytest.skip("No studio PNGs available for cover image")
    image_path = pngs[0]
    pid = gen_id()
    doc = {
        "id": pid,
        "slug": f"phase5b-test-{uuid.uuid4().hex[:8]}",
        "name": "Phase 5b Test Journal",
        "description": "Auto-PDF integration test journal.",
        "price": 0.0,
        "type": "merch",
        "image_url": f"/api/static/products/{image_path.name}",
        "image_gallery": [f"/api/static/products/{image_path.name}"],
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
        # cleanup generated PDFs
        for f in (ROOT / "static" / "pdfs").glob(f"*{pid}*"):
            try:
                f.unlink()
            except Exception:
                pass
        client.close()


# ============ Pure unit tests ============
def test_compute_spine_width_within_lulu_tolerance():
    """For 144 pages, our spine + bleeds must land inside Lulu's window."""
    from utils.journal_pdf import compute_spine_width, BLEED, TRIM_W
    from reportlab.lib.units import inch
    spine = compute_spine_width(144)
    cover_w = (TRIM_W * 2) + spine + (BLEED * 2)
    cover_w_inches = cover_w / inch
    # Lulu's accepted range for 144pp 5.5×8.5 BW paperback
    assert 11.572 <= cover_w_inches <= 11.697, f"cover_w={cover_w_inches:.4f} out of range"


def test_generate_interior_creates_pdf(tmp_path):
    from utils.journal_pdf import generate_interior_pdf
    out = generate_interior_pdf(tmp_path / "interior.pdf", page_count=8, title="Test")
    assert out.exists()
    assert out.stat().st_size > 1000  # non-trivial
    # Should be a valid PDF header
    assert out.read_bytes()[:4] == b"%PDF"


def test_generate_cover_creates_pdf(tmp_path):
    from utils.journal_pdf import generate_cover_pdf
    # Use any studio png as cover image
    pngs = list((ROOT / "static" / "products").glob("studio-*.png"))
    if not pngs:
        pytest.skip("No studio PNGs available")
    out = generate_cover_pdf(tmp_path / "cover.pdf", pngs[0], page_count=144, title="Test")
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"


def test_interior_page_count_rounded_up_to_4(tmp_path):
    """page_count=10 should be bumped to 12 (multiple of 4) for binding."""
    from utils.journal_pdf import generate_interior_pdf
    out = generate_interior_pdf(tmp_path / "i.pdf", page_count=10)
    raw = out.read_bytes()
    # Crudely count /Type/Page occurrences
    page_count = raw.count(b"/Type /Page\n") + raw.count(b"/Type/Page")
    # ReportLab may write pages differently — just ensure >= 12 distinct pages
    assert page_count >= 12, f"expected >=12 pages, got {page_count}"


# ============ HTTP integration tests ============
@pytest.mark.asyncio
async def test_auto_generate_pdfs_endpoint(admin_token: str, journal_with_cover_image: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/lulu/auto-generate-pdfs", json={
            "product_id": journal_with_cover_image,
            "page_count": 144,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["interior_pdf_url"].endswith(".pdf")
        assert body["cover_pdf_url"].endswith(".pdf")
        assert journal_with_cover_image in body["interior_pdf_url"]
        assert journal_with_cover_image in body["cover_pdf_url"]


@pytest.mark.asyncio
async def test_auto_generate_then_make_fulfillable(admin_token: str, journal_with_cover_image: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post("/lulu/auto-generate-pdfs", json={
            "product_id": journal_with_cover_image, "page_count": 144,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        # Use the auto-generated URLs to make-fulfillable
        r = await client.post("/lulu/make-fulfillable", json={
            "product_id": journal_with_cover_image,
            "pod_package_id": "0550X0850BWSTDPB060UW444MXX",
            "page_count": 144,
            "interior_pdf_url": body["interior_pdf_url"],
            "cover_pdf_url": body["cover_pdf_url"],
        })
        assert r.status_code == 200, r.text
        assert r.json()["base_cost_usd"] > 0


@pytest.mark.asyncio
async def test_auto_generate_rejects_unsupported_category(admin_token: str) -> None:
    """A cap product should be rejected by auto-PDF."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    cur = db.products.find({"category": "cap"}, {"_id": 0, "id": 1}).limit(1)
    rows = await cur.to_list(1)
    client.close()
    if not rows:
        pytest.skip("No cap product in DB")
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as http_client:
        r = await http_client.post("/lulu/auto-generate-pdfs", json={
            "product_id": rows[0]["id"], "page_count": 144,
        })
        assert r.status_code == 400
        assert "journal/notebook" in r.json()["detail"]
