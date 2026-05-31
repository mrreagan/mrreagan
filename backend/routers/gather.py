"""Gather — community spaces, geographic hierarchy, message board, events, resources.

Design constraints (per user spec):
  - Cost contained: pure MongoDB, no real-time chat, no paid geocoder.
  - Hybrid hierarchy: continents + countries + major US/CA/UK regions are
    pre-seeded; cities/neighborhoods are proposed by Stewards and approved by
    admins. No depth limit beyond neighborhood for now.
  - Steward role does moderation; community sales (if any) flow through existing
    referral/rev-share plumbing (foundation receives standard cut).

Collections introduced:
  communities          {id, slug (hierarchical path), label, parent_slug, kind,
                        country_code, lat, lng, status, steward_user_ids[],
                        welcome_text, post_count, event_count, member_count,
                        created_at, updated_at, created_by, approved_by, approved_at}
  community_proposals  {id, slug, label, parent_slug, kind, lat, lng,
                        proposed_by, note, status, created_at, decided_at}
  community_members    {id, community_slug, user_id, joined_at, role}
  community_posts      {id, community_slug, author_id, author_name, body,
                        parent_id, pinned, hidden, created_at, updated_at}
  community_events     {id, community_slug, title, description, start_at,
                        end_at, location_name, location_url, host_id, created_at}
  community_resources  {id, community_slug, title, kind, url, body, pinned,
                        created_by, created_at}

`kind` field on communities: continent | country | region | city | neighborhood.
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Literal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user, require_roles, get_current_user_optional
from models import gen_id, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.gather")
router = APIRouter(prefix="/gather", tags=["gather"])
admin_router = APIRouter(prefix="/admin/gather", tags=["admin-gather"])

COMMUNITY_KINDS = ("continent", "country", "region", "city", "neighborhood")


# ============ Models ============
class CommunityProposal(BaseModel):
    label: str = Field(min_length=2, max_length=160)
    parent_slug: str = Field(min_length=2, max_length=200,
                              description="Slug of the parent community (e.g. north-america/us/california)")
    kind: Literal["city", "neighborhood"]
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    note: Optional[str] = Field(default="", max_length=2000)


class CommunityUpdate(BaseModel):
    welcome_text: Optional[str] = Field(default=None, max_length=4000)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)


class CommunityPostCreate(BaseModel):
    body: str = Field(min_length=2, max_length=8000)
    parent_id: Optional[str] = Field(default=None, max_length=120)


class CommunityEventCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: Optional[str] = Field(default="", max_length=4000)
    start_at: str  # ISO datetime
    end_at: Optional[str] = None
    location_name: Optional[str] = Field(default="", max_length=400)
    location_url: Optional[str] = Field(default=None, max_length=600)
    is_virtual: bool = False


class CommunityResourceCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    kind: Literal["link", "note"] = "link"
    url: Optional[str] = Field(default=None, max_length=600)
    body: Optional[str] = Field(default="", max_length=8000)
    pinned: bool = False


class StewardAssign(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)


# ============ Helpers ============
def _slugify_part(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "x"


async def _get_community(db, slug: str) -> dict:
    c = await db.communities.find_one({"slug": slug}, {"_id": 0})
    if not c:
        raise HTTPException(404, f"Community '{slug}' not found")
    return c


async def _require_steward_or_admin(db, user: dict, community: dict) -> str:
    """Returns 'admin' | 'steward' or raises 403."""
    if user.get("role") == "admin":
        return "admin"
    if user["id"] in (community.get("steward_user_ids") or []):
        return "steward"
    raise HTTPException(403, "Only stewards or admins can do that here")


async def _increment(db, slug: str, field: str, delta: int = 1) -> None:
    await db.communities.update_one(
        {"slug": slug}, {"$inc": {field: delta}, "$set": {"updated_at": now_iso()}},
    )


# ============ Public hierarchy ============
@router.get("/tree")
async def get_tree(
    parent_slug: Optional[str] = None,
    depth: int = Query(1, ge=1, le=4),
):
    """Return the children of a parent community (default: continents).

    Used by the Gather landing drill-down. Frontend pages through this 1-2 deep
    at a time rather than fetching the whole world.
    """
    from database import db
    query = {"status": "active"}
    if parent_slug:
        query["parent_slug"] = parent_slug
    else:
        query["kind"] = "continent"
    nodes = await db.communities.find(
        query, {"_id": 0, "welcome_text": 0},
    ).sort([("kind", 1), ("label", 1)]).to_list(500)
    return nodes


@router.get("/community/{slug:path}")
async def get_community(slug: str, user: Optional[dict] = Depends(get_current_user_optional)):
    """Get a community's metadata + a slice of recent activity."""
    from database import db
    c = await _get_community(db, slug)
    posts = await db.community_posts.find(
        {"community_slug": slug, "parent_id": None, "hidden": {"$ne": True}},
        {"_id": 0},
    ).sort([("pinned", -1), ("created_at", -1)]).limit(20).to_list(20)
    events = await db.community_events.find(
        {"community_slug": slug, "start_at": {"$gte": now_iso()[:10]}},
        {"_id": 0},
    ).sort("start_at", 1).limit(10).to_list(10)
    resources = await db.community_resources.find(
        {"community_slug": slug}, {"_id": 0},
    ).sort([("pinned", -1), ("created_at", -1)]).limit(20).to_list(20)
    is_member = False
    if user:
        is_member = bool(await db.community_members.find_one(
            {"community_slug": slug, "user_id": user["id"]}, {"_id": 0, "id": 1},
        ))
    stewards = []
    if c.get("steward_user_ids"):
        users = await db.users.find(
            {"id": {"$in": c["steward_user_ids"]}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "avatar_url": 1},
        ).to_list(10)
        stewards = [
            {"id": u["id"], "name": f"{u.get('first_name','')} {u.get('last_name','')}".strip(),
             "avatar_url": u.get("avatar_url")}
            for u in users
        ]
    return {
        "community": c,
        "posts": posts,
        "events": events,
        "resources": resources,
        "stewards": stewards,
        "is_member": is_member,
        "viewer_is_steward": bool(user and user["id"] in (c.get("steward_user_ids") or [])),
        "viewer_is_admin": bool(user and user.get("role") == "admin"),
    }


@router.get("/search")
async def search_communities(q: str = Query(min_length=2, max_length=80), limit: int = Query(20, ge=1, le=50)):
    """Free-text search across community labels + parent paths."""
    from database import db
    rx = re.escape(q.strip())
    nodes = await db.communities.find(
        {"status": "active", "label": {"$regex": rx, "$options": "i"}},
        {"_id": 0, "slug": 1, "label": 1, "kind": 1, "parent_slug": 1, "member_count": 1},
    ).limit(limit).to_list(limit)
    return nodes


# ============ Membership ============
@router.post("/community/{slug:path}/join")
async def join_community(slug: str, user: dict = Depends(get_current_user)):
    from database import db
    await _get_community(db, slug)
    existing = await db.community_members.find_one({"community_slug": slug, "user_id": user["id"]})
    if existing:
        return {"ok": True, "already_member": True}
    await db.community_members.insert_one({
        "id": gen_id(),
        "community_slug": slug,
        "user_id": user["id"],
        "joined_at": now_iso(),
        "role": "member",
    })
    await _increment(db, slug, "member_count", 1)
    return {"ok": True, "already_member": False}


@router.post("/community/{slug:path}/leave")
async def leave_community(slug: str, user: dict = Depends(get_current_user)):
    from database import db
    r = await db.community_members.delete_one({"community_slug": slug, "user_id": user["id"]})
    if r.deleted_count:
        await _increment(db, slug, "member_count", -1)
    return {"ok": True, "left": bool(r.deleted_count)}


# ============ Posts ============
@router.post("/community/{slug:path}/posts")
async def create_post(slug: str, data: CommunityPostCreate, user: dict = Depends(get_current_user)):
    from database import db
    c = await _get_community(db, slug)
    if c["status"] != "active":
        raise HTTPException(400, "Community is not active")
    if data.parent_id:
        parent = await db.community_posts.find_one({"id": data.parent_id, "community_slug": slug})
        if not parent:
            raise HTTPException(400, "Parent post not found in this community")
    doc = {
        "id": gen_id(),
        "community_slug": slug,
        "author_id": user["id"],
        "author_name": f"{user.get('first_name','')} {user.get('last_name','')}".strip() or "member",
        "author_role": user.get("role", "member"),
        "body": data.body.strip(),
        "parent_id": data.parent_id,
        "pinned": False,
        "hidden": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.community_posts.insert_one(dict(doc))
    if not data.parent_id:
        await _increment(db, slug, "post_count", 1)
    doc.pop("_id", None)
    return doc


@router.get("/community/{slug:path}/posts/{post_id}")
async def get_post_thread(slug: str, post_id: str):
    """Return a root post + replies."""
    from database import db
    root = await db.community_posts.find_one(
        {"id": post_id, "community_slug": slug, "hidden": {"$ne": True}}, {"_id": 0},
    )
    if not root:
        raise HTTPException(404, "Post not found")
    replies = await db.community_posts.find(
        {"parent_id": post_id, "hidden": {"$ne": True}}, {"_id": 0},
    ).sort("created_at", 1).to_list(200)
    return {"post": root, "replies": replies}


@router.post("/community/{slug:path}/posts/{post_id}/pin")
async def pin_post(slug: str, post_id: str, pinned: bool = True, user: dict = Depends(get_current_user)):
    from database import db
    c = await _get_community(db, slug)
    await _require_steward_or_admin(db, user, c)
    await db.community_posts.update_one(
        {"id": post_id, "community_slug": slug}, {"$set": {"pinned": pinned}},
    )
    return {"ok": True, "pinned": pinned}


@router.post("/community/{slug:path}/posts/{post_id}/hide")
async def hide_post(slug: str, post_id: str, user: dict = Depends(get_current_user)):
    from database import db
    c = await _get_community(db, slug)
    actor = await _require_steward_or_admin(db, user, c)
    await db.community_posts.update_one(
        {"id": post_id, "community_slug": slug},
        {"$set": {"hidden": True, "hidden_by": user["id"], "hidden_role": actor}},
    )
    return {"ok": True}


# ============ Events ============
@router.post("/community/{slug:path}/events")
async def create_event(slug: str, data: CommunityEventCreate, user: dict = Depends(get_current_user)):
    from database import db
    c = await _get_community(db, slug)
    # Anyone can propose; stewards moderate. v1 = direct create, future = drafts.
    await _require_steward_or_admin(db, user, c)
    doc = {
        "id": gen_id(),
        "community_slug": slug,
        "title": data.title.strip(),
        "description": (data.description or "").strip(),
        "start_at": data.start_at,
        "end_at": data.end_at,
        "location_name": data.location_name,
        "location_url": data.location_url,
        "is_virtual": data.is_virtual,
        "host_id": user["id"],
        "created_at": now_iso(),
    }
    await db.community_events.insert_one(dict(doc))
    await _increment(db, slug, "event_count", 1)
    doc.pop("_id", None)
    return doc


@router.delete("/community/{slug:path}/events/{event_id}")
async def delete_event(slug: str, event_id: str, user: dict = Depends(get_current_user)):
    from database import db
    c = await _get_community(db, slug)
    await _require_steward_or_admin(db, user, c)
    r = await db.community_events.delete_one({"id": event_id, "community_slug": slug})
    if r.deleted_count:
        await _increment(db, slug, "event_count", -1)
    return {"ok": True, "deleted": bool(r.deleted_count)}


# ============ Resources ============
@router.post("/community/{slug:path}/resources")
async def create_resource(slug: str, data: CommunityResourceCreate, user: dict = Depends(get_current_user)):
    from database import db
    c = await _get_community(db, slug)
    await _require_steward_or_admin(db, user, c)
    doc = {
        "id": gen_id(),
        "community_slug": slug,
        "title": data.title.strip(),
        "kind": data.kind,
        "url": data.url,
        "body": (data.body or "").strip(),
        "pinned": data.pinned,
        "created_by": user["id"],
        "created_at": now_iso(),
    }
    await db.community_resources.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.delete("/community/{slug:path}/resources/{rid}")
async def delete_resource(slug: str, rid: str, user: dict = Depends(get_current_user)):
    from database import db
    c = await _get_community(db, slug)
    await _require_steward_or_admin(db, user, c)
    r = await db.community_resources.delete_one({"id": rid, "community_slug": slug})
    return {"ok": True, "deleted": bool(r.deleted_count)}


# ============ Steward-level community editing ============
@router.put("/community/{slug:path}")
async def update_community(slug: str, data: CommunityUpdate, user: dict = Depends(get_current_user)):
    from database import db
    c = await _get_community(db, slug)
    await _require_steward_or_admin(db, user, c)
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(400, "Nothing to update")
    updates["updated_at"] = now_iso()
    await db.communities.update_one({"slug": slug}, {"$set": updates})
    return await _get_community(db, slug)


# ============ Proposing a new community ============
@router.post("/propose")
async def propose_community(data: CommunityProposal, user: dict = Depends(get_current_user)):
    """Anyone (signed in) can propose a new city/neighborhood; admin approves."""
    from database import db
    parent = await db.communities.find_one({"slug": data.parent_slug}, {"_id": 0, "slug": 1, "kind": 1})
    if not parent:
        raise HTTPException(400, f"Parent '{data.parent_slug}' not found")
    if data.kind == "city" and parent["kind"] not in ("country", "region"):
        raise HTTPException(400, "A city must be proposed under a country or region")
    if data.kind == "neighborhood" and parent["kind"] != "city":
        raise HTTPException(400, "A neighborhood must be proposed under a city")
    new_slug = f"{data.parent_slug}/{_slugify_part(data.label)}"
    if await db.communities.find_one({"slug": new_slug}, {"_id": 0, "slug": 1}):
        raise HTTPException(400, f"'{new_slug}' already exists")
    if await db.community_proposals.find_one({"slug": new_slug, "status": "pending"}, {"_id": 0, "slug": 1}):
        raise HTTPException(400, f"There's already a pending proposal for '{new_slug}'")
    doc = {
        "id": gen_id(),
        "slug": new_slug,
        "label": data.label.strip(),
        "parent_slug": data.parent_slug,
        "kind": data.kind,
        "lat": data.lat,
        "lng": data.lng,
        "proposed_by": user["id"],
        "note": (data.note or "").strip(),
        "status": "pending",
        "created_at": now_iso(),
    }
    await db.community_proposals.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


# ============ Admin ============
@admin_router.get("/proposals")
async def list_proposals(status: Optional[str] = "pending", user: dict = Depends(require_roles("admin"))):
    from database import db
    query = {}
    if status:
        query["status"] = status
    rows = await db.community_proposals.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return rows


@admin_router.post("/proposals/{pid}/approve")
async def approve_proposal(pid: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    p = await db.community_proposals.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Proposal not found")
    if p["status"] != "pending":
        raise HTTPException(400, f"Proposal already {p['status']}")
    now = now_iso()
    community = {
        "id": gen_id(),
        "slug": p["slug"],
        "label": p["label"],
        "parent_slug": p["parent_slug"],
        "kind": p["kind"],
        "lat": p.get("lat"),
        "lng": p.get("lng"),
        "status": "active",
        "steward_user_ids": [],
        "welcome_text": "",
        "post_count": 0,
        "event_count": 0,
        "member_count": 0,
        "created_at": now,
        "updated_at": now,
        "created_by": p.get("proposed_by"),
        "approved_by": user["id"],
        "approved_at": now,
    }
    await db.communities.insert_one(dict(community))
    await db.community_proposals.update_one(
        {"id": pid}, {"$set": {"status": "approved", "decided_at": now, "decided_by": user["id"]}},
    )
    await log_action(
        db, user, "gather.community.approve",
        target_type="community", target_id=p["slug"],
        metadata={"label": p["label"], "kind": p["kind"]},
    )
    community.pop("_id", None)
    return community


@admin_router.post("/proposals/{pid}/reject")
async def reject_proposal(pid: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    p = await db.community_proposals.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Proposal not found")
    if p["status"] != "pending":
        raise HTTPException(400, f"Proposal already {p['status']}")
    await db.community_proposals.update_one(
        {"id": pid}, {"$set": {"status": "rejected", "decided_at": now_iso(), "decided_by": user["id"]}},
    )
    return {"ok": True}


@admin_router.post("/community/{slug:path}/stewards")
async def assign_steward(slug: str, data: StewardAssign, user: dict = Depends(require_roles("admin"))):
    """Add a user as a steward of this community. Up to 2 stewards per node."""
    from database import db
    c = await _get_community(db, slug)
    existing = list(c.get("steward_user_ids") or [])
    if data.user_id in existing:
        return c
    if len(existing) >= 2:
        raise HTTPException(400, "Max 2 stewards per community")
    target = await db.users.find_one({"id": data.user_id}, {"_id": 0, "id": 1})
    if not target:
        raise HTTPException(404, "User not found")
    existing.append(data.user_id)
    await db.communities.update_one(
        {"slug": slug}, {"$set": {"steward_user_ids": existing, "updated_at": now_iso()}},
    )
    await log_action(
        db, user, "gather.steward.assign",
        target_type="community", target_id=slug, metadata={"steward_user_id": data.user_id},
    )
    return await _get_community(db, slug)


@admin_router.delete("/community/{slug:path}/stewards/{uid}")
async def remove_steward(slug: str, uid: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    c = await _get_community(db, slug)
    new_ids = [x for x in (c.get("steward_user_ids") or []) if x != uid]
    await db.communities.update_one(
        {"slug": slug}, {"$set": {"steward_user_ids": new_ids, "updated_at": now_iso()}},
    )
    await log_action(
        db, user, "gather.steward.remove",
        target_type="community", target_id=slug, metadata={"steward_user_id": uid},
    )
    return await _get_community(db, slug)
