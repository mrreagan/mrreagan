"""Build .ics calendar files and QR-code PNGs for workshop emails."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import qrcode
from ics import Calendar, Event


def build_ics(workshop: dict) -> bytes:
    """Return raw ics file bytes for a single workshop event."""
    cal = Calendar()
    ev = Event()
    ev.name = workshop.get("title", "Birthright workshop")
    if workshop.get("start_date"):
        ev.begin = workshop["start_date"]
    if workshop.get("end_date"):
        ev.end = workshop["end_date"]
    loc = ", ".join(filter(None, [workshop.get("location_name"), workshop.get("location_address")]))
    if loc:
        ev.location = loc
    ev.description = workshop.get("short_description") or workshop.get("full_description") or ""
    ev.organizer = "Birthright Foundation"
    cal.events.add(ev)
    return str(cal).encode("utf-8")


def build_qr_png(content: str, box_size: int = 8) -> bytes:
    """Return PNG bytes of a QR code encoding `content`."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1A2424", back_color="#FAF8F5")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
