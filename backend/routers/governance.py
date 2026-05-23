"""Governance: proposals, voting, global defaults (rev-share), member flags.

Roles:
  - Anyone authenticated can read proposals and global defaults.
  - Only `governance_member=True` users (or admin) can create proposals & vote.
  - Only admin can update global defaults or set member flags.
  - Only admin or ombudsman can close a proposal early.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user, require_roles
from models import (
    GlobalDefaultsUpdate,
    MemberFlagsUpdate,
    ProposalCreate,
    VoteCast,
    gen_id,
    now_iso,
)
from utils.audit import log_action

logger = logging.getLogger("birthright.governance")
router = APIRouter(prefix="/governance", tags=["governance"])


# ============ HELPERS ============

def _require_governance(user: dict) -> None:
    if user.get("role") == "admin":
        return
    if not user.get("governance_member"):
        raise HTTPException(
            status_code=403,
            detail="Only governance members can perform this action.",
        )


async def _recompute_tally(db, proposal_id: str) -> dict:
    pipeline = [
        {"$match": {"proposal_id": proposal_id}},
        {"$group": {"_id": "$vote", "count": {"$sum": 1}}},
    ]
    tally = {"yes_count": 0, "no_count": 0, "abstain_count": 0}
    async for row in db.governance_votes.aggregate(pipeline):
        key = f"{row['_id']}_count"
        if key in tally:
            tally[key] = row["count"]
    await db.proposals.update_one({"id": proposal_id}, {"$set": tally})
    return tally


# ============ GLOBAL DEFAULTS ============

DEFAULT_REV_SHARE = {
    "facilitator": [
        {"name": "standard", "pct": 70.0, "description": "Default facilitator share of workshop net revenue."},
    ],
    "community": [
        {"name": "standard", "pct": 10.0, "description": "Default referral payout to community partners."},
    ],
    "research": [
        {"name": "standard", "pct": 0.0, "description": "Research partners receive grants, not rev-share, by default."},
    ],
    "vendor": [
        {"name": "standard", "pct": 80.0, "description": "Default vendor share of vendor-listed product net revenue."},
    ],
}


@router.get("/defaults")
async def get_defaults():
    from database import db
    doc = await db.foundation_settings.find_one({"key": "global_defaults"}, {"_id": 0})
    if not doc:
        doc = {
            "key": "global_defaults",
            "rev_share": DEFAULT_REV_SHARE,
            "min_listing_rating": 0.0,
            "indemnification_active_version_id": None,
            "updated_by": None,
            "updated_at": None,
        }
        await db.foundation_settings.insert_one(dict(doc))
        doc.pop("_id", None)
    return doc


@router.put("/defaults")
async def update_defaults(
    data: GlobalDefaultsUpdate,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_by"] = user["id"]
    updates["updated_at"] = now_iso()
    await db.foundation_settings.update_one(
        {"key": "global_defaults"}, {"$set": updates}, upsert=True
    )
    await log_action(
        db, user, "governance.defaults.update",
        target_type="global_defaults", target_id="global_defaults",
        metadata={"fields": list(updates.keys())},
    )
    doc = await db.foundation_settings.find_one({"key": "global_defaults"}, {"_id": 0})
    return doc


# ============ MEMBER FLAGS ============

@router.get("/members")
async def list_members(user: dict = Depends(get_current_user)):
    """List governance members + ombudsman. Public to all signed-in users so partners
    know who to escalate to."""
    from database import db
    members = await db.users.find(
        {"$or": [{"governance_member": True}, {"is_ombudsman": True}]},
        {"_id": 0, "password_hash": 0},
    ).to_list(500)
    return [
        {
            "id": m["id"],
            "name": f"{m['first_name']} {m['last_name']}",
            "role": m["role"],
            "governance_member": bool(m.get("governance_member")),
            "is_ombudsman": bool(m.get("is_ombudsman")),
            "bio": m.get("bio", ""),
            "credentials": m.get("credentials", ""),
            "avatar_url": m.get("avatar_url", ""),
        }
        for m in members
    ]


@router.put("/members/{user_id}")
async def set_member_flags(
    user_id: str,
    data: MemberFlagsUpdate,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    target = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    # Ombudsman implies governance member
    if updates.get("is_ombudsman") and not target.get("governance_member"):
        updates["governance_member"] = True
    await db.users.update_one({"id": user_id}, {"$set": updates})
    await log_action(
        db, user, "governance.member.update",
        target_type="user", target_id=user_id,
        metadata={"changes": updates, "target_email": target.get("email")},
    )
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return updated


# ============ PROPOSALS ============

@router.get("/proposals")
async def list_proposals(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    proposals = await db.proposals.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return proposals


@router.post("/proposals")
async def create_proposal(
    data: ProposalCreate,
    user: dict = Depends(get_current_user),
):
    _require_governance(user)
    from database import db
    closes_at = data.voting_closes_at
    if not closes_at:
        closes_at = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    proposal = {
        "id": gen_id(),
        "title": data.title.strip(),
        "summary": data.summary.strip(),
        "body": data.body.strip(),
        "category": data.category,
        "proposer_id": user["id"],
        "proposer_name": f"{user['first_name']} {user['last_name']}",
        "status": "open",
        "created_at": now_iso(),
        "voting_closes_at": closes_at,
        "closed_at": None,
        "closed_by": None,
        "implementation_notes": (data.implementation_notes or "").strip(),
        "yes_count": 0,
        "no_count": 0,
        "abstain_count": 0,
    }
    await db.proposals.insert_one(proposal)
    proposal.pop("_id", None)
    await log_action(
        db, user, "governance.proposal.create",
        target_type="proposal", target_id=proposal["id"],
        metadata={"title": proposal["title"], "category": proposal["category"]},
    )
    return proposal


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    from database import db
    p = await db.proposals.find_one({"id": proposal_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return p


@router.get("/proposals/{proposal_id}/votes")
async def list_votes(proposal_id: str, user: dict = Depends(get_current_user)):
    from database import db
    p = await db.proposals.find_one({"id": proposal_id}, {"_id": 0, "id": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    votes = await db.governance_votes.find(
        {"proposal_id": proposal_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return votes


@router.post("/proposals/{proposal_id}/vote")
async def cast_vote(
    proposal_id: str,
    data: VoteCast,
    user: dict = Depends(get_current_user),
):
    _require_governance(user)
    from database import db
    p = await db.proposals.find_one({"id": proposal_id})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if p["status"] != "open":
        raise HTTPException(status_code=400, detail=f"Proposal is {p['status']}, no longer accepting votes")
    # one vote per voter — update on re-cast
    existing = await db.governance_votes.find_one({
        "proposal_id": proposal_id, "voter_id": user["id"],
    })
    if existing:
        await db.governance_votes.update_one(
            {"id": existing["id"]},
            {"$set": {
                "vote": data.vote,
                "comment": (data.comment or "").strip(),
                "updated_at": now_iso(),
            }},
        )
        vote_id = existing["id"]
        verb = "update"
    else:
        vote = {
            "id": gen_id(),
            "proposal_id": proposal_id,
            "voter_id": user["id"],
            "voter_name": f"{user['first_name']} {user['last_name']}",
            "vote": data.vote,
            "comment": (data.comment or "").strip(),
            "created_at": now_iso(),
        }
        await db.governance_votes.insert_one(vote)
        vote_id = vote["id"]
        verb = "create"

    tally = await _recompute_tally(db, proposal_id)
    await log_action(
        db, user, f"governance.vote.{verb}",
        target_type="proposal", target_id=proposal_id,
        metadata={"vote": data.vote, "vote_id": vote_id},
    )
    return {"success": True, **tally}


@router.post("/proposals/{proposal_id}/close")
async def close_proposal(
    proposal_id: str,
    user: dict = Depends(get_current_user),
):
    """Close voting and tally. Admin OR ombudsman, OR the original proposer (withdraw)."""
    from database import db
    p = await db.proposals.find_one({"id": proposal_id})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if p["status"] != "open":
        raise HTTPException(status_code=400, detail=f"Proposal already {p['status']}")

    role = user.get("role")
    is_admin = role == "admin"
    is_ombudsman = bool(user.get("is_ombudsman"))
    is_proposer = user["id"] == p["proposer_id"]
    if not (is_admin or is_ombudsman or is_proposer):
        raise HTTPException(status_code=403, detail="Only admin, ombudsman, or the proposer can close")

    if is_proposer and not (is_admin or is_ombudsman):
        new_status = "withdrawn"
    else:
        tally = await _recompute_tally(db, proposal_id)
        new_status = "passed" if tally["yes_count"] > tally["no_count"] else "failed"

    await db.proposals.update_one(
        {"id": proposal_id},
        {"$set": {"status": new_status, "closed_at": now_iso(), "closed_by": user["id"]}},
    )
    await log_action(
        db, user, "governance.proposal.close",
        target_type="proposal", target_id=proposal_id,
        metadata={"status": new_status},
    )
    updated = await db.proposals.find_one({"id": proposal_id}, {"_id": 0})
    return updated
