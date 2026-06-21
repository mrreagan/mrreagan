"""Reusable Gemini Nano Banana image generation.

Centralizes the product-image generation flow used by:
  - POST /api/products/{id}/regenerate-image  (hero replacement)
  - POST /api/admin/products/image-queue/{id}/generate (additional shots)

Returns the public URL of the saved PNG (under /api/static/products/).
Raises a runtime error if generation fails so the caller decides what to do.
"""
from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger("birthright.image_gen")

_BRAND_SUFFIX = (
    " Brand palette: muted teal #476B6B, gold #C9A961, cream #FAF8F5. "
    "Square 1:1. Editorial product photography on warm cream linen, soft "
    "natural light. No printed brand name, no logo text, no human faces, "
    "no watermark."
)


async def generate_product_image(prompt: str, file_stem: str, session_id: str) -> str:
    """Generate one product image via Nano Banana and persist it to disk.

    Args:
      prompt: free-form scene description (no brand boilerplate needed).
      file_stem: stem used for the output filename, e.g. 'secure-bonds-mug-3'.
      session_id: stable identifier (e.g. product id) for the LLM session.

    Returns:
      Public URL of the saved PNG, e.g. '/api/static/products/<stem>.png'.
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    full_prompt = prompt.strip() + _BRAND_SUFFIX
    chat = (
        LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message="You generate clean editorial e-commerce product mockup photography.",
        )
        .with_model("gemini", "gemini-3.1-flash-image-preview")
        .with_params(modalities=["image", "text"])
    )
    _, images = await chat.send_message_multimodal_response(UserMessage(text=full_prompt))
    if not images:
        raise RuntimeError("No image returned from generator")

    static_dir = Path(__file__).resolve().parent.parent / "static" / "products"
    static_dir.mkdir(parents=True, exist_ok=True)
    out = static_dir / f"{file_stem}.png"
    out.write_bytes(base64.b64decode(images[0]["data"]))
    return f"/api/static/products/{file_stem}.png"
