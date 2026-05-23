"""Seed 12 default subscription plans (4 partner_types × 3 durations).

Idempotent. Run via `python -m scripts.seed_subscription_plans`.

Pricing intent (placeholders — admin tunes for production):
  • Shorter duration → higher rev-share %
  • Longer duration → lower rev-share % (volume/commitment discount on share)
  • Facilitator plans carry TWO tiers:
      - birthright_ip_pct: when facilitator presents Birthright IP materials
      - other_content_pct: when facilitator presents own / vendor content
    Birthright IP is always the higher of the two.
  • Research partner subscriptions exist for site access; default rev-share is
    0% because research collaborations are typically grant-based.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
from models import gen_id, now_iso


PLANS = [
    # ---- Facilitators ----
    {
        "partner_type": "facilitator", "duration_months": 1,
        "name": "Facilitator — Monthly",
        "tagline": "Try Birthright facilitation. Highest rev-share, lowest commitment.",
        "price_usd": 99.0,
        "birthright_ip_pct": 70.0, "other_content_pct": 50.0,
    },
    {
        "partner_type": "facilitator", "duration_months": 12,
        "name": "Facilitator — Annual",
        "tagline": "Most popular. Save vs. monthly with steady rev-share.",
        "price_usd": 999.0,
        "birthright_ip_pct": 65.0, "other_content_pct": 45.0,
    },
    {
        "partner_type": "facilitator", "duration_months": 24,
        "name": "Facilitator — 2-Year",
        "tagline": "Deepest commitment. Best price; rev-share tuned for longevity.",
        "price_usd": 1799.0,
        "birthright_ip_pct": 60.0, "other_content_pct": 40.0,
    },
    # ---- Community ----
    {
        "partner_type": "community", "duration_months": 1,
        "name": "Community — Monthly",
        "tagline": "Refer participants and track payouts month to month.",
        "price_usd": 29.0,
        "default_pct": 12.0,
    },
    {
        "partner_type": "community", "duration_months": 12,
        "name": "Community — Annual",
        "tagline": "Steady year-long partnership.",
        "price_usd": 299.0,
        "default_pct": 10.0,
    },
    {
        "partner_type": "community", "duration_months": 24,
        "name": "Community — 2-Year",
        "tagline": "Anchor partner. Long-term referral relationship.",
        "price_usd": 549.0,
        "default_pct": 8.0,
    },
    # ---- Research ----
    {
        "partner_type": "research", "duration_months": 1,
        "name": "Research — Monthly",
        "tagline": "Access for short-term studies. Grant-funded engagements still apply.",
        "price_usd": 49.0,
        "default_pct": 0.0,
    },
    {
        "partner_type": "research", "duration_months": 12,
        "name": "Research — Annual",
        "tagline": "Standard academic year cadence.",
        "price_usd": 499.0,
        "default_pct": 0.0,
    },
    {
        "partner_type": "research", "duration_months": 24,
        "name": "Research — 2-Year",
        "tagline": "Multi-year cohort study cadence.",
        "price_usd": 899.0,
        "default_pct": 0.0,
    },
    # ---- Vendors ----
    {
        "partner_type": "vendor", "duration_months": 1,
        "name": "Vendor — Monthly",
        "tagline": "List materials and earn the highest vendor share.",
        "price_usd": 49.0,
        "default_pct": 82.0,
    },
    {
        "partner_type": "vendor", "duration_months": 12,
        "name": "Vendor — Annual",
        "tagline": "Steady catalog presence with strong margins.",
        "price_usd": 499.0,
        "default_pct": 78.0,
    },
    {
        "partner_type": "vendor", "duration_months": 24,
        "name": "Vendor — 2-Year",
        "tagline": "Long-term catalog anchor partner.",
        "price_usd": 899.0,
        "default_pct": 75.0,
    },
]


async def main() -> None:
    now = now_iso()
    upserts = 0
    inserts = 0
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
    print("== Subscription plans seed ==")
    print(f"   inserts: {inserts}   updates: {upserts}")
    print(f"   total plans in DB: {total}")


if __name__ == "__main__":
    asyncio.run(main())
