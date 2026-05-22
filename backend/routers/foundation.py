"""Foundation content, governing members, contact, newsletter, sponsors, dashboard."""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from models import (
    GoverningMember,
    GoverningMemberCreate,
    FoundationContent,
    ContactMessageCreate,
    NewsletterSubscribe,
    gen_id,
    now_iso,
)
from auth_utils import get_current_user, require_roles

router = APIRouter(tags=["foundation"])


# ========== FOUNDATION CONTENT ==========
@router.get("/foundation/content")
async def get_content():
    from server import db
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
    from server import db
    await db.foundation_content.update_one(
        {"key": "content"}, {"$set": {**data.model_dump(), "key": "content"}}, upsert=True
    )
    return data


# ========== GOVERNING MEMBERS ==========
@router.get("/foundation/governing-members")
async def list_members():
    from server import db
    members = await db.governing_members.find({}, {"_id": 0}).sort("order", 1).to_list(1000)
    return members


@router.post("/foundation/governing-members")
async def create_member(data: GoverningMemberCreate, user: dict = Depends(require_roles("admin"))):
    from server import db
    m = {**data.model_dump(), "id": gen_id()}
    await db.governing_members.insert_one(m)
    m.pop("_id", None)
    return m


@router.put("/foundation/governing-members/{member_id}")
async def update_member(member_id: str, data: GoverningMemberCreate, user: dict = Depends(require_roles("admin"))):
    from server import db
    await db.governing_members.update_one({"id": member_id}, {"$set": data.model_dump()})
    m = await db.governing_members.find_one({"id": member_id}, {"_id": 0})
    return m


@router.delete("/foundation/governing-members/{member_id}")
async def delete_member(member_id: str, user: dict = Depends(require_roles("admin"))):
    from server import db
    await db.governing_members.delete_one({"id": member_id})
    return {"success": True}


# ========== FACILITATORS (public profiles) ==========
@router.get("/facilitators")
async def list_facilitators():
    from server import db
    facs = await db.users.find({"role": "facilitator"}, {"_id": 0, "password_hash": 0}).to_list(1000)
    # add workshop count + avg rating
    for f in facs:
        f["workshop_count"] = await db.workshops.count_documents({"facilitator_id": f["id"]})
    return facs


@router.get("/facilitators/{slug_or_id}")
async def get_facilitator(slug_or_id: str):
    from server import db
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


# ========== CONTACT ==========
@router.post("/contact")
async def submit_contact(data: ContactMessageCreate):
    from server import db
    msg = {**data.model_dump(), "id": gen_id(), "created_at": now_iso(), "read": False}
    await db.contact_messages.insert_one(msg)
    # Optionally subscribe to newsletter
    if data.newsletter_opt_in:
        await db.newsletter_subscribers.update_one(
            {"email": data.email.lower()},
            {
                "$setOnInsert": {
                    "id": gen_id(),
                    "email": data.email.lower(),
                    "name": f"{data.first_name} {data.last_name or ''}".strip(),
                    "created_at": now_iso(),
                    "active": True,
                }
            },
            upsert=True,
        )
    msg.pop("_id", None)
    return {"success": True, "message": "Thank you for reaching out. We'll be in touch soon."}


@router.get("/contact/messages")
async def list_contact(user: dict = Depends(require_roles("admin"))):
    from server import db
    items = await db.contact_messages.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


# ========== NEWSLETTER ==========
@router.post("/newsletter")
async def subscribe(data: NewsletterSubscribe):
    from server import db
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
    return {"success": True, "message": "Welcome! You're subscribed to birthright updates."}


@router.get("/newsletter/subscribers")
async def list_subscribers(user: dict = Depends(require_roles("admin"))):
    from server import db
    items = await db.newsletter_subscribers.find({}, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return items


# ========== SPONSORS ==========
@router.get("/sponsors")
async def list_sponsors():
    from server import db
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
    from server import db
    # registrations
    regs = await db.registrations.find(
        {"user_id": user["id"], "payment_status": "paid"}, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    for r in regs:
        w = await db.workshops.find_one({"id": r["workshop_id"]}, {"_id": 0})
        r["workshop"] = w
    # orders
    orders = await db.orders.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    # impact statements
    impacts = await db.impact_statements.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {
        "registrations": regs,
        "orders": orders,
        "impact_statements": impacts,
    }


@router.get("/dashboard/facilitator")
async def facilitator_dashboard(user: dict = Depends(require_roles("facilitator", "admin"))):
    from server import db
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
    from server import db
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
    from server import db
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(10000)
    return users


@router.put("/admin/users/{user_id}/role")
async def change_role(user_id: str, body: dict, user: dict = Depends(require_roles("admin"))):
    from server import db
    new_role = body.get("role")
    if new_role not in ("admin", "facilitator", "participant"):
        raise HTTPException(status_code=400, detail="Invalid role")
    await db.users.update_one({"id": user_id}, {"$set": {"role": new_role}})
    return {"success": True}


# ========== WAITLIST ==========
@router.post("/workshops/{workshop_id}/waitlist")
async def join_waitlist(workshop_id: str, user: dict = Depends(get_current_user)):
    from server import db
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
