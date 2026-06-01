"""Partner AI wallet — top-ups, balance, history. Phase 6C.4."""
from __future__ import annotations

from typing import Optional

from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from auth_utils import get_current_user, require_roles
from models import gen_id, now_iso
from utils.ai_billing import (
    FOUNDATION_MARKUP_PCT,
    PRICE_MULTIPLIER,
    PRICING_DISCLOSURE,
    TOPUP_PACKS_USD,
    credit_wallet,
    get_wallet,
)
from utils.audit import log_action

my_router = APIRouter(prefix="/ai-wallet", tags=["ai-wallet"])
admin_router = APIRouter(prefix="/admin/ai-wallet", tags=["ai-wallet-admin"])


# ============ ME ============

async def _spend_windows(db, user_id: str) -> dict:
    """Return today/week/month spend rollups + by-feature breakdown (30d).

    All windows are computed from `ai_usage_events.created_at` (ISO strings).
    Uses MongoDB `$gte` on the ISO string — works because ISO 8601 sorts
    lexicographically the same as chronologically.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    since_today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    since_week = (now - timedelta(days=7)).isoformat()
    since_month = (now - timedelta(days=30)).isoformat()

    async def _sum(since_iso: str) -> dict:
        pipeline = [
            {"$match": {"user_id": user_id, "created_at": {"$gte": since_iso}}},
            {"$group": {"_id": None, "events": {"$sum": 1}, "cost_usd": {"$sum": "$cost_usd"}}},
        ]
        rows = await db.ai_usage_events.aggregate(pipeline).to_list(1)
        if not rows:
            return {"events": 0, "cost_usd": 0.0}
        r = rows[0]
        return {"events": int(r.get("events") or 0), "cost_usd": round(float(r.get("cost_usd") or 0), 4)}

    today = await _sum(since_today)
    week = await _sum(since_week)
    month = await _sum(since_month)

    by_feature_pipeline = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": since_month}}},
        {"$group": {"_id": "$feature", "events": {"$sum": 1}, "cost_usd": {"$sum": "$cost_usd"}}},
        {"$sort": {"cost_usd": -1}},
    ]
    by_feature = [
        {"feature": r["_id"] or "unknown", "events": int(r.get("events") or 0),
         "cost_usd": round(float(r.get("cost_usd") or 0), 4)}
        for r in await db.ai_usage_events.aggregate(by_feature_pipeline).to_list(50)
    ]
    return {"today": today, "week": week, "month": month, "by_feature_30d": by_feature}


@my_router.get("/me")
async def my_wallet(user: dict = Depends(get_current_user)):
    from database import db
    w = await get_wallet(db, user["id"])
    recent_events = await db.ai_usage_events.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(25)
    recent_entries = await db.ai_wallet_entries.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(25)
    spend = await _spend_windows(db, user["id"])
    return {
        "wallet": w,
        "topup_packs_usd": TOPUP_PACKS_USD,
        "recent_usage": recent_events,
        "recent_entries": recent_entries,
        "spend_windows": spend,
        "pricing": {
            "multiplier": PRICE_MULTIPLIER,
            "foundation_markup_pct": FOUNDATION_MARKUP_PCT,
            "disclosure": PRICING_DISCLOSURE,
        },
    }


@my_router.get("/me/summary")
async def my_wallet_summary(user: dict = Depends(get_current_user)):
    """Lightweight read for dashboard at-a-glance tile. Returns only the
    minimum needed to render a one-line summary without pulling 25 events.
    """
    from database import db
    w = await get_wallet(db, user["id"])
    spend = await _spend_windows(db, user["id"])
    return {
        "balance_usd": float(w.get("balance_usd") or 0.0),
        "lifetime_spend_usd": float(w.get("lifetime_spend_usd") or 0.0),
        "this_month_spend_usd": spend["month"]["cost_usd"],
        "this_month_events": spend["month"]["events"],
        "low_balance": (w.get("balance_usd") or 0.0) < 1.0,
        "auto_recharge_enabled": bool(w.get("auto_recharge_enabled")),
    }


class TopupCheckoutRequest(BaseModel):
    amount_usd: float = Field(ge=5.0, le=500.0)
    origin_url: str = Field(min_length=4, max_length=600)


@my_router.post("/topup/checkout")
async def topup_checkout(
    data: TopupCheckoutRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    from database import db
    from routers.checkout import get_stripe

    success_url = f"{data.origin_url}/dashboard/ai-wallet?topup=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/dashboard/ai-wallet?topup=cancelled"
    metadata = {
        "type": "ai_wallet_topup",
        "user_id": user["id"],
        "amount_usd": str(data.amount_usd),
    }
    req = CheckoutSessionRequest(
        amount=data.amount_usd, currency="usd",
        success_url=success_url, cancel_url=cancel_url, metadata=metadata,
    )
    session = await get_stripe(request).create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"],
        "type": "ai_wallet_topup",
        "amount": data.amount_usd,
        "currency": "usd",
        "metadata": metadata,
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id}


class AutoRechargeSettings(BaseModel):
    enabled: bool
    threshold_usd: float = Field(ge=1.0, le=100.0)
    amount_usd: float = Field(ge=10.0, le=500.0)


@my_router.put("/auto-recharge")
async def set_auto_recharge(
    data: AutoRechargeSettings,
    user: dict = Depends(get_current_user),
):
    from database import db
    await get_wallet(db, user["id"])
    await db.ai_wallets.update_one(
        {"user_id": user["id"]},
        {"$set": {
            "auto_recharge_enabled": data.enabled,
            "auto_recharge_threshold_usd": data.threshold_usd,
            "auto_recharge_amount_usd": data.amount_usd,
            "updated_at": now_iso(),
        }},
    )
    return await get_wallet(db, user["id"])


# ============ WEBHOOK INTEGRATION ============

async def credit_topup_from_txn(db, txn: dict) -> None:
    """Called by Stripe webhook on payment success for an ai_wallet_topup."""
    user_id = txn.get("user_id") or txn.get("metadata", {}).get("user_id")
    amount = float(txn.get("amount") or txn.get("metadata", {}).get("amount_usd") or 0)
    if not user_id or amount <= 0:
        return
    await credit_wallet(db, user_id, amount, source="stripe_topup", ref=txn["session_id"])


# ============ ADMIN ============

@admin_router.get("/usage-report")
async def usage_report(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).isoformat()
    since_today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    since_week = (now - timedelta(days=7)).isoformat()
    since_month = (now - timedelta(days=30)).isoformat()

    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {
            "_id": {"user_email": "$user_email", "feature": "$feature"},
            "event_count": {"$sum": 1},
            "tokens_in": {"$sum": "$tokens_in"},
            "tokens_out": {"$sum": "$tokens_out"},
            "images": {"$sum": "$images"},
            "cost_usd": {"$sum": "$cost_usd"},
        }},
        {"$sort": {"cost_usd": -1}},
    ]
    rows = await db.ai_usage_events.aggregate(pipeline).to_list(500)
    by_user_feature = [
        {"user_email": r["_id"].get("user_email") or "(anonymous)",
         "feature": r["_id"].get("feature"),
         "events": r["event_count"],
         "tokens_in": r["tokens_in"],
         "tokens_out": r["tokens_out"],
         "images": r["images"],
         "cost_usd": round(r["cost_usd"], 4)}
        for r in rows
    ]
    # Totals across the selected window
    total_cost = sum(r["cost_usd"] for r in rows)
    total_events = sum(r["event_count"] for r in rows)

    # Time-window rollups (always today/week/month — independent of `days` filter)
    async def _window_total(since_iso: str) -> dict:
        agg = await db.ai_usage_events.aggregate([
            {"$match": {"created_at": {"$gte": since_iso}}},
            {"$group": {"_id": None, "events": {"$sum": 1}, "cost_usd": {"$sum": "$cost_usd"}}},
        ]).to_list(1)
        if not agg:
            return {"events": 0, "cost_usd": 0.0}
        a = agg[0]
        return {"events": int(a.get("events") or 0), "cost_usd": round(float(a.get("cost_usd") or 0), 4)}

    windows = {
        "today": await _window_total(since_today),
        "week": await _window_total(since_week),
        "month": await _window_total(since_month),
    }

    # Hydrate wallets with user email for human-readable display.
    wallet_rows = await db.ai_wallets.find({}, {"_id": 0}).to_list(500)
    user_ids = [w["user_id"] for w in wallet_rows if w.get("user_id")]
    user_lookup: dict[str, dict] = {}
    if user_ids:
        async for u in db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "email": 1, "first_name": 1, "last_name": 1, "role": 1},
        ):
            user_lookup[u["id"]] = u
    wallets = []
    for w in wallet_rows:
        u = user_lookup.get(w.get("user_id")) or {}
        wallets.append({
            **w,
            "user_email": u.get("email"),
            "user_name": (f"{u.get('first_name','')} {u.get('last_name','')}".strip() or None),
            "user_role": u.get("role"),
        })
    # Sort wallets by lifetime spend desc so admin sees heavy users first.
    wallets.sort(key=lambda x: -(x.get("lifetime_spend_usd") or 0))

    return {
        "days": days,
        "since": since,
        "total_events": total_events,
        "total_cost_usd": round(total_cost, 4),
        "by_user_feature": by_user_feature,
        "wallets": wallets,
        "windows": windows,
    }


class AdminGrantRequest(BaseModel):
    user_id: str
    amount_usd: float = Field(gt=0, le=10000)
    note: Optional[str] = Field(default=None, max_length=400)


@admin_router.post("/grant")
async def admin_grant(data: AdminGrantRequest, user: dict = Depends(require_roles("admin"))):
    from database import db
    target = await db.users.find_one({"id": data.user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    w = await credit_wallet(db, data.user_id, data.amount_usd, source="admin_grant",
                             ref=f"grant_{gen_id()}")
    await log_action(
        db, user, "ai_wallet.admin_grant",
        target_type="user", target_id=data.user_id,
        metadata={"amount_usd": data.amount_usd, "note": data.note},
    )
    return w
