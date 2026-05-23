"""Migrate existing reviews from workshop-only to polymorphic schema.

Backfills: subject_type, subject_id, subject_category, partner_id, verified_purchase,
moderated, reported_count, updated_at.

Idempotent: safe to re-run.
"""
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from database import db  # noqa: E402


async def main():
    total = await db.reviews.count_documents({})
    needs_migration = await db.reviews.count_documents({"subject_type": {"$exists": False}})
    print(f"Total reviews: {total}; need migration: {needs_migration}")
    if needs_migration == 0:
        print("Nothing to do.")
        return

    cursor = db.reviews.find({"subject_type": {"$exists": False}}, {"_id": 0})
    updated = 0
    async for r in cursor:
        workshop_id = r.get("workshop_id")
        if not workshop_id:
            print(f"  skipping review {r.get('id')} — no workshop_id")
            continue
        w = await db.workshops.find_one({"id": workshop_id}, {"_id": 0, "facilitator_id": 1})
        verified = False
        if r.get("user_id"):
            reg = await db.registrations.find_one(
                {"workshop_id": workshop_id, "user_id": r["user_id"], "payment_status": "paid"}
            )
            verified = bool(reg)
        update_doc = {
            "subject_type": "workshop",
            "subject_id": workshop_id,
            "subject_category": "workshop",
            "partner_id": (w or {}).get("facilitator_id"),
            "verified_purchase": verified,
            "moderated": False,
            "reported_count": 0,
        }
        await db.reviews.update_one({"id": r["id"]}, {"$set": update_doc})
        updated += 1

    print(f"Migrated {updated} reviews.")


if __name__ == "__main__":
    asyncio.run(main())
