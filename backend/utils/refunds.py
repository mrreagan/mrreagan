"""Stripe refund helper. Uses the underlying stripe SDK directly with our test/live API key.

Refunds are processed against the payment_intent id which Stripe records on each
checkout session. We look up the session from our payment_transactions collection
to find the payment_intent, then call stripe.Refund.create.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import stripe

logger = logging.getLogger("birthright.refunds")


async def refund_session(session_id: str) -> dict:
    """Issue a full refund for a Stripe Checkout Session.

    Returns a dict with keys:
        status: 'succeeded' | 'pending' | 'failed'
        refund_id: stripe refund id (or None)
        amount: refunded amount in dollars (float) or None
        error: error string (only when status='failed')
    """
    stripe.api_key = os.environ.get("STRIPE_API_KEY", "")
    if not stripe.api_key:
        return {"status": "failed", "refund_id": None, "amount": None, "error": "STRIPE_API_KEY missing"}

    try:
        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
        payment_intent = session.get("payment_intent")
        if not payment_intent:
            return {"status": "failed", "refund_id": None, "amount": None,
                    "error": "No payment_intent on session (was the payment completed?)"}
        refund = await asyncio.to_thread(stripe.Refund.create, payment_intent=payment_intent)
        amount_dollars = (refund.get("amount") or 0) / 100.0
        return {
            "status": refund.get("status") or "pending",  # 'succeeded', 'pending', 'failed', 'canceled'
            "refund_id": refund.get("id"),
            "amount": amount_dollars,
            "error": None,
        }
    except stripe.error.InvalidRequestError as e:
        msg = str(e)
        logger.warning(f"refund InvalidRequestError for session {session_id}: {msg}")
        return {"status": "failed", "refund_id": None, "amount": None, "error": msg}
    except Exception as e:
        logger.error(f"refund failed for session {session_id}: {e}")
        return {"status": "failed", "refund_id": None, "amount": None, "error": str(e)}
