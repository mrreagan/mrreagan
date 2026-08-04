"""Counsel review & audit — checklist and activity log.

Two features in one router:

1. **Review checklist.**
   Counsel can mark each legal draft (plus the briefing itself) as manually
   reviewed with their initials and a timestamp. Both counsel and full admin
   can see the status. The manual checkbox is a durable record of counsel's
   sign-off; the auto column reflects whether counsel has actually opened
   the document URL, sourced from the activity log below.

2. **Counsel activity log.**
   A middleware records every request made by any `readonly_admin` user.
   Only full admins can view the log at `/api/admin/counsel-activity` — the
   counsel account cannot see its own log (protects against a hostile
   counsel account tampering with the audit trail).

Collections:
    counsel_review_status  {slug, user_id, email, manual_reviewed,
                            manual_reviewed_at, manual_initials, notes,
                            updated_at}
    counsel_activity_log   {id, user_id, email, method, path, status_code,
                            timestamp, ip, user_agent, notes}
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from auth_utils import require_roles, COOKIE_NAME, JWT_SECRET, JWT_ALG
from models import gen_id, now_iso
import jwt

logger = logging.getLogger("birthright.counsel_audit")


# ============ Discovery of reviewable documents ============
LEGAL_DOC_DIR = Path(__file__).resolve().parent.parent / "legal_docs"


def _all_reviewable_docs() -> list[dict]:
    """List every document counsel is expected to review — the briefing plus
    every draft registered in the manifest. Keeps this list in one place so
    review status stays synced with the download index."""
    docs: list[dict] = [
        {
            "slug": "counsel-briefing",
            "display_name": "Legal Briefing for Counsel",
            "category": "Briefing",
            "download_url": "/api/legal/docs/counsel-briefing-docx",
        },
    ]
    try:
        import sys
        sys.path.insert(0, str(LEGAL_DOC_DIR))
        from _manifest import DRAFT_LEGAL_DOCS  # type: ignore
    except Exception:
        DRAFT_LEGAL_DOCS = []
    for d in DRAFT_LEGAL_DOCS:
        docs.append({
            "slug": d["slug"],
            "display_name": d.get("display_name", d["slug"]),
            "category": d.get("category", "Draft"),
            "download_url": f"/api/legal/drafts/{d['slug']}",
        })
    return docs


# ============ Middleware ============
_LOG_METHODS_ALWAYS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
_LOG_SKIP_PATH_PREFIXES = (
    "/api/counsel/log-ping",   # avoid recursive logging of the log-viewer itself
    "/static/",
)


class CounselActivityLoggerMiddleware(BaseHTTPMiddleware):
    """Persists every request made by a `readonly_admin` user. Non-blocking:
    if the DB write fails we still return the response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method not in _LOG_METHODS_ALWAYS:
            return response
        path = request.url.path
        if any(path.startswith(p) for p in _LOG_SKIP_PATH_PREFIXES):
            return response

        # Only log if a JWT is present and the caller is the counsel role.
        info = _peek_user(request)
        if not info or info.get("role") != "readonly_admin":
            return response

        try:
            from database import db
            email = info.get("email")
            if not email and info.get("id"):
                u = await db.users.find_one({"id": info["id"]}, {"_id": 0, "email": 1})
                if u:
                    email = u.get("email")
            await db.counsel_activity_log.insert_one({
                "id": gen_id(),
                "user_id": info.get("id") or "",
                "email": email or "",
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent", "")[:512],
            })
        except Exception as e:
            logger.warning("counsel activity logging failed: %s", e)
        return response


def _peek_user(request: Request) -> Optional[dict]:
    token = None
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return {
            "id": payload.get("sub") or payload.get("id"),
            "email": payload.get("email"),
            "role": payload.get("role"),
        }
    except Exception:
        return None


# ============ Router ============
router = APIRouter(prefix="/counsel", tags=["counsel-review"])
admin_router = APIRouter(prefix="/admin/counsel", tags=["counsel-audit"])


class ReviewMarkPayload(BaseModel):
    reviewed: bool
    initials: Optional[str] = None
    notes: Optional[str] = None


async def _visit_summary_for(db, user_id: str) -> dict[str, dict]:
    """Aggregate visits from the activity log per document slug so the
    checklist can auto-mark items counsel has actually opened."""
    slug_visits: dict[str, dict] = {}

    async for entry in db.counsel_activity_log.find({
        "user_id": user_id,
        "status_code": {"$lt": 400},
    }):
        path = entry.get("path") or ""
        slug: str | None = None
        # Match /api/legal/drafts/{slug}
        if path.startswith("/api/legal/drafts/"):
            slug = path[len("/api/legal/drafts/"):].strip("/").split("?")[0]
        elif path.startswith("/api/legal/docs/counsel-briefing"):
            slug = "counsel-briefing"
        if not slug:
            continue
        prior = slug_visits.get(slug)
        ts = entry.get("timestamp")
        if not prior or (ts and ts > prior.get("last_visited_at", "")):
            slug_visits[slug] = {
                "visited": True,
                "last_visited_at": ts,
                "visit_count": (prior["visit_count"] + 1) if prior else 1,
            }
        else:
            prior["visit_count"] += 1
    return slug_visits


@router.get("/review-status")
async def review_status(user: dict = Depends(require_roles("admin"))):
    """Return the full review checklist with both manual and auto status.

    Accessible to admin AND readonly_admin (require_roles("admin") accepts
    readonly_admin per auth_utils). Auto status is scoped to the counsel
    user actually recorded on the row when a mark is set, but the visits
    aggregation shows all counsel users' visits so multi-counsel review
    is supported.
    """
    from database import db
    docs = _all_reviewable_docs()

    # Load ALL manual marks (counsel + any second reviewer) so admin sees the union.
    marks_by_slug: dict[str, list[dict]] = {}
    async for m in db.counsel_review_status.find({}):
        m.pop("_id", None)
        marks_by_slug.setdefault(m["slug"], []).append(m)

    # Aggregate visits across all readonly_admin users so `auto` reflects
    # any counsel account that has opened the URL.
    aggregate_visits: dict[str, dict] = {}
    async for entry in db.counsel_activity_log.find({"status_code": {"$lt": 400}}):
        path = entry.get("path") or ""
        slug: str | None = None
        if path.startswith("/api/legal/drafts/"):
            slug = path[len("/api/legal/drafts/"):].strip("/").split("?")[0]
        elif path.startswith("/api/legal/docs/counsel-briefing"):
            slug = "counsel-briefing"
        if not slug:
            continue
        cur = aggregate_visits.get(slug) or {"visit_count": 0, "last_visited_at": "", "last_visited_by": None}
        cur["visit_count"] += 1
        ts = entry.get("timestamp") or ""
        if ts > cur["last_visited_at"]:
            cur["last_visited_at"] = ts
            cur["last_visited_by"] = entry.get("email")
        aggregate_visits[slug] = cur

    out: list[dict] = []
    for d in docs:
        slug = d["slug"]
        marks = marks_by_slug.get(slug, [])
        # Manual = any reviewer has marked reviewed
        manual_reviewed = any(m.get("manual_reviewed") for m in marks)
        latest_manual = max(marks, key=lambda m: m.get("updated_at", "")) if marks else None
        auto = aggregate_visits.get(slug) or {"visit_count": 0, "last_visited_at": None, "last_visited_by": None}
        out.append({
            **d,
            "manual_reviewed": manual_reviewed,
            "manual_reviewed_at": latest_manual.get("manual_reviewed_at") if latest_manual else None,
            "manual_initials": latest_manual.get("manual_initials") if latest_manual else None,
            "notes": latest_manual.get("notes") if latest_manual else None,
            "reviewer_email": latest_manual.get("email") if latest_manual else None,
            "auto_visited": auto["visit_count"] > 0,
            "auto_visit_count": auto["visit_count"],
            "auto_last_visited_at": auto["last_visited_at"],
            "auto_last_visited_by": auto["last_visited_by"],
        })
    return out


@router.put("/review-status/{slug}")
async def mark_reviewed(
    slug: str,
    data: ReviewMarkPayload,
    user: dict = Depends(require_roles("admin")),
):
    """Manual mark — counsel (or admin) checks off a document."""
    from database import db
    valid = {d["slug"] for d in _all_reviewable_docs()}
    if slug not in valid:
        raise HTTPException(status_code=404, detail=f"Unknown document slug: {slug}")

    now = now_iso()
    existing = await db.counsel_review_status.find_one({"slug": slug, "user_id": user["id"]})
    update = {
        "manual_reviewed": bool(data.reviewed),
        "manual_reviewed_at": now if data.reviewed else None,
        "manual_initials": (data.initials or "").strip() or None,
        "notes": (data.notes or "").strip() or None,
        "updated_at": now,
    }
    if existing:
        await db.counsel_review_status.update_one({"id": existing["id"]}, {"$set": update})
        existing.update(update)
        existing.pop("_id", None)
        return existing
    doc = {
        "id": gen_id(),
        "slug": slug,
        "user_id": user["id"],
        "email": user.get("email"),
        "created_at": now,
        **update,
    }
    await db.counsel_review_status.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ============ Admin-only audit view ============
@admin_router.get("/activity")
async def counsel_activity(
    limit: int = 500,
    email: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    """Full activity log — admin-only.

    A `readonly_admin` caller technically also passes require_roles("admin"),
    but we hide the log from them so a compromised counsel account cannot
    inspect (or later, manipulate) its own audit trail.
    """
    from database import db
    if user.get("role") == "readonly_admin":
        raise HTTPException(
            status_code=403,
            detail="Counsel accounts cannot view their own activity log.",
        )
    q: dict = {}
    if email:
        q["email"] = email
    cursor = db.counsel_activity_log.find(q).sort("timestamp", -1).limit(max(1, min(limit, 5000)))
    out: list[dict] = []
    async for e in cursor:
        e.pop("_id", None)
        out.append(e)
    return out


@admin_router.get("/activity/summary")
async def counsel_activity_summary(user: dict = Depends(require_roles("admin"))):
    """Per-counsel-user summary: last activity, total requests, top paths."""
    from database import db
    if user.get("role") == "readonly_admin":
        raise HTTPException(status_code=403, detail="Counsel accounts cannot view audit summary.")
    summary: dict[str, dict] = {}
    async for e in db.counsel_activity_log.find({}):
        email = e.get("email") or "(unknown)"
        s = summary.setdefault(email, {
            "email": email,
            "total_requests": 0,
            "last_activity_at": None,
            "unique_paths": set(),
            "read_count": 0,
            "blocked_writes": 0,
        })
        s["total_requests"] += 1
        s["unique_paths"].add(e.get("path", ""))
        ts = e.get("timestamp")
        if ts and (not s["last_activity_at"] or ts > s["last_activity_at"]):
            s["last_activity_at"] = ts
        if e.get("method") == "GET":
            s["read_count"] += 1
        if e.get("status_code") == 403 and e.get("method") in ("POST", "PUT", "PATCH", "DELETE"):
            s["blocked_writes"] += 1
    out = []
    for s in summary.values():
        s["unique_path_count"] = len(s["unique_paths"])
        del s["unique_paths"]
        out.append(s)
    return sorted(out, key=lambda x: x["last_activity_at"] or "", reverse=True)


@admin_router.delete("/activity")
async def counsel_activity_clear(user: dict = Depends(require_roles("admin"))):
    """Purge the activity log (admin-only, e.g. after a review cycle closes)."""
    from database import db
    if user.get("role") == "readonly_admin":
        raise HTTPException(status_code=403, detail="Counsel cannot clear their own log.")
    r = await db.counsel_activity_log.delete_many({})
    return {"deleted": r.deleted_count}
