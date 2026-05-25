"""Founding-Partner gating — v1.11.0 Step 5.

Public stats endpoint + admin cap control. The cap is the maximum number of
partners who can hold the `is_founding_partner` flag simultaneously. Cap
defaults to 50 and is stored in `foundation_settings` (key='founding_partner_cap').

Applicants opt-in via `apply_as_founding_partner=true` on their partner
application. Admin approval is what actually flips `is_founding_partner=True` on
the profile — and it only happens if `taken < cap`. If approving an applicant
who requested founding-partner status would exceed the cap, the partner is
still approved but without the flag (admin sees a warning + decides).

The flag itself is purely advisory data the directory and rev-share resolver
read. Founding partners get:
  - Public "Founding Partner" badge on cards + profile
  - Locked rev-share rate for the duration of `founding_rate_expires_at`
    (default: 5 years from grant)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth_utils import require_roles
from models import FoundingPartnerCapUpdate, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.founding")

DEFAULT_CAP = 50
DEFAULT_GRANT_YEARS = 5

public_router = APIRouter(prefix="/founding-partners", tags=["founding-partners"])
admin_router = APIRouter(prefix="/admin/founding-partners", tags=["founding-partners-admin"])


async def _get_cap(db) -> int:
    doc = await db.foundation_settings.find_one({"key": "founding_partner_cap"}, {"_id": 0})
    if doc and doc.get("cap"):
        return int(doc["cap"])
    return DEFAULT_CAP


async def _taken_count(db) -> int:
    """Count CURRENT founding partners (flag set + expiration not passed)."""
    now = datetime.now(timezone.utc).isoformat()
    return await db.partner_profiles.count_documents({
        "is_founding_partner": True,
        "status": "active",
        "$or": [
            {"founding_rate_expires_at": None},
            {"founding_rate_expires_at": {"$gt": now}},
        ],
    })


@public_router.get("/stats")
async def stats():
    from database import db
    cap = await _get_cap(db)
    taken = await _taken_count(db)
    return {
        "cap": cap,
        "taken": taken,
        "available": max(cap - taken, 0),
        "is_open": taken < cap,
    }


@admin_router.put("/cap")
async def update_cap(data: FoundingPartnerCapUpdate, user: dict = Depends(require_roles("admin"))):
    from database import db
    await db.foundation_settings.update_one(
        {"key": "founding_partner_cap"},
        {"$set": {"key": "founding_partner_cap", "cap": data.cap, "updated_at": now_iso(), "updated_by": user["id"]}},
        upsert=True,
    )
    await log_action(db, user, "founding_partner.cap.update", metadata={"cap": data.cap})
    return {"cap": data.cap}


@admin_router.post("/{profile_id}/grant")
async def grant_founding_status(profile_id: str, user: dict = Depends(require_roles("admin"))):
    """Flip `is_founding_partner=true` and stamp `founding_rate_expires_at` to now+5y.
    Returns 400 if the cap is full."""
    from database import db
    profile = await db.partner_profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.get("is_founding_partner"):
        raise HTTPException(status_code=400, detail="Already a founding partner")
    cap = await _get_cap(db)
    taken = await _taken_count(db)
    if taken >= cap:
        raise HTTPException(status_code=400, detail=f"Founding-partner cap is full ({taken}/{cap}). Raise the cap to grant more.")
    expires = (datetime.now(timezone.utc) + timedelta(days=DEFAULT_GRANT_YEARS * 365)).isoformat()
    await db.partner_profiles.update_one(
        {"id": profile_id},
        {"$set": {"is_founding_partner": True, "founding_rate_expires_at": expires, "updated_at": now_iso()}},
    )
    await log_action(
        db, user, "founding_partner.grant",
        target_type="partner_profile", target_id=profile_id,
        metadata={"partner_type": profile.get("partner_type"), "expires_at": expires},
    )
    out = await db.partner_profiles.find_one({"id": profile_id}, {"_id": 0, "webhook_secret": 0})
    return out


@admin_router.post("/{profile_id}/revoke")
async def revoke_founding_status(profile_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    profile = await db.partner_profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.partner_profiles.update_one(
        {"id": profile_id},
        {"$set": {"is_founding_partner": False, "founding_rate_expires_at": None, "updated_at": now_iso()}},
    )
    await log_action(
        db, user, "founding_partner.revoke",
        target_type="partner_profile", target_id=profile_id,
        metadata={"partner_type": profile.get("partner_type")},
    )
    out = await db.partner_profiles.find_one({"id": profile_id}, {"_id": 0, "webhook_secret": 0})
    return out
