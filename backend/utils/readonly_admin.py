"""Read-only counsel access.

Purpose:
    Give outside legal counsel a real login they can use to inspect every
    admin and public URL on the platform WITHOUT being able to mutate data.

Design:
    - New user role: `readonly_admin`.
    - A FastAPI middleware inspects every incoming request. If the caller
      is authenticated with `role = readonly_admin` and the HTTP method is
      NOT safe (POST/PUT/PATCH/DELETE), the request is rejected with 403.
    - `require_roles("admin")` decorators are extended platform-wide to also
      accept `readonly_admin`. Combined with the middleware, this gives
      counsel view-only access to every admin surface without cascading
      hand-edits across every router.
    - Startup seed guarantees a canonical counsel account exists. Credentials
      are also mirrored to /app/memory/test_credentials.md for handoff.

Notes:
    - Login/logout is intentionally exempt so counsel can actually sign in.
    - Webhooks (Stripe) are exempt because Stripe callers have no user
      session — the middleware only fires when a session/JWT is present.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth_utils import COOKIE_NAME, JWT_SECRET, JWT_ALG
import jwt  # PyJWT — already installed as an auth_utils transitive dep

logger = logging.getLogger("birthright.readonly")

READONLY_ROLE = "readonly_admin"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Paths a counsel account must be able to hit even though they mutate — login,
# logout, session refresh, password reset. Anything with side effects that a
# read-only session legitimately needs.
_ALLOWLIST_EXACT = frozenset({
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/refresh",
})
_ALLOWLIST_PREFIXES = (
    "/api/auth/",             # covers login/logout/refresh + optional MFA in future
    "/api/password-reset/",   # counsel can reset their own password
    "/api/counsel/review-status/",  # counsel can check off their own review checklist
)

# Regex allow-list — used when a write path must be permitted by exact
# shape rather than by prefix. We use this for the comment-CREATE route
# because it lives under /api/legal/comments/{slug} but there are also
# mutating sub-routes (/apply-roundtrip, /import-roundtrip, /{id}/resolve)
# that MUST stay blocked for counsel. Prefix allow-listing would leak
# those; explicit shape allow-listing does not.
_ALLOWLIST_REGEX = (
    # POST /api/legal/comments/<slug>   — counsel can post a redline / comment.
    # The <slug> is a filename-safe token; anything with an extra path
    # segment (apply-roundtrip / import-roundtrip / <id>/resolve / export)
    # is intentionally excluded.
    re.compile(r"^/api/legal/comments/[A-Za-z0-9._-]+/?$"),
)


class ReadonlyEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        path = request.url.path
        if path in _ALLOWLIST_EXACT:
            return await call_next(request)
        if any(path.startswith(p) for p in _ALLOWLIST_PREFIXES):
            return await call_next(request)
        if any(rx.match(path) for rx in _ALLOWLIST_REGEX):
            return await call_next(request)

        # Not a safe method and not allow-listed. Check if the caller is a
        # read-only admin; if so, refuse. Everyone else falls through.
        role = _peek_role_from_request(request)
        if role == READONLY_ROLE:
            logger.info(
                "readonly_admin blocked from %s %s (headers: %s)",
                request.method, path, request.headers.get("origin", "?"),
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        "This is a read-only counsel account. Data cannot be "
                        "modified from this session. Contact engineering if "
                        "you need mutable admin access."
                    ),
                    "readonly": True,
                },
            )
        return await call_next(request)


def _peek_role_from_request(request: Request) -> str | None:
    """Best-effort role extraction — mirrors `auth_utils.get_current_user`
    but returns None on any failure so the request continues normally."""
    token: str | None = None
    auth_hdr = request.headers.get("authorization")
    if auth_hdr and auth_hdr.lower().startswith("bearer "):
        token = auth_hdr.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("role")
    except Exception:
        return None


# =========================================================================
# Seed helper
# =========================================================================
COUNSEL_EMAIL = os.environ.get("COUNSEL_EMAIL", "counsel@birthright.live")
_DEFAULT_COUNSEL_PASSWORD = "counsel-review-2026"  # noqa: S105 — seed only, published in test_credentials.md
COUNSEL_PASSWORD = os.environ.get("COUNSEL_PASSWORD", _DEFAULT_COUNSEL_PASSWORD)


async def ensure_counsel_account(db) -> dict:
    """Idempotent seed for the counsel read-only account. Returns the user doc.

    Bootstrap logic (first boot ever):
        - No user with role=readonly_admin exists → create one from the
          COUNSEL_EMAIL / COUNSEL_PASSWORD env values.

    Steady-state logic (subsequent boots):
        - A readonly_admin user exists → treat the DB as the source of truth
          for both email and password. Only reconcile `role` and `is_active`
          so a misconfigured field can never leave you locked out. **Never
          overwrite the password on boot** — otherwise a rotation from the
          `/admin/settings/counsel` page would be undone on next redeploy.
    """
    from models import gen_id, now_iso
    from passlib.context import CryptContext

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Look up by role, not email, so an email rotation done from the UI
    # keeps working across redeploys.
    existing = await db.users.find_one({"role": READONLY_ROLE})
    if not existing:
        user = {
            "id": gen_id(),
            "email": COUNSEL_EMAIL,
            "password_hash": pwd_ctx.hash(COUNSEL_PASSWORD),
            "first_name": "Counsel",
            "last_name": "Reviewer",
            "role": READONLY_ROLE,
            "is_active": True,
            "is_foundation": False,
            "created_at": now_iso(),
            "notes": (
                "Read-only counsel review account — auto-seeded from env. "
                "Once created, credentials are managed via "
                "/admin/settings/counsel; env vars are only used for the "
                "initial bootstrap."
            ),
        }
        await db.users.insert_one(user)
        logger.info("Seeded counsel read-only account: %s", COUNSEL_EMAIL)
        return user

    # Existing — reconcile only structural fields (role + active). Do NOT
    # touch email / password_hash — those are UI-managed.
    updates = {}
    if existing.get("role") != READONLY_ROLE:
        updates["role"] = READONLY_ROLE
    if not existing.get("is_active", True):
        updates["is_active"] = True
    if updates:
        await db.users.update_one({"id": existing["id"]}, {"$set": updates})
        logger.info("Reconciled counsel account structural fields: %s", list(updates.keys()))
    return {**existing, **updates}
