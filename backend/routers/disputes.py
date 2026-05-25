"""Disputes (Phase 6C.3) + Ombudsman queue (Phase 6C.2).

Disputes are records of conflict between users on the platform — payment issues,
conduct violations, content moderation appeals, etc. They follow a status flow:
    open → under_review → resolved | dismissed

The Ombudsman queue (`/admin/ombudsman`) surfaces:
  - flagged DM threads (data already in `dm_threads.ombudsman_flagged`)
  - open + under_review disputes assigned to ombudsmen or unassigned

Permission model:
  - Anyone signed-in can file a dispute against another user.
  - Filer + respondent can each see their own disputes (`/me/disputes`).
  - Admin OR `is_ombudsman=true` users can list, assign, update, and resolve.

Step 10 hand-off:
  Resolution records an optional `financial_credit_usd` value so the refund/
  clawback cascade in Step 10 can pull from `disputes` to trigger refunds.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user, require_roles
from models import (
    DisputeAssign, DisputeCreate, DisputeResolution, DisputeStatusUpdate,
    gen_id, now_iso,
)
from utils.audit import log_action

logger = logging.getLogger("birthright.disputes")

router = APIRouter(prefix="/disputes", tags=["disputes"])
my_router = APIRouter(prefix="/me/disputes", tags=["disputes"])
admin_router = APIRouter(prefix="/admin/disputes", tags=["disputes-admin"])
ombudsman_router = APIRouter(prefix="/admin/ombudsman", tags=["ombudsman"])


# ============ HELPERS ============

async def _require_admin_or_ombuds(user: dict) -> dict:
    if user.get("role") == "admin" or user.get("is_ombudsman"):
        return user
    raise HTTPException(status_code=403, detail="Admin or ombudsman role required")


async def _enrich_dispute(db, d: dict) -> dict:
    user_ids = {d.get("filed_by"), d.get("against_user_id"), d.get("assigned_ombudsman_id")}
    user_ids.discard(None)
    if not user_ids:
        return d
    users_by = {}
    async for u in db.users.find(
        {"id": {"$in": list(user_ids)}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1},
    ):
        users_by[u["id"]] = {
            "id": u["id"],
            "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("email", "Birthright user"),
            "email": u.get("email"),
        }
    d["filed_by_user"] = users_by.get(d.get("filed_by"))
    d["against_user"] = users_by.get(d.get("against_user_id"))
    if d.get("assigned_ombudsman_id"):
        d["assigned_ombudsman_user"] = users_by.get(d["assigned_ombudsman_id"])
    return d


# ============ FILER-SIDE ENDPOINTS ============

@router.post("")
async def file_dispute(data: DisputeCreate, user: dict = Depends(get_current_user)):
    from database import db
    if data.against_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot file a dispute against yourself")
    respondent = await db.users.find_one({"id": data.against_user_id}, {"_id": 0, "id": 1})
    if not respondent:
        raise HTTPException(status_code=404, detail="Respondent not found")
    # Optional FK validation
    if data.transaction_id:
        txn = await db.payment_transactions.find_one({"id": data.transaction_id, "user_id": user["id"]})
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found or not yours")
    if data.thread_id:
        thread = await db.dm_threads.find_one(
            {"id": data.thread_id, "participants": user["id"]}, {"_id": 0, "id": 1}
        )
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found or you're not a participant")

    doc = {
        "id": gen_id(),
        "filed_by": user["id"],
        "against_user_id": data.against_user_id,
        "category": data.category,
        "title": data.title.strip(),
        "description": data.description.strip(),
        "transaction_id": data.transaction_id,
        "thread_id": data.thread_id,
        "status": "open",
        "assigned_ombudsman_id": None,
        "events": [{"at": now_iso(), "by": user["id"], "type": "filed", "note": "Dispute filed."}],
        "resolution": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.disputes.insert_one(dict(doc))
    await log_action(
        db, user, "dispute.file", target_type="dispute", target_id=doc["id"],
        metadata={"category": data.category, "against": data.against_user_id, "transaction_id": data.transaction_id},
    )
    return await _enrich_dispute(db, doc)


@my_router.get("")
async def my_disputes(
    role: str = Query("all", regex="^(all|filed|against)$"),
    user: dict = Depends(get_current_user),
):
    from database import db
    if role == "filed":
        q = {"filed_by": user["id"]}
    elif role == "against":
        q = {"against_user_id": user["id"]}
    else:
        q = {"$or": [{"filed_by": user["id"]}, {"against_user_id": user["id"]}]}
    rows = await db.disputes.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [await _enrich_dispute(db, r) for r in rows]


@my_router.get("/{dispute_id}")
async def my_dispute_detail(dispute_id: str, user: dict = Depends(get_current_user)):
    from database import db
    d = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if user["id"] not in (d["filed_by"], d["against_user_id"]):
        raise HTTPException(status_code=403, detail="Not your dispute")
    return await _enrich_dispute(db, d)


# ============ ADMIN / OMBUDSMAN ============

@admin_router.get("")
async def admin_list_disputes(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    await _require_admin_or_ombuds(user)
    from database import db
    q: dict = {}
    if status:
        q["status"] = status
    if assigned_to == "me":
        q["assigned_ombudsman_id"] = user["id"]
    elif assigned_to == "unassigned":
        q["assigned_ombudsman_id"] = None
    rows = await db.disputes.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [await _enrich_dispute(db, r) for r in rows]


@admin_router.get("/{dispute_id}")
async def admin_dispute_detail(dispute_id: str, user: dict = Depends(get_current_user)):
    await _require_admin_or_ombuds(user)
    from database import db
    d = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return await _enrich_dispute(db, d)


@admin_router.post("/{dispute_id}/assign")
async def admin_assign(
    dispute_id: str, data: DisputeAssign, user: dict = Depends(get_current_user),
):
    await _require_admin_or_ombuds(user)
    from database import db
    target = await db.users.find_one(
        {"id": data.ombudsman_user_id, "is_ombudsman": True}, {"_id": 0, "id": 1},
    )
    if not target:
        raise HTTPException(status_code=400, detail="Target user is not an ombudsman")
    d = await db.disputes.find_one({"id": dispute_id})
    if not d:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if d.get("status") in ("resolved", "dismissed"):
        raise HTTPException(status_code=400, detail=f"Dispute is already {d['status']}")
    event = {"at": now_iso(), "by": user["id"], "type": "assigned", "note": f"Assigned to {data.ombudsman_user_id}"}
    await db.disputes.update_one(
        {"id": dispute_id},
        {"$set": {"assigned_ombudsman_id": data.ombudsman_user_id, "updated_at": now_iso()},
         "$push": {"events": event}},
    )
    await log_action(db, user, "dispute.assign", target_type="dispute", target_id=dispute_id,
                    metadata={"to": data.ombudsman_user_id})
    return await _enrich_dispute(db, await db.disputes.find_one({"id": dispute_id}, {"_id": 0}))


@admin_router.post("/{dispute_id}/status")
async def admin_update_status(
    dispute_id: str, data: DisputeStatusUpdate, user: dict = Depends(get_current_user),
):
    await _require_admin_or_ombuds(user)
    from database import db
    d = await db.disputes.find_one({"id": dispute_id})
    if not d:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if data.status in ("resolved", "dismissed"):
        raise HTTPException(status_code=400, detail="Use /resolve for terminal states")
    event = {"at": now_iso(), "by": user["id"], "type": "status_change",
             "from": d["status"], "to": data.status, "note": data.note.strip()}
    await db.disputes.update_one(
        {"id": dispute_id},
        {"$set": {"status": data.status, "updated_at": now_iso()}, "$push": {"events": event}},
    )
    await log_action(db, user, "dispute.status", target_type="dispute", target_id=dispute_id,
                    metadata={"from": d["status"], "to": data.status})
    return await _enrich_dispute(db, await db.disputes.find_one({"id": dispute_id}, {"_id": 0}))


@admin_router.post("/{dispute_id}/resolve")
async def admin_resolve(
    dispute_id: str, data: DisputeResolution, user: dict = Depends(get_current_user),
):
    await _require_admin_or_ombuds(user)
    from database import db
    d = await db.disputes.find_one({"id": dispute_id})
    if not d:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if d.get("status") in ("resolved", "dismissed"):
        raise HTTPException(status_code=400, detail=f"Dispute is already {d['status']}")
    final_status = "dismissed" if data.outcome == "dismissed" else "resolved"
    resolution = {
        "outcome": data.outcome,
        "note": data.resolution_note.strip(),
        "financial_credit_usd": data.financial_credit_usd,
        "resolved_by": user["id"],
        "resolved_at": now_iso(),
    }
    event = {"at": now_iso(), "by": user["id"], "type": "resolved",
             "from": d["status"], "to": final_status,
             "outcome": data.outcome, "note": data.resolution_note.strip()}
    await db.disputes.update_one(
        {"id": dispute_id},
        {"$set": {"status": final_status, "resolution": resolution, "updated_at": now_iso()},
         "$push": {"events": event}},
    )
    await log_action(db, user, "dispute.resolve", target_type="dispute", target_id=dispute_id,
                    metadata={"outcome": data.outcome, "financial_credit_usd": data.financial_credit_usd})
    return await _enrich_dispute(db, await db.disputes.find_one({"id": dispute_id}, {"_id": 0}))


# ============ OMBUDSMAN QUEUE (Phase 6C.2) ============

@ombudsman_router.get("/queue")
async def ombudsman_queue(user: dict = Depends(get_current_user)):
    """One-stop queue: open + under_review disputes assigned to me (or
    unassigned if I'm an ombudsman/admin), plus flagged DM threads."""
    await _require_admin_or_ombuds(user)
    from database import db
    is_admin = user.get("role") == "admin"
    dispute_q: dict = {"status": {"$in": ["open", "under_review"]}}
    if not is_admin:
        # Ombudsmen see only their assigned + unassigned
        dispute_q["$or"] = [
            {"assigned_ombudsman_id": user["id"]},
            {"assigned_ombudsman_id": None},
        ]
    disputes_open = await db.disputes.find(dispute_q, {"_id": 0}).sort("created_at", -1).to_list(200)
    enriched = [await _enrich_dispute(db, d) for d in disputes_open]

    flagged_threads = await db.dm_threads.find(
        {"ombudsman_flagged": True, "status": {"$ne": "archived"}}, {"_id": 0},
    ).sort("ombudsman_flagged_at", -1).to_list(200)

    return {
        "disputes": enriched,
        "flagged_threads": flagged_threads,
        "counts": {
            "open_disputes": sum(1 for d in disputes_open if d["status"] == "open"),
            "under_review_disputes": sum(1 for d in disputes_open if d["status"] == "under_review"),
            "flagged_threads": len(flagged_threads),
        },
    }


@ombudsman_router.get("/users")
async def list_ombudsmen(user: dict = Depends(get_current_user)):
    """Used by the assign dropdown."""
    await _require_admin_or_ombuds(user)
    from database import db
    rows = await db.users.find(
        {"is_ombudsman": True},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1},
    ).to_list(50)
    return [
        {
            "id": u["id"],
            "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("email"),
            "email": u.get("email"),
        }
        for u in rows
    ]
