"""V4 promo assets — three-quarter perspective heroes + readable cards.

Round-3 directives from the founder:
  1. Mobile-readable cards: bigger body text, max contrast, more line spacing.
  2. Alternate the patch's rotational tilt across the 5 phrases (L, R, L, R, L).
  3. Each hero gets a signature symbolic object (key & kintsugi are the model).
  4. Soften lighting — single directional warm source, deeper shadows.
  5. ~35° three-quarter perspective ("looking at a table"), not 90° top-down.

Hero #4 in v2 drifted into a stretched hexagon; v4 prompts firmly preserve
the rounded-corner rectangle shape.

Output:
  /app/frontend/public/fb-assets/v4/hero-XX-<slug>.png   (1024x1024 hero)
  /app/frontend/public/fb-assets/v4/fb-XX-<slug>.png     (1080x1920 card)
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
OUT_DIR = Path("/app/frontend/public/fb-assets/v4")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/app/scripts/fonts")
FONT_ITALIC = str(FONT_DIR / "CormorantGaramond-Italic.ttf")
FONT_REGULAR = str(FONT_DIR / "CormorantGaramond-Regular.ttf")
FONT_SEMIBOLD = str(FONT_DIR / "CormorantGaramond-SemiBold.ttf")

# Brand palette (sampled from logo)
TEAL_DEEP = (44, 78, 90)        # #2C4E5A
GOLD = (168, 122, 74)           # #A87A4A
CARD_BG = (248, 242, 229)       # #F8F2E5


PHRASES = [
    {
        "idx": "01",
        "slug": "secure-connection",
        "phrase": "Secure connection is your birthright",
        "focal": "birthright",
        "source": SRC_DIR / "2074.jpeg",
        "tilt": "rotated slightly counter-clockwise (about 8-10° to the left), matching the tilt direction used for phrase #3 — the top edge of the patch should slope upward toward the right side of the frame",
        "signature": (
            "a small antique brass signet ring resting on the linen just "
            "to the lower-left of the patch (suggesting identity, "
            "inheritance, and the idea of being 'born holding the "
            "deed')."
        ),
        "vibe": (
            "draped soft cream linen surface with subtle natural folds. "
            "A few stems of dried lavender lie diagonally in the upper "
            "right, partly out of focus."
        ),
        "body": (
            "This isn't aspirational. It's not \"if you're lucky\" or "
            "\"for some people.\" It's the constitutional truth that "
            "every human being arrives wired for, and worthy of, a "
            "steady, responsive bond. We don't earn secure attachment — "
            "we recognize it as the default we were built for, even "
            "when life pulled us away from it. To carry this phrase is "
            "to refuse the lie that connection has to be deserved, "
            "performed, or paid for."
        ),
        "punch": "You were born holding the deed.",
    },
    {
        "idx": "02",
        "slug": "founder-of-love-story",
        "phrase": "You are the founder of your own love story",
        "focal": "founder",
        "source": SRC_DIR / "2076.jpeg",
        "tilt": "rotated slightly clockwise (about 8-10° to the right)",
        "signature": (
            "a vintage brass-nibbed fountain pen lying diagonally just "
            "below the patch — its nib facing the patch, suggesting the "
            "pen returning to the founder's hand."
        ),
        "vibe": (
            "sheet of pale ivory deckle-edge handmade paper with subtle "
            "fibre texture. A single pressed olive leaf rests near the "
            "upper-left corner, slightly out of focus."
        ),
        "body": (
            "Most of us inherited a love story before we could write "
            "one — from our parents' marriage, our family's silences, "
            "our culture's clichés about how romance is supposed to "
            "go. To be the founder is to take the pen back. Not to "
            "discard what was given, but to author the next chapter "
            "consciously: who you love, how you love, what counts as a "
            "happy ending."
        ),
        "punch": (
            "The bond you build now isn't an extension of what came "
            "before — it's a fresh founding document, and you're the "
            "one signing it."
        ),
    },
    {
        "idx": "03",
        "slug": "created-for-connection",
        "phrase": "We are created for connection",
        "focal": "connection",
        "source": SRC_DIR / "2075.jpeg",
        "tilt": "rotated slightly counter-clockwise (about 8-10° to the left)",
        "signature": (
            "two small handmade unglazed cream ceramic cups resting "
            "with their rims gently touching, set just to the upper "
            "right of the patch — a quiet two-ness, the simplest "
            "possible image of bond."
        ),
        "vibe": (
            "a pale grey natural stone slab with very subtle veining "
            "and a soft matte surface."
        ),
        "body": (
            "This is Sue Johnson's discovery dressed as theology and "
            "biology at the same time. Whether you read \"created\" as "
            "a divine act or a developmental one, the message is "
            "identical: your nervous system was not designed to thrive "
            "alone. The hunger you feel for closeness isn't a personal "
            "failing or a sign of weakness — it's the original "
            "blueprint asserting itself."
        ),
        "punch": (
            "We are not solitary creatures who occasionally bond. We "
            "are bonding creatures who occasionally find ourselves "
            "alone."
        ),
    },
    {
        "idx": "04",
        "slug": "bond-is-the-cure",
        "phrase": "The bond is the cure",
        "focal": "cure",
        "source": SRC_DIR / "2077.jpeg",
        "tilt": "rotated slightly clockwise (about 10-12° to the right)",
        "signature": (
            "a small antique bronze skeleton key resting on the silk "
            "just to the lower-left of the patch — the cure as the key "
            "that opens what was closed."
        ),
        "vibe": (
            "draped off-white raw silk fabric with soft natural folds "
            "and gentle creases catching the light."
        ),
        "body": (
            "We chase cures in books, therapy, podcasts, and "
            "prescriptions. Sometimes one of them helps. But the "
            "deepest healing for relational wounds always comes "
            "through a different relationship — one that proves the "
            "old story wrong by living a steadier one in its place. "
            "The bond itself, when it is finally safe and responsive, "
            "becomes the medicine."
        ),
        "punch": "Not a metaphor. Not a side effect. The cure.",
    },
    {
        "idx": "05",
        "slug": "repair-is-older",
        "phrase": "Repair is older than rupture",
        "focal": "Repair",
        "source": SRC_DIR / "2073.jpeg",
        "tilt": "rotated slightly counter-clockwise (about 8-10° to the left), matching the tilt direction used for phrase #3 — the top edge of the patch should slope upward toward the right side of the frame",
        "signature": (
            "the patch rests directly INSIDE a shallow handmade cream "
            "porcelain dish whose body bears delicate gold kintsugi "
            "seams — thin real-gold-leaf lacquer veins, not painted "
            "lines. The dish is the signature object; the patch is "
            "cradled within it."
        ),
        "vibe": (
            "the porcelain dish sits on a pale stone surface with very "
            "soft warm tones."
        ),
        "body": (
            "Most people assume rupture comes first and repair is the "
            "scramble afterward. But mother-infant repair cycles begin "
            "in the first weeks of life — before any conscious wound "
            "is ever named. The dance of rupture-and-repair is the "
            "relationship; it's been native to you since before you "
            "had language for either."
        ),
        "punch": (
            "You don't have to learn repair from scratch. You have to "
            "remember it."
        ),
    },
]


# ---------- Nano Banana hero prompt --------------------------------------

HERO_PROMPT = (
    "Produce a single high-resolution editorial product photograph based on "
    "the patch shown in the attached reference photo.\n\n"
    "PATCH (must be preserved exactly):\n"
    "• Shape: rounded-corner rectangle — NOT hexagonal, NOT a diamond, NOT "
    "stretched. Aspect roughly 1.6:1 width-to-height, with gently rounded "
    "corners and a stitched border just inside the edge.\n"
    "• Material: warm brown leather, same grain and tone as the reference.\n"
    "• Engraving: keep the engraved content EXACT — the small flame icon, "
    "the small 'birthright.live' wordmark beneath the flame, and the phrase "
    "'{phrase}'. The phrase must be spelled exactly. Do not add quotation "
    "marks. Do not add a trailing period. Slightly deepen and sharpen the "
    "engraving so it reads cleanly even at thumbnail size.\n"
    "• Quantity: ONE patch only. No stacked second patch, no duplicates.\n\n"
    "STAGING:\n"
    "• The patch lies flat on its surface and is {tilt}, so it does not sit "
    "perfectly axis-aligned in the frame — a natural editorial tilt.\n"
    "• Surface / background: {vibe}\n"
    "• ABSOLUTELY NO WOOD anywhere in the image. The surface must contrast "
    "clearly with the warm brown leather.\n"
    "• Signature object: {signature}\n\n"
    "CAMERA & LIGHT:\n"
    "• Camera angle is a three-quarter overhead view, roughly 35-40 degrees "
    "from horizontal — as if you are standing beside the table looking "
    "down at the surface. The surface recedes naturally in perspective; "
    "this is NOT a 90° top-down flat-lay.\n"
    "• Lighting is soft, warm and moody — a single directional window-light "
    "source from the upper-left grazing across the surface so the engraving "
    "catches a gentle highlight while deeper, softer shadows fall to the "
    "lower-right. Lower-key overall: muted highlights, no harsh glare, real "
    "shadow depth, faint film-grain mood. Editorial, contemplative, "
    "sacred-but-secular.\n\n"
    "OUTPUT:\n"
    "• Square 1:1 framing.\n"
    "• Patch occupies roughly 55-65% of the frame, off-centre for natural "
    "editorial balance.\n"
    "• No extra text, watermark, logo, sticker, ribbon, price tag, label, "
    "frame, border or graphic element anywhere other than what is engraved "
    "on the patch itself."
)


async def generate_hero(entry: dict) -> Path:
    out = OUT_DIR / f"hero-{entry['idx']}-{entry['slug']}.png"
    if out.exists() and out.stat().st_size > 30_000:
        print(f"  · skip hero (exists) {out.name}")
        return out

    src = entry["source"]
    if not src.exists():
        raise FileNotFoundError(src)

    prompt = HERO_PROMPT.format(
        phrase=entry["phrase"],
        tilt=entry["tilt"],
        vibe=entry["vibe"],
        signature=entry["signature"],
    )
    chat = (
        LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"fb4-hero-{entry['idx']}-{uuid.uuid4().hex[:6]}",
            system_message=(
                "You are a senior editorial product photographer producing "
                "moody, three-quarter-perspective hero shots of "
                "laser-engraved leather patches for birthright.live."
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
        raise RuntimeError(f"No hero image returned for {entry['slug']}")
    data = images[0].get("data") if isinstance(images[0], dict) else images[0]
    img_bytes = base64.b64decode(data) if isinstance(data, str) else data
    out.write_bytes(img_bytes)
    print(f"  ✓ hero  {out.name}  ({len(img_bytes):,} bytes)")
    return out


# ---------- Card composite (v4 — mobile-readable) ------------------------

CARD_W, CARD_H = 1080, 1920
SIDE = 90


def wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        if font.getbbox(trial)[2] <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def build_card(entry: dict, hero_path: Path) -> Path:
    out = OUT_DIR / f"fb-{entry['idx']}-{entry['slug']}.png"
    card = Image.new("RGB", (CARD_W, CARD_H), CARD_BG)
    draw = ImageDraw.Draw(card)

    # ---- Hero square ----
    hero_top = 70
    hero_side = CARD_W - 2 * SIDE
    hero = Image.open(hero_path).convert("RGB")
    hw, hh = hero.size
    s = min(hw, hh)
    hero = hero.crop(((hw - s) // 2, (hh - s) // 2,
                      (hw + s) // 2, (hh + s) // 2))
    hero = hero.resize((hero_side, hero_side), Image.LANCZOS)
    card.paste(hero, (SIDE, hero_top))

    # ---- Gold hairline ----
    rule_y = hero_top + hero_side + 56
    rule_w = 200
    draw.rectangle(
        (CARD_W // 2 - rule_w // 2, rule_y,
         CARD_W // 2 + rule_w // 2, rule_y + 2),
        fill=GOLD,
    )

    # ---- Phrase ----
    italic = ImageFont.truetype(FONT_ITALIC, 64)
    roman = ImageFont.truetype(FONT_SEMIBOLD, 66)
    space_w = italic.getbbox(" ")[2]
    focal = entry["focal"].lower()

    def is_focal(t: str) -> bool:
        return t.strip(",.!?;:").lower() == focal

    def w_of(t: str) -> int:
        f = roman if is_focal(t) else italic
        b = f.getbbox(t)
        return b[2] - b[0]

    max_w = CARD_W - 2 * SIDE
    tokens = entry["phrase"].split(" ")
    lines: list[list[str]] = [[]]
    cur_w = 0
    for t in tokens:
        tw = w_of(t)
        add = tw if not lines[-1] else space_w + tw
        if cur_w + add <= max_w or not lines[-1]:
            lines[-1].append(t)
            cur_w += add
        else:
            lines.append([t])
            cur_w = tw

    phrase_y = rule_y + 36
    line_h = 78
    for line in lines:
        total = sum(w_of(t) for t in line) + space_w * (len(line) - 1)
        x = (CARD_W - total) // 2
        for i, t in enumerate(line):
            f = roman if is_focal(t) else italic
            draw.text((x, phrase_y + (-2 if is_focal(t) else 0)),
                      t, font=f, fill=TEAL_DEEP)
            x += w_of(t) + (space_w if i < len(line) - 1 else 0)
        phrase_y += line_h

    # ---- Body (BIGGER + DEEPER for mobile readability) ----
    body_font = ImageFont.truetype(FONT_ITALIC, 38)
    body_lines = wrap(entry["body"], body_font, CARD_W - 2 * SIDE - 30)
    body_y = phrase_y + 36
    for line in body_lines:
        bb = body_font.getbbox(line)
        x = (CARD_W - (bb[2] - bb[0])) // 2
        draw.text((x, body_y), line, font=body_font, fill=TEAL_DEEP)
        body_y += 54

    # ---- Punchline (BIG italic) ----
    punch_font = ImageFont.truetype(FONT_ITALIC, 52)
    punch_lines = wrap(entry["punch"], punch_font, CARD_W - 2 * SIDE - 30)
    body_y += 28
    for line in punch_lines:
        bb = punch_font.getbbox(line)
        x = (CARD_W - (bb[2] - bb[0])) // 2
        draw.text((x, body_y), line, font=punch_font, fill=TEAL_DEEP)
        body_y += 68

    # ---- Footer ----
    wm_font = ImageFont.truetype(FONT_REGULAR, 32)
    wm = "birthright.live"
    bb = wm_font.getbbox(wm)
    draw.text(
        ((CARD_W - (bb[2] - bb[0])) // 2, CARD_H - 80),
        wm, font=wm_font, fill=GOLD,
    )

    card.save(out, "PNG", optimize=True)
    print(f"  ✓ card  {out.name}")
    return out


# ---------- Driver -------------------------------------------------------

async def main() -> None:
    print("Generating v4 assets (perspective + signature object + readable copy)…")
    print(f"  out → {OUT_DIR}")
    sem = asyncio.Semaphore(3)

    async def _one(entry):
        async with sem:
            hero = await generate_hero(entry)
            build_card(entry, hero)

    await asyncio.gather(*[_one(e) for e in PHRASES])
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
