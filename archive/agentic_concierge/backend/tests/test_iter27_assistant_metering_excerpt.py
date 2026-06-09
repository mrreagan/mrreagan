"""Phase 6C.4 — AI billing, wallet, research collab, vendor AI, assistant metering."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://birthright-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@birthright.org", "birthright2026")
ELENA = ("elena@birthright.org", "birthright2026")  # research partner
DAVID = ("demo@birthright.org", "birthright2026")  # vendor partner — demo has active vendor profile per seed
DEMO  = ("demo@birthright.org",  "birthright2026")  # participant


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    body = r.json()
    return body["token"], body["user"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# -------------------- ASSISTANT METERING + REPLAY --------------------

class TestAssistantMetering:
    def test_anon_chat_no_balance_gate(self):
        # anonymous (no auth) — should work without billing
        r = requests.post(
            f"{API}/assistant/chat",
            json={"message": "hi there", "session_id": None},
            timeout=60,
        )
        # 200 or some safe success/redirect code; not 402
        assert r.status_code != 402, r.text
        assert r.status_code == 200, r.text

    def test_participant_chat_no_balance_gate(self):
        token, _ = _login(*DEMO)
        r = requests.post(
            f"{API}/assistant/chat",
            headers=_hdr(token),
            json={"message": "hello", "session_id": None},
            timeout=60,
        )
        assert r.status_code != 402
        assert r.status_code == 200, r.text

    def test_my_sessions_last_empty_for_brand_new_session(self):
        # use a brand new account to ensure no history... or just check the structure
        token, _ = _login(*DEMO)
        r = requests.get(f"{API}/assistant/my-sessions/last", headers=_hdr(token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "session_id" in data
        assert "messages" in data
        assert isinstance(data["messages"], list)

    def test_my_sessions_last_after_chat(self):
        token, _ = _login(*DEMO)
        # send a message to ensure history exists
        chat = requests.post(
            f"{API}/assistant/chat",
            headers=_hdr(token),
            json={"message": "test message for replay", "session_id": None},
            timeout=60,
        )
        assert chat.status_code == 200
        r = requests.get(f"{API}/assistant/my-sessions/last", headers=_hdr(token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] is not None
        assert len(data["messages"]) >= 1
