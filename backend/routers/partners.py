"""Partner foundation: applications, profiles, public directory, admin queue.

This is the gateway layer for Phase 6B. Subsequent sub-phases (subscriptions,
referrals, vendor catalog, research) all attach to `PartnerProfile`.

Schema:
  partner_applications  {id, user_id|invitee_email, invited_by_admin_id|None,
                         partner_type, status, data{...}, admin_note,
                         created_at, decided_at, decided_by}
  partner_profiles      {id, user_id, partner_type, status, public, slug,
                         headline, bio, website_url, location, photo_url,
                         meta{...}, approved_at, approved_by,
                         created_at, updated_at}

Rules:
  - One PROFILE per (user_id, partner_type). A user can be approved for
    multiple types (e.g. facilitator + research).
  - One PENDING application per (user_id, partner_type) at a time.
  - Approving creates/refreshes the profile. Rejecting just records the
    decision.
  - Revoking flips profile.status='revoked' but keeps the row for audit.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user, require_roles
from models import (
    PartnerApplicationDecision,
    PartnerApplyData,
    PartnerInviteCreate,
    PartnerProfileUpdate,
    gen_id,
    now_iso,
)
from utils.audit import log_action

logger = logging.getLogger("birthright.partners")
router = APIRouter(prefix="/partners", tags=["partners"])
admin_router = APIRouter(prefix="/admin/partners", tags=["admin-partners"])


# ============ HELPERS ============

PARTNER_TYPE_VALUES = ("facilitator", "community", "research", "vendor")

# Fields that get persisted into application.data (everything except partner_type)
_APP_DATA_FIELDS = (
    "headline", "bio", "website_url", "location",
    "presents_birthright_ip", "credentials", "training_history", "sample_curriculum_url",
    "organization", "audience_size", "referral_plan",
    "institution", "area_of_research", "sample_publications_url",
    "business_name", "product_categories",
    "apply_as_founding_partner",
)


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:80] or "partner"


async def _unique_slug(db, base: str, exclude_id: Optional[str] = None) -> str:
    slug = base
    i = 1
    while True:
        existing = await db.partner_profiles.find_one({"slug": slug})
        if not existing or existing.get("id") == exclude_id:
            return slug
        i += 1
        slug = f"{base}-{i}"


async def _enrich_app(db, app: dict) -> dict:
    """Add applicant_email + applicant_name to an application row for display."""
    if app.get("user_id"):
        u = await db.users.find_one({"id": app["user_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            app["applicant_email"] = u.get("email")
            app["applicant_name"] = f"{u.get('first_name','')} {u.get('last_name','')}".strip()
    else:
        app["applicant_email"] = app.get("invitee_email")
        app["applicant_name"] = None
    return app


# ============ APPLICANT-FACING ROUTES ============

async def _validate_apply(db, user: dict, data: PartnerApplyData) -> None:
    """Raise HTTPException if this user cannot file a new application of this type.

    Three rules:
      1. No active profile of the same type already.
      2. No pending application of the same type already.
      3. Facilitators MUST declare Birthright IP intent.
    """
    existing_profile = await db.partner_profiles.find_one({
        "user_id": user["id"], "partner_type": data.partner_type, "status": "active",
    })
    if existing_profile:
        raise HTTPException(
            status_code=400,
            detail=f"You already have an active {data.partner_type} partner profile.",
        )
    pending = await db.partner_applications.find_one({
        "user_id": user["id"], "partner_type": data.partner_type, "status": "pending",
    })
    if pending:
        raise HTTPException(
            status_code=400,
            detail=f"You already have a pending {data.partner_type} application.",
        )
    if data.partner_type == "facilitator" and data.presents_birthright_ip is None:
        raise HTTPException(
            status_code=400,
            detail="Please indicate whether you intend to present Birthright IP materials.",
        )


def _build_application_doc(user: dict, data: PartnerApplyData) -> dict:
    payload = data.model_dump()
    return {
        "id": gen_id(),
        "user_id": user["id"],
        "invitee_email": None,
        "invited_by_admin_id": None,
        "partner_type": data.partner_type,
        "status": "pending",
        "data": {k: payload.get(k) for k in _APP_DATA_FIELDS if payload.get(k) is not None},
        "admin_note": "",
        "created_at": now_iso(),
        "decided_at": None,
        "decided_by": None,
    }


@router.post("/apply")
async def apply(data: PartnerApplyData, user: dict = Depends(get_current_user)):
    """Self-serve application. Caller picks partner_type via the payload."""
    from database import db
    await _validate_apply(db, user, data)
    app_doc = _build_application_doc(user, data)
    await db.partner_applications.insert_one(dict(app_doc))
    await log_action(
        db, user, "partner.application.create",
        target_type="partner_application", target_id=app_doc["id"],
        metadata={"partner_type": data.partner_type},
    )
    app_doc.pop("_id", None)
    return app_doc



@router.get("/my-applications")
async def my_applications(user: dict = Depends(get_current_user)):
    from database import db
    apps = await db.partner_applications.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return apps


@router.get("/my-profiles")
async def my_profiles(user: dict = Depends(get_current_user)):
    from database import db
    profiles = await db.partner_profiles.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("partner_type", 1).to_list(20)
    return profiles


@router.get("/my-rev-share/{partner_type}")
async def my_rev_share(
    partner_type: str,
    presents_birthright_ip: bool = False,
    user: dict = Depends(get_current_user),
):
    """Show the caller their applicable rev-share rate for a partner_type.

    For facilitators, pass `presents_birthright_ip=true` to see the Birthright-IP
    tier; false (default) to see the rate for own/vendor content.
    """
    if partner_type not in PARTNER_TYPE_VALUES:
        raise HTTPException(status_code=400, detail="Invalid partner_type")
    from database import db
    from utils.rev_share import resolve_rev_share
    return await resolve_rev_share(
        db, user["id"], partner_type, presents_birthright_ip=presents_birthright_ip
    )


@router.put("/my-profiles/{partner_type}")
async def update_my_profile(
    partner_type: str,
    data: PartnerProfileUpdate,
    user: dict = Depends(get_current_user),
):
    if partner_type not in PARTNER_TYPE_VALUES:
        raise HTTPException(status_code=400, detail="Invalid partner_type")
    from database import db
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": partner_type}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="No partner profile of that type")
    if profile["status"] == "revoked":
        raise HTTPException(status_code=403, detail="Profile is revoked")

    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    updates["updated_at"] = now_iso()
    await db.partner_profiles.update_one({"id": profile["id"]}, {"$set": updates})
    await log_action(
        db, user, "partner.profile.update",
        target_type="partner_profile", target_id=profile["id"],
        metadata={"fields": list(updates.keys()), "partner_type": partner_type},
    )
    out = await db.partner_profiles.find_one({"id": profile["id"]}, {"_id": 0})
    return out


# ============ PUBLIC DIRECTORY ============

@router.get("")
async def list_public_partners(
    partner_type: Optional[str] = None,
    q: Optional[str] = None,
    samples: int = Query(0, ge=0, le=1),
    limit: int = Query(60, ge=1, le=200),
):
    """Public partner directory. Only `status=active` and `public=true` rows.
    By default excludes sample personas. Pass `samples=1` to return ONLY samples."""
    from database import db
    query: dict = {"status": "active", "public": True}
    if samples == 1:
        query["is_sample"] = True
    else:
        query["$or"] = [{"is_sample": {"$ne": True}}, {"is_sample": {"$exists": False}}]
    if partner_type:
        if partner_type not in PARTNER_TYPE_VALUES:
            raise HTTPException(status_code=400, detail="Invalid partner_type")
        query["partner_type"] = partner_type
    if q and len(q.strip()) >= 2:
        rx = re.escape(q.strip())
        # Combine with existing $or if present
        text_or = [
            {"headline": {"$regex": rx, "$options": "i"}},
            {"bio": {"$regex": rx, "$options": "i"}},
            {"location": {"$regex": rx, "$options": "i"}},
            {"display_name": {"$regex": rx, "$options": "i"}},
        ]
        if "$or" in query:
            query = {"$and": [{"$or": query.pop("$or")}, {"$or": text_or}, query]}
        else:
            query["$or"] = text_or
    profiles = await db.partner_profiles.find(
        query, {"_id": 0, "meta": 0}
    ).sort("approved_at", -1).to_list(limit)
    # Pin currently-featured partners to the top (within the active filter).
    from datetime import datetime, timezone
    now_iso_str = datetime.now(timezone.utc).isoformat()
    featured, rest = [], []
    for p in profiles:
        if p.get("featured_until") and p["featured_until"] > now_iso_str:
            featured.append(p)
        else:
            rest.append(p)
    featured.sort(key=lambda p: p.get("featured_until") or "", reverse=True)
    return featured + rest


@router.get("/{slug}")
async def get_public_partner(slug: str):
    from database import db
    profile = await db.partner_profiles.find_one(
        {"slug": slug, "status": "active", "public": True}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Partner not found")
    return profile


# ============ ADMIN ROUTES ============

@admin_router.get("/applications")
async def list_applications(
    status: Optional[str] = None,
    partner_type: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    if partner_type:
        query["partner_type"] = partner_type
    apps = await db.partner_applications.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    enriched = [await _enrich_app(db, a) for a in apps]
    return enriched


@admin_router.post("/invite")
async def invite_partner(data: PartnerInviteCreate, user: dict = Depends(require_roles("admin"))):
    """Admin creates a pre-filled pending application. Sends an invitation email
    (currently dry-run via the existing mailer); user can finalize on /partners/apply."""
    from database import db
    # If the invitee email already maps to a registered user, attach to their id.
    target_user = await db.users.find_one({"email": data.email.lower().strip()}, {"_id": 0, "password_hash": 0})
    app_doc = {
        "id": gen_id(),
        "user_id": target_user["id"] if target_user else None,
        "invitee_email": data.email.lower().strip(),
        "invited_by_admin_id": user["id"],
        "partner_type": data.partner_type,
        "status": "pending",
        "data": {},
        "admin_note": (data.admin_note or "").strip(),
        "created_at": now_iso(),
        "decided_at": None,
        "decided_by": None,
    }
    await db.partner_applications.insert_one(dict(app_doc))
    await log_action(
        db, user, "partner.application.invite",
        target_type="partner_application", target_id=app_doc["id"],
        metadata={"partner_type": data.partner_type, "invitee_email": data.email},
    )
    # Best-effort invite email (dry-run handles it). Don't import at top-level
    # to avoid circular concerns.
    try:
        from utils.mailer import send_email
        subject = f"You're invited to apply as a Birthright {data.partner_type.title()} partner"
        body_html = f"""
            <p>You've been invited by a Birthright admin to apply as a <strong>{data.partner_type}</strong> partner.</p>
            <p>{(data.admin_note or '').strip() or 'No additional note from the admin.'}</p>
            <p>If you don't have an account yet, sign up at <a href='https://birthright.live/register'>birthright.live/register</a> with this email address. Then visit <a href='https://birthright.live/partners/apply'>birthright.live/partners/apply</a> to complete your application.</p>
        """
        await send_email(
            to=data.email, subject=subject, html=body_html,
            template_name="partner_invite",
            metadata={"application_id": app_doc["id"], "partner_type": data.partner_type},
        )
    except Exception as e:
        logger.error(f"partner invite email failed: {e}")
    app_doc.pop("_id", None)
    enriched = await _enrich_app(db, app_doc)
    return enriched


async def _load_approvable_application(db, app_id: str) -> tuple[dict, dict]:
    """Fetch + validate that an application is approvable. Returns (app, applicant)."""
    app = await db.partner_applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Application is already {app['status']}")
    if not app.get("user_id"):
        raise HTTPException(
            status_code=400,
            detail="Application has no linked user yet. Invitee must register + apply first.",
        )
    applicant = await db.users.find_one({"id": app["user_id"]}, {"_id": 0, "password_hash": 0})
    if not applicant:
        raise HTTPException(status_code=400, detail="Applicant user not found")
    return app, applicant


async def _upsert_partner_profile(db, app: dict, applicant: dict, admin_id: str) -> dict:
    """Create or refresh the (user_id, partner_type) profile from an approved application."""
    display_name = f"{applicant['first_name']} {applicant['last_name']}".strip()
    base_slug = _slugify(f"{display_name}-{app['partner_type']}")
    existing = await db.partner_profiles.find_one({
        "user_id": app["user_id"], "partner_type": app["partner_type"],
    })
    slug = existing.get("slug") if existing else await _unique_slug(db, base_slug)
    now = now_iso()
    profile_doc = {
        "id": existing.get("id") if existing else gen_id(),
        "user_id": app["user_id"],
        "partner_type": app["partner_type"],
        "status": "active",
        "public": True,
        "slug": slug,
        "display_name": display_name,
        "headline": app.get("data", {}).get("headline", ""),
        "bio": app.get("data", {}).get("bio", ""),
        "website_url": app.get("data", {}).get("website_url"),
        "location": app.get("data", {}).get("location"),
        "photo_url": applicant.get("avatar_url"),
        "meta": app.get("data", {}),
        "approved_at": now,
        "approved_by": admin_id,
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }
    if existing:
        await db.partner_profiles.update_one({"id": existing["id"]}, {"$set": profile_doc})
    else:
        await db.partner_profiles.insert_one(dict(profile_doc))
    profile_doc.pop("_id", None)
    return profile_doc


@admin_router.post("/applications/{app_id}/approve")
async def approve_application(
    app_id: str,
    data: PartnerApplicationDecision,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    app, applicant = await _load_approvable_application(db, app_id)
    profile_doc = await _upsert_partner_profile(db, app, applicant, user["id"])
    # Mint referral code for the new profile (lazy on read otherwise)
    try:
        from routers.referrals import ensure_referral_code
        await ensure_referral_code(db, profile_doc)
    except Exception as e:
        logger.error(f"referral code mint failed for {profile_doc.get('id')}: {e}")

    # Auto-grant founding-partner status if requested and cap allows
    founding_granted = False
    requested_founding = bool(app.get("data", {}).get("apply_as_founding_partner"))
    if requested_founding:
        try:
            from routers.founding import _get_cap, _taken_count, DEFAULT_GRANT_YEARS
            from datetime import datetime, timedelta, timezone
            cap = await _get_cap(db)
            taken = await _taken_count(db)
            if taken < cap:
                expires = (datetime.now(timezone.utc) + timedelta(days=DEFAULT_GRANT_YEARS * 365)).isoformat()
                await db.partner_profiles.update_one(
                    {"id": profile_doc["id"]},
                    {"$set": {"is_founding_partner": True, "founding_rate_expires_at": expires, "updated_at": now_iso()}},
                )
                founding_granted = True
        except Exception as e:
            logger.error(f"founding grant failed for {profile_doc['id']}: {e}")

    await db.partner_applications.update_one(
        {"id": app_id},
        {"$set": {
            "status": "approved",
            "decided_at": now_iso(),
            "decided_by": user["id"],
            "admin_note": (data.admin_note or "").strip(),
            "founding_granted_on_approve": founding_granted,
        }},
    )
    await log_action(
        db, user, "partner.application.approve",
        target_type="partner_application", target_id=app_id,
        metadata={"partner_type": app["partner_type"], "profile_id": profile_doc["id"], "founding_granted": founding_granted},
    )
    profile_doc = await db.partner_profiles.find_one({"id": profile_doc["id"]}, {"_id": 0, "webhook_secret": 0})
    return {"application_status": "approved", "profile": profile_doc, "founding_granted": founding_granted}


@admin_router.post("/applications/{app_id}/reject")
async def reject_application(
    app_id: str,
    data: PartnerApplicationDecision,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    app = await db.partner_applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Application is already {app['status']}")
    await db.partner_applications.update_one(
        {"id": app_id},
        {"$set": {
            "status": "rejected",
            "decided_at": now_iso(),
            "decided_by": user["id"],
            "admin_note": (data.admin_note or "").strip(),
        }},
    )
    await log_action(
        db, user, "partner.application.reject",
        target_type="partner_application", target_id=app_id,
        metadata={"partner_type": app["partner_type"]},
    )
    updated = await db.partner_applications.find_one({"id": app_id}, {"_id": 0})
    return updated


@admin_router.post("/profiles/{profile_id}/revoke")
async def revoke_profile(
    profile_id: str,
    data: PartnerApplicationDecision,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    p = await db.partner_profiles.find_one({"id": profile_id})
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.partner_profiles.update_one(
        {"id": profile_id},
        {"$set": {
            "status": "revoked",
            "public": False,
            "revoked_at": now_iso(),
            "revoked_by": user["id"],
            "revoke_reason": (data.admin_note or "").strip(),
        }},
    )
    await log_action(
        db, user, "partner.profile.revoke",
        target_type="partner_profile", target_id=profile_id,
        metadata={"partner_type": p["partner_type"], "user_id": p["user_id"]},
    )
    updated = await db.partner_profiles.find_one({"id": profile_id}, {"_id": 0})
    return updated


@admin_router.post("/profiles/{profile_id}/reinstate")
async def reinstate_profile(profile_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    p = await db.partner_profiles.find_one({"id": profile_id})
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.partner_profiles.update_one(
        {"id": profile_id},
        {"$set": {"status": "active", "public": True, "reinstated_at": now_iso()}},
    )
    await log_action(
        db, user, "partner.profile.reinstate",
        target_type="partner_profile", target_id=profile_id,
        metadata={"partner_type": p["partner_type"], "user_id": p["user_id"]},
    )
    updated = await db.partner_profiles.find_one({"id": profile_id}, {"_id": 0})
    return updated
