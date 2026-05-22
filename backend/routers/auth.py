"""Auth routes: register, login, me, update profile."""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from models import UserRegister, UserLogin, UserProfile, UserUpdate, gen_id, now_iso
from auth_utils import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(data: UserRegister):
    from database import db
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "id": gen_id(),
        "email": data.email.lower(),
        "password_hash": hash_password(data.password),
        "first_name": data.first_name,
        "last_name": data.last_name,
        "phone": data.phone or "",
        "role": "participant",  # default
        "bio": "",
        "avatar_url": "",
        "facilitator_slug": None,
        "credentials": None,
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    token = create_token(user["id"], user["role"])
    user.pop("password_hash", None)
    user.pop("_id", None)
    return {"token": token, "user": user}


@router.post("/login")
async def login(data: UserLogin):
    from database import db
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], user["role"])
    user.pop("password_hash", None)
    user.pop("_id", None)
    return {"token": token, "user": user}


@router.get("/me", response_model=UserProfile)
async def me(user: dict = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserProfile)
async def update_me(updates: UserUpdate, user: dict = Depends(get_current_user)):
    from database import db
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if update_data:
        await db.users.update_one({"id": user["id"]}, {"$set": update_data})
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return updated
