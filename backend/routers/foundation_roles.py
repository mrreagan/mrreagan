"""Foundation Roles — Phase 6B.4.5b.

Open foundation-board seats advertised on `/join-us`, plus an applications
collection where prospects submit their interest. Admins triage from
`/admin/foundation-applications`.

Schema:
  foundation_roles  {id, slug, title, headline, who_you_are, what_youll_do,
                     what_you_bring, time_commitment, compensation_summary,
                     order, open, seeded_member_id, created_at, updated_at}
  foundation_role_applications {id, role_slug, role_id, name, email,
                                current_role, why_drawn, resume_url,
                                linkedin_url, phone, status, admin_note,
                                created_at, decided_at, decided_by}
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import require_roles
from models import (
    FoundationRoleApplicationDecision,
    FoundationRoleApplicationSubmit,
    FoundationRoleCreate,
    FoundationRoleUpdate,
    gen_id,
    now_iso,
)
from utils.audit import log_action

logger = logging.getLogger("birthright.foundation_roles")

public_router = APIRouter(prefix="/foundation-roles", tags=["foundation-roles"])
applications_router = APIRouter(prefix="/foundation-role-applications", tags=["foundation-role-applications"])
admin_router = APIRouter(prefix="/admin/foundation-roles", tags=["admin-foundation-roles"])
admin_apps_router = APIRouter(prefix="/admin/foundation-role-applications", tags=["admin-foundation-role-applications"])


# ============ PUBLIC ============

@public_router.get("")
async def list_roles(open_only: bool = Query(True)):
    from database import db
    query: dict = {}
    if open_only:
        query["open"] = True
    roles = await db.foundation_roles.find(query, {"_id": 0}).sort([("order", 1), ("created_at", 1)]).to_list(50)
    return roles


@public_router.get("/{slug}")
async def get_role(slug: str):
    from database import db
    role = await db.foundation_roles.find_one({"slug": slug}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


# ============ APPLICANT-FACING ============

@applications_router.post("")
async def submit_application(data: FoundationRoleApplicationSubmit):
    """Anyone can submit — no auth required (we're recruiting board members)."""
    from database import db
    role = await db.foundation_roles.find_one({"slug": data.role_slug})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if not role.get("open", True):
        raise HTTPException(status_code=400, detail="This role is no longer accepting applications")

    doc = {
        "id": gen_id(),
        "role_slug": data.role_slug,
        "role_id": role["id"],
        "role_title": role["title"],
        "name": data.name.strip(),
        "email": data.email.lower().strip(),
        "current_role": (data.current_role or "").strip(),
        "why_drawn": data.why_drawn.strip(),
        "resume_url": (data.resume_url or None),
        "linkedin_url": (data.linkedin_url or None),
        "phone": (data.phone or None),
        "status": "new",  # new | reviewing | interviewing | accepted | declined | withdrawn
        "admin_note": "",
        "created_at": now_iso(),
        "decided_at": None,
        "decided_by": None,
    }
    await db.foundation_role_applications.insert_one(dict(doc))
    doc.pop("_id", None)

    # Best-effort confirmation email (dry-run friendly)
    try:
        from utils.mailer import send_email
        await send_email(
            to=data.email,
            subject=f"Thanks for applying to Birthright Foundation — {role['title']}",
            html=f"""
                <p>Hi {data.name.split(' ')[0]},</p>
                <p>Thanks for putting your name forward for the <strong>{role['title']}</strong> role
                with the Birthright Foundation. We've received your application and a member of the
                governing board will be in touch within two weeks.</p>
                <p>With gratitude,<br/>The Birthright Foundation</p>
            """,
            template_name="foundation_role_application_ack",
            metadata={"application_id": doc["id"], "role_slug": data.role_slug},
        )
    except Exception as e:
        logger.error(f"foundation role ack email failed: {e}")

    return {"id": doc["id"], "status": doc["status"], "role_slug": doc["role_slug"]}


# ============ ADMIN: ROLES CRUD ============

@admin_router.get("")
async def admin_list_roles(user: dict = Depends(require_roles("admin"))):
    from database import db
    return await db.foundation_roles.find({}, {"_id": 0}).sort([("order", 1), ("created_at", 1)]).to_list(100)


@admin_router.post("")
async def admin_create_role(data: FoundationRoleCreate, user: dict = Depends(require_roles("admin"))):
    from database import db
    if await db.foundation_roles.find_one({"slug": data.slug}):
        raise HTTPException(status_code=400, detail="Slug already exists")
    now = now_iso()
    doc = {**data.model_dump(), "id": gen_id(), "created_at": now, "updated_at": now}
    await db.foundation_roles.insert_one(dict(doc))
    await log_action(db, user, "foundation_role.create", target_type="foundation_role", target_id=doc["id"],
                     metadata={"slug": doc["slug"], "title": doc["title"]})
    doc.pop("_id", None)
    return doc


@admin_router.put("/{slug}")
async def admin_update_role(slug: str, data: FoundationRoleUpdate, user: dict = Depends(require_roles("admin"))):
    from database import db
    role = await db.foundation_roles.find_one({"slug": slug})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updates["updated_at"] = now_iso()
    await db.foundation_roles.update_one({"id": role["id"]}, {"$set": updates})
    await log_action(db, user, "foundation_role.update", target_type="foundation_role", target_id=role["id"],
                     metadata={"slug": slug, "fields": list(updates.keys())})
    out = await db.foundation_roles.find_one({"id": role["id"]}, {"_id": 0})
    return out


@admin_router.delete("/{slug}")
async def admin_delete_role(slug: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    role = await db.foundation_roles.find_one({"slug": slug})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    await db.foundation_roles.delete_one({"id": role["id"]})
    await log_action(db, user, "foundation_role.delete", target_type="foundation_role", target_id=role["id"],
                     metadata={"slug": slug})
    return {"deleted": True, "slug": slug}


# ============ ADMIN: APPLICATIONS QUEUE ============

_VALID_STATUSES = ("new", "reviewing", "interviewing", "accepted", "declined", "withdrawn")


@admin_apps_router.get("")
async def admin_list_applications(
    status: Optional[str] = None,
    role_slug: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    if role_slug:
        query["role_slug"] = role_slug
    apps = await db.foundation_role_applications.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return apps


@admin_apps_router.post("/{app_id}/decision")
async def admin_decide(
    app_id: str,
    status: str,
    data: FoundationRoleApplicationDecision,
    user: dict = Depends(require_roles("admin")),
):
    """Set application status. `status` must be one of the valid statuses."""
    if status not in _VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {_VALID_STATUSES}")
    from database import db
    app = await db.foundation_role_applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    decided = status in ("accepted", "declined", "withdrawn")
    update = {
        "status": status,
        "admin_note": (data.admin_note or "").strip(),
    }
    if decided:
        update["decided_at"] = now_iso()
        update["decided_by"] = user["id"]
    await db.foundation_role_applications.update_one({"id": app_id}, {"$set": update})
    await log_action(db, user, "foundation_role_application.decision",
                     target_type="foundation_role_application", target_id=app_id,
                     metadata={"status": status, "role_slug": app.get("role_slug")})
    updated = await db.foundation_role_applications.find_one({"id": app_id}, {"_id": 0})
    return updated
