"""Vendor autonomous catalog (Phase 6B.4).

Vendors with an active 'vendor' PartnerProfile can CRUD their own products.
Auto-publish, but admin can flag or unpublish at any time.

Endpoints:
  GET    /api/vendor/products              — caller's own products (any status)
  POST   /api/vendor/products              — create (auto-published)
  PUT    /api/vendor/products/{id}         — update own
  DELETE /api/vendor/products/{id}         — delete own (only if not yet sold)
  GET    /api/admin/vendor-products        — list ALL vendor products (status filter)
  POST   /api/admin/vendor-products/{id}/flag      — flag w/ note
  POST   /api/admin/vendor-products/{id}/unflag
  POST   /api/admin/vendor-products/{id}/unpublish — admin takedown
  POST   /api/admin/vendor-products/{id}/restore   — undo takedown
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user, require_roles
from models import VendorProductCreate, VendorProductUpdate, VendorModerationAction, gen_id, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.vendor_catalog")

vendor_router = APIRouter(prefix="/vendor/products", tags=["vendor-catalog"])
admin_router = APIRouter(prefix="/admin/vendor-products", tags=["vendor-catalog-admin"])


# ============ HELPERS ============

async def _get_active_vendor_profile(db, user_id: str) -> dict:
    """Return caller's active vendor PartnerProfile or raise 403."""
    profile = await db.partner_profiles.find_one(
        {"user_id": user_id, "partner_type": "vendor", "status": "active"},
        {"_id": 0},
    )
    if not profile:
        raise HTTPException(
            status_code=403,
            detail="You need an approved vendor partner profile to manage products. Apply at /partners/apply.",
        )
    return profile


async def _ensure_owner_or_404(db, product_id: str, user_id: str) -> dict:
    """Return the product if the caller owns it. 404 otherwise (no enumeration)."""
    p = await db.products.find_one({"id": product_id, "vendor_user_id": user_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p


# ============ VENDOR ENDPOINTS ============

@vendor_router.get("")
async def list_my_vendor_products(user: dict = Depends(get_current_user)):
    """All products the caller has created (any moderation status)."""
    from database import db
    products = await db.products.find(
        {"vendor_user_id": user["id"], "is_vendor_product": True},
        {"_id": 0},
    ).sort("created_at", -1).to_list(1000)
    return products


@vendor_router.post("")
async def create_vendor_product(
    data: VendorProductCreate,
    user: dict = Depends(get_current_user),
):
    from database import db
    profile = await _get_active_vendor_profile(db, user["id"])
    # Vendors typically want their brand on the listing, not their personal name.
    meta = profile.get("meta") or {}
    vendor_name = (meta.get("business_name") or "").strip() or profile.get("display_name") or ""

    product = {
        "id": gen_id(),
        "name": data.name.strip(),
        "description": data.description.strip(),
        "price": float(data.price),
        "type": "merch",
        "workshop_id": None,
        "image_url": (data.image_url or "").strip(),
        "inventory": 100,  # print-on-demand / infinite per product decision
        "category": (data.category or "general").strip().lower() or "general",
        "is_vendor_product": True,
        "vendor_partner_id": profile["id"],
        "vendor_user_id": user["id"],
        "vendor_name": vendor_name,
        "vendor_slug": profile.get("slug"),
        "moderation_status": "active",
        "moderation_note": None,
        "created_at": now_iso(),
    }
    await db.products.insert_one(dict(product))
    await log_action(
        db, user, "vendor_product.create",
        target_type="product", target_id=product["id"],
        metadata={"vendor_partner_id": profile["id"], "name": product["name"]},
    )
    return product


@vendor_router.put("/{product_id}")
async def update_vendor_product(
    product_id: str,
    data: VendorProductUpdate,
    user: dict = Depends(get_current_user),
):
    from database import db
    existing = await _ensure_owner_or_404(db, product_id, user["id"])
    if existing["moderation_status"] == "unpublished":
        raise HTTPException(
            status_code=400,
            detail="This product was unpublished by an admin. Contact support to restore it before editing.",
        )
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return existing
    # Light normalization
    if "name" in updates:
        updates["name"] = updates["name"].strip()
    if "description" in updates:
        updates["description"] = updates["description"].strip()
    if "category" in updates:
        updates["category"] = (updates["category"] or "general").strip().lower() or "general"
    if "price" in updates:
        updates["price"] = float(updates["price"])
    await db.products.update_one({"id": product_id}, {"$set": updates})
    await log_action(
        db, user, "vendor_product.update",
        target_type="product", target_id=product_id,
        metadata={"fields": list(updates.keys())},
    )
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    return p


@vendor_router.delete("/{product_id}")
async def delete_vendor_product(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    from database import db
    existing = await _ensure_owner_or_404(db, product_id, user["id"])
    # Soft-prevent deletion if there are any successful orders for this product.
    # (Required for accurate reporting + payout history.)
    sold = await db.orders.count_documents({"items.product_id": product_id, "status": "paid"})
    if sold > 0:
        raise HTTPException(
            status_code=400,
            detail="This product has paid orders — unpublish it instead of deleting.",
        )
    await db.products.delete_one({"id": product_id})
    await log_action(
        db, user, "vendor_product.delete",
        target_type="product", target_id=product_id,
        metadata={"name": existing.get("name")},
    )
    return {"success": True}


# ============ ADMIN ENDPOINTS ============

@admin_router.get("")
async def admin_list_vendor_products(
    status: Optional[str] = Query(default=None, description="active|flagged|unpublished"),
    vendor_user_id: Optional[str] = None,
    limit: int = Query(default=500, ge=1, le=2000),
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {"is_vendor_product": True}
    if status:
        query["moderation_status"] = status
    if vendor_user_id:
        query["vendor_user_id"] = vendor_user_id
    rows = await db.products.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return rows


async def _set_moderation(db, product_id: str, status: str, note: str, actor: dict, action: str) -> dict:
    p = await db.products.find_one({"id": product_id, "is_vendor_product": True})
    if not p:
        raise HTTPException(status_code=404, detail="Vendor product not found")
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"moderation_status": status, "moderation_note": note or None}},
    )
    await log_action(
        db, actor, action, target_type="product", target_id=product_id,
        metadata={"new_status": status, "note": note, "vendor_user_id": p.get("vendor_user_id")},
    )
    return await db.products.find_one({"id": product_id}, {"_id": 0})


@admin_router.post("/{product_id}/flag")
async def admin_flag_product(
    product_id: str,
    data: VendorModerationAction,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    return await _set_moderation(db, product_id, "flagged", (data.moderation_note or "").strip(), user, "vendor_product.flag")


@admin_router.post("/{product_id}/unflag")
async def admin_unflag_product(
    product_id: str,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    return await _set_moderation(db, product_id, "active", "", user, "vendor_product.unflag")


@admin_router.post("/{product_id}/unpublish")
async def admin_unpublish_product(
    product_id: str,
    data: VendorModerationAction,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    return await _set_moderation(db, product_id, "unpublished", (data.moderation_note or "").strip(), user, "vendor_product.unpublish")


@admin_router.post("/{product_id}/restore")
async def admin_restore_product(
    product_id: str,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    return await _set_moderation(db, product_id, "active", "", user, "vendor_product.restore")
