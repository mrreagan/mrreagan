"""POD order dispatch — Phase 6.

When a Stripe-paid order contains items flagged `fulfillable_via=printful` or
`fulfillable_via=lulu`, dispatch real fulfillment orders to the respective
provider. Persist the returned provider IDs + status onto the order doc so
the customer can see "in production" → "shipped".

Routing rules:
  - Each line item is dispatched independently (an order can mix Birthright-
    fulfilled merch, Printful merch, and Lulu books in one Stripe charge).
  - Printful + Lulu calls are best-effort: a failure logs an error but does
    NOT roll back the Stripe charge (we don't refund customers because a
    POD provider was briefly down). Failed dispatches are recorded as
    fulfillment status `failed_to_dispatch` for admin retry.
  - Both providers run in their respective sandbox/production envs per
    PRINTFUL_API_TOKEN and LULU_ENV settings.
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from utils import lulu_client as lulu
from utils import printful_client as printful

logger = logging.getLogger("birthright.order_dispatch")


# ============ Address adapters ============
def _address_to_printful(addr: Dict[str, Any], contact_email: str) -> Dict[str, Any]:
    """Map our shipping_address dict → Printful recipient shape."""
    return {
        "name": addr.get("name") or "Birthright Customer",
        "address1": addr.get("address1") or addr.get("street1") or "",
        "address2": addr.get("address2") or "",
        "city": addr.get("city") or "",
        "state_code": addr.get("state_code") or addr.get("state") or "",
        "country_code": addr.get("country_code") or addr.get("country") or "US",
        "zip": addr.get("postcode") or addr.get("zip") or "",
        "phone": addr.get("phone_number") or "",
        "email": contact_email,
    }


def _address_to_lulu(addr: Dict[str, Any]) -> Dict[str, Any]:
    """Map our shipping_address dict → Lulu shipping_address shape."""
    return {
        "name": addr.get("name") or "Birthright Customer",
        "street1": addr.get("street1") or addr.get("address1") or "",
        "street2": addr.get("street2") or addr.get("address2") or "",
        "city": addr.get("city") or "",
        "state_code": addr.get("state_code") or addr.get("state") or "",
        "country_code": addr.get("country_code") or addr.get("country") or "US",
        "postcode": addr.get("postcode") or addr.get("zip") or "",
        "phone_number": addr.get("phone_number") or "555-555-5555",
    }


# ============ Per-item dispatch ============
async def _dispatch_printful_item(
    *, product: Dict[str, Any], quantity: int, recipient: Dict[str, Any], external_id: str,
) -> Dict[str, Any]:
    variant_id = product.get("printful_sync_variant_id")
    if not variant_id:
        raise ValueError("Product missing printful_sync_variant_id")
    confirm = (os.environ.get("PRINTFUL_AUTO_CONFIRM") or "false").lower() == "true"
    result = await printful.create_order(
        external_id=external_id,
        recipient=recipient,
        items=[{"sync_variant_id": int(variant_id), "quantity": int(quantity)}],
        confirm=confirm,
    )
    return {
        "provider": "printful",
        "provider_order_id": str(result.get("id") or ""),
        "status": (result.get("status") or "draft"),
        "confirmed": confirm,
    }


async def _dispatch_lulu_item(
    *, product: Dict[str, Any], quantity: int, shipping_address: Dict[str, Any],
    contact_email: str, external_id: str,
) -> Dict[str, Any]:
    if not product.get("lulu_pod_package_id") or not product.get("lulu_interior_pdf_url"):
        raise ValueError("Product missing lulu config (pod_package_id / interior_pdf_url)")
    result = await lulu.create_print_job(
        contact_email=contact_email,
        external_id=external_id,
        pod_package_id=product["lulu_pod_package_id"],
        page_count=int(product.get("lulu_page_count") or 144),
        title=product.get("name", "Birthright Journal")[:60],
        cover_url=product["lulu_cover_pdf_url"],
        interior_url=product["lulu_interior_pdf_url"],
        shipping_address=_address_to_lulu(shipping_address),
        quantity=int(quantity),
    )
    status_obj = result.get("status")
    status_name = status_obj.get("name") if isinstance(status_obj, dict) else str(status_obj or "CREATED")
    return {
        "provider": "lulu",
        "provider_order_id": str(result.get("id") or ""),
        "status": status_name,
        "env": result.get("lulu_env") or (os.environ.get("LULU_ENV") or "sandbox"),
    }


# ============ Public entry point ============
async def dispatch_order(db, order: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Walk an order's line items; dispatch each POD item; return per-item statuses.

    Returns a list of fulfillment records (one per item), shaped:
      {product_id, quantity, provider | None, provider_order_id, status, error?}
    """
    shipping_address = order.get("shipping_address") or {}
    contact_email = order.get("contact_email") or "fulfillment@birthright.org"
    items = order.get("items") or []
    fulfillments: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        pid = item.get("product_id")
        qty = int(item.get("quantity", 1) or 1)
        product = await db.products.find_one({"id": pid}, {"_id": 0}) if pid else None
        record: Dict[str, Any] = {
            "product_id": pid,
            "quantity": qty,
            "provider": None,
            "provider_order_id": None,
            "status": "fulfilled_by_birthright",
        }
        if not product:
            record["status"] = "product_not_found"
            fulfillments.append(record)
            continue

        provider = product.get("fulfillable_via")
        if not provider:
            # Birthright-fulfilled merch (no POD); nothing to dispatch.
            fulfillments.append(record)
            continue
        if not shipping_address or not shipping_address.get("address1") and not shipping_address.get("street1"):
            record.update({"status": "failed_to_dispatch", "provider": provider,
                            "error": "Missing shipping address on order"})
            fulfillments.append(record)
            continue

        # Printful caps external_id at 32 chars (alphanumeric + dash/underscore).
        # Lulu allows up to 60. Use a compact form that fits Printful's window.
        external_id = f"br-{order['id'][:8]}-{idx}-{uuid.uuid4().hex[:8]}"
        try:
            if provider == "printful":
                result = await _dispatch_printful_item(
                    product=product, quantity=qty,
                    recipient=_address_to_printful(shipping_address, contact_email),
                    external_id=external_id,
                )
            elif provider == "lulu":
                result = await _dispatch_lulu_item(
                    product=product, quantity=qty,
                    shipping_address=shipping_address,
                    contact_email=contact_email,
                    external_id=external_id,
                )
            else:
                record["status"] = f"unknown_provider:{provider}"
                fulfillments.append(record)
                continue
            record.update(result)
        except Exception as ex:
            logger.exception("Dispatch failed for product %s via %s", pid, provider)
            record.update({"status": "failed_to_dispatch", "provider": provider,
                            "error": str(ex)[:300]})
        fulfillments.append(record)
    return fulfillments


# ============ Status normalization for customer-facing view ============
CUSTOMER_STATUS_MAP = {
    # Birthright
    "fulfilled_by_birthright": "Preparing",
    "product_not_found": "Issue with order",
    "failed_to_dispatch": "Issue with fulfillment",
    # Printful
    "draft": "Preparing for printing",
    "pending": "Confirmed — being printed",
    "inprocess": "Being printed",
    "onhold": "On hold",
    "partial": "Partially shipped",
    "fulfilled": "Shipped",
    "canceled": "Canceled",
    # Lulu (note: Lulu uses ALLCAPS)
    "CREATED": "Preparing for printing",
    "UNPAID": "Awaiting payment",
    "PAYMENT_IN_PROGRESS": "Confirming payment",
    "PRODUCTION_READY": "Ready to print",
    "PRODUCTION_DELAYED": "Production delayed",
    "IN_PRODUCTION": "Being printed",
    "SHIPPED": "Shipped",
    "REJECTED": "Print files rejected",
    "CANCELED": "Canceled",
}


def customer_friendly_status(raw: Optional[str]) -> str:
    if not raw:
        return "Preparing"
    return CUSTOMER_STATUS_MAP.get(str(raw), str(raw).replace("_", " ").title())
