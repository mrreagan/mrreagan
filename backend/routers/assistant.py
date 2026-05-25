"""Birthright AI Concierge — site-wide agentic assistant (Phase 6B.6).

Architecture:
  - Backend wraps Claude Sonnet 4.5 via emergentintegrations.LlmChat.
  - System prompt embeds the full site map, user role, and the structured
    "action proposal" protocol the LLM uses to request agentic actions.
  - Claude emits actions inside `<<ACTION>>{...json}<<END>>` blocks. The
    backend strips them out of the reply text and returns them as a
    `proposed_actions[]` array so the frontend can render confirmation cards.
  - On user confirm, the frontend POSTs to /api/assistant/execute, which
    runs the action server-side OR returns a directive for the frontend to
    execute (e.g., `navigate`). Every action is audit-logged.
  - Forbidden actions (final payment, role changes, account deletion) are
    rejected at the executor layer regardless of LLM intent.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user_optional, get_current_user
from models import gen_id, now_iso
from utils.audit import log_action

load_dotenv()

logger = logging.getLogger("birthright.assistant")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"

router = APIRouter(prefix="/assistant", tags=["assistant"])

ACTION_BLOCK_RE = re.compile(r"<<ACTION>>(.*?)<<END>>", re.DOTALL)


# ============ ACTION REGISTRY ============

# Each action describes:
#   tier:        "auto"     → frontend executes without confirmation (safe)
#                "confirm"  → frontend renders a confirm card first
#                "forbidden"→ server refuses to execute regardless of LLM intent
#   execute:     "frontend" → server returns the directive, frontend acts
#                "backend"  → server performs the action and returns a result
ACTIONS: dict[str, dict] = {
    # ----- Tier "auto" / frontend-executed -----
    "navigate":        {"tier": "auto", "execute": "frontend",
                         "label": "Navigate to a page"},
    "prefill_form":    {"tier": "auto", "execute": "frontend",
                         "label": "Pre-fill form fields"},
    "scroll_to":       {"tier": "auto", "execute": "frontend",
                         "label": "Scroll to a section"},
    "open_modal":      {"tier": "auto", "execute": "frontend",
                         "label": "Open a UI modal"},
    # ----- Tier "auto" / backend search & lookup -----
    "search_workshops":{"tier": "auto", "execute": "backend",
                         "label": "Search workshops"},
    "search_products": {"tier": "auto", "execute": "backend",
                         "label": "Search shop products"},
    "search_partners": {"tier": "auto", "execute": "backend",
                         "label": "Search partners"},
    "search_research": {"tier": "auto", "execute": "backend",
                         "label": "Search research"},
    "lookup_my_subscriptions": {"tier": "auto", "execute": "backend",
                         "label": "Look up your active subscriptions"},
    "lookup_my_registrations": {"tier": "auto", "execute": "backend",
                         "label": "Look up your workshop registrations"},
    # ----- Tier "confirm" / backend write actions -----
    "add_to_cart":     {"tier": "confirm", "execute": "frontend",
                         "label": "Add a product to your cart"},
    "register_for_workshop": {"tier": "confirm", "execute": "frontend",
                         "label": "Start workshop registration (you'll complete payment yourself)"},
    "send_dm":         {"tier": "confirm", "execute": "backend",
                         "label": "Send a direct message"},
    "file_dispute":    {"tier": "confirm", "execute": "backend",
                         "label": "File a dispute"},
    "submit_research_draft": {"tier": "confirm", "execute": "backend",
                         "label": "Save a research artifact draft"},
    "submit_partner_application": {"tier": "confirm", "execute": "backend",
                         "label": "Submit a partner application"},
    "cancel_my_subscription": {"tier": "confirm", "execute": "backend",
                         "label": "Cancel one of your subscriptions"},
    "sign_agreement":  {"tier": "confirm", "execute": "backend",
                         "label": "Sign the active Partnership Agreement"},
    "bookmark":        {"tier": "confirm", "execute": "backend",
                         "label": "Bookmark this item"},
    # ----- Tier "forbidden" -----
    "checkout_payment":     {"tier": "forbidden", "execute": "none",
                              "label": "Run final payment"},
    "change_user_role":     {"tier": "forbidden", "execute": "none",
                              "label": "Change a user role"},
    "delete_account":       {"tier": "forbidden", "execute": "none",
                              "label": "Delete an account"},
}


# ============ SYSTEM PROMPT ============

SYSTEM_PROMPT_TEMPLATE = """You are the Birthright Foundation AI Concierge — a warm, concise site guide for the platform at birthright.live.

THE PLATFORM (one paragraph summary):
Birthright is a nonprofit foundation. We run attachment-focused workshops, sell related merch + workshop materials, and host a network of partners across four roles: Facilitators (run workshops), Vendors (sell curated merch), Community (refer new people), and Research (publish briefs + papers). Every payment side-effect (workshop seat, subscription, featured slot) can be cleanly refunded with a cascade that also reverses partner commissions. Partners must sign Agreement v2 before opening DMs, filing disputes, or subscribing.

USER CONTEXT (refreshed every turn):
{user_context}

CURRENT PAGE:
{page_context}

SITE MAP (key public + signed-in routes):
  /                — Home
  /workshops       — Upcoming workshops list
  /workshops/{{slug}} — Workshop detail + registration
  /shop            — Merch + workshop materials
  /shop/{{id}}      — Product detail
  /cart, /checkout/success
  /partners        — Public partner directory
  /partners/{{slug}}, /partners/apply
  /sponsorship     — 5 gemstone tiers + freeform donation
  /research        — Research library (briefs + papers)
  /facilitators    — Public facilitator list
  /about, /mission, /education, /governance, /contact, /join-us
  /login, /register, /forgot-password
  /dashboard       — Participant home
  /dashboard/workshops, /dashboard/orders, /dashboard/bookmarks
  /dashboard/messages, /dashboard/disputes, /dashboard/reports
  /dashboard/partner/* — partner-only pages (research, payouts, sales, featured, subscribe)
  /facilitator    — Facilitator dashboard
  /admin/*        — Admin-only (users, workshops, products, partners, payouts,
                    subscriptions, refunds, research, ombudsman, governance, etc.)
  /legal/agreement — Partnership Agreement v2

HOW YOU HELP:
1. Be brief. Two short sentences is often perfect.
2. When the user asks where something is, *navigate them there* via an action instead of just describing.
3. When the user wants to do something the platform supports, *do it for them* (with a confirm step for any write action).
4. If you don't know an answer, say so and suggest the best human contact (hello@birthright.live or the Contact page).
5. Never invent partner names, prices, dates, or workshop details. If you need data, call a search_* action and use the result.

AGENTIC ACTIONS:
You can propose actions for the user. Emit each action as a JSON object inside a single line wrapped by `<<ACTION>>` and `<<END>>` markers. Multiple actions are allowed per reply. Each action has:
  - `type`:   one of the allowed types below
  - `params`: object — the action's parameters
  - `label`:  short human-readable summary shown on the confirm card

Allowed action types (tier in parens):
{action_list}

Action contracts (param schemas):
  navigate              params={{ "path": "/some/route" }}
  prefill_form          params={{ "form_id": "string", "values": {{...}} }}
  scroll_to             params={{ "element_id": "string" }}
  open_modal            params={{ "modal_id": "string", "params": {{...}} }}
  search_workshops      params={{ "query": "string", "limit": int }}
  search_products       params={{ "query": "string", "limit": int }}
  search_partners       params={{ "query": "string", "partner_type": "facilitator|vendor|community|research|all", "limit": int }}
  search_research       params={{ "query": "string", "limit": int }}
  lookup_my_subscriptions params={{}}
  lookup_my_registrations params={{}}
  add_to_cart           params={{ "product_id": "string", "quantity": int }}
  register_for_workshop params={{ "workshop_id": "string" }}
  send_dm               params={{ "thread_id": "string", "content": "string" }}
  file_dispute          params={{ "target_user_id": "string", "category": "billing|conduct|fraud|service", "description": "string" }}
  submit_research_draft params={{ "title": "string", "abstract": "string", "authors": "string", "publication_date": "YYYY-MM-DD", "full_text_url": "string", "tier": "brief|paper" }}
  submit_partner_application params={{ "partner_type": "facilitator|vendor|community|research", "display_name": "string", "headline": "string", "bio": "string" }}
  cancel_my_subscription params={{ "subscription_id": "string" }}
  sign_agreement        params={{}}
  bookmark              params={{ "subject_type": "workshop|product|research|partner|facilitator", "subject_id": "string", "label": "optional string" }}

EXAMPLE:
User: "Take me to the November attachment workshop"
You: "Heading to the Workshops list now — I'll filter to November.
<<ACTION>>{{"type":"navigate","params":{{"path":"/workshops"}},"label":"Open the Workshops list"}}<<END>>"

User: "Help me file a dispute against vendor Quiet Hours Studio for an unfilled order"
You: "I can file that for you. Here's the draft — review and confirm:
<<ACTION>>{{"type":"file_dispute","params":{{"target_user_id":"vendor:quiet-hours-studio","category":"service","description":"Order not fulfilled within the stated window."}},"label":"File a service dispute against Quiet Hours Studio"}}<<END>>"

NEVER propose these (refused server-side regardless):
  - Final Stripe payment
  - Changing anyone's role
  - Deleting an account

KEEP your chat reply concise (≤120 words usually). The user can always ask follow-ups.
"""


def _build_system_prompt(user: Optional[dict], page_context: dict) -> str:
    if user:
        uc = (f"Signed in as {user.get('first_name','')} {user.get('last_name','')} "
              f"({user.get('email','')}) — role: {user.get('role','user')}.")
        if user.get("is_ombudsman"):
            uc += " Also serves as ombudsman."
    else:
        uc = "Visitor is NOT signed in. Most write actions require sign-in — direct them to /login or /register."
    page_str = (
        f"Path: {page_context.get('path','/')}\n"
        f"Title: {page_context.get('title','')}\n"
        f"Notes: {page_context.get('notes','')}"
    )
    action_lines = []
    for k, meta in ACTIONS.items():
        if meta["tier"] == "forbidden":
            continue
        action_lines.append(f"  - {k}  ({meta['tier']}) — {meta['label']}")
    return SYSTEM_PROMPT_TEMPLATE.format(
        user_context=uc,
        page_context=page_str,
        action_list="\n".join(action_lines),
    )


# ============ CHAT ============

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, max_length=80)
    message: str = Field(min_length=1, max_length=4000)
    page_context: dict = Field(default_factory=dict)


class ProposedAction(BaseModel):
    id: str
    type: str
    params: dict
    label: str
    tier: str            # "auto" | "confirm"
    execute: str         # "frontend" | "backend"


class ChatResponse(BaseModel):
    session_id: str
    reply_text: str
    proposed_actions: list[ProposedAction]
    user_signed_in: bool


def _parse_actions(raw_reply: str) -> tuple[str, list[ProposedAction]]:
    actions: list[ProposedAction] = []
    cleaned = raw_reply
    for m in ACTION_BLOCK_RE.finditer(raw_reply):
        body = m.group(1).strip()
        try:
            data = json.loads(body)
        except Exception:
            logger.warning("Could not parse action block: %s", body[:200])
            continue
        atype = data.get("type")
        meta = ACTIONS.get(atype)
        if not meta or meta["tier"] == "forbidden":
            logger.info("Dropping disallowed action: %s", atype)
            continue
        actions.append(ProposedAction(
            id=str(uuid.uuid4()),
            type=atype,
            params=data.get("params") or {},
            label=(data.get("label") or meta["label"])[:200],
            tier=meta["tier"],
            execute=meta["execute"],
        ))
    cleaned = ACTION_BLOCK_RE.sub("", cleaned).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, actions


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: Optional[dict] = Depends(get_current_user_optional)):
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="Assistant not configured (missing EMERGENT_LLM_KEY)")
    from database import db
    session_id = req.session_id or f"asst_{uuid.uuid4().hex}"

    # Persist user turn
    await db.assistant_messages.insert_one({
        "id": gen_id(),
        "session_id": session_id,
        "user_id": (user or {}).get("id"),
        "role": "user",
        "content": req.message,
        "page_context": req.page_context,
        "created_at": now_iso(),
    })

    # Replay prior turns into LlmChat for continuity.
    prior = await db.assistant_messages.find(
        {"session_id": session_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)

    system_prompt = _build_system_prompt(user, req.page_context)
    chat_client = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model(MODEL_PROVIDER, MODEL_NAME)

    # Re-send earlier USER messages to rebuild context (LlmChat handles history).
    # Skip the just-stored turn (we'll send it as the live message below).
    user_turns = [m for m in prior if m["role"] == "user"][:-1]
    for m in user_turns:
        try:
            await chat_client.send_message(UserMessage(text=m["content"]))
        except Exception as e:
            logger.warning("Replay turn failed (ignoring): %s", e)

    try:
        raw_reply = await chat_client.send_message(UserMessage(text=req.message))
    except Exception as e:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"Assistant temporarily unavailable: {e}") from e

    reply_text, proposed = _parse_actions(str(raw_reply or ""))

    # Persist assistant turn (with parsed actions for replay/audit)
    await db.assistant_messages.insert_one({
        "id": gen_id(),
        "session_id": session_id,
        "user_id": (user or {}).get("id"),
        "role": "assistant",
        "content": reply_text,
        "proposed_actions": [a.model_dump() for a in proposed],
        "created_at": now_iso(),
    })

    return ChatResponse(
        session_id=session_id,
        reply_text=reply_text or "(no reply)",
        proposed_actions=proposed,
        user_signed_in=user is not None,
    )


# ============ EXECUTE ============

class ExecuteRequest(BaseModel):
    session_id: str
    action_id: str
    action_type: str
    params: dict = Field(default_factory=dict)


class ExecuteResponse(BaseModel):
    ok: bool
    directive: Optional[dict] = None    # for frontend-executed actions
    result: Optional[Any] = None        # for backend-executed actions
    error: Optional[str] = None


def _require_signed_in(user: Optional[dict]):
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to perform this action")


async def _execute_backend(action_type: str, params: dict, user: Optional[dict]) -> Any:
    """Run a backend-tier action and return a JSON-serializable result."""
    from database import db

    if action_type == "search_workshops":
        rows = await db.workshops.find({"status": "upcoming"}, {"_id": 0}).limit(50).to_list(50)
        q = (params.get("query") or "").strip().lower()
        if q:
            rows = [r for r in rows if q in (r.get("title", "") + " " + r.get("description", "")).lower()]
        return rows[: int(params.get("limit") or 8)]

    if action_type == "search_products":
        rows = await db.products.find(
            {"$or": [{"is_vendor_product": {"$exists": False}},
                     {"moderation_status": "active"}]},
            {"_id": 0},
        ).limit(50).to_list(50)
        q = (params.get("query") or "").strip().lower()
        if q:
            rows = [r for r in rows if q in (r.get("name", "") + " " + r.get("description", "")).lower()]
        return rows[: int(params.get("limit") or 8)]

    if action_type == "search_partners":
        query: dict = {"status": "active", "is_sample": {"$ne": True}}
        if params.get("partner_type") and params["partner_type"] != "all":
            query["partner_type"] = params["partner_type"]
        rows = await db.partner_profiles.find(query, {"_id": 0}).limit(50).to_list(50)
        q = (params.get("query") or "").strip().lower()
        if q:
            rows = [r for r in rows if q in (r.get("display_name", "") + " " + r.get("headline", "") + " " + r.get("bio", "")).lower()]
        return rows[: int(params.get("limit") or 8)]

    if action_type == "search_research":
        rows = await db.research_artifacts.find({"status": "published"}, {"_id": 0}).limit(50).to_list(50)
        q = (params.get("query") or "").strip().lower()
        if q:
            rows = [r for r in rows if q in (r.get("title", "") + " " + r.get("abstract", "")).lower()]
        return rows[: int(params.get("limit") or 8)]

    if action_type == "lookup_my_subscriptions":
        _require_signed_in(user)
        rows = await db.partner_subscriptions.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
        return rows

    if action_type == "lookup_my_registrations":
        _require_signed_in(user)
        rows = await db.registrations.find({"user_id": user["id"]}, {"_id": 0}).to_list(50)
        return rows

    if action_type == "send_dm":
        _require_signed_in(user)
        thread_id = params.get("thread_id")
        content = (params.get("content") or "").strip()
        if not thread_id or not content:
            raise HTTPException(status_code=400, detail="thread_id and content are required")
        thread = await db.dm_threads.find_one({"id": thread_id, "participants": user["id"]})
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found or not yours")
        msg_id = gen_id()
        await db.dm_messages.insert_one({
            "id": msg_id, "thread_id": thread_id, "sender_id": user["id"],
            "content": content, "created_at": now_iso(),
            "read_by": [user["id"]], "via_assistant": True,
        })
        await db.dm_threads.update_one({"id": thread_id}, {"$set": {"last_message_at": now_iso()}})
        return {"message_id": msg_id}

    if action_type == "file_dispute":
        _require_signed_in(user)
        dispute_id = gen_id()
        await db.disputes.insert_one({
            "id": dispute_id,
            "complainant_id": user["id"],
            "target_user_id": params.get("target_user_id"),
            "category": params.get("category") or "service",
            "description": (params.get("description") or "")[:4000],
            "status": "open",
            "created_at": now_iso(),
            "via_assistant": True,
        })
        return {"dispute_id": dispute_id}

    if action_type == "submit_research_draft":
        _require_signed_in(user)
        profile = await db.partner_profiles.find_one(
            {"user_id": user["id"], "partner_type": "research", "status": "active"}
        )
        if not profile:
            raise HTTPException(status_code=403, detail="Only active research partners can submit artifacts")
        artifact_id = gen_id()
        await db.research_artifacts.insert_one({
            "id": artifact_id,
            "partner_id": profile["id"],
            "partner_slug": profile["slug"],
            "partner_display_name": profile["display_name"],
            "user_id": user["id"],
            "title": params.get("title", "")[:300],
            "abstract": params.get("abstract", "")[:4000],
            "authors": params.get("authors", "")[:500],
            "publication_date": params.get("publication_date") or datetime.now(timezone.utc).date().isoformat(),
            "full_text_url": params.get("full_text_url", "")[:600],
            "tier": params.get("tier") if params.get("tier") in ("brief", "paper") else "brief",
            "status": "draft",
            "categories": [],
            "tags": [],
            "moderation_note": None,
            "moderated_by": None,
            "moderated_at": None,
            "submitted_at": None,
            "promoted_until": None,
            "view_count": 0,
            "via_assistant": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
        return {"artifact_id": artifact_id, "next_step": "Open /dashboard/partner/research and click Submit for review when ready."}

    if action_type == "submit_partner_application":
        _require_signed_in(user)
        app_id = gen_id()
        await db.partner_applications.insert_one({
            "id": app_id,
            "user_id": user["id"],
            "status": "submitted",
            "via_assistant": True,
            "data": {
                "partner_type": params.get("partner_type", "community"),
                "display_name": params.get("display_name", "")[:200],
                "headline": params.get("headline", "")[:160],
                "bio": params.get("bio", "")[:2000],
            },
            "created_at": now_iso(),
        })
        return {"application_id": app_id}

    if action_type == "cancel_my_subscription":
        _require_signed_in(user)
        sub_id = params.get("subscription_id")
        sub = await db.partner_subscriptions.find_one({"id": sub_id, "user_id": user["id"]})
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        await db.partner_subscriptions.update_one(
            {"id": sub_id},
            {"$set": {"status": "cancelled", "cancelled_at": now_iso(), "cancelled_via": "assistant"}},
        )
        return {"subscription_id": sub_id}

    if action_type == "sign_agreement":
        _require_signed_in(user)
        active = await db.indemnification_versions.find_one(
            {"is_active": True}, {"_id": 0}, sort=[("created_at", -1)]
        )
        if not active:
            raise HTTPException(status_code=404, detail="No active agreement to sign")
        await db.indemnification_signatures.insert_one({
            "id": gen_id(),
            "user_id": user["id"],
            "version_id": active["id"],
            "signed_at": now_iso(),
            "via_assistant": True,
        })
        return {"version_id": active["id"], "version": active.get("version")}

    if action_type == "bookmark":
        _require_signed_in(user)
        bookmark_id = gen_id()
        await db.bookmarks.insert_one({
            "id": bookmark_id, "user_id": user["id"],
            "subject_type": params.get("subject_type"),
            "subject_id": params.get("subject_id"),
            "label": params.get("label"),
            "created_at": now_iso(), "via_assistant": True,
        })
        return {"bookmark_id": bookmark_id}

    raise HTTPException(status_code=400, detail=f"Unknown backend action: {action_type}")


@router.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest, user: Optional[dict] = Depends(get_current_user_optional)):
    from database import db
    meta = ACTIONS.get(req.action_type)
    if not meta:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action_type}")
    if meta["tier"] == "forbidden":
        raise HTTPException(status_code=403, detail=f"Action '{req.action_type}' is not allowed via assistant")

    audit_doc = {
        "id": gen_id(),
        "session_id": req.session_id,
        "action_id": req.action_id,
        "action_type": req.action_type,
        "params": req.params,
        "user_id": (user or {}).get("id"),
        "tier": meta["tier"],
        "execute": meta["execute"],
        "created_at": now_iso(),
    }

    try:
        if meta["execute"] == "frontend":
            # Server just acknowledges. Frontend performs the directive.
            directive = {"type": req.action_type, "params": req.params}
            audit_doc["result"] = "directive_returned"
            await db.assistant_audit.insert_one(audit_doc)
            if user:
                await log_action(
                    db, user, f"assistant.execute.{req.action_type}",
                    target_type="assistant_action", target_id=req.action_id,
                    metadata={"tier": meta["tier"]},
                )
            return ExecuteResponse(ok=True, directive=directive)
        result = await _execute_backend(req.action_type, req.params, user)
        audit_doc["result"] = "ok"
        await db.assistant_audit.insert_one(audit_doc)
        if user:
            await log_action(
                db, user, f"assistant.execute.{req.action_type}",
                target_type="assistant_action", target_id=req.action_id,
                metadata={"tier": meta["tier"]},
            )
        return ExecuteResponse(ok=True, result=result)
    except HTTPException as he:
        audit_doc["result"] = f"error:{he.status_code}"
        audit_doc["error"] = he.detail
        await db.assistant_audit.insert_one(audit_doc)
        return ExecuteResponse(ok=False, error=str(he.detail))
    except Exception as e:
        logger.exception("Assistant execute failed")
        audit_doc["result"] = "error:500"
        audit_doc["error"] = str(e)
        await db.assistant_audit.insert_one(audit_doc)
        return ExecuteResponse(ok=False, error=str(e))


# ============ SESSIONS ============

@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user: Optional[dict] = Depends(get_current_user_optional)):
    from database import db
    rows = await db.assistant_messages.find(
        {"session_id": session_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    # Visitor-or-owner check: anonymous sessions are unscoped; user-scoped sessions
    # are returned only to the owner.
    if rows:
        owners = {r.get("user_id") for r in rows if r.get("user_id")}
        if owners and (not user or user["id"] not in owners):
            raise HTTPException(status_code=403, detail="Not your session")
    return {"session_id": session_id, "messages": rows}


@router.get("/my-sessions")
async def my_sessions(user: dict = Depends(get_current_user)):
    """List your recent assistant sessions (newest first, max 20)."""
    from database import db
    pipeline = [
        {"$match": {"user_id": user["id"]}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$session_id",
            "last_at": {"$first": "$created_at"},
            "last_role": {"$first": "$role"},
            "last_content": {"$first": "$content"},
        }},
        {"$sort": {"last_at": -1}},
        {"$limit": 20},
    ]
    rows = await db.assistant_messages.aggregate(pipeline).to_list(20)
    return [
        {"session_id": r["_id"], "last_at": r["last_at"],
         "last_role": r["last_role"], "last_content": r["last_content"]}
        for r in rows
    ]


# ============ META ============

@router.get("/meta")
async def meta():
    """Public meta — surfaces allowed actions to the frontend for confirm-card rendering."""
    return {
        "model": f"{MODEL_PROVIDER}:{MODEL_NAME}",
        "actions": [
            {"type": k, "tier": v["tier"], "execute": v["execute"], "label": v["label"]}
            for k, v in ACTIONS.items() if v["tier"] != "forbidden"
        ],
    }
