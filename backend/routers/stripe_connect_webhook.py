"""Stripe Connect webhook — handles `account.updated` and
`transfer.failed` so Connect state and payout state stay coherent without
needing the artist or admin to poll.

Mounted at `/api/webhook/stripe-connect` (separate from the regular
checkout webhook at `/api/webhook/stripe`).
"""
from __future__ import annotations

import logging
import os

import stripe
from fastapi import APIRouter, HTTPException, Request

from models import now_iso

logger = logging.getLogger("birthright.stripe_connect_webhook")

router = APIRouter(prefix="/webhook", tags=["stripe-connect-webhook"])


def _verify(payload: bytes, sig_header: str | None) -> stripe.Event:
    secret = os.environ.get("STRIPE_CONNECT_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(503, "Connect webhook secret not configured")
    if not sig_header:
        raise HTTPException(400, "Missing Stripe-Signature header")
    try:
        return stripe.Webhook.construct_event(payload, sig_header, secret)
    except stripe.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")


@router.post("/stripe-connect")
async def stripe_connect_webhook(request: Request):
    from database import db
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    event = _verify(payload, sig_header)
    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "account.updated":
        # An artist's onboarding state changed — refresh our cached flags.
        acct_id = obj.get("id")
        artist_user_id = (obj.get("metadata") or {}).get("artist_user_id")
        if not artist_user_id:
            # Try to find by stripe_account_id since metadata may be empty
            # on some platform Express accounts.
            method = await db.partner_payout_methods.find_one(
                {"stripe_account_id": acct_id}, {"_id": 0, "user_id": 1},
            )
            if method:
                artist_user_id = method["user_id"]
        if not artist_user_id:
            logger.warning("account.updated for unknown account %s", acct_id)
            return {"ok": True, "ignored": "unknown_account"}

        details_submitted = bool(obj.get("details_submitted"))
        charges_enabled = bool(obj.get("charges_enabled"))
        payouts_enabled = bool(obj.get("payouts_enabled"))
        if payouts_enabled:
            stage = "ready"
        elif details_submitted:
            stage = "pending_review"
        else:
            stage = "pending_onboarding"
        await db.partner_payout_methods.update_one(
            {"user_id": artist_user_id},
            {"$set": {
                "stripe_connect_status": stage,
                "stripe_charges_enabled": charges_enabled,
                "stripe_payouts_enabled": payouts_enabled,
                "stripe_details_submitted": details_submitted,
                "updated_at": now_iso(),
            }},
        )
        logger.info(
            "Stripe account.updated: artist=%s acct=%s stage=%s",
            artist_user_id, acct_id, stage,
        )
        return {"ok": True, "stage": stage}

    elif etype in ("transfer.failed", "transfer.reversed"):
        # A previously-marked-paid payout's transfer failed at Stripe. Flip
        # the corresponding payout row back to 'pending' with a failure
        # reason so the admin can retry or switch to manual.
        transfer_id = obj.get("id")
        metadata = obj.get("metadata") or {}
        payout_id = metadata.get("payout_id")
        reason = obj.get("failure_message") or obj.get(
            "failure_code") or etype
        if not payout_id:
            # Try to look up by stripe_transfer_id.
            row = await db.artist_sale_payouts.find_one(
                {"stripe_transfer_id": transfer_id},
                {"_id": 0, "id": 1},
            )
            if row:
                payout_id = row["id"]
        if not payout_id:
            logger.warning("transfer.failed for unknown payout %s", transfer_id)
            return {"ok": True, "ignored": "unknown_payout"}
        await db.artist_sale_payouts.update_one(
            {"id": payout_id},
            {"$set": {
                "status": "pending",
                "paid_at": None,
                "stripe_transfer_id": None,
                "payout_reference": None,
                "notes": f"[auto] Transfer {transfer_id} reverted: {reason}",
                "transfer_failure_reason": reason,
                "transfer_failed_at": now_iso(),
            }},
        )
        logger.warning(
            "transfer.failed handled: payout=%s transfer=%s reason=%s",
            payout_id, transfer_id, reason,
        )
        return {"ok": True, "rolled_back": payout_id}

    # Ignore unrelated events.
    return {"ok": True, "ignored": etype}
