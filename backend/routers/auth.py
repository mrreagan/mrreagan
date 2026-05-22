"""Auth routes: register, login, logout, me, update profile."""
from fastapi import APIRouter, HTTPException, Depends, Response
from models import UserRegister, UserLogin, UserProfile, UserUpdate, gen_id, now_iso
from auth_utils import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
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
async def register(data: UserRegister, response: Response):
    if await db.users.find_one({"email": data.email.lower()}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = _build_user_doc(data)
    await db.users.insert_one(user)
    token = create_token(user["id"], user["role"])
    set_session_cookie(response, token)
    return {"token": token, "user": _public_user(user)}


@router.post("/login")
async def login(data: UserLogin, response: Response):
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], user["role"])
    set_session_cookie(response, token)
    return {"token": token, "user": _public_user(user)}


@router.post("/logout")
async def logout(response: Response):
    clear_session_cookie(response)
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
