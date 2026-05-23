"""Audit log viewer (admin + ombudsman). Read-only.

The log is append-only; there is no write endpoint here. Writes happen via
`utils.audit.log_action()` invoked from governance/legal/admin handlers.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user

logger = logging.getLogger("birthright.audit_api")
router = APIRouter(prefix="/audit", tags=["audit"])


def _require_admin_or_ombudsman(user: dict) -> None:
    if user.get("role") == "admin":
        return
    if user.get("is_ombudsman"):
        return
    raise HTTPException(status_code=403, detail="Only admin or ombudsman can view the audit log.")


@router.get("")
async def list_entries(
    limit: int = Query(100, ge=1, le=500),
    action_prefix: Optional[str] = None,
    actor_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    _require_admin_or_ombudsman(user)
    from database import db
    query: dict = {}
    if action_prefix:
        query["action"] = {"$regex": f"^{action_prefix}"}
    if actor_id:
        query["actor_id"] = actor_id
    if target_type:
        query["target_type"] = target_type
    if target_id:
        query["target_id"] = target_id
    entries = await db.audit_log.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return entries
