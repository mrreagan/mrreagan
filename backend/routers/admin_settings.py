"""Admin console settings — currently just counsel-credential rotation.

Endpoints:
    GET  /api/admin/settings/counsel          → current counsel email + hints
    POST /api/admin/settings/counsel/rotate   → change email and/or password

Rules:
    - Admin-only. Read-only counsel cannot rotate their own credentials
      this way (they use the standard password-reset flow instead).
    - The DB is the source of truth once the account has been seeded;
      env vars are only used for the initial bootstrap. See
      utils/readonly_admin.py::ensure_counsel_account.
"""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from passlib.context import CryptContext

from auth_utils import require_roles
from database import db
from models import now_iso
from utils.readonly_admin import READONLY_ROLE, COUNSEL_EMAIL, COUNSEL_PASSWORD
from utils.audit import log_action

logger = logging.getLogger("birthright.admin.settings")
router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _redact_email(email: str) -> str:
    if "@" not in email:
        return "?"
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{local[:1]}•@{domain}"
    return f"{local[0]}{'•' * (len(local) - 2)}{local[-1]}@{domain}"


@router.get("/counsel")
async def get_counsel_settings(user: dict = Depends(require_roles("admin"))):
    """Return the current counsel account state so the settings UI can
    prefill the form."""
    doc = await db.users.find_one({"role": READONLY_ROLE}, {"_id": 0})
    if not doc:
        # Should never happen after boot, but degrade gracefully.
        return {
            "seeded": False,
            "email": COUNSEL_EMAIL,
            "email_redacted": _redact_email(COUNSEL_EMAIL),
            "env_email_default": COUNSEL_EMAIL,
            "notes": "No counsel account exists yet. Restart the backend or hit /rotate to seed one.",
        }
    return {
        "seeded": True,
        "email": doc["email"],
        "email_redacted": _redact_email(doc["email"]),
        "env_email_default": COUNSEL_EMAIL,
        "env_password_default_in_use": _pwd_ctx.verify(
            COUNSEL_PASSWORD, doc.get("password_hash", "") or " "
        ),
        "created_at": doc.get("created_at"),
        "last_rotated_at": doc.get("counsel_credentials_rotated_at"),
        "last_rotated_by": doc.get("counsel_credentials_rotated_by"),
    }


@router.post("/counsel/rotate")
async def rotate_counsel_credentials(
    payload: dict,
    request: Request,
    user: dict = Depends(require_roles("admin")),
):
    """Rotate the counsel email and/or password. Either field is optional;
    at least one must be provided.

    Payload: { "email": "counsel@birthright.live", "password": "new-secret-2026" }

    Password requirement: >= 12 characters. Email must be a plausible RFC-shape
    address. Both are stored in the DB user record and persist across
    backend restarts (the seeder no longer overwrites them).
    """
    new_email = (payload.get("email") or "").strip()
    new_password = payload.get("password") or ""
    if not new_email and not new_password:
        raise HTTPException(status_code=400, detail="email or password required")

    updates: dict = {}
    if new_email:
        if not _EMAIL_RE.match(new_email):
            raise HTTPException(status_code=400, detail="Email doesn't look valid")
        # Guard against collision — refuse if another account (non-counsel)
        # already owns that email, to avoid dupes and login confusion.
        clash = await db.users.find_one(
            {"email": new_email, "role": {"$ne": READONLY_ROLE}},
            {"_id": 0, "id": 1},
        )
        if clash:
            raise HTTPException(status_code=409, detail="That email is already in use by another account")
        updates["email"] = new_email
    if new_password:
        if len(new_password) < 12:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 12 characters",
            )
        updates["password_hash"] = _pwd_ctx.hash(new_password)

    existing = await db.users.find_one({"role": READONLY_ROLE}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=500, detail="Counsel account not seeded")

    updates["counsel_credentials_rotated_at"] = now_iso()
    updates["counsel_credentials_rotated_by"] = user.get("email")

    await db.users.update_one({"id": existing["id"]}, {"$set": updates})

    # Audit — record which fields changed, never the value of the password.
    changed = [k for k in updates if k in ("email", "password_hash")]
    await log_action(
        db, user, "counsel.credentials.rotate",
        target_type="user", target_id=existing["id"],
        metadata={"fields_changed": changed, "new_email": new_email if new_email else None},
    )
    logger.info("counsel credentials rotated by %s (%s)", user.get("email"), changed)

    # Best-effort: invalidate any active counsel sessions by touching a
    # server-side revocation token. If a "user_token_revocations" pattern
    # doesn't exist yet, this is a no-op; login continues to work.
    try:
        await db.user_token_revocations.update_one(
            {"user_id": existing["id"]},
            {"$set": {"revoked_at": now_iso()}},
            upsert=True,
        )
    except Exception as exc:
        logger.warning("counsel token revocation write failed: %s", exc)

    return {
        "ok": True,
        "email": updates.get("email", existing["email"]),
        "password_changed": "password_hash" in updates,
        "rotated_at": updates["counsel_credentials_rotated_at"],
    }
