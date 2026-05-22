"""Workshop routes."""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from models import WorkshopCreate, Workshop, WorkshopUpdate, gen_id, now_iso
from auth_utils import get_current_user, require_roles, get_current_user_optional
from utils.mailer import send_email
from utils.email_templates import workshop_cancelled
from utils.refunds import refund_session

logger = logging.getLogger("birthright.workshops")
router = APIRouter(prefix="/workshops", tags=["workshops"])


def _gen_check_in_code() -> str:
    """6-char uppercase alphanumeric, no ambiguous chars (0/O, 1/I/L)."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


@router.get("")
async def list_workshops(status: Optional[str] = None, search: Optional[str] = None):
    from database import db
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
        # Never expose check-in code in public list
        w.pop("check_in_code", None)
    return workshops


@router.get("/{workshop_id}")
async def get_workshop(workshop_id: str):
    from database import db
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
    from database import db
    payload = data.model_dump()
    # Facilitators can only create workshops assigned to themselves.
    if user["role"] == "facilitator":
        payload["facilitator_id"] = user["id"]
    # Always generate the check-in code server-side; ignore anything the client sent.
    payload["check_in_code"] = _gen_check_in_code()
    # Enforce slug uniqueness
    existing = await db.workshops.find_one({"slug": payload["slug"]})
    if existing:
        raise HTTPException(status_code=400, detail="A workshop with this slug already exists")
    workshop = {**payload, "id": gen_id(), "created_at": now_iso()}
    await db.workshops.insert_one(workshop)
    workshop.pop("_id", None)
    return workshop


@router.post("/{workshop_id}/duplicate")
async def duplicate_workshop(
    workshop_id: str,
    user: dict = Depends(require_roles("admin", "facilitator")),
):
    """Clone a workshop into a new draft. Dates shift 30 days into the future; slug gets '-copy' suffix."""
    from database import db
    src = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    if not src:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if user["role"] == "facilitator" and src["facilitator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your workshop")

    def _shift(iso: Optional[str], days: int = 30) -> Optional[str]:
        if not iso:
            return iso
        try:
            return (datetime.fromisoformat(iso.replace("Z", "+00:00")) + timedelta(days=days)).isoformat()
        except Exception:
            return iso

    base_slug = f"{src['slug']}-copy"
    slug = base_slug
    n = 2
    while await db.workshops.find_one({"slug": slug}):
        slug = f"{base_slug}-{n}"
        n += 1

    clone = {
        **src,
        "id": gen_id(),
        "slug": slug,
        "title": f"{src['title']} (Copy)",
        "start_date": _shift(src.get("start_date")),
        "end_date": _shift(src.get("end_date")),
        "early_bird_until": _shift(src.get("early_bird_until")),
        "status": "draft",
        "check_in_code": _gen_check_in_code(),
        "created_at": now_iso(),
    }
    await db.workshops.insert_one(clone)
    clone.pop("_id", None)
    return clone


@router.post("/{workshop_id}/cancel")
async def cancel_workshop(
    workshop_id: str,
    user: dict = Depends(require_roles("admin", "facilitator")),
):
    """Cancel a workshop, refund all paid registrants, and email everyone."""
    from database import db
    w = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if user["role"] == "facilitator" and w["facilitator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your workshop")
    if w["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Workshop already cancelled")

    regs = await db.registrations.find(
        {"workshop_id": workshop_id, "payment_status": "paid"}, {"_id": 0}
    ).to_list(1000)

    refund_results = []
    app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
    for r in regs:
        # 1) refund
        if r.get("payment_session_id") and r["payment_session_id"] != "seed_demo":
            res = await refund_session(r["payment_session_id"])
        else:
            res = {"status": "manual", "refund_id": None,
                   "amount": r.get("amount_paid", 0), "error": "No real Stripe session (seeded)"}
        amount = res.get("amount") if res.get("amount") is not None else r.get("amount_paid", 0)
        # 2) mark registration cancelled + record refund metadata
        await db.registrations.update_one(
            {"id": r["id"]},
            {"$set": {
                "payment_status": "cancelled",
                "cancelled_at": now_iso(),
                "cancelled_reason": "workshop_cancelled",
                "refund_status": res.get("status"),
                "refund_id": res.get("refund_id"),
                "refund_amount": amount,
                "refund_error": res.get("error"),
            }},
        )
        # 3) email registrant
        try:
            u = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "password_hash": 0})
            if u and u.get("email"):
                subj, html, text = workshop_cancelled(
                    first_name=u["first_name"], workshop=w,
                    refund_amount=amount, refund_status=res.get("status", "pending"),
                    app_url=app_url,
                )
                await send_email(
                    to=u["email"], subject=subj, html=html, text=text,
                    template_name="workshop_cancelled",
                    metadata={"workshop_id": workshop_id, "registration_id": r["id"]},
                )
        except Exception as e:
            logger.error(f"cancel email failed for reg {r['id']}: {e}")
        refund_results.append({
            "registration_id": r["id"], "user_id": r["user_id"],
            "amount": amount, "status": res.get("status"),
            "error": res.get("error"),
        })

    # mark workshop cancelled (last, so failures above can be retried)
    await db.workshops.update_one(
        {"id": workshop_id}, {"$set": {"status": "cancelled", "cancelled_at": now_iso()}}
    )
    return {
        "success": True,
        "refunds_attempted": len(refund_results),
        "refunds_succeeded": sum(1 for r in refund_results if r["status"] == "succeeded"),
        "refunds_pending": sum(1 for r in refund_results if r["status"] == "pending"),
        "refunds_failed": sum(1 for r in refund_results if r["status"] not in ("succeeded", "pending")),
        "results": refund_results,
    }


@router.get("/{workshop_id}/revenue")
async def workshop_revenue(
    workshop_id: str,
    user: dict = Depends(require_roles("admin", "facilitator")),
):
    """Per-workshop revenue stats. Facilitators only their own."""
    from database import db
    w = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if user["role"] == "facilitator" and w["facilitator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your workshop")
    regs = await db.registrations.find({"workshop_id": workshop_id}, {"_id": 0}).to_list(2000)
    paid = [r for r in regs if r["payment_status"] == "paid"]
    cancelled = [r for r in regs if r["payment_status"] == "cancelled"]
    gross = sum(float(r.get("amount_paid", 0)) for r in paid + cancelled)
    refunded = sum(float(r.get("refund_amount") or 0) for r in cancelled)
    net = gross - refunded
    return {
        "workshop_id": workshop_id,
        "title": w["title"],
        "capacity": w["capacity"],
        "paid_count": len(paid),
        "cancelled_count": len(cancelled),
        "checked_in_count": sum(1 for r in paid if r.get("checked_in")),
        "gross_revenue": round(gross, 2),
        "refunded": round(refunded, 2),
        "net_revenue": round(net, 2),
    }


@router.put("/{workshop_id}")
async def update_workshop(workshop_id: str, updates: WorkshopUpdate, user: dict = Depends(require_roles("admin", "facilitator"))):
    from database import db
    w = await db.workshops.find_one({"id": workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if user["role"] == "facilitator" and w["facilitator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your workshop")
    update_data = updates.model_dump(exclude_none=True)
    if update_data:
        await db.workshops.update_one({"id": workshop_id}, {"$set": update_data})
    updated = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    return updated


@router.delete("/{workshop_id}")
async def delete_workshop(workshop_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    await db.workshops.delete_one({"id": workshop_id})
    return {"success": True}


@router.get("/{workshop_id}/participants")
async def get_participants(workshop_id: str, user: dict = Depends(require_roles("admin", "facilitator"))):
    from database import db
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
    from database import db
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
    from database import db
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
