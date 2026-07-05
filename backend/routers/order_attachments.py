"""Buyer file uploads for vendor-custom orders.

Used when a product is `fulfillable_via = "vendor_custom_form"` — the buyer
uploads their artwork/text file on the product detail page BEFORE checkout.
The returned `attachment_id` is included in the cart item and then handed
to the vendor dispatch flow after Stripe payment.
"""
from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from models import gen_id, now_iso

logger = logging.getLogger("birthright.order_attachments")
router = APIRouter(prefix="/products", tags=["order-attachments"])

ATTACHMENT_DIR = Path(__file__).resolve().parent.parent / "static" / "attachments"
ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)

# Per-file cap. 7C's engraving artwork rarely exceeds a few MB; leave headroom
# for higher-DPI PDFs. Keeping this in code so admins don't need env changes.
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_MIME_PREFIXES = ("image/", "application/pdf", "application/postscript",
                          "image/svg+xml", "application/illustrator",
                          "application/vnd.adobe.photoshop", "application/zip")


@router.post("/{product_id}/attachment")
async def upload_attachment(product_id: str, file: UploadFile = File(...)):
    """Store one file for a product-in-cart and return an `attachment_id`."""
    from database import db

    product = await db.products.find_one({"id": product_id}, {"_id": 0, "id": 1, "fulfillable_via": 1, "name": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.get("fulfillable_via") != "vendor_custom_form":
        raise HTTPException(status_code=400, detail="This product doesn't accept file uploads.")

    mime = (file.content_type or "").lower()
    if not any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {mime or 'unknown'}")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024*1024)}MB limit.")

    original_name = file.filename or "upload"
    safe_ext = Path(original_name).suffix.lower()[:8]
    stored_name = f"{secrets.token_urlsafe(16)}{safe_ext}"
    (ATTACHMENT_DIR / stored_name).write_bytes(contents)

    doc = {
        "id": gen_id(),
        "product_id": product_id,
        "original_name": original_name,
        "stored_name": stored_name,
        "mime": mime,
        "size": len(contents),
        "created_at": now_iso(),
    }
    await db.order_attachments.insert_one(doc)
    return {
        "attachment_id": doc["id"],
        "original_name": original_name,
        "size": len(contents),
    }
