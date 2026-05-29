"""Outbound-click attribution — Phase 6B / v1.11.0 Step 2.

`GET /api/out/{slug}?dest=&utm_source=...` logs an outbound_click row and 302s to
the partner's `external_site_url` (or to the `dest` query param if it points to
the partner's registered domain).

Click attribution data captured:
  - partner_id, partner_slug
  - user_id (if logged in via the standard auth cookie)
  - referrer (from Referer header)
  - utm params (utm_source, utm_medium, utm_campaign, utm_term, utm_content)
  - destination URL actually redirected to
  - ip + user-agent (best-effort, helpful for spam/bot filtering later)
"""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from auth_utils import get_current_user_optional, require_roles
from models import gen_id, now_iso

logger = logging.getLogger("birthright.outbound")

# Top-level public router — clean `/api/out/{slug}` URL for sharing.
router = APIRouter(prefix="/out", tags=["outbound"])
admin_router = APIRouter(prefix="/admin/outbound-clicks", tags=["outbound-admin"])

_UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")


def _safe_dest(profile: dict, dest: Optional[str]) -> str:
    """Pick the redirect target. If `dest` is provided and shares the partner's
    external_site_url host, honor it; otherwise fall back to external_site_url."""
    fallback = (profile.get("external_site_url") or profile.get("website_url") or "").strip()
    if not dest:
        return fallback
    try:
        dest_host = urlparse(dest).netloc.lower()
        fallback_host = urlparse(fallback).netloc.lower()
    except Exception:
        return fallback
    if dest_host and fallback_host and dest_host == fallback_host:
        return dest
    return fallback


def _append_via(url: str, via_slug: str) -> str:
    """Stamp `?via=birthright_<slug>` on the URL so the partner can attribute
    inbound traffic and self-report sales via the partner-sales-reports flow."""
    if not url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}via=birthright_{via_slug}"


@router.get("/{slug}")
async def outbound_click(
    slug: str,
    request: Request,
    dest: Optional[str] = Query(default=None, description="Optional sub-path on the partner's site"),
    product_id: Optional[str] = Query(default=None, description="If set, redirect to that product's external_url"),
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Public endpoint. Logs the click then 302s to the partner's external site
    (or to an off-site product's external_url). Always stamps `?via=birthright_<slug>`
    on the destination so partners can attribute inbound traffic.
    Falls back to `/partners/{slug}` when no external URL is set."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"slug": slug, "status": "active", "public": True}, {"_id": 0}
    )
    if not profile:
        return RedirectResponse(url="/partners", status_code=302)

    # Phase 4 — product-scoped outbound link.
    target: str = ""
    via_product_id: Optional[str] = None
    if product_id:
        prod = await db.products.find_one({
            "id": product_id,
            "is_off_site": True,
            "moderation_status": "active",
            "vendor_partner_id": profile["id"],
        }, {"_id": 0, "external_url": 1, "id": 1})
        if prod and prod.get("external_url"):
            target = prod["external_url"]
            via_product_id = prod["id"]
    if not target:
        target = _safe_dest(profile, dest)
    if not target:
        return RedirectResponse(url=f"/partners/{slug}", status_code=302)

    target = _append_via(target, slug)

    qp = dict(request.query_params)
    utm = {k: qp[k] for k in _UTM_KEYS if k in qp}

    doc = {
        "id": gen_id(),
        "partner_id": profile["id"],
        "partner_slug": slug,
        "partner_type": profile.get("partner_type"),
        "user_id": user["id"] if user else None,
        "session_id": request.cookies.get("session_id"),
        "dest_url": target,
        "product_id": via_product_id,
        "referrer": request.headers.get("referer"),
        "utm_params": utm,
        "user_agent": (request.headers.get("user-agent") or "")[:500],
        "ip": (request.client.host if request.client else None),
        "is_sample": bool(profile.get("is_sample")),
        "created_at": now_iso(),
    }
    try:
        await db.outbound_clicks.insert_one(doc)
    except Exception as e:
        logger.warning(f"outbound click log failed for {slug}: {e}")

    return RedirectResponse(url=target, status_code=302)


# ============ ADMIN ============

@admin_router.get("")
async def list_clicks(
    partner_id: Optional[str] = None,
    partner_slug: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if partner_id:
        query["partner_id"] = partner_id
    if partner_slug:
        query["partner_slug"] = partner_slug
    rows = await db.outbound_clicks.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return rows


@admin_router.get("/summary")
async def click_summary(user: dict = Depends(require_roles("admin"))):
    """Top partners by outbound-click count (all-time)."""
    from database import db
    pipeline = [
        {"$group": {
            "_id": {"partner_id": "$partner_id", "partner_slug": "$partner_slug"},
            "clicks": {"$sum": 1},
            "with_user": {"$sum": {"$cond": [{"$ne": ["$user_id", None]}, 1, 0]}},
            "last_click_at": {"$max": "$created_at"},
        }},
        {"$sort": {"clicks": -1}},
        {"$limit": 200},
    ]
    rows = []
    async for r in db.outbound_clicks.aggregate(pipeline):
        rows.append({
            "partner_id": r["_id"]["partner_id"],
            "partner_slug": r["_id"]["partner_slug"],
            "clicks": r["clicks"],
            "with_user": r["with_user"],
            "anonymous": r["clicks"] - r["with_user"],
            "last_click_at": r["last_click_at"],
        })
    return rows
