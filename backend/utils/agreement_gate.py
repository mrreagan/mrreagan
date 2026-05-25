"""Reusable dependency: ensures the caller has signed the latest active
universal indemnification agreement. Used to gate partner-side actions that
require fresh consent after v2 publishing.

If the caller is NOT signed on the active version, raises 409 with a clear
error code so the frontend can show the "re-sign required" banner.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException

from auth_utils import get_current_user


async def require_active_agreement(user: dict = Depends(get_current_user)) -> dict:
    from database import db
    active = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not active:
        return user  # no agreement published yet — fail-open
    sig = await db.indemnification_signatures.find_one(
        {"user_id": user["id"], "version_id": active["id"]}
    )
    if not sig:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "agreement_required",
                "active_version": active["version"],
                "active_version_id": active["id"],
                "message": f"You must accept the latest agreement (v{active['version']}) before continuing.",
            },
        )
    return user
