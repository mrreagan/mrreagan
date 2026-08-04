"""Auth routes: register, login, logout, me, update profile."""
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from typing import Optional
from models import UserRegister, UserLogin, UserProfile, UserUpdate, gen_id, now_iso
from auth_utils import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
    get_current_user_optional,
    set_session_cookie,
    clear_session_cookie,
)
from database import db

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_user_doc(data: UserRegister) -> dict:
    """Construct user document from registration payload."""
    return {
        "id": gen_id(),
        "email": data.email.lower(),
        "password_hash": hash_password(data.password),
        "first_name": data.first_name,
        "last_name": data.last_name,
        "phone": data.phone or "",
        "role": "participant",
        "bio": "",
        "avatar_url": "",
        "facilitator_slug": None,
        "credentials": None,
        "created_at": now_iso(),
    }


def _public_user(user: dict) -> dict:
    """Strip sensitive fields before returning to client."""
    safe = {k: v for k, v in user.items() if k not in ("password_hash", "_id")}
    return safe


@router.post("/register")
async def register(data: UserRegister, request: Request, response: Response):
    if not data.accepted_terms or not data.accepted_privacy:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Service and Privacy Policy to create an account.",
        )
    if await db.users.find_one({"email": data.email.lower()}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = _build_user_doc(data)
    user["terms_accepted_at"] = now_iso()
    user["privacy_accepted_at"] = now_iso()
    await db.users.insert_one(user)
    token = create_token(user["id"], user["role"])
    set_session_cookie(response, token)
    # Log security events: account creation + consent captured.
    try:
        from utils.user_activity import log_event, CAT_ACCOUNT, CAT_SIGN
        await log_event(
            db, user_id=user["id"], email=user["email"], role=user["role"],
            event_type="account.created", category=CAT_ACCOUNT,
            method="POST", path="/api/auth/register", status_code=200, request=request,
        )
        await log_event(
            db, user_id=user["id"], email=user["email"], role=user["role"],
            event_type="signing.terms_accepted", category=CAT_SIGN,
            method="POST", path="/api/auth/register", status_code=200,
            metadata={"policy": "terms_of_service", "version": "current"},
            request=request,
        )
        await log_event(
            db, user_id=user["id"], email=user["email"], role=user["role"],
            event_type="signing.privacy_accepted", category=CAT_SIGN,
            method="POST", path="/api/auth/register", status_code=200,
            metadata={"policy": "privacy_policy", "version": "current"},
            request=request,
        )
    except Exception:
        pass
    return {"token": token, "user": _public_user(user)}


@router.post("/login")
async def login(data: UserLogin, request: Request, response: Response):
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        # Log failed attempt for security forensics.
        try:
            from utils.user_activity import log_event, CAT_AUTH
            await log_event(
                db, user_id=user["id"] if user else None, email=email,
                event_type="auth.login_failed", category=CAT_AUTH,
                role=(user or {}).get("role"), method="POST", path="/api/auth/login",
                status_code=401, request=request,
            )
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], user["role"])
    set_session_cookie(response, token)
    try:
        from utils.user_activity import log_event, CAT_AUTH
        await log_event(
            db, user_id=user["id"], email=user.get("email"),
            event_type="auth.login_success", category=CAT_AUTH,
            role=user.get("role"), method="POST", path="/api/auth/login",
            status_code=200, request=request,
        )
    except Exception:
        pass
    return {"token": token, "user": _public_user(user)}


@router.post("/logout")
async def logout(request: Request, response: Response, user: Optional[dict] = Depends(get_current_user_optional)):
    clear_session_cookie(response)
    if user:
        try:
            from utils.user_activity import log_event, CAT_AUTH
            await log_event(
                db, user_id=user["id"], email=user.get("email"),
                event_type="auth.logout", category=CAT_AUTH,
                role=user.get("role"), method="POST", path="/api/auth/logout",
                status_code=200, request=request,
            )
        except Exception:
            pass
    return {"success": True}


@router.get("/me", response_model=UserProfile)
async def me(user: dict = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserProfile)
async def update_me(updates: UserUpdate, user: dict = Depends(get_current_user)):
    update_data = updates.model_dump(exclude_none=True)
    if update_data:
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
    return await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
