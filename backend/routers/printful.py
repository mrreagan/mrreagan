"""Printful — Phase 2: Admin one-click "Make fulfillable" on AI Studio drafts.

Workflow:
  1) Admin clicks "Make fulfillable on Printful" on a Studio draft card.
  2) Backend looks up the draft's category → default Printful product_id+variant_id.
  3) Optionally fetches base cost from Printful catalog → suggests retail price.
  4) Creates a sync product with the AI-generated image URL as the print file.
  5) Persists printful_sync_product_id + retail price on the products doc.
  6) The product now also displays a "Fulfillable on Printful" badge to admin.

Future phases will wire this to actual order fulfillment.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from models import now_iso
from utils import printful_client as pf
from utils.audit import log_action

logger = logging.getLogger("birthright.printful")
router = APIRouter(prefix="/printful", tags=["printful"])

# ---- Category → Printful default product/variant mapping ----
# Picked sensible neutral defaults. Admin can override per-draft from the UI.
# Source: Printful catalog (May 2026). Re-validate by hitting /products/{id}.
CATEGORY_MAP: dict[str, dict] = {
    "cap":     {"product_id": 252, "variant_id": 8747,  "label": "Yupoong 6606 Retro Trucker (Black)",       "thread_colors": ["#FFFFFF"], "embroidery_placement": "embroidery_front"},
    "tee":     {"product_id": 71,  "variant_id": 4017,  "label": "Bella+Canvas 3001 Unisex Tee (Black/M)",   "thread_colors": None,        "embroidery_placement": None},
    "hoodie":  {"product_id": 146, "variant_id": 5531,  "label": "Gildan 18500 Unisex Hoodie (Black/M)",     "thread_colors": None,        "embroidery_placement": None},
    "mug":     {"product_id": 19,  "variant_id": 1320,  "label": "White Glossy Mug (11oz)",                  "thread_colors": None,        "embroidery_placement": None},
}


# ============ Pydantic ============
class MakeFulfillableRequest(BaseModel):
    product_id: str = Field(min_length=1)
    variant_id_override: Optional[int] = None
    retail_price_override: Optional[float] = Field(default=None, gt=0)
    markup_multiplier: float = Field(default=2.0, ge=1.2, le=5.0)


class MakeFulfillableResponse(BaseModel):
    ok: bool
    sync_product_id: int
    sync_variant_id: int
    base_cost_usd: Optional[float]
    retail_price_usd: float
    printful_label: str


# ============ Helpers ============
def _admin_only(user: dict) -> None:
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")


async def _abs_image_url(image_url: str) -> str:
    """Printful needs a publicly-fetchable URL. Convert relative /api/static/* to absolute."""
    if image_url.startswith(("http://", "https://")):
        return image_url
    # PRINTFUL_PUBLIC_IMAGE_BASE wins (so preview env can point to its own URL),
    # otherwise fall back to PUBLIC_APP_URL (production).
    base = (os.environ.get("PRINTFUL_PUBLIC_IMAGE_BASE") or os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")
    if not base:
        raise HTTPException(500, "PUBLIC_APP_URL not configured — cannot share image with Printful")
    return f"{base}{image_url}"


# ============ Endpoints ============
@router.get("/categories")
async def list_supported_categories(user: dict = Depends(get_current_user)):
    """Return the categories we currently support pushing to Printful."""
    _admin_only(user)
    return [
        {"category": cat, "product_id": cfg["product_id"], "variant_id": cfg["variant_id"], "label": cfg["label"]}
        for cat, cfg in CATEGORY_MAP.items()
    ]


@router.post("/make-fulfillable", response_model=MakeFulfillableResponse)
async def make_fulfillable(req: MakeFulfillableRequest, user: dict = Depends(get_current_user)):
    """Push an AI Studio draft product to Printful as a Sync Product."""
    _admin_only(user)
    from database import db

    product = await db.products.find_one({"id": req.product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    if product.get("printful_sync_product_id"):
        raise HTTPException(400, "Product is already fulfillable on Printful")

    category = (product.get("category") or "").lower()
    if category not in CATEGORY_MAP:
        raise HTTPException(
            400,
            f"Category '{category}' is not yet supported on Printful. Supported: {list(CATEGORY_MAP.keys())}",
        )

    mapping = CATEGORY_MAP[category]
    variant_id = int(req.variant_id_override or mapping["variant_id"])

    image_url = product.get("image_url") or ""
    if not image_url:
        raise HTTPException(400, "Product has no image_url — generate one first")
    file_url = await _abs_image_url(image_url)

    # 1) Base cost discovery
    base_cost = await pf.get_variant_price(mapping["product_id"], variant_id)

    # 2) Retail price decision
    if req.retail_price_override:
        retail_price = float(req.retail_price_override)
    elif base_cost:
        retail_price = pf.suggest_retail_price(base_cost, req.markup_multiplier)
    else:
        raise HTTPException(502, "Could not fetch base cost from Printful — set retail_price_override manually")

    # 3) Create sync product
    try:
        result = await pf.create_sync_product(
            name=product.get("name", "Untitled"),
            variant_id=variant_id,
            file_url=file_url,
            retail_price=f"{retail_price:.2f}",
            external_id=product["id"],
            thread_colors=mapping.get("thread_colors"),
            embroidery_placement=mapping.get("embroidery_placement"),
        )
    except pf.PrintfulError as ex:
        logger.exception("Printful create_sync_product failed for product %s", product["id"])
        raise HTTPException(502, f"Printful error: {ex}") from ex

    sync_product_id = int(result["id"])
    # The create response returns variant count, not the full variant list.
    # Fetch detail to capture the real sync_variant_id.
    sync_variant_id = 0
    try:
        detail = await pf.get_sync_product(sync_product_id)
        svs = detail.get("sync_variants") or []
        if svs:
            sync_variant_id = int(svs[0]["id"])
    except Exception as ex:
        logger.warning("Could not fetch sync_variants for %s: %s", sync_product_id, ex)

    # 4) Persist
    await db.products.update_one(
        {"id": product["id"]},
        {"$set": {
            "printful_sync_product_id": sync_product_id,
            "printful_sync_variant_id": sync_variant_id,
            "printful_variant_id": variant_id,
            "printful_base_cost_usd": base_cost,
            "printful_label": mapping["label"],
            "fulfillable_via": "printful",
            "price": retail_price,
            "fulfillable_at": now_iso(),
        }},
    )

    await log_action(
        db, user, "printful.make_fulfillable",
        target_type="product", target_id=product["id"],
        metadata={
            "sync_product_id": sync_product_id,
            "variant_id": variant_id,
            "base_cost_usd": base_cost,
            "retail_price_usd": retail_price,
        },
    )

    return MakeFulfillableResponse(
        ok=True,
        sync_product_id=sync_product_id,
        sync_variant_id=sync_variant_id,
        base_cost_usd=base_cost,
        retail_price_usd=retail_price,
        printful_label=mapping["label"],
    )


@router.delete("/sync-products/{product_id}")
async def detach_from_printful(product_id: str, user: dict = Depends(get_current_user)):
    """Unlink a Birthright product from Printful (and delete the sync product on their side)."""
    _admin_only(user)
    from database import db
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    sync_id = product.get("printful_sync_product_id")
    if not sync_id:
        raise HTTPException(400, "Product is not linked to Printful")
    try:
        await pf.delete_sync_product(int(sync_id))
    except pf.PrintfulError as ex:
        logger.warning("Printful delete failed (continuing local unlink): %s", ex)
    await db.products.update_one(
        {"id": product_id},
        {"$unset": {
            "printful_sync_product_id": "",
            "printful_sync_variant_id": "",
            "printful_variant_id": "",
            "printful_base_cost_usd": "",
            "printful_label": "",
            "fulfillable_via": "",
            "fulfillable_at": "",
        }},
    )
    await log_action(
        db, user, "printful.detach",
        target_type="product", target_id=product_id,
        metadata={"sync_product_id": sync_id},
    )
    return {"ok": True}
