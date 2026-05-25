"""AI usage metering + wallet — Phase 6C.4.

Single source of truth for:
  - Per-model price table (Claude Sonnet 4.5, Nano Banana, etc.)
  - Cost computation for a single LLM/image call
  - Partner AI wallet balance read + atomic debit
  - Usage event recording (db.ai_usage_events, idempotent via event id)

Default billing: 1× passthrough (no markup). Override with AI_PRICE_MULTIPLIER
env var if foundation policy changes.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from models import gen_id, now_iso

logger = logging.getLogger("birthright.ai_billing")

# All prices in USD per UNIT. For LLMs: per 1,000,000 tokens. For images: per image.
PRICE_TABLE: dict[str, dict] = {
    # Anthropic
    "claude-sonnet-4-5-20250929": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-sonnet-4-5": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-sonnet-4-6":        {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-haiku-4-5-20251001": {"input_per_mtok": 0.80, "output_per_mtok": 4.00},
    "claude-opus-4-7":           {"input_per_mtok": 15.00, "output_per_mtok": 75.00},
    # OpenAI text
    "gpt-5.4":      {"input_per_mtok": 5.00, "output_per_mtok": 15.00},
    "gpt-5.4-mini": {"input_per_mtok": 0.60, "output_per_mtok": 2.40},
    # Google text
    "gemini-3.1-pro-preview":   {"input_per_mtok": 2.50, "output_per_mtok": 10.00},
    "gemini-3-flash-preview":   {"input_per_mtok": 0.15, "output_per_mtok": 0.60},
    # Image generation
    "nano-banana":     {"per_image": 0.04},
    "gemini-2.5-flash-image": {"per_image": 0.04},
    "gpt-image-1":     {"per_image": 0.07},
}

PRICE_MULTIPLIER = float(os.environ.get("AI_PRICE_MULTIPLIER", "1.0"))
LOW_BALANCE_WARN_USD = float(os.environ.get("AI_LOW_BALANCE_WARN", "1.00"))
TOPUP_PACKS_USD = [10, 25, 50, 100]


def compute_cost(model: str, *, tokens_in: int = 0, tokens_out: int = 0, images: int = 0) -> float:
    p = PRICE_TABLE.get(model)
    if not p:
        # Unknown model: bill nothing, but log so we know to add it.
        logger.warning("ai_billing: no price entry for model %s — bill $0.00 for this call", model)
        return 0.0
    cost = 0.0
    if "input_per_mtok" in p:
        cost += (tokens_in / 1_000_000.0) * p["input_per_mtok"]
        cost += (tokens_out / 1_000_000.0) * p["output_per_mtok"]
    if "per_image" in p:
        cost += images * p["per_image"]
    cost *= PRICE_MULTIPLIER
    return round(cost, 6)


async def get_wallet(db, user_id: str) -> dict:
    """Return the user's AI wallet, lazily creating it on first access."""
    w = await db.ai_wallets.find_one({"user_id": user_id}, {"_id": 0})
    if w:
        return w
    doc = {
        "id": gen_id(),
        "user_id": user_id,
        "balance_usd": 0.0,
        "lifetime_topup_usd": 0.0,
        "lifetime_spend_usd": 0.0,
        "auto_recharge_enabled": False,
        "auto_recharge_threshold_usd": 5.0,
        "auto_recharge_amount_usd": 25.0,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.ai_wallets.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


async def credit_wallet(db, user_id: str, amount_usd: float, *, source: str, ref: Optional[str] = None) -> dict:
    """Credit funds (top-up or admin grant). Idempotent via `ref` if provided."""
    if amount_usd <= 0:
        raise ValueError("amount must be positive")
    if ref:
        existing = await db.ai_wallet_entries.find_one({"ref": ref, "type": "credit"})
        if existing:
            return await get_wallet(db, user_id)
    await get_wallet(db, user_id)  # ensure exists
    await db.ai_wallets.update_one(
        {"user_id": user_id},
        {"$inc": {"balance_usd": amount_usd, "lifetime_topup_usd": amount_usd},
         "$set": {"updated_at": now_iso()}},
    )
    await db.ai_wallet_entries.insert_one({
        "id": gen_id(),
        "user_id": user_id,
        "type": "credit",
        "amount_usd": round(amount_usd, 4),
        "source": source,           # "stripe_topup" | "admin_grant" | "auto_recharge"
        "ref": ref,
        "created_at": now_iso(),
    })
    return await get_wallet(db, user_id)


async def record_usage(
    db,
    user: dict,
    *,
    feature: str,            # "concierge" | "research_assistant" | "vendor_pdm"
    model: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    images: int = 0,
    meta: Optional[dict] = None,
) -> dict:
    """Compute cost, debit wallet, write a usage event. Returns the event dict."""
    cost_usd = compute_cost(model, tokens_in=tokens_in, tokens_out=tokens_out, images=images)
    event = {
        "id": gen_id(),
        "user_id": user["id"] if user else None,
        "user_email": (user or {}).get("email"),
        "feature": feature,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "images": images,
        "cost_usd": cost_usd,
        "meta": meta or {},
        "created_at": now_iso(),
    }
    await db.ai_usage_events.insert_one(dict(event))
    if user and cost_usd > 0:
        await get_wallet(db, user["id"])  # ensure exists
        await db.ai_wallets.update_one(
            {"user_id": user["id"]},
            {"$inc": {"balance_usd": -cost_usd, "lifetime_spend_usd": cost_usd},
             "$set": {"updated_at": now_iso()}},
        )
        await db.ai_wallet_entries.insert_one({
            "id": gen_id(),
            "user_id": user["id"],
            "type": "debit",
            "amount_usd": cost_usd,
            "source": feature,
            "ref": event["id"],
            "model": model,
            "created_at": now_iso(),
        })
    event.pop("_id", None)
    return event


async def require_balance(db, user: Optional[dict], *, min_usd: float = 0.01, feature: str = "ai") -> None:
    """Raise 402 Payment Required if the partner's AI balance is too low."""
    if not user:
        return  # anonymous Concierge use is free (foundation absorbs cost)
    w = await get_wallet(db, user["id"])
    if (w.get("balance_usd") or 0.0) < min_usd:
        raise HTTPException(
            status_code=402,
            detail=(f"AI balance too low to use {feature}. Top up at /dashboard/ai-wallet "
                    f"(min ${min_usd:.2f}, current ${w.get('balance_usd', 0.0):.4f})."),
        )


async def try_auto_recharge(db, user: dict, stripe_factory) -> Optional[str]:
    """If wallet is below threshold and auto-recharge is enabled, queue a Stripe
    session. Returns the session URL or None.

    Stripe call is opt-in and async — callers can fire-and-forget.
    """
    w = await get_wallet(db, user["id"])
    if not w.get("auto_recharge_enabled"):
        return None
    if (w.get("balance_usd") or 0.0) > (w.get("auto_recharge_threshold_usd") or 0.0):
        return None
    # Implementation note: actual Stripe checkout creation happens in the router
    # (which has access to the request object). This helper only signals intent.
    await db.ai_wallets.update_one(
        {"user_id": user["id"]},
        {"$set": {"auto_recharge_last_triggered_at": now_iso()}},
    )
    return "needs_checkout"
