"""Founder Collection — bundle SKU: all five engraved patches for $40
(vs $50 if purchased individually). Off-site fulfilment routes through
the same 7C's Farmstead custom-order page; the buyer specifies "Birthright
five-patch set" in the order notes.

Run: python -m scripts.seed_patch_bundle
"""
from __future__ import annotations

import asyncio
import os
import pathlib
import sys

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from models import now_iso  # noqa: E402

BUNDLE_ID = "founder-patch-bundle-all-five"
CUSTOM_ORDER_URL = "https://7csfarmstead.com/pages/custom-order?bundle=birthright-five"


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    existing = await db.products.find_one({"id": BUNDLE_ID}, {"_id": 0, "id": 1})
    doc = {
        "id": BUNDLE_ID,
        "slug": "patch-bundle-all-five",
        "name": "The Full Set — Five engraved patches",
        # Intentionally minimal copy. The individual patch detail pages
        # carry the long-form narrative.
        "description": (
            "All five Birthright phrases, hand-engraved by 7C's Farmstead, "
            "delivered as one set. Save $10 versus buying each patch "
            "individually. Each patch's full story lives on its own product "
            "page — open any of the five in this collection to read it."
        ),
        "price": 40.00,
        "type": "merch",
        "category": "patches",
        "collection": "founder_collection",
        "image_url": "/fb-assets/v4/hero-02-founder-of-love-story.png",
        "inventory": 999,
        "is_homepage_feature": False,
        "moderation_status": "active",
        "is_off_site": True,
        "external_url": CUSTOM_ORDER_URL,
        "vendor_slug": "7cs-farmstead",
        "vendor_name": "7C's Farmstead",
        "is_vendor_product": True,
        "is_bundle": True,
        "bundle_skus": [
            "founder-patch-01-secure-connection",
            "founder-patch-02-founder-of-love-story",
            "founder-patch-03-created-for-connection",
            "founder-patch-04-bond-is-the-cure",
            "founder-patch-05-repair-is-older",
        ],
        "affiliate_revenue_share_pct": 15.0,
        # Sorts AFTER patch-02 (the homepage hero) but ahead of patches 01,
        # 03, 04, 05 — i.e. second card in the rail.
        "created_at": "2026-03-01T12:00:58.5+00:00",
        "updated_at": now_iso(),
    }
    if existing:
        r = await db.products.update_one({"id": BUNDLE_ID}, {"$set": doc})
        print(f"bundle updated: matched={r.matched_count} modified={r.modified_count}")
    else:
        await db.products.insert_one(doc)
        print(f"bundle inserted: {BUNDLE_ID}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
