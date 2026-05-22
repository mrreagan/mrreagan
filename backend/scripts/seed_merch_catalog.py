"""One-time migration: seed 50 Birthright-themed merch items with AI-generated mockup images.

Usage:
    cd /app/backend && python -m scripts.seed_merch_catalog
    # or: python scripts/seed_merch_catalog.py

Behavior:
- Loads `/app/backend/data/catalog.json`
- Skips any product whose `slug` already exists in `products.category_slug`
  (idempotent — safe to re-run; will only fill missing items)
- For each new item, generates a single mockup image via Gemini Nano Banana
  using the EMERGENT_LLM_KEY, saves PNG to `/app/backend/static/products/<slug>.png`
- Inserts the product into MongoDB with image_url=`/api/static/products/<slug>.png`
- If image generation fails (rate-limit, transient), inserts product with a
  cream placeholder image_url so the catalog still seeds.

This script is intentionally separate from `seed_data.py` (which is idempotent
on empty DB only). It can be run repeatedly without duplicating data.
"""
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from database import db  # noqa: E402
from models import gen_id, now_iso  # noqa: E402

CATALOG_PATH = BACKEND_DIR / "data" / "catalog.json"
STATIC_DIR = BACKEND_DIR / "static" / "products"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Placeholder used if image generation fails — a neutral cream block from Unsplash
FALLBACK_IMAGE = "https://images.unsplash.com/photo-1452860606245-08befc0ff44b?w=800"

GEMINI_MODEL = "gemini-3.1-flash-image-preview"


def _build_prompt(item: dict, style: str) -> str:
    """Compose a single product-photography prompt."""
    return (
        f"{item['image_prompt']}. "
        f"Brand palette: muted teal #476B6B, gold #C9A961, cream #FAF8F5, deep ink. "
        f"{style} "
        "Do NOT include any printed brand name, logo text, watermark, or human faces."
    )


async def _generate_image(slug: str, prompt: str) -> str | None:
    """Generate one image. Returns saved file path or None on failure.

    Imports emergentintegrations lazily so the migration script still runs
    (in placeholder mode) if the lib is unavailable.
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        print(f"  [warn] emergentintegrations import failed: {e}")
        return None

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        print("  [warn] EMERGENT_LLM_KEY not set; using fallback images")
        return None

    try:
        chat = (
            LlmChat(
                api_key=api_key,
                session_id=f"birthright-merch-{slug}",
                system_message="You generate clean editorial e-commerce product mockup photography.",
            )
            .with_model("gemini", GEMINI_MODEL)
            .with_params(modalities=["image", "text"])
        )
        msg = UserMessage(text=prompt)
        _, images = await chat.send_message_multimodal_response(msg)
        if not images:
            print(f"  [warn] no image returned for {slug}")
            return None
        img_bytes = base64.b64decode(images[0]["data"])
        out = STATIC_DIR / f"{slug}.png"
        out.write_bytes(img_bytes)
        return str(out)
    except Exception as e:
        print(f"  [warn] generation failed for {slug}: {type(e).__name__}: {e}")
        return None


async def main():
    if not CATALOG_PATH.exists():
        print(f"FATAL: catalog not found at {CATALOG_PATH}")
        sys.exit(1)
    catalog = json.loads(CATALOG_PATH.read_text())
    style = catalog["_meta"]["image_style"]
    items = catalog["items"]
    print(f"Loaded {len(items)} catalog items.")

    # Build set of existing slugs (we'll record slug per product for idempotency)
    existing = set()
    async for p in db.products.find({"slug": {"$exists": True}}, {"slug": 1, "_id": 0}):
        if p.get("slug"):
            existing.add(p["slug"])
    print(f"Found {len(existing)} existing slug-tagged products in DB.")

    new_products = []
    generated = 0
    fallback = 0
    skipped = 0

    for idx, item in enumerate(items, start=1):
        slug = item["slug"]
        if slug in existing:
            skipped += 1
            continue

        print(f"[{idx:02d}/{len(items)}] {slug} -- generating image...")
        prompt = _build_prompt(item, style)
        local_path = await _generate_image(slug, prompt)

        if local_path:
            image_url = f"/api/static/products/{slug}.png"
            generated += 1
        else:
            image_url = FALLBACK_IMAGE
            fallback += 1

        product = {
            "id": gen_id(),
            "slug": slug,
            "name": item["name"],
            "description": item["description"],
            "price": float(item["price"]),
            "type": item.get("type_override") or "merch",
            "workshop_id": None,
            "image_url": image_url,
            "inventory": item.get("inventory", 75),
            "category": item["category"],
            "created_at": now_iso(),
        }
        new_products.append(product)

    if new_products:
        await db.products.insert_many(new_products)
        print(
            f"\nInserted {len(new_products)} new products. "
            f"(images generated: {generated}, fallback used: {fallback}, "
            f"already-present skipped: {skipped})"
        )
    else:
        print(f"\nNothing to insert (skipped: {skipped}).")


if __name__ == "__main__":
    asyncio.run(main())
