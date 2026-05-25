"""Direct Messaging — Phase 6C.1.

Threads link two users where at least one has an active partner_profile.

Opt-in (cold-outreach) rules:
  - PartnerProfile.accepts_new_dms (default True for facilitator+community;
    False for research+vendor at seed time).
  - If the *recipient* of a brand-new thread has accepts_new_dms=False, the
    thread is created with status='pending'. The pending thread shows the
    opening message to the recipient, who can Accept (→ status='active') or
    Block (→ status='blocked'). Until accepted, the sender cannot post further
    messages.
  - Either party can subsequently archive (status='archived').

Ombudsman / privacy (matches user choice "2c"):
  - Admins see thread *metadata* (participants, timestamps, message counts)
    always.
  - Admins see message *bodies* only after a thread is flagged for review
    (`ombudsman_flagged=True`).

REST surface:
  POST   /api/dm/threads                       open or fetch a thread
  GET    /api/dm/threads                       my inbox
  GET    /api/dm/threads/{id}                  thread detail + messages
  POST   /api/dm/threads/{id}/messages         send message in an active thread
  POST   /api/dm/threads/{id}/accept           recipient accepts a pending thread
  POST   /api/dm/threads/{id}/block            recipient blocks a pending/active thread
  POST   /api/dm/threads/{id}/archive          either party archives
  POST   /api/dm/threads/{id}/flag             escalate to ombudsman
  POST   /api/dm/threads/{id}/read             mark up to last message as read
  PUT    /api/me/dm/preferences                toggle accepts_new_dms per partner profile
  GET    /api/admin/dm/threads                 admin metadata-only inbox
  GET    /api/admin/dm/threads/{id}            admin view (bodies only if flagged)

WS:
  /api/ws/dm/{thread_id}                       realtime delivery for thread participants
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status,
)

from auth_utils import COOKIE_NAME, decode_token, get_current_user, require_roles
from models import (
    DmAcceptsToggle, DmMessageCreate, DmThreadCreate, DmThreadFlag,
    gen_id, now_iso,
)
from utils.audit import log_action
from utils.ws_manager import Connection, dm_registry

logger = logging.getLogger("birthright.dm")

router = APIRouter(prefix="/dm", tags=["dm"])
my_prefs_router = APIRouter(prefix="/me/dm", tags=["dm"])
admin_router = APIRouter(prefix="/admin/dm", tags=["dm-admin"])
ws_router = APIRouter(tags=["dm-ws"])


# ============ HELPERS ============

async def _is_partner(db, user_id: str) -> bool:
    """At least one approved partner profile counts."""
    return await db.partner_profiles.find_one({"user_id": user_id, "status": "active"}) is not None


async def _recipient_accepts(db, user_id: str) -> bool:
    """A recipient 'accepts new DMs' if ANY of their active partner profiles has
    accepts_new_dms != False. Defaults to True if no explicit flag was ever set."""
    cursor = db.partner_profiles.find(
        {"user_id": user_id, "status": "active"},
        {"_id": 0, "accepts_new_dms": 1, "partner_type": 1},
    )
    any_profile = False
    async for p in cursor:
        any_profile = True
        if p.get("accepts_new_dms") is None:
            # default by type
            if p.get("partner_type") in ("facilitator", "community"):
                return True
        elif p["accepts_new_dms"] is True:
            return True
    # If no partner profile, fall back to True (the recipient is a regular user a partner is reaching out to)
    return not any_profile


async def _thread_for_pair(db, a: str, b: str) -> Optional[dict]:
    return await db.dm_threads.find_one(
        {"participants": {"$all": [a, b]}, "participants.2": {"$exists": False}},
        {"_id": 0},
    )


def _other_participant(thread: dict, user_id: str) -> str:
    return next(p for p in thread["participants"] if p != user_id)


def _thread_strip(t: dict) -> dict:
    """Sanitize thread document for response."""
    t.pop("_id", None)
    return t


async def _enrich_thread(db, thread: dict, viewer_id: str) -> dict:
    other_id = _other_participant(thread, viewer_id)
    other = await db.users.find_one(
        {"id": other_id},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "avatar_url": 1, "role": 1},
    ) or {"id": other_id}
    # Pull the most recent partner profile of the "other" user (for badging)
    other_profile = await db.partner_profiles.find_one(
        {"user_id": other_id, "status": "active"},
        {"_id": 0, "partner_type": 1, "display_name": 1, "slug": 1},
        sort=[("created_at", -1)],
    )
    unread_field = f"unread_{viewer_id}"
    return {
        **thread,
        "other_participant": {
            "id": other_id,
            "name": f"{other.get('first_name', '')} {other.get('last_name', '')}".strip() or "Birthright user",
            "avatar_url": other.get("avatar_url"),
            "role": other.get("role"),
            "partner_type": (other_profile or {}).get("partner_type"),
            "partner_display_name": (other_profile or {}).get("display_name"),
            "partner_slug": (other_profile or {}).get("slug"),
        },
        "unread_count": int(thread.get(unread_field, 0) or 0),
    }


# ============ THREADS ============

@router.post("/threads")
async def open_thread(data: DmThreadCreate, user: dict = Depends(get_current_user)):
    from database import db
    if data.recipient_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot DM yourself")
    recipient = await db.users.find_one({"id": data.recipient_id}, {"_id": 0, "id": 1})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # Eligibility — at least one side must be a partner
    sender_is_partner = await _is_partner(db, user["id"])
    recipient_is_partner = await _is_partner(db, data.recipient_id)
    if not (sender_is_partner or recipient_is_partner):
        raise HTTPException(status_code=403, detail="Direct messages require at least one Birthright partner")

    existing = await _thread_for_pair(db, user["id"], data.recipient_id)
    if existing:
        # Just return the existing thread (idempotent open). If initial_message is provided
        # AND thread is active, post it too.
        if data.initial_message and existing.get("status") == "active":
            await _persist_and_broadcast(
                db, existing, sender_id=user["id"], sender_name=_full_name(user),
                content=data.initial_message, share_url=data.share_url,
            )
            existing = await db.dm_threads.find_one({"id": existing["id"]}, {"_id": 0})
        return await _enrich_thread(db, _thread_strip(existing), user["id"])

    # New thread — accepts gate determines initial status
    accepts = await _recipient_accepts(db, data.recipient_id)
    initial_status = "active" if accepts else "pending"

    thread = {
        "id": gen_id(),
        "participants": sorted([user["id"], data.recipient_id]),  # canonical order
        "initiator_id": user["id"],
        "status": initial_status,
        "created_at": now_iso(),
        "last_message_at": None,
        "last_message_preview": "",
        "message_count": 0,
        f"unread_{user['id']}": 0,
        f"unread_{data.recipient_id}": 0,
        "ombudsman_flagged": False,
        "share_url": data.share_url,
    }
    await db.dm_threads.insert_one(dict(thread))
    if data.initial_message:
        await _persist_and_broadcast(
            db, thread, sender_id=user["id"], sender_name=_full_name(user),
            content=data.initial_message, share_url=data.share_url,
        )
    fresh = await db.dm_threads.find_one({"id": thread["id"]}, {"_id": 0})
    return await _enrich_thread(db, fresh, user["id"])


def _full_name(user: dict) -> str:
    return f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", "Birthright user")


async def _persist_and_broadcast(
    db, thread: dict, *, sender_id: str, sender_name: str, content: str, share_url: Optional[str] = None,
) -> dict:
    msg = {
        "id": gen_id(),
        "thread_id": thread["id"],
        "sender_id": sender_id,
        "sender_name": sender_name,
        "content": content[:4000],
        "share_url": share_url,
        "created_at": now_iso(),
        "read_by": [sender_id],
    }
    await db.dm_messages.insert_one(dict(msg))
    other_id = next(p for p in thread["participants"] if p != sender_id)
    await db.dm_threads.update_one(
        {"id": thread["id"]},
        {
            "$set": {
                "last_message_at": msg["created_at"],
                "last_message_preview": content[:160],
            },
            "$inc": {"message_count": 1, f"unread_{other_id}": 1},
        },
    )
    # Realtime broadcast (best-effort; recipients may be offline)
    try:
        room = await dm_registry.room_for(thread["id"])
        msg.pop("_id", None)
        await room.broadcast(
            {"type": "chat", "message": msg},
            sender_id=sender_id, recipient_id=None,  # both participants
        )
    except Exception as e:
        logger.debug(f"dm broadcast suppressed: {e}")
    return msg


@router.get("/threads")
async def list_my_threads(user: dict = Depends(get_current_user)):
    from database import db
    rows = await db.dm_threads.find(
        {"participants": user["id"], "status": {"$ne": "archived"}},
        {"_id": 0},
    ).sort("last_message_at", -1).to_list(200)
    return [await _enrich_thread(db, r, user["id"]) for r in rows]


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, user: dict = Depends(get_current_user)):
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]}, {"_id": 0})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = await db.dm_messages.find(
        {"thread_id": thread_id}, {"_id": 0},
    ).sort("created_at", 1).to_list(1000)
    enriched = await _enrich_thread(db, thread, user["id"])
    return {**enriched, "messages": messages}


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: str, data: DmMessageCreate, user: dict = Depends(get_current_user),
):
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread["status"] == "blocked":
        raise HTTPException(status_code=403, detail="Thread is blocked")
    if thread["status"] == "pending":
        # Only the recipient can post once (their acceptance often happens via a reply)
        if thread["initiator_id"] == user["id"]:
            raise HTTPException(status_code=403, detail="Waiting for recipient to accept your first message")
        # Acceptance via reply — flip to active
        await db.dm_threads.update_one({"id": thread_id}, {"$set": {"status": "active"}})
        thread["status"] = "active"
    msg = await _persist_and_broadcast(
        db, thread, sender_id=user["id"], sender_name=_full_name(user), content=data.content,
    )
    return msg


@router.post("/threads/{thread_id}/accept")
async def accept_thread(thread_id: str, user: dict = Depends(get_current_user)):
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Thread is {thread['status']}")
    if thread["initiator_id"] == user["id"]:
        raise HTTPException(status_code=403, detail="Only the recipient can accept")
    await db.dm_threads.update_one({"id": thread_id}, {"$set": {"status": "active", "accepted_at": now_iso()}})
    return await db.dm_threads.find_one({"id": thread_id}, {"_id": 0})


@router.post("/threads/{thread_id}/block")
async def block_thread(thread_id: str, user: dict = Depends(get_current_user)):
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread["initiator_id"] == user["id"]:
        raise HTTPException(status_code=403, detail="Only the recipient can block")
    await db.dm_threads.update_one(
        {"id": thread_id},
        {"$set": {"status": "blocked", "blocked_at": now_iso(), "blocked_by": user["id"]}},
    )
    return await db.dm_threads.find_one({"id": thread_id}, {"_id": 0})


@router.post("/threads/{thread_id}/archive")
async def archive_thread(thread_id: str, user: dict = Depends(get_current_user)):
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    await db.dm_threads.update_one(
        {"id": thread_id},
        {"$set": {"status": "archived", "archived_at": now_iso(), "archived_by": user["id"]}},
    )
    return {"archived": True}


@router.post("/threads/{thread_id}/flag")
async def flag_thread(
    thread_id: str, data: DmThreadFlag, user: dict = Depends(get_current_user),
):
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    flag_doc = {
        "flagged_by": user["id"],
        "flagged_at": now_iso(),
        "reason": data.reason.strip(),
    }
    await db.dm_threads.update_one(
        {"id": thread_id},
        {"$set": {
            "ombudsman_flagged": True,
            "ombudsman_flagged_at": now_iso(),
        },
         "$push": {"ombudsman_flags": flag_doc}},
    )
    await log_action(
        db, user, "dm.flag", target_type="dm_thread", target_id=thread_id,
        metadata={"reason_len": len(data.reason)},
    )
    return {"flagged": True}


@router.post("/threads/{thread_id}/read")
async def mark_read(thread_id: str, user: dict = Depends(get_current_user)):
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    field = f"unread_{user['id']}"
    await db.dm_threads.update_one({"id": thread_id}, {"$set": {field: 0}})
    # Also append user_id to read_by on unread messages (best-effort)
    await db.dm_messages.update_many(
        {"thread_id": thread_id, "read_by": {"$ne": user["id"]}},
        {"$addToSet": {"read_by": user["id"]}},
    )
    return {"read": True}


# ============ MY PREFERENCES ============

@my_prefs_router.put("/preferences")
async def update_dm_preferences(
    data: DmAcceptsToggle, user: dict = Depends(get_current_user),
):
    """Toggle `accepts_new_dms` across all of the caller's active partner profiles."""
    from database import db
    result = await db.partner_profiles.update_many(
        {"user_id": user["id"], "status": "active"},
        {"$set": {"accepts_new_dms": data.accepts_new_dms, "updated_at": now_iso()}},
    )
    return {"accepts_new_dms": data.accepts_new_dms, "profiles_updated": result.modified_count}


@my_prefs_router.get("/preferences")
async def get_dm_preferences(user: dict = Depends(get_current_user)):
    from database import db
    profiles = await db.partner_profiles.find(
        {"user_id": user["id"], "status": "active"},
        {"_id": 0, "partner_type": 1, "accepts_new_dms": 1},
    ).to_list(20)
    return profiles


# ============ ADMIN / OMBUDSMAN ============

@admin_router.get("/threads")
async def admin_list_threads(
    flagged_only: bool = False,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if flagged_only:
        query["ombudsman_flagged"] = True
    rows = await db.dm_threads.find(query, {"_id": 0}).sort("last_message_at", -1).to_list(500)
    # Always strip preview when not flagged
    for r in rows:
        if not r.get("ombudsman_flagged"):
            r["last_message_preview"] = "[hidden — not flagged]"
    return rows


@admin_router.get("/threads/{thread_id}")
async def admin_get_thread(thread_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id}, {"_id": 0})
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    # Always return metadata
    payload = {**thread}
    if thread.get("ombudsman_flagged"):
        messages = await db.dm_messages.find({"thread_id": thread_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)
        payload["messages"] = messages
    else:
        payload["messages"] = None
        payload["bodies_locked"] = True
    await log_action(
        db, user, "dm.admin_view", target_type="dm_thread", target_id=thread_id,
        metadata={"with_bodies": bool(thread.get("ombudsman_flagged"))},
    )
    return payload


# ============ WEBSOCKET ============

async def _ws_authenticate(websocket: WebSocket) -> Optional[dict]:
    token = websocket.cookies.get(COOKIE_NAME) or websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    from database import db
    return await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})


@ws_router.websocket("/ws/dm/{thread_id}")
async def dm_ws(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    user = await _ws_authenticate(websocket)
    if not user:
        await websocket.send_json({"type": "error", "detail": "Authentication required"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    from database import db
    thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]})
    if not thread:
        await websocket.send_json({"type": "error", "detail": "No access to this thread"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    room = await dm_registry.room_for(thread_id)
    conn = Connection(
        ws=websocket, user_id=user["id"],
        user_name=_full_name(user), user_role=user["role"],
    )
    await room.add(conn)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "typing":
                await room.broadcast(
                    {"type": "typing", "user_id": conn.user_id, "user_name": conn.user_name,
                     "is_typing": bool(data.get("is_typing"))},
                    sender_id=conn.user_id, recipient_id=None,
                )
            # Chat sends use the REST POST endpoint so we maintain consistent ACL +
            # accepts-gate logic. The REST path then broadcasts via this same room.
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"dm_ws error for user {user.get('id')}: {e}")
    finally:
        await room.remove(websocket)
        await dm_registry.drop_if_empty(thread_id)
