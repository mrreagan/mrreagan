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


def _load_catalog_items() -> tuple[list[dict] | None, dict | None]:
    """Read catalog.json. Returns (items, error_summary)."""
    if not CATALOG_PATH.exists():
        logger.warning(f"catalog.json not found at {CATALOG_PATH} — skipping catalog seed")
        return None, {"inserted": 0, "skipped": 0, "missing_catalog": True}
    try:
        catalog = json.loads(CATALOG_PATH.read_text())
        return catalog.get("items", []), None
    except Exception as e:
        logger.error(f"catalog.json parse failed: {e}")
        return None, {"inserted": 0, "skipped": 0, "parse_error": True}


async def _existing_slugs(db) -> set[str]:
    """Return the set of product slugs already present in MongoDB."""
    existing: set[str] = set()
    async for p in db.products.find({"slug": {"$exists": True}}, {"slug": 1, "_id": 0}):
        if p.get("slug"):
            existing.add(p["slug"])
    return existing


def _resolve_image_url(slug: str) -> str:
    """Point at the committed per-slug PNG, falling back to a placeholder."""
    if (STATIC_DIR / f"{slug}.png").exists():
        return f"/api/static/products/{slug}.png"
    return "/api/static/products/_placeholder.png"


def _build_catalog_product(item: dict) -> dict:
    """Compose a catalog product document for insert."""
    slug = item["slug"]
    return {
        "id": gen_id(),
        "slug": slug,
        "name": item["name"],
        "description": item["description"],
        "price": float(item["price"]),
        "type": item.get("type_override") or "merch",
        "workshop_id": None,
        "image_url": _resolve_image_url(slug),
        "inventory": int(item.get("inventory", 75)),
        "category": item["category"],
        "created_at": now_iso(),
    }


async def ensure_catalog_seeded(db) -> dict:
    """Insert any items from catalog.json whose `slug` is missing in DB.

    Returns a small summary dict for logging. Never raises — log + skip on error.
    """
    items, error = _load_catalog_items()
    if error is not None:
        return error

    existing = await _existing_slugs(db)
    to_insert = [
        _build_catalog_product(item)
        for item in items
        if item.get("slug") and item["slug"] not in existing
    ]

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
