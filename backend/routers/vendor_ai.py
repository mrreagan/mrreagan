"""Vendor Product Development & Sourcing Manager — generative AI for vendor partners.
Phase 6C.4.

Capabilities (all metered via ai_billing, 1× passthrough):
  - write_description(brief, category) → product description copy
  - suggest_price(description, category) → price range
  - marketing_blurb(description, audience) → short marketing copy
  - generate_image(prompt) → Nano Banana image, saved to /api/static/products/
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from utils.ai_billing import record_usage, require_balance

load_dotenv()
logger = logging.getLogger("birthright.vendor_ai")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
TEXT_MODEL_PROVIDER = "anthropic"
TEXT_MODEL_NAME = "claude-sonnet-4-5-20250929"
IMAGE_MODEL_NAME = "nano-banana"

STATIC_DIR = Path("/app/backend/static/products")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/vendor-ai", tags=["vendor-ai"])


async def _require_vendor_partner(db, user: dict) -> dict:
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": "vendor", "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=403, detail="Only active vendor partners can use Vendor PDM")
    return profile


async def _call_claude(system: str, user_text: str, session_suffix: str) -> tuple[str, int, int]:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"vendor_ai_{session_suffix}",
        system_message=system,
    ).with_model(TEXT_MODEL_PROVIDER, TEXT_MODEL_NAME)
    reply = await chat.send_message(UserMessage(text=user_text))
    text = str(reply or "")
    return text, (len(system) + len(user_text)) // 4, len(text) // 4


# ============ WRITE DESCRIPTION ============

class DescribeRequest(BaseModel):
    brief: str = Field(min_length=10, max_length=4000)
    category: str = Field(default="merch", max_length=80)
    target_words: int = Field(default=120, ge=40, le=300)


@router.post("/write-description")
async def write_description(req: DescribeRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_vendor_partner(db, user)
    await require_balance(db, user, min_usd=0.005, feature="Vendor PDM")
    system = (
        "You write product descriptions for the Birthright Foundation storefront — calm, "
        "honest, attachment-aware brand voice. Avoid hype, never make medical claims. "
        f"Target {req.target_words} words. Output only the description text."
    )
    user_text = f"Category: {req.category}\nBrief: {req.brief}"
    reply, tin, tout = await _call_claude(system, user_text, session_suffix=user["id"])
    event = await record_usage(
        db, user, feature="vendor_pdm", model=TEXT_MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "write_description", "category": req.category},
    )
    return {"description": reply.strip(), "cost_usd": event["cost_usd"]}


# ============ SUGGEST PRICE ============

class PriceRequest(BaseModel):
    description: str = Field(min_length=10, max_length=4000)
    category: str = Field(default="merch", max_length=80)


@router.post("/suggest-price")
async def suggest_price(req: PriceRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_vendor_partner(db, user)
    await require_balance(db, user, min_usd=0.002, feature="Vendor PDM")
    system = (
        "You suggest a retail price range (USD) for a product on Birthright Foundation's "
        "storefront. Existing catalog covers $5–$95 across apparel, journals, books, prints, "
        "decks, home goods, bags. Return STRICT JSON only: "
        '{"low_usd": number, "mid_usd": number, "high_usd": number, "rationale": "short string"}'
    )
    payload = f"Category: {req.category}\nProduct: {req.description}"
    reply, tin, tout = await _call_claude(system, payload, session_suffix=user["id"])
    import json
    import re
    cleaned = reply.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except Exception:
        data = {"rationale": cleaned}
    event = await record_usage(
        db, user, feature="vendor_pdm", model=TEXT_MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "suggest_price", "category": req.category},
    )
    return {**data, "cost_usd": event["cost_usd"]}


# ============ MARKETING BLURB ============

class MarketingRequest(BaseModel):
    description: str = Field(min_length=10, max_length=4000)
    audience: str = Field(default="general", max_length=200)
    max_chars: int = Field(default=240, ge=80, le=600)


@router.post("/marketing-blurb")
async def marketing_blurb(req: MarketingRequest, user: dict = Depends(get_current_user)):
    from database import db
    await _require_vendor_partner(db, user)
    await require_balance(db, user, min_usd=0.002, feature="Vendor PDM")
    system = (
        "Write a single short marketing blurb (≤ {n} chars) suitable for social media or a "
        "product card. Birthright voice: warm, calm, honest. No emoji. No exclamation marks."
    ).format(n=req.max_chars)
    payload = f"Audience: {req.audience}\nProduct: {req.description}"
    reply, tin, tout = await _call_claude(system, payload, session_suffix=user["id"])
    event = await record_usage(
        db, user, feature="vendor_pdm", model=TEXT_MODEL_NAME,
        tokens_in=tin, tokens_out=tout,
        meta={"action": "marketing_blurb"},
    )
    return {"blurb": reply.strip()[: req.max_chars], "cost_usd": event["cost_usd"]}


# ============ GENERATE IMAGE ============

class ImageRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=2000)
    slug: str = Field(default="vendor", max_length=80, pattern=r"^[a-z0-9-]+$")


@router.post("/generate-image")
async def generate_image(req: ImageRequest, user: dict = Depends(get_current_user)):
    """Generates a single product image via Nano Banana and saves it under /api/static/products."""
    from database import db
    await _require_vendor_partner(db, user)
    await require_balance(db, user, min_usd=0.04, feature="Vendor PDM")
    # Import lazily so the rest of the router still loads if the optional dep changes
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration as _Unused  # noqa: F401
    except Exception:
        pass
    try:
        from emergentintegrations.llm.gemini.image_generation import GeminiImageGeneration
    except Exception as e:
        logger.exception("Nano Banana SDK not available")
        raise HTTPException(status_code=503, detail=f"Image generation unavailable: {e}") from e
    gen = GeminiImageGeneration(api_key=EMERGENT_LLM_KEY)
    images = await gen.generate_images(
        prompt=req.prompt,
        model="gemini-2.5-flash-image",
        number_of_images=1,
    )
    if not images:
        raise HTTPException(status_code=502, detail="Image generation returned no output")
    image_bytes = images[0]
    filename = f"{req.slug}-{uuid.uuid4().hex[:8]}.png"
    out_path = STATIC_DIR / filename
    # bytes-or-base64 robust handling
    if isinstance(image_bytes, str):
        import base64
        image_bytes = base64.b64decode(image_bytes)
    await asyncio.to_thread(out_path.write_bytes, image_bytes)
    event = await record_usage(
        db, user, feature="vendor_pdm", model=IMAGE_MODEL_NAME,
        images=1,
        meta={"action": "generate_image", "filename": filename},
    )
    return {
        "image_url": f"/api/static/products/{filename}",
        "cost_usd": event["cost_usd"],
    }
