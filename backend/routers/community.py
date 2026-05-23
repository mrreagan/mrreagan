"""Community routes: discussions/Q&A, chat, reviews, impact statements, support."""
import logging
import os
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from models import (
    DiscussionCreate,
    ChatMessageCreate,
    ReviewCreate,
    ImpactStatementCreate,
    SupportRequestCreate,
    SupportResponse,
    gen_id,
    now_iso,
)
from auth_utils import get_current_user, require_roles
from utils.mailer import send_email
from utils.email_templates import qa_reply_notification

logger = logging.getLogger("birthright.community")
router = APIRouter(tags=["community"])


async def _ensure_workshop_access(db, workshop_id: str, user: dict, allow_facilitator=True, allow_admin=True):
    """User must be registered (paid) OR be the workshop's facilitator/admin."""
    if allow_admin and user.get("role") == "admin":
        return True
    if allow_facilitator and user.get("role") == "facilitator":
        w = await db.workshops.find_one({"id": workshop_id})
        if w and w["facilitator_id"] == user["id"]:
            return True
    reg = await db.registrations.find_one(
        {"workshop_id": workshop_id, "user_id": user["id"], "payment_status": "paid"}
    )
    return bool(reg)


# ========== DISCUSSIONS / Q&A ==========
@router.post("/discussions")
async def create_discussion(data: DiscussionCreate, user: dict = Depends(get_current_user)):
    from database import db
    if not await _ensure_workshop_access(db, data.workshop_id, user):
        raise HTTPException(status_code=403, detail="Not enrolled in this workshop")
    doc = {
        **data.model_dump(),
        "id": gen_id(),
        "user_id": user["id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "user_role": user["role"],
        "answered": False,
        "created_at": now_iso(),
    }
    await db.discussions.insert_one(doc)
    doc.pop("_id", None)
    # If this is a facilitator/admin reply to a question, notify the question's author
    try:
        if data.parent_id and user["role"] in ("facilitator", "admin"):
            parent = await db.discussions.find_one({"id": data.parent_id})
            if parent and parent.get("is_question") and parent["user_id"] != user["id"]:
                author = await db.users.find_one({"id": parent["user_id"]}, {"_id": 0, "password_hash": 0})
                workshop = await db.workshops.find_one({"id": data.workshop_id}, {"_id": 0})
                if author and workshop and author.get("email"):
                    app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
                    excerpt = (data.content or "")[:280] + ("…" if len(data.content or "") > 280 else "")
                    subject, html, text = qa_reply_notification(
                        first_name=author["first_name"], workshop=workshop,
                        reply_excerpt=excerpt, app_url=app_url,
                    )
                    await send_email(
                        to=author["email"], subject=subject, html=html, text=text,
                        template_name="qa_reply",
                        metadata={"workshop_id": data.workshop_id, "discussion_id": doc["id"]},
                    )
            # mark question as answered
            if parent and parent.get("is_question"):
                await db.discussions.update_one({"id": parent["id"]}, {"$set": {"answered": True}})
    except Exception as e:
        logger.error(f"Q&A reply notification failed: {e}")
    return doc


@router.get("/discussions")
async def list_discussions(
    workshop_id: str = Query(...),
    is_question: Optional[bool] = None,
    user: dict = Depends(get_current_user),
):
    from database import db
    if not await _ensure_workshop_access(db, workshop_id, user):
        raise HTTPException(status_code=403, detail="Not enrolled in this workshop")
    query: dict = {"workshop_id": workshop_id}
    if is_question in (True, False):
        query["is_question"] = is_question
    items = await db.discussions.find(query, {"_id": 0}).sort("created_at", 1).to_list(1000)
    # Filter private: only author + facilitator + admin can see private ones
    is_facilitator_or_admin = user["role"] == "admin"
    if user["role"] == "facilitator":
        w = await db.workshops.find_one({"id": workshop_id})
        if w and w["facilitator_id"] == user["id"]:
            is_facilitator_or_admin = True
    visible = []
    for it in items:
        if it.get("is_private") and not is_facilitator_or_admin and it["user_id"] != user["id"]:
            continue
        visible.append(it)
    return visible


@router.post("/discussions/{discussion_id}/mark-answered")
async def mark_answered(discussion_id: str, user: dict = Depends(require_roles("facilitator", "admin"))):
    from database import db
    await db.discussions.update_one({"id": discussion_id}, {"$set": {"answered": True}})
    return {"success": True}


# ========== CHAT (polling) ==========
@router.post("/chat")
async def send_chat(data: ChatMessageCreate, user: dict = Depends(get_current_user)):
    from database import db
    if not await _ensure_workshop_access(db, data.workshop_id, user):
        raise HTTPException(status_code=403, detail="Not enrolled in this workshop")
    msg = {
        **data.model_dump(),
        "id": gen_id(),
        "sender_id": user["id"],
        "sender_name": f"{user['first_name']} {user['last_name']}",
        "created_at": now_iso(),
    }
    await db.chat_messages.insert_one(msg)
    msg.pop("_id", None)
    return msg


@router.get("/chat")
async def list_chat(
    workshop_id: str = Query(...),
    recipient_id: Optional[str] = None,
    since: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    from database import db
    if not await _ensure_workshop_access(db, workshop_id, user):
        raise HTTPException(status_code=403, detail="Not enrolled in this workshop")
    query = {"workshop_id": workshop_id}
    # DM filter: messages between user and recipient_id
    if recipient_id:
        query["$or"] = [
            {"sender_id": user["id"], "recipient_id": recipient_id},
            {"sender_id": recipient_id, "recipient_id": user["id"]},
        ]
    else:
        # group chat: messages with no recipient
        query["recipient_id"] = None
    if since:
        query["created_at"] = {"$gt": since}
    msgs = await db.chat_messages.find(query, {"_id": 0}).sort("created_at", 1).to_list(1000)
    return msgs


@router.get("/chat/participants")
async def chat_participants(workshop_id: str = Query(...), user: dict = Depends(get_current_user)):
    from database import db
    if not await _ensure_workshop_access(db, workshop_id, user):
        raise HTTPException(status_code=403, detail="Not enrolled in this workshop")
    w = await db.workshops.find_one({"id": workshop_id})
    regs = await db.registrations.find(
        {"workshop_id": workshop_id, "payment_status": "paid"}, {"_id": 0}
    ).to_list(1000)
    participants = []
    seen = set()
    if w:
        fac = await db.users.find_one({"id": w["facilitator_id"]}, {"_id": 0, "password_hash": 0})
        if fac:
            participants.append(
                {
                    "id": fac["id"],
                    "name": f"{fac['first_name']} {fac['last_name']}",
                    "role": "facilitator",
                }
            )
            seen.add(fac["id"])
    for r in regs:
        if r["user_id"] in seen or r["user_id"] == user["id"]:
            continue
        u = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            participants.append(
                {"id": u["id"], "name": f"{u['first_name']} {u['last_name']}", "role": "participant"}
            )
            seen.add(u["id"])
    return participants


# ========== REVIEWS (moved to dedicated routers/reviews.py — universal polymorphic) ==========


# ========== IMPACT STATEMENTS ==========
@router.post("/impact-statements")
async def create_impact(data: ImpactStatementCreate, user: dict = Depends(get_current_user)):
    from database import db
    if not await _ensure_workshop_access(db, data.workshop_id, user, allow_facilitator=False, allow_admin=False):
        raise HTTPException(status_code=403, detail="Only registered participants can submit impact statements")
    existing = await db.impact_statements.find_one({"workshop_id": data.workshop_id, "user_id": user["id"]})
    payload = {
        "what_learned": data.what_learned,
        "how_grew": data.how_grew,
        "benefits": data.benefits,
        "improvements": data.improvements,
        "is_public": data.is_public,
        "anonymous": data.anonymous,
    }
    if existing:
        await db.impact_statements.update_one({"id": existing["id"]}, {"$set": payload})
        return await db.impact_statements.find_one({"id": existing["id"]}, {"_id": 0})
    stmt = {
        **data.model_dump(),
        "id": gen_id(),
        "user_id": user["id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "created_at": now_iso(),
    }
    await db.impact_statements.insert_one(stmt)
    stmt.pop("_id", None)
    return stmt


@router.get("/impact-statements")
async def list_impact(
    workshop_id: Optional[str] = None, public_only: bool = False, user: Optional[dict] = None
):
    from database import db
    query = {}
    if workshop_id:
        query["workshop_id"] = workshop_id
    if public_only:
        query["is_public"] = True
    items = await db.impact_statements.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for it in items:
        if it.get("anonymous"):
            it["user_name"] = "Anonymous Participant"
            it["user_id"] = None
    return items


@router.get("/impact-statements/mine")
async def my_impact_statements(user: dict = Depends(get_current_user)):
    from database import db
    items = await db.impact_statements.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


# ========== SUPPORT REQUESTS ==========
@router.post("/support-requests")
async def create_support(data: SupportRequestCreate, user: dict = Depends(get_current_user)):
    from database import db
    if not await _ensure_workshop_access(db, data.workshop_id, user, allow_facilitator=False, allow_admin=False):
        raise HTTPException(status_code=403, detail="Only registered participants can submit support requests")
    req = {
        **data.model_dump(),
        "id": gen_id(),
        "user_id": user["id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "status": "open",
        "response": None,
        "responded_by": None,
        "responded_at": None,
        "created_at": now_iso(),
    }
    await db.support_requests.insert_one(req)
    req.pop("_id", None)
    return req


@router.get("/support-requests")
async def list_support(
    workshop_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    from database import db
    query = {}
    if user["role"] == "participant":
        query["user_id"] = user["id"]
    elif user["role"] == "facilitator":
        # only their workshops
        my_workshops = await db.workshops.find({"facilitator_id": user["id"]}, {"id": 1, "_id": 0}).to_list(1000)
        ids = [w["id"] for w in my_workshops]
        query["workshop_id"] = {"$in": ids}
    # admin sees all
    if workshop_id:
        query["workshop_id"] = workshop_id
    items = await db.support_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return items


@router.post("/support-requests/{req_id}/respond")
async def respond_support(
    req_id: str, body: SupportResponse, user: dict = Depends(require_roles("facilitator", "admin"))
):
    from database import db
    sr = await db.support_requests.find_one({"id": req_id})
    if not sr:
        raise HTTPException(status_code=404, detail="Not found")
    if user["role"] == "facilitator":
        w = await db.workshops.find_one({"id": sr["workshop_id"]})
        if not w or w["facilitator_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not your workshop")
    await db.support_requests.update_one(
        {"id": req_id},
        {
            "$set": {
                "response": body.response,
                "status": "resolved",
                "responded_by": f"{user['first_name']} {user['last_name']}",
                "responded_at": now_iso(),
            }
        },
    )
    return {"success": True}
