"""Refund / Clawback admin endpoints — v1.11.0 Step 10.

Exposes:
  POST   /api/admin/refunds                       — fire the full refund cascade
  GET    /api/admin/refunds                       — list past cascades (audit)
  GET    /api/admin/refunds/{cascade_id}          — detail of one cascade
  GET    /api/admin/clawbacks                     — pending clawbacks (paid credits that need recovery)
  POST   /api/admin/clawbacks/{id}/resolve        — mark recovered or written off
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import require_roles
from models import ClawbackResolve, RefundCascadeRequest, now_iso
from utils.audit import log_action
from utils.refund_cascade import run_refund_cascade

logger = logging.getLogger("birthright.refunds_admin")

admin_router = APIRouter(prefix="/admin/refunds", tags=["refunds-admin"])
clawback_router = APIRouter(prefix="/admin/clawbacks", tags=["clawbacks-admin"])


@admin_router.post("")
async def trigger_refund(
    data: RefundCascadeRequest,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    try:
        cascade = await run_refund_cascade(
            db, txn_id=data.txn_id, actor=user,
            reason=data.reason.strip(), skip_stripe=data.skip_stripe,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return cascade


@admin_router.get("")
async def list_cascades(
    txn_type: Optional[str] = None,
    limit: int = Query(default=200, le=1000),
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    q: dict = {}
    if txn_type:
        q["txn_type"] = txn_type
    rows = await db.refund_cascades.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return rows


@admin_router.get("/{cascade_id}")
async def get_cascade(cascade_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    c = await db.refund_cascades.find_one({"id": cascade_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Cascade not found")
    return c


# ============ CLAWBACKS ============

@clawback_router.get("")
async def list_clawbacks(
    status: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    q: dict = {}
    if status:
        q["status"] = status
    rows = await db.clawback_pending.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Enrich with partner name
    partner_ids = list({r["partner_user_id"] for r in rows if r.get("partner_user_id")})
    users_by = {}
    if partner_ids:
        async for u in db.users.find(
            {"id": {"$in": partner_ids}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1},
        ):
            users_by[u["id"]] = u
    for r in rows:
        u = users_by.get(r.get("partner_user_id"), {})
        r["partner_name"] = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        r["partner_email"] = u.get("email")
    return rows


@clawback_router.post("/{clawback_id}/resolve")
async def resolve_clawback(
    clawback_id: str,
    data: ClawbackResolve,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    cb = await db.clawback_pending.find_one({"id": clawback_id})
    if not cb:
        raise HTTPException(status_code=404, detail="Clawback not found")
    if cb.get("status") != "pending_recovery":
        raise HTTPException(status_code=400, detail=f"Clawback is already {cb['status']}")
    await db.clawback_pending.update_one(
        {"id": clawback_id},
        {"$set": {
            "status": data.status,
            "resolved_at": now_iso(),
            "resolved_by": user["id"],
            "resolution_note": data.note.strip(),
        }},
    )
    await log_action(
        db, user, f"clawback.{data.status}",
        target_type="clawback_pending", target_id=clawback_id,
        metadata={"amount_usd": cb.get("amount_usd"), "partner_user_id": cb.get("partner_user_id")},
    )
    return await db.clawback_pending.find_one({"id": clawback_id}, {"_id": 0})
