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

from auth_utils import get_current_user, require_roles
from utils.agreement_gate import require_active_agreement
from emergentintegrations.payments.stripe.checkout import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    StripeCheckout,
)
from models import (
    AdminSubscriptionRevokeRequest,
    SubscriptionCancelRequest,
    SubscriptionCheckoutRequest,
    SubscriptionPlanChangeRequest,
    gen_id,
    now_iso,
)
from utils.audit import log_action

logger = logging.getLogger("birthright.subscriptions")
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
admin_router = APIRouter(prefix="/admin/subscriptions", tags=["subscriptions-admin"])

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
    data: SubscriptionCheckoutRequest, request: Request, user: dict = Depends(require_active_agreement)
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
    # If this is a plan-change checkout, mark the predecessor as superseded
    supersedes_id = meta.get("supersedes_subscription_id")
    if supersedes_id:
        sub["supersedes_subscription_id"] = supersedes_id
        sub["prorated_credit_usd"] = float(meta.get("prorated_credit_usd") or 0)
        await db.partner_subscriptions.update_one(
            {"id": supersedes_id, "status": {"$in": ["active", "cancelled"]}},
            {"$set": {
                "status": "superseded",
                "superseded_at": now_dt.isoformat(),
                "superseded_by_session_id": txn["session_id"],
            }},
        )
    await db.partner_subscriptions.insert_one(dict(sub))
    # Audit log (best-effort)
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    await log_action(
        db, user, "subscription.activate",
        target_type="partner_subscription", target_id=sub["id"],
        metadata={"plan_id": plan_id, "partner_type": plan["partner_type"], "expires_at": expires_at},
    )


# ============ CANCEL & PLAN CHANGE (v1.11.0 Step 9) ============

@router.post("/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    data: SubscriptionCancelRequest,
    user: dict = Depends(get_current_user),
):
    """Partner-initiated cancel. The paid window remains in effect until
    `expires_at`, so this is non-destructive — it just disables renewal prompts
    and records intent. Returns the updated subscription."""
    from database import db
    sub = await db.partner_subscriptions.find_one({"id": subscription_id, "user_id": user["id"]})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Subscription already cancelled")
    await db.partner_subscriptions.update_one(
        {"id": subscription_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": now_iso(),
            "cancel_reason": (data.reason or "").strip(),
            "cancelled_by": "partner",
        }},
    )
    await log_action(
        db, user, "subscription.cancel",
        target_type="partner_subscription", target_id=subscription_id,
        metadata={"plan_id": sub.get("plan_id"), "reason_len": len(data.reason or "")},
    )
    return await db.partner_subscriptions.find_one({"id": subscription_id}, {"_id": 0})


def _prorated_credit(sub: dict, plan: dict) -> float:
    """Return USD credit for the unused remainder of `sub` at this moment.

    credit = amount_paid * (days_remaining / total_days)
    Clamped at 0 if expired."""
    try:
        amount = float(sub.get("amount_paid") or 0)
        expires = datetime.fromisoformat(sub["expires_at"])
        started = datetime.fromisoformat(sub["started_at"])
    except Exception:
        return 0.0
    now_dt = datetime.now(timezone.utc)
    if expires <= now_dt:
        return 0.0
    total_days = max(1, (expires - started).days)
    remaining_days = max(0, (expires - now_dt).days)
    return round(amount * remaining_days / total_days, 2)


@router.get("/{subscription_id}/change-preview")
async def change_preview(
    subscription_id: str,
    new_plan_id: str,
    user: dict = Depends(get_current_user),
):
    """Preview what a plan change would cost without committing to a checkout."""
    from database import db
    sub = await db.partner_subscriptions.find_one({"id": subscription_id, "user_id": user["id"]})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    new_plan = await db.subscription_plans.find_one({"id": new_plan_id, "active": True})
    if not new_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if new_plan["partner_type"] != sub["partner_type"]:
        raise HTTPException(status_code=400, detail="New plan must match the partner type of the current subscription")
    credit = _prorated_credit(sub, new_plan) if sub.get("status") == "active" else 0.0
    new_price = float(new_plan["price_usd"])
    due = max(0.0, round(new_price - credit, 2))
    return {
        "current_plan_id": sub["plan_id"],
        "new_plan_id": new_plan_id,
        "new_plan_name": new_plan.get("name"),
        "new_plan_price_usd": new_price,
        "prorated_credit_usd": credit,
        "amount_due_usd": due,
        "current_expires_at": sub.get("expires_at"),
    }


@router.post("/{subscription_id}/change-plan")
async def change_plan(
    subscription_id: str,
    data: SubscriptionPlanChangeRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Start a Stripe checkout for the prorated `amount_due`. On success, the
    standard subscription fulfillment runs, and we mark the prior sub as
    `superseded`. Free upgrades (when credit >= new price) skip Stripe.
    """
    from database import db
    sub = await db.partner_subscriptions.find_one({"id": subscription_id, "user_id": user["id"]})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub.get("status") not in ("active", "cancelled"):
        raise HTTPException(status_code=400, detail="Only active or cancelled subscriptions can change plans")
    new_plan = await db.subscription_plans.find_one({"id": data.new_plan_id, "active": True})
    if not new_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if new_plan["partner_type"] != sub["partner_type"]:
        raise HTTPException(status_code=400, detail="New plan must match the partner type")
    if new_plan["id"] == sub["plan_id"] and sub.get("status") == "active":
        raise HTTPException(status_code=400, detail="Already on this plan")

    credit = _prorated_credit(sub, new_plan)
    due = max(0.0, round(float(new_plan["price_usd"]) - credit, 2))
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": new_plan["partner_type"], "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=403, detail="Approved partner profile required")

    metadata = {
        "type": "subscription",
        "plan_id": new_plan["id"],
        "partner_type": new_plan["partner_type"],
        "duration_months": str(new_plan["duration_months"]),
        "partner_profile_id": profile["id"],
        "user_id": user["id"],
        "supersedes_subscription_id": subscription_id,
        "prorated_credit_usd": str(credit),
    }

    # If the credit covers the new plan entirely, fulfill in-band without Stripe
    if due <= 0.0:
        synthetic_txn = {
            "id": gen_id(),
            "session_id": f"comp_change_{subscription_id}_{new_plan['id']}",
            "user_id": user["id"],
            "type": "subscription",
            "amount": 0.0,
            "currency": "usd",
            "metadata": metadata,
            "payment_status": "paid",
            "status": "complete",
            "created_at": now_iso(),
        }
        await db.payment_transactions.insert_one(dict(synthetic_txn))
        await create_subscription_from_txn(db, synthetic_txn)
        await db.partner_subscriptions.update_one(
            {"id": subscription_id},
            {"$set": {
                "status": "superseded", "superseded_at": now_iso(),
                "superseded_by_session_id": synthetic_txn["session_id"],
            }},
        )
        await log_action(
            db, user, "subscription.change_plan.free",
            target_type="partner_subscription", target_id=subscription_id,
            metadata={"new_plan_id": new_plan["id"], "credit_usd": credit},
        )
        return {"checkout_required": False, "amount_due_usd": 0.0, "prorated_credit_usd": credit}

    # Otherwise charge the difference via Stripe
    success_url = f"{data.origin_url}/dashboard/partner?subscription=changed&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/dashboard/partner?subscription=change_cancelled"
    stripe = _get_stripe(request)
    session = await stripe.create_checkout_session(
        CheckoutSessionRequest(
            amount=due, currency="usd", success_url=success_url, cancel_url=cancel_url,
            metadata=metadata,
        )
    )
    await db.payment_transactions.insert_one({
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"],
        "type": "subscription",
        "amount": due,
        "currency": "usd",
        "metadata": metadata,
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    })
    return {
        "checkout_required": True,
        "url": session.url,
        "session_id": session.session_id,
        "amount_due_usd": due,
        "prorated_credit_usd": credit,
    }


# ============ ADMIN (v1.11.0 Step 9) ============

@admin_router.get("")
async def admin_list_subscriptions(
    status: Optional[str] = None,
    partner_type: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    if partner_type:
        query["partner_type"] = partner_type
    rows = await db.partner_subscriptions.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Enrich with user + plan
    user_ids = list({r["user_id"] for r in rows})
    plan_ids = list({r["plan_id"] for r in rows})
    users_by = {}
    if user_ids:
        async for u in db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1},
        ):
            users_by[u["id"]] = u
    plans_by = {}
    if plan_ids:
        async for p in db.subscription_plans.find({"id": {"$in": plan_ids}}, {"_id": 0}):
            plans_by[p["id"]] = p
    now = datetime.now(timezone.utc).isoformat()
    for r in rows:
        u = users_by.get(r["user_id"], {})
        r["partner_name"] = f"{u.get('first_name','')} {u.get('last_name','')}".strip()
        r["partner_email"] = u.get("email", "")
        r["plan"] = plans_by.get(r["plan_id"])
        r["is_active"] = bool(r.get("expires_at") and r["expires_at"] > now and r["status"] == "active")
    return rows


@admin_router.post("/{subscription_id}/revoke")
async def admin_revoke_subscription(
    subscription_id: str,
    data: AdminSubscriptionRevokeRequest,
    user: dict = Depends(require_roles("admin")),
):
    """Admin revoke — ends the subscription immediately (sets expires_at=now,
    status='revoked'). Optional refund flag triggers Stripe refund of the
    `amount_paid` on the original payment_session_id."""
    from database import db
    sub = await db.partner_subscriptions.find_one({"id": subscription_id})
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub.get("status") in ("revoked", "superseded"):
        raise HTTPException(status_code=400, detail=f"Subscription is already {sub['status']}")

    refund_result = None
    if data.refund and sub.get("payment_session_id") and not sub["payment_session_id"].startswith("comp_change_"):
        try:
            from utils.refunds import refund_session
            refund_result = await refund_session(sub["payment_session_id"])
        except Exception as e:
            logger.error(f"refund failed for sub {subscription_id}: {e}")
            refund_result = {"status": "error", "error": str(e)}

    await db.partner_subscriptions.update_one(
        {"id": subscription_id},
        {"$set": {
            "status": "revoked",
            "revoked_at": now_iso(),
            "revoked_by": user["id"],
            "revoke_reason": data.reason.strip(),
            "expires_at": now_iso(),
            "refund": refund_result,
        }},
    )
    await log_action(
        db, user, "subscription.admin_revoke",
        target_type="partner_subscription", target_id=subscription_id,
        metadata={
            "plan_id": sub.get("plan_id"), "refund_requested": data.refund,
            "refund_status": (refund_result or {}).get("status") if isinstance(refund_result, dict) else None,
        },
    )
    return await db.partner_subscriptions.find_one({"id": subscription_id}, {"_id": 0})

