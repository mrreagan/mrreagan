"""Product / Storefront routes."""
import base64
import logging
import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from models import ProductCreate, ProductUpdate, gen_id, now_iso
from auth_utils import require_roles, get_current_user_optional

logger = logging.getLogger("birthright.products")
router = APIRouter(prefix="/products", tags=["products"])


class RegenerateImageRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=2000)


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or gen_id()[:8]


@router.get("")
async def list_products(
    type: Optional[str] = None,
    workshop_id: Optional[str] = None,
    category: Optional[str] = None,
    vendor_id: Optional[str] = None,
):
    """Public product listing.

    Vendor products with moderation_status != 'active' are HIDDEN from the
    public storefront. Foundation products (is_vendor_product != True) are
    always shown (admins curate them via /admin/products).
    """
    from database import db
    query: dict = {
        # Exclude vendor products that are not currently active.
        "$or": [
            {"is_vendor_product": {"$ne": True}},
            {"is_vendor_product": True, "moderation_status": "active"},
        ],
    }
    if type:
        query["type"] = type
    if workshop_id:
        query["workshop_id"] = workshop_id
    if category:
        query["category"] = category
    if vendor_id:
        query["vendor_partner_id"] = vendor_id
    products = await db.products.find(query, {"_id": 0}).to_list(1000)
    return products


def _is_vendor_product_hidden_from(p: dict, user: Optional[dict]) -> bool:
    """Vendor products with non-active moderation are hidden from the public.
    Admins and the vendor owner can still see them."""
    if not p.get("is_vendor_product"):
        return False
    if p.get("moderation_status") == "active":
        return False
    if user and user.get("role") == "admin":
        return False
    if user and user.get("id") == p.get("vendor_user_id"):
        return False
    return True


async def _resolve_material_lock(p: dict, user: Optional[dict], db) -> tuple[bool, str]:
    """Return (locked, reason) for a workshop_material product.
    Non-materials are never locked."""
    if p["type"] != "workshop_material" or not p.get("workshop_id"):
        return False, ""
    if not user:
        return True, "Sign in and register for the workshop to purchase materials."
    if user["role"] == "admin":
        return False, ""
    reg = await db.registrations.find_one(
        {
            "workshop_id": p["workshop_id"],
            "user_id": user["id"],
            "payment_status": "paid",
        }
    )
    if reg:
        return False, ""
    return True, "Only registered workshop participants can purchase these materials."


@router.get("/{product_id}")
async def get_product(product_id: str, user: Optional[dict] = Depends(get_current_user_optional)):
    from database import db
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    if _is_vendor_product_hidden_from(p, user):
        raise HTTPException(status_code=404, detail="Product not found")
    locked, lock_reason = await _resolve_material_lock(p, user, db)
    p["locked"] = locked
    if locked:
        p["lock_reason"] = lock_reason
    return p


@router.post("")
async def create_product(data: ProductCreate, user: dict = Depends(require_roles("admin"))):
    from database import db
    product = {**data.model_dump(), "id": gen_id(), "created_at": now_iso()}
    await db.products.insert_one(product)
    product.pop("_id", None)
    if product.get("image_url"):
        from utils.image_caption_agent import schedule_caption_if_image_changed
        schedule_caption_if_image_changed(
            db, "products", product["id"],
            old_image_url=None, new_image_url=product["image_url"],
        )
    return product


@router.put("/{product_id}")
async def update_product(product_id: str, updates: ProductUpdate, user: dict = Depends(require_roles("admin"))):
    from database import db
    update_data = updates.model_dump(exclude_none=True)
    # Snapshot the previous image URL so we can detect a swap and trigger
    # the AI caption agent for just this one record.
    prev = await db.products.find_one({"id": product_id}, {"_id": 0, "image_url": 1})
    if update_data:
        await db.products.update_one({"id": product_id}, {"$set": update_data})
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    if p and "image_url" in update_data:
        from utils.image_caption_agent import schedule_caption_if_image_changed
        schedule_caption_if_image_changed(
            db, "products", product_id,
            old_image_url=(prev or {}).get("image_url"),
            new_image_url=p.get("image_url"),
        )
    return p


@router.delete("/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    await db.products.delete_one({"id": product_id})
    return {"success": True}


# ─── Founder Collection carousel admin ──────────────────────────────────
# Dedicated endpoint pair so the admin doesn't have to dig through the
# product list to swap who's featured. Up to 3 ranked slots.

@router.get("/founder-carousel/manage", tags=["admin"])
async def list_founder_carousel(user: dict = Depends(require_roles("admin"))):
    """Return every founder_collection product split into 'featured'
    (rank 1–3, in rank order) + 'available' (everything else)."""
    from database import db
    rows = await db.products.find(
        {"collection": "founder_collection"},
        {"_id": 0},
    ).to_list(200)
    featured = sorted(
        [r for r in rows if r.get("carousel_rank") in (1, 2, 3)],
        key=lambda r: r.get("carousel_rank", 99),
    )
    featured_ids = {r["id"] for r in featured}
    available = sorted(
        [r for r in rows if r["id"] not in featured_ids],
        key=lambda r: r.get("name", ""),
    )
    return {"featured": featured, "available": available}


class CarouselAssignment(BaseModel):
    """Body of POST /products/founder-carousel/manage — assigns one
    product to a specific carousel slot (1, 2, or 3) and frees any
    other product that previously held that slot."""
    product_id: str
    rank: int = Field(ge=1, le=3)


@router.post("/founder-carousel/manage", tags=["admin"])
async def assign_founder_carousel(
    body: CarouselAssignment,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    # Free the slot first — whoever held it loses their rank.
    await db.products.update_many(
        {"carousel_rank": body.rank, "id": {"$ne": body.product_id}},
        {"$set": {"carousel_rank": None}},
    )
    r = await db.products.update_one(
        {"id": body.product_id, "collection": "founder_collection"},
        {"$set": {"carousel_rank": body.rank}},
    )
    if r.matched_count == 0:
        raise HTTPException(
            404,
            "Product not found, or it isn't in collection=founder_collection",
        )
    return {"ok": True}


class CarouselUnassign(BaseModel):
    product_id: str


@router.delete("/founder-carousel/manage", tags=["admin"])
async def unassign_founder_carousel(
    body: CarouselUnassign,
    user: dict = Depends(require_roles("admin")),
):
    """Remove a product from the carousel (it stays in the full
    collection view at /equip/collection/founder)."""
    from database import db
    r = await db.products.update_one(
        {"id": body.product_id},
        {"$set": {"carousel_rank": None}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Product not found")
    return {"ok": True}


@router.post("/{product_id}/regenerate-image")
async def regenerate_image(
    product_id: str,
    data: RegenerateImageRequest,
    user: dict = Depends(require_roles("admin")),
):
    """Generate a fresh mockup with Gemini Nano Banana, save to /api/static/products/<slug>.png,
    and update the product's image_url."""
    from database import db
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")

    slug = product.get("slug") or _slugify(product["name"])
    # Append a short stable suffix from product.id so two products with the same
    # name-derived slug don't overwrite each other's PNGs on disk.
    file_stem = f"{slug}-{product['id'][:8]}" if not product.get("slug") else slug

    try:
        from utils.image_generator import generate_product_image
        new_url = await generate_product_image(
            prompt=data.prompt,
            file_stem=file_stem,
            session_id=f"regen-{product_id}",
        )
    except Exception as e:
        logger.error(f"image regen failed for {product_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Image generation failed: {e}")

    await db.products.update_one(
        {"id": product_id},
        {"$set": {"image_url": new_url, "slug": slug}},
    )
    updated = await db.products.find_one({"id": product_id}, {"_id": 0})
    # Auto-caption the freshly generated image so the help assistant can
    # describe it without waiting for a manual /admin/image-captions pass.
    from utils.image_caption_agent import schedule_caption_if_image_changed
    schedule_caption_if_image_changed(
        db, "products", product_id,
        old_image_url=product.get("image_url"),
        new_image_url=new_url,
    )
    return updated
