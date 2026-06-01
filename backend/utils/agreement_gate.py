"""Reusable dependency: ensures the caller has signed the latest active
universal indemnification agreement. Used to gate partner-side actions that
require fresh consent after v2 publishing.

Two variants:
  - `require_active_agreement`  — gates everyone (used by DM + subscription
    flows where any user is treated equally).
  - `require_active_agreement_partner` — gates partners; ADMINS PASS
    THROUGH so they can run platform operations (publishing new agreement
    versions, moderating content, etc.) without first signing every
    version they author. This is the gate to use on partner-write
    endpoints (product/artifact/featured-slot/AI-Studio creation,
    payout edits).

Both raise HTTP 409 with code=agreement_required and the active version
metadata so the frontend can route the user to /legal/agreement.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException

from auth_utils import get_current_user


def _agreement_required(active: dict) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "code": "agreement_required",
            "active_version": active["version"],
            "active_version_id": active["id"],
            "message": f"You must accept the latest agreement (v{active['version']}) before continuing.",
        },
    )


async def require_active_agreement(user: dict = Depends(get_current_user)) -> dict:
    from database import db
    active = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not active:
        return user  # no agreement published yet — fail-open
    sig = await db.indemnification_signatures.find_one(
        {"user_id": user["id"], "version_id": active["id"]}
    )
    if not sig:
        raise _agreement_required(active)
    return user


async def require_active_agreement_partner(user: dict = Depends(get_current_user)) -> dict:
    """Like `require_active_agreement` but exempts admins.

    Used on partner-write endpoints. Admins are exempt because they operate
    on behalf of the Foundation — gating their access would create a
    bootstrap deadlock (an admin couldn't publish v2 without first signing
    v2, which doesn't exist yet from their POV). Admins still see the
    banner like everyone else; this exemption is API-side only.
    """
    if (user or {}).get("role") == "admin":
        return user
    from database import db
    active = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not active:
        return user
    sig = await db.indemnification_signatures.find_one(
        {"user_id": user["id"], "version_id": active["id"]}
    )
    if not sig:
        raise _agreement_required(active)
    return user
