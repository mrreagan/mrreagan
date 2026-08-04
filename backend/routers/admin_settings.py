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
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from passlib.context import CryptContext

from auth_utils import require_roles
from database import db
from models import gen_id, now_iso
from utils.readonly_admin import READONLY_ROLE, COUNSEL_EMAIL, COUNSEL_PASSWORD
from utils.audit import log_action
from utils.mailer import send_email

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


def _require_true_admin(user: dict):
    """`require_roles('admin')` in this codebase also admits
    `readonly_admin` (counsel) for read-side admin routes. For the
    credentials endpoints we want STRICT admin — otherwise counsel could
    read `env_password_default_in_use` and learn whether the account
    still uses the seeded default. Enforce that here explicitly."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/counsel")
async def get_counsel_settings(user: dict = Depends(require_roles("admin"))):
    """Return the current counsel account state so the settings UI can
    prefill the form."""
    _require_true_admin(user)
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
    _require_true_admin(user)
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


# ============ SEND-A-LINK FLOW ============
# Instead of admin typing counsel's new password into the rotate form,
# admin clicks "Send set-password link". We generate a 24-hour, one-time
# opaque token, store it hashed in a small collection, and email
# counsel a link at the CURRENT counsel email address so they can pick
# their own password. Admin never handles the plaintext password.

_TOKEN_TTL_HOURS = 24


def _hash_token(raw: str) -> str:
    import hashlib
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _public_site_url(request: Request) -> str:
    from os import environ
    base = environ.get("PUBLIC_SITE_URL")
    if base:
        return base.rstrip("/")
    host = request.headers.get("host", "birthright.live")
    scheme = "https" if request.url.scheme == "https" else "http"
    return f"{scheme}://{host}"


@router.post("/counsel/send-set-password-link")
async def send_set_password_link(request: Request, user: dict = Depends(require_roles("admin"))):
    """Email the current counsel address a one-time link to set a new
    password. Admin does not see or type the new password. Any older
    unused link is superseded — only the newest token is valid.
    """
    _require_true_admin(user)
    account = await db.users.find_one({"role": READONLY_ROLE}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=500, detail="Counsel account not seeded")

    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS)

    # Supersede older links: one active token at a time.
    await db.counsel_password_tokens.delete_many({"user_id": account["id"]})
    await db.counsel_password_tokens.insert_one({
        "id": gen_id(),
        "user_id": account["id"],
        "token_hash": token_hash,
        "created_at": now_iso(),
        "expires_at": expires_at.isoformat(),
        "used_at": None,
        "created_by_email": user.get("email"),
    })

    link = f"{_public_site_url(request)}/counsel/set-password?token={raw_token}"

    subject = "Birthright · Set your counsel account password"
    html = f"""
    <div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;color:#1A2424">
      <h2 style="font-family:'Cormorant Garamond',serif;color:#0F2424">Set your counsel password</h2>
      <p>Birthright Foundation's Executive Director has invited you to set
      the password for your read-only counsel review account.</p>
      <p style="margin:24px 0">
        <a href="{link}" style="display:inline-block;background:#0F2424;color:#FAF8F5;padding:12px 20px;text-decoration:none;font-family:sans-serif;font-size:14px;border-radius:4px">
          Set your password
        </a>
      </p>
      <p style="color:#5C6B6B;font-size:13px">This link works once and expires in {_TOKEN_TTL_HOURS} hours.
      After you set your password you'll sign in at
      <a href="{_public_site_url(request)}/login" style="color:#476B6B">{_public_site_url(request)}/login</a>
      with the email <strong>{account['email']}</strong>.</p>
      <p style="color:#5C6B6B;font-size:13px">If you did not expect this
      email, ignore it. Questions? Reply to this email or write to
      legal@birthright.live.</p>
    </div>
    """
    text = (
        f"Birthright counsel account — set your password\n\n"
        f"Open this link to set your password (expires in {_TOKEN_TTL_HOURS} hours, one-time use):\n"
        f"{link}\n\n"
        f"Sign in afterwards at {_public_site_url(request)}/login as {account['email']}.\n"
    )
    try:
        email_id = await send_email(
            to=account["email"],
            subject=subject,
            html=html,
            text=text,
            template_name="counsel_set_password_link",
            metadata={"user_id": account["id"]},
        )
    except Exception as exc:
        logger.warning("counsel set-password email failed: %s", exc)
        email_id = None

    await log_action(
        db, user, "counsel.set_password_link.send",
        target_type="user", target_id=account["id"],
        metadata={"expires_at": expires_at.isoformat(), "email_id": email_id},
    )
    return {
        "ok": True,
        "email_sent_to": account["email"],
        "expires_at": expires_at.isoformat(),
        "email_id": email_id,
    }


@router.post("/counsel/set-password-from-token")
async def set_password_from_token(payload: dict, request: Request):
    """Public — accepts a token from the emailed link + new password.
    Verifies the token (hash match, unexpired, unused), rotates the
    counsel password, marks the token used, and revokes any active
    counsel session so old JWTs can't ride through.
    """
    _pwd_ctx_local = _pwd_ctx
    token = (payload.get("token") or "").strip()
    new_password = payload.get("password") or ""
    if not token:
        raise HTTPException(status_code=400, detail="token required")
    if len(new_password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters")

    token_hash = _hash_token(token)
    doc = await db.counsel_password_tokens.find_one({"token_hash": token_hash}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or unknown token")
    if doc.get("used_at"):
        raise HTTPException(status_code=400, detail="This link has already been used")
    try:
        exp = datetime.fromisoformat(doc["expires_at"].replace("Z", "+00:00"))
    except Exception:
        exp = datetime.now(timezone.utc) - timedelta(seconds=1)
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(status_code=400, detail="This link has expired. Ask admin for a new one.")

    account = await db.users.find_one({"id": doc["user_id"]}, {"_id": 0})
    if not account or account.get("role") != READONLY_ROLE:
        raise HTTPException(status_code=400, detail="Token no longer maps to a counsel account")

    await db.users.update_one(
        {"id": account["id"]},
        {"$set": {
            "password_hash": _pwd_ctx_local.hash(new_password),
            "counsel_credentials_rotated_at": now_iso(),
            "counsel_credentials_rotated_by": "self-service-via-link",
        }},
    )
    await db.counsel_password_tokens.update_one(
        {"token_hash": token_hash},
        {"$set": {"used_at": now_iso(),
                  "used_from_ip": request.client.host if request and request.client else None}},
    )
    # Kill any existing counsel JWT — auth_utils checks this on every request.
    await db.user_token_revocations.update_one(
        {"user_id": account["id"]},
        {"$set": {"revoked_at": now_iso()}},
        upsert=True,
    )
    await log_action(
        db, {"id": account["id"], "email": account["email"], "role": account["role"]},
        "counsel.set_password.self_service",
        target_type="user", target_id=account["id"],
        metadata={"via": "set-password-link"},
    )
    return {"ok": True, "email": account["email"]}
