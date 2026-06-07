"""Generate Facebook-ready promotional assets for the 5 Birthright leather patches.

For each phrase we produce TWO images:

  1. *Hero* — Nano Banana 2 (image-to-image) takes the physical patch photo
     (currently sitting on a paper towel) and:
       a) Replaces the paper-towel background with a brand-aligned, store-ready
          scene (mixed vibes across the 5 phrases for visual range).
       b) Slightly deepens / sharpens the engraving so the phrase and the
          'birthright.live' wordmark read cleanly even when scaled down.
       c) Preserves the patch shape, color, stitching and the engraved text
          exactly.

  2. *Social card* — Pillow code-composite at 1080x1350 (Facebook portrait
     feed). The hero image is placed in the upper portion of the card; the
     long-form "beautiful explanation" is typeset below it in
     Cormorant Garamond italic with a bold roman focal word and a gold
     hairline rule, matching the birthright.live editorial aesthetic.

Outputs land in /app/frontend/public/fb-assets/ so the user can preview them
through the existing static-asset pipeline.
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

from emergentintegrations.llm.chat import (  # noqa: E402
    FileContentWithMimeType,
    LlmChat,
    UserMessage,
)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

SRC_DIR = Path("/app/scripts/fb_assets/sources")
OUT_DIR = Path("/app/frontend/public/fb-assets")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/tmp/fonts")
FONT_ITALIC = str(FONT_DIR / "CormorantGaramond-Italic.ttf")
FONT_REGULAR = str(FONT_DIR / "CormorantGaramond-Regular.ttf")
FONT_BOLD = str(FONT_DIR / "CormorantGaramond-Bold.ttf")
FONT_SEMIBOLD = str(FONT_DIR / "CormorantGaramond-SemiBold.ttf")

# ---------- Source-image → phrase mapping ---------------------------------
# Confirmed from analyze_file_tool: 2073 rose-gold = "Repair…"; 2074-2077
# medium-brown layered patches each carrying their own phrase.
PHRASES = [
    {
        "idx": "01",
        "slug": "secure-connection",
        "phrase": "Secure connection is your birthright",
        "focal": "birthright",
        "source": SRC_DIR / "2074.jpeg",
        "vibe": (
            "warm cream linen surface with a soft natural-window diffused "
            "light, a hint of dried lavender sprig out of focus in the "
            "far background, faint warm shadow"
        ),
        "card_bg": (252, 246, 235),   # cream
        "card_accent": (181, 138, 70),  # warm gold
        "explanation": (
            "Before you earned it, before you proved yourself worthy, before "
            "the world taught you to bargain for love — connection was "
            "already yours. A secure bond is not a reward for good "
            "behaviour. It is the inheritance every person is born holding. "
            "To return to it is not to gain something new; it is to "
            "remember what you already are."
        ),
    },
    {
        "idx": "02",
        "slug": "founder-of-love-story",
        "phrase": "You are the founder of your own love story",
        "focal": "founder",
        "source": SRC_DIR / "2076.jpeg",
        "vibe": (
            "aged ivory parchment with a single pressed botanical leaf at "
            "the upper corner, soft museum lighting, faint deckle-edge "
            "paper texture"
        ),
        "card_bg": (247, 241, 230),
        "card_accent": (161, 117, 60),
        "explanation": (
            "No one writes your story for you. Not the family you came "
            "from, not the wounds you carry, not the script the world "
            "handed you. You are the founder — the one who chooses, who "
            "repairs, who begins again. The pen has always been in your "
            "hand."
        ),
    },
    {
        "idx": "03",
        "slug": "created-for-connection",
        "phrase": "We are created for connection",
        "focal": "connection",
        "source": SRC_DIR / "2075.jpeg",
        "vibe": (
            "smooth warm walnut wood surface with very soft directional "
            "golden-hour light, a faint out-of-focus ceramic cup at the "
            "far edge"
        ),
        "card_bg": (245, 238, 225),
        "card_accent": (143, 96, 48),
        "explanation": (
            "Our nervous systems are not built for isolation. From the "
            "first breath, we calibrate ourselves through the eyes, voice "
            "and warmth of another. Loneliness is not a personality "
            "trait — it is a signal that we were designed for something "
            "more. Connection is not optional. It is constitutive."
        ),
    },
    {
        "idx": "04",
        "slug": "bond-is-the-cure",
        "phrase": "The bond is the cure",
        "focal": "cure",
        "source": SRC_DIR / "2077.jpeg",
        "vibe": (
            "off-white raw silk fabric draped softly with subtle folds, "
            "low ambient morning light, a single small bronze key blurred "
            "in the deep background"
        ),
        "card_bg": (248, 243, 233),
        "card_accent": (167, 124, 64),
        "explanation": (
            "Insight will not heal you. Strategies will not heal you. A "
            "book, a podcast, a perfectly worded boundary — none of them "
            "will heal you. The bond heals you. The repeated experience "
            "of being seen, held, and stayed with by someone who will "
            "not leave — that is the medicine. Everything else is the "
            "wrapper."
        ),
    },
    {
        "idx": "05",
        "slug": "repair-is-older",
        "phrase": "Repair is older than rupture",
        "focal": "Repair",
        "source": SRC_DIR / "2073.jpeg",
        "vibe": (
            "pale stone surface with quiet kintsugi vibe — a hint of a "
            "ceramic shard with a thin gold seam blurred in the far "
            "background, soft window light from the left"
        ),
        "card_bg": (244, 239, 228),
        "card_accent": (155, 110, 52),
        "explanation": (
            "Long before the first wound, repair was already inside us. "
            "Babies cry and reach. Parents return. The dance of rupture "
            "and repair is older than language, older than memory, older "
            "than the breach itself. The capacity to mend is not "
            "something we acquire — it is something we are born holding, "
            "waiting for the moment we are brave enough to use it."
        ),
    },
]


# ---------- Nano Banana hero generation -----------------------------------

HERO_PROMPT_TEMPLATE = (
    "Take the leather patch shown in the attached photograph and produce a "
    "high-resolution, store-ready product photograph of THE SAME PATCH on a "
    "new background.\n\n"
    "ABSOLUTE RULES (do not violate):\n"
    "1. The patch itself must remain visually identical: same overall "
    "shape (slightly rounded-corner rectangle), same leather colour and "
    "grain, same stitched border. Do not invent a new patch.\n"
    "2. Preserve the engraved content EXACTLY: the small flame icon, the "
    "small wordmark 'birthright.live' beneath the flame, and the engraved "
    "phrase '{phrase}'. The phrase must be spelled exactly. Do not change, "
    "translate, rearrange or omit any word. Do not add quotation marks "
    "and do not add a trailing period.\n"
    "3. Slightly DEEPEN and SHARPEN the engraving so that the flame icon, "
    "the 'birthright.live' wordmark, and the phrase all read crisply even "
    "when the image is scaled to a small social-feed thumbnail. The "
    "engraving should look like a real laser-burned recess with a faint "
    "darker char inside the recess — clearly legible, never blurred.\n"
    "4. Show ONLY ONE patch, cleanly composed (no stacked second patch "
    "behind it).\n"
    "5. Replace the paper-towel background entirely with: {vibe}.\n"
    "6. Lighting: soft, warm, editorial product-photography. No harsh "
    "highlights, no neon, no oversaturated colours. The mood is "
    "contemplative, sacred, premium, timeless.\n"
    "7. Composition: the patch is the hero, occupying roughly 55-65% of "
    "the frame, slightly off-centre for natural editorial balance. Frame "
    "is square (1:1) at high resolution.\n"
    "8. Absolutely no extra text, watermark, logo, sticker, ribbon, price "
    "tag, label, frame, border or graphic element anywhere in the image "
    "other than what is engraved on the patch itself."
)


async def generate_hero(phrase_entry: dict) -> Path:
    out = OUT_DIR / f"hero-{phrase_entry['idx']}-{phrase_entry['slug']}.png"
    if out.exists() and out.stat().st_size > 30_000:
        print(f"  · skip hero (exists) {out.name}")
        return out

    src = phrase_entry["source"]
    if not src.exists():
        raise FileNotFoundError(src)

    prompt = HERO_PROMPT_TEMPLATE.format(
        phrase=phrase_entry["phrase"],
        vibe=phrase_entry["vibe"],
    )
    chat = (
        LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"fb-hero-{phrase_entry['idx']}-{uuid.uuid4().hex[:6]}",
            system_message=(
                "You are a senior editorial product photographer producing "
                "Facebook-ready hero shots of laser-engraved leather patches "
                "for the brand birthright.live."
            ),
        )
        .with_model("gemini", "gemini-3.1-flash-image-preview")
        .with_params(modalities=["image", "text"])
    )
    msg = UserMessage(
        text=prompt,
        file_contents=[FileContentWithMimeType(
            mime_type="image/jpeg",
            file_path=str(src),
        )],
    )
    _, images = await chat.send_message_multimodal_response(msg)
    if not images:
        raise RuntimeError(f"No hero image returned for {phrase_entry['slug']}")
    data = images[0].get("data") if isinstance(images[0], dict) else images[0]
    img_bytes = base64.b64decode(data) if isinstance(data, str) else data
    out.write_bytes(img_bytes)
    print(f"  ✓ hero  {out.name}  ({len(img_bytes):,} bytes)")
    return out


# ---------- Pillow social-card composite ----------------------------------

CARD_W, CARD_H = 1080, 1350  # Facebook portrait feed sweet-spot


def _wrap_lines(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """Greedy word-wrap returning a list of lines that each fit max_w."""
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        bbox = font.getbbox(trial)
        if bbox[2] - bbox[0] <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def build_social_card(phrase_entry: dict, hero_path: Path) -> Path:
    """Compose the 1080x1350 social card. Hero on top, copy below."""
    out = OUT_DIR / f"fb-{phrase_entry['idx']}-{phrase_entry['slug']}.png"

    bg = phrase_entry["card_bg"]
    accent = phrase_entry["card_accent"]
    ink = (38, 30, 22)            # warm near-black

    card = Image.new("RGB", (CARD_W, CARD_H), bg)
    draw = ImageDraw.Draw(card)

    # ---- Hero image at the top, cropped to a square, with margin ----------
    side_margin = 80
    hero_top = 80
    hero_side = CARD_W - 2 * side_margin  # 920
    hero = Image.open(hero_path).convert("RGB")
    # center-crop to square
    hw, hh = hero.size
    s = min(hw, hh)
    hero = hero.crop(((hw - s) // 2, (hh - s) // 2,
                      (hw + s) // 2, (hh + s) // 2))
    hero = hero.resize((hero_side, hero_side), Image.LANCZOS)
    card.paste(hero, (side_margin, hero_top))

    # ---- Gold hairline rule under the hero -------------------------------
    rule_y = hero_top + hero_side + 56
    rule_w = 160
    draw.rectangle(
        (CARD_W // 2 - rule_w // 2, rule_y,
         CARD_W // 2 + rule_w // 2, rule_y + 2),
        fill=accent,
    )

    # ---- Phrase (editorial display, italic body + roman focal) -----------
    phrase = phrase_entry["phrase"]
    focal = phrase_entry["focal"]

    italic_font = ImageFont.truetype(FONT_ITALIC, 56)
    roman_font = ImageFont.truetype(FONT_SEMIBOLD, 58)

    # tokenize phrase preserving spaces
    tokens = phrase.split(" ")
    # measure
    spaces = " "
    space_w = italic_font.getbbox(spaces)[2]

    def token_width(tok: str) -> int:
        f = roman_font if tok.strip(",.!?").lower() == focal.lower() else italic_font
        b = f.getbbox(tok)
        return b[2] - b[0]

    # wrap phrase into 1-2 lines
    max_phrase_w = CARD_W - 2 * side_margin
    phrase_lines: list[list[str]] = [[]]
    cur_w = 0
    for tok in tokens:
        tw = token_width(tok)
        added = tw if not phrase_lines[-1] else space_w + tw
        if cur_w + added <= max_phrase_w or not phrase_lines[-1]:
            phrase_lines[-1].append(tok)
            cur_w += added
        else:
            phrase_lines.append([tok])
            cur_w = tw

    # render phrase, centered, baseline-aligned
    phrase_y = rule_y + 28
    line_h = 70
    for line in phrase_lines:
        # measure total line width
        total = 0
        widths = []
        for i, tok in enumerate(line):
            tw = token_width(tok)
            widths.append(tw)
            total += tw
            if i < len(line) - 1:
                total += space_w
        x = (CARD_W - total) // 2
        for i, tok in enumerate(line):
            is_focal = tok.strip(",.!?").lower() == focal.lower()
            f = roman_font if is_focal else italic_font
            # nudge roman down slightly so optical baseline matches italic
            y_off = 0 if not is_focal else -2
            draw.text((x, phrase_y + y_off), tok, font=f, fill=ink)
            x += widths[i] + (space_w if i < len(line) - 1 else 0)
        phrase_y += line_h

    # ---- Explanation paragraph (smaller, justified-feeling italic) -------
    body_font = ImageFont.truetype(FONT_ITALIC, 30)
    body_lines = _wrap_lines(
        phrase_entry["explanation"],
        body_font,
        CARD_W - 2 * side_margin - 60,
    )
    body_y = phrase_y + 30
    body_line_h = 42
    for line in body_lines:
        bbox = body_font.getbbox(line)
        w = bbox[2] - bbox[0]
        x = (CARD_W - w) // 2
        draw.text((x, body_y), line, font=body_font, fill=(70, 56, 40))
        body_y += body_line_h

    # ---- Footer wordmark -------------------------------------------------
    wm_font = ImageFont.truetype(FONT_REGULAR, 26)
    wm = "birthright.live"
    bbox = wm_font.getbbox(wm)
    w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_W - w) // 2, CARD_H - 60),
        wm,
        font=wm_font,
        fill=accent,
    )

    card.save(out, "PNG", optimize=True)
    print(f"  ✓ card  {out.name}")
    return out


# ---------- Driver --------------------------------------------------------

async def main() -> None:
    print("Generating Facebook promo assets…")
    print(f"  out → {OUT_DIR}")
    sem = asyncio.Semaphore(3)

    async def _one(entry):
        async with sem:
            hero = await generate_hero(entry)
            build_social_card(entry, hero)

    await asyncio.gather(*[_one(e) for e in PHRASES])
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
