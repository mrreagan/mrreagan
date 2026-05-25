"""Featured-Partner Showcase — v1.11.0 Step 4.

Self-serve paid featuring: a partner buys a 30-day featured slot via Stripe. On
payment success the partner's `featured_until` is set to `now + 30 days`. Admin
can revoke or grant for free at any time. The public `/featured` page returns
currently-featured partners in random shuffle order.

Schema (existing on partner_profiles, set in v1.11.0 step 1):
  featured_until                ISO datetime — null when not featured
  featured_mission_alignment    str
  featured_signature_content    str (long-form)
  featured_video_url            str
  featured_image_urls           list[str] up to 3
  featured_custom_cta           str (up to 200 chars)
  featured_custom_cta_url       str (link target for the CTA)
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest

from auth_utils import get_current_user, require_roles
from models import (
    FeaturePartnerRequest,
    FeatureCheckoutRequest,
    FeaturedContentUpdate,
    gen_id,
    now_iso,
)
from utils.audit import log_action

logger = logging.getLogger("birthright.featured")

# Default price + duration. Admin-overridable via foundation_settings (key=featured_pricing).
DEFAULT_FEATURED_PRICE_USD = 99.0
DEFAULT_FEATURED_DURATION_DAYS = 30

public_router = APIRouter(prefix="/featured", tags=["featured"])
my_router = APIRouter(prefix="/me/featured", tags=["featured-partner"])
admin_router = APIRouter(prefix="/admin/featured", tags=["featured-admin"])


# ============ HELPERS ============

async def _get_pricing(db) -> dict:
    doc = await db.foundation_settings.find_one({"key": "featured_pricing"}, {"_id": 0})
    if doc and doc.get("price_usd") and doc.get("duration_days"):
        return {"price_usd": float(doc["price_usd"]), "duration_days": int(doc["duration_days"])}
    return {"price_usd": DEFAULT_FEATURED_PRICE_USD, "duration_days": DEFAULT_FEATURED_DURATION_DAYS}


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_featured(profile: dict) -> bool:
    until = profile.get("featured_until")
    if not until:
        return False
    try:
        return datetime.fromisoformat(until) > datetime.now(timezone.utc)
    except Exception:
        return False


def _content_updates_from(data: dict) -> dict:
    """Map content fields onto the profile's featured_* columns."""
    mapping = {
        "mission_alignment": "featured_mission_alignment",
        "signature_content": "featured_signature_content",
        "video_url": "featured_video_url",
        "image_urls": "featured_image_urls",
        "custom_cta": "featured_custom_cta",
        "custom_cta_url": "featured_custom_cta_url",
    }
    out: dict = {}
    for src, dst in mapping.items():
        if data.get(src) is not None:
            out[dst] = data[src]
    return out


# ============ PUBLIC ============

@public_router.get("/pricing")
async def public_pricing():
    from database import db
    return await _get_pricing(db)


@public_router.get("")
async def list_featured(limit: int = Query(60, ge=1, le=200)):
    """Return all currently-featured partners (random shuffle order)."""
    from database import db
    now = _now_utc_iso()
    rows = await db.partner_profiles.find(
        {
            "status": "active",
            "public": True,
            "featured_until": {"$gt": now},
            # Hide sample personas from the live featured page
            "$or": [{"is_sample": {"$ne": True}}, {"is_sample": {"$exists": False}}],
        },
        {"_id": 0, "meta": 0, "webhook_secret": 0},
    ).to_list(limit)
    random.shuffle(rows)
    return rows


# ============ PARTNER-FACING (self-serve checkout + content edit) ============

@my_router.get("")
async def my_featured_state(
    partner_type: str = Query(...),
    user: dict = Depends(get_current_user),
):
    from database import db
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": partner_type, "status": "active"},
        {"_id": 0, "webhook_secret": 0},
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"No active {partner_type} partner profile")
    pricing = await _get_pricing(db)
    return {"profile": profile, "is_featured": _is_featured(profile), "pricing": pricing}


@my_router.put("")
async def update_my_featured_content(
    data: FeaturedContentUpdate,
    partner_type: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Update content during an active featured window."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": partner_type, "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"No active {partner_type} partner profile")
    if not _is_featured(profile):
        raise HTTPException(status_code=400, detail="You don't have an active featured window. Purchase one first.")
    updates = _content_updates_from(data.model_dump(exclude_none=True))
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updates["updated_at"] = now_iso()
    await db.partner_profiles.update_one({"id": profile["id"]}, {"$set": updates})
    await log_action(
        db, user, "partner.featured.content.update",
        target_type="partner_profile", target_id=profile["id"],
        metadata={"fields": list(updates.keys())},
    )
    out = await db.partner_profiles.find_one({"id": profile["id"]}, {"_id": 0, "webhook_secret": 0})
    return out


@my_router.post("/checkout")
async def checkout_featured_slot(
    data: FeatureCheckoutRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Create Stripe checkout for a featured slot. On payment success the
    featured window activates for the configured duration."""
    from database import db
    from routers.checkout import get_stripe
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": data.partner_type, "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"No active {data.partner_type} partner profile")
    if profile.get("is_sample"):
        raise HTTPException(status_code=400, detail="Sample profiles cannot purchase featured slots")

    pricing = await _get_pricing(db)
    amount = pricing["price_usd"]
    duration_days = pricing["duration_days"]

    success_url = f"{data.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&type=featured"
    cancel_url = f"{data.origin_url}/dashboard/partner/featured"

    metadata = {
        "type": "featured_slot",
        "user_id": user["id"],
        "partner_profile_id": profile["id"],
        "partner_type": data.partner_type,
        "duration_days": str(duration_days),
        # Stash content so fulfillment can apply it immediately
        "mission_alignment": (data.mission_alignment or "")[:500],
        "signature_content_len": str(len(data.signature_content or "")),
    }
    checkout_req = CheckoutSessionRequest(
        amount=amount, currency="usd", success_url=success_url, cancel_url=cancel_url, metadata=metadata
    )
    stripe_checkout = get_stripe(request)
    session = await stripe_checkout.create_checkout_session(checkout_req)

    txn = {
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"],
        "type": "featured_slot",
        "amount": amount,
        "currency": "usd",
        "metadata": metadata,
        "partner_profile_id": profile["id"],
        "duration_days": duration_days,
        # Full content payload kept on the txn (not in Stripe metadata which has a 500-char limit per value)
        "featured_content": {
            "mission_alignment": data.mission_alignment or "",
            "signature_content": data.signature_content,
            "video_url": data.video_url,
            "image_urls": data.image_urls or [],
            "custom_cta": data.custom_cta,
            "custom_cta_url": data.custom_cta_url,
        },
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    }
    await db.payment_transactions.insert_one(txn)
    return {"url": session.url, "session_id": session.session_id}


async def activate_featured_from_txn(db, txn: dict) -> None:
    """Stripe webhook handler — apply featured window after payment clears."""
    profile_id = txn.get("partner_profile_id") or txn.get("metadata", {}).get("partner_profile_id")
    if not profile_id:
        return
    profile = await db.partner_profiles.find_one({"id": profile_id})
    if not profile:
        return
    duration_days = int(txn.get("duration_days") or txn.get("metadata", {}).get("duration_days") or DEFAULT_FEATURED_DURATION_DAYS)
    # Extend if already featured, otherwise start a fresh window from now.
    now = datetime.now(timezone.utc)
    current_until = None
    if profile.get("featured_until"):
        try:
            current_until = datetime.fromisoformat(profile["featured_until"])
        except Exception:
            current_until = None
    start = current_until if (current_until and current_until > now) else now
    new_until = (start + timedelta(days=duration_days)).isoformat()

    updates = {"featured_until": new_until, "updated_at": now_iso()}
    updates.update(_content_updates_from(txn.get("featured_content") or {}))
    await db.partner_profiles.update_one({"id": profile_id}, {"$set": updates})
    await db.featured_slot_purchases.insert_one({
        "id": gen_id(),
        "partner_profile_id": profile_id,
        "user_id": txn.get("user_id"),
        "session_id": txn["session_id"],
        "amount": float(txn["amount"]),
        "duration_days": duration_days,
        "featured_until": new_until,
        "created_at": now_iso(),
    })


# ============ ADMIN (grant / revoke) ============

@admin_router.post("/{profile_id}/grant")
async def admin_grant_feature(
    profile_id: str,
    data: FeaturePartnerRequest,
    user: dict = Depends(require_roles("admin")),
):
    """Admin manually grants a featured window (free / comped). `until` is ISO."""
    from database import db
    profile = await db.partner_profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    updates = {
        "featured_until": data.until,
        "featured_mission_alignment": data.mission_alignment or "",
        "featured_signature_content": data.signature_content,
        "featured_video_url": data.video_url,
        "featured_image_urls": data.image_urls or [],
        "featured_custom_cta": data.custom_cta,
        "updated_at": now_iso(),
    }
    await db.partner_profiles.update_one({"id": profile_id}, {"$set": updates})
    await log_action(
        db, user, "partner.featured.grant",
        target_type="partner_profile", target_id=profile_id,
        metadata={"until": data.until, "partner_type": profile["partner_type"]},
    )
    out = await db.partner_profiles.find_one({"id": profile_id}, {"_id": 0, "webhook_secret": 0})
    return out


@admin_router.post("/{profile_id}/revoke")
async def admin_revoke_feature(
    profile_id: str,
    reason: Optional[str] = Query(default=None, max_length=2000),
    user: dict = Depends(require_roles("admin")),
):
    """Immediately end the featured window. (No refund logic; that's a follow-up.)"""
    from database import db
    profile = await db.partner_profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.partner_profiles.update_one(
        {"id": profile_id},
        {"$set": {"featured_until": None, "updated_at": now_iso(), "featured_revoke_reason": (reason or "").strip()}},
    )
    await log_action(
        db, user, "partner.featured.revoke",
        target_type="partner_profile", target_id=profile_id,
        metadata={"reason": reason, "partner_type": profile["partner_type"]},
    )
    out = await db.partner_profiles.find_one({"id": profile_id}, {"_id": 0, "webhook_secret": 0})
    return out


@admin_router.get("")
async def admin_list_featured(
    include_expired: bool = Query(False),
    user: dict = Depends(require_roles("admin")),
):
    """Admin view: all profiles with a featured_until set (currently or in the past)."""
    from database import db
    query: dict = {"featured_until": {"$ne": None}}
    if not include_expired:
        query["featured_until"] = {"$gt": _now_utc_iso()}
    rows = await db.partner_profiles.find(query, {"_id": 0, "webhook_secret": 0}).sort("featured_until", -1).to_list(500)
    return rows
