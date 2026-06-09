"""One-shot upgrade: bring the five Founder Collection patches in line with
the user's stated direction:

  - Price: $10 each (was a placeholder $38) — the price charged on 7C's
    Farmstead. Shipping handled by 7C's separately.
  - Description: full PatchesLanding narrative copy verbatim (long-form,
    not the punchline-only blurb).
  - Revenue framework: affiliate revenue share with 7C's Farmstead at 15%.
    The storefront no longer claims a 20% "Foundation patronage" — that
    framing was inaccurate for off-site fulfillment. Outbound clicks
    continue to be attributed via the existing /api/out/{slug} stamp.
  - Reorder: bump patches ahead of hats/journal in the Founder rail by
    rewriting `created_at` so they sort first.
  - Homepage feature: ONLY 'founder-of-love-story' carries the flag.
  - Also wipe regression-test pollution from db.research_artifacts.

Run: python -m scripts.upgrade_founder_patches
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

VENDOR_SLUG = "7cs-farmstead"
VENDOR_NAME = "7C's Farmstead"
CUSTOM_ORDER_URL = "https://7csfarmstead.com/pages/custom-order"

# Affiliate revenue share — kept here for reference and surfaced in admin
# UI labels. The actual reconciliation is off-platform (7C's remits quarterly).
AFFILIATE_PCT = 15.0


# Verbatim text from /shop/patches (PatchesLanding.jsx) — long-form
# descriptions, no second-guessing or shortening.
PATCHES = [
    {
        "idx": "01", "slug": "secure-connection",
        "name_phrase": "Secure connection is your birthright",
        "description": (
            "This isn’t aspirational. It’s the constitutional truth that "
            "every human being arrives wired for, and worthy of, a steady, "
            "responsive bond. We don’t earn secure attachment — we recognize "
            "it as the default we were built for.\n\n"
            "You were born holding the deed."
        ),
    },
    {
        "idx": "02", "slug": "founder-of-love-story",
        "name_phrase": "You are the founder of your own love story",
        "description": (
            "Most of us inherited a love story before we could write one. "
            "To be the founder is to take the pen back — to author the next "
            "chapter consciously: who you love, how you love, what counts "
            "as a happy ending.\n\n"
            "The pen has always been in your hand."
        ),
    },
    {
        "idx": "03", "slug": "created-for-connection",
        "name_phrase": "We are created for connection",
        "description": (
            "Whether you read “created” as a divine act or a developmental "
            "one, the message is identical: your nervous system was not "
            "designed to thrive alone. The hunger you feel for closeness "
            "is the original blueprint asserting itself.\n\n"
            "We are bonding creatures who occasionally find ourselves alone."
        ),
    },
    {
        "idx": "04", "slug": "bond-is-the-cure",
        "name_phrase": "The bond is the cure",
        "description": (
            "We chase cures in books, therapy, podcasts, prescriptions. "
            "But the deepest healing for relational wounds always comes "
            "through a different relationship — one that proves the old "
            "story wrong by living a steadier one in its place.\n\n"
            "Not a metaphor. Not a side effect. The cure."
        ),
    },
    {
        "idx": "05", "slug": "repair-is-older",
        "name_phrase": "Repair is older than rupture",
        "description": (
            "Mother-infant repair cycles begin in the first weeks of life "
            "— before any conscious wound is ever named. The dance of "
            "rupture-and-repair is the relationship; it’s been native to "
            "you since before you had language for either.\n\n"
            "You don’t have to learn repair from scratch. You have to "
            "remember it."
        ),
    },
]


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # ─── 1. Re-key the homepage feature flag ───────────────────────
    # Strip the flag from every founder_collection row first, then set
    # only on patch-02 (the artist's choice).
    r1 = await db.products.update_many(
        {"collection": "founder_collection"},
        {"$set": {"is_homepage_feature": False}},
    )
    r2 = await db.products.update_one(
        {"id": "founder-patch-02-founder-of-love-story"},
        {"$set": {"is_homepage_feature": True}},
    )
    print(f"homepage feature: cleared {r1.modified_count}, "
          f"promoted {r2.matched_count}")

    # ─── 2. Upgrade each patch row ────────────────────────────────
    # Backdate created_at so patches sort ahead of hats/journal in
    # /api/products feeds (descending). Use an offset so 02 comes first
    # (it's the homepage hero).
    base_iso = "2026-03-01T12:00:00+00:00"
    sort_order = ["02", "01", "03", "04", "05"]   # 02 first
    for rank, idx_key in enumerate(sort_order):
        # Newer = higher sort. rank=0 → newest.
        # Use millisecond offsets so they sort in our chosen order.
        ts = f"2026-03-01T12:00:{59 - rank:02d}+00:00"
        p = next((x for x in PATCHES if x["idx"] == idx_key))
        sku_id = f"founder-patch-{p['idx']}-{p['slug']}"
        r = await db.products.update_one(
            {"id": sku_id},
            {"$set": {
                "name": f"Leather-engraved patch · {p['name_phrase']}",
                "description": p["description"],
                "price": 10.00,
                "category": "patches",
                "collection": "founder_collection",
                "is_off_site": True,
                "external_url": CUSTOM_ORDER_URL,
                "vendor_slug": VENDOR_SLUG,
                "vendor_name": VENDOR_NAME,
                "is_vendor_product": True,
                # Affiliate share for admin reporting. The storefront UI
                # surfaces this on the product editor (not on the public
                # page) so operators can see the framework at a glance.
                "affiliate_revenue_share_pct": AFFILIATE_PCT,
                "affiliate_note": (
                    f"7C's Farmstead remits {AFFILIATE_PCT}% of every "
                    "Birthright-attributed sale on a quarterly basis. "
                    "Tracked off-platform via the ?via= stamp on outbound "
                    "clicks (see db.outbound_clicks)."
                ),
                "created_at": ts,
                "updated_at": now_iso(),
            }},
        )
        print(f"  patch {idx_key}: matched={r.matched_count} "
              f"modified={r.modified_count}")
    print(f"reordered with base_iso={base_iso}")

    # ─── 3. Clean research-artifact regression pollution ──────────
    r3 = await db.research_artifacts.delete_many({
        "$or": [
            {"title": {"$regex": "Admin-Approve-Me"}},
            {"abstract": {"$regex": "regression test", "$options": "i"}},
            {"author_name": {"$regex": "Pytest", "$options": "i"}},
        ]
    })
    print(f"research pollution removed: {r3.deleted_count}")

    # ─── 4. Sync the affiliate metadata onto the vendor profile ──
    r4 = await db.partner_profiles.update_one(
        {"slug": VENDOR_SLUG},
        {"$set": {
            "affiliate_revenue_share_pct": AFFILIATE_PCT,
            "affiliate_terms": (
                f"7C's Farmstead remits {AFFILIATE_PCT}% of each "
                "Birthright-referred sale to Birthright Foundation. "
                "Reconciled quarterly via the ?via=birthright_7cs-farmstead "
                "outbound stamp on tracked clicks."
            ),
            "updated_at": now_iso(),
        }},
    )
    print(f"vendor profile updated: matched={r4.matched_count}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
