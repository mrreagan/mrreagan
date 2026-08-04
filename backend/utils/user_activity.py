"""User activity audit — Tier 1 + Tier 2 logging.

Tier 1 (security events, all users):
    Login success/failure, logout, password change, MFA changes, sensitive
    document signings (ToS, Indemnification, Partnership), checkout success,
    account deletion.

Tier 2 (admin URL trace):
    A middleware records every request from any user with role `admin`.
    Provides a self-audit trail for the platform's admins. Excludes the
    read-only counsel role — counsel is already covered by
    routers.counsel_audit.CounselActivityLoggerMiddleware.

Retention:
    Entries older than 365 days are removed nightly by
    `sweep_stale_activity` (wired into the scheduler).

Erasure policy:
    Per product decision, log entries are retained even after the associated
    user account is deleted. This preserves the security timeline for legal
    defense. Rows for deleted users still carry the historical email so
    admins can trace activity, but no linkage to a live account remains.

Collections:
    user_activity_log {id, user_id, email, role, event_type, category,
                       method, path, status_code, ip, user_agent,
                       metadata, timestamp}
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.middleware.base import BaseHTTPMiddleware

from auth_utils import require_roles, get_current_user, COOKIE_NAME, JWT_SECRET, JWT_ALG
from models import gen_id
import jwt

logger = logging.getLogger("birthright.user_activity")

RETENTION_DAYS = 365

# Event categories — normalized so admin filters and user views group cleanly.
CAT_AUTH = "auth"
CAT_SECURITY = "security"
CAT_SIGN = "signing"
CAT_PAYMENT = "payment"
CAT_ADMIN_TRACE = "admin_trace"
CAT_ADMIN_ACTION = "admin_action"
CAT_ACCOUNT = "account"

# --- Which events users can see for themselves (transparency). Everything
# else is admin-only. Admin trace is never user-visible.
_USER_VISIBLE_CATEGORIES = frozenset({CAT_AUTH, CAT_SECURITY, CAT_SIGN, CAT_PAYMENT, CAT_ACCOUNT})


# =========================================================================
# Core helper — call this from any router when a security-relevant event happens
# =========================================================================
async def log_event(
    db,
    *,
    user_id: Optional[str],
    email: Optional[str],
    event_type: str,
    category: str,
    role: Optional[str] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    metadata: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    """Persist one activity event. Never raises — failures are logged but do
    not break the calling flow."""
    try:
        entry = {
            "id": gen_id(),
            "user_id": user_id or None,
            "email": (email or "").lower() or None,
            "role": role,
            "event_type": event_type,
            "category": category,
            "method": method,
            "path": path,
            "status_code": status_code,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if request is not None:
            entry["ip"] = request.client.host if request.client else None
            entry["user_agent"] = (request.headers.get("user-agent") or "")[:512]
        await db.user_activity_log.insert_one(entry)
    except Exception as e:
        logger.warning("user_activity log_event failed (%s): %s", event_type, e)


# =========================================================================
# Middleware — Tier 2: every admin URL is auto-traced
# =========================================================================
_TRACE_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
_TRACE_SKIP_PREFIXES = (
    "/api/admin/counsel/",       # counsel audit page (recursive)
    "/api/admin/user-activity",  # this page's own reads
    "/static/",
)


class AdminTraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method not in _TRACE_METHODS:
            return response
        path = request.url.path
        if any(path.startswith(p) for p in _TRACE_SKIP_PREFIXES):
            return response

        info = _peek_user(request)
        if not info or info.get("role") != "admin":
            # Only trace real admins. `readonly_admin` is covered by
            # the counsel-specific middleware. Regular users are not traced.
            return response

        try:
            from database import db
            email = info.get("email")
            if not email and info.get("id"):
                u = await db.users.find_one({"id": info["id"]}, {"_id": 0, "email": 1})
                if u:
                    email = u.get("email")
            await log_event(
                db,
                user_id=info.get("id"),
                email=email,
                role="admin",
                event_type="admin.request",
                category=CAT_ADMIN_TRACE,
                method=request.method,
                path=path,
                status_code=response.status_code,
                request=request,
            )
        except Exception as e:
            logger.warning("admin trace failed: %s", e)
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


# =========================================================================
# Retention sweep — nightly
# =========================================================================
async def sweep_stale_activity(db) -> int:
    """Delete activity entries older than 365 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    result = await db.user_activity_log.delete_many({"timestamp": {"$lt": cutoff}})
    if result.deleted_count:
        logger.info("user_activity retention sweep: purged %d entries", result.deleted_count)
    return result.deleted_count


# =========================================================================
# Routers
# =========================================================================
user_router = APIRouter(prefix="/account", tags=["account-activity"])
admin_router = APIRouter(prefix="/admin/user-activity", tags=["admin-user-activity"])


@user_router.get("/activity")
async def my_activity(
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    """A signed-in user's own security-relevant events. Admin URL traces are
    hidden from user-facing view."""
    from database import db
    cursor = db.user_activity_log.find({
        "user_id": user["id"],
        "category": {"$in": list(_USER_VISIBLE_CATEGORIES)},
    }).sort("timestamp", -1).limit(limit)
    out: list[dict] = []
    async for e in cursor:
        e.pop("_id", None)
        # Never leak IP/UA to the user themselves (unnecessary and creepy).
        e.pop("ip", None)
        e.pop("user_agent", None)
        out.append(e)
    return out


@admin_router.get("")
async def admin_user_activity(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    category: Optional[str] = None,
    event_type: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = Query(500, ge=1, le=5000),
    admin: dict = Depends(require_roles("admin")),
):
    """Full user activity — admin only. Counsel accounts (readonly_admin)
    are blocked from viewing this because it would let them audit other users'
    private security events."""
    if admin.get("role") == "readonly_admin":
        raise HTTPException(status_code=403, detail="User activity audit is admin-only.")
    from database import db
    q: dict = {}
    if user_id:
        q["user_id"] = user_id
    if email:
        q["email"] = email.lower()
    if category:
        q["category"] = category
    if event_type:
        q["event_type"] = event_type
    time_range: dict = {}
    if since:
        time_range["$gte"] = since
    if until:
        time_range["$lte"] = until
    if time_range:
        q["timestamp"] = time_range
    cursor = db.user_activity_log.find(q).sort("timestamp", -1).limit(limit)
    out: list[dict] = []
    async for e in cursor:
        e.pop("_id", None)
        out.append(e)
    return out


@admin_router.get("/summary")
async def admin_activity_summary(admin: dict = Depends(require_roles("admin"))):
    """Aggregate view: per-user totals and top event types last 30 days."""
    if admin.get("role") == "readonly_admin":
        raise HTTPException(status_code=403, detail="User activity audit is admin-only.")
    from database import db
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    per_user: dict[str, dict] = {}
    per_event: dict[str, int] = {}
    total = 0
    async for e in db.user_activity_log.find({"timestamp": {"$gte": cutoff}}):
        total += 1
        email = e.get("email") or "(unknown)"
        u = per_user.setdefault(email, {
            "email": email,
            "role": e.get("role"),
            "events": 0,
            "last_at": None,
            "categories": {},
        })
        u["events"] += 1
        cat = e.get("category") or "other"
        u["categories"][cat] = u["categories"].get(cat, 0) + 1
        ts = e.get("timestamp")
        if ts and (not u["last_at"] or ts > u["last_at"]):
            u["last_at"] = ts
        per_event[e.get("event_type", "?")] = per_event.get(e.get("event_type", "?"), 0) + 1
    return {
        "window_days": 30,
        "total_events": total,
        "per_user": sorted(per_user.values(), key=lambda x: x["events"], reverse=True),
        "top_events": sorted(
            [{"event_type": k, "count": v} for k, v in per_event.items()],
            key=lambda x: x["count"], reverse=True,
        )[:20],
    }
