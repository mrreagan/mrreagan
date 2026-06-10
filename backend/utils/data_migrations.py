"""Forward-only, idempotent data migrations.

Why this exists:
  Code deploys ship the Python/JS; they do NOT mutate MongoDB documents.
  Several recent features (Founder Collection patches, $10 pricing, the
  5-patch bundle SKU, carousel_rank, the 7C's Farmstead vendor profile)
  required one-time data writes. Those writes happen on each developer's
  machine but never reach production unless something runs them there.

This module fixes that. Each migration:
  - Has a stable string ID (never reused, never renumbered).
  - Is idempotent — running it twice is a no-op.
  - Records its application in db.system_migrations on success.
  - Auto-runs once on backend startup (via apply_pending()).
  - Can be re-triggered manually by an admin via the API endpoint.

To add a new migration: append a (migration_id, async_fn) pair to
MIGRATIONS at the bottom. Never edit an applied migration in place —
add a new one instead. That keeps prod and preview in lockstep.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, List, Tuple

logger = logging.getLogger("birthright.migrations")

MigrationFn = Callable[[object], Awaitable[dict]]


# ─── Migration implementations ────────────────────────────────────────


async def _2026_02_seed_founder_patches(db) -> dict:
    """Seed 7C's Farmstead vendor profile + 5 founder-collection patch
    products. Idempotent: skips already-created rows."""
    from models import gen_id, now_iso

    VENDOR_SLUG = "7cs-farmstead"
    VENDOR_NAME = "7C's Farmstead"
    CUSTOM_ORDER_URL = "https://7csfarmstead.com/pages/custom-order"

    patches = [
        ("01", "secure-connection", "Secure connection is your birthright",
         "This isn’t aspirational. It’s the constitutional truth that "
         "every human being arrives wired for, and worthy of, a steady, "
         "responsive bond. We don’t earn secure attachment — we recognize "
         "it as the default we were built for.\n\n"
         "You were born holding the deed."),
        ("02", "founder-of-love-story", "You are the founder of your own love story",
         "Most of us inherited a love story before we could write one. "
         "To be the founder is to take the pen back — to author the next "
         "chapter consciously: who you love, how you love, what counts "
         "as a happy ending.\n\n"
         "The pen has always been in your hand."),
        ("03", "created-for-connection", "We are created for connection",
         "Whether you read “created” as a divine act or a developmental "
         "one, the message is identical: your nervous system was not "
         "designed to thrive alone. The hunger you feel for closeness "
         "is the original blueprint asserting itself.\n\n"
         "We are bonding creatures who occasionally find ourselves alone."),
        ("04", "bond-is-the-cure", "The bond is the cure",
         "We chase cures in books, therapy, podcasts, prescriptions. "
         "But the deepest healing for relational wounds always comes "
         "through a different relationship — one that proves the old "
         "story wrong by living a steadier one in its place.\n\n"
         "Not a metaphor. Not a side effect. The cure."),
        ("05", "repair-is-older", "Repair is older than rupture",
         "Mother-infant repair cycles begin in the first weeks of life "
         "— before any conscious wound is ever named. The dance of "
         "rupture-and-repair is the relationship; it’s been native to "
         "you since before you had language for either.\n\n"
         "You don’t have to learn repair from scratch. You have to "
         "remember it."),
    ]

    # Vendor profile.
    existing = await db.partner_profiles.find_one({"slug": VENDOR_SLUG},
                                                    {"_id": 0, "id": 1})
    if existing:
        vendor_id = existing["id"]
    else:
        vendor_id = gen_id()
        await db.partner_profiles.insert_one({
            "id": vendor_id, "slug": VENDOR_SLUG, "user_id": None,
            "partner_type": "vendor", "status": "active", "public": True,
            "display_name": VENDOR_NAME,
            "headline": "Hand-engraved leather, made to order",
            "bio": ("Small-batch leather goods crafted by hand. 7C's Farmstead "
                    "fulfills birthright Foundation's leather-engraved patch "
                    "series under a custom-order arrangement; every piece is "
                    "made to order. Lead time is typically 2–4 weeks."),
            "location": "United States",
            "external_site_url": "https://7csfarmstead.com",
            "website_url": "https://7csfarmstead.com",
            "referral_code": "SEVENCSFARM",
            "is_founding_partner": False, "is_sample": False,
            "approved_at": now_iso(), "approved_by": "migration",
            "affiliate_revenue_share_pct": 15.0,
            "affiliate_terms": (
                "7C's Farmstead remits 15% of each birthright-referred "
                "sale to birthright Foundation. Reconciled quarterly via "
                "the ?via=birthright_7cs-farmstead outbound stamp."),
            "created_at": now_iso(), "updated_at": now_iso(),
        })

    # Patch products.
    created = 0
    for idx, slug, phrase, desc in patches:
        sku_id = f"founder-patch-{idx}-{slug}"
        if await db.products.find_one({"id": sku_id}, {"_id": 0, "id": 1}):
            continue
        await db.products.insert_one({
            "id": sku_id, "slug": f"patch-{slug}",
            "name": f"Leather-engraved patch · {phrase}",
            "description": desc,
            "price": 10.00,
            "type": "merch", "category": "patches",
            "collection": "founder_collection",
            "image_url": f"/fb-assets/v4/hero-{idx}-{slug}.png",
            "inventory": 999, "is_homepage_feature": False,
            "moderation_status": "active",
            "is_off_site": True, "external_url": CUSTOM_ORDER_URL,
            "vendor_partner_id": vendor_id,
            "vendor_name": VENDOR_NAME, "vendor_slug": VENDOR_SLUG,
            "is_vendor_product": True,
            "affiliate_revenue_share_pct": 15.0,
            "affiliate_note": (
                "7C's Farmstead remits 15% of every birthright-attributed "
                "sale on a quarterly basis."),
            # Future-dated created_at so patches sort ahead of older items.
            "created_at": f"2026-12-31T23:59:{60 - int(idx):02d}+00:00",
            "updated_at": now_iso(),
        })
        created += 1
    return {"vendor_id": vendor_id, "patches_created": created}


async def _2026_02_seed_patch_bundle(db) -> dict:
    """Seed the 5-patch bundle SKU at $40."""
    from models import now_iso
    BUNDLE_ID = "founder-patch-bundle-all-five"
    doc = {
        "id": BUNDLE_ID, "slug": "patch-bundle-all-five",
        "name": "The Full Set — Five engraved patches",
        "description": (
            "All five birthright phrases, hand-engraved by 7C's Farmstead, "
            "delivered as one set. Save $10 versus buying each patch "
            "individually. Each patch's full story lives on its own product "
            "page — open any of the five in this collection to read it."),
        "price": 40.00, "type": "merch", "category": "patches",
        "collection": "founder_collection",
        "image_url": "/fb-assets/v4/hero-02-founder-of-love-story.png",
        "inventory": 999, "is_homepage_feature": False,
        "moderation_status": "active", "is_off_site": True,
        "external_url": "https://7csfarmstead.com/pages/custom-order?bundle=birthright-five",
        "vendor_slug": "7cs-farmstead", "vendor_name": "7C's Farmstead",
        "is_vendor_product": True, "is_bundle": True,
        "bundle_skus": [
            "founder-patch-01-secure-connection",
            "founder-patch-02-founder-of-love-story",
            "founder-patch-03-created-for-connection",
            "founder-patch-04-bond-is-the-cure",
            "founder-patch-05-repair-is-older",
        ],
        "affiliate_revenue_share_pct": 15.0,
        "created_at": "2026-12-31T23:59:58+00:00",
        "updated_at": now_iso(),
    }
    existing = await db.products.find_one({"id": BUNDLE_ID}, {"_id": 0, "id": 1})
    if existing:
        return {"already_present": True}
    await db.products.insert_one(doc)
    return {"created": BUNDLE_ID}


async def _2026_02_carousel_default_ranks(db) -> dict:
    """Assign the default 3-slot carousel: patch-02 → 1, bundle → 2, patch-01 → 3.
    Only sets ranks where currently null, so it won't override an admin's
    later manual reshuffle."""
    slots = [
        (1, "founder-patch-02-founder-of-love-story"),
        (2, "founder-patch-bundle-all-five"),
        (3, "founder-patch-01-secure-connection"),
    ]
    set_count = 0
    for rank, pid in slots:
        # Only set if no product currently holds this rank AND this product
        # doesn't already have a rank — so we never stomp on admin choices.
        slot_taken = await db.products.find_one(
            {"carousel_rank": rank}, {"_id": 0, "id": 1})
        my_rank = await db.products.find_one(
            {"id": pid}, {"_id": 0, "carousel_rank": 1})
        if slot_taken is None and my_rank and my_rank.get("carousel_rank") is None:
            await db.products.update_one(
                {"id": pid}, {"$set": {"carousel_rank": rank}})
            set_count += 1
    # Make sure Hat Pair is not stuck holding the homepage feature flag.
    await db.products.update_one(
        {"id": "843532f6-1a64-46b9-94bc-c4c7f94fa07f"},
        {"$set": {"is_homepage_feature": False}},
    )
    return {"slots_set": set_count}


async def _2026_02_research_pollution_cleanup(db) -> dict:
    """Wipe regression-test pollution from db.research_artifacts."""
    r = await db.research_artifacts.delete_many({
        "$or": [
            {"title": {"$regex": "Admin-Approve-Me"}},
            {"abstract": {"$regex": "regression test", "$options": "i"}},
            {"author_name": {"$regex": "Pytest", "$options": "i"}},
        ]
    })
    return {"deleted": r.deleted_count}


async def _2026_02_system_settings_defaults(db) -> dict:
    """Seed the singleton system_settings document with admin-editable
    site-wide values (currently: support_email, hello_email)."""
    from models import now_iso
    doc = await db.system_settings.find_one({"id": "global"}, {"_id": 0})
    if doc:
        return {"already_present": True}
    await db.system_settings.insert_one({
        "id": "global",
        "support_email": "support@birthright.live",
        "hello_email": "hello@birthright.live",
        "updated_at": now_iso(),
        "updated_by": "migration",
    })
    return {"created": True}


# ─── Registry — append-only ─────────────────────────────────────────
MIGRATIONS: List[Tuple[str, MigrationFn]] = [
    ("2026_02_seed_founder_patches",       _2026_02_seed_founder_patches),
    ("2026_02_seed_patch_bundle",          _2026_02_seed_patch_bundle),
    ("2026_02_carousel_default_ranks",     _2026_02_carousel_default_ranks),
    ("2026_02_research_pollution_cleanup", _2026_02_research_pollution_cleanup),
    ("2026_02_system_settings_defaults",   _2026_02_system_settings_defaults),
]


# ─── Runner ─────────────────────────────────────────────────────────
async def applied_ids(db) -> set:
    rows = await db.system_migrations.find({}, {"_id": 0, "id": 1}).to_list(500)
    return {r["id"] for r in rows}


async def apply_pending(db, *, force: bool = False) -> list[dict]:
    """Run every migration not yet applied. Returns a per-migration log.

    Set force=True to re-run every migration (idempotently). Useful from the
    admin endpoint when an operator wants to be extra sure.
    """
    log: list[dict] = []
    seen = set() if force else await applied_ids(db)
    for mid, fn in MIGRATIONS:
        if mid in seen:
            log.append({"id": mid, "status": "skipped"})
            continue
        try:
            result = await fn(db)
            await db.system_migrations.update_one(
                {"id": mid},
                {"$set": {
                    "id": mid,
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                    "result": result,
                }},
                upsert=True,
            )
            log.append({"id": mid, "status": "applied", "result": result})
            logger.info("migration applied: %s -> %s", mid, result)
        except Exception as exc:
            logger.exception("migration failed: %s", mid)
            log.append({"id": mid, "status": "error", "error": str(exc)})
            # Stop on first error — operator must intervene.
            break
    return log
