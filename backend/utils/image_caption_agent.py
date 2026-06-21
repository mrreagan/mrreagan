"""AI image-caption agent.

Goal: every visitor-facing image on birthright.live should have a short, factual
description stored alongside it, so the help assistant can answer questions
like "what's in James Reagan's profile photo?" without ever bothering the
admin to type a caption.

This module does it lazily:

  1. `auto_caption_pending(db, limit)` scans the four visitor-facing collections
     for records that have an `image_url` but no `image_caption` (or whose
     `image_caption_source_url` no longer matches their current `image_url`,
     meaning the image was swapped and the cache is stale).
  2. For each, it fetches the image bytes, base64-encodes them, and asks
     Claude Sonnet 4.5 (vision) for a 30-60 word factual description.
  3. The caption is written back along with the source URL hash so we can
     detect future swaps.
  4. The help-context cache is invalidated so the new captions appear in the
     assistant's next answer.

Cost: a single vision call on Claude Sonnet 4.5 is roughly $0.003 with the
1.5× Foundation markup (~700 image tokens + ~70 output tokens). Captioning
all ~120 visitor-facing images on the site is a one-time ~$0.36. After that,
only new/changed images get re-captioned.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Any, Optional

import httpx
from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage

logger = logging.getLogger("birthright.image_caption")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
# Sonnet 4.5 is multimodal; cheap enough for one-shot captioning at ~$0.003/image.
CAPTION_MODEL = "claude-sonnet-4-5-20250929"
CAPTION_PROVIDER = "anthropic"

# Visitor-facing collections that have public images. Each entry tells us
# how to project + describe the record for the captioning prompt.
COLLECTIONS = {
    "governing_members": {
        "name_field": "name",
        "image_field": "image_url",
        "context_field": "title",   # subtitle for caption prompt context
    },
    "partner_profiles": {
        "name_field": "display_name",
        "image_field": "avatar_url",
        "context_field": "partner_type",
        "filter": {"status": "active"},
    },
    "products": {
        "name_field": "name",
        "image_field": "image_url",
        "context_field": "category",
        "filter": {"moderation_status": "active"},
    },
    "research_artifacts": {
        "name_field": "title",
        "image_field": "image_url",
        "context_field": "kind",
        "filter": {"status": "published"},
    },
}

# Avoid stampedes — only one captioning pass runs at a time per process.
_lock = asyncio.Lock()


async def _fetch_image_bytes(url: str) -> Optional[bytes]:
    """Download an image. Handles both absolute http(s) URLs and root-relative
    paths (`/api/static/...` served by FastAPI, or `/fb-assets/...` served by
    the frontend bundler)."""
    if not url:
        return None
    if url.startswith("/"):
        if url.startswith("/api/"):
            base = "http://127.0.0.1:8001"
        else:
            # Frontend-served static asset — resolve against the public origin.
            base = os.environ.get("PUBLIC_APP_URL") or "https://birthright.live"
        url = f"{base}{url}"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code != 200 or len(r.content) < 200:
                return None
            return r.content
    except Exception as exc:
        logger.warning("image fetch failed for %s: %s", url, exc)
        return None


async def _describe_image(image_bytes: bytes, subject: str, context_hint: str) -> Optional[str]:
    """Ask Claude Sonnet 4.5 (vision) for a short factual caption."""
    if not EMERGENT_LLM_KEY:
        logger.warning("EMERGENT_LLM_KEY missing — cannot caption images")
        return None
    prompt = (
        f"You are captioning an image on the birthright.live foundation website. "
        f"The image is associated with: '{subject}'"
        f"{f' ({context_hint})' if context_hint else ''}.\n\n"
        "Write a single concise factual description, 30-60 words, focused on "
        "what's visible in the image: subjects, expressions, posture, clothing, "
        "objects held or near them, setting/background, and overall mood. "
        "Avoid speculation about identity or emotion beyond what's plainly shown. "
        "Plain prose. No bullet points, no preamble like 'The image shows…'. "
        "Just describe."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"caption-{subject[:20]}",
            system_message="You describe images factually and concisely for an accessibility/search-context use case.",
        ).with_model(CAPTION_PROVIDER, CAPTION_MODEL).with_params(max_tokens=220)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        msg = UserMessage(text=prompt, file_contents=[ImageContent(image_base64=b64)])
        reply = await chat.send_message(msg)
        text = (reply or "").strip()
        # Defensive: strip stray quotes/code-fence wrappers.
        if text.startswith(("\"", "'")) and text.endswith(("\"", "'")):
            text = text[1:-1].strip()
        return text or None
    except Exception as exc:
        logger.warning("vision caption call failed for %r: %s", subject, exc)
        return None


async def auto_caption_pending(db, *, limit: int = 25, force: bool = False) -> dict:
    """Caption up to `limit` records that lack captions across all collections.

    Returns a small report dict: { collection_counts, errors, total_captioned }.
    Safe to call concurrently — only one pass runs at a time.
    """
    if _lock.locked():
        return {"skipped": True, "reason": "another captioning pass is running"}
    async with _lock:
        results = {"total_captioned": 0, "errors": 0, "collections": {}}
        budget_left = max(1, int(limit))
        for col_name, cfg in COLLECTIONS.items():
            if budget_left <= 0:
                break
            base_filter = dict(cfg.get("filter") or {})
            base_filter[cfg["image_field"]] = {"$nin": [None, ""]}
            if not force:
                # Only records whose caption is missing OR whose source url has changed.
                base_filter["$or"] = [
                    {"image_caption": {"$in": [None, ""]}},
                    {"image_caption_source_url": {"$exists": False}},
                    {"$expr": {"$ne": ["$image_caption_source_url", f"${cfg['image_field']}"]}},
                ]
            projection = {
                "_id": 0, "id": 1,
                cfg["name_field"]: 1,
                cfg["image_field"]: 1,
                cfg["context_field"]: 1,
            }
            cursor = db[col_name].find(base_filter, projection).limit(budget_left)
            captioned = 0
            async for doc in cursor:
                if budget_left <= 0:
                    break
                image_url = doc.get(cfg["image_field"])
                subject = doc.get(cfg["name_field"]) or "(untitled)"
                context_hint = doc.get(cfg["context_field"]) or ""
                img_bytes = await _fetch_image_bytes(image_url)
                if not img_bytes:
                    results["errors"] += 1
                    budget_left -= 1
                    continue
                caption = await _describe_image(img_bytes, subject, context_hint)
                if not caption:
                    results["errors"] += 1
                    budget_left -= 1
                    continue
                await db[col_name].update_one(
                    {"id": doc["id"]},
                    {"$set": {
                        "image_caption": caption,
                        "image_caption_source_url": image_url,
                    }},
                )
                captioned += 1
                results["total_captioned"] += 1
                budget_left -= 1
                logger.info("captioned %s/%s: %s", col_name, doc["id"], subject)
            results["collections"][col_name] = captioned
        # Invalidate help-context cache so new captions show up immediately.
        try:
            from utils.help_context import invalidate_cache
            invalidate_cache()
        except Exception:
            pass
        return results
