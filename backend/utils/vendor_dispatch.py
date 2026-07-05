"""Vendor custom-form middleman dispatch.

When a birthright-paid order contains items marked
`fulfillable_via = "vendor_custom_form"` (e.g., 7C's Farmstead leather patches),
we:
  1. Build a prefilled URL for the vendor's own custom-order form (Formester,
     Google Forms, etc.) using the field map stored on the product.
  2. Email the vendor with the link and any file attachments the buyer
     uploaded during checkout.
  3. Log a `vendor_orders` row so admins can reconcile wholesale payments.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from utils.mailer import send_email, attachment_from_bytes

logger = logging.getLogger("birthright.vendor_dispatch")

# Where uploaded attachments are persisted on disk.
ATTACHMENT_DIR = Path(__file__).resolve().parent.parent / "static" / "attachments"


def _shipping_to_source(shipping: Dict[str, Any], contact_email: Optional[str]) -> Dict[str, str]:
    """Flatten our shipping_address + email into the source keys the field map expects."""
    full = (shipping.get("name") or "").strip()
    first, _, last = full.partition(" ")
    return {
        "first_name": first or full,
        "last_name":  last,
        "email":      contact_email or "",
        "phone":      shipping.get("phone_number") or shipping.get("phone") or "",
        "address1":   shipping.get("address1") or shipping.get("street1") or "",
        "address2":   shipping.get("address2") or shipping.get("street2") or "",
        "city":       shipping.get("city") or "",
        "state":      shipping.get("state_code") or shipping.get("state") or "",
        "postal_code":shipping.get("postcode") or shipping.get("zip") or "",
        "country":    shipping.get("country_code") or shipping.get("country") or "US",
    }


def build_prefilled_url(
    product: Dict[str, Any],
    quantity: int,
    order_id: str,
    shipping: Dict[str, Any],
    contact_email: Optional[str],
    attachment_filenames: Optional[List[str]] = None,
) -> str:
    """Return the vendor's custom-order form URL with every field prefilled
    that we know how to fill. `attachment_filenames` is optional and kept
    only for future vendors that require per-order artwork (7C's does not —
    they already have the files for every SKU we sell)."""
    base = product.get("vendor_form_url")
    if not base:
        return ""
    query: Dict[str, str] = dict(product.get("vendor_form_query_base") or {})
    field_map: Dict[str, str] = product.get("vendor_form_field_map") or {}

    quantity_summary = f"{quantity} × {product.get('name', 'birthright patch')}"
    # Keep the Message minimal — every patch is an existing SKU that 7C's
    # already has files for. No customization is allowed on these orders.
    message = f"{product.get('name', 'birthright leather patch')}, quantity: {quantity}"

    sources = _shipping_to_source(shipping, contact_email)
    sources.update({
        "quantity_summary": quantity_summary,
        "message":          message,
        "product_choice":   product.get("vendor_product_choice_value") or "Other",
        "referral_source":  product.get("vendor_referral_source") or "Birthright",
    })

    for form_field, source_key in field_map.items():
        val = sources.get(source_key, "")
        if val:
            query[form_field] = str(val)

    return f"{base}?{urlencode(query)}"


async def dispatch_vendor_item(
    *,
    db,
    product: Dict[str, Any],
    quantity: int,
    order: Dict[str, Any],
    item_attachment_ids: List[str],
) -> Dict[str, Any]:
    """Send the vendor the prefilled form URL + attachments, and log a
    `vendor_orders` row. Returns a fulfillment record."""
    from models import gen_id, now_iso
    order_id = order["id"]
    contact_email = order.get("contact_email")
    shipping = order.get("shipping_address") or {}

    # Load attachment records + on-disk files
    attachments_meta: List[Dict[str, Any]] = []
    email_attachments = []
    if item_attachment_ids:
        docs = await db.order_attachments.find(
            {"id": {"$in": item_attachment_ids}}, {"_id": 0},
        ).to_list(20)
        for d in docs:
            attachments_meta.append(d)
            fp = ATTACHMENT_DIR / d["stored_name"]
            if fp.exists():
                email_attachments.append(
                    attachment_from_bytes(d["original_name"], fp.read_bytes(), d.get("mime") or "application/octet-stream")
                )

    prefill_url = build_prefilled_url(
        product=product, quantity=quantity, order_id=order_id,
        shipping=shipping, contact_email=contact_email,
        attachment_filenames=[a["original_name"] for a in attachments_meta],
    )

    vendor_order = {
        "id": gen_id(),
        "order_id": order_id,
        "product_id": product["id"],
        "product_name": product.get("name"),
        "vendor_slug": product.get("vendor_slug"),
        "vendor_name": product.get("vendor_name"),
        "buyer_email": contact_email,
        "buyer_name": shipping.get("name"),
        "shipping_address": shipping,
        "quantity": quantity,
        "retail_price": product.get("price") or 0,
        "wholesale_price": product.get("wholesale_price") or 0,
        "margin": (product.get("price") or 0) - (product.get("wholesale_price") or 0),
        "prefilled_form_url": prefill_url,
        "attachments": attachments_meta,
        "vendor_notified_at": None,
        "vendor_notification_error": None,
        "wholesale_paid_at": None,
        "wholesale_payment_reference": None,
        "status": "pending_vendor_ack",
        "created_at": now_iso(),
    }
    await db.vendor_orders.insert_one(vendor_order)

    # Email the vendor
    vendor_email = os.environ.get(f"VENDOR_EMAIL_{(product.get('vendor_slug') or '').upper().replace('-', '_')}") \
        or os.environ.get("VENDOR_EMAIL_DEFAULT") \
        or "orders@7csfarmstead.com"
    admin_bcc = os.environ.get("VENDOR_ORDER_BCC")

    subject = f"[birthright.live] Reorder · {product.get('name')} × {quantity}"
    body_lines = [
        f"Hi {product.get('vendor_name') or 'partner'},",
        "",
        "Please fulfill another reorder of this existing SKU — no customization,",
        "use the file already on record for this patch. Ship directly to the buyer",
        "at the address below. Wholesale ${:.2f} × {} + shipping will be settled per".format(
            (product.get("wholesale_price") or 0), quantity
        ),
        "our standing arrangement (buyer already paid birthright retail + shipping).",
        "",
        "One-click submit — every field is prefilled on your custom-order form:",
        prefill_url,
        "",
        "Order details:",
        f"  Order ID:     birthright #{order_id[:8]}",
        f"  Product:      {product.get('name')}",
        f"  Quantity:     {quantity}",
        f"  Buyer:        {shipping.get('name') or contact_email}",
        f"  Email:        {contact_email}",
        f"  Ship to:      {shipping.get('address1', '')}, {shipping.get('city', '')}, {shipping.get('state_code') or shipping.get('state', '')} {shipping.get('postcode') or shipping.get('zip', '')}",
        "",
        "— birthright.live",
    ]
    text = "\n".join(body_lines)
    html = "<br>".join(body_lines).replace(prefill_url, f'<a href="{prefill_url}">{prefill_url}</a>')

    try:
        await send_email(
            to=vendor_email,
            subject=subject,
            html=html,
            text=text,
            attachments=email_attachments or None,
            template_name="vendor_custom_order",
            metadata={"order_id": order_id, "vendor_order_id": vendor_order["id"]},
        )
        # Also send a copy to the admin BCC address for audit if configured.
        if admin_bcc:
            try:
                await send_email(
                    to=admin_bcc,
                    subject=f"[cc] {subject}",
                    html=html, text=text,
                    attachments=email_attachments or None,
                    template_name="vendor_custom_order_admin_cc",
                    metadata={"order_id": order_id, "vendor_order_id": vendor_order["id"]},
                )
            except Exception as exc:
                logger.warning("admin bcc failed: %s", exc)
        await db.vendor_orders.update_one(
            {"id": vendor_order["id"]},
            {"$set": {"vendor_notified_at": now_iso(), "status": "notified"}},
        )
        notified = True
    except Exception as exc:
        logger.exception("vendor email failed for order %s: %s", order_id, exc)
        await db.vendor_orders.update_one(
            {"id": vendor_order["id"]},
            {"$set": {"vendor_notification_error": str(exc)[:400]}},
        )
        notified = False

    return {
        "provider": "vendor_custom_form",
        "provider_order_id": vendor_order["id"],
        "status": "vendor_notified" if notified else "vendor_notify_failed",
        "prefilled_form_url": prefill_url,
    }
