"""Lulu — Phase 5: Admin "Make fulfillable on Lulu" on AI Studio drafts (paper goods).

Unlike Printful, Lulu has no sync product catalog. So "Make fulfillable" here
is a purely-internal config write that records:
  - pod_package_id  (book spec from Lulu's developer Price Calculator)
  - page_count
  - interior_pdf_url / cover_pdf_url (admin/vendor provides for now)
  - base_cost_usd  (from a fresh /print-job-cost-calculations/ call)
  - retail_price_usd (2× base, rounded to $.95)

A separate test endpoint creates a sandbox print job to verify file validity
before opening the product to customers.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from models import now_iso
from utils import lulu_client as lulu
from utils.audit import log_action

logger = logging.getLogger("birthright.lulu")
router = APIRouter(prefix="/lulu", tags=["lulu"])

# ---- Curated pod_package_id presets ----
# Values must be confirmed against https://developers.lulu.com/price-calculator
# for the live account. We expose a small starter set; admin can override per draft.
POD_PRESETS: dict[str, dict] = {
    "journal_5_5x8_5_bw_pb": {
        "pod_package_id": "0550X0850BWSTDPB060UW444MXX",
        "label": "Journal · 5.5×8.5 · paperback · B&W · 60# cream",
        "default_page_count": 144,
        "applies_to": ["journal", "notebook"],
    },
    "workbook_8_5x11_bw_pb": {
        "pod_package_id": "0850X1100BWSTDPB060UW444MXX",
        "label": "Workbook · 8.5×11 · paperback · B&W · 60# cream",
        "default_page_count": 100,
        "applies_to": ["notebook"],
    },
    "gift_journal_5_5x8_5_hc": {
        "pod_package_id": "0550X0850BWSTDCW060UW444MXX",
        "label": "Gift journal · 5.5×8.5 · casebound hardcover · B&W",
        "default_page_count": 144,
        "applies_to": ["journal"],
    },
}

LULU_CATEGORIES = {"journal", "notebook"}


# ============ Pydantic ============
class CostPreviewRequest(BaseModel):
    pod_package_id: str = Field(min_length=1, max_length=64)
    page_count: int = Field(ge=4, le=800)
    quantity: int = Field(default=1, ge=1, le=10)


class CostPreviewResponse(BaseModel):
    pod_package_id: str
    page_count: int
    line_cost_usd: float
    shipping_cost_usd: float
    fulfillment_cost_usd: float
    tax_usd: float
    base_cost_excl_tax_usd: float
    total_cost_usd: float
    suggested_retail_usd: float
    currency: str = "USD"
    env: str


class MakeFulfillableRequest(BaseModel):
    product_id: str = Field(min_length=1)
    pod_package_id: str = Field(min_length=1, max_length=64)
    page_count: int = Field(ge=4, le=800)
    interior_pdf_url: str = Field(min_length=10, max_length=500)
    cover_pdf_url: str = Field(min_length=10, max_length=500)
    retail_price_override: Optional[float] = Field(default=None, gt=0)
    markup_multiplier: float = Field(default=2.0, ge=1.2, le=5.0)


class MakeFulfillableResponse(BaseModel):
    ok: bool
    pod_package_id: str
    base_cost_usd: float
    retail_price_usd: float
    env: str


# ============ Helpers ============
def _admin_only(user: dict) -> None:
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")


def _validate_url(u: str) -> str:
    s = u.strip()
    if not s.lower().startswith(("http://", "https://")):
        raise HTTPException(400, "PDF URL must be http(s)://...")
    # Don't enforce .pdf extension — many hosts use signed URLs with query strings.
    # Lulu will reject the file at validation time if it's not a real PDF.
    return s


# ============ Endpoints ============
@router.get("/env")
async def lulu_env(user: dict = Depends(get_current_user)):
    """Return current Lulu environment + base URL (admin debugging)."""
    _admin_only(user)
    return {"env": (os.environ.get("LULU_ENV") or "sandbox"), "base_url": lulu.get_base_url()}


@router.get("/presets")
async def list_presets(user: dict = Depends(get_current_user)):
    """Return the curated pod_package_id presets we currently support."""
    _admin_only(user)
    return [
        {"key": k, **v}
        for k, v in POD_PRESETS.items()
    ]


@router.get("/interior-styles")
async def list_interior_styles(user: dict = Depends(get_current_user)):
    """Return the available interior page styles (for admin override dropdown)."""
    _admin_only(user)
    from utils import journal_pdf  # noqa: PLC0415
    return [
        {"key": k, "description": v}
        for k, v in journal_pdf.INTERIOR_STYLES.items()
    ]


@router.post("/cost-preview", response_model=CostPreviewResponse)
async def cost_preview(req: CostPreviewRequest, user: dict = Depends(get_current_user)):
    """Hit Lulu's cost calculator. Returns a cost breakdown + a suggested retail price."""
    _admin_only(user)
    try:
        raw = await lulu.calculate_cost(
            pod_package_id=req.pod_package_id,
            page_count=req.page_count,
            quantity=req.quantity,
        )
    except lulu.LuluError as ex:
        raise HTTPException(502, f"Lulu cost preview failed: {ex}") from ex
    summary = lulu.summarise_cost(raw)
    suggested = lulu.suggest_retail_price(summary["base_cost_excl_tax_usd"])
    return CostPreviewResponse(
        pod_package_id=req.pod_package_id,
        page_count=req.page_count,
        currency=raw.get("currency", "USD"),
        env=(os.environ.get("LULU_ENV") or "sandbox"),
        suggested_retail_usd=suggested,
        **summary,
    )


@router.post("/make-fulfillable", response_model=MakeFulfillableResponse)
async def make_fulfillable(req: MakeFulfillableRequest, user: dict = Depends(get_current_user)):
    """Persist Lulu fulfillment config on the product.

    Steps:
      1) Look up the product, ensure it's a paper-goods category we support on Lulu.
      2) Call Lulu's cost calculator to confirm config is valid + capture base cost.
      3) Compute retail price (override or 2× rounded to $.95).
      4) Write printful-style fulfillment fields on the product doc.
    """
    _admin_only(user)
    from database import db

    product = await db.products.find_one({"id": req.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    if product.get("lulu_pod_package_id"):
        raise HTTPException(400, "Product is already fulfillable on Lulu")
    if product.get("fulfillable_via") == "printful":
        raise HTTPException(400, "Product is already fulfillable on Printful — unlink first")

    category = (product.get("category") or "").lower()
    if category not in LULU_CATEGORIES:
        raise HTTPException(
            400,
            f"Category '{category}' is not yet supported on Lulu. Supported: {sorted(LULU_CATEGORIES)}",
        )

    interior_url = _validate_url(req.interior_pdf_url)
    cover_url = _validate_url(req.cover_pdf_url)

    # 1) Hit Lulu cost calc to validate pod_package_id + capture base cost
    try:
        raw = await lulu.calculate_cost(
            pod_package_id=req.pod_package_id,
            page_count=req.page_count,
            quantity=1,
        )
    except lulu.LuluError as ex:
        raise HTTPException(502, f"Lulu rejected this config: {ex}") from ex
    summary = lulu.summarise_cost(raw)
    base_cost = summary["base_cost_excl_tax_usd"]
    if base_cost <= 0:
        raise HTTPException(502, "Lulu returned a zero base cost — config likely invalid")

    # 2) Retail price decision
    retail_price = (
        float(req.retail_price_override)
        if req.retail_price_override
        else lulu.suggest_retail_price(base_cost, req.markup_multiplier)
    )

    # 3) Persist
    await db.products.update_one(
        {"id": product["id"]},
        {"$set": {
            "lulu_pod_package_id": req.pod_package_id,
            "lulu_page_count": req.page_count,
            "lulu_interior_pdf_url": interior_url,
            "lulu_cover_pdf_url": cover_url,
            "lulu_base_cost_usd": base_cost,
            "lulu_env": (os.environ.get("LULU_ENV") or "sandbox"),
            "fulfillable_via": "lulu",
            "price": retail_price,
            "fulfillable_at": now_iso(),
        }},
    )

    await log_action(
        db, user, "lulu.make_fulfillable",
        target_type="product", target_id=product["id"],
        metadata={
            "pod_package_id": req.pod_package_id,
            "page_count": req.page_count,
            "base_cost_usd": base_cost,
            "retail_price_usd": retail_price,
        },
    )

    return MakeFulfillableResponse(
        ok=True,
        pod_package_id=req.pod_package_id,
        base_cost_usd=base_cost,
        retail_price_usd=retail_price,
        env=(os.environ.get("LULU_ENV") or "sandbox"),
    )


@router.delete("/fulfillment/{product_id}")
async def detach_from_lulu(product_id: str, user: dict = Depends(get_current_user)):
    """Unlink a product from Lulu. (Lulu has no sync product to delete.)"""
    _admin_only(user)
    from database import db
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    if product.get("fulfillable_via") != "lulu":
        raise HTTPException(400, "Product is not linked to Lulu")
    await db.products.update_one(
        {"id": product_id},
        {"$unset": {
            "lulu_pod_package_id": "",
            "lulu_page_count": "",
            "lulu_interior_pdf_url": "",
            "lulu_cover_pdf_url": "",
            "lulu_base_cost_usd": "",
            "lulu_env": "",
            "fulfillable_via": "",
            "fulfillable_at": "",
        }},
    )
    await log_action(
        db, user, "lulu.detach",
        target_type="product", target_id=product_id,
        metadata={"pod_package_id": product.get("lulu_pod_package_id")},
    )
    return {"ok": True}


class TestPrintJobRequest(BaseModel):
    product_id: str = Field(min_length=1)
    name: str = Field(default="Birthright Test", min_length=1, max_length=80)
    address1: str = Field(min_length=3)
    city: str = Field(min_length=2)
    state_code: str = Field(min_length=2, max_length=3)
    postcode: str = Field(min_length=4, max_length=10)
    country_code: str = Field(default="US", min_length=2, max_length=2)
    phone_number: str = Field(default="555-555-5555")
    contact_email: str = Field(min_length=4)


class AutoGeneratePdfsRequest(BaseModel):
    product_id: str = Field(min_length=1)
    page_count: int = Field(default=144, ge=4, le=800)
    interior_style: Optional[str] = Field(default=None, description="Override the inferred style; one of utils.journal_pdf.INTERIOR_STYLES.")


class AutoGeneratePdfsResponse(BaseModel):
    ok: bool
    interior_pdf_url: str
    cover_pdf_url: str
    page_count: int
    interior_style: str


@router.post("/auto-generate-pdfs", response_model=AutoGeneratePdfsResponse)
async def auto_generate_pdfs(req: AutoGeneratePdfsRequest, user: dict = Depends(get_current_user)):
    """Phase 5b — auto-generate a Lulu-compliant interior + cover PDF for a
    journal/notebook draft using its AI-generated cover image.

    Closes the loop from "dream → fulfillable" with zero manual PDF prep:
      1) Locate the product's AI cover image on disk.
      2) Run reportlab to write static/pdfs/interior-<id>.pdf + cover-<id>.pdf.
      3) Return public URLs the admin can paste into make-fulfillable.
    """
    _admin_only(user)
    from pathlib import Path as _Path  # noqa: PLC0415
    from database import db  # noqa: PLC0415
    from utils import journal_pdf  # noqa: PLC0415

    product = await db.products.find_one({"id": req.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    if (product.get("category") or "").lower() not in LULU_CATEGORIES:
        raise HTTPException(400, "Auto-PDF only supports journal/notebook for now.")

    image_url = product.get("image_url") or ""
    if not image_url.startswith("/api/static/"):
        raise HTTPException(400, "Product image must be a Studio-generated static asset.")
    # /api/static/products/foo.png → /app/backend/static/products/foo.png
    rel = image_url[len("/api/static/"):]
    backend_static = _Path(__file__).resolve().parents[1] / "static"
    image_path = backend_static / rel
    if not image_path.exists():
        raise HTTPException(404, f"Cover image not found on disk: {rel}")

    pdfs_dir = backend_static / "pdfs"
    # Decide interior style: request override > stored inference > default
    style = (req.interior_style or product.get("interior_style") or journal_pdf.DEFAULT_INTERIOR_STYLE).strip().lower()
    if style not in journal_pdf.INTERIOR_STYLES:
        logger.info("Unknown interior_style '%s' — falling back to default", style)
        style = journal_pdf.DEFAULT_INTERIOR_STYLE
    try:
        interior_path, cover_path = journal_pdf.generate_pair(
            cover_image_path=image_path,
            output_dir=pdfs_dir,
            product_id=product["id"],
            page_count=req.page_count,
            title=product.get("name", "Birthright Journal"),
            interior_style=style,
        )
    except Exception as ex:
        logger.exception("Auto-PDF generation failed for product %s", product["id"])
        raise HTTPException(500, f"PDF generation failed: {ex}") from ex

    base = (os.environ.get("PRINTFUL_PUBLIC_IMAGE_BASE") or os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")
    if not base:
        raise HTTPException(500, "PUBLIC_APP_URL not configured — cannot share PDFs with Lulu")

    interior_url = f"{base}/api/static/pdfs/{interior_path.name}"
    cover_url = f"{base}/api/static/pdfs/{cover_path.name}"

    # Persist the chosen style on the product for next time
    await db.products.update_one({"id": product["id"]}, {"$set": {"interior_style": style}})

    await log_action(
        db, user, "lulu.auto_generate_pdfs",
        target_type="product", target_id=product["id"],
        metadata={
            "interior_pdf_url": interior_url,
            "cover_pdf_url": cover_url,
            "page_count": req.page_count,
            "interior_style": style,
        },
    )

    return AutoGeneratePdfsResponse(
        ok=True,
        interior_pdf_url=interior_url,
        cover_pdf_url=cover_url,
        page_count=req.page_count,
        interior_style=style,
    )


@router.post("/test-print-job")
async def submit_test_print_job(req: TestPrintJobRequest, user: dict = Depends(get_current_user)):
    """Submit a real (sandbox) print job using this product's stored Lulu config."""
    _admin_only(user)
    from database import db
    product = await db.products.find_one({"id": req.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    if product.get("fulfillable_via") != "lulu":
        raise HTTPException(400, "Product is not linked to Lulu — call make-fulfillable first")
    try:
        result = await lulu.create_print_job(
            contact_email=req.contact_email,
            external_id=f"test-{product['id'][:24]}",
            pod_package_id=product["lulu_pod_package_id"],
            page_count=product["lulu_page_count"],
            title=product.get("name", "Untitled"),
            cover_url=product["lulu_cover_pdf_url"],
            interior_url=product["lulu_interior_pdf_url"],
            shipping_address={
                "name": req.name,
                "street1": req.address1,
                "city": req.city,
                "state_code": req.state_code,
                "postcode": req.postcode,
                "country_code": req.country_code,
                "phone_number": req.phone_number,
            },
        )
    except lulu.LuluError as ex:
        raise HTTPException(502, f"Lulu print job failed: {ex}") from ex
    await log_action(
        db, user, "lulu.test_print_job",
        target_type="product", target_id=product["id"],
        metadata={
            "lulu_print_job_id": result.get("id"),
            "status": (result.get("status") or {}).get("name") if isinstance(result.get("status"), dict) else result.get("status"),
            "env": os.environ.get("LULU_ENV") or "sandbox",
        },
    )
    return {
        "ok": True,
        "lulu_print_job_id": result.get("id"),
        "status": result.get("status"),
        "env": os.environ.get("LULU_ENV") or "sandbox",
    }
