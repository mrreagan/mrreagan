"""birthright Help — lightweight support assistant.

Design goals: minimal token spend. Every turn flows through:

  1. KB-first deflection: lexical match against `data/help_kb.json`.
     If the top entry scores above DEFLECT_THRESHOLD we return the
     curated answer verbatim — zero LLM tokens. This handles the long
     tail of repeatable account/platform questions.

  2. LLM fallback only when KB is uncertain: a single Claude Haiku 4.5
     turn with a compressed system prompt + the top-2 KB snippets as
     context + last 3 conversation turns. Output capped at 250 tokens.

  3. Per-message billing: if the user is signed in and the turn did
     hit the LLM, we debit their AI wallet via `record_usage`. Anonymous
     turns and KB-only deflections are free (Foundation absorbs cost).

Public endpoints (mounted at /api/help):
  - POST /chat            → main conversational turn
  - GET  /session/{id}    → recall a saved conversation
  - POST /escalate        → user-initiated human handoff
"""
from __future__ import annotations

import json
import logging
import math
import os
import pathlib
import re
from typing import Optional

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth_utils import get_current_user_optional
from models import gen_id, now_iso
from utils.ai_billing import record_usage

load_dotenv()
logger = logging.getLogger("birthright.help")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
# Haiku 4.5 — cheapest Claude tier; ~3.75× cheaper than Sonnet.
HELP_MODEL = "claude-haiku-4-5-20251001"

# Lexical matching tuning.
DEFLECT_THRESHOLD = 0.55       # KB-only answer above this score
LLM_INJECT_TOP_K = 2           # how many KB entries to inject as context

# Hard cost guards.
MAX_OUTPUT_TOKENS = 250        # cap output every turn
MAX_HISTORY_TURNS = 3          # last 3 user/assistant pairs only
MAX_USER_CHARS = 1500          # truncate over-long messages

router = APIRouter(prefix="/help", tags=["help"])

_KB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "help_kb.json"
_KB_CACHE: dict | None = None


def _kb() -> dict:
    """Load the KB once into memory. Re-read if the file mtime changes
    so editors can hot-update content without a restart."""
    global _KB_CACHE
    try:
        mtime = _KB_PATH.stat().st_mtime
    except FileNotFoundError:
        return {"entries": [], "voice": {}}
    if _KB_CACHE and _KB_CACHE.get("_mtime") == mtime:
        return _KB_CACHE
    with _KB_PATH.open() as f:
        data = json.load(f)
    data["_mtime"] = mtime
    _KB_CACHE = data
    return data


_WORD_RE = re.compile(r"[a-z0-9']+")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "have", "has", "had", "i", "you", "we", "they", "he", "she", "it",
    "my", "your", "our", "their", "this", "that", "these", "those", "but",
    "if", "then", "so", "what", "how", "why", "where", "when", "who",
    "can", "could", "should", "would", "will", "may", "might",
}


def _tokens(s: str) -> set[str]:
    return {t for t in _WORD_RE.findall((s or "").lower()) if t not in _STOP and len(t) > 1}


def _score_entry(qtoks: set[str], entry: dict, q_lower: str) -> float:
    """Cheap lexical similarity:
       1. PHRASE boost — if any KB pattern occurs as a substring inside
          the question, that's a strong intent signal and dominates.
       2. Otherwise weighted token overlap (recall-leaning) against
          tags + patterns + first 300 chars of the answer.
    No embeddings, no provider call."""
    if not qtoks:
        return 0.0

    # Phrase substring boost — caps the entry at a high score so phrase
    # intent (e.g. "sign in") dominates loose token overlap from another
    # entry (e.g. workshops' "sign up for workshop").
    patterns = [p.lower() for p in entry.get("patterns", [])]
    for pat in patterns:
        # Require pattern to be >= 2 informative tokens for the phrase
        # boost, so we don't trigger on single-word patterns.
        if len(pat.split()) >= 2 and pat in q_lower:
            return 0.95

    blob = " ".join([
        " ".join(entry.get("tags", [])),
        " ".join(entry.get("patterns", [])),
        " ".join(entry.get("patterns", [])),         # patterns weighted ×2
        entry.get("answer", "")[:300],
    ])
    et = _tokens(blob)
    if not et:
        return 0.0
    overlap = len(qtoks & et)
    if overlap == 0:
        return 0.0
    recall = overlap / max(1, len(qtoks))
    precision = overlap / max(1, math.sqrt(len(et)))
    return round(0.7 * recall + 0.3 * precision, 4)


def _rank_kb(question: str) -> list[tuple[float, dict]]:
    qtoks = _tokens(question)
    q_lower = (question or "").lower()
    scored = [(_score_entry(qtoks, e, q_lower), e) for e in _kb().get("entries", [])]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


# ============ Schemas ============
class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None


class ChatOut(BaseModel):
    session_id: str
    reply: str
    follow_up: Optional[str] = None
    source: str                    # "kb" | "llm" | "kb_greet"
    kb_id: Optional[str] = None
    suggestions: list[str] = []
    cost_usd: float = 0.0          # what we billed this turn (0 if anon/KB)
    escalate_offer: bool = False
    tokens_in: int = 0
    tokens_out: int = 0


class EscalateIn(BaseModel):
    session_id: str
    email: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=2000)


# ============ Endpoints ============
@router.get("/voice")
async def get_voice():
    """Public — fetch the greeting + agent label so the frontend can
    render the welcome message without an extra LLM round-trip."""
    v = _kb().get("voice", {})
    return {
        "agent_name": v.get("name", "birthright Help"),
        "agent_label": v.get("agent_label", "AI Agent"),
        "greeting": v.get("greeting", "Hi there. How can I help?"),
        "starter_prompts": [
            "How do I sign in?",
            "Where can I buy the patches?",
            "How do artist tiers work?",
            "Talk to a human",
        ],
    }


def _save_messages(db, session_id: str, user_id: Optional[str],
                   user_msg: str, assistant_msg: str, source: str,
                   kb_id: Optional[str], cost_usd: float) -> None:
    """Append both sides of the turn to the session doc; create on first turn."""
    return db.help_sessions.update_one(
        {"id": session_id},
        {"$setOnInsert": {
            "id": session_id,
            "user_id": user_id,
            "created_at": now_iso(),
        },
         "$set": {"updated_at": now_iso()},
         "$inc": {"turns": 1, "total_cost_usd": cost_usd},
         "$push": {"messages": {
             "$each": [
                 {"role": "user", "content": user_msg, "at": now_iso()},
                 {"role": "assistant", "content": assistant_msg,
                  "source": source, "kb_id": kb_id, "at": now_iso()},
             ],
         }}},
        upsert=True,
    )


@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn,
               user: Optional[dict] = Depends(get_current_user_optional)):
    """Main turn handler. KB-deflection-first → LLM fallback."""
    from database import db
    msg = body.message.strip()[:MAX_USER_CHARS]
    session_id = body.session_id or gen_id()

    # ─── KB-first deflection ────────────────────────────────────────
    ranked = _rank_kb(msg)
    top_score, top_entry = (ranked[0] if ranked else (0.0, None))

    if top_entry and top_score >= DEFLECT_THRESHOLD:
        reply = top_entry["answer"]
        follow_up = top_entry.get("follow_up_label")
        kb_id = top_entry.get("id")
        await _save_messages(db, session_id, user["id"] if user else None,
                             msg, reply, "kb", kb_id, 0.0)
        return ChatOut(
            session_id=session_id, reply=reply, follow_up=follow_up,
            source="kb", kb_id=kb_id, cost_usd=0.0,
            escalate_offer=kb_id in ("contact-human", "delete-account",
                                      "refund-policy"),
        )

    # ─── LLM fallback (low-confidence KB OR completely novel question) ──
    if not EMERGENT_LLM_KEY:
        # No LLM available — graceful KB-best-guess + escalation offer.
        fallback = (top_entry["answer"] if top_entry
                    else _kb().get("voice", {}).get("fallback",
                          "I'm not sure about that one — want me to flag it for a human?"))
        await _save_messages(db, session_id, user["id"] if user else None,
                             msg, fallback, "kb", None, 0.0)
        return ChatOut(session_id=session_id, reply=fallback,
                       source="kb", escalate_offer=True)

    # Compact system prompt — kept short on purpose.
    voice = _kb().get("voice", {})
    snippets = [e for s, e in ranked[:LLM_INJECT_TOP_K] if s > 0]
    snippet_block = "\n".join(
        f"[{i+1}] {e['id']}: {e['answer']}" for i, e in enumerate(snippets)
    ) or "(none)"
    sys_prompt = (
        "You are birthright Help — a warm, plainspoken AI support agent for "
        "birthright.live, a Foundation that publishes practitioner research, "
        "runs workshops, and supports an artist economy.\n\n"
        f"VOICE: {voice.get('tone', 'warm, plainspoken')}\n"
        "RULES:\n"
        "- Answer in 2–4 short sentences. No fluff.\n"
        "- If the answer lives in the KB snippets below, use that wording.\n"
        "- If you don't know, say so and offer to flag a human "
        "(support@birthright.live).\n"
        "- End with one short follow-up question like 'Did that answer your question?'\n"
        "- Never make up URLs, prices, or policies.\n\n"
        f"KB SNIPPETS:\n{snippet_block}"
    )

    # Pull short conversation history for context.
    sess = await db.help_sessions.find_one(
        {"id": session_id}, {"_id": 0, "messages": 1},
    )
    history = (sess or {}).get("messages", [])[-(MAX_HISTORY_TURNS * 2):]
    history_text = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in history)
    user_payload = (
        (f"Recent conversation:\n{history_text}\n\n" if history_text else "")
        + f"User: {msg}"
    )

    try:
        chat_client = (LlmChat(api_key=EMERGENT_LLM_KEY,
                               session_id=session_id,
                               system_message=sys_prompt)
                       .with_model("anthropic", HELP_MODEL)
                       .with_params(max_tokens=MAX_OUTPUT_TOKENS))
        reply_text = await chat_client.send_message(UserMessage(text=user_payload))
        reply_text = (reply_text or "").strip()
    except Exception as exc:
        logger.exception("Help LLM call failed: %s", exc)
        fallback = (top_entry["answer"] if top_entry
                    else voice.get("fallback",
                          "I'm having trouble reaching the AI right now — "
                          "email support@birthright.live and we'll respond personally."))
        await _save_messages(db, session_id, user["id"] if user else None,
                             msg, fallback, "kb", None, 0.0)
        return ChatOut(session_id=session_id, reply=fallback,
                       source="kb", escalate_offer=True)

    # Rough token accounting (Haiku tokenizer ≈ 4 chars/token).
    tokens_in = max(50, (len(sys_prompt) + len(user_payload)) // 4)
    tokens_out = max(20, len(reply_text) // 4)

    cost = 0.0
    if user:
        try:
            ev = await record_usage(
                db, user, feature="help", model=HELP_MODEL,
                tokens_in=tokens_in, tokens_out=tokens_out,
                meta={"session_id": session_id},
            )
            cost = ev.get("cost_usd", 0.0)
        except Exception as exc:
            logger.warning("Help billing failed: %s", exc)

    await _save_messages(db, session_id, user["id"] if user else None,
                         msg, reply_text, "llm", None, cost)
    return ChatOut(
        session_id=session_id, reply=reply_text, source="llm",
        cost_usd=cost, tokens_in=tokens_in, tokens_out=tokens_out,
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str,
                      user: Optional[dict] = Depends(get_current_user_optional)):
    """Recall the messages for a session. Anyone holding the session_id can
    read it (it's a UUID and lives only in the holder's localStorage)."""
    from database import db
    s = await db.help_sessions.find_one({"id": session_id}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.post("/escalate")
async def escalate(body: EscalateIn, request: Request,
                   user: Optional[dict] = Depends(get_current_user_optional)):
    """Mark the session for human follow-up. We don't auto-email yet —
    the admin Help inbox surfaces escalations and a human team member
    responds from support@birthright.live."""
    from database import db
    s = await db.help_sessions.find_one({"id": body.session_id}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Session not found")
    await db.help_escalations.insert_one({
        "id": gen_id(),
        "session_id": body.session_id,
        "user_id": user["id"] if user else None,
        "user_email": (user or {}).get("email") or body.email,
        "note": (body.note or "").strip(),
        "status": "open",
        "created_at": now_iso(),
    })
    return {
        "ok": True,
        "message": _kb().get("voice", {}).get(
            "human_handoff",
            "Flagged for a human — they'll be in touch within one business day."),
    }
