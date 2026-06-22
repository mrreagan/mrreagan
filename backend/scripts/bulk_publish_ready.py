"""Bulk-publish every queue entry currently in 'ready' status.

Heroes replace `image_url` (old hero is demoted to `additional_images`).
Additional shots are appended to `additional_images`.

The publish endpoint in `routers/image_queue.py` already does the right
thing per kind — we just iterate.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402


async def publish_one(entry: dict) -> tuple[bool, str]:
    image_url = entry["image_url"]
    pid = entry["product_id"]
    kind = entry.get("kind", "additional")
    product = await db.products.find_one(
        {"id": pid}, {"_id": 0, "additional_images": 1, "image_url": 1}
    )
    if not product:
        return False, "product missing"

    if kind == "hero":
        existing = product.get("additional_images") or []
        old_hero = product.get("image_url")
        if old_hero and old_hero not in existing and old_hero != image_url:
            existing.append(old_hero)
        await db.products.update_one(
            {"id": pid},
            {"$set": {
                "image_url": image_url,
                "additional_images": existing,
                "image_caption": None,
                "image_caption_source_url": None,
            }},
        )
    else:
        existing = product.get("additional_images") or []
        if image_url not in existing:
            existing.append(image_url)
            await db.products.update_one(
                {"id": pid}, {"$set": {"additional_images": existing}}
            )

    await db.pending_additional_images.update_one(
        {"id": entry["id"]}, {"$set": {"status": "published"}}
    )
    return True, kind


async def main():
    ready = await db.pending_additional_images.find(
        {"status": "ready"}, {"_id": 0}
    ).to_list(2000)
    print(f"Publishing {len(ready)} ready entries...")
    counts = {"hero": 0, "additional": 0, "skip": 0}
    for e in ready:
        ok, info = await publish_one(e)
        if not ok:
            counts["skip"] += 1
            print(f"  SKIP {e['product_name']}: {info}")
        else:
            counts[info] += 1
            print(f"  OK   [{info}] {e['product_name']}")
    print(f"\nDone. {counts}")


if __name__ == "__main__":
    asyncio.run(main())
