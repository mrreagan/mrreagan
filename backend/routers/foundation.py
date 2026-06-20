"""Foundation content, governing members, contact, newsletter, sponsors, dashboard."""
import logging
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from models import (
    GoverningMemberCreate,
    FoundationContent,
    ContactMessageCreate,
    NewsletterSubscribe,
    gen_id,
    now_iso,
)
from auth_utils import get_current_user, require_roles
from utils.mailer import send_email, is_real_send_enabled
from utils.email_templates import (
    contact_autoreply,
    contact_admin_notify,
    newsletter_welcome,
)

logger = logging.getLogger("birthright.foundation")
router = APIRouter(tags=["foundation"])


# ========== FOUNDATION CONTENT ==========
@router.get("/foundation/content")
async def get_content():
    from database import db
    doc = await db.foundation_content.find_one({"key": "content"}, {"_id": 0})
    if not doc:
        return {
            "mission_statement": "",
            "about_text": "",
            "education_structure": "",
            "vision": "",
            "values": [],
        }
    return doc


@router.put("/foundation/content")
async def update_content(data: FoundationContent, user: dict = Depends(require_roles("admin"))):
    from database import db
    await db.foundation_content.update_one(
        {"key": "content"}, {"$set": {**data.model_dump(), "key": "content"}}, upsert=True
    )
    return data


# ========== GOVERNING MEMBERS ==========
@router.get("/foundation/governing-members")
async def list_members():
    from database import db
    members = await db.governing_members.find({}, {"_id": 0}).sort("order", 1).to_list(1000)
    return members


@router.post("/foundation/governing-members")
async def create_member(data: GoverningMemberCreate, user: dict = Depends(require_roles("admin"))):
    from database import db
    m = {**data.model_dump(), "id": gen_id()}
    await db.governing_members.insert_one(m)
    m.pop("_id", None)
    return m


@router.put("/foundation/governing-members/{member_id}")
async def update_member(member_id: str, data: GoverningMemberCreate, user: dict = Depends(require_roles("admin"))):
    from database import db
    await db.governing_members.update_one({"id": member_id}, {"$set": data.model_dump()})
    m = await db.governing_members.find_one({"id": member_id}, {"_id": 0})
    return m


@router.delete("/foundation/governing-members/{member_id}")
async def delete_member(member_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    await db.governing_members.delete_one({"id": member_id})
    return {"success": True}


# ========== FACILITATORS (public profiles) ==========
@router.get("/facilitators")
async def list_facilitators():
    from database import db
    facs = await db.users.find({"role": "facilitator"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    # add workshop count + avg rating
    for f in facs:
        f["workshop_count"] = await db.workshops.count_documents({"facilitator_id": f["id"]})
    return facs


@router.get("/facilitators/{slug_or_id}")
async def get_facilitator(slug_or_id: str):
    from database import db
    f = await db.users.find_one(
        {"$or": [{"facilitator_slug": slug_or_id}, {"id": slug_or_id}], "role": "facilitator"},
        {"_id": 0, "password_hash": 0},
    )
    if not f:
        raise HTTPException(status_code=404, detail="Facilitator not found")
    workshops = await db.workshops.find({"facilitator_id": f["id"]}, {"_id": 0}).to_list(1000)
    f["workshops"] = workshops
    # aggregate reviews on their workshops
    workshop_ids = [w["id"] for w in workshops]
    reviews = await db.reviews.find({"workshop_id": {"$in": workshop_ids}}, {"_id": 0}).to_list(1000)
    for r in reviews:
        if r.get("anonymous"):
            r["user_name"] = "Anonymous Participant"
    f["reviews"] = reviews
    if reviews:
        f["avg_rating"] = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
    else:
        f["avg_rating"] = None
    return f


async def _subscribe_to_newsletter(db, data) -> bool:
    """Add to newsletter if opted-in and not already subscribed. Returns True
    if a welcome email was queued for a NEW subscription."""
    if not data.newsletter_opt_in:
        return False
    if await db.newsletter_subscribers.find_one({"email": data.email.lower()}):
        return False
    await db.newsletter_subscribers.insert_one({
        "id": gen_id(),
        "email": data.email.lower(),
        "name": f"{data.first_name} {data.last_name or ''}".strip(),
        "created_at": now_iso(),
        "active": True,
    })
    try:
        subj, html, text = newsletter_welcome(name=data.first_name)
        await send_email(
            to=data.email, subject=subj, html=html, text=text,
            template_name="newsletter_welcome",
            metadata={"source": "contact_form_opt_in"},
        )
        return True
    except Exception as e:
        logger.error(f"newsletter welcome (contact opt-in) failed: {e}")
        return False


async def _send_contact_emails(data, contact_id: str) -> None:
    """Notify admin and auto-reply the sender. Best-effort; never raises."""
    try:
        admin_inbox = os.environ.get("ADMIN_NOTIFY_EMAIL") or os.environ.get("REPLY_TO_EMAIL")
        full_name = f"{data.first_name} {data.last_name or ''}".strip()
        if admin_inbox:
            subj, html, text = contact_admin_notify(
                name=full_name, email=data.email, phone=data.phone or "",
                subject_line=data.subject or "", message=data.message,
            )
            await send_email(
                to=admin_inbox, subject=subj, html=html, text=text,
                reply_to=data.email, template_name="contact_admin_notify",
                metadata={"contact_id": contact_id},
            )
        subj, html, text = contact_autoreply(first_name=data.first_name)
        await send_email(
            to=data.email, subject=subj, html=html, text=text,
            template_name="contact_autoreply", metadata={"contact_id": contact_id},
        )
    except Exception as e:
        logger.error(f"contact email failed: {e}")


# ========== CONTACT ==========
@router.post("/contact")
async def submit_contact(data: ContactMessageCreate):
    from database import db
    msg = {**data.model_dump(), "id": gen_id(), "created_at": now_iso(), "read": False}
    await db.contact_messages.insert_one(msg)
    msg.pop("_id", None)
    sent_welcome = await _subscribe_to_newsletter(db, data)
    await _send_contact_emails(data, msg["id"])
    return {
        "success": True,
        "message": "Thank you for reaching out. We'll be in touch soon.",
        "subscribed": sent_welcome,
    }


@router.get("/contact/messages")
async def list_contact(user: dict = Depends(require_roles("admin"))):
    from database import db
    items = await db.contact_messages.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


# ========== NEWSLETTER ==========
@router.post("/newsletter")
async def subscribe(data: NewsletterSubscribe):
    from database import db
    existing = await db.newsletter_subscribers.find_one({"email": data.email.lower()})
    if existing:
        return {"success": True, "message": "You're already subscribed. Thank you!"}
    sub = {
        "id": gen_id(),
        "email": data.email.lower(),
        "name": data.name or "",
        "created_at": now_iso(),
        "active": True,
    }
    await db.newsletter_subscribers.insert_one(sub)
    try:
        subj, html, text = newsletter_welcome(name=data.name or "")
        await send_email(
            to=data.email, subject=subj, html=html, text=text,
            template_name="newsletter_welcome", metadata={"subscriber_id": sub["id"]},
        )
    except Exception as e:
        logger.error(f"newsletter welcome email failed: {e}")
    return {"success": True, "message": "Welcome! You're subscribed to birthright updates."}


@router.get("/newsletter/subscribers")
async def list_subscribers(user: dict = Depends(require_roles("admin"))):
    from database import db
    items = await db.newsletter_subscribers.find({}, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return items


# ========== SPONSORS ==========
@router.get("/sponsors")
async def list_sponsors():
    from database import db
    sponsors = await db.sponsors.find({"status": "active", "public_display": True}, {"_id": 0}).to_list(1000)
    # enrich with user name
    for s in sponsors:
        if s.get("user_id"):
            u = await db.users.find_one({"id": s["user_id"]}, {"_id": 0, "password_hash": 0})
            if u:
                s["name"] = f"{u['first_name']} {u['last_name']}"
    return sponsors


# ========== USER DASHBOARD ==========
@router.get("/dashboard/me")
async def my_dashboard(user: dict = Depends(get_current_user)):
    from database import db
    # registrations
    regs = await db.registrations.find(
        {"user_id": user["id"], "payment_status": "paid"}, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    for r in regs:
        w = await db.workshops.find_one({"id": r["workshop_id"]}, {"_id": 0})
        r["workshop"] = w
    # orders — enrich fulfillments with customer-friendly status labels
    from utils.order_dispatch import customer_friendly_status
    orders = await db.orders.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for o in orders:
        for f in (o.get("fulfillments") or []):
            f["customer_status"] = customer_friendly_status(f.get("status"))
    # impact statements
    impacts = await db.impact_statements.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {
        "registrations": regs,
        "orders": orders,
        "impact_statements": impacts,
    }


@router.get("/dashboard/facilitator")
async def facilitator_dashboard(user: dict = Depends(require_roles("facilitator", "admin"))):
    from database import db
    query = {} if user["role"] == "admin" else {"facilitator_id": user["id"]}
    workshops = await db.workshops.find(query, {"_id": 0}).sort("start_date", 1).to_list(1000)
    for w in workshops:
        w["registered_count"] = await db.registrations.count_documents(
            {"workshop_id": w["id"], "payment_status": "paid"}
        )
        w["open_qa"] = await db.discussions.count_documents(
            {"workshop_id": w["id"], "is_question": True, "answered": False}
        )
        w["open_support"] = await db.support_requests.count_documents(
            {"workshop_id": w["id"], "status": "open"}
        )
    return {"workshops": workshops}


@router.get("/dashboard/admin")
async def admin_dashboard(user: dict = Depends(require_roles("admin"))):
    from database import db
    return {
        "users_count": await db.users.count_documents({}),
        "workshops_count": await db.workshops.count_documents({}),
        "registrations_count": await db.registrations.count_documents({"payment_status": "paid"}),
        "orders_count": await db.orders.count_documents({}),
        "products_count": await db.products.count_documents({}),
        "newsletter_count": await db.newsletter_subscribers.count_documents({"active": True}),
        "sponsors_count": await db.sponsors.count_documents({"status": "active"}),
        "contact_messages": await db.contact_messages.count_documents({"read": False}),
        "total_revenue": sum(
            [
                t["amount"]
                async for t in db.payment_transactions.find(
                    {"payment_status": "paid"}, {"amount": 1, "_id": 0}
                )
            ]
        ),
    }


@router.get("/admin/users")
async def list_users(user: dict = Depends(require_roles("admin"))):
    from database import db
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(10000)
    return users


@router.patch("/admin/users/{user_id}/foundation-status")
async def set_user_foundation_status(
    user_id: str,
    payload: dict,
    admin: dict = Depends(require_roles("admin")),
):
    """Toggle the `is_foundation` flag on a user record.

    Foundation members (board, paid staff, governing officers) get:
      - Wholesale pricing on equip products that have a `wholesale_price` set
      - 1:1 passthrough on AI wallet usage (no Foundation markup)
      - No patronage markup added on gallery purchases
    """
    from database import db
    is_foundation = bool(payload.get("is_foundation"))
    target = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "first_name": 1, "is_foundation": 1})
    if not target:
        raise HTTPException(status_code=404, detail="user not found")
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_foundation": is_foundation, "updated_at": now_iso()}},
    )
    return {"user_id": user_id, "email": target.get("email"), "is_foundation": is_foundation}


@router.get("/admin/email-log")
async def email_log(user: dict = Depends(require_roles("admin")), limit: int = 100):
    """Combined view of dry-run-queued + actually-sent emails for inspection."""
    from database import db
    sent = await db.email_log.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    queued = await db.outbound_emails.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    combined = sorted(sent + queued, key=lambda e: e.get("created_at", ""), reverse=True)
    return {
        "items": combined[:limit],
        "real_send_enabled": is_real_send_enabled(),
    }


@router.get("/admin/email-status")
async def email_status(user: dict = Depends(require_roles("admin"))):
    """Cutover diagnostic — reveals what's blocking the live-mode flip without
    leaking the actual key (`RESEND_API_KEY` is reported only by presence)."""
    import os as _os
    from database import db
    key = _os.environ.get("RESEND_API_KEY", "")
    sender = _os.environ.get("SENDER_EMAIL", "")
    reply = _os.environ.get("REPLY_TO_EMAIL", "")
    dry_run_raw = _os.environ.get("EMAIL_DRY_RUN", "true")
    dry_run = dry_run_raw.lower() == "true"
    sent_count = await db.email_log.count_documents({})
    queued_count = await db.outbound_emails.count_documents({})
    failed_count = await db.email_log.count_documents({"status": "failed"})
    return {
        "dry_run": dry_run,
        "real_send_enabled": is_real_send_enabled(),
        "resend_key_configured": bool(key) and key.startswith("re_"),
        "resend_key_prefix": (key[:6] + "…") if key else "",
        "sender_email": sender,
        "reply_to_email": reply or sender,
        "sender_domain": sender.split("@", 1)[1] if "@" in sender else "",
        "queued_dry_run_count": queued_count,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "checklist": _email_cutover_checklist(key, sender, dry_run_raw),
    }


def _email_cutover_checklist(key: str, sender: str, dry_run_raw: str) -> list[dict]:
    """Return a list of `{step, ok, hint}` rows the admin UI renders verbatim."""
    return [
        {
            "step": "RESEND_API_KEY configured",
            "ok": bool(key) and key.startswith("re_"),
            "hint": "Set RESEND_API_KEY=re_xxx in backend/.env (from your Resend dashboard).",
        },
        {
            "step": "SENDER_EMAIL configured",
            "ok": "@" in sender,
            "hint": "Set SENDER_EMAIL to a Resend-verified sender (e.g. hello@birthright.live).",
        },
        {
            "step": "Sender domain DNS verified on Resend",
            "ok": False if not sender else None,  # unverifiable from here
            "hint": "Confirm SPF/DKIM/DMARC records for the sender domain on your DNS provider — Resend dashboard will turn the domain green.",
        },
        {
            "step": "EMAIL_DRY_RUN=false in backend/.env",
            "ok": dry_run_raw.lower() == "false",
            "hint": "Flip to false then run `sudo supervisorctl restart backend`.",
        },
    ]


class EmailTestRequest(BaseModel):
    to: str
    subject: Optional[str] = "Birthright email cutover test"


@router.post("/admin/email-test")
async def email_test(req: EmailTestRequest, user: dict = Depends(require_roles("admin"))):
    """Send (or dry-run-queue) a self-test email. Use after flipping EMAIL_DRY_RUN
    to confirm the live Resend path works."""
    from utils.mailer import send_email
    target = req.to.strip()
    if not target or "@" not in target:
        raise HTTPException(400, "Provide a valid recipient email")
    subject = (req.subject or "Birthright email cutover test").strip()[:120]
    html = (
        "<div style=\"font-family:Georgia,serif;color:#1A2424;max-width:560px\">"
        "<h2 style=\"font-weight:400\">Email cutover test</h2>"
        f"<p>Hi! This is a live test from <strong>{user.get('email')}</strong> via the Birthright "
        "admin console. If you're reading this, real sends are working.</p>"
        f"<p style=\"color:#5C6B6B;font-size:13px;margin-top:24px\">Sent at {now_iso()}.</p>"
        "</div>"
    )
    text = f"Email cutover test from {user.get('email')} at {now_iso()}."
    email_id = await send_email(
        to=target, subject=subject, html=html, text=text,
        template_name="email_cutover_test",
        metadata={"sent_by": user["id"], "sent_by_email": user.get("email")},
    )
    return {
        "ok": email_id is not None,
        "email_id": email_id,
        "real_send_enabled": is_real_send_enabled(),
        "to": target,
    }


@router.put("/admin/users/{user_id}/role")
async def change_role(user_id: str, body: dict, user: dict = Depends(require_roles("admin"))):
    from database import db
    new_role = body.get("role")
    if new_role not in ("admin", "facilitator", "participant"):
        raise HTTPException(status_code=400, detail="Invalid role")
    await db.users.update_one({"id": user_id}, {"$set": {"role": new_role}})
    return {"success": True}


# ========== WAITLIST ==========
@router.post("/workshops/{workshop_id}/waitlist")
async def join_waitlist(workshop_id: str, user: dict = Depends(get_current_user)):
    from database import db
    existing = await db.waitlist.find_one({"workshop_id": workshop_id, "user_id": user["id"]})
    if existing:
        return {"success": True, "message": "Already on the waitlist"}
    entry = {
        "id": gen_id(),
        "workshop_id": workshop_id,
        "user_id": user["id"],
        "created_at": now_iso(),
        "notified": False,
    }
    await db.waitlist.insert_one(entry)
    return {"success": True, "message": "You're on the waitlist. We'll notify you if a spot opens."}
