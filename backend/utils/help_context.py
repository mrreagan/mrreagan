"""Live platform context for the AI help assistant.

The static KB at `data/help_kb.json` covers high-frequency how-to questions,
but it can't keep up with people, products, and published work. This module
compiles a single compact "fact pack" out of the live database — leadership,
mission/about, partner profiles, equip catalog, workshops, research, and the
site map — refreshed every few minutes and injected into every LLM-fallback
turn.

The goal is simple: the assistant should answer ANY question whose answer
exists on birthright.live, with confidence, citing what's on-site —
and should only suggest contacting a human for account-specific or billing
issues it can't resolve itself.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger("birthright.help.context")

# Cache the assembled context for this many seconds. Long enough to keep
# token spend down across rapid-fire questions, short enough that newly
# published artifacts (new partner, new product, new research) appear
# within a working session.
_CACHE_TTL_SECONDS = 300

_CACHE: dict[str, Any] = {"text": "", "ts": 0.0}
_LOCK = asyncio.Lock()


def _truncate(s: str | None, n: int) -> str:
    if not s:
        return ""
    s = " ".join(s.split())  # collapse whitespace
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


async def _collect(db) -> str:
    """Build a compact human-readable platform fact pack."""
    sections: list[str] = []

    # ─── Foundation identity ──────────────────────────────────────────
    fc = await db.foundation_content.find_one({"key": "content"}, {"_id": 0}) or {}
    if fc:
        sections.append("FOUNDATION OVERVIEW:")
        if fc.get("mission_statement"):
            sections.append(f"  Mission: {_truncate(fc['mission_statement'], 320)}")
        if fc.get("about_text"):
            sections.append(f"  About: {_truncate(fc['about_text'], 420)}")
        if fc.get("vision"):
            sections.append(f"  Vision: {_truncate(fc['vision'], 240)}")
        if fc.get("education_structure"):
            sections.append(f"  Education structure: {_truncate(fc['education_structure'], 380)}")
        if isinstance(fc.get("values"), list):
            vals = " · ".join(str(v)[:80] for v in fc["values"][:6])
            if vals:
                sections.append(f"  Values: {vals}")
        sections.append("")

    # ─── Leadership / governing members ────────────────────────────────
    members = await db.governing_members.find({}, {"_id": 0}).sort("order", 1).to_list(20)
    if members:
        real = [m for m in members if not m.get("is_sample")]
        samples = [m for m in members if m.get("is_sample")]
        sections.append("LEADERSHIP — actual current officers (see /lead):")
        for m in real:
            line = f"  - {m.get('name')} — {m.get('title','')}"
            if m.get("bio"):
                line += f". {_truncate(m['bio'], 220)}"
            if m.get("image_caption"):
                line += f" [Photo description: {_truncate(m['image_caption'], 260)}]"
            sections.append(line)
        if samples:
            sections.append("")
            sections.append(
                "LEADERSHIP — placeholder/sample bios (NOT real officers; "
                "shown on /lead as illustrations of roles the foundation is "
                "building toward — never present these as actual people. "
                "Image descriptions ARE available so you can answer 'what "
                "does the photo look like?' questions; just remind the visitor "
                "the person is illustrative):"
            )
            for m in samples:
                line = f"  - [SAMPLE] {m.get('name')} — {m.get('title','')}"
                if m.get("image_caption"):
                    line += f" [Photo: {_truncate(m['image_caption'], 240)}]"
                sections.append(line)
        sections.append("")

    # ─── Active partner network ────────────────────────────────────────
    # Include sample partners too — they render publicly at /partner and
    # /partner/<slug>, so the assistant must know about them or it'll fail
    # questions like "are there any artists doing ceramics?" (Rosa Mendieta).
    partners = await db.partner_profiles.find(
        {"status": "active", "public": True},
        {"_id": 0, "slug": 1, "display_name": 1, "partner_type": 1,
         "headline": 1, "bio": 1, "location": 1, "website_url": 1, "image_caption": 1},
    ).to_list(60)
    # Filter out obvious test fixtures whose names start with "test-" /
    # "oof-" — those are pytest scaffolding, not real visitor-facing content.
    partners = [
        p for p in partners
        if not (p.get("slug", "").startswith(("test-", "oof-", "rene-search-")))
    ]
    if partners:
        sections.append("PARTNERS (public on /partner directory):")
        for p in partners:
            bits = [p.get("display_name", ""), p.get("partner_type", "")]
            if p.get("location"):
                bits.append(p["location"])
            head = " · ".join(b for b in bits if b)
            line = f"  - /partner/{p.get('slug')} — {head}"
            if p.get("headline"):
                line += f": {_truncate(p['headline'], 220)}"
            elif p.get("bio"):
                line += f": {_truncate(p['bio'], 220)}"
            if p.get("image_caption"):
                line += f" [Photo: {_truncate(p['image_caption'], 200)}]"
            sections.append(line)
        sections.append("")

    # ─── Equip catalog (top sellable products) ─────────────────────────
    products = await db.products.find(
        {"moderation_status": "active"},
        {"_id": 0, "slug": 1, "name": 1, "price": 1, "type": 1, "category": 1,
         "vendor_slug": 1, "short_description": 1, "collection": 1, "is_off_site": 1,
         "is_homepage_feature": 1, "carousel_rank": 1, "image_caption": 1},
    ).to_list(200)
    if products:
        # Sort: homepage features → carousel rank → name. Limit to 30 most
        # likely to be asked about.
        def sk(p):
            return (
                0 if p.get("is_homepage_feature") else 1,
                p.get("carousel_rank") if isinstance(p.get("carousel_rank"), int) else 9999,
                (p.get("name") or "").lower(),
            )
        products.sort(key=sk)
        sections.append("EQUIP CATALOG (live products at /equip):")
        for p in products[:30]:
            price = f"${p['price']:.0f}" if isinstance(p.get("price"), (int, float)) else "—"
            tag = []
            if p.get("collection"):
                tag.append(p["collection"])
            if p.get("vendor_slug"):
                tag.append(f"by {p['vendor_slug']}")
            if p.get("is_off_site"):
                tag.append("partner-fulfilled")
            line = f"  - /equip/{p.get('slug')} — {p.get('name')} ({price}"
            if tag:
                line += f" · {' · '.join(tag)}"
            line += ")"
            if p.get("short_description"):
                line += f": {_truncate(p['short_description'], 100)}"
            if p.get("image_caption"):
                line += f" [Image: {_truncate(p['image_caption'], 160)}]"
            sections.append(line)
        sections.append("")

    # ─── Workshops ─────────────────────────────────────────────────────
    workshops = await db.workshops.find(
        {"status": {"$in": ["upcoming", "open", "active", "published"]}},
        {"_id": 0, "title": 1, "short_description": 1, "price_usd": 1, "date": 1,
         "slug": 1, "id": 1, "status": 1},
    ).to_list(30)
    if workshops:
        sections.append("WORKSHOPS (practitioner programs at /learn):")
        for w in workshops:
            price = f"${w['price_usd']:.0f}" if isinstance(w.get("price_usd"), (int, float)) else ""
            line = f"  - {w.get('title','')}"
            if price:
                line += f" ({price})"
            if w.get("short_description"):
                line += f": {_truncate(w['short_description'], 160)}"
            sections.append(line)
        sections.append("")

    # ─── Published research ────────────────────────────────────────────
    research = await db.research_artifacts.find(
        {"status": "published"},
        {"_id": 0, "title": 1, "kind": 1, "summary": 1, "url": 1, "slug": 1},
    ).to_list(20)
    if research:
        sections.append("PUBLISHED RESEARCH (see /research):")
        for r in research:
            line = f"  - {r.get('title','')}"
            if r.get("kind"):
                line += f" [{r['kind']}]"
            if r.get("summary"):
                line += f": {_truncate(r['summary'], 200)}"
            sections.append(line)
        sections.append("")

    # ─── Site map (canonical routes for navigation answers) ────────────
    sections.append("SITE MAP (canonical routes):")
    sections.append("  / — Home / mission overview")
    sections.append("  /about — Foundation overview, education structure, values")
    sections.append("  /lead — Governing members, board, leadership team")
    sections.append("  /lead/proposals — Open governance proposals")
    sections.append("  /equip — Equip shop: patches, founder collection, vendor goods")
    sections.append("  /equip/collection/founder — Founder Collection carousel")
    sections.append("  /learn — Workshops & curriculum (Foundations, Reflection, Practice)")
    sections.append("  /research — Published research artifacts and case studies")
    sections.append("  /partner — Partner directory (vendors, community, research, facilitators, artists, stewards)")
    sections.append("  /partner/types — Partner type comparison + tier structure")
    sections.append("  /partner/apply — Become a partner")
    sections.append("  /partner/artist — Artist partnership terms")
    sections.append("  /donate — Donations and sponsorship tiers")
    sections.append("  /help — This AI help assistant + escalation to humans")
    sections.append("  /dashboard — Member dashboard (workshops, AI wallet, payouts)")

    return "\n".join(sections)


async def get_platform_context(db) -> str:
    """Return the cached platform fact pack, refreshing if stale."""
    now = time.time()
    if _CACHE["text"] and (now - _CACHE["ts"]) < _CACHE_TTL_SECONDS:
        return _CACHE["text"]
    async with _LOCK:
        # Double-check after acquiring the lock — another coroutine may
        # have just refreshed it.
        if _CACHE["text"] and (time.time() - _CACHE["ts"]) < _CACHE_TTL_SECONDS:
            return _CACHE["text"]
        try:
            text = await _collect(db)
            _CACHE["text"] = text
            _CACHE["ts"] = time.time()
            logger.info(
                "help context refreshed: %d chars, %d sections",
                len(text), text.count("\n\n") + 1,
            )
        except Exception as exc:
            logger.exception("help context build failed: %s", exc)
            # Fall back to stale cache if we have one, else empty string.
            return _CACHE["text"] or ""
    return _CACHE["text"]


def invalidate_cache() -> None:
    """Force the next call to rebuild. Used by admin tools after content edits."""
    _CACHE["text"] = ""
    _CACHE["ts"] = 0.0
