"""Per-workshop chat WebSocket room manager.

Each workshop_id has a set of active WebSocket connections, each tagged with the
authenticated user_id so the server can apply DM filtering (only deliver a private
message to the sender + named recipient sockets).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("birthright.ws")


class Connection:
    __slots__ = ("ws", "user_id", "user_name", "user_role")

    def __init__(self, ws: WebSocket, user_id: str, user_name: str, user_role: str):
        self.ws = ws
        self.user_id = user_id
        self.user_name = user_name
        self.user_role = user_role


class WorkshopRoom:
    def __init__(self):
        self.connections: list[Connection] = []
        self._lock = asyncio.Lock()

    async def add(self, conn: Connection) -> None:
        async with self._lock:
            self.connections.append(conn)

    async def remove(self, ws: WebSocket) -> None:
        async with self._lock:
            self.connections = [c for c in self.connections if c.ws is not ws]

    def _targets(self, sender_id: str, recipient_id: str | None) -> list[Connection]:
        if not recipient_id:
            return list(self.connections)  # group: everyone in the room
        # DM: any socket for the sender OR recipient (a user could be connected from 2 tabs)
        return [c for c in self.connections if c.user_id in (sender_id, recipient_id)]

    async def broadcast(self, payload: dict[str, Any], sender_id: str, recipient_id: str | None) -> None:
        targets = self._targets(sender_id, recipient_id)
        dead: list[WebSocket] = []
        for c in targets:
            try:
                await c.ws.send_json(payload)
            except Exception as e:
                logger.debug(f"ws send failed for {c.user_id}: {e}")
                dead.append(c.ws)
        for ws in dead:
            await self.remove(ws)

    def presence_snapshot(self) -> list[dict[str, str]]:
        """Distinct online users in this room (collapses multi-tab)."""
        seen: dict[str, dict[str, str]] = {}
        for c in self.connections:
            seen[c.user_id] = {"id": c.user_id, "name": c.user_name, "role": c.user_role}
        return list(seen.values())


class ChatRoomRegistry:
    def __init__(self):
        self._rooms: dict[str, WorkshopRoom] = {}
        self._lock = asyncio.Lock()

    async def room_for(self, workshop_id: str) -> WorkshopRoom:
        async with self._lock:
            r = self._rooms.get(workshop_id)
            if r is None:
                r = WorkshopRoom()
                self._rooms[workshop_id] = r
            return r

    async def drop_if_empty(self, workshop_id: str) -> None:
        async with self._lock:
            r = self._rooms.get(workshop_id)
            if r and not r.connections:
                self._rooms.pop(workshop_id, None)


# singleton — workshop chat rooms
registry = ChatRoomRegistry()
# singleton — DM threads (reuses WorkshopRoom semantics; key is dm thread id)
dm_registry = ChatRoomRegistry()
