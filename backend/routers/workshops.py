"""Workshop routes."""
import logging
import os
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from models import WorkshopCreate, WorkshopUpdate, gen_id, now_iso
from auth_utils import get_current_user, require_roles
from utils.mailer import send_email
from utils.email_templates import workshop_cancelled
from utils.refunds import refund_session
from utils.calendar_qr import build_ics
from fastapi.responses import Response

logger = logging.getLogger("birthright.workshops")
router = APIRouter(prefix="/workshops", tags=["workshops"])


def _gen_check_in_code() -> str:
    """6-char uppercase alphanumeric, no ambiguous chars (0/O, 1/I/L)."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


async def _fetch_facilitators(db, facilitator_ids: list) -> dict:
    if not facilitator_ids:
        return {}
    rows = await db.users.find(
        {"id": {"$in": facilitator_ids}}, {"_id": 0, "password_hash": 0}
    ).to_list(len(facilitator_ids))
    return {f["id"]: f for f in rows}


async def _registration_counts(db, workshop_ids: list) -> dict:
    counts = {wid: 0 for wid in workshop_ids}
    if not workshop_ids:
        return counts
    pipeline = [
        {"$match": {"workshop_id": {"$in": workshop_ids}, "payment_status": "paid"}},
        {"$group": {"_id": "$workshop_id", "n": {"$sum": 1}}},
    ]
    async for row in db.registrations.aggregate(pipeline):
        counts[row["_id"]] = row["n"]
    return counts


def _build_facilitator_summary(fac: Optional[dict]) -> Optional[dict]:
    if not fac:
        return None
    return {
        "id": fac["id"],
        "first_name": fac["first_name"],
        "last_name": fac["last_name"],
        "avatar_url": fac.get("avatar_url", ""),
        "facilitator_slug": fac.get("facilitator_slug"),
        "credentials": fac.get("credentials"),
    }


async def _enrich_workshops(db, workshops: list) -> list:
    """Attach facilitator summary + registered_count + spots_left, and strip check_in_code."""
    facilitator_ids = list({w["facilitator_id"] for w in workshops if w.get("facilitator_id")})
    facs_by_id = await _fetch_facilitators(db, facilitator_ids)
    counts_by_workshop = await _registration_counts(db, [w["id"] for w in workshops])

    for w in workshops:
        w["facilitator"] = _build_facilitator_summary(facs_by_id.get(w.get("facilitator_id")))
        w["registered_count"] = counts_by_workshop.get(w["id"], 0)
        w["spots_left"] = max(0, w["capacity"] - w["registered_count"])
        # Never expose check-in code in public list
        w.pop("check_in_code", None)
    return workshops


@router.get("")
async def list_workshops(status: Optional[str] = None, search: Optional[str] = None):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"short_description": {"$regex": search, "$options": "i"}},
        ]
    workshops = await db.workshops.find(query, {"_id": 0}).sort("start_date", 1).to_list(1000)
    return await _enrich_workshops(db, workshops)


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


@router.get("/{workshop_id}/ics")
async def workshop_ics(workshop_id: str):
    """Public .ics calendar download for any workshop (by id or slug)."""
    from database import db
    w = await db.workshops.find_one({"id": workshop_id}, {"_id": 0})
    if not w:
        w = await db.workshops.find_one({"slug": workshop_id}, {"_id": 0})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    ics_bytes = build_ics(w)
    safe_slug = (w.get("slug") or w.get("id") or "workshop").replace("/", "-")
    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{safe_slug}.ics"'},
    )


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


async def _refund_registration(db, reg: dict) -> dict:
    """Refund one registration via Stripe (or short-circuit for seeded demo data).

    Returns the refund result dict: {status, refund_id, amount, error}.
    """
    if reg.get("payment_session_id") and reg["payment_session_id"] != "seed_demo":
        return await refund_session(reg["payment_session_id"])
    return {
        "status": "manual",
        "refund_id": None,
        "amount": reg.get("amount_paid", 0),
        "error": "No real Stripe session (seeded)",
    }


async def _mark_registration_cancelled(db, reg: dict, refund: dict, amount: float) -> None:
    await db.registrations.update_one(
        {"id": reg["id"]},
        {"$set": {
            "payment_status": "cancelled",
            "cancelled_at": now_iso(),
            "cancelled_reason": "workshop_cancelled",
            "refund_status": refund.get("status"),
            "refund_id": refund.get("refund_id"),
            "refund_amount": amount,
            "refund_error": refund.get("error"),
        }},
    )


async def _email_registrant_cancellation(
    db, reg: dict, workshop: dict, refund: dict, amount: float, app_url: str
) -> None:
    """Best-effort email. Never raises."""
    try:
        u = await db.users.find_one({"id": reg["user_id"]}, {"_id": 0, "password_hash": 0})
        if not (u and u.get("email")):
            return
        subj, html, text = workshop_cancelled(
            first_name=u["first_name"], workshop=workshop,
            refund_amount=amount, refund_status=refund.get("status", "pending"),
            app_url=app_url,
        )
        await send_email(
            to=u["email"], subject=subj, html=html, text=text,
            template_name="workshop_cancelled",
            metadata={"workshop_id": workshop["id"], "registration_id": reg["id"]},
        )
    except Exception as e:
        logger.error(f"cancel email failed for reg {reg['id']}: {e}")


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

    app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
    refund_results = []
    for reg in regs:
        refund = await _refund_registration(db, reg)
        amount = refund.get("amount") if refund.get("amount") is not None else reg.get("amount_paid", 0)
        await _mark_registration_cancelled(db, reg, refund, amount)
        await _email_registrant_cancellation(db, reg, w, refund, amount, app_url)
        refund_results.append({
            "registration_id": reg["id"], "user_id": reg["user_id"],
            "amount": amount, "status": refund.get("status"),
            "error": refund.get("error"),
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
    user_ids = list({r["user_id"] for r in regs if r.get("user_id")})
    users_by_id: dict = {}
    if user_ids:
        rows = await db.users.find(
            {"id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}
        ).to_list(len(user_ids))
        users_by_id = {u["id"]: u for u in rows}
    for r in regs:
        r["user"] = users_by_id.get(r.get("user_id"))
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
