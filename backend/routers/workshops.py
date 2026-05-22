"""Workshop routes."""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from models import WorkshopCreate, Workshop, WorkshopUpdate, gen_id, now_iso
from auth_utils import get_current_user, require_roles, get_current_user_optional

router = APIRouter(prefix="/workshops", tags=["workshops"])


@router.get("")
async def list_workshops(status: Optional[str] = None, search: Optional[str] = None):
    from server import db
    query = {}
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"short_description": {"$regex": search, "$options": "i"}},
        ]
    workshops = await db.workshops.find(query, {"_id": 0}).sort("start_date", 1).to_list(1000)
    # enrich with facilitator info and registration count
    for w in workshops:
        fac = await db.users.find_one({"id": w["facilitator_id"]}, {"_id": 0, "password_hash": 0})
        w["facilitator"] = (
            {
                "id": fac["id"],
                "first_name": fac["first_name"],
                "last_name": fac["last_name"],
                "avatar_url": fac.get("avatar_url", ""),
                "facilitator_slug": fac.get("facilitator_slug"),
                "credentials": fac.get("credentials"),
            }
            if fac
            else None
        )
        w["registered_count"] = await db.registrations.count_documents(
            {"workshop_id": w["id"], "payment_status": "paid"}
        )
        w["spots_left"] = max(0, w["capacity"] - w["registered_count"])
    return workshops


@router.get("/{workshop_id}")
async def get_workshop(workshop_id: str):
    from server import db
    w = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    if not w:
        # try slug
        w = await db.workshops.find_one({"slug": workshop_id}, {"_id": 0})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    fac = await db.users.find_one({"id": w["facilitator_id"]}, {"_id": 0, "password_hash": 0})
    w["facilitator"] = (
        {
            "id": fac["id"],
            "first_name": fac["first_name"],
            "last_name": fac["last_name"],
            "avatar_url": fac.get("avatar_url", ""),
            "bio": fac.get("bio", ""),
            "facilitator_slug": fac.get("facilitator_slug"),
            "credentials": fac.get("credentials"),
        }
        if fac
        else None
    )
    w["registered_count"] = await db.registrations.count_documents(
        {"workshop_id": w["id"], "payment_status": "paid"}
    )
    w["spots_left"] = max(0, w["capacity"] - w["registered_count"])
    # Don't expose check_in_code to public
    w.pop("check_in_code", None)
    return w


@router.post("")
async def create_workshop(data: WorkshopCreate, user: dict = Depends(require_roles("admin", "facilitator"))):
    from server import db
    workshop = {**data.model_dump(), "id": gen_id(), "created_at": now_iso()}
    await db.workshops.insert_one(workshop)
    workshop.pop("_id", None)
    return workshop


@router.put("/{workshop_id}")
async def update_workshop(workshop_id: str, updates: WorkshopUpdate, user: dict = Depends(require_roles("admin", "facilitator"))):
    from server import db
    w = await db.workshops.find_one({"id": workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if user["role"] == "facilitator" and w["facilitator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your workshop")
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if update_data:
        await db.workshops.update_one({"id": workshop_id}, {"$set": update_data})
    updated = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    return updated


@router.delete("/{workshop_id}")
async def delete_workshop(workshop_id: str, user: dict = Depends(require_roles("admin"))):
    from server import db
    await db.workshops.delete_one({"id": workshop_id})
    return {"success": True}


@router.get("/{workshop_id}/participants")
async def get_participants(workshop_id: str, user: dict = Depends(require_roles("admin", "facilitator"))):
    from server import db
    w = await db.workshops.find_one({"id": workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if user["role"] == "facilitator" and w["facilitator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your workshop")
    regs = await db.registrations.find({"workshop_id": workshop_id, "payment_status": "paid"}, {"_id": 0}).to_list(1000)
    for r in regs:
        u = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "password_hash": 0})
        r["user"] = u
    return regs


@router.post("/{workshop_id}/check-in")
async def check_in(workshop_id: str, body: dict, user: dict = Depends(get_current_user)):
    from server import db
    code = body.get("code", "")
    w = await db.workshops.find_one({"id": workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if w["check_in_code"].upper() != code.upper():
        raise HTTPException(status_code=400, detail="Invalid check-in code")
    reg = await db.registrations.find_one(
        {"workshop_id": workshop_id, "user_id": user["id"], "payment_status": "paid"}
    )
    if not reg:
        raise HTTPException(status_code=403, detail="You are not registered for this workshop")
    await db.registrations.update_one(
        {"id": reg["id"]},
        {"$set": {"checked_in": True, "checked_in_at": now_iso()}},
    )
    return {"success": True, "message": "Checked in successfully"}


@router.get("/{workshop_id}/my-registration")
async def my_registration(workshop_id: str, user: dict = Depends(get_current_user)):
    from server import db
    reg = await db.registrations.find_one(
        {"workshop_id": workshop_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not reg:
        return {"registered": False}
    w = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    # include check-in code only if registered + paid (facilitator-shown only is too restrictive; we show after registration)
    return {
        "registered": True,
        "registration": reg,
        "check_in_code_required": True,
        "directions_notes": w.get("directions_notes", ""),
        "location_name": w.get("location_name", ""),
        "location_address": w.get("location_address", ""),
        "map_url": w.get("map_url", ""),
    }
