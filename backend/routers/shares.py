"""Universal Share & Save System — v1.11.0 Step 8.5.

Three concerns in one router:

  1. **Share event logging** — `POST /api/shares/log` accepts anon or
     authenticated events. When a page loads with `?via=<token>` we call
     this; when a share button is clicked we also call this. If `via`
     resolves to a community partner's referral code we set the
     `birthright_ref` cookie so any subsequent Stripe checkout in the
     same session credits the partner.

  2. **Polymorphic bookmarks** — auth-only. `GET/POST/DELETE /api/me/bookmarks`.

  3. **My referral / via slug** — `GET /api/me/share-token` returns the
     token a logged-in user should append to share URLs:
       * if they have an active community PartnerProfile → their `referral_code`
       * otherwise → their user id (still trackable, not paid)
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from auth_utils import get_current_user, get_current_user_optional
from models import BookmarkCreate, ShareLogCreate, gen_id, now_iso
from routers.referrals import REFERRAL_COOKIE, REFERRAL_COOKIE_MAX_AGE

logger = logging.getLogger("birthright.shares")

public_router = APIRouter(prefix="/shares", tags=["shares"])
my_router = APIRouter(prefix="/me", tags=["shares-me"])


# ============ SHARE EVENT LOGGING ============

@public_router.post("/log")
async def log_share(
    data: ShareLogCreate,
    request: Request,
    response: Response,
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Anon-friendly. Logs share click. If `via` matches an active
    community-partner referral_code, sets birthright_ref cookie for
    later checkout attribution."""
    from database import db

    via_resolved = None
    if data.via:
        candidate = data.via.strip().upper()
        profile = await db.partner_profiles.find_one(
            {"referral_code": candidate, "status": "active"}, {"_id": 0}
        )
        if profile and profile.get("partner_type") == "community":
            via_resolved = {
                "referral_code": candidate,
                "partner_profile_id": profile["id"],
                "partner_user_id": profile["user_id"],
            }
            response.set_cookie(
                key=REFERRAL_COOKIE,
                value=candidate,
                max_age=REFERRAL_COOKIE_MAX_AGE,
                httponly=False,
                samesite="lax",
                secure=True,
            )

    doc = {
        "id": gen_id(),
        "surface": data.surface,
        "surface_id": data.surface_id,
        "channel": data.channel,
        "via": data.via,
        "via_resolved": via_resolved,
        "path": data.path,
        "session_id": data.session_id,
        "user_id": (user or {}).get("id"),
        "user_agent": request.headers.get("user-agent", "")[:300],
        "referrer": request.headers.get("referer", "")[:600],
        "created_at": now_iso(),
    }
    await db.share_events.insert_one(dict(doc))
    return {"logged": True, "attribution_set": bool(via_resolved)}


# ============ MY SHARE TOKEN ============

@my_router.get("/share-token")
async def my_share_token(user: dict = Depends(get_current_user)):
    """Returns the token the caller should append as `?via=` on share URLs.

    Community partners get their referral_code (eligible for payout).
    All other users get their user id (analytics only; no payout)."""
    from database import db
    community = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": "community", "status": "active"}
    )
    if community:
        code = community.get("referral_code")
        if code:
            return {"via": code, "kind": "community_referral", "pays_out": True}
    return {"via": user["id"], "kind": "user_id", "pays_out": False}


# ============ BOOKMARKS ============

@my_router.get("/bookmarks")
async def list_my_bookmarks(
    subject_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    from database import db
    query: dict = {"user_id": user["id"]}
    if subject_type:
        query["subject_type"] = subject_type
    rows = await db.bookmarks.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return rows


@my_router.post("/bookmarks")
async def create_bookmark(data: BookmarkCreate, user: dict = Depends(get_current_user)):
    from database import db
    existing = await db.bookmarks.find_one(
        {"user_id": user["id"], "subject_type": data.subject_type, "subject_id": data.subject_id}
    )
    if existing:
        # idempotent: update label/note if provided
        updates: dict = {}
        if data.label is not None:
            updates["label"] = data.label
        if data.note is not None:
            updates["note"] = data.note
        if updates:
            updates["updated_at"] = now_iso()
            await db.bookmarks.update_one({"id": existing["id"]}, {"$set": updates})
        out = await db.bookmarks.find_one({"id": existing["id"]}, {"_id": 0})
        return out
    doc = {
        "id": gen_id(),
        "user_id": user["id"],
        "subject_type": data.subject_type,
        "subject_id": data.subject_id,
        "label": data.label,
        "note": data.note,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.bookmarks.insert_one(dict(doc))
    return doc


@my_router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: str, user: dict = Depends(get_current_user)):
    from database import db
    res = await db.bookmarks.delete_one({"id": bookmark_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"deleted": True, "id": bookmark_id}
