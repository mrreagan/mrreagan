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

from fastapi import APIRouter, Depends, HTTPException, Request
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
    # Pocket-size paperback journal — intended for the daily-carry market
    # (purse / coat pocket / glove box). Page count tuned smaller so the
    # book stays slim and pocketable.
    "pocket_journal_5x8_bw_pb": {
        "pod_package_id": "0500X0800BWSTDPB060UW444MXX",
        "label": "Pocket journal · 5×8 · paperback · B&W · 60# cream",
        "default_page_count": 96,
        "applies_to": ["journal", "notebook"],
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


async def _can_fulfill(db, user: dict, product: dict) -> tuple[bool, str]:
    """Vendor self-service POD permission gate.

    Allow if:
      - user is admin, OR
      - user is the original vendor creator AND the draft is still pending_review
        / changes_requested (not yet active and not rejected).
    Returns (allowed, actor_role).
    """
    if user.get("role") == "admin":
        return True, "admin"
    if not product.get("is_vendor_product"):
        return False, "non-vendor"
    if product.get("vendor_user_id") != user["id"] and product.get("created_by") != user["id"]:
        return False, "not-owner"
    if not product.get("studio_draft"):
        return False, "not-draft"
    if product.get("moderation_status") not in ("pending_review", "changes_requested"):
        return False, "not-mutable"
    return True, "vendor"


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
    # Open to any authenticated user — vendors need this for their Studio.
    return [
        {"key": k, **v}
        for k, v in POD_PRESETS.items()
    ]


class PresetValidationRow(BaseModel):
    key: str
    pod_package_id: str
    label: str
    page_count: int
    ok: bool
    base_cost_usd: Optional[float] = None
    suggested_retail_usd: Optional[float] = None
    error: Optional[str] = None


@router.post("/validate-presets")
async def validate_presets(user: dict = Depends(get_current_user)):
    """Run a fresh cost-calc against every preset in the current LULU_ENV.

    Used before flipping LULU_ENV=production — confirms each `pod_package_id`
    actually resolves on the live Lulu account before customers see any books.
    """
    _admin_only(user)
    env = os.environ.get("LULU_ENV") or "sandbox"
    rows: list[PresetValidationRow] = []
    for key, cfg in POD_PRESETS.items():
        page_count = int(cfg["default_page_count"])
        try:
            raw = await lulu.calculate_cost(
                pod_package_id=cfg["pod_package_id"],
                page_count=page_count,
                quantity=1,
            )
            summary = lulu.summarise_cost(raw)
            rows.append(PresetValidationRow(
                key=key, pod_package_id=cfg["pod_package_id"], label=cfg["label"],
                page_count=page_count, ok=True,
                base_cost_usd=summary["base_cost_excl_tax_usd"],
                suggested_retail_usd=lulu.suggest_retail_price(summary["base_cost_excl_tax_usd"]),
            ))
        except lulu.LuluError as ex:
            rows.append(PresetValidationRow(
                key=key, pod_package_id=cfg["pod_package_id"], label=cfg["label"],
                page_count=page_count, ok=False, error=str(ex)[:300],
            ))
    return {"env": env, "results": [r.model_dump() for r in rows]}


@router.get("/interior-styles")
async def list_interior_styles(user: dict = Depends(get_current_user)):
    """Return the available interior page styles (for admin override dropdown)."""
    # Open to any authenticated user — vendors need this for their Studio.
    from utils import journal_pdf  # noqa: PLC0415
    return [
        {"key": k, "description": v}
        for k, v in journal_pdf.INTERIOR_STYLES.items()
    ]


@router.post("/cost-preview", response_model=CostPreviewResponse)
async def cost_preview(req: CostPreviewRequest, user: dict = Depends(get_current_user)):
    """Hit Lulu's cost calculator. Returns a cost breakdown + a suggested retail price."""
    # Open to any authenticated user — vendors need to preview cost on their drafts.
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
      1) Look up the product, ensure caller can fulfill it (admin OR draft owner),
         and that it's a paper-goods category we support on Lulu.
      2) Call Lulu's cost calculator to confirm config is valid + capture base cost.
      3) Compute retail price (override or 2× rounded to $.95).
      4) Write printful-style fulfillment fields on the product doc.
    """
    from database import db

    product = await db.products.find_one({"id": req.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    allowed, actor_role = await _can_fulfill(db, user, product)
    if not allowed:
        raise HTTPException(403, f"You can't make this product fulfillable ({actor_role})")
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
        db, user, f"lulu.make_fulfillable.{actor_role}",
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
    from database import db
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    allowed, actor_role = await _can_fulfill(db, user, product)
    if not allowed:
        raise HTTPException(403, f"You can't unlink this product ({actor_role})")
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
        db, user, f"lulu.detach.{actor_role}",
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
    page_count: Optional[int] = Field(default=None, ge=4, le=800, description="Override; if omitted, uses the AI-suggested page count stored on the product (or 144).")
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
    from pathlib import Path as _Path  # noqa: PLC0415
    from database import db  # noqa: PLC0415
    from utils import journal_pdf  # noqa: PLC0415

    product = await db.products.find_one({"id": req.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    allowed, actor_role = await _can_fulfill(db, user, product)
    if not allowed:
        raise HTTPException(403, f"You can't generate PDFs for this product ({actor_role})")
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
    # Decide page count: request override > stored AI suggestion > default 144
    page_count = int(
        req.page_count
        if req.page_count is not None
        else (product.get("lulu_page_count_suggested") or 144)
    )
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
            page_count=page_count,
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

    # Persist the chosen style + page count on the product for next time
    await db.products.update_one(
        {"id": product["id"]},
        {"$set": {"interior_style": style, "lulu_page_count_suggested": page_count}},
    )

    await log_action(
        db, user, f"lulu.auto_generate_pdfs.{actor_role}",
        target_type="product", target_id=product["id"],
        metadata={
            "interior_pdf_url": interior_url,
            "cover_pdf_url": cover_url,
            "page_count": page_count,
            "interior_style": style,
        },
    )

    return AutoGeneratePdfsResponse(
        ok=True,
        interior_pdf_url=interior_url,
        cover_pdf_url=cover_url,
        page_count=page_count,
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


# ============ Webhook subscriptions (Lulu → Birthright) ============
def _webhook_token() -> str:
    tok = (os.environ.get("LULU_WEBHOOK_TOKEN") or "").strip()
    if not tok:
        raise HTTPException(500, "LULU_WEBHOOK_TOKEN is not configured on the server")
    return tok


def _public_webhook_url() -> str:
    base = (os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")
    if not base:
        raise HTTPException(500, "PUBLIC_APP_URL is not configured")
    return f"{base}/api/lulu/webhook/{_webhook_token()}"


class SubscribeWebhookResponse(BaseModel):
    ok: bool
    id: str
    url: str
    topics: list[str]
    env: str


@router.post("/webhooks", response_model=SubscribeWebhookResponse)
async def subscribe_webhook(user: dict = Depends(get_current_user)):
    """Register our webhook URL with Lulu so PRINT_JOB_STATUS_CHANGED events flow in."""
    _admin_only(user)
    url = _public_webhook_url()
    try:
        result = await lulu.create_webhook(url=url)
    except lulu.LuluError as ex:
        # Lulu returns 400 with a "non_field_errors" array when the URL is already
        # subscribed. Surface a friendly hint.
        raise HTTPException(502, f"Lulu rejected webhook subscription: {ex}") from ex
    from database import db
    await log_action(
        db, user, "lulu.webhook_subscribe",
        target_type="lulu_webhook", target_id=str(result.get("id") or ""),
        metadata={"url": url, "env": os.environ.get("LULU_ENV") or "sandbox"},
    )
    return SubscribeWebhookResponse(
        ok=True,
        id=str(result.get("id") or ""),
        url=str(result.get("url") or url),
        topics=list(result.get("topics") or ["PRINT_JOB_STATUS_CHANGED"]),
        env=(os.environ.get("LULU_ENV") or "sandbox"),
    )


@router.get("/webhooks")
async def list_lulu_webhooks(user: dict = Depends(get_current_user)):
    """List Lulu-side webhook subscriptions for this account."""
    _admin_only(user)
    try:
        subs = await lulu.list_webhooks()
    except lulu.LuluError as ex:
        raise HTTPException(502, f"Lulu list webhooks failed: {ex}") from ex
    return {
        "expected_url": _public_webhook_url(),
        "env": (os.environ.get("LULU_ENV") or "sandbox"),
        "subscriptions": subs,
    }


@router.delete("/webhooks/{webhook_id}")
async def delete_lulu_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    _admin_only(user)
    try:
        await lulu.delete_webhook(webhook_id)
    except lulu.LuluError as ex:
        raise HTTPException(502, f"Lulu delete webhook failed: {ex}") from ex
    from database import db
    await log_action(
        db, user, "lulu.webhook_delete",
        target_type="lulu_webhook", target_id=webhook_id,
    )
    return {"ok": True}


@router.post("/webhooks/{webhook_id}/test")
async def test_lulu_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    """Ask Lulu to fire a dummy PRINT_JOB_STATUS_CHANGED at our endpoint."""
    _admin_only(user)
    try:
        return await lulu.send_webhook_test(webhook_id)
    except lulu.LuluError as ex:
        raise HTTPException(502, f"Lulu test webhook failed: {ex}") from ex


# ---- Public receiver (Lulu → us) ----
@router.post("/webhook/{token}")
async def receive_lulu_webhook(token: str, request: Request):
    """Public endpoint Lulu posts status updates to. Secured by a long shared
    token in the URL path (configured via LULU_WEBHOOK_TOKEN).

    Lulu's payload is the print-job resource itself; we route it through
    order_dispatch.apply_lulu_webhook which finds the matching order +
    persists tracking + status updates.
    """
    expected = _webhook_token()
    # constant-time compare to keep timing-attacks off the table
    import hmac  # noqa: PLC0415
    if not hmac.compare_digest(token, expected):
        raise HTTPException(401, "Invalid webhook token")
    try:
        payload = await request.json()
    except Exception as ex:
        raise HTTPException(400, f"Invalid JSON: {ex}") from ex
    if not isinstance(payload, dict):
        raise HTTPException(400, "Payload must be a JSON object")
    from database import db
    from utils.order_dispatch import apply_lulu_webhook  # noqa: PLC0415
    result = await apply_lulu_webhook(db, payload)
    if not result.get("matched"):
        # Acknowledge with 200 so Lulu doesn't retry forever, but log loudly.
        logger.warning(
            "lulu webhook: no order matched (reason=%s job=%s)",
            result.get("reason"), result.get("job_id"),
        )
    return {"received": True, **result}
