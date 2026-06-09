"""Backend tests for the lightweight Help support assistant.

  - /api/help/voice returns greeting + starter prompts from KB
  - Common questions deflect from the KB (source='kb', cost=0)
  - Novel questions either return KB best-guess + escalate offer
    (when LLM key is absent in CI) or hit the LLM (source='llm')
  - /api/help/escalate creates a row and returns the human handoff message
  - KB scorer behaves: weights patterns over the noise of stop words
"""
from __future__ import annotations

import pathlib
import sys
import uuid

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from routers.help_assistant import _rank_kb, _tokens, DEFLECT_THRESHOLD  # noqa: E402

API_BASE = "http://localhost:8001/api"


@pytest_asyncio.fixture
async def db_handle():
    import os
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    yield db
    client.close()


# ---------- KB ranking unit tests ---------------------------------------
def test_kb_login_question_matches_login_entry():
    ranked = _rank_kb("how do I reset my password?")
    top_score, top = ranked[0]
    assert top["id"] == "login-magic-link"
    assert top_score >= DEFLECT_THRESHOLD


def test_kb_patches_question_matches_patches_entry():
    ranked = _rank_kb("where can I buy the leather patches?")
    assert ranked[0][1]["id"] == "patches"
    assert ranked[0][0] >= DEFLECT_THRESHOLD


def test_kb_tier_question_matches_artist_tiers():
    ranked = _rank_kb("how do artist tiers work?")
    assert ranked[0][1]["id"] == "artist-tiers"


def test_kb_tokenizer_drops_stop_words():
    t = _tokens("How do I sign in to the platform?")
    # Stop words gone; payload words present.
    assert "the" not in t
    assert "how" not in t
    assert "sign" in t
    assert "platform" in t


# ---------- Live HTTP — voice + chat + escalate -------------------------
@pytest.mark.asyncio
async def test_help_voice_endpoint():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/help/voice")
        assert r.status_code == 200
        body = r.json()
        assert body["agent_name"] == "Birthright Help"
        assert body["agent_label"] == "AI Agent"
        assert isinstance(body["starter_prompts"], list)
        assert len(body["starter_prompts"]) >= 3


@pytest.mark.asyncio
async def test_help_chat_kb_deflection_is_free(db_handle):
    """A common 'where can I buy patches' question must deflect to KB
    with zero cost — no LLM call."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.post("/help/chat",
                         json={"message": "where can I buy the leather patches?"})
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "kb"
        assert body["kb_id"] == "patches"
        assert body["cost_usd"] == 0.0
        # Persists session.
        sid = body["session_id"]
        assert sid


@pytest.mark.asyncio
async def test_help_chat_anon_llm_fallback_not_billed(db_handle):
    """Anonymous user: even when the LLM fallback fires for a novel
    question, no wallet debit because user is unauthenticated."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as c:
        r = await c.post("/help/chat",
                         json={"message": "do you offer parental leave for staff?"})
        assert r.status_code == 200
        body = r.json()
        assert body["source"] in ("llm", "kb")  # llm if key present, else kb fallback
        assert body["cost_usd"] == 0.0  # anon never billed


@pytest.mark.asyncio
async def test_help_session_persists_messages(db_handle):
    db = db_handle
    sid = f"test-help-{uuid.uuid4().hex[:8]}"
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        await c.post("/help/chat",
                     json={"message": "how do I sign in?", "session_id": sid})
        r = await c.get(f"/help/session/{sid}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == sid
        assert len(body.get("messages", [])) >= 2  # user + assistant
    # Cleanup
    await db.help_sessions.delete_one({"id": sid})


@pytest.mark.asyncio
async def test_help_escalate_creates_row(db_handle):
    db = db_handle
    sid = f"test-help-esc-{uuid.uuid4().hex[:8]}"
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        await c.post("/help/chat",
                     json={"message": "talk to a human", "session_id": sid})
        r = await c.post("/help/escalate",
                         json={"session_id": sid, "email": "test@example.com",
                                "note": "Need refund help"})
        assert r.status_code == 200
        assert r.json()["ok"] is True
    row = await db.help_escalations.find_one(
        {"session_id": sid}, {"_id": 0},
    )
    assert row is not None
    assert row["user_email"] == "test@example.com"
    assert row["status"] == "open"
    # Cleanup
    await db.help_sessions.delete_one({"id": sid})
    await db.help_escalations.delete_one({"session_id": sid})
