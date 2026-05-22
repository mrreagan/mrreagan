"""Payments: Stripe checkout for workshop registration, products, donations, sponsorships."""
import os
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionResponse,
    CheckoutStatusResponse,
    CheckoutSessionRequest,
)
from models import (
    CheckoutRequest,
    WorkshopCheckoutRequest,
    DonationRequest,
    SponsorshipRequest,
    gen_id,
    now_iso,
)
from auth_utils import get_current_user, get_current_user_optional

router = APIRouter(prefix="/checkout", tags=["checkout"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")

# Fixed sponsorship tiers - amounts defined server-side only
SPONSORSHIP_TIERS = {
    "amethyst": {"name": "Amethyst Sponsor", "amount": 250.0, "perks": "Recognition on website, quarterly impact updates"},
    "ruby": {"name": "Ruby Sponsor", "amount": 500.0, "perks": "Amethyst perks + invitation to annual gathering"},
    "sapphire": {"name": "Sapphire Sponsor", "amount": 1000.0, "perks": "Ruby perks + dedicated thank-you card from a workshop cohort"},
    "emerald": {"name": "Emerald Sponsor", "amount": 2500.0, "perks": "Sapphire perks + name on our Sponsors Wall"},
    "diamond": {"name": "Diamond Sponsor", "amount": 5000.0, "perks": "Emerald perks + sponsor a full workshop scholarship"},
}


def get_stripe(request: Request) -> StripeCheckout:
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)


@router.get("/sponsorship-tiers")
async def get_sponsorship_tiers():
    return [{"id": k, **v} for k, v in SPONSORSHIP_TIERS.items()]


@router.post("/workshop")
async def checkout_workshop(
    data: WorkshopCheckoutRequest, request: Request, user: dict = Depends(get_current_user)
):
    from database import db
    w = await db.workshops.find_one({"id": data.workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    # Check if already registered
    existing = await db.registrations.find_one(
        {"workshop_id": data.workshop_id, "user_id": user["id"], "payment_status": "paid"}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this workshop")
    # Check capacity
    paid_count = await db.registrations.count_documents(
        {"workshop_id": data.workshop_id, "payment_status": "paid"}
    )
    if paid_count >= w["capacity"]:
        raise HTTPException(status_code=400, detail="Workshop is full. Join the waitlist instead.")
    # Determine price (early bird vs regular)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    tier = "regular"
    amount = float(w["regular_price"])
    if w.get("early_bird_until"):
        try:
            eb_until = datetime.fromisoformat(w["early_bird_until"].replace("Z", "+00:00"))
            if now < eb_until:
                tier = "early_bird"
                amount = float(w["early_bird_price"])
        except Exception:
            pass

    success_url = f"{data.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&type=workshop"
    cancel_url = f"{data.origin_url}/workshops/{w['slug']}"

    stripe_checkout = get_stripe(request)
    metadata = {
        "type": "workshop",
        "workshop_id": data.workshop_id,
        "user_id": user["id"],
        "pricing_tier": tier,
    }
    checkout_req = CheckoutSessionRequest(
        amount=amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_req)

    # Record transaction
    txn = {
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"],
        "type": "workshop",
        "amount": amount,
        "currency": "usd",
        "metadata": metadata,
        "items": [{"workshop_id": data.workshop_id, "pricing_tier": tier}],
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    }
    await db.payment_transactions.insert_one(txn)
    return {"url": session.url, "session_id": session.session_id}


@router.post("/products")
async def checkout_products(
    data: CheckoutRequest, request: Request, user: Optional[dict] = Depends(get_current_user_optional)
):
    from database import db
    if not data.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    # Validate and compute total server-side
    total = 0.0
    line_items = []
    for item in data.items:
        p = await db.products.find_one({"id": item.product_id})
        if not p:
            raise HTTPException(status_code=400, detail=f"Product not found: {item.product_id}")
        # Workshop-material gating
        if p["type"] == "workshop_material":
            if not user:
                raise HTTPException(status_code=403, detail="Sign in to purchase workshop materials")
            reg = await db.registrations.find_one(
                {"workshop_id": p["workshop_id"], "user_id": user["id"], "payment_status": "paid"}
            )
            if not reg and user.get("role") != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Materials for this workshop are limited to registered participants.",
                )
        qty = max(1, int(item.quantity))
        total += float(p["price"]) * qty
        line_items.append({"product_id": p["id"], "name": p["name"], "price": p["price"], "quantity": qty})
    total = round(total, 2)
    success_url = f"{data.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&type=order"
    cancel_url = f"{data.origin_url}/shop"
    stripe_checkout = get_stripe(request)
    metadata = {
        "type": "order",
        "user_id": user["id"] if user else "guest",
        "item_count": str(len(line_items)),
    }
    checkout_req = CheckoutSessionRequest(
        amount=total, currency="usd", success_url=success_url, cancel_url=cancel_url, metadata=metadata
    )
    session = await stripe_checkout.create_checkout_session(checkout_req)
    txn = {
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"] if user else None,
        "type": "order",
        "amount": total,
        "currency": "usd",
        "metadata": metadata,
        "items": line_items,
        "shipping_address": data.shipping_address,
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    }
    await db.payment_transactions.insert_one(txn)
    return {"url": session.url, "session_id": session.session_id}


@router.post("/donation")
async def checkout_donation(
    data: DonationRequest, request: Request, user: Optional[dict] = Depends(get_current_user_optional)
):
    from database import db
    if data.amount < 1:
        raise HTTPException(status_code=400, detail="Minimum donation is $1")
    amount = round(float(data.amount), 2)
    success_url = f"{data.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&type=donation"
    cancel_url = f"{data.origin_url}/about"
    stripe_checkout = get_stripe(request)
    metadata = {
        "type": "donation",
        "user_id": user["id"] if user else "guest",
        "note": data.note or "",
    }
    checkout_req = CheckoutSessionRequest(
        amount=amount, currency="usd", success_url=success_url, cancel_url=cancel_url, metadata=metadata
    )
    session = await stripe_checkout.create_checkout_session(checkout_req)
    txn = {
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"] if user else None,
        "type": "donation",
        "amount": amount,
        "currency": "usd",
        "metadata": metadata,
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    }
    await db.payment_transactions.insert_one(txn)
    return {"url": session.url, "session_id": session.session_id}


@router.post("/sponsorship")
async def checkout_sponsorship(
    data: SponsorshipRequest, request: Request, user: Optional[dict] = Depends(get_current_user_optional)
):
    from database import db
    tier = SPONSORSHIP_TIERS.get(data.tier_id)
    if not tier:
        raise HTTPException(status_code=400, detail="Invalid sponsorship tier")
    amount = float(tier["amount"])
    success_url = f"{data.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&type=sponsorship"
    cancel_url = f"{data.origin_url}/sponsorship"
    stripe_checkout = get_stripe(request)
    metadata = {
        "type": "sponsorship",
        "tier_id": data.tier_id,
        "tier_name": tier["name"],
        "user_id": user["id"] if user else "guest",
    }
    checkout_req = CheckoutSessionRequest(
        amount=amount, currency="usd", success_url=success_url, cancel_url=cancel_url, metadata=metadata
    )
    session = await stripe_checkout.create_checkout_session(checkout_req)
    txn = {
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"] if user else None,
        "type": "sponsorship",
        "amount": amount,
        "currency": "usd",
        "metadata": metadata,
        "tier_id": data.tier_id,
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    }
    await db.payment_transactions.insert_one(txn)
    return {"url": session.url, "session_id": session.session_id}


@router.get("/status/{session_id}")
async def checkout_status(session_id: str, request: Request):
    from database import db
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # If already marked paid, just return
    if txn["payment_status"] == "paid":
        return {
            "payment_status": "paid",
            "status": "complete",
            "type": txn["type"],
            "amount": txn["amount"],
        }
    stripe_checkout = get_stripe(request)
    status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    update = {
        "payment_status": status.payment_status,
        "status": status.status,
    }
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})
    # Process side-effects only ONCE
    if status.payment_status == "paid" and txn["payment_status"] != "paid":
        await _process_paid_transaction({**txn, **update})
    return {
        "payment_status": status.payment_status,
        "status": status.status,
        "type": txn["type"],
        "amount": txn["amount"],
    }


async def _process_paid_transaction(txn: dict):
    """Handle side-effects of a successful payment."""
    from database import db
    t_type = txn["type"]
    if t_type == "workshop":
        meta = txn.get("metadata", {})
        # Create registration if not exists
        existing = await db.registrations.find_one(
            {"workshop_id": meta["workshop_id"], "user_id": meta["user_id"], "payment_status": "paid"}
        )
        if not existing:
            reg = {
                "id": gen_id(),
                "workshop_id": meta["workshop_id"],
                "user_id": meta["user_id"],
                "pricing_tier": meta.get("pricing_tier", "regular"),
                "amount_paid": txn["amount"],
                "payment_session_id": txn["session_id"],
                "payment_status": "paid",
                "checked_in": False,
                "checked_in_at": None,
                "created_at": now_iso(),
            }
            await db.registrations.insert_one(reg)
    elif t_type == "order":
        # Create order record
        order = {
            "id": gen_id(),
            "user_id": txn.get("user_id"),
            "items": txn.get("items", []),
            "total": txn["amount"],
            "shipping_address": txn.get("shipping_address"),
            "payment_session_id": txn["session_id"],
            "status": "paid",
            "created_at": now_iso(),
        }
        await db.orders.insert_one(order)
        # Decrement inventory
        for item in txn.get("items", []):
            await db.products.update_one(
                {"id": item["product_id"]}, {"$inc": {"inventory": -item["quantity"]}}
            )
    elif t_type == "sponsorship":
        sponsor = {
            "id": gen_id(),
            "user_id": txn.get("user_id"),
            "tier_id": txn.get("tier_id"),
            "amount": txn["amount"],
            "payment_session_id": txn["session_id"],
            "status": "active",
            "public_display": True,
            "created_at": now_iso(),
        }
        await db.sponsors.insert_one(sponsor)
    elif t_type == "donation":
        donation = {
            "id": gen_id(),
            "user_id": txn.get("user_id"),
            "amount": txn["amount"],
            "note": txn.get("metadata", {}).get("note", ""),
            "payment_session_id": txn["session_id"],
            "created_at": now_iso(),
        }
        await db.donations.insert_one(donation)


# Webhook endpoint registered separately on root /api
async def stripe_webhook(request: Request):
    from database import db
    stripe_checkout = get_stripe(request)
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    try:
        evt = await stripe_checkout.handle_webhook(body, signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")
    if evt.payment_status == "paid":
        txn = await db.payment_transactions.find_one({"session_id": evt.session_id})
        if txn and txn["payment_status"] != "paid":
            await db.payment_transactions.update_one(
                {"session_id": evt.session_id},
                {"$set": {"payment_status": "paid", "status": "complete"}},
            )
            await _process_paid_transaction({**txn, "payment_status": "paid"})
    return {"received": True}
