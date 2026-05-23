"""Runtime seed helpers — run on EVERY startup, idempotent by design.

Distinct from `seed_data.seed_if_empty` which only fires on a fresh DB.
This module handles two production-critical jobs:

1. `ensure_catalog_seeded` — backfills the 50 AI-generated catalog items from
   `data/catalog.json` whenever they're missing (keyed on product `slug`).
   Uses the committed PNGs under `static/products/<slug>.png`; never calls
   the image generator at runtime. Safe to call on every boot.

2. `repair_known_broken_images` — heals two specific seeded products whose
   original Unsplash CDN URLs went stale. Looks them up by NAME (since
   product IDs differ across environments) and rewrites `image_url` to the
   stable committed-PNG path.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from models import gen_id, now_iso

logger = logging.getLogger("birthright.runtime_seed")

BACKEND_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BACKEND_DIR / "data" / "catalog.json"
STATIC_DIR = BACKEND_DIR / "static" / "products"

# Mapping of product NAME -> stable committed PNG filename. Add entries here
# any time a seeded product's image_url needs to be self-healed across deploys.
KNOWN_IMAGE_REPAIRS: dict[str, str] = {
    "Birthright Hardcover Journal": "birthright-hardcover-journal.png",
    "Enamel Pin — Flame": "enamel-pin-flame.png",
}


async def ensure_catalog_seeded(db) -> dict:
    """Insert any items from catalog.json whose `slug` is missing in DB.

    Returns a small summary dict for logging. Never raises — log + skip on error.
    """
    if not CATALOG_PATH.exists():
        logger.warning(f"catalog.json not found at {CATALOG_PATH} — skipping catalog seed")
        return {"inserted": 0, "skipped": 0, "missing_catalog": True}

    try:
        catalog = json.loads(CATALOG_PATH.read_text())
        items = catalog.get("items", [])
    except Exception as e:
        logger.error(f"catalog.json parse failed: {e}")
        return {"inserted": 0, "skipped": 0, "parse_error": True}

    # Build set of slugs already in DB
    existing: set[str] = set()
    async for p in db.products.find({"slug": {"$exists": True}}, {"slug": 1, "_id": 0}):
        if p.get("slug"):
            existing.add(p["slug"])

    to_insert: list[dict] = []
    for item in items:
        slug = item.get("slug")
        if not slug or slug in existing:
            continue
        png_path = STATIC_DIR / f"{slug}.png"
        image_url = (
            f"/api/static/products/{slug}.png"
            if png_path.exists()
            else "/api/static/products/_placeholder.png"
        )
        to_insert.append({
            "id": gen_id(),
            "slug": slug,
            "name": item["name"],
            "description": item["description"],
            "price": float(item["price"]),
            "type": item.get("type_override") or "merch",
            "workshop_id": None,
            "image_url": image_url,
            "inventory": int(item.get("inventory", 75)),
            "category": item["category"],
            "created_at": now_iso(),
        })

    if to_insert:
        await db.products.insert_many(to_insert)
        logger.info(f"catalog seed: inserted {len(to_insert)} products; {len(existing)} already present")
    else:
        logger.info(f"catalog seed: nothing to insert ({len(existing)} slug-tagged products in DB)")
    return {"inserted": len(to_insert), "skipped": len(existing)}


async def repair_known_broken_images(db) -> int:
    """Rewrite image_url for products whose CDN-hosted images went stale.

    Matches by product NAME (stable across environments) — only updates rows
    whose current image_url still points at the legacy host.
    Returns the number of repaired rows.
    """
    repaired = 0
    for name, filename in KNOWN_IMAGE_REPAIRS.items():
        new_url = f"/api/static/products/{filename}"
        result = await db.products.update_many(
            {
                "name": name,
                "$or": [
                    {"image_url": {"$regex": "^https?://"}},  # any external URL
                    {"image_url": {"$exists": False}},
                    {"image_url": ""},
                    {"image_url": {"$ne": new_url}},  # also re-point old self-hosted IDs
                ],
            },
            {"$set": {"image_url": new_url}},
        )
        if result.modified_count:
            logger.info(f"image repair: {result.modified_count}x {name!r} -> {new_url}")
            repaired += result.modified_count
    return repaired
