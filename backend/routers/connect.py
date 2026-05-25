"""Connect — Teams-style collaboration hub.

Phase 1 scope:
- Channels (public + role-gated private)
- Real-time messages via WebSocket (reuses ws_manager pattern)
- Member roster per channel
- Meeting scheduling with ICS calendar invite download

Routes:
    GET    /api/connect/channels                  List channels visible to user
    POST   /api/connect/channels                  Create channel (admin only)
    GET    /api/connect/channels/{id}             Channel detail incl. member list
    GET    /api/connect/channels/{id}/messages    Last N messages (default 100)
    POST   /api/connect/channels/{id}/messages    Post message (also broadcasts via WS)
    POST   /api/connect/channels/{id}/join        Join a public/role-eligible channel
    POST   /api/connect/channels/{id}/leave       Leave channel
    GET    /api/connect/channels/{id}/meetings    List upcoming meetings
    POST   /api/connect/channels/{id}/meetings    Create meeting (member or admin)
    GET    /api/connect/meetings/{id}/ics         Download .ics calendar file (public)
    WS     /api/ws/connect/{channel_id}           Real-time message stream
"""
from __future__ import annotations

import logging
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth_utils import get_current_user, COOKIE_NAME, decode_token
from models import gen_id, now_iso
from utils.ws_manager import Connection, ChatRoomRegistry

logger = logging.getLogger("birthright.connect")
router = APIRouter(prefix="/connect", tags=["connect"])
ws_router = APIRouter(tags=["connect-ws"])

# Singleton registry for connect channel WS rooms (separate from workshop chat).
connect_registry = ChatRoomRegistry()

MAX_CONTENT_LEN = 4000
ChannelType = Literal["public", "role_gated"]
ChannelRole = Literal["all", "facilitators", "partners", "alumni", "admins"]


# ============ Models ============
class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=64)
    slug: str = Field(..., min_length=2, max_length=40)
    description: str = Field("", max_length=400)
    type: ChannelType = "public"
    role_required: ChannelRole = "all"  # only relevant when type == "role_gated"
    is_announcement_only: bool = False  # only admins can post


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LEN)


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=140)
    description: str = Field("", max_length=1000)
    start_iso: str  # ISO 8601 datetime
    end_iso: str
    location: str = Field("", max_length=240)


# ============ Helpers ============
def _user_role_buckets(user: dict) -> set[str]:
    """All role buckets a user belongs to for channel-access checks."""
    buckets = {"all"}
    role = user.get("role", "")
    if role == "admin":
        buckets.update({"admins", "facilitators", "partners", "alumni"})
    if role == "facilitator":
        buckets.add("facilitators")
    if user.get("is_partner") or role == "partner":
        buckets.add("partners")
    if user.get("is_alumni"):
        buckets.add("alumni")
    return buckets


async def _user_can_access(channel: dict, user: dict) -> bool:
    if user.get("role") == "admin":
        return True
    if channel.get("type") == "public":
        return True
    return channel.get("role_required", "all") in _user_role_buckets(user)


async def _seed_default_channels(db) -> None:
    """Idempotently create the starter channel set."""
    defaults = [
        {"name": "Announcements", "slug": "announcements", "description": "Foundation-wide announcements from the team.", "type": "public", "role_required": "all", "is_announcement_only": True},
        {"name": "General", "slug": "general", "description": "Open conversation for everyone in the Birthright community.", "type": "public", "role_required": "all", "is_announcement_only": False},
        {"name": "Alumni", "slug": "alumni", "description": "Workshop graduates — keep the practice alive.", "type": "role_gated", "role_required": "alumni", "is_announcement_only": False},
        {"name": "Facilitators", "slug": "facilitators", "description": "Private channel for certified facilitators.", "type": "role_gated", "role_required": "facilitators", "is_announcement_only": False},
        {"name": "Partners", "slug": "partners", "description": "Private channel for partners (vendors, research, community).", "type": "role_gated", "role_required": "partners", "is_announcement_only": False},
    ]
    for d in defaults:
        existing = await db.connect_channels.find_one({"slug": d["slug"]})
        if existing:
            continue
        await db.connect_channels.insert_one({
            "id": gen_id(),
            "slug": d["slug"],
            "name": d["name"],
            "description": d["description"],
            "type": d["type"],
            "role_required": d["role_required"],
            "is_announcement_only": d["is_announcement_only"],
            "created_by": "system",
            "created_at": now_iso(),
        })


# ============ Endpoints — Channels ============
@router.get("/channels")
async def list_channels(user: dict = Depends(get_current_user)):
    from database import db
    await _seed_default_channels(db)
    channels = await db.connect_channels.find({}, {"_id": 0}).sort("created_at", 1).to_list(200)
    visible = [c for c in channels if await _user_can_access(c, user)]
    # attach last_message_at + unread sentinel (simple "latest activity" feel)
    for c in visible:
        last = await db.connect_messages.find_one(
            {"channel_id": c["id"]}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)]
        )
        c["last_message_at"] = last["created_at"] if last else None
        c["message_count"] = await db.connect_messages.count_documents({"channel_id": c["id"]})
    return visible


@router.post("/channels", status_code=201)
async def create_channel(body: ChannelCreate, user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Only admins can create channels in Phase 1.")
    from database import db
    if await db.connect_channels.find_one({"slug": body.slug}):
        raise HTTPException(400, "A channel with this slug already exists.")
    doc = {
        "id": gen_id(),
        "slug": body.slug.lower().replace(" ", "-"),
        "name": body.name.strip(),
        "description": body.description.strip(),
        "type": body.type,
        "role_required": body.role_required if body.type == "role_gated" else "all",
        "is_announcement_only": body.is_announcement_only,
        "created_by": user["id"],
        "created_at": now_iso(),
    }
    await db.connect_channels.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str, user: dict = Depends(get_current_user)):
    from database import db
    c = await db.connect_channels.find_one({"id": channel_id}, {"_id": 0})
    if not c:
        c = await db.connect_channels.find_one({"slug": channel_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Channel not found")
    if not await _user_can_access(c, user):
        raise HTTPException(403, "This channel is restricted.")
    return c


@router.get("/channels/{channel_id}/messages")
async def list_messages(channel_id: str, limit: int = 100, user: dict = Depends(get_current_user)):
    from database import db
    c = await db.connect_channels.find_one({"id": channel_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Channel not found")
    if not await _user_can_access(c, user):
        raise HTTPException(403, "This channel is restricted.")
    limit = max(1, min(limit, 500))
    cursor = db.connect_messages.find({"channel_id": c["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit)
    rows = await cursor.to_list(limit)
    rows.reverse()  # oldest -> newest for UI
    return rows


@router.post("/channels/{channel_id}/messages", status_code=201)
async def post_message(channel_id: str, body: MessageCreate, user: dict = Depends(get_current_user)):
    from database import db
    c = await db.connect_channels.find_one({"id": channel_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Channel not found")
    if not await _user_can_access(c, user):
        raise HTTPException(403, "This channel is restricted.")
    if c.get("is_announcement_only") and user.get("role") != "admin":
        raise HTTPException(403, "Only admins can post to this announcements channel.")
    msg = {
        "id": gen_id(),
        "channel_id": c["id"],
        "sender_id": user["id"],
        "sender_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", "Member"),
        "sender_role": user.get("role", "member"),
        "content": body.content.strip(),
        "created_at": now_iso(),
    }
    await db.connect_messages.insert_one(msg)
    msg.pop("_id", None)
    # broadcast to any open WS connections on this channel
    room = await connect_registry.room_for(c["id"])
    await room.broadcast(
        {"type": "chat", "message": msg},
        sender_id=user["id"],
        recipient_id=None,
    )
    return msg


@router.get("/channels/{channel_id}/members")
async def list_members(channel_id: str, user: dict = Depends(get_current_user)):
    """Distinct posters in this channel + currently-connected presence."""
    from database import db
    c = await db.connect_channels.find_one({"id": channel_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Channel not found")
    if not await _user_can_access(c, user):
        raise HTTPException(403, "This channel is restricted.")
    poster_ids = await db.connect_messages.distinct("sender_id", {"channel_id": c["id"]})
    poster_ids = poster_ids[:200]
    posters = []
    if poster_ids:
        rows = await db.users.find(
            {"id": {"$in": poster_ids}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "role": 1, "avatar_url": 1},
        ).to_list(len(poster_ids))
        posters = rows
    room = await connect_registry.room_for(c["id"])
    online = room.presence_snapshot()
    return {"posters": posters, "online": online}


# ============ Endpoints — Meetings ============
@router.get("/channels/{channel_id}/meetings")
async def list_meetings(channel_id: str, user: dict = Depends(get_current_user)):
    from database import db
    c = await db.connect_channels.find_one({"id": channel_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Channel not found")
    if not await _user_can_access(c, user):
        raise HTTPException(403, "This channel is restricted.")
    meetings = await db.connect_meetings.find(
        {"channel_id": c["id"]}, {"_id": 0}
    ).sort("start_iso", 1).to_list(200)
    return meetings


@router.post("/channels/{channel_id}/meetings", status_code=201)
async def create_meeting(channel_id: str, body: MeetingCreate, user: dict = Depends(get_current_user)):
    from database import db
    c = await db.connect_channels.find_one({"id": channel_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Channel not found")
    if not await _user_can_access(c, user):
        raise HTTPException(403, "This channel is restricted.")
    doc = {
        "id": gen_id(),
        "channel_id": c["id"],
        "title": body.title.strip(),
        "description": body.description.strip(),
        "start_iso": body.start_iso,
        "end_iso": body.end_iso,
        "location": body.location.strip(),
        "organizer_id": user["id"],
        "organizer_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        "created_at": now_iso(),
    }
    await db.connect_meetings.insert_one(doc)
    doc.pop("_id", None)

    # Auto-post a system message announcing the meeting
    msg = {
        "id": gen_id(),
        "channel_id": c["id"],
        "sender_id": user["id"],
        "sender_name": doc["organizer_name"] or "Member",
        "sender_role": user.get("role", "member"),
        "content": f"📅 Scheduled a meeting: \"{doc['title']}\" — {doc['start_iso']}",
        "meeting_id": doc["id"],
        "created_at": now_iso(),
    }
    await db.connect_messages.insert_one(msg)
    msg.pop("_id", None)
    room = await connect_registry.room_for(c["id"])
    await room.broadcast({"type": "chat", "message": msg}, sender_id=user["id"], recipient_id=None)
    return doc


@router.get("/meetings/{meeting_id}/ics")
async def meeting_ics(meeting_id: str):
    """Public ICS download. Anyone with the link can add to their calendar."""
    from database import db
    from utils.calendar_qr import build_ics
    m = await db.connect_meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Meeting not found")
    ics_bytes = build_ics({
        "title": m["title"],
        "start_date": m["start_iso"],
        "end_date": m["end_iso"],
        "location_name": m.get("location", ""),
        "location_address": "",
        "short_description": m.get("description", ""),
    })
    safe_name = "".join(ch for ch in m["title"] if ch.isalnum() or ch in "-_").lower()[:48] or "meeting"
    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.ics"'},
    )


# ============ WebSocket ============
async def _ws_authenticate(websocket: WebSocket) -> Optional[dict]:
    token = websocket.cookies.get(COOKIE_NAME) or websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    from database import db
    return await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})


@ws_router.websocket("/ws/connect/{channel_id}")
async def connect_ws(websocket: WebSocket, channel_id: str):
    await websocket.accept()
    user = await _ws_authenticate(websocket)
    if not user:
        await websocket.send_json({"type": "error", "detail": "Authentication required"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    from database import db
    c = await db.connect_channels.find_one({"id": channel_id}, {"_id": 0})
    if not c:
        await websocket.send_json({"type": "error", "detail": "Channel not found"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if not await _user_can_access(c, user):
        await websocket.send_json({"type": "error", "detail": "No access to this channel"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    room = await connect_registry.room_for(c["id"])
    conn = Connection(
        ws=websocket,
        user_id=user["id"],
        user_name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", "Member"),
        user_role=user.get("role", "member"),
    )
    await room.add(conn)
    await room.broadcast({"type": "presence", "users": room.presence_snapshot()}, sender_id=user["id"], recipient_id=None)

    try:
        while True:
            data = await websocket.receive_json()
            t = data.get("type")
            if t == "ping":
                await websocket.send_json({"type": "pong"})
            elif t == "typing":
                await room.broadcast(
                    {"type": "typing", "user_id": conn.user_id, "user_name": conn.user_name, "is_typing": bool(data.get("is_typing"))},
                    sender_id=user["id"],
                    recipient_id=None,
                )
            # message posting goes through the REST endpoint so it persists; WS just broadcasts.
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"connect_ws error for user {user.get('id')}: {e}")
    finally:
        await room.remove(websocket)
        try:
            await room.broadcast({"type": "presence", "users": room.presence_snapshot()}, sender_id=user["id"], recipient_id=None)
        except Exception:
            pass
        await connect_registry.drop_if_empty(c["id"])
