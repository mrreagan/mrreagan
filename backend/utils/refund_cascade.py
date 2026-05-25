"""Refund / clawback cascade — v1.11.0 Step 10.

Given a `payment_transactions` document, run the full cascade:

  1. Call Stripe to refund the original payment (full only, for now).
  2. Mark the source transaction `payment_status='refunded'`.
  3. Reverse the side-effects of that transaction:
       * `workshop`         → cancel the registration, free the seat
       * `subscription`     → set sub status='revoked', expires_at=now
       * `featured_slot`    → set featured_until=now on the partner profile
       * `research_promotion` → reset promoted_until + tier on the artifact
       * `order`            → mark order refunded (no inventory restock — manual decision)
       * `sponsorship`      → mark sponsor entry refunded
       * `donation`         → mark donation refunded
  4. Clawback derived partner credits:
       * `referral_payouts` rows with status='earned' tied to this txn → status='reversed'
       * `partner_off_site_credits` rows with status='earned' tied to this txn → status='reversed'
       * Any rows already marked `status='paid'` → enqueue in `clawback_pending`
         collection for human handling (cannot un-pay automatically).
  5. Record a `refund_cascades` row capturing the full graph (for the
     admin/audit trail and the partner-facing financial reports).
"""
from __future__ import annotations

import logging
from typing import Optional

from models import gen_id, now_iso
from utils.audit import log_action
from utils.refunds import refund_session

logger = logging.getLogger("birthright.refund_cascade")


async def _reverse_side_effects(db, txn: dict) -> dict:
    """Undo whatever the original _PAID_HANDLER produced. Returns a summary."""
    summary: dict = {"type": txn.get("type")}
    session_id = txn.get("session_id")
    txn_type = txn.get("type")

    if txn_type == "workshop":
        reg = await db.registrations.find_one({"payment_session_id": session_id})
        if reg and reg.get("status") != "cancelled":
            await db.registrations.update_one(
                {"id": reg["id"]},
                {"$set": {"status": "cancelled", "cancelled_at": now_iso(),
                          "refund_cascade": True}},
            )
            # Free a seat
            if reg.get("workshop_id"):
                await db.workshops.update_one(
                    {"id": reg["workshop_id"]},
                    {"$inc": {"spots_left": 1}},
                )
            summary["registration_id"] = reg["id"]
            summary["workshop_id"] = reg.get("workshop_id")

    elif txn_type == "subscription":
        sub = await db.partner_subscriptions.find_one({"payment_session_id": session_id})
        if sub and sub.get("status") not in ("revoked", "superseded"):
            await db.partner_subscriptions.update_one(
                {"id": sub["id"]},
                {"$set": {"status": "revoked", "revoked_at": now_iso(),
                          "revoke_reason": "refund cascade", "expires_at": now_iso(),
                          "refund_cascade": True}},
            )
            summary["subscription_id"] = sub["id"]

    elif txn_type == "featured_slot":
        # featured.py sets featured_until on the partner_profile from txn metadata
        profile_id = (txn.get("metadata") or {}).get("partner_profile_id")
        if profile_id:
            await db.partner_profiles.update_one(
                {"id": profile_id},
                {"$set": {"featured_until": now_iso(), "refund_cascade_at": now_iso()}},
            )
            summary["partner_profile_id"] = profile_id

    elif txn_type == "research_promotion":
        artifact_id = (txn.get("metadata") or {}).get("artifact_id")
        if artifact_id:
            await db.research_artifacts.update_one(
                {"id": artifact_id},
                {"$set": {"promoted_until": now_iso(), "is_promoted": False,
                          "refund_cascade_at": now_iso()}},
            )
            summary["artifact_id"] = artifact_id

    elif txn_type == "order":
        order = await db.orders.find_one({"payment_session_id": session_id})
        if order and order.get("status") != "refunded":
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"status": "refunded", "refunded_at": now_iso()}},
            )
            summary["order_id"] = order["id"]

    elif txn_type == "sponsorship":
        sponsor = await db.sponsors.find_one({"payment_session_id": session_id})
        if sponsor:
            await db.sponsors.update_one(
                {"id": sponsor["id"]},
                {"$set": {"status": "refunded", "refunded_at": now_iso()}},
            )
            summary["sponsor_id"] = sponsor["id"]

    elif txn_type == "donation":
        donation = await db.donations.find_one({"payment_session_id": session_id})
        if donation:
            await db.donations.update_one(
                {"id": donation["id"]},
                {"$set": {"status": "refunded", "refunded_at": now_iso()}},
            )
            summary["donation_id"] = donation["id"]

    return summary


async def _clawback_credits(db, txn: dict) -> dict:
    """Walk the partner credits derived from this transaction. Reverse the earned
    ones; queue the already-paid ones for human follow-up."""
    session_id = txn.get("session_id")
    reversed_ids = []
    paid_clawbacks = []

    # On-site referrals attribute via payment_session_id field
    referrals = await db.referral_payouts.find(
        {"payment_session_id": session_id}, {"_id": 0},
    ).to_list(50)
    for r in referrals:
        if r.get("status") == "earned":
            await db.referral_payouts.update_one(
                {"id": r["id"]},
                {"$set": {"status": "reversed", "reversed_at": now_iso(),
                          "reverse_reason": "refund cascade"}},
            )
            reversed_ids.append(("referral_payouts", r["id"]))
        elif r.get("status") == "paid":
            # Already disbursed — record for human follow-up
            cb = {
                "id": gen_id(),
                "source": "on_site_referral",
                "credit_id": r["id"],
                "partner_user_id": r.get("partner_user_id"),
                "amount_usd": float(r.get("amount_usd") or 0),
                "original_payment_session_id": session_id,
                "original_txn_id": txn["id"],
                "status": "pending_recovery",
                "created_at": now_iso(),
            }
            await db.clawback_pending.insert_one(dict(cb))
            paid_clawbacks.append(cb)

    # Off-site credits attribute via source_session_id field (or none — best effort)
    off_site = await db.partner_off_site_credits.find(
        {"$or": [
            {"source_session_id": session_id},
            {"source_id": session_id},
        ]}, {"_id": 0},
    ).to_list(50)
    for o in off_site:
        if o.get("status") == "earned":
            await db.partner_off_site_credits.update_one(
                {"id": o["id"]},
                {"$set": {"status": "reversed", "reversed_at": now_iso(),
                          "reverse_reason": "refund cascade"}},
            )
            reversed_ids.append(("partner_off_site_credits", o["id"]))
        elif o.get("status") == "paid":
            cb = {
                "id": gen_id(),
                "source": "off_site_credit",
                "credit_id": o["id"],
                "partner_user_id": o.get("partner_user_id"),
                "amount_usd": float(o.get("amount_usd") or 0),
                "original_payment_session_id": session_id,
                "original_txn_id": txn["id"],
                "status": "pending_recovery",
                "created_at": now_iso(),
            }
            await db.clawback_pending.insert_one(dict(cb))
            paid_clawbacks.append(cb)

    return {
        "reversed_count": len(reversed_ids),
        "reversed": reversed_ids,
        "paid_clawback_count": len(paid_clawbacks),
        "paid_clawback_total_usd": round(sum(c["amount_usd"] for c in paid_clawbacks), 2),
    }


async def run_refund_cascade(
    db, *, txn_id: str, actor: dict, reason: str,
    skip_stripe: bool = False, dispute_id: Optional[str] = None,
) -> dict:
    """Top-level entry. Returns a dict with everything that happened.

    `skip_stripe` lets callers run the cascade for non-Stripe artifacts
    (e.g. comp'd subscriptions whose session_id starts with 'comp_').
    """
    txn = await db.payment_transactions.find_one({"id": txn_id}, {"_id": 0})
    if not txn:
        raise ValueError(f"Transaction {txn_id} not found")
    if txn.get("payment_status") == "refunded":
        raise ValueError("Transaction already refunded")

    # 1. Stripe refund (optional)
    refund_result: dict
    if skip_stripe or not txn.get("session_id") or txn["session_id"].startswith("comp_"):
        refund_result = {"status": "skipped", "refund_id": None, "amount": None, "error": None}
    else:
        refund_result = await refund_session(txn["session_id"])

    # 2. Mark the source transaction
    await db.payment_transactions.update_one(
        {"id": txn_id},
        {"$set": {
            "payment_status": "refunded",
            "refunded_at": now_iso(),
            "refund_result": refund_result,
            "refund_reason": reason,
        }},
    )

    # 3 + 4. Side-effects + credit clawback
    side_effects = await _reverse_side_effects(db, txn)
    credits_summary = await _clawback_credits(db, txn)

    # 5. Cascade record
    cascade = {
        "id": gen_id(),
        "txn_id": txn_id,
        "txn_type": txn.get("type"),
        "txn_amount": float(txn.get("amount") or 0),
        "actor_id": actor["id"],
        "actor_name": f"{actor.get('first_name', '')} {actor.get('last_name', '')}".strip(),
        "reason": reason,
        "dispute_id": dispute_id,
        "stripe_refund": refund_result,
        "side_effects": side_effects,
        "credit_clawback": credits_summary,
        "created_at": now_iso(),
    }
    await db.refund_cascades.insert_one(dict(cascade))

    await log_action(
        db, actor, "refund.cascade",
        target_type="payment_transaction", target_id=txn_id,
        metadata={
            "amount": cascade["txn_amount"], "type": cascade["txn_type"],
            "stripe_status": refund_result.get("status"),
            "reversed_credits": credits_summary["reversed_count"],
            "paid_clawback_total": credits_summary["paid_clawback_total_usd"],
            "dispute_id": dispute_id,
        },
    )

    return cascade
