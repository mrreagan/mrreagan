"""AI Studio — Phase 1 (admin-only).

Workflow:
  1) Admin describes a product concept in plain language.
  2) Admin requests a cost estimate BEFORE spending any AI dollars.
  3) Admin confirms and triggers generation.
  4) Studio generates:
       - 1–3 hero images via Nano Banana (Gemini 2.5 Flash Image).
       - Copy variants (name + description) via Claude Sonnet 4.5,
         one per selected audience (Founder Collection, General Equip).
  5) Studio saves the result as a DRAFT product in db.products with
     moderation_status="unpublished" and a special "studio_draft" tag so
     Admin can review on /admin/products and publish manually.

The route prefix is /studio (mounted under /api).
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from models import gen_id, now_iso
from utils.ai_billing import (
    FOUNDATION_MARKUP_PCT,
    PRICE_MULTIPLIER,
    PRICING_DISCLOSURE,
    compute_cost,
    get_wallet,
    record_usage,
    require_balance,
)

logger = logging.getLogger("birthright.studio")
router = APIRouter(prefix="/studio", tags=["studio"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
TEXT_MODEL = "claude-sonnet-4-5"
IMAGE_MODEL = "nano-banana"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static" / "products"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Token budgets used for ESTIMATE (real call may use less). Keeps estimates
# slightly pessimistic — better to over-quote and under-charge than the reverse.
_EST_TOKENS_IN_PER_VARIANT = 600       # system prompt + brief + style guide
_EST_TOKENS_OUT_PER_VARIANT = 700      # name + description draft

PRODUCT_CATEGORIES = [
    "cap",        # hats, beanies
    "tee",
    "hoodie",
    "sweatshirt",
    "mug",
    "water_bottle",
    "tote",
    "poster",
    "notebook",
    "journal",
]
AUDIENCES = ["founder_collection", "general_equip"]


# ============ Helpers ============
def _admin_only(user: dict) -> None:
    if user.get("role") != "admin":
        raise HTTPException(403, "AI Studio is admin-only in Phase 1.")


async def _vendor_profile(db, user: dict) -> Optional[dict]:
    """Return an active vendor partner profile for this user, if any."""
    return await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": "vendor", "status": "active"},
        {"_id": 0},
    )


async def _studio_access(db, user: dict) -> tuple[str, Optional[dict]]:
    """Gate AI Studio access. Returns ('admin', None) or ('vendor', profile).
    Raises 403 if neither."""
    if user.get("role") == "admin":
        return "admin", None
    vp = await _vendor_profile(db, user)
    if vp:
        return "vendor", vp
    raise HTTPException(403, "AI Studio requires admin role or an active vendor partner profile.")


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "studio-draft"


def _build_image_prompt(brief: str, category: str, audience: str) -> str:
    """Compose a tight prompt for Nano Banana. Birthright's brand language is
    quiet, restrained, editorial; deliberately not 'gradient-y AI slop'."""
    style = (
        "Photorealistic product photo on a clean cream (#F4F1EA) background, "
        "natural daylight, soft shadows, editorial composition. "
        "Brand language: quiet, grounded, secure-attachment. No text overlays "
        "unless explicitly described. Avoid: rainbow gradients, glowing effects, "
        "stock-photo cliché."
    )
    audience_hint = (
        "Founder Collection identity-wear: dignified, personal, like a small "
        "talisman the wearer reaches for."
        if audience == "founder_collection"
        else "General Equip: useful daily object; calm and confident, not loud."
    )
    return (
        f"Birthright Foundation product mockup. Category: {category}. "
        f"Brief: {brief}. {audience_hint} {style}"
    )


def _claude_system_prompt(audience: str) -> str:
    if audience == "founder_collection":
        return (
            "You write product copy for the Birthright Foundation's 'Founder "
            "Collection' — identity-wear that whispers 'you are the founder of "
            "your own love story.' Voice: quiet, grounded, personal. Avoid "
            "marketing-speak. Each piece supports the foundation."
        )
    return (
        "You write product copy for Birthright Foundation's general store, "
        "'Equip.' Voice: useful, calm, confident. Products are designed to "
        "live with the work — to be reached for daily. No marketing-speak."
    )


# Allowed interior styles (kept in sync with utils/journal_pdf.INTERIOR_STYLES).
_INTERIOR_STYLE_HINTS = {
    "lined": "general journaling, daily reflection, prose, notes",
    "blank": "morning pages, free writing, sketching, no rules wanted",
    "dot_grid": "bullet journaling, sketchnotes, habit grids, planners",
    "split_top_blank_bottom_lined": "daily intentions, drawings + reflection, gratitude with sketch",
    "dated_lined": "diaries, dated journals, anniversary keepsakes",
    "habit_tracker": "habit trackers, gratitude logs, streak journals, 31-day challenges",
}


async def _infer_interior_style(brief: str, *, user_id: str) -> str:
    """Ask Claude to pick the best interior page style for this journal brief.

    Returns one of the keys in _INTERIOR_STYLE_HINTS. Falls back to 'lined'
    if Claude returns something we don't recognize.
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    options = "\n".join(f"- {k}: {v}" for k, v in _INTERIOR_STYLE_HINTS.items())
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"studio-style-{user_id}-{uuid.uuid4().hex[:8]}",
        system_message=(
            "You decide the interior page layout for a journal product based on its brief. "
            "Reply with ONLY the style key, no quotes, no explanation."
        ),
    ).with_model("anthropic", TEXT_MODEL)
    msg = UserMessage(
        text=(
            f"Pick the best interior style for this journal:\n\n"
            f"\"{brief}\"\n\n"
            f"Options (key: when to use):\n{options}\n\n"
            f"Reply with one key. If unsure, reply 'lined'."
        )
    )
    response = await chat.send_message(msg)
    raw = response if isinstance(response, str) else getattr(response, "content", "") or ""
    candidate = raw.strip().strip("`'\"").splitlines()[0].strip().lower() if raw.strip() else "lined"
    if candidate in _INTERIOR_STYLE_HINTS:
        return candidate
    # Try fuzzy match — pick the first allowed key that's a substring
    for key in _INTERIOR_STYLE_HINTS:
        if key in candidate:
            return key
    return "lined"


# ============ Pydantic ============
class EstimateRequest(BaseModel):
    brief: str = Field(min_length=10, max_length=1200)
    category: str = Field(min_length=2, max_length=40)
    audiences: List[Literal["founder_collection", "general_equip"]] = Field(min_length=1, max_length=2)
    image_count: int = Field(default=2, ge=1, le=3)

    def validate_category(self) -> None:
        if self.category not in PRODUCT_CATEGORIES:
            raise HTTPException(400, f"category must be one of {PRODUCT_CATEGORIES}")


class EstimateResponse(BaseModel):
    estimated_cost_usd: float
    your_balance_usd: float
    after_this_prompt_usd: float
    foundation_portion_usd: float
    provider_portion_usd: float
    multiplier: float
    foundation_markup_pct: float
    disclosure: str
    insufficient_funds: bool
    significant_portion_of_balance: bool   # > 20%


class GenerateRequest(EstimateRequest):
    """Same fields — Studio sends estimate first, then confirms with this."""
    # Phase 4 — Off-site referral mode (vendor-only).
    is_off_site: bool = False
    external_url: Optional[str] = Field(default=None, max_length=500)


# ============ Endpoints ============
@router.post("/estimate", response_model=EstimateResponse)
async def estimate_cost(req: EstimateRequest, user: dict = Depends(get_current_user)):
    """Pre-prompt cost estimate. NEVER touches LLMs. Pure math."""
    from database import db
    await _studio_access(db, user)
    req.validate_category()
    n_audiences = len(req.audiences)
    text_cost = compute_cost(
        TEXT_MODEL,
        tokens_in=_EST_TOKENS_IN_PER_VARIANT * n_audiences,
        tokens_out=_EST_TOKENS_OUT_PER_VARIANT * n_audiences,
    )
    image_cost = compute_cost(IMAGE_MODEL, images=req.image_count)
    total = round(text_cost + image_cost, 6)
    wallet = await get_wallet(db, user["id"])
    balance = float(wallet.get("balance_usd") or 0.0)
    foundation_portion = round(total * (PRICE_MULTIPLIER - 1.0) / PRICE_MULTIPLIER, 6)
    provider_portion = round(total - foundation_portion, 6)
    return EstimateResponse(
        estimated_cost_usd=total,
        your_balance_usd=round(balance, 4),
        after_this_prompt_usd=round(balance - total, 4),
        foundation_portion_usd=foundation_portion,
        provider_portion_usd=provider_portion,
        multiplier=PRICE_MULTIPLIER,
        foundation_markup_pct=FOUNDATION_MARKUP_PCT,
        disclosure=PRICING_DISCLOSURE,
        insufficient_funds=balance < total,
        significant_portion_of_balance=balance > 0 and (total / balance) > 0.20,
    )


@router.post("/generate", status_code=201)
async def generate_draft(req: GenerateRequest, user: dict = Depends(get_current_user)):
    """Run the full generation pipeline and save a draft product. Idempotent
    only at the database level — each call genuinely spends AI dollars."""
    from database import db
    actor_role, vendor_profile = await _studio_access(db, user)
    # ---- 0) Validate off-site fields BEFORE spending any AI dollars ----
    if req.is_off_site:
        if actor_role != "vendor":
            raise HTTPException(400, "Off-site mode is only available to vendor partners.")
        if not req.external_url or not req.external_url.strip().lower().startswith(("http://", "https://")):
            raise HTTPException(400, "Off-site products require a valid external_url (http(s)://...)")
    estimate = await estimate_cost(req, user)
    await require_balance(db, user, min_usd=estimate.estimated_cost_usd, feature="AI Studio")

    # ---- 1) Images ----
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import base64
    image_urls: List[str] = []
    for i in range(req.image_count):
        prompt = _build_image_prompt(req.brief, req.category, req.audiences[0])
        try:
            img_chat = (
                LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"studio-img-{user['id']}-{uuid.uuid4().hex[:8]}",
                    system_message="You generate clean, brand-aligned product mockups for Birthright Foundation.",
                )
                .with_model("gemini", "gemini-3.1-flash-image-preview")
                .with_params(modalities=["image", "text"])
            )
            _, images = await img_chat.send_message_multimodal_response(UserMessage(text=prompt))
        except Exception as ex:
            logger.exception("Image generation failed on image %d/%d", i + 1, req.image_count)
            raise HTTPException(502, f"Image generation failed: {ex}") from ex
        if not images:
            raise HTTPException(502, "Image generation returned no output")
        img_data = images[0].get("data") if isinstance(images[0], dict) else images[0]
        img_bytes = base64.b64decode(img_data) if isinstance(img_data, str) else img_data
        filename = f"studio-{_slugify(req.category)}-{uuid.uuid4().hex[:8]}.png"
        out_path = STATIC_DIR / filename
        await asyncio.to_thread(out_path.write_bytes, img_bytes)
        image_urls.append(f"/api/static/products/{filename}")
    await record_usage(
        db, user, feature="studio", model=IMAGE_MODEL,
        images=req.image_count,
        meta={"action": "generate_images", "category": req.category, "count": req.image_count},
    )

    # ---- 2) Copy variants per audience ----
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    copy_variants: dict = {}
    total_tokens_in = 0
    total_tokens_out = 0
    for audience in req.audiences:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"studio-{user['id']}-{uuid.uuid4().hex[:8]}",
            system_message=_claude_system_prompt(audience),
        ).with_model("anthropic", TEXT_MODEL)
        user_msg = UserMessage(
            text=(
                f"Draft a product name and a 70-100 word description for a Birthright "
                f"{req.category} based on this brief:\n\n"
                f"\"{req.brief}\"\n\n"
                f"Return JSON with two keys exactly: name, description. "
                f"The name should be short (2-5 words). The description should be "
                f"sensory and grounded, no marketing-speak, no exclamation points."
            )
        )
        try:
            response = await chat.send_message(user_msg)
        except Exception as ex:
            logger.exception("Claude copy generation failed for audience=%s", audience)
            raise HTTPException(502, f"Copy generation failed: {ex}") from ex
        # Parse: Claude usually returns clean JSON for this kind of strict instruction.
        text = response if isinstance(response, str) else getattr(response, "content", "") or ""
        try:
            import json as _json
            # Strip code-fences if present
            stripped = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
            data = _json.loads(stripped)
            name = (data.get("name") or "").strip()
            description = (data.get("description") or "").strip()
        except Exception:
            # Fallback: split on first newline
            lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
            name = lines[0][:80] if lines else "Untitled draft"
            description = " ".join(lines[1:])[:1200] if len(lines) > 1 else text[:1200]
        copy_variants[audience] = {"name": name, "description": description}
        total_tokens_in += _EST_TOKENS_IN_PER_VARIANT
        total_tokens_out += _EST_TOKENS_OUT_PER_VARIANT
    await record_usage(
        db, user, feature="studio", model=TEXT_MODEL,
        tokens_in=total_tokens_in, tokens_out=total_tokens_out,
        meta={"action": "generate_copy", "audiences": req.audiences},
    )

    # ---- 2b) Interior style inference (journal/notebook only) ----
    interior_style: Optional[str] = None
    if req.category in ("journal", "notebook"):
        try:
            interior_style = await _infer_interior_style(req.brief, user_id=user["id"])
            # Tiny but real spend — bill once as a classifier call (~200 in/40 out).
            await record_usage(
                db, user, feature="studio", model=TEXT_MODEL,
                tokens_in=200, tokens_out=40,
                meta={"action": "infer_interior_style", "style": interior_style},
            )
        except Exception:
            logger.exception("interior style inference failed — defaulting to lined")
            interior_style = "lined"

    # ---- 3) Save draft product ----
    primary_audience = req.audiences[0]
    primary = copy_variants[primary_audience]
    slug_base = _slugify(primary["name"]) or "studio-draft"
    # Ensure slug uniqueness
    slug = slug_base
    n = 1
    while await db.products.find_one({"slug": slug}):
        n += 1
        slug = f"{slug_base}-{n}"
    is_vendor = actor_role == "vendor"
    # Vendors → drafts go to admin moderation queue.
    # Admins → drafts stay unpublished until they manually publish.
    moderation_status = "pending_review" if is_vendor else "unpublished"
    moderation_note = (
        "Vendor AI Studio submission — awaiting admin moderation."
        if is_vendor
        else "AI Studio draft — review and publish when ready."
    )
    draft = {
        "id": gen_id(),
        "slug": slug,
        "name": primary["name"],
        "description": primary["description"],
        "price": 0.0,            # admin/vendor sets price on review
        "type": "merch",
        "workshop_id": None,
        "image_url": image_urls[0] if image_urls else "",
        "image_gallery": image_urls,
        "inventory": 0,
        "category": req.category,
        "collection": "founder_collection" if primary_audience == "founder_collection" else None,
        "max_per_order": None,
        "is_homepage_feature": False,
        # The big new bits — drafts that are NOT yet published:
        "studio_draft": True,
        "studio_brief": req.brief,
        "studio_audiences": req.audiences,
        "studio_copy_variants": copy_variants,
        "interior_style": interior_style,
        "moderation_status": moderation_status,
        "moderation_note": moderation_note,
        "created_at": now_iso(),
        "created_by": user["id"],
    }
    if is_vendor and vendor_profile:
        draft["is_vendor_product"] = True
        draft["vendor_user_id"] = user["id"]
        draft["vendor_partner_id"] = vendor_profile["id"]
        draft["vendor_name"] = (vendor_profile.get("meta") or {}).get("business_name") or vendor_profile.get("display_name")
        draft["vendor_slug"] = vendor_profile.get("slug")
    # Phase 4 — off-site mode (vendor only).
    # Phase 4 — off-site mode (already validated at request start).
    if req.is_off_site:
        draft["is_off_site"] = True
        draft["external_url"] = req.external_url.strip()
        # Keep type=merch so the public Shop's default filter still surfaces them.
        # Cart logic below detects is_off_site to skip Stripe and link out instead.
    await db.products.insert_one(dict(draft))
    draft.pop("_id", None)
    logger.info(
        "studio: %s %s created draft product %s (slug=%s, status=%s)",
        actor_role, user.get("email"), draft["id"], slug, moderation_status,
    )
    return draft


@router.get("/drafts")
async def list_drafts(user: dict = Depends(get_current_user)):
    """List AI-Studio admin drafts awaiting publish (admin's own unpublished drafts)."""
    _admin_only(user)
    from database import db
    rows = await db.products.find(
        {"studio_draft": True, "moderation_status": "unpublished"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    return rows


@router.get("/my-drafts")
async def list_my_drafts(user: dict = Depends(get_current_user)):
    """Vendor self-service: list my own AI Studio submissions with status."""
    from database import db
    await _studio_access(db, user)
    rows = await db.products.find(
        {"studio_draft": True, "created_by": user["id"]},
        {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    return rows


@router.post("/drafts/{product_id}/publish")
async def publish_draft(product_id: str, user: dict = Depends(get_current_user)):
    """Admin clicks 'Publish' on /admin/products → flip moderation + clear draft flag."""
    _admin_only(user)
    from database import db
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Draft not found")
    if not doc.get("studio_draft"):
        raise HTTPException(400, "Product is not an AI Studio draft")
    if (doc.get("price") or 0) <= 0:
        raise HTTPException(400, "Set a non-zero price before publishing")
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "studio_draft": False,
            "moderation_status": "active",
            "moderation_note": None,
            "published_at": now_iso(),
        }},
    )
    return {"ok": True}


@router.delete("/drafts/{product_id}")
async def discard_draft(product_id: str, user: dict = Depends(get_current_user)):
    """Discard a draft (and delete its generated images from disk best-effort).
    Admin can discard any. Vendor can discard only their own non-approved drafts."""
    from database import db
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Draft not found")
    if not doc.get("studio_draft"):
        raise HTTPException(400, "Only AI Studio drafts can be discarded via this endpoint")
    is_admin = user.get("role") == "admin"
    is_owner = doc.get("created_by") == user["id"]
    if not (is_admin or is_owner):
        raise HTTPException(403, "You can only discard your own drafts")
    if not is_admin and doc.get("moderation_status") == "active":
        raise HTTPException(400, "Cannot discard a published product")
    for url in doc.get("image_gallery", []):
        # /api/static/products/foo.png  →  /app/backend/static/products/foo.png
        fname = url.rsplit("/", 1)[-1]
        try:
            (STATIC_DIR / fname).unlink(missing_ok=True)
        except Exception:
            pass
    await db.products.delete_one({"id": product_id})
    return {"ok": True}


# ============ Admin moderation queue (vendor submissions) ============
admin_router = APIRouter(prefix="/admin/studio", tags=["studio-admin"])


@admin_router.get("/queue")
async def admin_queue(
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List vendor AI Studio submissions for moderation.

    Filter by status: pending_review (default), changes_requested, rejected, active.
    """
    _admin_only(user)
    from database import db
    q: dict = {"studio_draft": True, "is_vendor_product": True}
    target = status or "pending_review"
    if target == "active":
        q = {"is_vendor_product": True, "studio_draft": False, "moderation_status": "active"}
    else:
        q["moderation_status"] = target
    rows = await db.products.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return rows


class AdminApproveRequest(BaseModel):
    price: float = Field(gt=0, description="Retail price set at approval time")
    admin_note: Optional[str] = Field(default=None, max_length=500)


@admin_router.post("/queue/{product_id}/approve")
async def admin_approve(product_id: str, data: AdminApproveRequest, user: dict = Depends(get_current_user)):
    """Approve a vendor draft, set retail price, publish."""
    _admin_only(user)
    from database import db
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Draft not found")
    if not doc.get("is_vendor_product") or not doc.get("studio_draft"):
        raise HTTPException(400, "Not a vendor AI Studio draft")
    if doc.get("moderation_status") not in ("pending_review", "changes_requested"):
        raise HTTPException(400, f"Cannot approve from status '{doc.get('moderation_status')}'")
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "studio_draft": False,
            "moderation_status": "active",
            "moderation_note": data.admin_note,
            "price": float(data.price),
            "published_at": now_iso(),
            "moderated_by": user["id"],
            "moderated_at": now_iso(),
        }},
    )
    return {"ok": True}


class AdminFeedbackRequest(BaseModel):
    admin_note: str = Field(min_length=3, max_length=500)


@admin_router.post("/queue/{product_id}/request-changes")
async def admin_request_changes(product_id: str, data: AdminFeedbackRequest, user: dict = Depends(get_current_user)):
    """Send the draft back to the vendor with a note explaining what to change."""
    _admin_only(user)
    from database import db
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Draft not found")
    if not doc.get("is_vendor_product") or not doc.get("studio_draft"):
        raise HTTPException(400, "Not a vendor AI Studio draft")
    if doc.get("moderation_status") not in ("pending_review", "changes_requested"):
        raise HTTPException(400, f"Cannot request changes from status '{doc.get('moderation_status')}'")
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "moderation_status": "changes_requested",
            "moderation_note": data.admin_note,
            "moderated_by": user["id"],
            "moderated_at": now_iso(),
        }},
    )
    return {"ok": True}


@admin_router.post("/queue/{product_id}/reject")
async def admin_reject(product_id: str, data: AdminFeedbackRequest, user: dict = Depends(get_current_user)):
    """Reject the vendor draft. Sets terminal status — vendor must start over."""
    _admin_only(user)
    from database import db
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Draft not found")
    if not doc.get("is_vendor_product") or not doc.get("studio_draft"):
        raise HTTPException(400, "Not a vendor AI Studio draft")
    if doc.get("moderation_status") == "active":
        raise HTTPException(400, "Cannot reject an already-approved product")
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "moderation_status": "rejected",
            "moderation_note": data.admin_note,
            "moderated_by": user["id"],
            "moderated_at": now_iso(),
        }},
    )
    return {"ok": True}
