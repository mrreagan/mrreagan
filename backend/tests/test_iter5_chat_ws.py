"""Iteration 5: Chat WebSocket end-to-end tests.

Covers: auth (valid/invalid/no-access), facilitator+admin access, group chat,
DM filtering (3-client), typing, ping/pong, validation, presence-on-disconnect.

REST chat endpoints (history + send) are smoke-checked at the end.
"""
import asyncio
import json
import os
import re

import pytest
import requests
import websockets

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://birthright-hub.preview.emergentagent.com").rstrip("/")
WS_BASE = re.sub(r"^http", "ws", BASE_URL)
WORKSHOP_SLUG = "foundations-of-secure-bonds"
PASSWORD = os.environ.get("BIRTHRIGHT_TEST_PASSWORD", "birthright2026")


# ----------------- helpers -----------------
def login(email: str) -> tuple[str, dict]:
    """Return (br_session token, user dict)."""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data["token"], data["user"]


def get_workshop_id(slug: str) -> str:
    r = requests.get(f"{BASE_URL}/api/workshops", params={"slug": slug}, timeout=20)
    assert r.status_code == 200
    for w in r.json():
        if w["slug"] == slug:
            return w["id"]
    raise AssertionError(f"workshop {slug} not found")


async def ws_connect(workshop_id: str, token: str | None, use_query: bool = False):
    url = f"{WS_BASE}/api/ws/chat/{workshop_id}"
    headers = []
    if token and not use_query:
        headers = [("Cookie", f"br_session={token}")]
    if token and use_query:
        url += f"?token={token}"
    return await websockets.connect(url, additional_headers=headers, open_timeout=10, ping_interval=None)


async def recv_one(ws, timeout=5):
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def drain(ws, want_type, timeout=5, max_msgs=10):
    """Read messages until we find one whose .type matches want_type, returning it.

    Also returns the list of intermediate messages we saw.
    """
    seen = []
    for _ in range(max_msgs):
        msg = await recv_one(ws, timeout=timeout)
        seen.append(msg)
        if msg.get("type") == want_type:
            return msg, seen
    raise AssertionError(f"did not see {want_type} in {seen}")


async def expect_no_message(ws, timeout=1.5):
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
        raise AssertionError(f"unexpected message on socket: {msg}")
    except asyncio.TimeoutError:
        return None


# ----------------- fixtures -----------------
@pytest.fixture(scope="module")
def workshop_id():
    return get_workshop_id(WORKSHOP_SLUG)


@pytest.fixture(scope="module")
def demo_creds():
    return login("demo@birthright.org")


@pytest.fixture(scope="module")
def elena_creds():
    return login("elena@birthright.org")


@pytest.fixture(scope="module")
def admin_creds():
    return login("admin@birthright.org")


@pytest.fixture(scope="module")
def marcus_creds():
    # Marcus facilitates 'Repair' workshop, not Foundations → no access via facilitator route
    return login("marcus@birthright.org")


# ======================= 1. AUTH =======================
class TestWsAuth:
    @pytest.mark.asyncio
    async def test_valid_cookie_paid_participant_gets_presence(self, workshop_id, demo_creds):
        token, user = demo_creds
        ws = await ws_connect(workshop_id, token)
        try:
            msg = await recv_one(ws)
            assert msg["type"] == "presence", f"first message should be presence, got {msg}"
            assert isinstance(msg["users"], list)
            assert any(u["id"] == user["id"] for u in msg["users"])
        finally:
            await ws.close()

    @pytest.mark.asyncio
    async def test_missing_cookie_rejected(self, workshop_id):
        ws = await ws_connect(workshop_id, token=None)
        try:
            msg = await recv_one(ws)
            assert msg.get("type") == "error"
            assert "Authentication" in msg.get("detail", "")
            # next should be a close
            with pytest.raises(websockets.ConnectionClosed) as ei:
                await asyncio.wait_for(ws.recv(), timeout=3)
            assert ei.value.code == 1008
        finally:
            try: await ws.close()
            except Exception: pass

    @pytest.mark.asyncio
    async def test_invalid_cookie_rejected(self, workshop_id):
        # Deliberately malformed value to exercise rejection path. Not a real credential.
        ws = await ws_connect(workshop_id, token="bogus-value")
        try:
            msg = await recv_one(ws)
            assert msg.get("type") == "error"
            with pytest.raises(websockets.ConnectionClosed) as ei:
                await asyncio.wait_for(ws.recv(), timeout=3)
            assert ei.value.code == 1008
        finally:
            try: await ws.close()
            except Exception: pass

    @pytest.mark.asyncio
    async def test_user_without_paid_registration_rejected(self, workshop_id, marcus_creds):
        # Marcus is a facilitator but NOT of Foundations workshop and has no paid reg → should be 1008.
        token, _ = marcus_creds
        ws = await ws_connect(workshop_id, token)
        try:
            msg = await recv_one(ws)
            assert msg.get("type") == "error"
            assert "access" in msg.get("detail", "").lower()
            with pytest.raises(websockets.ConnectionClosed) as ei:
                await asyncio.wait_for(ws.recv(), timeout=3)
            assert ei.value.code == 1008
        finally:
            try: await ws.close()
            except Exception: pass

    @pytest.mark.asyncio
    async def test_facilitator_of_workshop_allowed(self, workshop_id, elena_creds):
        token, _ = elena_creds
        ws = await ws_connect(workshop_id, token)
        try:
            msg = await recv_one(ws)
            assert msg["type"] == "presence"
        finally:
            await ws.close()

    @pytest.mark.asyncio
    async def test_admin_allowed_any_workshop(self, workshop_id, admin_creds):
        token, _ = admin_creds
        ws = await ws_connect(workshop_id, token)
        try:
            msg = await recv_one(ws)
            assert msg["type"] == "presence"
        finally:
            await ws.close()

    @pytest.mark.asyncio
    async def test_token_query_param_fallback(self, workshop_id, demo_creds):
        token, _ = demo_creds
        ws = await ws_connect(workshop_id, token, use_query=True)
        try:
            msg = await recv_one(ws)
            assert msg["type"] == "presence"
        finally:
            await ws.close()


# ======================= 2. CHAT / DM / TYPING / PING =======================
class TestWsMessaging:
    @pytest.mark.asyncio
    async def test_group_chat_broadcasts_to_all_and_persists(self, workshop_id, demo_creds, elena_creds):
        a_tok, a_user = demo_creds
        b_tok, b_user = elena_creds
        ws_a = await ws_connect(workshop_id, a_tok)
        ws_b = await ws_connect(workshop_id, b_tok)
        try:
            # drain initial presence on both
            await drain(ws_a, "presence")
            await drain(ws_b, "presence")
            # b might receive presence again when a was already in; drain extra non-chat
            content = f"TEST_group_{os.urandom(4).hex()}"
            await ws_a.send(json.dumps({"type": "chat", "content": content, "recipient_id": None}))
            msg_a, _ = await drain(ws_a, "chat", timeout=6)
            msg_b, _ = await drain(ws_b, "chat", timeout=6)
            for m in (msg_a, msg_b):
                assert m["message"]["content"] == content
                assert m["message"]["recipient_id"] in (None,)
                assert m["message"]["sender_id"] == a_user["id"]
            # Verify persistence via REST history
            r = requests.get(
                f"{BASE_URL}/api/chat",
                params={"workshop_id": workshop_id},
                cookies={"br_session": a_tok},
                timeout=15,
            )
            assert r.status_code == 200
            assert any(x["content"] == content for x in r.json())
        finally:
            await ws_a.close(); await ws_b.close()

    @pytest.mark.asyncio
    async def test_dm_filtering_three_clients(self, workshop_id, demo_creds, elena_creds, admin_creds):
        a_tok, a_user = demo_creds
        b_tok, b_user = elena_creds
        c_tok, c_user = admin_creds
        ws_a = await ws_connect(workshop_id, a_tok)
        ws_b = await ws_connect(workshop_id, b_tok)
        ws_c = await ws_connect(workshop_id, c_tok)
        try:
            for w in (ws_a, ws_b, ws_c):
                await drain(w, "presence")
            # drain any extra presence updates
            for w in (ws_a, ws_b, ws_c):
                try: await asyncio.wait_for(w.recv(), timeout=0.5)
                except asyncio.TimeoutError: pass
            content = f"TEST_dm_{os.urandom(4).hex()}"
            await ws_b.send(json.dumps({"type": "chat", "content": content, "recipient_id": a_user["id"]}))
            msg_a, _ = await drain(ws_a, "chat", timeout=6)
            msg_b, _ = await drain(ws_b, "chat", timeout=6)
            assert msg_a["message"]["content"] == content
            assert msg_a["message"]["recipient_id"] == a_user["id"]
            assert msg_a["message"]["sender_id"] == b_user["id"]
            assert msg_b["message"]["content"] == content
            # C should NOT receive this DM
            await expect_no_message(ws_c, timeout=1.5)
        finally:
            await ws_a.close(); await ws_b.close(); await ws_c.close()

    @pytest.mark.asyncio
    async def test_typing_broadcast_group(self, workshop_id, demo_creds, elena_creds):
        a_tok, a_user = demo_creds
        b_tok, b_user = elena_creds
        ws_a = await ws_connect(workshop_id, a_tok)
        ws_b = await ws_connect(workshop_id, b_tok)
        try:
            await drain(ws_a, "presence"); await drain(ws_b, "presence")
            # drain any extra presence
            for w in (ws_a, ws_b):
                try: await asyncio.wait_for(w.recv(), timeout=0.4)
                except asyncio.TimeoutError: pass
            await ws_a.send(json.dumps({"type": "typing", "is_typing": True, "recipient_id": None}))
            msg, _ = await drain(ws_b, "typing", timeout=4)
            assert msg["user_id"] == a_user["id"]
            assert msg["is_typing"] is True
            assert msg["recipient_id"] is None
        finally:
            await ws_a.close(); await ws_b.close()

    @pytest.mark.asyncio
    async def test_ping_pong(self, workshop_id, demo_creds):
        token, _ = demo_creds
        ws = await ws_connect(workshop_id, token)
        try:
            await drain(ws, "presence")
            await ws.send(json.dumps({"type": "ping"}))
            msg, _ = await drain(ws, "pong", timeout=4)
            assert msg["type"] == "pong"
        finally:
            await ws.close()

    @pytest.mark.asyncio
    async def test_empty_content_rejected(self, workshop_id, demo_creds):
        token, _ = demo_creds
        ws = await ws_connect(workshop_id, token)
        try:
            await drain(ws, "presence")
            await ws.send(json.dumps({"type": "chat", "content": "   ", "recipient_id": None}))
            msg, _ = await drain(ws, "error", timeout=4)
            assert "Empty" in msg["detail"]
        finally:
            await ws.close()

    @pytest.mark.asyncio
    async def test_oversize_content_rejected(self, workshop_id, demo_creds):
        token, _ = demo_creds
        ws = await ws_connect(workshop_id, token)
        try:
            await drain(ws, "presence")
            big = "x" * 4100
            await ws.send(json.dumps({"type": "chat", "content": big, "recipient_id": None}))
            msg, _ = await drain(ws, "error", timeout=4)
            assert "4000" in msg["detail"]
        finally:
            await ws.close()


# ======================= 3. PRESENCE ON DISCONNECT =======================
class TestWsPresence:
    @pytest.mark.asyncio
    async def test_presence_updates_on_disconnect(self, workshop_id, demo_creds, elena_creds):
        a_tok, a_user = demo_creds
        b_tok, b_user = elena_creds
        ws_a = await ws_connect(workshop_id, a_tok)
        ws_b = await ws_connect(workshop_id, b_tok)
        try:
            await drain(ws_a, "presence")
            p_b_first, _ = await drain(ws_b, "presence")
            # B might immediately also receive presence triggered by A's earlier-still join — drain a couple if any
            # Now A disconnects → B should receive an updated presence broadcast not containing A.
            await ws_a.close()
            # Collect presence frames for up to ~3s and validate the last seen one has no A
            last_users = p_b_first["users"]
            deadline = asyncio.get_event_loop().time() + 4
            saw_drop = False
            while asyncio.get_event_loop().time() < deadline:
                try:
                    msg = await asyncio.wait_for(ws_b.recv(), timeout=1.5)
                except asyncio.TimeoutError:
                    break
                m = json.loads(msg)
                if m.get("type") == "presence":
                    last_users = m["users"]
                    if not any(u["id"] == a_user["id"] for u in last_users):
                        saw_drop = True
                        break
            assert saw_drop, f"never saw presence drop A; last={last_users}"
        finally:
            try: await ws_b.close()
            except Exception: pass


# ======================= 4. REST chat smoke =======================
class TestRestChatStillWorks:
    def test_get_history(self, workshop_id, demo_creds):
        tok, _ = demo_creds
        r = requests.get(
            f"{BASE_URL}/api/chat",
            params={"workshop_id": workshop_id},
            cookies={"br_session": tok},
            timeout=15,
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_post_message_rest(self, workshop_id, demo_creds):
        tok, _ = demo_creds
        content = f"TEST_rest_{os.urandom(3).hex()}"
        r = requests.post(
            f"{BASE_URL}/api/chat",
            json={"workshop_id": workshop_id, "content": content, "recipient_id": None},
            cookies={"br_session": tok},
            timeout=15,
        )
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body["content"] == content
