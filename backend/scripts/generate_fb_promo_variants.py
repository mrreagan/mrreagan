"""V4 multi-format variants — IG square, IG Story/Reel, Twitter/X.

Reuses the existing v4 heroes (no Nano Banana cost). Code-composites three
extra sizes per phrase so a single campaign can drop straight into every
major social surface without re-shooting.

  • IG square      1080 × 1080  — hero centred, small caption strip
  • IG Story/Reel  1080 × 1920  — hero on top, full caption beneath
  • Twitter/X      1600 ×  900  — hero left, caption right (similar to FB
                                  landscape but at Twitter's native ratio)

Output: /app/frontend/public/fb-assets/v4-multi/
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERO_DIR = Path("/app/frontend/public/fb-assets/v4")
OUT_DIR = Path("/app/frontend/public/fb-assets/v4-multi")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/app/scripts/fonts")
FONT_ITALIC = str(FONT_DIR / "CormorantGaramond-Italic.ttf")
FONT_REGULAR = str(FONT_DIR / "CormorantGaramond-Regular.ttf")
FONT_SEMIBOLD = str(FONT_DIR / "CormorantGaramond-SemiBold.ttf")

TEAL_DEEP = (44, 78, 90)
GOLD = (168, 122, 74)
CARD_BG = (248, 242, 229)

# Same verbatim copy as v3/v4.
PHRASES = [
    {"idx": "01", "slug": "secure-connection",
     "phrase": "Secure connection is your birthright", "focal": "birthright",
     "body": (
         "This isn't aspirational. It's not \"if you're lucky\" or \"for "
         "some people.\" It's the constitutional truth that every human "
         "being arrives wired for, and worthy of, a steady, responsive "
         "bond. We don't earn secure attachment — we recognize it as the "
         "default we were built for, even when life pulled us away from "
         "it. To carry this phrase is to refuse the lie that connection "
         "has to be deserved, performed, or paid for."
     ),
     "punch": "You were born holding the deed."},
    {"idx": "02", "slug": "founder-of-love-story",
     "phrase": "You are the founder of your own love story", "focal": "founder",
     "body": (
         "Most of us inherited a love story before we could write one — "
         "from our parents' marriage, our family's silences, our "
         "culture's clichés about how romance is supposed to go. To be "
         "the founder is to take the pen back. Not to discard what was "
         "given, but to author the next chapter consciously: who you "
         "love, how you love, what counts as a happy ending."
     ),
     "punch": (
         "The bond you build now isn't an extension of what came "
         "before — it's a fresh founding document, and you're the one "
         "signing it."
     )},
    {"idx": "03", "slug": "created-for-connection",
     "phrase": "We are created for connection", "focal": "connection",
     "body": (
         "This is Sue Johnson's discovery dressed as theology and "
         "biology at the same time. Whether you read \"created\" as a "
         "divine act or a developmental one, the message is identical: "
         "your nervous system was not designed to thrive alone. The "
         "hunger you feel for closeness isn't a personal failing or a "
         "sign of weakness — it's the original blueprint asserting "
         "itself."
     ),
     "punch": (
         "We are not solitary creatures who occasionally bond. We are "
         "bonding creatures who occasionally find ourselves alone."
     )},
    {"idx": "04", "slug": "bond-is-the-cure",
     "phrase": "The bond is the cure", "focal": "cure",
     "body": (
         "We chase cures in books, therapy, podcasts, and "
         "prescriptions. Sometimes one of them helps. But the deepest "
         "healing for relational wounds always comes through a "
         "different relationship — one that proves the old story wrong "
         "by living a steadier one in its place. The bond itself, when "
         "it is finally safe and responsive, becomes the medicine."
     ),
     "punch": "Not a metaphor. Not a side effect. The cure."},
    {"idx": "05", "slug": "repair-is-older",
     "phrase": "Repair is older than rupture", "focal": "Repair",
     "body": (
         "Most people assume rupture comes first and repair is the "
         "scramble afterward. But mother-infant repair cycles begin in "
         "the first weeks of life — before any conscious wound is ever "
         "named. The dance of rupture-and-repair is the relationship; "
         "it's been native to you since before you had language for "
         "either."
     ),
     "punch": (
         "You don't have to learn repair from scratch. You have to "
         "remember it."
     )},
]


def wrap(text, font, max_w):
    words = text.split()
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if font.getbbox(trial)[2] <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur)); cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _hero(entry, side):
    """Load hero, centre-crop to square, resize to `side`."""
    p = HERO_DIR / f"hero-{entry['idx']}-{entry['slug']}.png"
    img = Image.open(p).convert("RGB")
    hw, hh = img.size
    s = min(hw, hh)
    img = img.crop(((hw - s) // 2, (hh - s) // 2,
                    (hw + s) // 2, (hh + s) // 2))
    return img.resize((side, side), Image.LANCZOS)


def _phrase_block(draw, entry, x, y, width, italic_size, roman_size, line_h, fill):
    """Render the phrase wrapping to `width`, left-aligned, with bold focal.
    Returns the y position immediately after the phrase block."""
    italic = ImageFont.truetype(FONT_ITALIC, italic_size)
    roman = ImageFont.truetype(FONT_SEMIBOLD, roman_size)
    space_w = italic.getbbox(" ")[2]
    focal = entry["focal"].lower()

    def is_focal(t): return t.strip(",.!?;:").lower() == focal

    def w_of(t):
        f = roman if is_focal(t) else italic
        return f.getbbox(t)[2] - f.getbbox(t)[0]

    tokens = entry["phrase"].split(" ")
    lines = [[]]
    cur_w = 0
    for t in tokens:
        tw = w_of(t)
        add = tw if not lines[-1] else space_w + tw
        if cur_w + add <= width or not lines[-1]:
            lines[-1].append(t); cur_w += add
        else:
            lines.append([t]); cur_w = tw

    for line in lines:
        cx = x
        for i, t in enumerate(line):
            f = roman if is_focal(t) else italic
            draw.text((cx, y + (-2 if is_focal(t) else 0)),
                      t, font=f, fill=fill)
            cx += w_of(t) + (space_w if i < len(line) - 1 else 0)
        y += line_h
    return y


# ---------- IG Square 1080×1080 -----------------------------------------
def build_ig_square(entry):
    """Hero fills the canvas; small caption strip overlay along the bottom
    with phrase + punchline (body omitted — too cramped at this size)."""
    out = OUT_DIR / f"ig-sq-{entry['idx']}-{entry['slug']}.png"
    W, H = 1080, 1080
    card = Image.new("RGB", (W, H), CARD_BG)
    draw = ImageDraw.Draw(card)

    # Hero fills almost the whole frame.
    hero = _hero(entry, W)
    card.paste(hero, (0, 0))

    # Cream strip overlay across the bottom.
    strip_h = 280
    strip = Image.new("RGBA", (W, strip_h), CARD_BG + (245,))
    card.paste(strip, (0, H - strip_h), strip)

    side = 70
    y = H - strip_h + 36
    # Phrase
    y = _phrase_block(draw, entry, side, y, W - 2 * side,
                       italic_size=42, roman_size=44, line_h=52, fill=TEAL_DEEP)
    # Gold rule + punchline (short — single line preferred at this scale)
    draw.rectangle((side, y + 14, side + 100, y + 16), fill=GOLD)
    pf = ImageFont.truetype(FONT_ITALIC, 34)
    punch_lines = wrap(entry["punch"], pf, W - 2 * side)
    y += 32
    for ln in punch_lines[:2]:
        draw.text((side, y), ln, font=pf, fill=TEAL_DEEP)
        y += 44
    card.save(out, "PNG", optimize=True)
    print(f"  ✓ IG square  {out.name}")
    return out


# ---------- IG Story / Reel 1080×1920 ------------------------------------
def build_ig_story(entry):
    """Hero at the top covering ~55% of height, then full caption beneath."""
    out = OUT_DIR / f"ig-story-{entry['idx']}-{entry['slug']}.png"
    W, H = 1080, 1920
    card = Image.new("RGB", (W, H), CARD_BG)
    draw = ImageDraw.Draw(card)

    # Hero — full width, square (cropped at bottom by canvas).
    hero = _hero(entry, W)
    card.paste(hero, (0, 80))

    side = 80
    y = 80 + W + 60  # below hero square

    # Gold rule
    draw.rectangle((W // 2 - 90, y, W // 2 + 90, y + 3), fill=GOLD)
    y += 38

    # Phrase (centred — use existing centred phrase renderer is complex;
    # simpler: render left-aligned within centred max-width window)
    y = _phrase_block(draw, entry, side, y, W - 2 * side,
                       italic_size=58, roman_size=60, line_h=72, fill=TEAL_DEEP)
    y += 18

    # Body
    bf = ImageFont.truetype(FONT_ITALIC, 32)
    for line in wrap(entry["body"], bf, W - 2 * side):
        draw.text((side, y), line, font=bf, fill=TEAL_DEEP)
        y += 46

    # Punchline
    pf = ImageFont.truetype(FONT_ITALIC, 44)
    y += 26
    for line in wrap(entry["punch"], pf, W - 2 * side):
        draw.text((side, y), line, font=pf, fill=TEAL_DEEP)
        y += 60

    # Footer
    wf = ImageFont.truetype(FONT_REGULAR, 28)
    wm = "birthright.live"
    bb = wf.getbbox(wm)
    draw.text(((W - (bb[2] - bb[0])) // 2, H - 70),
              wm, font=wf, fill=GOLD)
    card.save(out, "PNG", optimize=True)
    print(f"  ✓ IG story   {out.name}")
    return out


# ---------- Twitter/X 1600×900 -------------------------------------------
def build_twitter(entry):
    """Twitter feed-native 16:9. Hero left square, caption right column."""
    out = OUT_DIR / f"tw-{entry['idx']}-{entry['slug']}.png"
    W, H = 1600, 900
    card = Image.new("RGB", (W, H), CARD_BG)
    draw = ImageDraw.Draw(card)

    HERO_SIDE = 820
    HERO_X, HERO_Y = 50, (H - HERO_SIDE) // 2
    card.paste(_hero(entry, HERO_SIDE), (HERO_X, HERO_Y))

    text_x = HERO_X + HERO_SIDE + 60
    text_w = W - text_x - 70

    italic_size, roman_size, phrase_lh = 50, 52, 64
    body_font = ImageFont.truetype(FONT_ITALIC, 28)
    punch_font = ImageFont.truetype(FONT_ITALIC, 40)
    wm_font = ImageFont.truetype(FONT_REGULAR, 24)

    # Pre-measure for vertical centring.
    tokens = entry["phrase"].split(" ")
    # Approximate phrase line count by re-using wrap with italic.
    tmp_italic = ImageFont.truetype(FONT_ITALIC, italic_size)
    phrase_lines = wrap(entry["phrase"], tmp_italic, text_w)
    body_lines = wrap(entry["body"], body_font, text_w)
    punch_lines = wrap(entry["punch"], punch_font, text_w)
    body_lh, punch_lh = 40, 54

    block_h = (4 + 26
               + len(phrase_lines) * phrase_lh + 26
               + len(body_lines) * body_lh + 22
               + len(punch_lines) * punch_lh)
    y = (H - block_h) // 2

    draw.rectangle((text_x, y, text_x + 110, y + 3), fill=GOLD)
    y += 30

    y = _phrase_block(draw, entry, text_x, y, text_w,
                       italic_size=italic_size, roman_size=roman_size,
                       line_h=phrase_lh, fill=TEAL_DEEP)
    y += 18

    for line in body_lines:
        draw.text((text_x, y), line, font=body_font, fill=TEAL_DEEP)
        y += body_lh

    y += 18
    for line in punch_lines:
        draw.text((text_x, y), line, font=punch_font, fill=TEAL_DEEP)
        y += punch_lh

    wm = "birthright.live"
    bb = wm_font.getbbox(wm)
    draw.text((W - 70 - (bb[2] - bb[0]), H - 50),
              wm, font=wm_font, fill=GOLD)
    card.save(out, "PNG", optimize=True)
    print(f"  ✓ Twitter    {out.name}")
    return out


def main():
    print("Generating v4 multi-format variants…")
    for e in PHRASES:
        build_ig_square(e)
        build_ig_story(e)
        build_twitter(e)
    print("Done.")


if __name__ == "__main__":
    main()
