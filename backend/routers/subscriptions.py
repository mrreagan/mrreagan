"""Partner subscriptions = time-bound licenses + rev-share tier.

v1 design: each "subscription" is a one-time purchase of a fixed-duration
plan via the existing Stripe one-time checkout. On payment we record a
`partner_subscription` row with `expires_at = now + duration_months`. The
profile is "licensed" while `expires_at > now`. There's no auto-renewal;
users renew by buying another plan when expiring.

Plan catalog is seeded in `scripts/seed_subscription_plans.py` (12 plans:
4 partner_types × 3 durations). Admin can edit via Mongo for now; UI later.

Rev-share resolution (see `utils/rev_share.py`):
  - Shorter subscription length = higher rev-share %
  - Facilitator plans carry TWO rates: `birthright_ip_pct` (higher) for
    presenting Birthright IP, `other_content_pct` (lower) for own/vendor
    materials. All other partner types use a single `default_pct`.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from auth_utils import get_current_user
from emergentintegrations.payments.stripe.checkout import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    StripeCheckout,
)
from models import SubscriptionCheckoutRequest, gen_id, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.subscriptions")
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")


def _get_stripe(request: Request) -> StripeCheckout:
    host_url = str(request.base_url).rstrip("/")
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}/api/webhook/stripe")


# ============ PLANS ============

@router.get("/plans")
async def list_plans(partner_type: Optional[str] = None):
    """Public plan catalog. Filter by partner_type if provided."""
    from database import db
    query: dict = {"active": True}
    if partner_type:
        if partner_type not in ("facilitator", "community", "research", "vendor"):
            raise HTTPException(status_code=400, detail="Invalid partner_type")
        query["partner_type"] = partner_type
    plans = await db.subscription_plans.find(query, {"_id": 0}).sort(
        [("partner_type", 1), ("duration_months", 1)]
    ).to_list(100)
    return plans


# ============ CHECKOUT ============

@router.post("/checkout")
async def checkout_subscription(
    data: SubscriptionCheckoutRequest, request: Request, user: dict = Depends(get_current_user)
):
    """Create a Stripe checkout for the chosen plan. The caller MUST have an
    approved partner profile of the plan's partner_type."""
    from database import db
    plan = await db.subscription_plans.find_one({"id": data.plan_id, "active": True})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    profile = await db.partner_profiles.find_one({
        "user_id": user["id"], "partner_type": plan["partner_type"], "status": "active",
    })
    if not profile:
        raise HTTPException(
            status_code=403,
            detail=f"You need an approved {plan['partner_type']} partner profile to subscribe to this plan. Apply at /partners/apply first.",
        )

    amount = float(plan["price_usd"])
    success_url = f"{data.origin_url}/dashboard/partner?subscription=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/partners/subscribe?type={plan['partner_type']}&cancelled=1"
    metadata = {
        "type": "subscription",
        "plan_id": plan["id"],
        "partner_type": plan["partner_type"],
        "duration_months": str(plan["duration_months"]),
        "partner_profile_id": profile["id"],
        "user_id": user["id"],
    }
    stripe = _get_stripe(request)
    session: CheckoutSessionResponse = await stripe.create_checkout_session(
        CheckoutSessionRequest(
            amount=amount, currency="usd", success_url=success_url, cancel_url=cancel_url,
            metadata=metadata,
        )
    )
    await db.payment_transactions.insert_one({
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"],
        "type": "subscription",
        "amount": amount,
        "currency": "usd",
        "metadata": metadata,
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id}


# ============ MY SUBSCRIPTIONS ============

@router.get("/my")
async def my_subscriptions(user: dict = Depends(get_current_user)):
    """Return all subscriptions for this user with the plan + computed `is_active`."""
    from database import db
    subs = await db.partner_subscriptions.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    plan_ids = list({s["plan_id"] for s in subs})
    plans = await db.subscription_plans.find(
        {"id": {"$in": plan_ids}}, {"_id": 0}
    ).to_list(len(plan_ids) or 1)
    plan_by_id = {p["id"]: p for p in plans}
    now = datetime.now(timezone.utc).isoformat()
    for s in subs:
        s["plan"] = plan_by_id.get(s["plan_id"])
        s["is_active"] = bool(s.get("expires_at") and s["expires_at"] > now and s["status"] == "active")
    return subs


# ============ POST-PAYMENT HANDLER (called from checkout.py _PAID_HANDLERS) ============

async def create_subscription_from_txn(db, txn: dict) -> None:
    """Side-effect of a successful subscription Stripe payment.

    Idempotent: if a subscription with this `payment_session_id` already exists,
    do nothing. Otherwise insert a new `partner_subscription` row.
    """
    meta = txn.get("metadata", {})
    plan_id = meta.get("plan_id")
    user_id = meta.get("user_id")
    profile_id = meta.get("partner_profile_id")
    if not (plan_id and user_id and profile_id):
        logger.error(f"subscription txn {txn.get('session_id')} missing metadata")
        return
    existing = await db.partner_subscriptions.find_one({"payment_session_id": txn["session_id"]})
    if existing:
        return
    plan = await db.subscription_plans.find_one({"id": plan_id})
    if not plan:
        logger.error(f"subscription plan {plan_id} not found at fulfillment time")
        return
    now_dt = datetime.now(timezone.utc)
    expires_at = (now_dt + timedelta(days=30 * int(plan["duration_months"]))).isoformat()
    sub = {
        "id": gen_id(),
        "user_id": user_id,
        "partner_profile_id": profile_id,
        "plan_id": plan_id,
        "partner_type": plan["partner_type"],
        "status": "active",
        "started_at": now_dt.isoformat(),
        "expires_at": expires_at,
        "duration_months": plan["duration_months"],
        "amount_paid": txn["amount"],
        "payment_session_id": txn["session_id"],
        "cancelled_at": None,
        "created_at": now_dt.isoformat(),
    }
    await db.partner_subscriptions.insert_one(dict(sub))
    # Audit log (best-effort)
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    await log_action(
        db, user, "subscription.activate",
        target_type="partner_subscription", target_id=sub["id"],
        metadata={"plan_id": plan_id, "partner_type": plan["partner_type"], "expires_at": expires_at},
    )
