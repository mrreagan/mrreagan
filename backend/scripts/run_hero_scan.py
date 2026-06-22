"""Offline hero-mismatch scan (avoids the proxy timeout)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402
from models import gen_id, now_iso  # noqa: E402
from routers.image_queue import _llm_propose_hero_replacement  # noqa: E402


async def main():
    cursor = db.products.find(
        {"is_off_site": {"$ne": True}},
        {"_id": 0, "id": 1, "name": 1, "description": 1, "image_caption": 1,
         "additional_images": 1},
    )
    products = await cursor.to_list(2000)
    print(f"Auditing {len(products)} products for hero mismatches...")

    queued = skipped = errors = 0
    for i, p in enumerate(products, 1):
        existing = await db.pending_additional_images.find_one(
            {"product_id": p["id"], "kind": "hero",
             "status": {"$in": ["queued", "generating", "ready"]}}
        )
        if existing:
            skipped += 1
            print(f"[{i:2d}/{len(products)}] SKIP (hero already queued) {p.get('name')}")
            continue

        # Collect hints from ready/published additional entries so the audit
        # considers them as part of the product's visual identity.
        hints: list[str] = []
        async for pe in db.pending_additional_images.find(
            {"product_id": p["id"], "kind": {"$in": ["additional", None]},
             "status": {"$in": ["ready", "published"]}},
            {"_id": 0, "prompt": 1},
        ):
            if pe.get("prompt"):
                hints.append(pe["prompt"][:400])

        try:
            prompt = await _llm_propose_hero_replacement(
                p.get("name", ""),
                p.get("description", ""),
                p.get("image_caption"),
                hints,
            )
        except Exception as exc:
            errors += 1
            print(f"[{i:2d}/{len(products)}] ERR  {p.get('name')}: {exc}")
            continue

        if not prompt:
            skipped += 1
            print(f"[{i:2d}/{len(products)}] OK   hero coherent: {p.get('name')}")
            continue
        await db.pending_additional_images.insert_one({
            "id": gen_id(),
            "product_id": p["id"],
            "product_name": p.get("name"),
            "kind": "hero",
            "prompt": prompt,
            "status": "queued",
            "image_url": None,
            "error": None,
            "created_at": now_iso(),
            "generated_at": None,
        })
        queued += 1
        print(f"[{i:2d}/{len(products)}] QUEUE hero replacement: {p.get('name')}")

    print(f"\nDone. queued={queued} skipped={skipped} errors={errors}")


if __name__ == "__main__":
    asyncio.run(main())
