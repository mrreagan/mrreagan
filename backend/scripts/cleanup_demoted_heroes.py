"""Strip demoted-hero clutter from products' additional_images.

When the publish flow used to demote the old hero into `additional_images`,
buyers ended up with the OLD product photo in their gallery (e.g., a white
convex mug appearing as a thumbnail next to the new teal mug).

This script keeps in `additional_images` only the URLs that were published
through the queue with kind="additional". Everything else (legacy seed
artwork, demoted heroes, leftover Unsplash test URLs) is removed.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402


async def main():
    cleaned = 0
    products = await db.products.find({}, {"_id": 0, "id": 1, "name": 1, "additional_images": 1}).to_list(2000)
    for p in products:
        original = p.get("additional_images") or []
        if not original:
            continue

        # Collect every URL that was *legitimately* published as an additional
        # shot for this product through the queue.
        approved = set()
        async for entry in db.pending_additional_images.find(
            {"product_id": p["id"], "kind": {"$in": ["additional", None]}, "status": "published"},
            {"_id": 0, "image_url": 1},
        ):
            url = entry.get("image_url")
            if url:
                approved.add(url)

        filtered = [u for u in original if u in approved]
        if filtered != original:
            dropped = [u for u in original if u not in approved]
            await db.products.update_one(
                {"id": p["id"]}, {"$set": {"additional_images": filtered}}
            )
            cleaned += 1
            print(f"  {p['name']}")
            for d in dropped:
                print(f"      - removed {d}")

    print(f"\nCleaned {cleaned} products.")


if __name__ == "__main__":
    asyncio.run(main())
