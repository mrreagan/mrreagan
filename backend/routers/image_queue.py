"""Admin-only additional-image generation queue.

Two flows live here:
  1. SCAN  — for every active product, ask an LLM to compare the
     description against the existing AI vision `image_caption`. If the
     description mentions a visual detail that the caption doesn't see
     (e.g., "flame stamped on the base" but the caption only sees the
     outside), an entry is queued with a generation prompt focused on
     that missing detail.
  2. PUBLISH / DISCARD — admin reviews ready images and either appends
     them to the product's `additional_images` or throws them away.

Endpoints (all admin):
  POST   /api/admin/products/image-queue/scan            run the scan job
  GET    /api/admin/products/image-queue                 list pending entries
  POST   /api/admin/products/image-queue/{entry_id}/generate
  POST   /api/admin/products/image-queue/{entry_id}/publish
  POST   /api/admin/products/image-queue/{entry_id}/discard
  POST   /api/admin/products/image-queue/queue           manual one-off

Storage: `pending_additional_images` collection with fields
  { id, product_id, product_name, prompt, status, image_url, error,
    created_at, generated_at }
status ∈ {queued, generating, ready, published, failed}
"""
from __future__ import annotations

import logging
import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import require_roles
from models import gen_id, now_iso

logger = logging.getLogger("birthright.image_queue")
router = APIRouter(prefix="/admin/products/image-queue", tags=["admin", "image-queue"])

ANALYSIS_MODEL = "claude-sonnet-4-5-20250929"
ANALYSIS_PROVIDER = "anthropic"


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or gen_id()[:8]


class QueueEntryCreate(BaseModel):
    product_id: str
    prompt: str = Field(min_length=10, max_length=2000)


class ScanResult(BaseModel):
    scanned: int
    queued: int
    skipped: int
    errors: int


async def _llm_detect_missing_detail(
    product_name: str,
    description: str,
    caption: Optional[str],
) -> Optional[str]:
    """Ask the LLM to spot details mentioned in the description that the
    image caption doesn't cover. Returns a focused image-gen prompt when
    a missing detail exists, otherwise None."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return None

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as exc:
        logger.warning("LLM library unavailable: %s", exc)
        return None

    system = (
        "You audit e-commerce product listings. Given a product name, marketing "
        "description, and an AI vision caption of the current hero photo, decide "
        "whether the description mentions a visible product detail that the "
        "current photo does NOT show. Common cases: a stamp/logo on the inside "
        "or underside of a vessel, an embroidered patch on the inside of a "
        "garment, a serial number on the back of a print, a debossed mark on "
        "the spine of a book, the texture of a finish that's hidden in the "
        "current angle.\n\n"
        "Respond in this exact format on a single line:\n"
        "NEEDS_SHOT: yes\nPROMPT: <50-150 word prompt for a second product "
        "photograph that shows the missing detail. Describe the object, the "
        "missing detail, the angle, and the studio aesthetic.>\n"
        "OR\n"
        "NEEDS_SHOT: no\nPROMPT:\n"
        "Be conservative — say no when the hero shot already covers the description."
    )
    user_msg = (
        f"PRODUCT NAME: {product_name}\n\n"
        f"DESCRIPTION:\n{description}\n\n"
        f"CURRENT IMAGE CAPTION (AI vision):\n{caption or '(no caption yet)'}\n"
    )
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"img-audit-{product_name[:30]}",
            system_message=system,
        ).with_model(ANALYSIS_PROVIDER, ANALYSIS_MODEL)
        resp = await chat.send_message(UserMessage(text=user_msg))
        text = (resp or "").strip()
        if "NEEDS_SHOT: no" in text.lower() or "needs_shot: no" in text:
            return None
        # Extract the prompt block (everything after "PROMPT:")
        m = re.search(r"PROMPT:\s*(.+)$", text, flags=re.DOTALL | re.IGNORECASE)
        prompt = m.group(1).strip() if m else ""
        if len(prompt) < 20:
            return None
        return prompt[:1800]
    except Exception as exc:
        logger.warning("LLM audit failed for %r: %s", product_name, exc)
        return None


@router.post("/scan")
async def scan_for_missing_details(user: dict = Depends(require_roles("admin"))) -> ScanResult:
    """Walk active products and queue an additional image for each one whose
    description references detail not in the current vision caption.
    Re-runs are idempotent — products with a non-failed pending entry are skipped.
    """
    from database import db

    cursor = db.products.find(
        {
            # Skip vendor off-site products (they manage their own imagery).
            "is_off_site": {"$ne": True},
            # Skip already-flagged sample audits to focus scans where it matters,
            # but include sample products too — the user wants those re-shot.
        },
        {"_id": 0, "id": 1, "name": 1, "description": 1, "image_caption": 1},
    )
    products = await cursor.to_list(2000)

    scanned = queued = skipped = errors = 0
    for p in products:
        scanned += 1
        # If an entry already exists for this product that's queued/ready/generating, skip
        existing = await db.pending_additional_images.find_one(
            {
                "product_id": p["id"],
                "status": {"$in": ["queued", "generating", "ready"]},
            }
        )
        if existing:
            skipped += 1
            continue
        try:
            prompt = await _llm_detect_missing_detail(
                p.get("name", ""),
                p.get("description", ""),
                p.get("image_caption"),
            )
        except Exception as exc:
            logger.warning("scan: audit failed for %s: %s", p.get("name"), exc)
            errors += 1
            continue
        if not prompt:
            skipped += 1
            continue
        await db.pending_additional_images.insert_one(
            {
                "id": gen_id(),
                "product_id": p["id"],
                "product_name": p.get("name"),
                "prompt": prompt,
                "status": "queued",
                "image_url": None,
                "error": None,
                "created_at": now_iso(),
                "generated_at": None,
            }
        )
        queued += 1
    return ScanResult(scanned=scanned, queued=queued, skipped=skipped, errors=errors)


@router.get("")
async def list_queue(
    status: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    items = await db.pending_additional_images.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.post("/queue")
async def queue_manual(
    data: QueueEntryCreate,
    user: dict = Depends(require_roles("admin")),
):
    """Manually queue an additional-image request for a specific product."""
    from database import db
    product = await db.products.find_one({"id": data.product_id}, {"_id": 0, "id": 1, "name": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    entry = {
        "id": gen_id(),
        "product_id": product["id"],
        "product_name": product.get("name"),
        "prompt": data.prompt.strip(),
        "status": "queued",
        "image_url": None,
        "error": None,
        "created_at": now_iso(),
        "generated_at": None,
    }
    await db.pending_additional_images.insert_one(entry)
    entry.pop("_id", None)
    return entry


@router.post("/{entry_id}/generate")
async def generate_entry(entry_id: str, user: dict = Depends(require_roles("admin"))):
    """Run Nano Banana for one queued entry. Synchronous (≈15-25s).
    On success status becomes 'ready' with the image_url set."""
    from database import db
    from utils.image_generator import generate_product_image

    entry = await db.pending_additional_images.find_one({"id": entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry["status"] not in ("queued", "failed"):
        raise HTTPException(status_code=400, detail=f"Entry already {entry['status']}")

    await db.pending_additional_images.update_one(
        {"id": entry_id}, {"$set": {"status": "generating", "error": None}}
    )
    try:
        # Stable filename per entry so re-runs overwrite cleanly.
        product = await db.products.find_one({"id": entry["product_id"]}, {"_id": 0, "slug": 1, "name": 1})
        slug = (product or {}).get("slug") or _slugify((product or {}).get("name") or "extra")
        file_stem = f"{slug}-extra-{entry_id[:8]}"
        image_url = await generate_product_image(
            prompt=entry["prompt"],
            file_stem=file_stem,
            session_id=f"queue-{entry_id}",
        )
        await db.pending_additional_images.update_one(
            {"id": entry_id},
            {"$set": {
                "status": "ready",
                "image_url": image_url,
                "generated_at": now_iso(),
                "error": None,
            }},
        )
        updated = await db.pending_additional_images.find_one({"id": entry_id}, {"_id": 0})
        return updated
    except Exception as exc:
        logger.error("generate_entry failed for %s: %s", entry_id, exc)
        await db.pending_additional_images.update_one(
            {"id": entry_id},
            {"$set": {"status": "failed", "error": str(exc)}},
        )
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}")


@router.post("/{entry_id}/publish")
async def publish_entry(entry_id: str, user: dict = Depends(require_roles("admin"))):
    """Append the generated image to the product's `additional_images` and
    mark the entry published. Idempotent against duplicate URLs."""
    from database import db
    entry = await db.pending_additional_images.find_one({"id": entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    if entry["status"] != "ready":
        raise HTTPException(status_code=400, detail="Entry is not ready to publish")
    image_url = entry["image_url"]
    product = await db.products.find_one({"id": entry["product_id"]}, {"_id": 0, "additional_images": 1})
    if not product:
        raise HTTPException(status_code=404, detail="Product no longer exists")
    existing = product.get("additional_images") or []
    if image_url not in existing:
        existing.append(image_url)
        await db.products.update_one(
            {"id": entry["product_id"]},
            {"$set": {"additional_images": existing}},
        )
    await db.pending_additional_images.update_one(
        {"id": entry_id},
        {"$set": {"status": "published"}},
    )
    return {"ok": True, "additional_images": existing}


@router.post("/{entry_id}/discard")
async def discard_entry(entry_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    res = await db.pending_additional_images.delete_one({"id": entry_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return {"ok": True}
