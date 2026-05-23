"""Password reset: request a token via email, then submit token + new password."""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth_utils import hash_password
from models import gen_id, now_iso
from utils.mailer import send_email
from utils.email_templates import password_reset as pw_reset_template

logger = logging.getLogger("birthright.password_reset")
router = APIRouter(prefix="/auth", tags=["auth"])

TOKEN_TTL_HOURS = 1


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=6)


@router.post("/request-password-reset")
async def request_password_reset(data: ForgotPasswordRequest):
    """Always returns success (do not leak which emails are registered)."""
    from database import db
    user = await db.users.find_one({"email": data.email.lower()}, {"_id": 0, "password_hash": 0})
    if user:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).isoformat()
        await db.password_reset_tokens.insert_one({
            "id": gen_id(),
            "token": token,
            "user_id": user["id"],
            "email": user["email"],
            "expires_at": expires,
            "used": False,
            "created_at": now_iso(),
        })
        app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
        reset_url = f"{app_url}/reset-password?token={token}"
        subject, html, text = pw_reset_template(first_name=user["first_name"], reset_url=reset_url)
        await send_email(
            to=user["email"], subject=subject, html=html, text=text,
            template_name="password_reset", metadata={"user_id": user["id"]},
        )
    # Don't reveal existence
    return {"success": True, "message": "If that email is registered, a reset link is on its way."}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    from database import db
    record = await db.password_reset_tokens.find_one({"token": data.token, "used": False})
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or already used token")
    try:
        expires = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed token")
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=400, detail="This reset link has expired. Please request a new one.")
    new_hash = hash_password(data.new_password)
    await db.users.update_one({"id": record["user_id"]}, {"$set": {"password_hash": new_hash}})
    await db.password_reset_tokens.update_one(
        {"id": record["id"]},
        {"$set": {"used": True, "used_at": now_iso()}},
    )
    # Invalidate any other outstanding tokens for this user
    await db.password_reset_tokens.update_many(
        {"user_id": record["user_id"], "used": False},
        {"$set": {"used": True, "used_at": now_iso(), "invalidated": True}},
    )
    return {"success": True, "message": "Password updated. You can sign in now."}
