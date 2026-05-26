"""AI usage metering + wallet — Phase 6C.4.

Single source of truth for:
  - Per-model price table (Claude Sonnet 4.5, Nano Banana, etc.)
  - Cost computation for a single LLM/image call (with foundation markup)
  - Partner AI wallet balance read + atomic debit
  - Usage event recording (db.ai_usage_events, idempotent via event id)

Default billing: 1.5× passthrough — partners pay the underlying provider cost
plus a 50% markup that directly supports Birthright Foundation. We disclose
this multiplier at every surface where the user sees price (top-up UI,
usage tables, AI panels, error messages). Override with AI_PRICE_MULTIPLIER
env var if foundation policy changes.
"""
from __future__ import annotations

import logging
import os
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

# 1.5× passthrough: provider cost + 50% to the Foundation.
PRICE_MULTIPLIER = float(os.environ.get("AI_PRICE_MULTIPLIER", "1.5"))
FOUNDATION_MARKUP_PCT = round((PRICE_MULTIPLIER - 1.0) * 100, 1)  # e.g. 50.0
PRICING_DISCLOSURE = (
    f"AI calls are billed at {PRICE_MULTIPLIER:.2f}× the underlying provider cost — "
    f"the extra {FOUNDATION_MARKUP_PCT:.0f}% directly supports Birthright Foundation. "
    f"Thank you for making this work possible."
)
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
    feature: str,            # "concierge" | "research_collab" | "vendor_pdm"
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
        # Fire-and-forget auto-recharge check (won't block the request).
        try:
            import asyncio
            asyncio.create_task(maybe_send_auto_recharge_email(db, user["id"]))
        except Exception as e:
            logger.warning("auto-recharge dispatch failed: %s", e)
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
    """Deprecated — see maybe_send_auto_recharge_email instead."""
    w = await get_wallet(db, user["id"])
    if not w.get("auto_recharge_enabled"):
        return None
    if (w.get("balance_usd") or 0.0) > (w.get("auto_recharge_threshold_usd") or 0.0):
        return None
    await db.ai_wallets.update_one(
        {"user_id": user["id"]},
        {"$set": {"auto_recharge_last_triggered_at": now_iso()}},
    )
    return "needs_checkout"


async def maybe_send_auto_recharge_email(db, user_id: str) -> Optional[str]:
    """Background helper invoked after a usage debit. If the user has
    auto-recharge enabled AND balance dipped below threshold AND we haven't
    sent a top-up link in the last 4 hours, build a Stripe Checkout session
    and email the partner a one-click "Top up now" link.

    Returns the session URL if one was created, else None.
    """
    from datetime import datetime, timezone, timedelta
    w = await db.ai_wallets.find_one({"user_id": user_id}, {"_id": 0})
    if not w or not w.get("auto_recharge_enabled"):
        return None
    threshold = float(w.get("auto_recharge_threshold_usd") or 5.0)
    if (w.get("balance_usd") or 0.0) > threshold:
        return None
    last = w.get("auto_recharge_last_email_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - last_dt) < timedelta(hours=4):
                return None
        except Exception:
            pass

    user = await db.users.find_one({"id": user_id})
    if not user or not user.get("email"):
        return None
    amount = float(w.get("auto_recharge_amount_usd") or 25.0)

    # Build a Stripe Checkout session via the existing emergentintegrations SDK.
    # We don't have a request object here so we use the static production URL
    # baked into env (PUBLIC_APP_URL falls back to the preview origin).
    try:
        from emergentintegrations.payments.stripe.checkout import (
            CheckoutSessionRequest, StripeCheckout,
        )
        stripe_key = os.environ.get("STRIPE_SECRET_KEY") or os.environ.get("STRIPE_API_KEY")
        origin = os.environ.get("PUBLIC_APP_URL", "https://birthright.live").rstrip("/")
        webhook_url = f"{origin}/api/webhook/stripe"
        stripe = StripeCheckout(api_key=stripe_key, webhook_url=webhook_url)
        metadata = {
            "type": "ai_wallet_topup",
            "user_id": user_id,
            "amount_usd": str(amount),
            "source": "auto_recharge",
        }
        sess = await stripe.create_checkout_session(CheckoutSessionRequest(
            amount=amount, currency="usd",
            success_url=f"{origin}/dashboard/ai-wallet?topup=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/dashboard/ai-wallet?topup=cancelled",
            metadata=metadata,
        ))
        await db.payment_transactions.insert_one({
            "id": gen_id(),
            "session_id": sess.session_id,
            "user_id": user_id,
            "type": "ai_wallet_topup",
            "amount": amount,
            "currency": "usd",
            "metadata": metadata,
            "payment_status": "initiated",
            "status": "open",
            "created_at": now_iso(),
        })
    except Exception as e:
        logger.exception("auto-recharge Stripe session failed: %s", e)
        return None

    # Email the link via the existing mailer.
    try:
        from utils.mailer import send_email
        await send_email(
            to=user["email"],
            subject=f"Your Birthright AI Wallet — top up ${amount:.0f} to continue",
            html=(
                f"<p>Hi {user.get('first_name','there')},</p>"
                f"<p>Your AI Wallet balance is ${float(w.get('balance_usd') or 0):.4f}, "
                f"below your auto-recharge threshold of ${threshold:.0f}.</p>"
                f"<p>Click the button below to top up ${amount:.0f} via Stripe and keep "
                f"your AI features running.</p>"
                f"<p><a href='{sess.url}' style='display:inline-block;padding:10px 18px;"
                f"background:#476B6B;color:#FAF8F5;text-decoration:none;border-radius:6px'>"
                f"Top up ${amount:.0f}</a></p>"
                f"<p>This link expires in 24 hours.</p>"
            ),
            template_name="ai_wallet_auto_recharge",
            metadata={"user_id": user_id, "amount_usd": amount, "session_id": sess.session_id},
        )
    except Exception as e:
        logger.exception("auto-recharge email send failed: %s", e)

    await db.ai_wallets.update_one(
        {"user_id": user_id},
        {"$set": {"auto_recharge_last_email_at": now_iso(),
                  "auto_recharge_last_session_id": sess.session_id}},
    )
    return sess.url
