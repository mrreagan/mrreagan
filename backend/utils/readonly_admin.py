"""Counsel access — end-user privileges + full legal-review write + admin-mutation lock.

Purpose:
    Give outside legal counsel a real login they can use to (a) inspect every
    admin URL, (b) fully author their legal work (comments, redlines, roundtrips,
    full-notice uploads), and (c) use the platform as a normal end user (cart,
    checkout, profile, orders) so they can experience the site in production
    context. Only the sensitive admin-mutation surface is locked down.

Design:
    - New user role: `readonly_admin`.
    - A FastAPI middleware inspects every incoming request. Counsel is allowed
      to mutate freely EXCEPT on paths under `/api/admin/*` (which run the
      site — settings, users, refunds, payouts, campaigns, etc). Legal work
      lives under `/api/legal/*`, so counsel can write there without any
      allow-listing gymnastics.
    - `require_roles("admin")` decorators are extended platform-wide to also
      accept `readonly_admin`. Combined with the middleware, this gives
      counsel full access to legal admin surfaces (`/api/legal/*`) while the
      middleware still fences off broader admin mutations.
    - Startup seed guarantees a canonical counsel account exists. Credentials
      are also mirrored to /app/memory/test_credentials.md for handoff.

Explicit exceptions (counsel-writable subset of /api/admin/*):
    - /api/admin/legal/*      — full legal review flow (notice uploads, etc)
    - /api/admin/settings/counsel/set-password-from-token
      + /api/admin/settings/counsel/set-password
      so counsel can accept a self-service password link.

Notes:
    - Login/logout is intentionally exempt so counsel can actually sign in.
    - Webhooks (Stripe) are exempt because Stripe callers have no user
      session — the middleware only fires when a session/JWT is present.
"""
from __future__ import annotations

import logging
import os
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth_utils import COOKIE_NAME, JWT_SECRET, JWT_ALG
import jwt  # PyJWT — already installed as an auth_utils transitive dep

logger = logging.getLogger("birthright.readonly")

READONLY_ROLE = "readonly_admin"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Any mutation whose path starts with one of these prefixes is denied for
# counsel. Everything else — including /api/legal/*, /api/cart, /api/checkout,
# /api/me, /api/orders, /api/reviews, /api/dm, etc — is allowed so counsel
# can use the platform as a normal end user AND author legal work.
_DENY_PREFIXES = (
    "/api/admin/",
)

# Narrow write allow-list carved OUT of `_DENY_PREFIXES`. These are admin
# routes counsel legitimately needs even though they live under `/api/admin/*`.
_ADMIN_ALLOWLIST_PREFIXES = (
    "/api/admin/legal/",                                # full legal-review surface (notice uploads, drafts)
    "/api/admin/settings/counsel/set-password-from-token",
    "/api/admin/settings/counsel/set-password",
)


class ReadonlyEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        path = request.url.path

        # Not an /api/admin/* mutation → let it through (cart, checkout,
        # profile, orders, legal review, reviews, DMs, …).
        if not any(path.startswith(p) for p in _DENY_PREFIXES):
            return await call_next(request)

        # /api/admin/* mutation on an explicit allow-list (legal work +
        # counsel self-service password) → let it through.
        if any(path.startswith(p) for p in _ADMIN_ALLOWLIST_PREFIXES):
            return await call_next(request)

        # /api/admin/* mutation NOT on the allow-list. Check the caller —
        # counsel gets refused; every other role passes through unchanged
        # (they still hit whatever role gate the route itself defines).
        role = _peek_role_from_request(request)
        if role == READONLY_ROLE:
            logger.info(
                "readonly_admin blocked from %s %s (origin: %s)",
                request.method, path, request.headers.get("origin", "?"),
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        "This admin route is off-limits for the counsel account. "
                        "Counsel has full access to legal review, notice uploads, "
                        "and normal end-user actions (cart, checkout, profile). "
                        "Contact engineering if you need broader admin access."
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
