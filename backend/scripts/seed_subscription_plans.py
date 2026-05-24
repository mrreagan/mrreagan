"""Seed subscription plans — v1.11.0 LOCKED MODEL.

Idempotent. Run via `python -m scripts.seed_subscription_plans`.

LOCKED PRICING PRINCIPLES (per pricing proposal v2):
  1. Longer commitment is ALWAYS rewarded — effective $/mo decreases,
     AND foundation share decreases. Partner keep increases with commitment.
  2. Foundation IP rev-share: foundation share 50% → 42% → 35% (floor).
     Floor of 35% cannot drop further except via admin override + governance log.
  3. Non-IP rev-share: foundation share 20% → 15% → 10%.
  4. Off-site rev-share: foundation share 7% → 5% → 3%.
  5. Community + Research have a FREE Starter tier. Paid tiers add benefits.
  6. Pre-traction multiplier × 0.5 is applied to subscription FEES only
     (rev-share % is plan-level and BTI-stable; predictable income for partners).

NOTE: rev-share percentages stored here are FOUNDATION'S share (what the foundation
keeps). Partner's keep = 100 - foundation_share.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
from models import gen_id, now_iso

# Pre-traction multiplier applied to subscription fees at seed time.
# Rev-share % is NOT multiplied — it stays at standard rates.
PRE_TRACTION_FEE_MULTIPLIER = 0.5


def fee(standard_usd: float) -> float:
    """Apply pre-traction multiplier to a standard-rate fee."""
    return round(standard_usd * PRE_TRACTION_FEE_MULTIPLIER, 2)


PLANS = [
    # ============ FACILITATOR ============
    {
        "partner_type": "facilitator", "duration_months": 1,
        "name": "Facilitator — Monthly",
        "tagline": "Try Birthright facilitation month-to-month.",
        "price_usd": fee(99.0),  # → $49.50
        # Foundation share (the foundation keeps these %):
        "foundation_ip_pct": 50.0,
        "non_ip_pct": 20.0,
        "off_site_pct": 7.0,
        # Legacy field names retained for backward compat with v1.8 code:
        "birthright_ip_pct": 50.0,
        "other_content_pct": 20.0,
    },
    {
        "partner_type": "facilitator", "duration_months": 12,
        "name": "Facilitator — Annual",
        "tagline": "24% effective discount vs monthly. Lower rev-share too.",
        "price_usd": fee(899.0),  # → $449.50
        "foundation_ip_pct": 42.0,
        "non_ip_pct": 15.0,
        "off_site_pct": 5.0,
        "birthright_ip_pct": 42.0,
        "other_content_pct": 15.0,
    },
    {
        "partner_type": "facilitator", "duration_months": 24,
        "name": "Facilitator — 2-Year",
        "tagline": "Best price (37% off). Foundation IP share floors at 35%.",
        "price_usd": fee(1499.0),  # → $749.50
        "foundation_ip_pct": 35.0,
        "non_ip_pct": 10.0,
        "off_site_pct": 3.0,
        "birthright_ip_pct": 35.0,
        "other_content_pct": 10.0,
    },

    # ============ COMMUNITY (FREE entry) ============
    # NOTE: For Community, foundation 'default_pct' represents the *community's* referral share
    # (kept for legacy code compat). The foundation does NOT keep this percentage —
    # the community partner keeps it. Foundation's share of inbound referrals = 100 - default_pct.
    {
        "partner_type": "community", "duration_months": 0,  # 0 = no-expiry free plan
        "name": "Community — Starter (Free)",
        "tagline": "FREE forever. 8% on every referral.",
        "price_usd": 0.0,
        "default_pct": 8.0,
        "off_site_pct": 7.0,  # foundation share of community-attributed off-site purchases
    },
    {
        "partner_type": "community", "duration_months": 1,
        "name": "Community — Plus (Monthly)",
        "tagline": "10% referral share + custom UTM links + monthly digest.",
        "price_usd": fee(19.0),  # → $9.50
        "default_pct": 10.0,
        "off_site_pct": 5.0,
    },
    {
        "partner_type": "community", "duration_months": 12,
        "name": "Community — Pro (Annual)",
        "tagline": "12% referral + featured listing eligibility + volume bonuses.",
        "price_usd": fee(99.0),  # → $49.50
        "default_pct": 12.0,
        "off_site_pct": 4.0,
    },
    {
        "partner_type": "community", "duration_months": 24,
        "name": "Community — 2-Year Pro",
        "tagline": "14% locked + Founding eligibility + lifetime locked rate.",
        "price_usd": fee(149.0),  # → $74.50
        "default_pct": 14.0,
        "off_site_pct": 3.0,
    },

    # ============ RESEARCH (FREE entry + Eminence Sharing Agreement) ============
    {
        "partner_type": "research", "duration_months": 0,
        "name": "Research — Standard (Free)",
        "tagline": "FREE forever. Submit research + chronological listing + ESA signed.",
        "price_usd": 0.0,
        "default_pct": 5.0,  # foundation keeps 5% of any monetized research on-site
        "off_site_pct": 3.0,
    },
    {
        "partner_type": "research", "duration_months": 12,
        "name": "Research — Citation Pro (Annual)",
        "tagline": "DOI minting + citation analytics + press-release co-rights.",
        "price_usd": fee(99.0),  # → $49.50
        "default_pct": 5.0,
        "off_site_pct": 3.0,
    },
    {
        "partner_type": "research", "duration_months": 24,
        "name": "Research — Citation Pro (2-Year)",
        "tagline": "Same benefits, locked rates, Founding eligibility.",
        "price_usd": fee(149.0),  # → $74.50
        "default_pct": 5.0,
        "off_site_pct": 3.0,
    },

    # ============ VENDOR (all sales are non-IP) ============
    {
        "partner_type": "vendor", "duration_months": 1,
        "name": "Vendor — Monthly",
        "tagline": "Foundation share 22% on-site. Try month-to-month.",
        "price_usd": fee(49.0),  # → $24.50
        "default_pct": 22.0,  # foundation share on-site
        "off_site_pct": 7.0,
    },
    {
        "partner_type": "vendor", "duration_months": 12,
        "name": "Vendor — Annual",
        "tagline": "29% effective discount + foundation share drops to 17%.",
        "price_usd": fee(419.0),  # → $209.50
        "default_pct": 17.0,
        "off_site_pct": 5.0,
    },
    {
        "partner_type": "vendor", "duration_months": 24,
        "name": "Vendor — 2-Year",
        "tagline": "Best vendor margin. Foundation share floors at 12%.",
        "price_usd": fee(749.0),  # → $374.50
        "default_pct": 12.0,
        "off_site_pct": 3.0,
    },
]


async def main() -> None:
    now = now_iso()
    upserts = 0
    inserts = 0
    # Clear any prior plans not in this set (avoid stale duplicates from earlier seed runs)
    valid_keys = {(p["partner_type"], p["duration_months"]) for p in PLANS}
    async for existing in db.subscription_plans.find({}, {"_id": 0, "id": 1, "partner_type": 1, "duration_months": 1}):
        k = (existing.get("partner_type"), existing.get("duration_months"))
        if k not in valid_keys:
            await db.subscription_plans.delete_one({"id": existing["id"]})

    for spec in PLANS:
        key = {"partner_type": spec["partner_type"], "duration_months": spec["duration_months"]}
        existing = await db.subscription_plans.find_one(key)
        doc = {
            **spec,
            "currency": "usd",
            "active": True,
            "updated_at": now,
        }
        if existing:
            await db.subscription_plans.update_one(
                {"id": existing["id"]}, {"$set": doc}
            )
            upserts += 1
        else:
            doc["id"] = gen_id()
            doc["created_at"] = now
            await db.subscription_plans.insert_one(doc)
            inserts += 1
    total = await db.subscription_plans.count_documents({})
    print("== Subscription plans seed (v1.11.0 LOCKED MODEL) ==")
    print(f"   pre-traction fee multiplier: × {PRE_TRACTION_FEE_MULTIPLIER}")
    print(f"   inserts: {inserts}   updates: {upserts}")
    print(f"   total plans in DB: {total}")


if __name__ == "__main__":
    asyncio.run(main())
