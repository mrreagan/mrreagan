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


async def _handle_typing(room, conn: Connection, data: dict) -> None:
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


async def _handle_chat(
    websocket: WebSocket, room, conn: Connection, workshop_id: str, data: dict,
) -> None:
    content = (data.get("content") or "").strip()
    if not content:
        await websocket.send_json({"type": "error", "detail": "Empty message"})
        return
    if len(content) > MAX_CONTENT_LEN:
        await websocket.send_json({"type": "error", "detail": f"Message exceeds {MAX_CONTENT_LEN} chars"})
        return
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


async def _dispatch_message(
    websocket: WebSocket, room, conn: Connection, workshop_id: str, data: dict,
) -> None:
    """Route a single inbound payload to its handler. Unknown types emit an error frame."""
    msg_type = data.get("type")
    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})
    elif msg_type == "typing":
        await _handle_typing(room, conn, data)
    elif msg_type == "chat":
        await _handle_chat(websocket, room, conn, workshop_id, data)
    else:
        await websocket.send_json({"type": "error", "detail": f"Unknown message type: {msg_type}"})


async def _broadcast_presence(room, conn: Connection) -> None:
    """Broadcast the current room presence to everyone. Swallows broadcast errors."""
    try:
        await room.broadcast(
            {"type": "presence", "users": room.presence_snapshot()},
            sender_id=conn.user_id,
            recipient_id=None,
        )
    except Exception as e:  # pragma: no cover — best-effort presence
        logger.debug(f"presence broadcast suppressed: {e}")


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
    await _broadcast_presence(room, conn)

    try:
        while True:
            data = await websocket.receive_json()
            await _dispatch_message(websocket, room, conn, workshop_id, data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"chat_ws error for user {user.get('id')}: {e}")
    finally:
        await room.remove(websocket)
        await _broadcast_presence(room, conn)
        await registry.drop_if_empty(workshop_id)
