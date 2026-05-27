"""Rich link previews (Open Graph / Twitter Card injection for crawlers).

When a social-media bot or messaging app fetches a deep link like
/shop/abc123 or /workshops/foundations-of-secure-bonds, it expects to see
Open Graph meta tags in the initial HTML response — React SPAs don't
provide those (the meta tags are only patched in after JS executes, by
which time the crawler is gone).

This middleware intercepts requests from known bot user agents, looks up
the relevant resource (product, workshop, research artifact, partner,
foundation role, etc.), and returns a minimal HTML stub with the right
og:image, og:title, og:description tags. Humans still see the full SPA.
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger("birthright.link_preview")
router = APIRouter(tags=["link-preview"])

# Pattern catches the major crawlers + messaging apps. We deliberately keep
# this broad so previews work in Slack, iMessage, Telegram, etc.
_BOT_UA = re.compile(
    r"facebookexternalhit|twitterbot|linkedinbot|slackbot|telegrambot|whatsapp|"
    r"discordbot|skypeuripreview|pinterest|googlebot|bingbot|applebot|"
    r"redditbot|embedly|outbrain|quora link preview|vkshare|w3c_validator|"
    r"yandex|baiduspider|duckduckbot",
    re.IGNORECASE,
)

DEFAULT_OG = {
    "title": "birthright — Secure Bonds > Thrive",
    "description": (
        "An educational foundation. Workshops, materials, and a quiet community for "
        "everyone learning to claim and recover the relationships they were always meant to have."
    ),
    "image": "https://customer-assets.emergentagent.com/job_c61b4345-eef4-4783-a5af-85e8af10eaf3/artifacts/s0oix25k_image.png",
}


def _is_bot(request: Request) -> bool:
    ua = request.headers.get("user-agent", "")
    return bool(_BOT_UA.search(ua))


def _abs_image(image_url: Optional[str], base_url: str) -> str:
    if not image_url:
        return DEFAULT_OG["image"]
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    # /api/static/... or /static/... — prepend the host
    return f"{base_url.rstrip('/')}{image_url}"


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _render_og_stub(title: str, description: str, image: str, canonical_url: str) -> str:
    """Minimal HTML stub for crawlers. Includes a meta refresh so any humans
    that accidentally land here still bounce to the real SPA."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(description)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="birthright">
<meta property="og:title" content="{_esc(title)}">
<meta property="og:description" content="{_esc(description)}">
<meta property="og:image" content="{_esc(image)}">
<meta property="og:url" content="{_esc(canonical_url)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_esc(title)}">
<meta name="twitter:description" content="{_esc(description)}">
<meta name="twitter:image" content="{_esc(image)}">
<link rel="canonical" href="{_esc(canonical_url)}">
<meta http-equiv="refresh" content="0; url={_esc(canonical_url)}">
</head>
<body>
<p><a href="{_esc(canonical_url)}">Continue to birthright</a></p>
</body>
</html>"""


# ---- Resource lookups -------------------------------------------------------
async def _lookup_product(db, identifier: str) -> Optional[Tuple[str, str, Optional[str]]]:
    # Try slug then id
    p = await db.products.find_one({"slug": identifier}, {"_id": 0})
    if not p:
        p = await db.products.find_one({"id": identifier}, {"_id": 0})
    if not p:
        return None
    title = f"{p.get('name', 'Birthright Shop')} — birthright"
    desc = (p.get("description") or "").strip()
    if len(desc) > 280:
        desc = desc[:277].rstrip() + "…"
    return title, desc or DEFAULT_OG["description"], p.get("image_url")


async def _lookup_workshop(db, slug: str) -> Optional[Tuple[str, str, Optional[str]]]:
    w = await db.workshops.find_one({"slug": slug}, {"_id": 0})
    if not w:
        w = await db.workshops.find_one({"id": slug}, {"_id": 0})
    if not w:
        return None
    title = f"{w.get('title', 'Workshop')} — birthright"
    desc = (w.get("short_description") or w.get("full_description") or "").strip()
    if len(desc) > 280:
        desc = desc[:277].rstrip() + "…"
    return title, desc or DEFAULT_OG["description"], w.get("image_url")


async def _lookup_research(db, identifier: str) -> Optional[Tuple[str, str, Optional[str]]]:
    r = await db.research_artifacts.find_one({"slug": identifier}, {"_id": 0})
    if not r:
        r = await db.research_artifacts.find_one({"id": identifier}, {"_id": 0})
    if not r:
        return None
    title = f"{r.get('title', 'Research')} — birthright"
    desc = (r.get("abstract") or "").strip()
    if len(desc) > 280:
        desc = desc[:277].rstrip() + "…"
    return title, desc or DEFAULT_OG["description"], r.get("hero_image_url") or r.get("image_url")


async def _lookup_partner(db, slug: str) -> Optional[Tuple[str, str, Optional[str]]]:
    p = await db.partner_profiles.find_one({"slug": slug}, {"_id": 0})
    if not p:
        return None
    title = f"{p.get('display_name', 'Partner')} — birthright partner"
    desc = (p.get("tagline") or p.get("bio") or "").strip()
    if len(desc) > 280:
        desc = desc[:277].rstrip() + "…"
    return title, desc or DEFAULT_OG["description"], p.get("avatar_url") or p.get("hero_image_url")


async def _resolve_meta(db, path: str) -> Tuple[str, str, Optional[str]]:
    """Returns (title, description, image_url_or_none) for a given path."""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return DEFAULT_OG["title"], DEFAULT_OG["description"], DEFAULT_OG["image"]

    head, tail = parts[0], parts[-1]

    if head == "shop" and len(parts) >= 2:
        hit = await _lookup_product(db, tail)
        if hit: return hit
    if head == "workshops" and len(parts) >= 2:
        hit = await _lookup_workshop(db, tail)
        if hit: return hit
    if head == "research" and len(parts) >= 2:
        hit = await _lookup_research(db, tail)
        if hit: return hit
    if head == "partners" and len(parts) >= 2:
        hit = await _lookup_partner(db, tail)
        if hit: return hit

    # Section-level fallbacks
    section_defaults = {
        "shop": ("Shop — birthright", "Journals, mugs, totes, and quiet objects designed to keep the practice close.", DEFAULT_OG["image"]),
        "workshops": ("Workshops — birthright", "Foundations, practice, and ongoing community. Find your next workshop.", DEFAULT_OG["image"]),
        "experiences": ("Workshops — birthright", "Foundations, practice, and ongoing community. Find your next workshop.", DEFAULT_OG["image"]),
        "research": ("Research — birthright", "Peer-reviewed papers, practitioner briefs, and field reports.", DEFAULT_OG["image"]),
        "partners": ("Partners — birthright", "Our community of facilitators, vendors, and researchers.", DEFAULT_OG["image"]),
        "sponsorship": ("Sponsor — birthright", "Help underwrite the work. Sponsor a workshop, a scholarship, or the foundation.", DEFAULT_OG["image"]),
        "governance": ("Governance — birthright", "How the foundation is led, and how you can step in.", DEFAULT_OG["image"]),
        "join-us": ("Join — birthright", "Open roles and ways to step into the foundation.", DEFAULT_OG["image"]),
        "contact": ("Contact — birthright", "Send us a note. We read every message.", DEFAULT_OG["image"]),
        "connect": ("Connect — birthright", "Channels, conversations, and meetings for the Birthright community.", DEFAULT_OG["image"]),
    }
    if head in section_defaults:
        return section_defaults[head]
    return DEFAULT_OG["title"], DEFAULT_OG["description"], DEFAULT_OG["image"]


@router.get("/link-preview")
async def link_preview(request: Request, path: str):
    """Bot-aware redirect endpoint used by share URLs.

    - **Crawler/bot User-Agent** → returns OG-tagged HTML stub so social
      previews render the correct image + title + description.
    - **Human User-Agent** → 302 redirect to the canonical SPA path so the
      user lands on the real page with no extra hop visible.

    The frontend rewrites share URLs to go through this endpoint so that
    iMessage, Slack, WhatsApp, Twitter, Facebook, LinkedIn, etc. all see
    proper Open Graph tags without requiring SSR of the SPA.
    """
    from database import db
    # Preserve any other query params (notably ?via=<token>) when redirecting humans.
    extra_qs = ""
    for k, v in request.query_params.multi_items():
        if k == "path":
            continue
        extra_qs += f"&{k}={v}" if extra_qs else f"?{k}={v}"

    base = str(request.base_url).rstrip("/").replace("/api", "")
    safe_path = path if path.startswith("/") else f"/{path}"
    canonical = f"{base}{safe_path}{extra_qs}"

    if not _is_bot(request):
        return RedirectResponse(url=canonical, status_code=302)

    title, desc, image_path = await _resolve_meta(db, safe_path)
    abs_image = _abs_image(image_path, base)
    html = _render_og_stub(title, desc, abs_image, canonical)
    return HTMLResponse(content=html)
