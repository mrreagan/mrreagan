"""Artist partnership — patronage payouts, tier resolution, admin tools.

Three responsibilities:

  1. /api/partner/me/artist-tier
     Public-to-the-caller tier summary for the signed-in artist's dashboard.

  2. /api/admin/artist-payouts ...
     Foundation operator's view of pending patronage payouts (artist gets
     list_price on each paid gallery line item; Foundation kept the 20%
     hospitality markup).

  3. /api/admin/artist-tier-overrides ...
     Manual tier placement for honorary or contractual exceptions.

The actual hook that creates payout rows fires from checkout (see
checkout._create_order_from_txn -> _record_artist_patronage_payouts) so
this router never has to. Reading is free; writing is admin-gated.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user, require_roles
from models import gen_id, now_iso
from utils.artist_tier import (
    TIERS,
    marginal_outbound_owed,
    resolve_artist_tier,
)

logger = logging.getLogger("birthright.artist_partnership")

my_router = APIRouter(prefix="/partner/me", tags=["artist-partnership"])
public_router = APIRouter(prefix="/partner/artist", tags=["artist-partnership-public"])
admin_router = APIRouter(prefix="/admin/artist", tags=["artist-partnership-admin"])


# ============ PUBLIC — tier table for the clarity page ============
@public_router.get("/tier-table")
async def public_tier_table():
    """Public — exposes the tier ladder so the 'Artist Partnership Terms'
    page can render the exact numbers the Foundation operates on. Clarity
    before commitment: the artist must be able to see this before signing
    up."""
    return {
        "tiers": [
            {
                "key": t["key"],
                "label": t["label"],
                "icon": t["icon"],
                "basis_lo": t["lo"],
                "basis_hi": t["hi"],
                "inbound_pct": t["inbound_pct"],
                "outbound_pct": t["outbound_pct"],
            }
            for t in TIERS
        ],
        "on_site_patronage_markup_pct": 20.0,
        "attribution": {
            "inbound": {
                "cookie_days": 30,
                "scope": "first_purchase_only",
                "model": "last_click",
            },
            "outbound": {
                "claim_window_days": 30,
                "scope": "first_purchase_only",
                "reporting_cadence": "quarterly",
                "model": "self_attested",
            },
        },
        "basis_definition": (
            "Trailing 12 months of Birthright-attributed gross revenue: "
            "the artist's gallery sales on Birthright at list price PLUS "
            "their self-reported off-site sales tagged with via=birthright. "
            "Recomputed monthly. Foundation only ever takes a share of "
            "what Foundation contributed to."
        ),
        "transitions": (
            "Tier changes take effect on the 1st of the following month. "
            "Tiers can rise or fall; downward protection is automatic "
            "during slower periods."
        ),
        "outbound_calculation": (
            "Outbound uses MARGINAL brackets: only the revenue above each "
            "threshold pays that tier's rate. Crossing a threshold by $1 "
            "never re-taxes everything below it."
        ),
    }


# ============ ARTIST DASHBOARD ============
@my_router.get("/artist-tier")
async def my_artist_tier(user: dict = Depends(get_current_user)):
    """Authenticated artist sees their current tier + basis + runway."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": "artist", "status": "active"},
        {"_id": 0},
    )
    if not profile:
        raise HTTPException(403, "You need an approved Artist partner profile.")
    summary = await resolve_artist_tier(db, user["id"])
    return summary


@my_router.get("/artist-payouts")
async def my_patronage_payouts(user: dict = Depends(get_current_user)):
    """Artist sees their own pending + paid patronage payouts."""
    from database import db
    rows = await db.artist_sale_payouts.find(
        {"artist_user_id": user["id"]}, {"_id": 0},
    ).sort("created_at", -1).to_list(500)
    pending = sum(r["list_price"] for r in rows if r["status"] == "pending")
    paid = sum(r["list_price"] for r in rows if r["status"] == "paid")
    return {
        "summary": {
            "count": len(rows),
            "lifetime_total": round(pending + paid, 2),
            "pending_payout": round(pending, 2),
            "paid_to_date": round(paid, 2),
        },
        "recent": rows[:100],
    }


# ============ ADMIN — patronage payouts ============
@admin_router.get("/payouts")
async def admin_list_payouts(
    status: Optional[Literal["pending", "paid", "cancelled"]] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    q = {}
    if status:
        q["status"] = status
    rows = await db.artist_sale_payouts.find(q, {"_id": 0}) \
        .sort("created_at", -1).to_list(2000)
    return {
        "count": len(rows),
        "total_pending": round(
            sum(r["list_price"] for r in rows if r["status"] == "pending"), 2),
        "total_paid": round(
            sum(r["list_price"] for r in rows if r["status"] == "paid"), 2),
        "rows": rows,
    }


class MarkPaid(BaseModel):
    payout_method: str = Field(min_length=2, max_length=80)
    payout_reference: str = Field(min_length=2, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=2000)


@admin_router.post("/payouts/{payout_id}/mark-paid")
async def admin_mark_paid(
    payout_id: str,
    data: MarkPaid,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    p = await db.artist_sale_payouts.find_one({"id": payout_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Payout not found")
    if p["status"] == "paid":
        raise HTTPException(400, "Already marked paid")
    await db.artist_sale_payouts.update_one(
        {"id": payout_id},
        {"$set": {
            "status": "paid",
            "paid_at": now_iso(),
            "paid_by_admin": user["email"],
            "payout_method": data.payout_method,
            "payout_reference": data.payout_reference,
            "notes": data.notes,
        }},
    )
    return {"ok": True}


# ============ ADMIN — tier overrides ============
class TierOverride(BaseModel):
    user_id: str
    tier_key: Literal[
        "emerging", "sustaining", "established", "thriving", "flourishing"
    ]
    reason: str = Field(min_length=4, max_length=500)


@admin_router.get("/tier-overrides")
async def admin_list_overrides(user: dict = Depends(require_roles("admin"))):
    from database import db
    rows = await db.artist_tier_overrides.find(
        {"active": True}, {"_id": 0},
    ).to_list(500)
    return rows


@admin_router.post("/tier-overrides")
async def admin_create_override(
    data: TierOverride,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    # Mark any existing override as inactive (audit trail preserved).
    await db.artist_tier_overrides.update_many(
        {"user_id": data.user_id, "active": True},
        {"$set": {"active": False, "deactivated_at": now_iso(),
                   "deactivated_by": user["email"]}},
    )
    doc = {
        "id": gen_id(),
        "user_id": data.user_id,
        "tier_key": data.tier_key,
        "reason": data.reason,
        "active": True,
        "created_at": now_iso(),
        "created_by": user["email"],
    }
    await db.artist_tier_overrides.insert_one(dict(doc))
    return {"ok": True, "id": doc["id"]}


# ============ Patronage payout helper (called from checkout) ============
async def record_patronage_payouts(db, order: dict) -> list[str]:
    """For each paid line item flagged is_gallery_artwork=True, insert one
    pending payout row. Idempotent on (order_id, product_id).

    Returns the list of inserted payout IDs.
    """
    inserted: list[str] = []
    items = order.get("items") or []
    if not items:
        return inserted
    # Find which line items are gallery artworks.
    pids = [li.get("product_id") for li in items if li.get("product_id")]
    if not pids:
        return inserted
    products = await db.products.find(
        {"id": {"$in": pids}, "is_gallery_artwork": True},
        {"_id": 0, "id": 1, "name": 1, "image_url": 1,
         "gallery_artist_user_id": 1, "gallery_artist_name": 1,
         "price": 1, "edition": 1, "dimensions": 1, "medium": 1},
    ).to_list(len(pids) + 1)
    by_id = {p["id"]: p for p in products}

    GALLERY_MARKUP_PCT = 0.20  # constant hospitality fee on top
    for li in items:
        prod = by_id.get(li.get("product_id"))
        if not prod:
            continue
        # Idempotency.
        exists = await db.artist_sale_payouts.find_one(
            {"order_id": order["id"], "product_id": prod["id"]},
            {"_id": 0, "id": 1},
        )
        if exists:
            continue
        qty = int(li.get("quantity") or 1)
        list_price = float(prod.get("price") or li.get("price") or 0) * qty
        markup = round(list_price * GALLERY_MARKUP_PCT, 2)
        doc = {
            "id": gen_id(),
            "order_id": order["id"],
            "product_id": prod["id"],
            "artist_user_id": prod.get("gallery_artist_user_id"),
            "artist_name": prod.get("gallery_artist_name"),
            "artwork_name": prod.get("name"),
            "artwork_image_url": prod.get("image_url"),
            "edition": prod.get("edition"),
            "dimensions": prod.get("dimensions"),
            "medium": prod.get("medium"),
            "quantity": qty,
            "list_price": round(list_price, 2),
            "foundation_markup": markup,
            "total_paid_by_buyer": round(list_price + markup, 2),
            "buyer_user_id": order.get("user_id"),
            "buyer_email": order.get("email"),
            "shipping_address": order.get("shipping_address"),
            "status": "pending",
            "created_at": now_iso(),
            "paid_at": None,
            "paid_by_admin": None,
            "payout_method": None,
            "payout_reference": None,
            "notes": None,
        }
        await db.artist_sale_payouts.insert_one(dict(doc))
        inserted.append(doc["id"])
    return inserted
