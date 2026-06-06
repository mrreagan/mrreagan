"""Generate the Birthright leather-patch engraving images via Nano Banana.

15 phrases × URL placements × patch shapes = 30 images.

Shapes:
  - rectangle           : plain horizontal rectangle, no visible border
  - hexagon             : elongated horizontal hexagonal outline (long stop-sign)

URL placements (within each shape):
  - top                 : 'birthright.live' above the flame
  - middle              : 'birthright.live' between the flame and the phrase
  - bottom              : 'birthright.live' beneath the phrase

Phrases × shapes × placements yields 30 images. We run up to 5 in parallel
to keep wall-clock under ~90 seconds.
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
OUT_DIR = Path("/app/frontend/public/engraving")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Wipe prior square images before regenerating so the folder is clean.
for old in OUT_DIR.glob("*.png"):
    old.unlink()
for old in OUT_DIR.glob("*.svg"):
    old.unlink()

SHAPES = {
    "rectangle": (
        "The composition is a horizontal rectangle, roughly 3:2 aspect "
        "ratio (wider than it is tall). The rectangle has NO visible "
        "border, outline, or frame — the design simply uses the full "
        "rectangular canvas with generous margin all around."
    ),
    "hexagon": (
        "The composition is contained inside a horizontal hexagonal "
        "outline — an elongated hexagon whose long axis runs left-to-"
        "right (think: a stop sign stretched horizontally, or a "
        "classic leather name-tag shape). The hexagon's edge is drawn "
        "as a thin clean solid black line. The entire design — flame, "
        "quotation, and URL — sits comfortably inside the hexagon "
        "with at least 8% margin between every edge of the design and "
        "the hexagon outline. Overall aspect ratio of the canvas is "
        "roughly 3:2 (wider than tall)."
    ),
}

LAYOUTS = {
    "bottom": (
        "Centered near the top of the composition, a single hand-drawn "
        "flame icon — simple, elegant, calligraphic line art in the "
        "style of a high-end brand mark. The flame is solid black "
        "outline only, modestly sized. In the middle of the canvas, "
        "the italic-serif quotation is set large and graceful, "
        "centered, breaking across two lines naturally. At the very "
        "bottom, in small clean sans-serif type — slightly larger than "
        "a publisher's mark but still understated — the URL "
        "'birthright.live' is set, centered, inconspicuous."
    ),
    "top": (
        "Centered at the very top of the canvas, in small clean sans-"
        "serif type — slightly larger than a publisher's mark but still "
        "understated — the URL 'birthright.live' appears. Below it, a "
        "single hand-drawn flame icon — simple, elegant, calligraphic "
        "line art, solid black outline only, modestly sized. Below the "
        "flame, the italic-serif quotation is set large and graceful, "
        "centered, breaking across two lines naturally."
    ),
    "middle": (
        "Centered near the top of the canvas, a single hand-drawn flame "
        "icon — simple, elegant, calligraphic line art, solid black "
        "outline only, modestly sized. Directly below the flame — "
        "sitting between the flame and the quotation — the URL "
        "'birthright.live' appears in small clean sans-serif type, "
        "centered and inconspicuous. Below the URL, the italic-serif "
        "quotation is set large and graceful, centered, breaking across "
        "two lines naturally, filling the lower portion of the canvas."
    ),
}

STYLE_BASE = (
    "Editorial, minimalist leather-patch design intended for laser "
    "engraving. Pure white background. All graphics and text rendered "
    "in solid black ink only — no color, no gradients, no shading, no "
    "textures. Composition centered and generously spaced. The phrase "
    "uses a CONTEMPORARY EDITORIAL SERIF, italic — similar in feeling to "
    "Canela, Le Jour Serif, Tiempos Headline, or a high-contrast Caslon "
    "italic. Characteristics: strong stroke contrast between thick and "
    "thin strokes, elegant high x-height, generous letter spacing, "
    "graceful descenders. This is the same editorial serif used on a "
    "high-end magazine masthead or boutique brand mission statement — "
    "not a generic Times New Roman, not a slab serif, not a script. "
    "TYPE SIZE: the phrase is set LARGE — bold and dominant — filling "
    "roughly 60-70% of the canvas width so it reads as the unmistakable "
    "hero of the composition. The flame icon and URL are deliberately "
    "small supporting marks, not equal partners with the phrase. "
    "CRITICAL TEXT RULES: the phrase appears as plain words on the "
    "canvas — NO quotation marks of any kind (no “ ”, no \" \", no ' ', "
    "no ‘ ’, no brackets, no parentheses), and NO trailing period, "
    "comma, ellipsis, exclamation point, or any other punctuation at "
    "the end of the phrase. The phrase begins with its first word and "
    "ends with its last word — nothing wraps, surrounds, or trails it. "
    "Overall feeling: contemplative, sacred, modern but timeless. "
    "Absolutely no embellishments, decorative borders, ornaments, or "
    "extra graphic elements beyond the flame icon, the phrase, the URL, "
    "and (if applicable) the hexagonal outline. White space is the "
    "design."
)

PHRASES = [
    # (idx, slug, phrase, emphasis_instruction)
    ("01", "secure-connection",
     'Secure connection is your birthright',
     "Within the phrase, the single word \"birthright\" is set in "
     "UPRIGHT ROMAN (not italic) of the same typeface, the same size or "
     "only a hair larger, creating elegant editorial contrast against "
     "the surrounding italic text. All other words remain in graceful "
     "italic. No other emphasis."),
    ("02", "founder-of-your-love-story",
     'You are the founder of your own love story',
     "Within the phrase, the two-word fragment \"your own\" is set in "
     "italic at a SLIGHTLY LARGER size than the rest of the phrase — "
     "perhaps 110-115% the size of the other words. NOT bold, NOT a "
     "different weight, NOT a different typeface — only larger. Every "
     "other word in the phrase is set at the same size as every other "
     "non-emphasized word, all in graceful italic. No other emphasis."),
    ("03", "created-for-connection",
     'We are created for connection',
     "The phrase is set in graceful italic throughout. No single word "
     "is emphasized in any way — no upright roman, no bold, no size "
     "change, no brackets, no parentheses. The phrase reads as one "
     "uniform italic line."),
    ("04", "the-bond-is-the-cure",
     'The bond is the cure',
     "The phrase is set in graceful italic throughout. No single word "
     "is emphasized in any way — no upright roman, no bold, no size "
     "change. The phrase reads as one uniform italic line."),
    ("05", "repair-is-older-than-rupture",
     'Repair is older than rupture',
     "The phrase is set in graceful italic throughout. No single word "
     "is emphasized in any way — no upright roman, no bold, no size "
     "change. The phrase reads as one uniform italic line."),
]


async def generate_one(idx: str, slug: str, phrase: str, emphasis: str,
                       shape: str, placement: str) -> Path:
    prompt = (
        f"{STYLE_BASE}\n\n"
        f"SHAPE: {SHAPES[shape]}\n\n"
        f"LAYOUT: {LAYOUTS[placement]}\n\n"
        f"The exact phrase to typeset, with no surrounding punctuation, "
        f"is:\n    {phrase}\n\n"
        f"Reminder: the phrase appears on the canvas exactly as those "
        f"words, with no opening quote, no closing quote, and no "
        f"trailing punctuation. Just the words.\n\n"
        f"TYPOGRAPHIC EMPHASIS: {emphasis}\n\n"
        f"No other text appears anywhere in the image except the phrase "
        f"and the small 'birthright.live' URL line."
    )
    chat = (
        LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"eng-{idx}-{shape}-{placement}-{uuid.uuid4().hex[:6]}",
            system_message="You are a senior editorial designer producing leather-patch engraving files.",
        )
        .with_model("gemini", "gemini-3.1-flash-image-preview")
        .with_params(modalities=["image", "text"])
    )
    _, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    if not images:
        raise RuntimeError(f"No image for {idx}-{shape}-{placement}")
    data = images[0].get("data") if isinstance(images[0], dict) else images[0]
    img_bytes = base64.b64decode(data) if isinstance(data, str) else data
    out = OUT_DIR / f"birthright-engraving-{idx}-{slug}-{shape}-url-{placement}.png"
    out.write_bytes(img_bytes)
    print(f"  ✓ {out.name}  ({len(img_bytes):,} bytes)")
    return out


async def _semaphored(sem, idx, slug, phrase, emphasis, shape, placement):
    async with sem:
        target = OUT_DIR / f"birthright-engraving-{idx}-{slug}-{shape}-url-{placement}.png"
        if target.exists() and target.stat().st_size > 10_000:
            print(f"  · skip (exists) {target.name}")
            return
        try:
            await generate_one(idx, slug, phrase, emphasis, shape, placement)
        except Exception as ex:
            print(f"  ✗ {idx}-{shape}-{placement} FAILED: {ex}")


SHAPES_TO_RUN = ("rectangle",)
LAYOUTS_TO_RUN = ("middle",)

async def main() -> None:
    tasks = []
    sem = asyncio.Semaphore(5)
    # Wipe any matching pre-existing images so the skip-guard doesn't
    # block this iteration's rerolls.
    for shape in SHAPES_TO_RUN:
        for placement in LAYOUTS_TO_RUN:
            for idx, slug, *_ in PHRASES:
                p = OUT_DIR / f"birthright-engraving-{idx}-{slug}-{shape}-url-{placement}.png"
                if p.exists():
                    p.unlink()
    for shape in SHAPES_TO_RUN:
        for placement in LAYOUTS_TO_RUN:
            for idx, slug, phrase, emphasis in PHRASES:
                tasks.append(_semaphored(sem, idx, slug, phrase, emphasis, shape, placement))
    print(f"Generating {len(tasks)} images "
          f"(shapes={SHAPES_TO_RUN}, placements={LAYOUTS_TO_RUN})…")
    await asyncio.gather(*tasks)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
