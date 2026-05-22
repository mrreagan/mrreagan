"""Registration self-service: cancel, release seat (admin/facilitator), waitlist promotion."""
import logging
import os
from fastapi import APIRouter, HTTPException, Depends
from auth_utils import get_current_user, require_roles
from models import now_iso
from utils.mailer import send_email
from utils.email_templates import waitlist_promotion

logger = logging.getLogger("birthright.registrations")
router = APIRouter(prefix="/registrations", tags=["registrations"])


async def _promote_waitlist(db, workshop_id: str) -> dict | None:
    """Notify the first non-notified waitlister that a seat opened. Returns the entry or None."""
    next_entry = await db.waitlist.find_one(
        {"workshop_id": workshop_id, "notified": False},
        sort=[("created_at", 1)],
    )
    if not next_entry:
        return None
    workshop = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    user = await db.users.find_one({"id": next_entry["user_id"]}, {"_id": 0, "password_hash": 0})
    if not (workshop and user and user.get("email")):
        return None
    try:
        app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
        subject, html, text = waitlist_promotion(
            first_name=user["first_name"], workshop=workshop, app_url=app_url,
        )
        await send_email(
            to=user["email"], subject=subject, html=html, text=text,
            template_name="waitlist_promotion",
            metadata={"workshop_id": workshop_id, "user_id": user["id"]},
        )
    except Exception as e:
        logger.error(f"waitlist promotion email failed: {e}")
    await db.waitlist.update_one(
        {"id": next_entry["id"]},
        {"$set": {"notified": True, "notified_at": now_iso()}},
    )
    return {"user_id": user["id"], "email": user["email"]}


async def _cancel_and_promote(db, registration: dict) -> dict | None:
    """Mark a paid registration cancelled and promote the next waitlister."""
    await db.registrations.update_one(
        {"id": registration["id"]},
        {"$set": {"payment_status": "cancelled", "cancelled_at": now_iso()}},
    )
    return await _promote_waitlist(db, registration["workshop_id"])


@router.delete("/{registration_id}")
async def cancel_my_registration(registration_id: str, user: dict = Depends(get_current_user)):
    """Participant self-service cancel. Releases the seat and notifies first waitlister."""
    from database import db
    reg = await db.registrations.find_one({"id": registration_id})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg["user_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not your registration")
    if reg["payment_status"] != "paid":
        raise HTTPException(status_code=400, detail="Registration is not active")
    if reg.get("checked_in"):
        raise HTTPException(status_code=400, detail="Cannot cancel after check-in")
    promoted = await _cancel_and_promote(db, reg)
    return {"success": True, "promoted": promoted}


@router.post("/{registration_id}/release")
async def release_seat(
    registration_id: str,
    user: dict = Depends(require_roles("facilitator", "admin")),
):
    """Facilitator/admin manually releases a seat (e.g., participant unreachable, no-show)."""
    from database import db
    reg = await db.registrations.find_one({"id": registration_id})
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if user["role"] == "facilitator":
        w = await db.workshops.find_one({"id": reg["workshop_id"]})
        if not w or w["facilitator_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not your workshop")
    if reg["payment_status"] != "paid":
        raise HTTPException(status_code=400, detail="Registration is not active")
    promoted = await _cancel_and_promote(db, reg)
    return {"success": True, "promoted": promoted}


@router.post("/promote-waitlist/{workshop_id}")
async def promote_waitlist_endpoint(
    workshop_id: str,
    user: dict = Depends(require_roles("facilitator", "admin")),
):
    """Manually trigger waitlist promotion if a seat is mathematically open."""
    from database import db
    w = await db.workshops.find_one({"id": workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if user["role"] == "facilitator" and w["facilitator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your workshop")
    promoted = await _promote_waitlist(db, workshop_id)
    return {"success": True, "promoted": promoted}
