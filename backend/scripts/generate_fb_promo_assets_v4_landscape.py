"""V4 LANDSCAPE social cards — 1920x1080 16:9.

Side-by-side layout: hero square on the LEFT, the verbatim "What this means"
copy flowing in a generous wider column on the RIGHT. Eliminates the
wasted vertical space of the portrait v3/v4 cards and breaks the body
paragraph into far fewer lines (each line now ~70 characters instead of
~38), so the text feels open and editorial on mobile and desktop alike.

Reads heroes from /app/frontend/public/fb-assets/v4/.
Writes cards to   /app/frontend/public/fb-assets/v4-landscape/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERO_DIR = Path("/app/frontend/public/fb-assets/v4")
OUT_DIR = Path("/app/frontend/public/fb-assets/v4-landscape")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/app/scripts/fonts")
FONT_ITALIC = str(FONT_DIR / "CormorantGaramond-Italic.ttf")
FONT_REGULAR = str(FONT_DIR / "CormorantGaramond-Regular.ttf")
FONT_SEMIBOLD = str(FONT_DIR / "CormorantGaramond-SemiBold.ttf")

TEAL_DEEP = (44, 78, 90)        # #2C4E5A
GOLD = (168, 122, 74)           # #A87A4A
CARD_BG = (248, 242, 229)       # #F8F2E5

# Same verbatim copy as v4.
PHRASES = [
    {
        "idx": "01", "slug": "secure-connection",
        "phrase": "Secure connection is your birthright", "focal": "birthright",
        "body": (
            "This isn't aspirational. It's not \"if you're lucky\" or "
            "\"for some people.\" It's the constitutional truth that every "
            "human being arrives wired for, and worthy of, a steady, "
            "responsive bond. We don't earn secure attachment — we "
            "recognize it as the default we were built for, even when "
            "life pulled us away from it. To carry this phrase is to "
            "refuse the lie that connection has to be deserved, "
            "performed, or paid for."
        ),
        "punch": "You were born holding the deed.",
    },
    {
        "idx": "02", "slug": "founder-of-love-story",
        "phrase": "You are the founder of your own love story", "focal": "founder",
        "body": (
            "Most of us inherited a love story before we could write "
            "one — from our parents' marriage, our family's silences, "
            "our culture's clichés about how romance is supposed to go. "
            "To be the founder is to take the pen back. Not to discard "
            "what was given, but to author the next chapter consciously: "
            "who you love, how you love, what counts as a happy ending."
        ),
        "punch": (
            "The bond you build now isn't an extension of what came "
            "before — it's a fresh founding document, and you're the "
            "one signing it."
        ),
    },
    {
        "idx": "03", "slug": "created-for-connection",
        "phrase": "We are created for connection", "focal": "connection",
        "body": (
            "This is Sue Johnson's discovery dressed as theology and "
            "biology at the same time. Whether you read \"created\" as "
            "a divine act or a developmental one, the message is "
            "identical: your nervous system was not designed to thrive "
            "alone. The hunger you feel for closeness isn't a personal "
            "failing or a sign of weakness — it's the original blueprint "
            "asserting itself."
        ),
        "punch": (
            "We are not solitary creatures who occasionally bond. We are "
            "bonding creatures who occasionally find ourselves alone."
        ),
    },
    {
        "idx": "04", "slug": "bond-is-the-cure",
        "phrase": "The bond is the cure", "focal": "cure",
        "body": (
            "We chase cures in books, therapy, podcasts, and "
            "prescriptions. Sometimes one of them helps. But the deepest "
            "healing for relational wounds always comes through a "
            "different relationship — one that proves the old story "
            "wrong by living a steadier one in its place. The bond "
            "itself, when it is finally safe and responsive, becomes "
            "the medicine."
        ),
        "punch": "Not a metaphor. Not a side effect. The cure.",
    },
    {
        "idx": "05", "slug": "repair-is-older",
        "phrase": "Repair is older than rupture", "focal": "Repair",
        "body": (
            "Most people assume rupture comes first and repair is the "
            "scramble afterward. But mother-infant repair cycles begin "
            "in the first weeks of life — before any conscious wound is "
            "ever named. The dance of rupture-and-repair is the "
            "relationship; it's been native to you since before you had "
            "language for either."
        ),
        "punch": (
            "You don't have to learn repair from scratch. You have to "
            "remember it."
        ),
    },
]


# ---------- Layout constants (16:9 landscape) ----------------------------
CARD_W, CARD_H = 1920, 1080

# Left column = hero square; right column = text.
LEFT_PAD = 60
HERO_SIDE = 960                 # square fills most of the left half
HERO_X = LEFT_PAD
HERO_Y = (CARD_H - HERO_SIDE) // 2

TEXT_X = HERO_X + HERO_SIDE + 80
TEXT_W = CARD_W - TEXT_X - 80   # ~820 px wide column for copy


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
    out = OUT_DIR / f"fb-ls-{entry['idx']}-{entry['slug']}.png"
    hero_path = HERO_DIR / f"hero-{entry['idx']}-{entry['slug']}.png"
    if not hero_path.exists():
        raise FileNotFoundError(hero_path)

    card = Image.new("RGB", (CARD_W, CARD_H), CARD_BG)
    draw = ImageDraw.Draw(card)

    # ---- Hero square (left column) ----
    hero = Image.open(hero_path).convert("RGB")
    hw, hh = hero.size
    s = min(hw, hh)
    hero = hero.crop(((hw - s) // 2, (hh - s) // 2,
                      (hw + s) // 2, (hh + s) // 2))
    hero = hero.resize((HERO_SIDE, HERO_SIDE), Image.LANCZOS)
    card.paste(hero, (HERO_X, HERO_Y))

    # ---- Right column: top-down stack ----
    # Top gold hairline, phrase, body, punchline, footer.
    # We measure heights first so we can vertically centre the block.

    italic = ImageFont.truetype(FONT_ITALIC, 64)
    roman = ImageFont.truetype(FONT_SEMIBOLD, 66)
    body_font = ImageFont.truetype(FONT_ITALIC, 38)
    punch_font = ImageFont.truetype(FONT_ITALIC, 50)
    wm_font = ImageFont.truetype(FONT_REGULAR, 30)

    space_w = italic.getbbox(" ")[2]
    focal = entry["focal"].lower()

    def is_focal(t: str) -> bool:
        return t.strip(",.!?;:").lower() == focal

    def w_of(t: str) -> int:
        f = roman if is_focal(t) else italic
        b = f.getbbox(t)
        return b[2] - b[0]

    # Wrap phrase to TEXT_W (left-aligned, so we don't need centring math).
    tokens = entry["phrase"].split(" ")
    phrase_lines: list[list[str]] = [[]]
    cur_w = 0
    for t in tokens:
        tw = w_of(t)
        add = tw if not phrase_lines[-1] else space_w + tw
        if cur_w + add <= TEXT_W or not phrase_lines[-1]:
            phrase_lines[-1].append(t)
            cur_w += add
        else:
            phrase_lines.append([t])
            cur_w = tw

    body_lines = wrap(entry["body"], body_font, TEXT_W)
    punch_lines = wrap(entry["punch"], punch_font, TEXT_W)

    PHRASE_LH = 80
    BODY_LH = 54
    PUNCH_LH = 66

    rule_h = 4
    gap_rule_phrase = 30
    gap_phrase_body = 38
    gap_body_punch = 30

    block_h = (
        rule_h
        + gap_rule_phrase
        + len(phrase_lines) * PHRASE_LH
        + gap_phrase_body
        + len(body_lines) * BODY_LH
        + gap_body_punch
        + len(punch_lines) * PUNCH_LH
    )

    y = (CARD_H - block_h) // 2

    # Gold hairline (left-aligned, 120 wide).
    draw.rectangle((TEXT_X, y, TEXT_X + 140, y + rule_h), fill=GOLD)
    y += rule_h + gap_rule_phrase

    # Phrase
    for line in phrase_lines:
        x = TEXT_X
        for i, t in enumerate(line):
            f = roman if is_focal(t) else italic
            draw.text((x, y + (-2 if is_focal(t) else 0)),
                      t, font=f, fill=TEAL_DEEP)
            x += w_of(t) + (space_w if i < len(line) - 1 else 0)
        y += PHRASE_LH

    # Body
    y += gap_phrase_body
    for line in body_lines:
        draw.text((TEXT_X, y), line, font=body_font, fill=TEAL_DEEP)
        y += BODY_LH

    # Punchline
    y += gap_body_punch
    for line in punch_lines:
        draw.text((TEXT_X, y), line, font=punch_font, fill=TEAL_DEEP)
        y += PUNCH_LH

    # ---- Footer wordmark (bottom-right of text column) ----
    wm = "birthright.live"
    bb = wm_font.getbbox(wm)
    wm_w = bb[2] - bb[0]
    draw.text(
        (CARD_W - 80 - wm_w, CARD_H - 60),
        wm, font=wm_font, fill=GOLD,
    )

    card.save(out, "PNG", optimize=True)
    print(f"  ✓ landscape  {out.name}")
    return out


def main() -> None:
    print("Generating v4-landscape cards (1920x1080)…")
    for e in PHRASES:
        build_card(e)
    print("Done.")


if __name__ == "__main__":
    main()
