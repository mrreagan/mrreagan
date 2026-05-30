"""Auto-generated journal PDFs for Lulu (Phase 5b).

Produces two Lulu-compliant PDFs from an AI-generated cover image:
  1) Interior: lined journal pages, N pages total, 5.5×8.5 trim + 0.125" bleed.
  2) Cover: back + spine + front, single page wrap, using the AI cover image.

Lulu requirements honored:
  - Bleed: 0.125" on every outside edge
  - Safety margin: 0.5" from trim
  - sRGB (reportlab defaults to DeviceRGB which Lulu accepts)
  - Embedded fonts (reportlab embeds by default for non-system fonts; we use Helvetica which Lulu accepts as a Type 1 base font)
  - Flattened, no transparency

Currently supports the journal 5.5×8.5 BW paperback spec
(pod_package_id=0550X0850BWSTDPB060UW444MXX). Other specs will need their own
TRIM_SIZES + spine math.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PIL import Image
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

logger = logging.getLogger("birthright.journal_pdf")

# ---- Embedded fonts (Lulu requires ALL fonts to be embedded; the base-14
# PDF fonts like Helvetica are NOT considered embedded). ReportLab ships
# Bitstream Vera which we register here as our prose and display faces.
import reportlab as _rl  # noqa: PLC0415
_RL_FONTS = Path(_rl.__file__).resolve().parent / "fonts"
_FONTS_REGISTERED = False


def _ensure_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("BirthrightSerif", str(_RL_FONTS / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("BirthrightSerif-Bold", str(_RL_FONTS / "VeraBd.ttf")))
    pdfmetrics.registerFont(TTFont("BirthrightSerif-Italic", str(_RL_FONTS / "VeraIt.ttf")))
    _FONTS_REGISTERED = True


FONT_BODY = "BirthrightSerif"
FONT_BOLD = "BirthrightSerif-Bold"

# ============ Interior style registry ============
INTERIOR_STYLES = {
    "lined": "Classic lined pages, ~22 ruled lines per page. Default for general journaling.",
    "blank": "No rules at all. Best for morning pages, free writing, sketching.",
    "dot_grid": "5mm dot grid. Best for bullet journaling, habit trackers, sketchnotes.",
    "split_top_blank_bottom_lined": "Top half blank for a sketch or intention, bottom half lined for notes. Best for daily intentions, drawings + reflection.",
    "dated_lined": "A small horizontal rule at the top for a date + lined body below. Best for diaries, dated journals.",
    "habit_tracker": "31-day habit tracker grid on the left, with lined notes on the right. Best for habit trackers, gratitude logs.",
}
DEFAULT_INTERIOR_STYLE = "lined"

# ============ Spec table ============
# Per Lulu 5.5×8.5 paperback BW 60# uncoated:
# - bleed: 0.125" all sides
# - spine: pages × 0.002252" for 60# uncoated B&W (Lulu published formula)
# Reference: developers.lulu.com → product specs → cover dimensions calculator
TRIM_W = 5.5 * inch
TRIM_H = 8.5 * inch
BLEED = 0.125 * inch
SAFETY = 0.5 * inch
PAGE_W = TRIM_W + 2 * BLEED
PAGE_H = TRIM_H + 2 * BLEED

SPINE_PER_PAGE = 0.002252 * inch  # 60# uncoated B&W; produces ~0.32" for 144pp
# Lulu's validator tolerates spine widths inside a ~0.125" window around the
# formula value, so we pad the spine by 0.06" to land in the middle of the
# accepted tolerance (avoids edge-of-window rejections due to PDF rounding).
SPINE_BINDING_ALLOWANCE = 0.06 * inch

# Lined paper rules
RULE_SPACING = 0.31 * inch  # ~0.31" between rules; ~22 lines per page
RULE_COLOR = HexColor("#E8E2D5")  # cream-warm rule color, very soft
PAGE_NUMBER_COLOR = HexColor("#C9A961")


# ============ Interior ============
def generate_interior_pdf(
    output_path: Path,
    page_count: int = 144,
    title: Optional[str] = None,
    show_page_numbers: bool = True,
    style: str = DEFAULT_INTERIOR_STYLE,
) -> Path:
    """Generate an interior PDF in the requested style.

    page_count must be a multiple of 4 for perfect-binding signatures.
    We coerce upward.
    """
    if page_count < 4:
        raise ValueError("page_count must be ≥ 4")
    if page_count % 4 != 0:
        page_count = page_count + (4 - page_count % 4)
    if style not in INTERIOR_STYLES:
        logger.warning("unknown interior style '%s' — falling back to '%s'", style, DEFAULT_INTERIOR_STYLE)
        style = DEFAULT_INTERIOR_STYLE

    _ensure_fonts()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    c.setTitle(title or "Birthright Journal")
    c.setAuthor("Birthright Foundation")

    drawer = _STYLE_DRAWERS.get(style, _draw_lined_page)
    for page_num in range(1, page_count + 1):
        drawer(c, page_num, show_page_numbers)
        c.showPage()

    c.save()
    logger.info("Generated interior PDF: %s (%s pages, style=%s)", output_path, page_count, style)
    return output_path


def _page_bounds(show_page_numbers: bool) -> tuple[float, float, float, float]:
    """Return (left, right, top, bottom) of the printable area within safety."""
    left = BLEED + SAFETY
    right = PAGE_W - BLEED - SAFETY
    top = PAGE_H - BLEED - SAFETY
    bottom = BLEED + SAFETY + (0.4 * inch if show_page_numbers else 0)
    return left, right, top, bottom


def _draw_page_number(c: canvas.Canvas, page_num: int) -> None:
    c.setFillColor(PAGE_NUMBER_COLOR)
    c.setFont(FONT_BODY, 8)
    c.drawCentredString(PAGE_W / 2, BLEED + SAFETY * 0.4, str(page_num))


def _draw_lined_page(c: canvas.Canvas, page_num: int, show_page_numbers: bool) -> None:
    left, right, top, bottom = _page_bounds(show_page_numbers)
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.5)
    y = top
    while y >= bottom:
        c.line(left, y, right, y)
        y -= RULE_SPACING
    if show_page_numbers:
        _draw_page_number(c, page_num)


def _draw_blank_page(c: canvas.Canvas, page_num: int, show_page_numbers: bool) -> None:
    """Truly blank — only the page number (if enabled)."""
    if show_page_numbers:
        _draw_page_number(c, page_num)


def _draw_dot_grid_page(c: canvas.Canvas, page_num: int, show_page_numbers: bool) -> None:
    """5mm dot grid (≈0.197") across the safe area."""
    left, right, top, bottom = _page_bounds(show_page_numbers)
    spacing = 0.2 * inch  # ~5mm
    dot_radius = 0.4  # in points
    c.setFillColor(RULE_COLOR)
    c.setStrokeColor(RULE_COLOR)
    y = top
    while y >= bottom:
        x = left
        while x <= right:
            c.circle(x, y, dot_radius, stroke=0, fill=1)
            x += spacing
        y -= spacing
    if show_page_numbers:
        _draw_page_number(c, page_num)


def _draw_split_page(c: canvas.Canvas, page_num: int, show_page_numbers: bool) -> None:
    """Top half blank (for sketch/intention), bottom half lined."""
    left, right, top, bottom = _page_bounds(show_page_numbers)
    mid = bottom + (top - bottom) / 2
    # A soft cream divider between the halves
    c.setStrokeColor(HexColor("#D9D1BD"))
    c.setLineWidth(0.7)
    c.line(left, mid, right, mid)
    # Lines in the bottom half
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.5)
    y = mid - RULE_SPACING * 0.6
    while y >= bottom:
        c.line(left, y, right, y)
        y -= RULE_SPACING
    if show_page_numbers:
        _draw_page_number(c, page_num)


def _draw_dated_lined_page(c: canvas.Canvas, page_num: int, show_page_numbers: bool) -> None:
    """A date rule across the top, then lined body below."""
    left, right, top, bottom = _page_bounds(show_page_numbers)
    # Date area marker
    c.setStrokeColor(HexColor("#C9A961"))
    c.setLineWidth(0.6)
    date_y = top - 0.15 * inch
    c.line(left, date_y, left + 2.5 * inch, date_y)
    c.setFillColor(PAGE_NUMBER_COLOR)
    c.setFont(FONT_BODY, 7)
    c.drawString(left, date_y - 0.12 * inch, "DATE")
    # Lined body starting below the date band
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.5)
    y = date_y - 0.6 * inch
    while y >= bottom:
        c.line(left, y, right, y)
        y -= RULE_SPACING
    if show_page_numbers:
        _draw_page_number(c, page_num)


def _draw_habit_tracker_page(c: canvas.Canvas, page_num: int, show_page_numbers: bool) -> None:
    """31-day habit checklist on the left third, lined notes on the right two-thirds."""
    left, right, top, bottom = _page_bounds(show_page_numbers)
    # Divider at ~38% of width
    div_x = left + (right - left) * 0.38
    c.setStrokeColor(HexColor("#D9D1BD"))
    c.setLineWidth(0.7)
    c.line(div_x, top, div_x, bottom)
    # Header
    c.setFillColor(HexColor("#0F2424"))
    c.setFont(FONT_BOLD, 9)
    c.drawString(left, top - 0.05 * inch, "HABIT")
    c.drawString(div_x + 0.15 * inch, top - 0.05 * inch, "NOTES")
    # 31-day checkbox column on the left
    rows = 31
    avail = top - bottom - 0.2 * inch
    step = avail / rows
    c.setStrokeColor(RULE_COLOR)
    c.setLineWidth(0.5)
    c.setFont(FONT_BODY, 7)
    c.setFillColor(HexColor("#5C6B6B"))
    y = top - 0.35 * inch
    for d in range(1, rows + 1):
        c.drawString(left, y - 0.05 * inch, f"{d:02d}")
        # Small square checkbox
        box_x = left + 0.3 * inch
        c.rect(box_x, y - 0.08 * inch, 0.14 * inch, 0.14 * inch, stroke=1, fill=0)
        y -= step
    # Lined notes on the right
    c.setStrokeColor(RULE_COLOR)
    note_left = div_x + 0.15 * inch
    y = top - 0.35 * inch
    while y >= bottom:
        c.line(note_left, y, right, y)
        y -= RULE_SPACING
    if show_page_numbers:
        _draw_page_number(c, page_num)


_STYLE_DRAWERS: dict = {
    "lined": _draw_lined_page,
    "blank": _draw_blank_page,
    "dot_grid": _draw_dot_grid_page,
    "split_top_blank_bottom_lined": _draw_split_page,
    "dated_lined": _draw_dated_lined_page,
    "habit_tracker": _draw_habit_tracker_page,
}


# ============ Cover ============
def compute_spine_width(page_count: int) -> float:
    """Lulu 60# uncoated B&W spine width formula + binding allowance to land
    safely within Lulu's accepted tolerance window."""
    return page_count * SPINE_PER_PAGE + SPINE_BINDING_ALLOWANCE


def generate_cover_pdf(
    output_path: Path,
    cover_image_path: Path,
    page_count: int = 144,
    title: str = "Birthright Journal",
    subtitle: Optional[str] = None,
) -> Path:
    """Generate a one-piece cover PDF (back + spine + front) using the AI image.

    The AI image is anchored on the FRONT panel (right portion of the spread).
    Back panel + spine are left in cream with the title typeset on the spine.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_fonts()

    spine_w = compute_spine_width(page_count)
    # Full cover dimensions (back + spine + front + bleed on all sides)
    cover_w = (TRIM_W * 2) + spine_w + (BLEED * 2)
    cover_h = TRIM_H + (BLEED * 2)

    c = canvas.Canvas(str(output_path), pagesize=(cover_w, cover_h), pageCompression=1)
    c.setTitle(title)
    c.setAuthor("Birthright Foundation")

    # 1) Cream base across the full spread (so back + spine match the front aesthetic)
    cream = HexColor("#F4F1EA")
    c.setFillColor(cream)
    c.rect(0, 0, cover_w, cover_h, stroke=0, fill=1)

    # 2) Place AI cover image on the FRONT panel (right portion)
    front_x = BLEED + TRIM_W + spine_w  # left edge of front trim
    front_w = TRIM_W + BLEED              # extends to right bleed edge
    front_y = 0
    front_h = cover_h

    # Bleed the image slightly past trim on the front-right + top + bottom for safety
    img_x = front_x - BLEED  # extend into spine seam by 0.125" so no white gap
    img_w = front_w + BLEED
    if Path(cover_image_path).exists():
        try:
            # Use PIL to convert to RGB if needed (Lulu wants sRGB, no alpha)
            with Image.open(cover_image_path) as im:
                if im.mode != "RGB":
                    im = im.convert("RGB")
                rgb_path = output_path.parent / f"{output_path.stem}_cover_rgb.jpg"
                im.save(rgb_path, "JPEG", quality=92)
            c.drawImage(
                str(rgb_path), img_x, front_y, width=img_w, height=front_h,
                preserveAspectRatio=False, mask="auto",
            )
        except Exception:
            logger.exception("Failed to place cover image, falling back to text-only front")
            _draw_text_front(c, front_x, front_y, front_w, front_h, title, subtitle)
    else:
        _draw_text_front(c, front_x, front_y, front_w, front_h, title, subtitle)

    # 3) Spine — vertical title text in cream
    spine_x = BLEED + TRIM_W
    _draw_spine(c, spine_x, BLEED, spine_w, TRIM_H, title)

    # 4) Back panel — simple Birthright tagline within safety margin
    back_x = BLEED
    _draw_back(c, back_x, BLEED, TRIM_W, TRIM_H)

    c.save()
    logger.info("Generated cover PDF: %s (page_count=%s, spine=%.3f\")", output_path, page_count, spine_w / inch)
    return output_path


def _draw_text_front(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str, subtitle: Optional[str]) -> None:
    c.setFillColor(HexColor("#0F2424"))
    c.setFont(FONT_BOLD, 36)
    c.drawCentredString(x + w / 2, y + h / 2 + 0.4 * inch, title)
    if subtitle:
        c.setFont(FONT_BODY, 14)
        c.setFillColor(HexColor("#5C6B6B"))
        c.drawCentredString(x + w / 2, y + h / 2 - 0.4 * inch, subtitle)


def _draw_spine(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str) -> None:
    """Vertical title text running spine bottom-to-top."""
    if w < 0.25 * inch:
        return  # spine too thin to typeset reliably
    c.saveState()
    c.translate(x + w / 2, y + 1.0 * inch)
    c.rotate(90)
    c.setFillColor(HexColor("#0F2424"))
    font_size = min(14, max(8, int(w / inch * 24)))
    c.setFont(FONT_BOLD, font_size)
    c.drawString(0, -font_size * 0.35, title[:42])
    c.restoreState()


def _draw_back(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    """Simple back panel: small mark + tagline, all within safety margin."""
    safe_x = x + SAFETY
    safe_y = y + SAFETY
    safe_w = w - 2 * SAFETY
    c.setFillColor(HexColor("#5C6B6B"))
    c.setFont(FONT_BODY, 10)
    c.drawString(safe_x, safe_y + 0.5 * inch, "Birthright Foundation")
    c.setFillColor(HexColor("#0F2424"))
    c.setFont(FONT_BODY, 11)
    tagline_y = safe_y + h - 2.0 * inch
    c.drawString(safe_x, tagline_y, "A journal for the work of becoming.")
    # Decorative rule
    c.setStrokeColor(HexColor("#C9A961"))
    c.setLineWidth(0.5)
    c.line(safe_x, tagline_y - 0.2 * inch, safe_x + safe_w * 0.3, tagline_y - 0.2 * inch)
    # Small footer in cream
    _ = white  # keep import used in case of future panels


def generate_pair(
    *,
    cover_image_path: Path,
    output_dir: Path,
    product_id: str,
    page_count: int = 144,
    title: str = "Birthright Journal",
    interior_style: str = DEFAULT_INTERIOR_STYLE,
) -> tuple[Path, Path]:
    """Convenience: generate both PDFs side-by-side for a product."""
    output_dir = Path(output_dir)
    interior_path = output_dir / f"interior-{product_id}.pdf"
    cover_path = output_dir / f"cover-{product_id}.pdf"
    generate_interior_pdf(interior_path, page_count=page_count, title=title, style=interior_style)
    generate_cover_pdf(cover_path, cover_image_path, page_count=page_count, title=title)
    return interior_path, cover_path
