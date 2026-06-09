"""One-shot seed: Founder Collection — 5 leather-engraved patches via 7C's
Farmstead (custom-order fulfillment partner). Idempotent.

7C's Farmstead is a custom-order artisan, not a programmatic vendor. We
re-use the existing `is_off_site=True` + outbound-click attribution
mechanism so each storefront card on /equip carries a "Buy on 7C's
Farmstead →" CTA that 302s through /api/out/7cs-farmstead with proper
?via=birthright stamping.

Also fixes the broken sample research artifact image (the Unsplash URL
in the seed has rotted; replace with a stable, brand-aligned image).

Run: python -m scripts.seed_founder_patches
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

from models import gen_id, now_iso  # noqa: E402


VENDOR_SLUG = "7cs-farmstead"
VENDOR_NAME = "7C's Farmstead"
VENDOR_URL_BASE = "https://7csfarmstead.com"
CUSTOM_ORDER_URL = "https://7csfarmstead.com/pages/custom-order"

PATCHES = [
    {
        "idx": "01",
        "slug": "secure-connection",
        "phrase": "Secure connection is your birthright",
        "blurb": (
            "Hand-engraved leather patch. The constitutional truth at "
            "the heart of Birthright's work — that every human being "
            "arrives wired for, and worthy of, a steady responsive "
            "bond. You were born holding the deed."
        ),
    },
    {
        "idx": "02",
        "slug": "founder-of-love-story",
        "phrase": "You are the founder of your own love story",
        "blurb": (
            "Hand-engraved leather patch. To be the founder is to take "
            "the pen back from inherited scripts and author the next "
            "chapter consciously. The pen has always been in your hand."
        ),
    },
    {
        "idx": "03",
        "slug": "created-for-connection",
        "phrase": "We are created for connection",
        "blurb": (
            "Hand-engraved leather patch. The hunger you feel for "
            "closeness isn't a flaw — it's the original blueprint "
            "asserting itself. We are bonding creatures who occasionally "
            "find ourselves alone."
        ),
    },
    {
        "idx": "04",
        "slug": "bond-is-the-cure",
        "phrase": "The bond is the cure",
        "blurb": (
            "Hand-engraved leather patch. The deepest healing for "
            "relational wounds always comes through a different "
            "relationship — one that proves the old story wrong by "
            "living a steadier one in its place. Not a metaphor. The cure."
        ),
    },
    {
        "idx": "05",
        "slug": "repair-is-older",
        "phrase": "Repair is older than rupture",
        "blurb": (
            "Hand-engraved leather patch. Mother-infant repair cycles "
            "begin in the first weeks of life — before any conscious "
            "wound is named. You don't have to learn repair from "
            "scratch. You have to remember it."
        ),
    },
]


# Stable, brand-aligned cover image for the sample research brief on
# co-regulation (Unsplash photo that has not been retired).
RESEARCH_FIX = {
    "id": "sample-co-regulation-brief-2025",
    "cover_image_url": (
        "https://images.unsplash.com/photo-1499377193864-82682aefed04"
        "?w=1200&q=80&auto=format&fit=crop"
    ),
}


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # ─── 1. Vendor profile for 7C's Farmstead ───────────────────────
    existing_v = await db.partner_profiles.find_one(
        {"slug": VENDOR_SLUG}, {"_id": 0, "id": 1, "referral_code": 1},
    )
    if existing_v:
        vendor_id = existing_v["id"]
        ref_code = existing_v.get("referral_code") or "SEVENCSFARM"
        print(f"vendor exists: id={vendor_id}, referral_code={ref_code}")
    else:
        vendor_id = gen_id()
        ref_code = "SEVENCSFARM"
        await db.partner_profiles.insert_one({
            "id": vendor_id,
            "slug": VENDOR_SLUG,
            "user_id": None,  # No platform login — external fulfillment partner.
            "partner_type": "vendor",
            "status": "active",
            "public": True,
            "display_name": VENDOR_NAME,
            "headline": "Hand-engraved leather, made to order",
            "bio": (
                "Small-batch leather goods crafted by hand. 7C's Farmstead "
                "fulfills Birthright Foundation's leather-engraved patch "
                "series under a custom-order arrangement; every piece is "
                "made to order. Lead time is typically 2–4 weeks."
            ),
            "location": "United States",
            "external_site_url": VENDOR_URL_BASE,
            "website_url": VENDOR_URL_BASE,
            "referral_code": ref_code,
            "is_founding_partner": False,
            "is_sample": False,
            "approved_at": now_iso(),
            "approved_by": "seed",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
        print(f"vendor created: id={vendor_id}")

    # ─── 2. The 5 patch products ────────────────────────────────────
    created, skipped = 0, 0
    for p in PATCHES:
        sku_id = f"founder-patch-{p['idx']}-{p['slug']}"
        exists = await db.products.find_one(
            {"id": sku_id}, {"_id": 0, "id": 1},
        )
        if exists:
            skipped += 1
            continue
        await db.products.insert_one({
            "id": sku_id,
            "slug": f"patch-{p['slug']}",
            "name": f"Leather-engraved patch · {p['phrase']}",
            "description": p["blurb"],
            "price": 38.00,
            "type": "merch",
            "category": "patches",
            "collection": "founder_collection",
            "image_url": f"/fb-assets/v4/hero-{p['idx']}-{p['slug']}.png",
            "inventory": 999,         # Made-to-order; effectively unlimited.
            "is_homepage_feature": False,
            "moderation_status": "active",
            # — Off-site / external fulfillment plumbing —
            "is_off_site": True,
            "external_url": CUSTOM_ORDER_URL,
            "vendor_partner_id": vendor_id,
            "vendor_user_id": None,
            "vendor_name": VENDOR_NAME,
            "vendor_slug": VENDOR_SLUG,
            "is_vendor_product": True,
            "created_at": now_iso(),
        })
        created += 1
        print(f"  + {sku_id}")
    print(f"patches: created={created}, skipped={skipped}")

    # ─── 3. Fix the broken research artifact cover image ────────────
    r = await db.research_artifacts.update_one(
        {"id": RESEARCH_FIX["id"]},
        {"$set": {"cover_image_url": RESEARCH_FIX["cover_image_url"]}},
    )
    print(f"research artifact updated: matched={r.matched_count} "
          f"modified={r.modified_count}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
