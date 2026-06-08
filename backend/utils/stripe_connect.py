"""Stripe Connect utilities — Express accounts + transfers for artist payouts.

Two surfaces:

  1. Onboarding (artist-facing)
     • `create_or_get_express_account(email, artist_user_id)` — lazily
       creates a Connect Express account scoped to the artist; idempotent
       via lookup by `metadata.artist_user_id`.
     • `create_onboarding_link(account_id, refresh_url, return_url)` —
       returns a hosted Stripe URL where the artist completes KYC, bank
       linkage, terms acceptance, etc.
     • `refresh_account_status(account_id)` — pulls the latest
       `charges_enabled` / `payouts_enabled` / `details_submitted` flags
       so the dashboard knows whether the artist is ready to receive
       transfers.

  2. Transfers (admin payout)
     • `create_transfer(amount_usd, destination_account_id, transfer_group,
        metadata)` — moves funds from the Foundation Stripe balance to
       the artist's Connect account. Idempotency key derived from the
       payout row id so repeated mark-paid clicks never double-pay.

Errors are caught at the call site so the existing manual payout flow
continues to work even when Connect isn't configured (e.g. test key on
a platform account without Connect enabled).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import stripe

logger = logging.getLogger("birthright.stripe_connect")

# Lazy because tests / first imports happen before .env is loaded.
def _stripe_key() -> str:
    k = os.environ.get("STRIPE_API_KEY")
    if not k:
        raise RuntimeError("STRIPE_API_KEY not configured")
    return k


def _client() -> "stripe":
    stripe.api_key = _stripe_key()
    return stripe


async def create_or_get_express_account(
    db, *, artist_user_id: str, email: str,
) -> dict:
    """Return the Stripe Connect account dict for this artist. Lazily creates
    one with `type='express'` if none exists yet (looked up by
    `db.partner_payout_methods.stripe_account_id`).
    """
    existing = await db.partner_payout_methods.find_one(
        {"user_id": artist_user_id}, {"_id": 0},
    )
    if existing and existing.get("stripe_account_id"):
        # Pull fresh status from Stripe.
        s = _client()
        acct = s.Account.retrieve(existing["stripe_account_id"])
        return dict(acct)

    s = _client()
    acct = s.Account.create(
        type="express",
        country="US",
        email=email,
        capabilities={
            "transfers": {"requested": True},
        },
        metadata={
            "artist_user_id": artist_user_id,
            "platform": "birthright.live",
        },
    )
    # Persist the account ID on the partner_payout_methods row so the
    # admin payout flow can find it later.
    from models import gen_id, now_iso
    if existing:
        await db.partner_payout_methods.update_one(
            {"user_id": artist_user_id},
            {"$set": {
                "method_type": "stripe_connect",
                "stripe_account_id": acct["id"],
                "stripe_connect_status": "pending_onboarding",
                "updated_at": now_iso(),
            }},
        )
    else:
        await db.partner_payout_methods.insert_one({
            "id": gen_id(),
            "user_id": artist_user_id,
            "method_type": "stripe_connect",
            "stripe_account_id": acct["id"],
            "stripe_connect_status": "pending_onboarding",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
    return dict(acct)


def create_onboarding_link(
    account_id: str, *, refresh_url: str, return_url: str,
) -> str:
    """Return a Stripe-hosted onboarding URL for the Express account."""
    s = _client()
    link = s.AccountLink.create(
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    return link["url"]


async def refresh_account_status(db, *, artist_user_id: str) -> dict:
    """Pull `charges_enabled` / `payouts_enabled` / `details_submitted` from
    Stripe and persist to the payout method row. Returns the new status."""
    method = await db.partner_payout_methods.find_one(
        {"user_id": artist_user_id}, {"_id": 0},
    )
    if not method or not method.get("stripe_account_id"):
        return {"connected": False}
    s = _client()
    acct = s.Account.retrieve(method["stripe_account_id"])
    status = {
        "connected": True,
        "stripe_account_id": acct["id"],
        "charges_enabled": bool(acct.get("charges_enabled")),
        "payouts_enabled": bool(acct.get("payouts_enabled")),
        "details_submitted": bool(acct.get("details_submitted")),
    }
    from models import now_iso
    if status["payouts_enabled"]:
        stage = "ready"
    elif status["details_submitted"]:
        stage = "pending_review"
    else:
        stage = "pending_onboarding"
    await db.partner_payout_methods.update_one(
        {"user_id": artist_user_id},
        {"$set": {
            "stripe_connect_status": stage,
            "stripe_charges_enabled": status["charges_enabled"],
            "stripe_payouts_enabled": status["payouts_enabled"],
            "stripe_details_submitted": status["details_submitted"],
            "updated_at": now_iso(),
        }},
    )
    status["stage"] = stage
    return status


def create_transfer(
    *, amount_usd: float, destination_account_id: str,
    transfer_group: str, idempotency_key: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Move `amount_usd` from the Foundation's Stripe balance to the artist's
    Connect account. Returns the Transfer object."""
    s = _client()
    amount_cents = int(round(amount_usd * 100))
    tx = s.Transfer.create(
        amount=amount_cents,
        currency="usd",
        destination=destination_account_id,
        transfer_group=transfer_group,
        metadata=metadata or {},
        idempotency_key=idempotency_key,
    )
    return dict(tx)
