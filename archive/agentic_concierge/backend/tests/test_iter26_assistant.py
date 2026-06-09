"""Phase 6B.6 — AI Concierge / Agentic Assistant.

Covers:
  - /api/assistant/meta — returns model + allowed actions list (≥10, no forbidden).
  - /api/assistant/chat — anonymous + signed-in turns, parses action blocks,
    persists messages in db.assistant_messages.
  - /api/assistant/execute — runs auto-tier search_* + frontend directives,
    rejects forbidden actions, requires sign-in for write actions.
  - Action parser strips `<<ACTION>>` blocks from reply_text.
  - Forbidden action types are rejected at execute time even if injected.

Note: chat tests make real Claude calls (the playbook does not offer a stub).
Tests use BIRTHRIGHT_API_BASE override; default is local supervisor URL.
"""
from __future__ import annotations

import os
import uuid

import httpx
import pytest

BASE = os.environ.get("BIRTHRIGHT_API_BASE", "http://localhost:8001/api")
ADMIN_EMAIL = os.environ.get("BIRTHRIGHT_ADMIN_EMAIL", "admin@birthright.org")
ADMIN_PASS = os.environ.get("BIRTHRIGHT_ADMIN_PASS", "birthright2026")


def _login(email: str, password: str) -> str:
    r = httpx.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["token"]


def _h(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


# ============ META ============

def test_meta_endpoint_returns_actions():
    r = httpx.get(f"{BASE}/assistant/meta", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "model" in body
    assert "anthropic" in body["model"]
    types = {a["type"] for a in body["actions"]}
    # Spot-check that core actions are exposed and forbidden ones are NOT.
    assert "navigate" in types
    assert "file_dispute" in types
    assert "search_workshops" in types
    assert "checkout_payment" not in types
    assert "change_user_role" not in types
    assert "delete_account" not in types


# ============ CHAT ============

def test_anonymous_chat_returns_navigate_action():
    r = httpx.post(
        f"{BASE}/assistant/chat",
        json={
            "session_id": None,
            "message": "Take me to the partners list page",
            "page_context": {"path": "/", "title": "Home"},
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["session_id"].startswith("asst_")
    assert d["user_signed_in"] is False
    assert "<<ACTION>>" not in d["reply_text"]
    nav_actions = [a for a in d["proposed_actions"] if a["type"] == "navigate"]
    assert len(nav_actions) >= 1
    assert nav_actions[0]["params"].get("path", "").startswith("/partners")
    assert nav_actions[0]["tier"] == "auto"


def test_signed_in_chat_session_persists():
    tok = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = httpx.post(
        f"{BASE}/assistant/chat",
        json={
            "session_id": None,
            "message": "Hi! Where can I find research papers on attachment?",
            "page_context": {"path": "/", "title": "Home"},
        },
        headers=_h(tok),
        timeout=30,
    )
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert r.json()["user_signed_in"] is True

    # Pull the session — admin should be allowed.
    s = httpx.get(f"{BASE}/assistant/sessions/{sid}", headers=_h(tok), timeout=10)
    assert s.status_code == 200
    msgs = s.json()["messages"]
    # We sent 1 user, got 1 assistant reply persisted = 2 total
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_search_workshops_action_executes():
    """search_workshops is an auto-tier backend action. We execute it directly."""
    r = httpx.post(
        f"{BASE}/assistant/execute",
        json={
            "session_id": f"asst_{uuid.uuid4().hex}",
            "action_id": str(uuid.uuid4()),
            "action_type": "search_workshops",
            "params": {"query": "secure", "limit": 5},
        },
        timeout=10,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert isinstance(d["result"], list)


def test_navigate_action_returns_directive():
    """navigate is auto-tier + frontend-execute. Server returns a directive only."""
    r = httpx.post(
        f"{BASE}/assistant/execute",
        json={
            "session_id": f"asst_{uuid.uuid4().hex}",
            "action_id": str(uuid.uuid4()),
            "action_type": "navigate",
            "params": {"path": "/workshops"},
        },
        timeout=10,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["directive"] == {"type": "navigate", "params": {"path": "/workshops"}}
    assert d["result"] is None


def test_forbidden_action_rejected_at_execute():
    r = httpx.post(
        f"{BASE}/assistant/execute",
        json={
            "session_id": f"asst_{uuid.uuid4().hex}",
            "action_id": str(uuid.uuid4()),
            "action_type": "checkout_payment",
            "params": {"amount": 100},
        },
        timeout=10,
    )
    assert r.status_code == 403


def test_unknown_action_400():
    r = httpx.post(
        f"{BASE}/assistant/execute",
        json={
            "session_id": f"asst_{uuid.uuid4().hex}",
            "action_id": str(uuid.uuid4()),
            "action_type": "not_a_real_action",
            "params": {},
        },
        timeout=10,
    )
    assert r.status_code == 400


def test_write_action_requires_signin():
    """file_dispute needs a logged-in user → reflected as ok=false with detail."""
    r = httpx.post(
        f"{BASE}/assistant/execute",
        json={
            "session_id": f"asst_{uuid.uuid4().hex}",
            "action_id": str(uuid.uuid4()),
            "action_type": "file_dispute",
            "params": {"target_user_id": "x", "category": "service", "description": "test"},
        },
        timeout=10,
    )
    assert r.status_code == 200  # endpoint always returns 200 with ok flag
    d = r.json()
    assert d["ok"] is False
    assert "sign in" in str(d.get("error", "")).lower()


def test_admin_my_sessions_listing():
    tok = _login(ADMIN_EMAIL, ADMIN_PASS)
    # Seed at least one assistant message under admin
    httpx.post(
        f"{BASE}/assistant/chat",
        json={"session_id": None, "message": "Hello", "page_context": {"path": "/", "title": ""}},
        headers=_h(tok),
        timeout=30,
    )
    r = httpx.get(f"{BASE}/assistant/my-sessions", headers=_h(tok), timeout=10)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert "session_id" in rows[0]
