"""Product / Storefront routes."""
import base64
import logging
import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from models import ProductCreate, Product, ProductUpdate, gen_id, now_iso
from auth_utils import get_current_user, require_roles, get_current_user_optional

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
    return product


@router.put("/{product_id}")
async def update_product(product_id: str, updates: ProductUpdate, user: dict = Depends(require_roles("admin"))):
    from database import db
    update_data = updates.model_dump(exclude_none=True)
    if update_data:
        await db.products.update_one({"id": product_id}, {"$set": update_data})
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    return p


@router.delete("/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    await db.products.delete_one({"id": product_id})
    return {"success": True}


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

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image library unavailable: {e}")

    slug = product.get("slug") or _slugify(product["name"])
    # Append a short stable suffix from product.id so two products with the same
    # name-derived slug don't overwrite each other's PNGs on disk.
    file_stem = f"{slug}-{product['id'][:8]}" if not product.get("slug") else slug
    full_prompt = (
        data.prompt.strip()
        + " Brand palette: muted teal #476B6B, gold #C9A961, cream #FAF8F5. "
        "Square 1:1. Editorial product photography on warm cream linen, soft natural light. "
        "No printed brand name, no logo text, no human faces, no watermark."
    )

    try:
        chat = (
            LlmChat(
                api_key=api_key,
                session_id=f"regen-{product_id}",
                system_message="You generate clean editorial e-commerce product mockup photography.",
            )
            .with_model("gemini", "gemini-3.1-flash-image-preview")
            .with_params(modalities=["image", "text"])
        )
        _, images = await chat.send_message_multimodal_response(UserMessage(text=full_prompt))
        if not images:
            raise HTTPException(status_code=502, detail="No image returned from generator")
        static_dir = Path(__file__).resolve().parent.parent / "static" / "products"
        static_dir.mkdir(parents=True, exist_ok=True)
        out = static_dir / f"{file_stem}.png"
        out.write_bytes(base64.b64decode(images[0]["data"]))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"image regen failed for {product_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Image generation failed: {e}")

    new_url = f"/api/static/products/{file_stem}.png"
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"image_url": new_url, "slug": slug}},
    )
    updated = await db.products.find_one({"id": product_id}, {"_id": 0})
    return updated
