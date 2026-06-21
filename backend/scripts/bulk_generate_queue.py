"""Bulk-generate every 'queued' image in the additional-images queue.

Runs sequentially (Nano Banana ≈ 15-25s each) so we don't trip rate limits.
On failure, marks the entry 'failed' with the error string so the admin can
retry from the UI.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402
from models import now_iso  # noqa: E402
from utils.image_generator import generate_product_image  # noqa: E402
from routers.image_queue import _slugify  # noqa: E402


async def main():
    # First: discard duplicates — keep only the oldest queued entry per product
    pipeline = [
        {"$match": {"status": "queued"}},
        {"$sort": {"created_at": 1}},
        {"$group": {"_id": "$product_id", "keep": {"$first": "$id"}, "dups": {"$push": "$id"}}},
    ]
    async for row in db.pending_additional_images.aggregate(pipeline):
        dups = [d for d in row["dups"] if d != row["keep"]]
        if dups:
            await db.pending_additional_images.delete_many({"id": {"$in": dups}})
            print(f"  cleaned {len(dups)} duplicate(s) for product {row['_id']}")

    queued = await db.pending_additional_images.find(
        {"status": "queued"}, {"_id": 0}
    ).to_list(500)
    print(f"Generating {len(queued)} images...")

    ok = fail = 0
    for i, entry in enumerate(queued, 1):
        pid = entry["product_id"]
        eid = entry["id"]
        prod = await db.products.find_one({"id": pid}, {"_id": 0, "slug": 1, "name": 1})
        slug = (prod or {}).get("slug") or _slugify((prod or {}).get("name") or "extra")
        file_stem = f"{slug}-extra-{eid[:8]}"
        try:
            await db.pending_additional_images.update_one(
                {"id": eid}, {"$set": {"status": "generating", "error": None}}
            )
            url = await generate_product_image(
                prompt=entry["prompt"],
                file_stem=file_stem,
                session_id=f"bulk-{eid}",
            )
            await db.pending_additional_images.update_one(
                {"id": eid},
                {"$set": {"status": "ready", "image_url": url, "generated_at": now_iso(), "error": None}},
            )
            ok += 1
            print(f"[{i:2d}/{len(queued)}] OK   {entry['product_name']}  →  {url}")
        except Exception as exc:
            fail += 1
            await db.pending_additional_images.update_one(
                {"id": eid},
                {"$set": {"status": "failed", "error": str(exc)}},
            )
            print(f"[{i:2d}/{len(queued)}] FAIL {entry['product_name']}: {exc}")

    print(f"\nDone. ok={ok} fail={fail}")


if __name__ == "__main__":
    asyncio.run(main())
