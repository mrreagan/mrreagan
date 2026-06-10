"""Payments: Stripe checkout for workshop registration, products, donations, sponsorships."""
import os
import logging
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
from utils.mailer import send_email, attachment_from_bytes
from utils.email_templates import order_receipt, workshop_confirmation
from utils.calendar_qr import build_ics, build_qr_png

logger = logging.getLogger("birthright.checkout")

router = APIRouter(prefix="/checkout", tags=["checkout"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET") or None

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
    return StripeCheckout(
        api_key=STRIPE_API_KEY,
        webhook_url=webhook_url,
        webhook_secret=STRIPE_WEBHOOK_SECRET,
    )


def _extract_referral_code(request: Request) -> Optional[str]:
    """Read the referral cookie set by /api/r/{code} (if any)."""
    val = request.cookies.get("birthright_ref")
    if not val:
        return None
    val = val.strip().upper()
    return val if val.isalnum() and len(val) == 8 else None


@router.get("/sponsorship-tiers")
async def get_sponsorship_tiers():
    return [{"id": k, **v} for k, v in SPONSORSHIP_TIERS.items()]


def _resolve_workshop_pricing(workshop: dict) -> tuple[str, float]:
    """Return (tier, amount) based on early-bird cutoff."""
    from datetime import datetime, timezone
    if workshop.get("early_bird_until"):
        try:
            eb_until = datetime.fromisoformat(workshop["early_bird_until"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) < eb_until:
                return "early_bird", float(workshop["early_bird_price"])
        except Exception:
            pass
    return "regular", float(workshop["regular_price"])


async def _validate_workshop_registration(db, workshop_id: str, user_id: str) -> dict:
    """Ensure workshop exists, user not already registered, capacity available. Returns workshop doc."""
    w = await db.workshops.find_one({"id": workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if await db.registrations.find_one(
        {"workshop_id": workshop_id, "user_id": user_id, "payment_status": "paid"}
    ):
        raise HTTPException(status_code=400, detail="Already registered for this workshop")
    paid_count = await db.registrations.count_documents(
        {"workshop_id": workshop_id, "payment_status": "paid"}
    )
    if paid_count >= w["capacity"]:
        raise HTTPException(status_code=400, detail="Workshop is full. Join the waitlist instead.")
    return w


def _record_transaction(txn_type: str, session_id: str, user_id: Optional[str], amount: float, metadata: dict, **extra) -> dict:
    """Build a payment_transactions document."""
    return {
        "id": gen_id(),
        "session_id": session_id,
        "user_id": user_id,
        "type": txn_type,
        "amount": amount,
        "currency": "usd",
        "metadata": metadata,
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
        **extra,
    }


@router.post("/workshop")
async def checkout_workshop(
    data: WorkshopCheckoutRequest, request: Request, user: dict = Depends(get_current_user)
):
    from database import db
    w = await _validate_workshop_registration(db, data.workshop_id, user["id"])
    tier, amount = _resolve_workshop_pricing(w)

    success_url = f"{data.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&type=workshop"
    cancel_url = f"{data.origin_url}/workshops/{w['slug']}"
    metadata = {
        "type": "workshop",
        "workshop_id": data.workshop_id,
        "user_id": user["id"],
        "pricing_tier": tier,
    }
    ref_code = _extract_referral_code(request)
    if ref_code:
        metadata["referral_code"] = ref_code
    stripe_checkout = get_stripe(request)
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(
        CheckoutSessionRequest(
            amount=amount, currency="usd", success_url=success_url, cancel_url=cancel_url, metadata=metadata,
        )
    )
    await db.payment_transactions.insert_one(
        _record_transaction(
            "workshop", session.session_id, user["id"], amount, metadata,
            items=[{"workshop_id": data.workshop_id, "pricing_tier": tier}],
        )
    )
    return {"url": session.url, "session_id": session.session_id}


async def _validate_cart_and_total(db, items, user) -> tuple[float, list, bool]:
    """Validate items, enforce gating, compute total server-side.
    Returns (total, line_items, needs_shipping)."""
    from routers.gallery import gallery_markup_for  # noqa: PLC0415
    total = 0.0
    line_items = []
    needs_shipping = False
    for item in items:
        p = await db.products.find_one({"id": item.product_id})
        if not p:
            raise HTTPException(status_code=400, detail=f"Product not found: {item.product_id}")
        if p.get("is_off_site"):
            raise HTTPException(
                status_code=400,
                detail=f"'{p.get('name')}' is sold on the vendor's own site and can't be checked out through Birthright.",
            )
        if p.get("is_gallery_artwork") and p.get("availability") not in (None, "available"):
            raise HTTPException(
                status_code=400,
                detail=f"'{p.get('name')}' is not currently available for purchase.",
            )
        if p.get("fulfillable_via") in ("printful", "lulu") or p.get("is_gallery_artwork"):
            needs_shipping = True
        await _enforce_material_gating(db, p, user)
        qty = max(1, int(item.quantity))
        line_total = float(p["price"]) * qty
        markup = gallery_markup_for(p) * qty
        total += line_total + markup
        line_items.append({
            "product_id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "quantity": qty,
            "is_gallery_artwork": bool(p.get("is_gallery_artwork")),
            "gallery_artist_user_id": p.get("gallery_artist_user_id"),
            "gallery_artist_name": p.get("gallery_artist_name"),
            "foundation_markup_per_unit": round(gallery_markup_for(p), 2),
        })
    return round(total, 2), line_items, needs_shipping


async def _enforce_material_gating(db, product: dict, user: Optional[dict]) -> None:
    """Workshop materials are restricted to registered (paid) participants and admins."""
    if product["type"] != "workshop_material":
        return
    if not user:
        raise HTTPException(status_code=403, detail="Sign in to purchase workshop materials")
    reg = await db.registrations.find_one(
        {"workshop_id": product["workshop_id"], "user_id": user["id"], "payment_status": "paid"}
    )
    if not reg and user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Materials for this workshop are limited to registered participants.",
        )


@router.post("/products")
async def checkout_products(
    data: CheckoutRequest, request: Request, user: Optional[dict] = Depends(get_current_user_optional)
):
    from database import db
    if not data.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    total, line_items, needs_shipping = await _validate_cart_and_total(db, data.items, user)
    if needs_shipping:
        addr = data.shipping_address or {}
        required = ("name", "address1", "city", "state_code", "postcode")
        missing = [k for k in required if not (addr.get(k) or "").strip()]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Shipping address is required (this order contains printed items). "
                    f"Missing: {', '.join(missing)}"
                ),
            )
    user_id = user["id"] if user else None
    success_url = f"{data.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&type=order"
    cancel_url = f"{data.origin_url}/shop"
    metadata = {"type": "order", "user_id": user_id or "guest", "item_count": str(len(line_items))}
    ref_code = _extract_referral_code(request)
    if ref_code:
        metadata["referral_code"] = ref_code
    stripe_checkout = get_stripe(request)
    session = await stripe_checkout.create_checkout_session(
        CheckoutSessionRequest(
            amount=total, currency="usd", success_url=success_url, cancel_url=cancel_url, metadata=metadata,
        )
    )
    await db.payment_transactions.insert_one(
        _record_transaction(
            "order", session.session_id, user_id, total, metadata,
            items=line_items, shipping_address=data.shipping_address,
        )
    )
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


async def _create_registration_from_txn(db, txn: dict) -> None:
    meta = txn.get("metadata", {})
    existing = await db.registrations.find_one(
        {"workshop_id": meta["workshop_id"], "user_id": meta["user_id"], "payment_status": "paid"}
    )
    if existing:
        return
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
        "reminder_sent": False,
        "created_at": now_iso(),
    }
    await db.registrations.insert_one(reg)
    # Referral attribution (if a community partner code was on the checkout)
    try:
        from routers.referrals import resolve_referral_for_checkout, record_referral
        attribution = await resolve_referral_for_checkout(db, meta.get("referral_code"))
        if attribution and attribution["partner_user_id"] != meta["user_id"]:
            workshop = await db.workshops.find_one({"id": meta["workshop_id"]}, {"_id": 0})
            await record_referral(db, txn, attribution, {
                "type": "workshop", "id": meta["workshop_id"],
                "label": workshop["title"] if workshop else "",
            })
    except Exception as e:
        logger.error(f"workshop referral attribution failed: {e}")
    # Send workshop confirmation email
    try:
        user = await db.users.find_one({"id": meta["user_id"]}, {"_id": 0, "password_hash": 0})
        workshop = await db.workshops.find_one({"id": meta["workshop_id"]}, {"_id": 0})
        if user and workshop and user.get("email"):
            app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
            check_in_code = workshop.get("check_in_code", "—")
            subject, html, text = workshop_confirmation(
                first_name=user["first_name"], workshop=workshop, registration=reg,
                check_in_code=check_in_code, app_url=app_url,
            )
            ics_bytes = build_ics(workshop)
            qr_bytes = build_qr_png(check_in_code)
            attachments = [
                attachment_from_bytes(f"{workshop['slug']}.ics", ics_bytes, "text/calendar"),
                attachment_from_bytes("check-in-qr.png", qr_bytes, "image/png"),
            ]
            await send_email(
                to=user["email"], subject=subject, html=html, text=text,
                attachments=attachments, template_name="workshop_confirmation",
                metadata={"workshop_id": workshop["id"], "registration_id": reg["id"]},
            )
    except Exception as e:
        logger.error(f"workshop confirmation email failed: {e}")


async def _create_order_from_txn(db, txn: dict) -> None:
    items = txn.get("items", [])
    # Pre-resolve customer email for both receipts and POD fulfillment.
    contact_email: Optional[str] = None
    if txn.get("user_id"):
        u = await db.users.find_one({"id": txn["user_id"]}, {"_id": 0, "email": 1})
        if u:
            contact_email = u.get("email")
    order = {
        "id": gen_id(),
        "user_id": txn.get("user_id"),
        "items": items,
        "total": txn["amount"],
        "shipping_address": txn.get("shipping_address"),
        "contact_email": contact_email,
        "payment_session_id": txn["session_id"],
        "status": "paid",
        "created_at": now_iso(),
    }
    await db.orders.insert_one(order)
    for item in items:
        await db.products.update_one(
            {"id": item["product_id"]}, {"$inc": {"inventory": -item["quantity"]}}
        )

    # Phase 6 — Dispatch POD-fulfilled items to their providers.
    try:
        from utils.order_dispatch import dispatch_order
        fulfillments = await dispatch_order(db, order)
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {"fulfillments": fulfillments, "fulfillment_at": now_iso()}},
        )
        logger.info(
            "order %s: dispatched %s line item(s) (%s POD)",
            order["id"], len(fulfillments),
            sum(1 for f in fulfillments if f.get("provider")),
        )
    except Exception as e:
        logger.exception("order dispatch failed: %s", e)
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {"fulfillments": [], "dispatch_error": str(e)[:300]}},
        )

    # Gallery patronage payouts (artist receives list_price; Foundation
    # kept the 20% hospitality markup at checkout).
    try:
        from routers.artist_partnership import record_patronage_payouts
        payout_ids = await record_patronage_payouts(db, order)
        if payout_ids:
            logger.info("order %s: %d artist patronage payout(s) created",
                         order["id"], len(payout_ids))
    except Exception as e:
        logger.exception("artist patronage payout creation failed: %s", e)
    # Referral attribution
    try:
        from routers.referrals import resolve_referral_for_checkout, record_referral
        meta = txn.get("metadata", {})
        attribution = await resolve_referral_for_checkout(db, meta.get("referral_code"))
        if attribution and attribution["partner_user_id"] != txn.get("user_id"):
            await record_referral(db, txn, attribution, {
                "type": "order", "id": order["id"],
                "label": f"Order #{order['id'][:8]} ({len(items)} item{'' if len(items) == 1 else 's'})",
            })
    except Exception as e:
        logger.error(f"order referral attribution failed: {e}")
    # Send order receipt
    try:
        if txn.get("user_id"):
            user = await db.users.find_one({"id": txn["user_id"]}, {"_id": 0, "password_hash": 0})
            if user and user.get("email"):
                app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
                subject, html, text = order_receipt(
                    first_name=user["first_name"], items=items,
                    total=txn["amount"], order_id=order["id"], app_url=app_url,
                )
                await send_email(
                    to=user["email"], subject=subject, html=html, text=text,
                    template_name="order_receipt", metadata={"order_id": order["id"]},
                )
    except Exception as e:
        logger.error(f"order receipt email failed: {e}")


async def _create_sponsor_from_txn(db, txn: dict) -> None:
    await db.sponsors.insert_one({
        "id": gen_id(),
        "user_id": txn.get("user_id"),
        "tier_id": txn.get("tier_id"),
        "amount": txn["amount"],
        "payment_session_id": txn["session_id"],
        "status": "active",
        "public_display": True,
        "created_at": now_iso(),
    })


async def _create_donation_from_txn(db, txn: dict) -> None:
    await db.donations.insert_one({
        "id": gen_id(),
        "user_id": txn.get("user_id"),
        "amount": txn["amount"],
        "note": txn.get("metadata", {}).get("note", ""),
        "payment_session_id": txn["session_id"],
        "created_at": now_iso(),
    })


_PAID_HANDLERS = {
    "workshop": _create_registration_from_txn,
    "order": _create_order_from_txn,
    "sponsorship": _create_sponsor_from_txn,
    "donation": _create_donation_from_txn,
}


async def _create_subscription_from_txn(db, txn: dict) -> None:
    """Dispatch to subscriptions module so router code owns its data model."""
    from routers.subscriptions import create_subscription_from_txn
    await create_subscription_from_txn(db, txn)


_PAID_HANDLERS["subscription"] = _create_subscription_from_txn


async def _activate_featured_from_txn(db, txn: dict) -> None:
    """Dispatch to featured module."""
    from routers.featured import activate_featured_from_txn
    await activate_featured_from_txn(db, txn)


_PAID_HANDLERS["featured_slot"] = _activate_featured_from_txn


async def _activate_research_promotion(db, txn: dict) -> None:
    from routers.research import activate_research_promotion
    await activate_research_promotion(db, txn)


_PAID_HANDLERS["research_promotion"] = _activate_research_promotion


async def _credit_ai_wallet_topup(db, txn: dict) -> None:
    from routers.ai_wallet import credit_topup_from_txn
    await credit_topup_from_txn(db, txn)


_PAID_HANDLERS["ai_wallet_topup"] = _credit_ai_wallet_topup


async def _process_paid_transaction(txn: dict):
    """Handle side-effects of a successful payment by dispatching to the correct handler."""
    from database import db
    handler = _PAID_HANDLERS.get(txn["type"])
    if handler:
        await handler(db, txn)


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
