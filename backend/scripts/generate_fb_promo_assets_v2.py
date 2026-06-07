"""V2 Facebook promo assets — flat-lay heroes, brand teal+gold cards, emphasized last sentence.

Round-2 directives from the founder:
  • Every patch must be photographed FLAT on its surface (top-down or
    very-near-top-down), never propped or angled like a product showcase.
  • Background must visually CONTRAST with the brown leather — cream linen,
    pale stone, ivory silk, cream porcelain. ABSOLUTELY NO WOOD.
  • Lean into the "apples of gold in settings of silver" motif — at least
    one hero shows the patch sitting inside the cream-porcelain dish with
    delicate gold kintsugi seams.
  • Description text is the co-star with the patch — give it real real
    estate (taller card, more whitespace), use BRAND TEAL ink and a GOLD
    accent (sampled from the logo), and italicize + scale up the LAST
    SENTENCE of each paragraph so it lands as the punchline.

Outputs land in /app/frontend/public/fb-assets/v2/.
"""
from __future__ import annotations

import asyncio
import base64
import os
import re
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
OUT_DIR = Path("/app/frontend/public/fb-assets/v2")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/app/scripts/fonts")
FONT_ITALIC = str(FONT_DIR / "CormorantGaramond-Italic.ttf")
FONT_REGULAR = str(FONT_DIR / "CormorantGaramond-Regular.ttf")
FONT_BOLD = str(FONT_DIR / "CormorantGaramond-Bold.ttf")
FONT_SEMIBOLD = str(FONT_DIR / "CormorantGaramond-SemiBold.ttf")

# ---------- Brand palette (sampled from the user-uploaded logo) ----------
BRAND_TEAL_DEEP = (44, 78, 90)        # #2C4E5A — wordmark, headings
BRAND_TEAL_MID = (61, 99, 115)        # #3D6373 — body copy
BRAND_GOLD = (168, 122, 74)           # #A87A4A — accents, hairlines, footer
BRAND_GOLD_LIGHT = (201, 160, 111)    # #C9A06F — softer gold
CARD_BG = (248, 242, 229)             # #F8F2E5 — warm cream

# ---------- Phrases ------------------------------------------------------

PHRASES = [
    {
        "idx": "01",
        "slug": "secure-connection",
        "phrase": "Secure connection is your birthright",
        "focal": "birthright",
        "source": SRC_DIR / "2074.jpeg",
        "vibe": (
            "the patch lies perfectly flat, fully top-down camera angle, "
            "on a soft cream linen surface with subtle natural weave. A "
            "few stems of dried lavender rest diagonally to the upper "
            "right, slightly out of focus. Soft natural window light "
            "from the upper-left casts a very gentle shadow under the "
            "patch. The cream surface CONTRASTS clearly with the warm "
            "brown leather."
        ),
        "explanation": (
            "Before you earned it, before you proved yourself worthy, "
            "before the world taught you to bargain for love — connection "
            "was already yours. A secure bond is not a reward for good "
            "behaviour. It is the inheritance every person is born "
            "holding. To return to it is not to gain something new; it "
            "is to remember what you already are."
        ),
        # Sentence that should appear italic + larger as the punchline.
        "punchline": (
            "To return to it is not to gain something new; "
            "it is to remember what you already are."
        ),
    },
    {
        "idx": "02",
        "slug": "founder-of-love-story",
        "phrase": "You are the founder of your own love story",
        "focal": "founder",
        "source": SRC_DIR / "2076.jpeg",
        "vibe": (
            "the patch lies completely flat, top-down camera angle, "
            "centred on a sheet of pale ivory deckle-edge handmade "
            "paper. A single pressed botanical leaf (eucalyptus or olive) "
            "sits just to the upper-left, partially out of focus. Soft "
            "diffused museum light. The ivory paper provides clean "
            "contrast with the warm brown leather. NO wood anywhere."
        ),
        "explanation": (
            "No one writes your story for you. Not the family you came "
            "from, not the wounds you carry, not the script the world "
            "handed you. You are the founder — the one who chooses, who "
            "repairs, who begins again. The pen has always been in your "
            "hand."
        ),
        "punchline": "The pen has always been in your hand.",
    },
    {
        "idx": "03",
        "slug": "created-for-connection",
        "phrase": "We are created for connection",
        "focal": "connection",
        "source": SRC_DIR / "2075.jpeg",
        "vibe": (
            "the patch lies flat, photographed fully top-down, on a "
            "cool pale-grey natural stone slab with very subtle veining. "
            "A small unglazed cream ceramic dish rests in the upper "
            "right, slightly out of focus, holding a single sprig of "
            "rosemary. Soft directional morning light. Clear visual "
            "contrast between the warm brown patch and the pale grey "
            "stone. NO wood anywhere."
        ),
        "explanation": (
            "Our nervous systems are not built for isolation. From the "
            "first breath, we calibrate ourselves through the eyes, "
            "voice and warmth of another. Loneliness is not a "
            "personality trait — it is a signal that we were designed "
            "for something more. Connection is not optional. It is "
            "constitutive."
        ),
        "punchline": "Connection is not optional. It is constitutive.",
    },
    {
        "idx": "04",
        "slug": "bond-is-the-cure",
        "phrase": "The bond is the cure",
        "focal": "cure",
        "source": SRC_DIR / "2077.jpeg",
        "vibe": (
            "the patch lies completely flat, top-down camera angle, on "
            "draped off-white raw silk fabric with soft natural folds. "
            "A small antique bronze key rests in the lower-left corner, "
            "out of focus. Low ambient morning light. The pale silk "
            "clearly contrasts the warm brown leather. NO wood anywhere."
        ),
        "explanation": (
            "Insight will not heal you. Strategies will not heal you. A "
            "book, a podcast, a perfectly worded boundary — none of "
            "them will heal you. The bond heals you. The repeated "
            "experience of being seen, held, and stayed with by someone "
            "who will not leave — that is the medicine. Everything "
            "else is the wrapper."
        ),
        "punchline": "Everything else is the wrapper.",
    },
    {
        "idx": "05",
        "slug": "repair-is-older",
        "phrase": "Repair is older than rupture",
        "focal": "Repair",
        "source": SRC_DIR / "2073.jpeg",
        "vibe": (
            "HERO STYLE-GUIDE SHOT — the patch is laid flat INSIDE a "
            "shallow handmade cream porcelain dish. The porcelain has "
            "delicate gold kintsugi seams running across its surface — "
            "thin gold-leaf veins from real lacquer repair, never "
            "painted-on lines. The dish sits on a pale stone surface. "
            "Top-down camera angle. Soft window light from the left. "
            "The composition evokes 'apples of gold in settings of "
            "silver' — a precious object resting in a precious vessel. "
            "Patch leather may be ROSE-GOLD/COPPER coloured here to "
            "honour the original physical engraving. NO wood anywhere."
        ),
        "explanation": (
            "Long before the first wound, repair was already inside us. "
            "Babies cry and reach. Parents return. The dance of rupture "
            "and repair is older than language, older than memory, "
            "older than the breach itself. The capacity to mend is not "
            "something we acquire — it is something we are born "
            "holding, waiting for the moment we are brave enough to "
            "use it."
        ),
        "punchline": (
            "The capacity to mend is not something we acquire — it is "
            "something we are born holding, waiting for the moment we "
            "are brave enough to use it."
        ),
    },
]


# ---------- Nano Banana hero generation ----------------------------------

HERO_PROMPT_TEMPLATE = (
    "Take the leather patch from the attached reference photograph and "
    "produce a single high-resolution, store-ready FLAT-LAY product "
    "photograph of THAT EXACT patch on a new surface.\n\n"
    "MANDATORY RULES (any violation ruins the asset):\n"
    "1. CAMERA ANGLE: strictly top-down or very-near-top-down (within "
    "about 10° of perfectly overhead). The patch lies flat on its "
    "surface — never propped up, never tilted on its edge, never "
    "angled like a product showcase. Flat-lay only.\n"
    "2. THE PATCH: preserve the patch identically — same rounded-corner "
    "rectangular shape, same warm brown leather grain, same dark "
    "stitched border. Show ONLY ONE patch (no second patch behind it).\n"
    "3. ENGRAVING: keep the engraved content EXACT — small flame icon, "
    "the small 'birthright.live' wordmark beneath the flame, and the "
    "engraved phrase '{phrase}'. The phrase must be spelled exactly. "
    "Do NOT add quotation marks. Do NOT add a trailing period. Do NOT "
    "rearrange or omit any word. Slightly deepen and sharpen the laser "
    "engraving so it reads crisply at thumbnail size.\n"
    "4. SCENE: {vibe}\n"
    "5. NO WOOD. The surface must contrast clearly with the warm brown "
    "leather. If anything wood-coloured appears, this asset is "
    "rejected.\n"
    "6. LIGHTING: soft, warm, editorial product-photography. Sacred, "
    "contemplative, premium, timeless. No harsh highlights, no neon, "
    "no oversaturation.\n"
    "7. COMPOSITION: square 1:1, the patch occupies roughly 55-65% of "
    "the frame, slightly off-centre for natural editorial balance.\n"
    "8. NO EXTRA TEXT, watermark, logo, sticker, ribbon, price tag, "
    "label, frame, border or graphic element anywhere in the image "
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
            session_id=f"fb2-hero-{phrase_entry['idx']}-{uuid.uuid4().hex[:6]}",
            system_message=(
                "You are a senior editorial product photographer producing "
                "Facebook-ready flat-lay hero shots of laser-engraved "
                "leather patches for the brand birthright.live."
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


# ---------- Social-card composite (v2) -----------------------------------

CARD_W, CARD_H = 1080, 1620  # taller 2:3 portrait — more room for the copy


def _wrap_lines(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """Greedy word-wrap."""
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
    out = OUT_DIR / f"fb-{phrase_entry['idx']}-{phrase_entry['slug']}.png"

    card = Image.new("RGB", (CARD_W, CARD_H), CARD_BG)
    draw = ImageDraw.Draw(card)

    side_margin = 90

    # ---- Hero square at top -------------------------------------------
    hero_top = 70
    hero_side = CARD_W - 2 * side_margin   # 900
    hero = Image.open(hero_path).convert("RGB")
    hw, hh = hero.size
    s = min(hw, hh)
    hero = hero.crop(((hw - s) // 2, (hh - s) // 2,
                      (hw + s) // 2, (hh + s) // 2))
    hero = hero.resize((hero_side, hero_side), Image.LANCZOS)
    card.paste(hero, (side_margin, hero_top))

    # ---- Gold hairline rule -------------------------------------------
    rule_y = hero_top + hero_side + 64
    rule_w = 180
    draw.rectangle(
        (CARD_W // 2 - rule_w // 2, rule_y,
         CARD_W // 2 + rule_w // 2, rule_y + 2),
        fill=BRAND_GOLD,
    )

    # ---- Phrase (teal, italic body + semibold roman focal) ------------
    phrase = phrase_entry["phrase"]
    focal = phrase_entry["focal"]
    italic_font = ImageFont.truetype(FONT_ITALIC, 62)
    roman_font = ImageFont.truetype(FONT_SEMIBOLD, 64)
    space_w = italic_font.getbbox(" ")[2]

    def is_focal(tok: str) -> bool:
        return tok.strip(",.!?;:").lower() == focal.lower()

    def tok_w(tok: str) -> int:
        f = roman_font if is_focal(tok) else italic_font
        b = f.getbbox(tok)
        return b[2] - b[0]

    max_w = CARD_W - 2 * side_margin
    tokens = phrase.split(" ")
    lines: list[list[str]] = [[]]
    cur_line_w = 0
    for tok in tokens:
        tw = tok_w(tok)
        added = tw if not lines[-1] else space_w + tw
        if cur_line_w + added <= max_w or not lines[-1]:
            lines[-1].append(tok)
            cur_line_w += added
        else:
            lines.append([tok])
            cur_line_w = tw

    phrase_y = rule_y + 36
    line_h = 78
    for line in lines:
        total = sum(tok_w(t) for t in line) + space_w * (len(line) - 1)
        x = (CARD_W - total) // 2
        for i, tok in enumerate(line):
            f = roman_font if is_focal(tok) else italic_font
            y_off = -2 if is_focal(tok) else 0
            draw.text((x, phrase_y + y_off), tok, font=f, fill=BRAND_TEAL_DEEP)
            x += tok_w(tok) + (space_w if i < len(line) - 1 else 0)
        phrase_y += line_h

    # ---- Explanation paragraph -----------------------------------------
    # Split off the punchline so we can typeset it larger + italic.
    punchline = phrase_entry["punchline"].strip()
    body = phrase_entry["explanation"].strip()
    # remove punchline from end of body if present
    if body.endswith(punchline):
        body_lead = body[: -len(punchline)].rstrip()
    else:
        # last-sentence fallback
        sentences = re.split(r"(?<=[.!?])\s+", body)
        body_lead = " ".join(sentences[:-1])
        punchline = sentences[-1]

    body_font = ImageFont.truetype(FONT_ITALIC, 32)
    punch_font = ImageFont.truetype(FONT_ITALIC, 40)

    text_max_w = CARD_W - 2 * side_margin - 40
    body_lines = _wrap_lines(body_lead, body_font, text_max_w) if body_lead else []
    punch_lines = _wrap_lines(punchline, punch_font, text_max_w)

    body_y = phrase_y + 30
    for line in body_lines:
        bbox = body_font.getbbox(line)
        w = bbox[2] - bbox[0]
        x = (CARD_W - w) // 2
        draw.text((x, body_y), line, font=body_font, fill=BRAND_TEAL_MID)
        body_y += 46

    # spacer before punchline
    body_y += 22

    for line in punch_lines:
        bbox = punch_font.getbbox(line)
        w = bbox[2] - bbox[0]
        x = (CARD_W - w) // 2
        draw.text((x, body_y), line, font=punch_font, fill=BRAND_TEAL_DEEP)
        body_y += 56

    # ---- Footer wordmark (gold) ---------------------------------------
    wm_font = ImageFont.truetype(FONT_REGULAR, 30)
    wm = "birthright.live"
    bbox = wm_font.getbbox(wm)
    w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_W - w) // 2, CARD_H - 70),
        wm,
        font=wm_font,
        fill=BRAND_GOLD,
    )

    card.save(out, "PNG", optimize=True)
    print(f"  ✓ card  {out.name}")
    return out


# ---------- Driver -------------------------------------------------------

async def main() -> None:
    print("Generating v2 Facebook promo assets…")
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
