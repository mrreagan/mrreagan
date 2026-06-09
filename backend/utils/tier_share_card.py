"""Render a brand-aligned, social-shareable PNG announcing an artist's
tier transition. Pure Pillow — no external services, no Nano Banana
call, no per-image cost. SVG-style flat composition.

Open Graph aspect: 1200×630.
"""
from __future__ import annotations

import io
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


# Birthright brand palette (matches frontend CSS variables).
BG = (248, 244, 236)        # #F8F4EC — bone
INK = (26, 36, 36)          # #1A2424 — graphite
TEAL = (44, 78, 90)         # #2C4E5A — river-deep
GOLD = (201, 169, 97)       # #C9A961 — ochre-bright
MOSS = (46, 92, 70)         # #2E5C46 — moss
WARM = (168, 122, 74)       # #A87A4A — ochre-warm
SUBTLE = (92, 107, 107)     # #5C6B6B — graphite-light

# Tier accent colors keyed to the same tone the artist sees on their
# dashboard so the share artifact feels of-a-piece with the platform.
TIER_ACCENT = {
    "emerging":    MOSS,
    "sustaining":  MOSS,
    "established": TEAL,
    "thriving":    GOLD,
    "flourishing": GOLD,
}

SERIF_REG = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SERIF_ITAL = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
SERIF_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SANS_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _text_w(draw: ImageDraw.ImageDraw, text: str,
            font: ImageFont.FreeTypeFont) -> int:
    """Width of a text string in the given font, Pillow-version-safe."""
    if hasattr(draw, "textlength"):
        return int(draw.textlength(text, font=font))
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def render_tier_share_png(
    *,
    tier_label: str,
    tier_icon: str,
    tier_key: str,
    artist_name: str,
    referral_url: str,
    headline: str = "I just reached",
    tagline: str = "Patronage with character.",
) -> bytes:
    """Compose the share card and return raw PNG bytes."""
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    accent = TIER_ACCENT.get(tier_key, TEAL)

    # Left accent column — a quiet vertical band like a magazine pull-tab.
    draw.rectangle([(0, 0), (24, H)], fill=accent)

    # Top label — small all-caps.
    label = _font(SANS_BOLD, 22)
    draw.text((80, 70), "BIRTHRIGHT  ·  ARTIST PATRONAGE",
              fill=SUBTLE, font=label)

    # Headline.
    f_head = _font(SERIF_ITAL, 56)
    draw.text((80, 130), headline, fill=INK, font=f_head)

    # Big tier line. Color emojis aren't reliably rasterized by Pillow's
    # default TTFs, so the PNG composition uses a typographic accent
    # (small filled disc) on the left rather than the unicode emoji.
    # The SVG variant + share text + social previews keep the emoji.
    f_tier = _font(SERIF_BOLD, 132)
    disc_r = 30
    disc_cx = 80 + disc_r
    disc_cy = 270
    draw.ellipse(
        [(disc_cx - disc_r, disc_cy - disc_r),
         (disc_cx + disc_r, disc_cy + disc_r)],
        fill=accent,
    )
    draw.text((80 + disc_r * 2 + 24, 210), tier_label, fill=accent, font=f_tier)

    # Underline rule beneath the tier line.
    draw.rectangle([(80, 370), (260, 374)], fill=accent)

    # Artist attribution.
    f_artist = _font(SERIF_ITAL, 38)
    if artist_name:
        draw.text((80, 396), f"— {artist_name}", fill=INK, font=f_artist)

    # Tagline.
    f_tag = _font(SERIF_REG, 26)
    draw.text((80, 460), tagline, fill=SUBTLE, font=f_tag)

    # Footer: referral URL + brand wordmark.
    f_url = _font(SANS_REG, 22)
    f_brand = _font(SERIF_BOLD, 28)
    draw.text((80, H - 70), referral_url, fill=TEAL, font=f_url)
    brand = "birthright.live"
    bw = _text_w(draw, brand, f_brand)
    draw.text((W - bw - 60, H - 78), brand, fill=INK, font=f_brand)

    # Subtle baseline rule.
    draw.rectangle([(80, H - 95), (W - 60, H - 93)], fill=(229, 225, 216))

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def render_tier_share_svg(
    *,
    tier_label: str,
    tier_icon: str,
    tier_key: str,
    artist_name: str,
    referral_url: str,
    headline: str = "I just reached",
    tagline: str = "Patronage with character.",
) -> str:
    """A simple SVG variant of the same composition. Browsers can
    download this and convert client-side if they want a hi-res
    vector copy; otherwise the PNG endpoint is the canonical sharable
    artifact (Open Graph friendly)."""
    accent = "#%02X%02X%02X" % TIER_ACCENT.get(tier_key, TEAL)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <rect width="1200" height="630" fill="#F8F4EC"/>
  <rect x="0" y="0" width="24" height="630" fill="{accent}"/>
  <text x="80" y="92" font-family="Liberation Sans, Helvetica, Arial, sans-serif"
        font-size="22" font-weight="700" letter-spacing="2" fill="#5C6B6B">
    BIRTHRIGHT  ·  ARTIST PATRONAGE
  </text>
  <text x="80" y="180" font-family="Liberation Serif, Georgia, serif"
        font-size="56" font-style="italic" fill="#1A2424">{headline}</text>
  <text x="80" y="328" font-family="Liberation Serif, Georgia, serif"
        font-size="132" font-weight="700" fill="{accent}">
    {tier_icon}  {tier_label}
  </text>
  <rect x="80" y="370" width="180" height="4" fill="{accent}"/>
  <text x="80" y="430" font-family="Liberation Serif, Georgia, serif"
        font-size="38" font-style="italic" fill="#1A2424">— {artist_name}</text>
  <text x="80" y="490" font-family="Liberation Serif, Georgia, serif"
        font-size="26" fill="#5C6B6B">{tagline}</text>
  <rect x="80" y="535" width="1060" height="2" fill="#E5E1D8"/>
  <text x="80" y="572" font-family="Liberation Sans, Helvetica, Arial, sans-serif"
        font-size="22" fill="#2C4E5A">{referral_url}</text>
  <text x="1140" y="565" text-anchor="end" font-family="Liberation Serif, Georgia, serif"
        font-size="28" font-weight="700" fill="#1A2424">birthright.live</text>
</svg>"""
