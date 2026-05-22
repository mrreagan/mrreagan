"""Real-time chat WebSocket endpoint.

Path:  /api/ws/chat/{workshop_id}
Auth:  reads `br_session` cookie from the WS handshake. If missing/invalid or the
       user is not a workshop attendee/facilitator/admin, the handshake is rejected
       with code 1008 (policy violation).

Client → Server payloads:
    { "type": "chat",   "content": "...", "recipient_id": "<user_id>" | null }
    { "type": "typing", "recipient_id": "<user_id>" | null, "is_typing": true|false }
    { "type": "ping" }

Server → Client payloads:
    { "type": "chat",     "message": {<chat doc>} }
    { "type": "typing",   "user_id": "...", "user_name": "...", "recipient_id": null | "...", "is_typing": true|false }
    { "type": "presence", "users": [{id,name,role}, ...] }
    { "type": "pong" }
    { "type": "error",    "detail": "..." }
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from auth_utils import COOKIE_NAME, decode_token
from models import gen_id, now_iso
from utils.ws_manager import Connection, registry

logger = logging.getLogger("birthright.chat_ws")
router = APIRouter(tags=["chat-ws"])

MAX_CONTENT_LEN = 4000


async def _authenticate(websocket: WebSocket) -> dict | None:
    """Return user dict if cookie auth succeeds, else None (caller closes 1008)."""
    token = websocket.cookies.get(COOKIE_NAME)
    if not token:
        # Some browsers / proxies put the cookie in headers oddly; second-chance from query string.
        token = websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    from database import db
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    return user


async def _can_access_workshop(workshop_id: str, user: dict) -> bool:
    from database import db
    if user.get("role") == "admin":
        return True
    w = await db.workshops.find_one({"id": workshop_id}, {"_id": 0, "facilitator_id": 1})
    if not w:
        return False
    if user.get("role") == "facilitator" and w.get("facilitator_id") == user["id"]:
        return True
    reg = await db.registrations.find_one(
        {"workshop_id": workshop_id, "user_id": user["id"], "payment_status": "paid"}
    )
    return bool(reg)


@router.websocket("/ws/chat/{workshop_id}")
async def chat_ws(websocket: WebSocket, workshop_id: str):
    await websocket.accept()
    user = await _authenticate(websocket)
    if not user:
        await websocket.send_json({"type": "error", "detail": "Authentication required"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if not await _can_access_workshop(workshop_id, user):
        await websocket.send_json({"type": "error", "detail": "No access to this workshop"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    room = await registry.room_for(workshop_id)
    conn = Connection(
        ws=websocket,
        user_id=user["id"],
        user_name=f"{user['first_name']} {user['last_name']}",
        user_role=user["role"],
    )
    await room.add(conn)
    # broadcast presence to everyone
    await room.broadcast(
        {"type": "presence", "users": room.presence_snapshot()},
        sender_id=conn.user_id,
        recipient_id=None,
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "typing":
                await room.broadcast(
                    {
                        "type": "typing",
                        "user_id": conn.user_id,
                        "user_name": conn.user_name,
                        "recipient_id": data.get("recipient_id"),
                        "is_typing": bool(data.get("is_typing")),
                    },
                    sender_id=conn.user_id,
                    recipient_id=data.get("recipient_id"),
                )
                continue

            if msg_type == "chat":
                content = (data.get("content") or "").strip()
                if not content:
                    await websocket.send_json({"type": "error", "detail": "Empty message"})
                    continue
                if len(content) > MAX_CONTENT_LEN:
                    await websocket.send_json({"type": "error", "detail": f"Message exceeds {MAX_CONTENT_LEN} chars"})
                    continue
                recipient_id = data.get("recipient_id") or None
                from database import db
                msg = {
                    "id": gen_id(),
                    "workshop_id": workshop_id,
                    "sender_id": conn.user_id,
                    "sender_name": conn.user_name,
                    "recipient_id": recipient_id,
                    "content": content,
                    "created_at": now_iso(),
                }
                await db.chat_messages.insert_one(msg)
                msg.pop("_id", None)
                await room.broadcast(
                    {"type": "chat", "message": msg},
                    sender_id=conn.user_id,
                    recipient_id=recipient_id,
                )
                continue

            await websocket.send_json({"type": "error", "detail": f"Unknown message type: {msg_type}"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"chat_ws error for user {user.get('id')}: {e}")
    finally:
        await room.remove(websocket)
        # broadcast updated presence
        try:
            await room.broadcast(
                {"type": "presence", "users": room.presence_snapshot()},
                sender_id=conn.user_id,
                recipient_id=None,
            )
        except Exception:
            pass
        await registry.drop_if_empty(workshop_id)
