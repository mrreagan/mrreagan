"""V3 social cards — verbatim "What this means" summaries (user-authored).

Heroes are reused from v2. This script only re-renders the social cards with
the user's ORIGINAL paragraph text exactly as they wrote it, on a taller
1080x1920 canvas to give the longer body enough room to breathe.

Output: /app/frontend/public/fb-assets/v3/fb-XX-<slug>.png
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERO_DIR = Path("/app/frontend/public/fb-assets/v2")
OUT_DIR = Path("/app/frontend/public/fb-assets/v3")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/app/scripts/fonts")
FONT_ITALIC = str(FONT_DIR / "CormorantGaramond-Italic.ttf")
FONT_REGULAR = str(FONT_DIR / "CormorantGaramond-Regular.ttf")
FONT_SEMIBOLD = str(FONT_DIR / "CormorantGaramond-SemiBold.ttf")

# Brand palette
TEAL_DEEP = (44, 78, 90)        # #2C4E5A
TEAL_MID = (61, 99, 115)        # #3D6373
GOLD = (168, 122, 74)           # #A87A4A
CARD_BG = (248, 242, 229)       # #F8F2E5

# Verbatim "What this means" copy provided by the founder.
PHRASES = [
    {
        "idx": "01",
        "slug": "secure-connection",
        "phrase": "Secure connection is your birthright",
        "focal": "birthright",
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


# ------- Layout constants ------------------------------------------------
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


def build_card(entry: dict) -> Path:
    out = OUT_DIR / f"fb-{entry['idx']}-{entry['slug']}.png"
    hero_path = HERO_DIR / f"hero-{entry['idx']}-{entry['slug']}.png"
    if not hero_path.exists():
        raise FileNotFoundError(hero_path)

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
    rule_w = 180
    draw.rectangle(
        (CARD_W // 2 - rule_w // 2, rule_y,
         CARD_W // 2 + rule_w // 2, rule_y + 2),
        fill=GOLD,
    )

    # ---- Phrase (italic + bold focal, teal) ----
    italic = ImageFont.truetype(FONT_ITALIC, 60)
    roman = ImageFont.truetype(FONT_SEMIBOLD, 62)
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

    phrase_y = rule_y + 30
    line_h = 74
    for line in lines:
        total = sum(w_of(t) for t in line) + space_w * (len(line) - 1)
        x = (CARD_W - total) // 2
        for i, t in enumerate(line):
            f = roman if is_focal(t) else italic
            draw.text((x, phrase_y + (-2 if is_focal(t) else 0)),
                      t, font=f, fill=TEAL_DEEP)
            x += w_of(t) + (space_w if i < len(line) - 1 else 0)
        phrase_y += line_h

    # ---- Body paragraph ----
    body_font = ImageFont.truetype(FONT_ITALIC, 30)
    body_lines = wrap(entry["body"], body_font, CARD_W - 2 * SIDE - 40)
    body_y = phrase_y + 30
    for line in body_lines:
        bb = body_font.getbbox(line)
        x = (CARD_W - (bb[2] - bb[0])) // 2
        draw.text((x, body_y), line, font=body_font, fill=TEAL_MID)
        body_y += 44

    # ---- Punchline ----
    punch_font = ImageFont.truetype(FONT_ITALIC, 40)
    punch_lines = wrap(entry["punch"], punch_font, CARD_W - 2 * SIDE - 60)
    body_y += 24
    for line in punch_lines:
        bb = punch_font.getbbox(line)
        x = (CARD_W - (bb[2] - bb[0])) // 2
        draw.text((x, body_y), line, font=punch_font, fill=TEAL_DEEP)
        body_y += 54

    # ---- Footer wordmark ----
    wm_font = ImageFont.truetype(FONT_REGULAR, 30)
    wm = "birthright.live"
    bb = wm_font.getbbox(wm)
    draw.text(
        ((CARD_W - (bb[2] - bb[0])) // 2, CARD_H - 80),
        wm, font=wm_font, fill=GOLD,
    )

    card.save(out, "PNG", optimize=True)
    print(f"  ✓ v3 card  {out.name}")
    return out


def main() -> None:
    print("Generating v3 cards (verbatim summaries)…")
    for e in PHRASES:
        build_card(e)
    print("Done.")


if __name__ == "__main__":
    main()
