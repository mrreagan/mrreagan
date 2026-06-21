"""One-shot (and idempotent) fulfillment router.

Walks every product that lacks an explicit fulfillment path and assigns
`fulfillable_via` based on a hand-tuned category + keyword map:

  apparel / cap / tote / hat / hoodie / crewneck / beanie / raglan / cardigan
  / pocket tee / bandana / socks / robe                       → printful
  bags (tote/crossbody/pouch/day pack)                        → printful
  prints / stickers / accessories (enamel pin)                → printful
  books / journals (paperback)                                → lulu
  home (candles/mugs/tea/blankets/incense)                    → sample
  decks (card sets)                                           → sample
  Brass items (keyring/lapel pin/bookmark/incense holder)     → sample

Skips anything already flagged. Re-runs are safe.

Run from /app/backend:
    python scripts/route_fulfillment.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402
from models import now_iso  # noqa: E402

# Keyword groups (case-insensitive substring match against product name)
SAMPLE_KEYWORDS = {
    "keyring", "lapel pin", "bookmark", "incense holder",
    "matchbox", "candle", "tea ", "loose leaf",
    "blanket", "eye pillow", "stone", "worry set",
    "coaster", "bottle", "mug", "stoneware",
}

LULU_KEYWORDS = {"journal", "notebook", "workbook", "booklet", "pocket guide"}


def decide_fulfillment(name: str, category: str) -> str:
    """Return 'printful' | 'lulu' | 'sample' (no path)."""
    n = (name or "").lower()
    c = (category or "").lower()

    # Manual override for sample-only artisanal items (candles, brass, mugs…)
    if any(k in n for k in SAMPLE_KEYWORDS):
        return "sample"

    # Card decks — neither POD partner handles these well
    if c == "decks":
        return "sample"

    # Books / journals → Lulu (paperback printing)
    if c in {"books", "journals", "journal"} or any(k in n for k in LULU_KEYWORDS):
        return "lulu"

    # Most apparel + paper goods → Printful
    if c in {
        "apparel", "bags", "prints", "stickers", "accessories", "cap", "tote",
    }:
        return "printful"

    # Anything else (home, general, digital, etc.) → sample
    return "sample"


async def main():
    cursor = db.products.find(
        {
            # Already-flagged products are left alone
            "fulfillable_via": {"$in": [None, ""]},
            "is_off_site": {"$ne": True},
            "is_gallery_artwork": {"$ne": True},
        },
        {"_id": 0, "id": 1, "name": 1, "category": 1, "fulfillable_via": 1},
    )
    products = await cursor.to_list(2000)

    counts = {"printful": 0, "lulu": 0, "sample": 0, "unchanged": 0}
    for p in products:
        verdict = decide_fulfillment(p.get("name", ""), p.get("category", ""))
        update = {"fulfillable_via": verdict, "fulfillable_at": now_iso()}
        await db.products.update_one({"id": p["id"]}, {"$set": update})
        counts[verdict] += 1
        print(f"  [{verdict:8s}] {p['name']}")

    print("\nSummary:", counts)


if __name__ == "__main__":
    asyncio.run(main())
