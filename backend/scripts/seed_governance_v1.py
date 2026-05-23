"""One-time seed for Phase 6A.2 governance state.

Idempotent — safe to re-run.

What it does:
1. Mark the existing 4 governing members as `governance_member=True` and the
   first one (Dr Maya Aronson per current seed) as `is_ombudsman=True`.
2. Insert the initial Universal Indemnification v1.0 as active (if none exists).
3. Insert the default global_defaults singleton (if missing).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db
from models import gen_id, now_iso
from routers.governance import DEFAULT_REV_SHARE
from routers.legal import DEFAULT_INDEMNIFICATION_BODY


async def upsert_governance_members():
    # Promote admin + facilitators to governance members by default; mark admin as ombudsman.
    members = await db.users.find(
        {"role": {"$in": ["admin", "facilitator"]}}, {"_id": 0, "id": 1, "role": 1, "email": 1}
    ).to_list(50)
    if not members:
        print("[seed] No admin/facilitator users found — skipping member flags.")
        return 0
    updated = 0
    for m in members:
        is_omb = m.get("role") == "admin"
        res = await db.users.update_one(
            {"id": m["id"]},
            {"$set": {"governance_member": True, "is_ombudsman": is_omb}},
        )
        updated += res.modified_count
        print(f"[seed]  · {m['email']} → governance_member=True, is_ombudsman={is_omb}")
    return updated


async def seed_indemnification():
    existing = await db.indemnification_versions.find_one({"version": "1.0"})
    if existing:
        # Ensure it is active and no other version is active
        await db.indemnification_versions.update_many({"active": True}, {"$set": {"active": False}})
        await db.indemnification_versions.update_one(
            {"id": existing["id"]}, {"$set": {"active": True}}
        )
        print("[seed] Indemnification v1.0 already exists — re-activated.")
        return existing["id"]
    doc = {
        "id": gen_id(),
        "version": "1.0",
        "body": DEFAULT_INDEMNIFICATION_BODY,
        "summary_of_changes": "Initial placeholder text. Replace before launch.",
        "active": True,
        "created_by": "system",
        "created_at": now_iso(),
        "activated_at": now_iso(),
    }
    await db.indemnification_versions.insert_one(dict(doc))
    print(f"[seed] Inserted Indemnification v1.0 (id={doc['id']}).")
    return doc["id"]


async def seed_global_defaults(indem_id: str):
    existing = await db.foundation_settings.find_one({"key": "global_defaults"})
    if existing:
        await db.foundation_settings.update_one(
            {"key": "global_defaults"},
            {"$set": {
                "indemnification_active_version_id": indem_id,
                "updated_at": now_iso(),
            }},
        )
        print("[seed] global_defaults exists — refreshed indemnification pointer.")
        return
    doc = {
        "key": "global_defaults",
        "rev_share": DEFAULT_REV_SHARE,
        "min_listing_rating": 0.0,
        "indemnification_active_version_id": indem_id,
        "updated_by": "system",
        "updated_at": now_iso(),
    }
    await db.foundation_settings.insert_one(dict(doc))
    print("[seed] Inserted global_defaults singleton.")


async def main():
    print("== Governance v1 seed ==")
    n = await upsert_governance_members()
    print(f"   members updated: {n}")
    indem_id = await seed_indemnification()
    await seed_global_defaults(indem_id)
    # Smoke counts
    n_members = await db.users.count_documents({"governance_member": True})
    n_omb = await db.users.count_documents({"is_ombudsman": True})
    print(f"   total governance_members: {n_members}; ombudsman: {n_omb}")
    print("== done ==")


if __name__ == "__main__":
    asyncio.run(main())
