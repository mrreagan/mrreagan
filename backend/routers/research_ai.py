"""AI Research Collaborator — peer-level generative AI for research partners.

Phase 6C.4 (revised May 25, 2026 per founder direction: this is not a
secretary, it's a colleague). Two capability groups, all metered via
ai_billing at 1× passthrough:

  INQUIRY:
    - synthesize_literature(topic, lens, depth)
    - map_landscape(topic)
    - generate_questions(domain, current_understanding)
    - critique_methodology(draft_text)

  DRAFTING:
    - summarize_notes(notes, target_words)
    - suggest_tags(title, abstract)
    - polish_draft(text, style)

Every call is gated to an ACTIVE research partner profile and debits the
caller's AI wallet.
"""
from __future__ import annotations

import json
import logging
import os
import re

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from utils.ai_billing import record_usage, require_balance

load_dotenv()
logger = logging.getLogger("birthright.research_collab")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"
FEATURE = "research_collab"

router = APIRouter(prefix="/research-collab", tags=["research-collaborator"])


async def _require_research_partner(db, user: dict) -> dict | None:
    """Phase 6C.4 (revised May 28, 2026): Research Collaborator is open to ALL
    signed-in members, not just formal research partners. The function name is
    preserved so we don't churn callers; it now returns the partner profile if
    one exists, else None, but never raises. Access is implicitly gated by the
    `Depends(get_current_user)` on each endpoint.
    """
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": "research", "status": "active"}
    )
    return profile


async def _call_claude(system: str, user_text: str, session_suffix: str) -> tuple[str, int, int]:
    """Returns (reply_text, tokens_in_estimate, tokens_out_estimate)."""
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"research_collab_{session_suffix}",
        system_message=system,
    ).with_model(MODEL_PROVIDER, MODEL_NAME)
    reply = await chat.send_message(UserMessage(text=user_text))
    text = str(reply or "")
    tokens_in = (len(system) + len(user_text)) // 4
    tokens_out = len(text) // 4
    return text, tokens_in, tokens_out


def _strip_codefence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s


# A shared prefix that sets the COLLABORATOR posture for every system prompt.
COLLAB_PREAMBLE = (
    "You are a research collaborator working alongside a Birthright Foundation research "
    "partner. You have broad command of attachment theory, developmental psychology, "
    "family systems, intergenerational trauma, the neurobiology of stress and bonding, "
    "ethnographic studies of family formation and repair, and adjacent literatures. "
    "Your relationship with the user is peer-level — you bring synthesis, breadth, and "
    "pattern-recognition; the user brings local expertise, ethical judgment, and field "
    "experience. Never fabricate citations, named programs of research, or empirical "
    "claims. When you reference established work, name only authors and programs you "
    "are confident about. If the topic falls outside the platform's mission (attachment, "
    "family, relational repair, and adjacent), say so plainly and stop. "
)


# ============ INQUIRY: SYNTHESIZE LITERATURE ============

class SynthesizeRequest(BaseModel):
    topic: str = Field(min_length=4, max_length=600)
    lens: str = Field(default="", max_length=400)
    depth: str = Field(default="standard", pattern="^(brief|standard|deep)$")


@router.post("/synthesize-literature")
async def synthesize_literature(req: SynthesizeRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_research_partner(db, user)
    await require_balance(db, user, min_usd=0.01, feature="Research Collaborator")
    depth_brief = {
        "brief":    "Be concise. Aim for ~250 words total.",
        "standard": "Aim for ~600 words total.",
        "deep":     "Go thorough — up to ~1200 words. Earn the length.",
    }[req.depth]
    system = (
        COLLAB_PREAMBLE +
        "Synthesize the existing literature on the user's topic. Output Markdown with these "
        "exact sections in this order: `## Foundational frame`, `## Established findings`, "
        "`## Live debates`, `## Frontiers`, `## Suggested entry points`. "
        f"{depth_brief} "
        "Under each section use 2–7 tight bullets. Where appropriate, name named programs "
        "of research, schools of thought, or specific scholars — but only when accurate. "
        "If you don't know, say so explicitly rather than fabricate."
    )
    payload = f"Topic: {req.topic}"
    if req.lens.strip():
        payload += f"\nLens to prioritize: {req.lens.strip()}"
    reply, tin, tout = await _call_claude(system, payload, session_suffix=user["id"])
    event = await record_usage(
        db, user, feature=FEATURE, model=MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "synthesize_literature", "depth": req.depth},
    )
    return {"markdown": reply.strip(), "cost_usd": event["cost_usd"]}


# ============ INQUIRY: MAP THE LANDSCAPE ============

class MapRequest(BaseModel):
    topic: str = Field(min_length=4, max_length=600)


@router.post("/map-landscape")
async def map_landscape(req: MapRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_research_partner(db, user)
    await require_balance(db, user, min_usd=0.01, feature="Research Collaborator")
    system = (
        COLLAB_PREAMBLE +
        "Map the research landscape for the user's topic as STRICT JSON only — no preamble, "
        "no markdown, no codefence. Schema:\n"
        '{\n'
        '  "key_concepts":            [{"name": "string", "one_line": "string"}],\n'
        '  "seminal_works_or_authors": [{"name": "string", "era": "string", "why": "string"}],\n'
        '  "modern_voices":           [{"name": "string", "current_focus": "string"}],\n'
        '  "live_debates":            [{"label": "string", "sides": ["string", "string"]}],\n'
        '  "recent_shifts":           [{"shift": "string", "since": "string"}],\n'
        '  "adjacent_fields":         [{"field": "string", "what_they_add": "string"}]\n'
        '}\n'
        "5–8 items per array maximum. Omit any array you are unsure about rather than "
        'fabricate. If the topic is out-of-scope, return {"error": "topic_out_of_scope", '
        '"suggestion": "..."}.'
    )
    reply, tin, tout = await _call_claude(system, f"Topic: {req.topic}", session_suffix=user["id"])
    cleaned = _strip_codefence(reply)
    try:
        data = json.loads(cleaned)
    except Exception:
        data = {"error": "parse_failed", "raw": cleaned[:2000]}
    event = await record_usage(
        db, user, feature=FEATURE, model=MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "map_landscape"},
    )
    return {**data, "cost_usd": event["cost_usd"]}


# ============ INQUIRY: GENERATE RESEARCH QUESTIONS ============

class QuestionsRequest(BaseModel):
    domain: str = Field(min_length=4, max_length=600)
    current_understanding: str = Field(default="", max_length=6000)
    count: int = Field(default=6, ge=3, le=12)


@router.post("/generate-questions")
async def generate_questions(req: QuestionsRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_research_partner(db, user)
    await require_balance(db, user, min_usd=0.008, feature="Research Collaborator")
    system = (
        COLLAB_PREAMBLE +
        f"Generate {req.count} unanswered research questions in the user's domain that would "
        "be tractable for a small nonprofit research lab — NOT '30-year longitudinal study' "
        "questions, but real, surfaceable, novel inquiries a partner could pursue in 6–24 "
        "months. Output STRICT JSON only:\n"
        '{"questions": [{"question": "string", "why_underexplored": "string", '
        '"suggested_methods": ["string"], "natural_collaborators": ["string"], '
        '"feasibility": "low|medium|high"}]}'
    )
    payload = f"Domain: {req.domain}"
    if req.current_understanding.strip():
        payload += f"\nCurrent understanding the partner already holds:\n{req.current_understanding.strip()}"
    reply, tin, tout = await _call_claude(system, payload, session_suffix=user["id"])
    cleaned = _strip_codefence(reply)
    try:
        data = json.loads(cleaned)
    except Exception:
        data = {"questions": [], "raw": cleaned[:2000]}
    event = await record_usage(
        db, user, feature=FEATURE, model=MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "generate_questions", "count": req.count},
    )
    return {**data, "cost_usd": event["cost_usd"]}


# ============ INQUIRY: CRITIQUE METHODOLOGY ============

class CritiqueRequest(BaseModel):
    draft_text: str = Field(min_length=80, max_length=20000)
    focus: str = Field(default="full", pattern="^(full|methods_only|findings_only)$")


@router.post("/critique-methodology")
async def critique_methodology(req: CritiqueRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_research_partner(db, user)
    await require_balance(db, user, min_usd=0.015, feature="Research Collaborator")
    focus_brief = {
        "full":           "Cover both methods and findings.",
        "methods_only":   "Focus on methodological rigor; do not opine on the findings themselves.",
        "findings_only":  "Focus on the findings' robustness and alternative interpretations.",
    }[req.focus]
    system = (
        COLLAB_PREAMBLE +
        "Provide a careful, generous methodological critique. Output Markdown with these "
        "exact sections in this order: `## Strengths`, `## Methodological gaps`, "
        "`## Confounds and alternative explanations`, `## Suggested robustness checks`, "
        "`## Where I'd push next`. Be specific — reference passages in the draft when "
        "useful. Stay direct, warm, and concrete. Do not invent citations or claim the "
        f"existence of literature you can't anchor. {focus_brief}"
    )
    reply, tin, tout = await _call_claude(system, req.draft_text, session_suffix=user["id"])
    event = await record_usage(
        db, user, feature=FEATURE, model=MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "critique_methodology", "focus": req.focus},
    )
    return {"markdown": reply.strip(), "cost_usd": event["cost_usd"]}


# ============ DRAFTING: SUMMARIZE NOTES (was: draft_abstract) ============

class SummarizeRequest(BaseModel):
    notes: str = Field(min_length=20, max_length=20000)
    target_words: int = Field(default=180, ge=80, le=400)


@router.post("/summarize-notes")
async def summarize_notes(req: SummarizeRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_research_partner(db, user)
    await require_balance(db, user, min_usd=0.005, feature="Research Collaborator")
    system = (
        COLLAB_PREAMBLE +
        "Compress the user's working notes into an abstract-style summary. Output ONLY the "
        f"paragraph — no preamble, no headings, no markdown. Target ~{req.target_words} "
        "words. Aim for clarity, precision, and a neutral scholarly tone. Mention key "
        "constructs and headline findings only if they appear in the notes."
    )
    reply, tin, tout = await _call_claude(system, req.notes, session_suffix=user["id"])
    event = await record_usage(
        db, user, feature=FEATURE, model=MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "summarize_notes", "target_words": req.target_words},
    )
    return {"summary": reply.strip(), "cost_usd": event["cost_usd"]}


# ============ DRAFTING: SUGGEST TAGS ============

class SuggestTagsRequest(BaseModel):
    title: str = Field(min_length=3, max_length=400)
    abstract: str = Field(min_length=10, max_length=4000)


@router.post("/suggest-tags")
async def suggest_tags(req: SuggestTagsRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_research_partner(db, user)
    await require_balance(db, user, min_usd=0.001, feature="Research Collaborator")
    system = (
        COLLAB_PREAMBLE +
        "Suggest concise, lowercase, hyphenated tags and 1–3 broader categories for the "
        "user's research artifact. Return STRICT JSON only: "
        '{"tags": [...], "categories": [...]} — max 10 tags, max 3 categories.'
    )
    payload = f"Title: {req.title}\n\nAbstract: {req.abstract}"
    reply, tin, tout = await _call_claude(system, payload, session_suffix=user["id"])
    cleaned = _strip_codefence(reply)
    try:
        data = json.loads(cleaned)
    except Exception:
        data = {"tags": [], "categories": [], "raw": cleaned[:1000]}
    event = await record_usage(
        db, user, feature=FEATURE, model=MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "suggest_tags"},
    )
    return {**data, "cost_usd": event["cost_usd"]}


# ============ DRAFTING: POLISH DRAFT ============

class PolishDraftRequest(BaseModel):
    text: str = Field(min_length=20, max_length=20000)
    style: str = Field(default="academic", pattern="^(academic|plain|practitioner)$")


@router.post("/polish-draft")
async def polish_draft(req: PolishDraftRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_research_partner(db, user)
    await require_balance(db, user, min_usd=0.005, feature="Research Collaborator")
    style_brief = {
        "academic":     "Match an academic-journal voice — neutral, precise, citations-friendly.",
        "plain":        "Plain-language style — readable by an educated non-specialist.",
        "practitioner": "Clinician-practitioner voice — direct, applied, actionable.",
    }[req.style]
    system = (
        COLLAB_PREAMBLE +
        "Polish the user's draft for clarity, grammar, and flow. Do NOT add new claims, "
        "references, or data. Preserve the author's voice. "
        f"{style_brief} Return ONLY the polished text."
    )
    reply, tin, tout = await _call_claude(system, req.text, session_suffix=user["id"])
    event = await record_usage(
        db, user, feature=FEATURE, model=MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "polish_draft", "style": req.style},
    )
    return {"polished": reply.strip(), "cost_usd": event["cost_usd"]}
