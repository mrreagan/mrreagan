"""Run the image-queue scan offline (avoids the ~100s proxy timeout).

Calls the same _llm_detect_missing_detail helper used by the API endpoint
but iterates products directly so we can see progress.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402
from models import gen_id, now_iso  # noqa: E402
from routers.image_queue import _llm_detect_missing_detail  # noqa: E402


async def main():
    cursor = db.products.find(
        {"is_off_site": {"$ne": True}},
        {"_id": 0, "id": 1, "name": 1, "description": 1, "image_caption": 1},
    )
    products = await cursor.to_list(2000)
    print(f"Auditing {len(products)} products...")

    queued = skipped = errors = 0
    for i, p in enumerate(products, 1):
        existing = await db.pending_additional_images.find_one(
            {"product_id": p["id"], "status": {"$in": ["queued", "generating", "ready"]}}
        )
        if existing:
            skipped += 1
            print(f"[{i:2d}/{len(products)}] SKIP (already queued) {p.get('name')}")
            continue
        try:
            prompt = await _llm_detect_missing_detail(
                p.get("name", ""),
                p.get("description", ""),
                p.get("image_caption"),
            )
        except Exception as exc:
            errors += 1
            print(f"[{i:2d}/{len(products)}] ERR  {p.get('name')}: {exc}")
            continue
        if not prompt:
            skipped += 1
            print(f"[{i:2d}/{len(products)}] OK   no missing detail: {p.get('name')}")
            continue
        await db.pending_additional_images.insert_one({
            "id": gen_id(),
            "product_id": p["id"],
            "product_name": p.get("name"),
            "prompt": prompt,
            "status": "queued",
            "image_url": None,
            "error": None,
            "created_at": now_iso(),
            "generated_at": None,
        })
        queued += 1
        print(f"[{i:2d}/{len(products)}] QUEUE {p.get('name')}")

    print(f"\nDone. queued={queued} skipped={skipped} errors={errors}")


if __name__ == "__main__":
    asyncio.run(main())
