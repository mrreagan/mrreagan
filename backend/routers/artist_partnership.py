"""Artist partnership — patronage payouts, tier resolution, admin tools.

Three responsibilities:

  1. /api/partner/me/artist-tier
     Public-to-the-caller tier summary for the signed-in artist's dashboard.

  2. /api/admin/artist-payouts ...
     Foundation operator's view of pending patronage payouts (artist gets
     list_price on each paid gallery line item; Foundation kept the 20%
     hospitality markup).

  3. /api/admin/artist-tier-overrides ...
     Manual tier placement for honorary or contractual exceptions.

The actual hook that creates payout rows fires from checkout (see
checkout._create_order_from_txn -> _record_artist_patronage_payouts) so
this router never has to. Reading is free; writing is admin-gated.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth_utils import get_current_user, require_roles
from models import gen_id, now_iso
from utils.artist_tier import (
    TIERS,
    marginal_outbound_owed,
    resolve_artist_tier,
)
from utils.tier_share_card import (
    render_tier_share_png,
    render_tier_share_svg,
)

logger = logging.getLogger("birthright.artist_partnership")

my_router = APIRouter(prefix="/partner/me", tags=["artist-partnership"])
public_router = APIRouter(prefix="/partner/artist", tags=["artist-partnership-public"])
admin_router = APIRouter(prefix="/admin/artist", tags=["artist-partnership-admin"])
share_router = APIRouter(prefix="/share/artist", tags=["artist-partnership-share"])


PUBLIC_TIER_MESSAGES = {
    "emerging": (
        "Welcomed to the gallery — your patronage helps build this "
        "artist's foundation from the ground up."
    ),
    "sustaining": (
        "Your patronage has helped this artist reach the Sustaining "
        "tier — a working practice with consistent earnings."
    ),
    "established": (
        "Your patronage has helped grow this artist's practice into "
        "an established livelihood."
    ),
    "thriving": (
        "Your patronage has been part of this artist's thriving "
        "success story."
    ),
    "flourishing": (
        "This artist has built a flourishing practice — and "
        "Foundation patronage has been a meaningful part of that story."
    ),
}


@public_router.get("/{slug}/impact")
async def public_artist_impact(slug: str):
    """Anonymous public widget data: tier label + icon + a gentle
    public-facing message. NO basis dollars, NO percentages, NO override
    reasoning. Designed for the artist's public gallery page so visitors
    can see that buying through Birthright meaningfully supports the
    artist's career, without exposing private revenue numbers."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"slug": slug, "partner_type": "artist", "status": "active",
         "public": True},
        {"_id": 0, "user_id": 1, "display_name": 1},
    )
    if not profile:
        raise HTTPException(404, "Artist not found")
    tier = await resolve_artist_tier(db, profile["user_id"])
    return {
        "tier_key": tier["tier_key"],
        "tier_label": tier["tier_label"],
        "tier_icon": tier["tier_icon"],
        "message": PUBLIC_TIER_MESSAGES.get(
            tier["tier_key"], PUBLIC_TIER_MESSAGES["emerging"],
        ),
        # No basis_12mo, no pct, no override reason — strictly anonymous.
    }


# ============ PUBLIC — tier table for the clarity page ============
@public_router.get("/tier-table")
async def public_tier_table():
    """Public — exposes the tier ladder so the 'Artist Partnership Terms'
    page can render the exact numbers the Foundation operates on. Clarity
    before commitment: the artist must be able to see this before signing
    up."""
    return {
        "tiers": [
            {
                "key": t["key"],
                "label": t["label"],
                "icon": t["icon"],
                "basis_lo": t["lo"],
                "basis_hi": t["hi"],
                "inbound_pct": t["inbound_pct"],
                "outbound_pct": t["outbound_pct"],
            }
            for t in TIERS
        ],
        "on_site_patronage_markup_pct": 20.0,
        "attribution": {
            "inbound": {
                "cookie_days": 30,
                "scope": "first_purchase_only",
                "model": "last_click",
            },
            "outbound": {
                "claim_window_days": 30,
                "scope": "first_purchase_only",
                "reporting_cadence": "quarterly",
                "model": "self_attested",
            },
        },
        "basis_definition": (
            "Trailing 12 months of Birthright-attributed gross revenue: "
            "the artist's gallery sales on Birthright at list price PLUS "
            "their self-reported off-site sales tagged with via=birthright. "
            "Recomputed monthly. Foundation only ever takes a share of "
            "what Foundation contributed to."
        ),
        "transitions": (
            "Tier changes take effect on the 1st of the following month. "
            "Tiers can rise or fall; downward protection is automatic "
            "during slower periods."
        ),
        "outbound_calculation": (
            "Outbound uses MARGINAL brackets: only the revenue above each "
            "threshold pays that tier's rate. Crossing a threshold by $1 "
            "never re-taxes everything below it."
        ),
    }


# ============ ARTIST DASHBOARD ============
@my_router.get("/artist-tier")
async def my_artist_tier(user: dict = Depends(get_current_user)):
    """Authenticated artist sees their current tier + basis + runway."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": "artist", "status": "active"},
        {"_id": 0},
    )
    if not profile:
        raise HTTPException(403, "You need an approved Artist partner profile.")
    summary = await resolve_artist_tier(db, user["id"])
    # Surface profile-level pieces the dashboard needs (share card URL,
    # display name, public visibility) without an extra round-trip.
    summary["slug"] = profile.get("slug")
    summary["display_name"] = profile.get("display_name")
    summary["public"] = bool(profile.get("public"))
    return summary


@my_router.get("/artist-payouts")
async def my_patronage_payouts(user: dict = Depends(get_current_user)):
    """Artist sees their own pending + paid patronage payouts."""
    from database import db
    rows = await db.artist_sale_payouts.find(
        {"artist_user_id": user["id"]}, {"_id": 0},
    ).sort("created_at", -1).to_list(500)
    pending = sum(r["list_price"] for r in rows if r["status"] == "pending")
    paid = sum(r["list_price"] for r in rows if r["status"] == "paid")
    return {
        "summary": {
            "count": len(rows),
            "lifetime_total": round(pending + paid, 2),
            "pending_payout": round(pending, 2),
            "paid_to_date": round(paid, 2),
        },
        "recent": rows[:100],
    }


# -------- Stripe Connect onboarding (artist-facing) --------

class StripeOnboardingRequest(BaseModel):
    origin: str = Field(min_length=8, max_length=400,
                         description="The site origin (window.location.origin) for return/refresh URLs.")


@my_router.post("/stripe-connect/onboarding-link")
async def stripe_connect_onboarding_link(
    body: StripeOnboardingRequest,
    user: dict = Depends(get_current_user),
):
    """Create (or reuse) the artist's Stripe Connect Express account and
    return a hosted onboarding URL. The artist completes KYC + bank
    linkage on Stripe-hosted pages and is redirected back to
    `/partner/me/payout-method`."""
    from database import db
    try:
        from utils.stripe_connect import (
            create_or_get_express_account, create_onboarding_link,
        )
        acct = await create_or_get_express_account(
            db, artist_user_id=user["id"], email=user["email"],
        )
        origin = body.origin.rstrip("/")
        url = create_onboarding_link(
            acct["id"],
            refresh_url=f"{origin}/partner/me/payout-method?stripe=refresh",
            return_url=f"{origin}/partner/me/payout-method?stripe=return",
        )
        return {"onboarding_url": url, "stripe_account_id": acct["id"]}
    except Exception as e:
        logger.exception("Stripe Connect onboarding link failed: %s", e)
        raise HTTPException(
            502,
            f"Couldn't create the Stripe onboarding link. "
            f"Make sure Stripe Connect is enabled on the Foundation's "
            f"platform account. Details: {str(e)[:200]}",
        )


@my_router.get("/stripe-connect/status")
async def stripe_connect_status(user: dict = Depends(get_current_user)):
    """Refresh the artist's Stripe Connect status from Stripe."""
    from database import db
    try:
        from utils.stripe_connect import refresh_account_status
        return await refresh_account_status(db, artist_user_id=user["id"])
    except Exception as e:
        logger.exception("Stripe Connect status refresh failed: %s", e)
        return {"connected": False, "error": str(e)[:200]}


# -------- Monthly revenue series (for sparkline) --------
@my_router.get("/monthly-revenue")
async def monthly_revenue(
    months: int = 12,
    user: dict = Depends(get_current_user),
):
    """Return Birthright-attributed revenue per calendar month for the
    trailing `months` months. Each entry sums:
      • on-site patronage at list_price for paid orders that month
      • off-site self-reported revenue with period_end in that month

    Output shape:
        [{ "month": "2025-03", "revenue": 0.0, "patronage": 0.0,
            "off_site": 0.0 }, …]
    Always returns `months` entries (zero-padded so the sparkline has a
    stable x-axis)."""
    from database import db
    from datetime import datetime, timedelta, timezone

    months = max(1, min(months, 36))
    today = datetime.now(timezone.utc).date()
    # Build the list of (year, month) buckets oldest → newest.
    buckets: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(months):
        buckets.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    buckets.reverse()
    keys = [f"{y:04d}-{m:02d}" for (y, m) in buckets]
    series = {k: {"patronage": 0.0, "off_site": 0.0} for k in keys}

    cutoff_dt = datetime(buckets[0][0], buckets[0][1], 1,
                          tzinfo=timezone.utc)
    cutoff = cutoff_dt.isoformat()

    # On-site patronage — group artist's paid line items by created_at month.
    orders = await db.orders.find(
        {"status": "paid", "created_at": {"$gte": cutoff}},
        {"_id": 0, "items": 1, "created_at": 1},
    ).to_list(50_000)
    pids = {li.get("product_id")
            for o in orders for li in (o.get("items") or [])
            if li.get("product_id")}
    if pids:
        artist_products = await db.products.find(
            {"id": {"$in": list(pids)},
             "is_gallery_artwork": True,
             "gallery_artist_user_id": user["id"]},
            {"_id": 0, "id": 1, "price": 1},
        ).to_list(len(pids) + 1)
        price_by_id = {p["id"]: float(p.get("price") or 0)
                        for p in artist_products}
    else:
        price_by_id = {}

    for o in orders:
        key = (o.get("created_at") or "")[:7]
        if key not in series:
            continue
        for li in o.get("items") or []:
            pid = li.get("product_id")
            if pid in price_by_id:
                series[key]["patronage"] += price_by_id[pid] * int(
                    li.get("quantity") or 0)

    # Off-site self-reported — bucket by period_end month.
    reports = await db.partner_sales_reports.find(
        {"partner_user_id": user["id"],
         "period_end": {"$gte": keys[0] + "-01"}},
        {"_id": 0, "amount_usd": 1, "period_end": 1, "status": 1},
    ).to_list(2000)
    for r in reports:
        key = (r.get("period_end") or "")[:7]
        if key not in series:
            continue
        # Count submitted + approved (since artist sees the value they
        # actually earned).
        if r.get("status") in ("approved", "submitted"):
            series[key]["off_site"] += float(r.get("amount_usd") or 0)

    return [
        {
            "month": k,
            "patronage": round(series[k]["patronage"], 2),
            "off_site": round(series[k]["off_site"], 2),
            "revenue": round(series[k]["patronage"] + series[k]["off_site"], 2),
        }
        for k in keys
    ]


# -------- Tier history (Task P3: audit timeline + share celebration) --------

@my_router.get("/tier-history")
async def my_tier_history(user: dict = Depends(get_current_user)):
    """All recorded tier transitions for the signed-in artist, newest
    first. Also returns the most recent UP transition that hasn't been
    dismissed, so the dashboard can surface a 'share your achievement'
    banner without an extra round-trip.

    Tracking starts going forward from the first time `resolve_artist_tier`
    runs for the artist; historical pre-deployment transitions are not
    backfilled."""
    from database import db
    rows = await db.artist_tier_history.find(
        {"user_id": user["id"]}, {"_id": 0},
    ).sort("created_at", -1).to_list(500)
    # Pending share = most recent UP transition where share_dismissed is falsy.
    pending = next(
        (r for r in rows
         if r.get("direction") == "up" and not r.get("share_dismissed")),
        None,
    )
    return {
        "rows": rows,
        "pending_share": pending,
    }


@my_router.post("/tier-history/{history_id}/dismiss-share")
async def my_dismiss_share(
    history_id: str, user: dict = Depends(get_current_user),
):
    """Acknowledge the 'share your achievement' banner. Belt-and-suspenders
    ownership check on `user_id` so one artist can't dismiss another's row."""
    from database import db
    r = await db.artist_tier_history.update_one(
        {"id": history_id, "user_id": user["id"]},
        {"$set": {"share_dismissed": True,
                   "share_dismissed_at": now_iso()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Tier-history row not found")
    return {"ok": True}


# -------- Share card (public; for OG previews + downloadable PNG) --------

async def _build_share_card_payload(db, slug: str) -> dict:
    """Look up an artist by slug + their current tier + a referral URL
    that drops a tracking cookie before landing on their gallery."""
    profile = await db.partner_profiles.find_one(
        {"slug": slug, "partner_type": "artist", "status": "active",
         "public": True},
        {"_id": 0, "user_id": 1, "display_name": 1, "referral_code": 1},
    )
    if not profile:
        raise HTTPException(404, "Artist not found")
    tier = await resolve_artist_tier(db, profile["user_id"])
    # Build a referral URL that funnels through /r/{code} so any sale
    # this share converts gets attributed back to the artist as inbound.
    code = profile.get("referral_code") or ""
    if code:
        share_url = (
            f"https://birthright.live/api/r/{code}"
            f"?dest=/partners/{slug}"
        )
    else:
        share_url = f"https://birthright.live/partners/{slug}"
    return {
        "tier_label": tier["tier_label"],
        "tier_icon": tier["tier_icon"],
        "tier_key": tier["tier_key"],
        "artist_name": profile.get("display_name", ""),
        "referral_url": share_url,
    }


@share_router.get("/{slug}/tier-card.png")
async def tier_share_card_png(slug: str):
    """Public Open-Graph-friendly PNG (1200×630) declaring the artist's
    current tier. Cached aggressively at the edge."""
    from database import db
    payload = await _build_share_card_payload(db, slug)
    png = render_tier_share_png(**payload)
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=900",
            "Content-Disposition": f'inline; filename="birthright-{slug}-tier.png"',
        },
    )


@share_router.get("/{slug}/tier-card.svg")
async def tier_share_card_svg(slug: str):
    """SVG variant for hi-res social sharing or print."""
    from database import db
    payload = await _build_share_card_payload(db, slug)
    svg = render_tier_share_svg(**payload)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=900"},
    )


# ============ ADMIN — patronage payouts ============
@admin_router.get("/payouts")
async def admin_list_payouts(
    status: Optional[Literal["pending", "paid", "cancelled"]] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    q = {}
    if status:
        q["status"] = status
    rows = await db.artist_sale_payouts.find(q, {"_id": 0}) \
        .sort("created_at", -1).to_list(2000)
    return {
        "count": len(rows),
        "total_pending": round(
            sum(r["list_price"] for r in rows if r["status"] == "pending"), 2),
        "total_paid": round(
            sum(r["list_price"] for r in rows if r["status"] == "paid"), 2),
        "rows": rows,
    }


class MarkPaid(BaseModel):
    payout_method: str = Field(min_length=2, max_length=80)
    payout_reference: str = Field(min_length=2, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=2000)


@admin_router.post("/payouts/{payout_id}/mark-paid")
async def admin_mark_paid(
    payout_id: str,
    data: MarkPaid,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    p = await db.artist_sale_payouts.find_one({"id": payout_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Payout not found")
    if p["status"] == "paid":
        raise HTTPException(400, "Already marked paid")

    # If admin asked for Stripe Connect transfer, attempt it before
    # flipping status. On failure, surface the Stripe error directly so
    # the operator can decide (retry, mark-paid manually with method=ach,
    # etc).
    stripe_tx_id: Optional[str] = None
    if data.payout_method == "stripe_connect":
        method = await db.partner_payout_methods.find_one(
            {"user_id": p.get("artist_user_id")}, {"_id": 0},
        )
        if not method or not method.get("stripe_account_id"):
            raise HTTPException(
                400,
                "Artist has no Stripe Connect account on file. Ask them "
                "to onboard at /partner/me/payout-method first.",
            )
        if method.get("stripe_connect_status") != "ready":
            raise HTTPException(
                400,
                f"Stripe account is not ready for transfers "
                f"(status: {method.get('stripe_connect_status')}). "
                f"Artist must complete onboarding first.",
            )
        try:
            from utils.stripe_connect import create_transfer
            tx = create_transfer(
                amount_usd=float(p["list_price"]),
                destination_account_id=method["stripe_account_id"],
                transfer_group=p["order_id"],
                idempotency_key=f"birthright-payout-{p['id']}",
                metadata={
                    "payout_id": p["id"],
                    "artist_user_id": p.get("artist_user_id") or "",
                    "order_id": p.get("order_id") or "",
                    "artwork": (p.get("artwork_name") or "")[:200],
                },
            )
            stripe_tx_id = tx["id"]
        except Exception as e:
            logger.exception("Stripe Connect transfer failed: %s", e)
            raise HTTPException(
                502, f"Stripe transfer failed: {str(e)[:300]}",
            )

    await db.artist_sale_payouts.update_one(
        {"id": payout_id},
        {"$set": {
            "status": "paid",
            "paid_at": now_iso(),
            "paid_by_admin": user["email"],
            "payout_method": data.payout_method,
            "payout_reference": stripe_tx_id or data.payout_reference,
            "stripe_transfer_id": stripe_tx_id,
            "notes": data.notes,
        }},
    )
    return {"ok": True, "stripe_transfer_id": stripe_tx_id}


# -------- Bulk payout (monthly disbursement) --------

class BulkPayRequest(BaseModel):
    payout_ids: Optional[list[str]] = Field(
        default=None,
        description="If omitted, all pending payouts where the artist has "
                     "a Stripe Connect account in 'ready' status will be paid.",
    )
    notes: Optional[str] = Field(default=None, max_length=2000)


@admin_router.post("/payouts/bulk-pay")
async def admin_bulk_pay(
    data: BulkPayRequest,
    user: dict = Depends(require_roles("admin")),
):
    """Iterate through pending payouts and fire a Stripe Connect Transfer
    for each artist with a ready Connect account. Returns a per-row result
    array; failed transfers leave the row in `pending` with a reason."""
    from database import db
    from utils.stripe_connect import create_transfer

    q = {"status": "pending"}
    if data.payout_ids:
        q["id"] = {"$in": data.payout_ids}
    rows = await db.artist_sale_payouts.find(q, {"_id": 0}).to_list(2000)

    # Pre-load all artist payout methods in one query.
    artist_ids = list({r.get("artist_user_id")
                        for r in rows if r.get("artist_user_id")})
    methods = await db.partner_payout_methods.find(
        {"user_id": {"$in": artist_ids}}, {"_id": 0},
    ).to_list(len(artist_ids) + 1) if artist_ids else []
    by_artist = {m["user_id"]: m for m in methods}

    results = []
    paid_total = 0.0
    for p in rows:
        m = by_artist.get(p.get("artist_user_id") or "")
        if not m or m.get("method_type") != "stripe_connect":
            results.append({
                "payout_id": p["id"], "ok": False,
                "skipped": "no_stripe_connect_method",
            })
            continue
        if m.get("stripe_connect_status") != "ready":
            results.append({
                "payout_id": p["id"], "ok": False,
                "skipped": f"connect_status_{m.get('stripe_connect_status')}",
            })
            continue
        try:
            tx = create_transfer(
                amount_usd=float(p["list_price"]),
                destination_account_id=m["stripe_account_id"],
                transfer_group=p["order_id"],
                idempotency_key=f"birthright-payout-{p['id']}",
                metadata={
                    "payout_id": p["id"],
                    "artist_user_id": p.get("artist_user_id") or "",
                    "order_id": p.get("order_id") or "",
                    "bulk": "true",
                },
            )
            await db.artist_sale_payouts.update_one(
                {"id": p["id"]},
                {"$set": {
                    "status": "paid",
                    "paid_at": now_iso(),
                    "paid_by_admin": user["email"],
                    "payout_method": "stripe_connect",
                    "payout_reference": tx["id"],
                    "stripe_transfer_id": tx["id"],
                    "notes": data.notes,
                }},
            )
            paid_total += float(p["list_price"])
            results.append({"payout_id": p["id"], "ok": True,
                              "stripe_transfer_id": tx["id"]})
        except Exception as e:
            logger.exception("Bulk pay transfer failed: %s", e)
            results.append({"payout_id": p["id"], "ok": False,
                              "error": str(e)[:300]})
    return {
        "attempted": len(rows),
        "paid": sum(1 for r in results if r["ok"]),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "failed": sum(1 for r in results if not r["ok"] and not r.get("skipped")),
        "total_paid_usd": round(paid_total, 2),
        "results": results,
    }


# ------- Public "patches" line for the marketing landing page -------


# ============ ADMIN — tier overrides ============
class TierOverride(BaseModel):
    user_id: str
    tier_key: Literal[
        "emerging", "sustaining", "established", "thriving", "flourishing"
    ]
    reason: str = Field(min_length=4, max_length=500)


@admin_router.get("/tier-overrides")
async def admin_list_overrides(user: dict = Depends(require_roles("admin"))):
    from database import db
    rows = await db.artist_tier_overrides.find(
        {"active": True}, {"_id": 0},
    ).to_list(500)
    return rows


@admin_router.post("/tier-overrides")
async def admin_create_override(
    data: TierOverride,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    # Mark any existing override as inactive (audit trail preserved).
    await db.artist_tier_overrides.update_many(
        {"user_id": data.user_id, "active": True},
        {"$set": {"active": False, "deactivated_at": now_iso(),
                   "deactivated_by": user["email"]}},
    )
    doc = {
        "id": gen_id(),
        "user_id": data.user_id,
        "tier_key": data.tier_key,
        "reason": data.reason,
        "active": True,
        "created_at": now_iso(),
        "created_by": user["email"],
    }
    await db.artist_tier_overrides.insert_one(dict(doc))
    return {"ok": True, "id": doc["id"]}


# ============ Patronage payout helper (called from checkout) ============
async def record_patronage_payouts(db, order: dict) -> list[str]:
    """For each paid line item flagged is_gallery_artwork=True, insert one
    pending payout row. Idempotent on (order_id, product_id).

    Returns the list of inserted payout IDs.
    """
    inserted: list[str] = []
    items = order.get("items") or []
    if not items:
        return inserted
    # Find which line items are gallery artworks.
    pids = [li.get("product_id") for li in items if li.get("product_id")]
    if not pids:
        return inserted
    products = await db.products.find(
        {"id": {"$in": pids}, "is_gallery_artwork": True},
        {"_id": 0, "id": 1, "name": 1, "image_url": 1,
         "gallery_artist_user_id": 1, "gallery_artist_name": 1,
         "price": 1, "edition": 1, "dimensions": 1, "medium": 1},
    ).to_list(len(pids) + 1)
    by_id = {p["id"]: p for p in products}

    GALLERY_MARKUP_PCT = 0.20  # constant hospitality fee on top
    for li in items:
        prod = by_id.get(li.get("product_id"))
        if not prod:
            continue
        # Idempotency.
        exists = await db.artist_sale_payouts.find_one(
            {"order_id": order["id"], "product_id": prod["id"]},
            {"_id": 0, "id": 1},
        )
        if exists:
            continue
        qty = int(li.get("quantity") or 1)
        list_price = float(prod.get("price") or li.get("price") or 0) * qty
        markup = round(list_price * GALLERY_MARKUP_PCT, 2)
        doc = {
            "id": gen_id(),
            "order_id": order["id"],
            "product_id": prod["id"],
            "artist_user_id": prod.get("gallery_artist_user_id"),
            "artist_name": prod.get("gallery_artist_name"),
            "artwork_name": prod.get("name"),
            "artwork_image_url": prod.get("image_url"),
            "edition": prod.get("edition"),
            "dimensions": prod.get("dimensions"),
            "medium": prod.get("medium"),
            "quantity": qty,
            "list_price": round(list_price, 2),
            "foundation_markup": markup,
            "total_paid_by_buyer": round(list_price + markup, 2),
            "buyer_user_id": order.get("user_id"),
            "buyer_email": order.get("email"),
            "shipping_address": order.get("shipping_address"),
            "status": "pending",
            "created_at": now_iso(),
            "paid_at": None,
            "paid_by_admin": None,
            "payout_method": None,
            "payout_reference": None,
            "notes": None,
        }
        await db.artist_sale_payouts.insert_one(dict(doc))
        inserted.append(doc["id"])
    return inserted
