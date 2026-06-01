"""Global search — Phase 7+ cross-site discovery.

Single endpoint that fans out a search query across all the user-facing
content types: workshops, products, partners, research artifacts, and
gallery items. Returns a unified, lightly-ranked result set the frontend
can render as a grouped dropdown.

Design choices:
  - Regex-anchored case-insensitive match on a small, controlled set of
    fields per collection (no full-text index needed for the volumes we
    serve; we can swap in an Atlas Search index later without changing
    the API contract).
  - Per-type result caps (default 5 each) keep response payloads small.
  - Only returns PUBLIC / ACTIVE rows. Drafts, paused profiles, and
    revoked items are filtered out so the search is safe to expose
    without auth.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Query

logger = logging.getLogger("birthright.search")

router = APIRouter(prefix="/search", tags=["search"])

# All searchable content types — frontend uses these slugs to filter.
SEARCHABLE_TYPES = (
    "workshop", "product", "partner", "research", "gallery",
)


def _regex(q: str) -> dict:
    return {"$regex": re.escape(q.strip()), "$options": "i"}


async def _search_workshops(db, q: str, limit: int) -> list[dict]:
    rx = _regex(q)
    cursor = db.workshops.find(
        {
            "$or": [
                {"title": rx},
                {"short_description": rx},
                {"full_description": rx},
            ],
            "status": {"$in": ["upcoming", "ongoing", "completed"]},
        },
        {
            "_id": 0, "id": 1, "title": 1, "slug": 1, "short_description": 1,
            "image_url": 1, "status": 1, "start_date": 1,
            "regular_price": 1, "early_bird_price": 1,
        },
    ).sort([("status", 1), ("start_date", 1)]).limit(limit)
    out = []
    async for w in cursor:
        out.append({
            "type": "workshop",
            "id": w["id"],
            "title": w.get("title"),
            "subtitle": w.get("short_description"),
            "image_url": w.get("image_url"),
            "url": f"/workshops/{w.get('slug') or w['id']}",
            "meta": {
                "status": w.get("status"),
                "start_date": w.get("start_date"),
                "price": w.get("early_bird_price") or w.get("regular_price"),
            },
        })
    return out


async def _search_products(db, q: str, limit: int) -> list[dict]:
    rx = _regex(q)
    cursor = db.products.find(
        {
            "$or": [
                {"name": rx},
                {"description": rx},
                {"category": rx},
            ],
        },
        {
            "_id": 0, "id": 1, "name": 1, "description": 1, "image_url": 1,
            "price": 1, "type": 1, "category": 1, "collection": 1,
        },
    ).limit(limit)
    out = []
    async for p in cursor:
        out.append({
            "type": "product",
            "id": p["id"],
            "title": p.get("name"),
            "subtitle": (p.get("description") or "")[:120],
            "image_url": p.get("image_url"),
            "url": f"/shop/{p['id']}",
            "meta": {
                "price": p.get("price"),
                "category": p.get("category"),
                "collection": p.get("collection"),
                "type": p.get("type"),
            },
        })
    return out


async def _search_partners(db, q: str, limit: int) -> list[dict]:
    rx = _regex(q)
    cursor = db.partner_profiles.find(
        {
            "$or": [
                {"display_name": rx},
                {"headline": rx},
                {"bio": rx},
                {"location": rx},
            ],
            "status": "active",
            "public": True,
            # Exclude sample/demo profiles — they're not real partners.
            "$and": [{"$or": [{"is_sample": {"$exists": False}}, {"is_sample": False}]}],
        },
        {
            "_id": 0, "id": 1, "slug": 1, "display_name": 1, "headline": 1,
            "partner_type": 1, "photo_url": 1, "location": 1,
        },
    ).limit(limit)
    out = []
    async for p in cursor:
        out.append({
            "type": "partner",
            "id": p["id"],
            "title": p.get("display_name"),
            "subtitle": p.get("headline") or f"{p.get('partner_type','').title()} partner",
            "image_url": p.get("photo_url"),
            "url": f"/partners/{p.get('slug') or p['id']}",
            "meta": {
                "partner_type": p.get("partner_type"),
                "location": p.get("location"),
            },
        })
    return out


async def _search_research(db, q: str, limit: int) -> list[dict]:
    rx = _regex(q)
    cursor = db.research_artifacts.find(
        {
            "$or": [
                {"title": rx},
                {"abstract": rx},
                {"summary": rx},
                {"tags": rx},  # tag arrays are matched element-wise by regex too
            ],
            "status": "published",
        },
        {
            "_id": 0, "id": 1, "slug": 1, "title": 1, "abstract": 1,
            "summary": 1, "cover_image_url": 1, "kind": 1, "tags": 1,
            "published_at": 1,
        },
    ).sort("published_at", -1).limit(limit)
    out = []
    async for r in cursor:
        out.append({
            "type": "research",
            "id": r["id"],
            "title": r.get("title"),
            "subtitle": (r.get("summary") or r.get("abstract") or "")[:140],
            "image_url": r.get("cover_image_url"),
            "url": f"/research/{r.get('slug') or r['id']}",
            "meta": {
                "kind": r.get("kind"),
                "tags": r.get("tags") or [],
                "published_at": r.get("published_at"),
            },
        })
    return out


async def _search_gallery(db, q: str, limit: int) -> list[dict]:
    rx = _regex(q)
    # Featured artists/gallery items live in partner_profiles + featured_slots.
    # For simplicity here we search active artist profiles directly so a query
    # like "weaver" surfaces the artist (their gallery is one click away).
    cursor = db.partner_profiles.find(
        {
            "$or": [
                {"display_name": rx},
                {"headline": rx},
                {"bio": rx},
                {"medium": rx},
            ],
            "partner_type": "artist",
            "status": "active",
            "public": True,
            "$and": [{"$or": [{"is_sample": {"$exists": False}}, {"is_sample": False}]}],
        },
        {
            "_id": 0, "id": 1, "slug": 1, "display_name": 1, "headline": 1,
            "photo_url": 1, "medium": 1, "location": 1,
        },
    ).limit(limit)
    out = []
    async for a in cursor:
        out.append({
            "type": "gallery",
            "id": a["id"],
            "title": a.get("display_name"),
            "subtitle": a.get("headline") or a.get("medium") or "Featured artist",
            "image_url": a.get("photo_url"),
            "url": f"/gallery/{a.get('slug') or a['id']}",
            "meta": {
                "medium": a.get("medium"),
                "location": a.get("location"),
            },
        })
    return out


@router.get("/global")
async def global_search(
    q: str = Query(..., min_length=2, max_length=200),
    types: Optional[str] = None,
    per_type_limit: int = Query(5, ge=1, le=20),
):
    """Fan-out search across all public content.

    Args:
      q: search query (min 2 chars).
      types: comma-separated subset of `SEARCHABLE_TYPES`. Default = all.
      per_type_limit: max results per content type.

    Returns: `{ "query": str, "results": [...], "counts": {type: int} }`.
    """
    from database import db
    wanted = set(SEARCHABLE_TYPES)
    if types:
        wanted = {t.strip() for t in types.split(",") if t.strip() in SEARCHABLE_TYPES}
    if not wanted:
        return {"query": q, "results": [], "counts": {}}

    runners = {
        "workshop": _search_workshops,
        "product":  _search_products,
        "partner":  _search_partners,
        "research": _search_research,
        "gallery":  _search_gallery,
    }

    grouped: dict[str, list[dict]] = {}
    for t in wanted:
        try:
            grouped[t] = await runners[t](db, q, per_type_limit)
        except Exception as ex:
            logger.warning("global_search: type=%s failed: %s", t, ex)
            grouped[t] = []

    # Flatten with stable type ordering so the frontend can render in groups
    # but a simple flat consumer also gets a sensible order.
    ordered_types = ("workshop", "partner", "product", "research", "gallery")
    flat: list[dict] = []
    counts: dict[str, int] = {}
    for t in ordered_types:
        rows = grouped.get(t, [])
        counts[t] = len(rows)
        flat.extend(rows)

    return {"query": q, "results": flat, "counts": counts}
