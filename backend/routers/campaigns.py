"""Sponsor Campaigns — target-specific sponsorship drives (pledge-only for now).

A "campaign" is a scoped fundraising goal (e.g., "Inside Success TV feature").
Public users can pledge support (name, org, email, amount, message, tier).
No money moves — all pledges are collected as intent, reviewed by admin,
then invoiced manually. This is deliberate: Birthright does not yet hold
501(c)(3) status, so nothing here is tax-deductible and we say so loudly.

Design notes:
  - `pledge_only=True` on every campaign until legal review says otherwise.
  - `non_deductible_notice` is stamped into API responses so the frontend
    cannot forget to display it.
  - Tiers are stored inline on the campaign so admins can vary them per drive.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth_utils import require_roles
from models import gen_id, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.campaigns")

public_router = APIRouter(prefix="/campaigns", tags=["campaigns"])
admin_router = APIRouter(prefix="/admin/campaigns", tags=["campaigns-admin"])

NON_DEDUCTIBLE_NOTICE = (
    "Birthright Foundation has not yet submitted or received IRS 501(c)(3) "
    "determination. Sponsorships and contributions are not currently "
    "tax-deductible as charitable donations. Sponsors receive a business "
    "receipt only. No representation is made about future tax status."
)


# ============ Models ============
class CampaignTier(BaseModel):
    id: str
    name: str
    amount: float
    perks: str
    recognition: str = "Named recognition on the campaign page (opt-in)."


class CampaignCreate(BaseModel):
    title: str
    slug: str
    tagline: str
    story: str  # markdown allowed
    goal_amount: float = Field(gt=0)
    hero_image_url: Optional[str] = None
    pill_label: str = "Sponsor this campaign"
    status: str = "active"  # active | paused | funded | archived
    contingency_note: Optional[str] = None
    tiers: List[CampaignTier] = []


class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    tagline: Optional[str] = None
    story: Optional[str] = None
    goal_amount: Optional[float] = None
    hero_image_url: Optional[str] = None
    pill_label: Optional[str] = None
    status: Optional[str] = None
    contingency_note: Optional[str] = None
    tiers: Optional[List[CampaignTier]] = None


class PledgeCreate(BaseModel):
    sponsor_name: str
    sponsor_email: EmailStr
    organization: Optional[str] = None
    amount: float = Field(gt=0)
    tier_id: Optional[str] = None
    message: Optional[str] = None
    display_publicly: bool = False  # opt-in to be listed as a named sponsor


class PledgeStatusUpdate(BaseModel):
    status: str  # pending | approved | invoiced | paid | declined | withdrawn
    admin_note: Optional[str] = None


# ============ Helpers ============
_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(s: str) -> str:
    return _slug_re.sub("-", s.strip().lower()).strip("-")


def _clean(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc


async def _campaign_stats(db, campaign_id: str) -> dict:
    """Aggregate approved+paid pledge totals for a campaign."""
    cursor = db.sponsor_pledges.find({
        "campaign_id": campaign_id,
        "status": {"$in": ["approved", "invoiced", "paid"]},
    })
    total_pledged = 0.0
    total_paid = 0.0
    sponsor_count = 0
    public_sponsors: list[dict] = []
    async for p in cursor:
        amt = float(p.get("amount") or 0)
        total_pledged += amt
        if p.get("status") == "paid":
            total_paid += amt
        sponsor_count += 1
        if p.get("display_publicly"):
            public_sponsors.append({
                "name": p.get("sponsor_name"),
                "organization": p.get("organization"),
                "amount": amt,
                "tier_id": p.get("tier_id"),
            })
    return {
        "total_pledged": round(total_pledged, 2),
        "total_paid": round(total_paid, 2),
        "sponsor_count": sponsor_count,
        "public_sponsors": public_sponsors,
    }


async def _hydrate(db, campaign: dict) -> dict:
    stats = await _campaign_stats(db, campaign["id"])
    return {
        **campaign,
        **stats,
        "progress_pct": round(
            (stats["total_pledged"] / campaign["goal_amount"]) * 100, 1
        ) if campaign.get("goal_amount") else 0,
        "non_deductible_notice": NON_DEDUCTIBLE_NOTICE,
    }


# ============ Public endpoints ============
@public_router.get("")
async def list_campaigns(status: str = "active"):
    from database import db
    cursor = db.sponsor_campaigns.find({"status": status}).sort("created_at", -1)
    out: list[dict] = []
    async for c in cursor:
        out.append(await _hydrate(db, _clean(c)))
    return {
        "campaigns": out,
        "non_deductible_notice": NON_DEDUCTIBLE_NOTICE,
    }


@public_router.get("/{slug}")
async def get_campaign(slug: str):
    from database import db
    c = await db.sponsor_campaigns.find_one({"slug": slug})
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await _hydrate(db, _clean(c))


@public_router.post("/{slug}/pledge")
async def create_pledge(slug: str, data: PledgeCreate):
    from database import db
    c = await db.sponsor_campaigns.find_one({"slug": slug})
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if c.get("status") not in ("active",):
        raise HTTPException(status_code=400, detail="Campaign is not accepting pledges")
    tier_snapshot = None
    if data.tier_id:
        tiers = c.get("tiers") or []
        tier = next((t for t in tiers if t.get("id") == data.tier_id), None)
        if not tier:
            raise HTTPException(status_code=400, detail="Invalid tier")
        tier_snapshot = tier
    pledge = {
        "id": gen_id(),
        "campaign_id": c["id"],
        "campaign_slug": slug,
        "sponsor_name": data.sponsor_name.strip(),
        "sponsor_email": str(data.sponsor_email),
        "organization": (data.organization or "").strip() or None,
        "amount": float(data.amount),
        "tier_id": data.tier_id,
        "tier_snapshot": tier_snapshot,
        "message": (data.message or "").strip() or None,
        "display_publicly": bool(data.display_publicly),
        "status": "pending",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.sponsor_pledges.insert_one(pledge)
    # Fire-and-forget notifications (dry-run safe).
    try:
        from utils.campaign_notify import send_pledge_confirmation
        await send_pledge_confirmation(pledge, c)
    except Exception as ex:
        logger.warning("Pledge notification dispatch failed: %s", ex)
    return {
        "ok": True,
        "pledge_id": pledge["id"],
        "message": (
            "Thank you. Your pledge has been recorded and the Birthright team "
            "will follow up by email to confirm details and next steps."
        ),
        "non_deductible_notice": NON_DEDUCTIBLE_NOTICE,
    }


# ============ Admin endpoints ============
@admin_router.get("")
async def admin_list_campaigns(user: dict = Depends(require_roles("admin"))):
    from database import db
    cursor = db.sponsor_campaigns.find({}).sort("created_at", -1)
    out: list[dict] = []
    async for c in cursor:
        out.append(await _hydrate(db, _clean(c)))
    return out


@admin_router.post("")
async def admin_create_campaign(
    data: CampaignCreate,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    slug = slugify(data.slug or data.title)
    existing = await db.sponsor_campaigns.find_one({"slug": slug})
    if existing:
        raise HTTPException(status_code=400, detail=f"Slug '{slug}' already in use")
    doc = {
        "id": gen_id(),
        **data.model_dump(),
        "slug": slug,
        "tiers": [t.model_dump() for t in (data.tiers or [])],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "created_by": user["id"],
    }
    await db.sponsor_campaigns.insert_one(doc)
    await log_action(db, user, "campaign.create", target_type="campaign", target_id=doc["id"])
    return await _hydrate(db, _clean(doc))


@admin_router.put("/{campaign_id}")
async def admin_update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    update = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "tiers" in update:
        update["tiers"] = [t if isinstance(t, dict) else t.model_dump() for t in update["tiers"]]
    update["updated_at"] = now_iso()
    result = await db.sponsor_campaigns.update_one({"id": campaign_id}, {"$set": update})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await log_action(db, user, "campaign.update", target_type="campaign", target_id=campaign_id)
    c = await db.sponsor_campaigns.find_one({"id": campaign_id})
    return await _hydrate(db, _clean(c))


@admin_router.delete("/{campaign_id}")
async def admin_delete_campaign(
    campaign_id: str,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    result = await db.sponsor_campaigns.delete_one({"id": campaign_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await log_action(db, user, "campaign.delete", target_type="campaign", target_id=campaign_id)
    return {"ok": True}


@admin_router.get("/pledges/all")
async def admin_list_pledges(
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    q: dict = {}
    if campaign_id:
        q["campaign_id"] = campaign_id
    if status:
        q["status"] = status
    cursor = db.sponsor_pledges.find(q).sort("created_at", -1)
    out: list[dict] = []
    async for p in cursor:
        out.append(_clean(p))
    return out


@admin_router.put("/pledges/{pledge_id}/status")
async def admin_update_pledge_status(
    pledge_id: str,
    data: PledgeStatusUpdate,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    valid = {"pending", "approved", "invoiced", "paid", "declined", "withdrawn"}
    if data.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use one of: {sorted(valid)}")
    existing = await db.sponsor_pledges.find_one({"id": pledge_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Pledge not found")
    prev_status = existing.get("status")
    update = {
        "status": data.status,
        "updated_at": now_iso(),
    }
    if data.admin_note is not None:
        update["admin_note"] = data.admin_note
    await db.sponsor_pledges.update_one({"id": pledge_id}, {"$set": update})
    await log_action(
        db, user, "campaign.pledge.status",
        target_type="pledge", target_id=pledge_id,
        metadata={"status": data.status, "prev_status": prev_status},
    )
    p = await db.sponsor_pledges.find_one({"id": pledge_id})
    # Trigger sponsor emails on meaningful state transitions.
    try:
        if data.status != prev_status:
            campaign = await db.sponsor_campaigns.find_one({"id": p["campaign_id"]})
            if campaign:
                from utils.campaign_notify import send_invoice, send_receipt
                if data.status == "invoiced":
                    await send_invoice(p, campaign, admin_note=data.admin_note)
                elif data.status == "paid":
                    await send_receipt(p, campaign)
                    # Sponsor Partner auto-elevation: only fires on transition to paid.
                    try:
                        from utils.sponsor_partner import maybe_elevate_sponsor_partner
                        await maybe_elevate_sponsor_partner(
                            db,
                            sponsor_email=p.get("sponsor_email", ""),
                            sponsor_name=p.get("sponsor_name", ""),
                            organization=p.get("organization"),
                            display_publicly=bool(p.get("display_publicly")),
                        )
                    except Exception as ex2:
                        logger.warning("Sponsor Partner elevation failed: %s", ex2)
    except Exception as ex:
        logger.warning("Pledge status email dispatch failed: %s", ex)
    return _clean(p)


@admin_router.post("/pledges/{pledge_id}/resend-invoice")
async def admin_resend_invoice(
    pledge_id: str,
    user: dict = Depends(require_roles("admin")),
):
    """Manually re-send the invoice email (e.g. after updating payment env vars)."""
    from database import db
    p = await db.sponsor_pledges.find_one({"id": pledge_id})
    if not p:
        raise HTTPException(status_code=404, detail="Pledge not found")
    campaign = await db.sponsor_campaigns.find_one({"id": p["campaign_id"]})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    from utils.campaign_notify import send_invoice
    await send_invoice(p, campaign, admin_note=p.get("admin_note"))
    await log_action(
        db, user, "campaign.pledge.invoice_resend",
        target_type="pledge", target_id=pledge_id,
    )
    return {"ok": True}


@admin_router.get("/sponsor-partners")
async def admin_list_sponsor_partners(
    user: dict = Depends(require_roles("admin")),
):
    """Sponsor Partner directory + lapsed/at-risk view.

    Returns each sponsor's current level, totals, and days since last payment
    so admins can proactively reach out to at-risk sponsors before they degrade.
    """
    from database import db
    now = datetime.now(timezone.utc)
    out: list[dict] = []
    async for r in db.sponsor_partner_records.find({}).sort("last_paid_at", -1):
        r.pop("_id", None)
        last_paid = r.get("last_paid_at")
        days_since = None
        if last_paid:
            try:
                lp = datetime.fromisoformat(str(last_paid).replace("Z", "+00:00"))
                days_since = int((now - lp).days)
            except Exception:
                pass
        risk = "healthy"
        if r.get("level") == "alumni_contributor":
            risk = "alumni"
        elif days_since is not None:
            if days_since > 540:
                risk = "at_risk_degrade_imminent"  # >18 months, degrades next run
            elif days_since > 365:
                risk = "at_risk_renewal_overdue"  # renewal window (>12 months)
            elif days_since > 180:
                risk = "check_in"
        r["days_since_last_paid"] = days_since
        r["risk"] = risk
        out.append(r)
    return out


@admin_router.post("/sponsor-partners/run-maintenance")
async def admin_run_sponsor_maintenance(
    user: dict = Depends(require_roles("admin")),
):
    """Manually trigger the 18-month degrade sweep (usually runs nightly)."""
    from database import db
    from utils.sponsor_partner import degrade_stale_sponsors
    count = await degrade_stale_sponsors(db)
    return {"degraded": count}


# ============ Seed helper (called at startup) ============
ISTV_CAMPAIGN_SLUG = "inside-success-tv-feature"


async def ensure_istv_campaign_seeded(db) -> None:
    """Seed the Inside Success TV sponsor campaign if it doesn't exist."""
    existing = await db.sponsor_campaigns.find_one({"slug": ISTV_CAMPAIGN_SLUG})
    if existing:
        return
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": gen_id(),
        "title": "Inside Success TV Feature — Birthright Story",
        "slug": ISTV_CAMPAIGN_SLUG,
        "tagline": (
            "Bring the Birthright origin story to a national streaming audience "
            "via a professionally produced Inside Success TV episode."
        ),
        "story": (
            "## The opportunity\n\n"
            "Inside Success TV has extended a conditional casting approval to "
            "James and Amanda Reagan to film a full episode telling the Birthright "
            "story — from ordinary life, through the challenge, to the mission of "
            "helping couples build secure connection. The episode would air across "
            "Inside Success TV's distribution channels (including Amazon Prime Video) "
            "and become a permanent authority asset for the movement.\n\n"
            "## Why we're seeking sponsors\n\n"
            "The production carries a real cost, and Birthright's founders are "
            "unwilling to spend from operating capital on a media placement whose "
            "ROI is not guaranteed. Rather than say no, we're inviting mission-aligned "
            "sponsors to underwrite the production in exchange for named recognition "
            "on the episode's promotion, on this campaign page, and in the "
            "downstream content the episode generates.\n\n"
            "## What sponsorship funds\n\n"
            "- Inside Success TV production fees\n"
            "- Travel and shoot logistics\n"
            "- Licensing of the finished asset so Birthright owns the story forever\n"
            "- Downstream promotion (social cutdowns, PR distribution, website integration)\n\n"
            "## Contingencies\n\n"
            "This campaign is **contingent on ISTV agreeing to the material contract "
            "and licensing changes flagged in our legal review** — including editorial "
            "approval, defined deliverables, perpetual usage rights, mutual termination, "
            "and refund on non-performance. If ISTV declines those redlines, sponsor "
            "funds will be returned or redirected (with sponsor consent) to a comparable "
            "media effort."
        ),
        "goal_amount": 25000.0,
        "hero_image_url": None,
        "pill_label": "Sponsor the ISTV feature",
        "status": "active",
        "contingency_note": (
            "Contingent on Inside Success TV agreeing to material contract and "
            "licensing redlines from our legal review."
        ),
        "tiers": [
            {
                "id": "bronze",
                "name": "Bronze Sponsor",
                "amount": 500.0,
                "perks": "Thank-you email + named listing on the campaign page (opt-in).",
                "recognition": "Named listing on the campaign page (opt-in).",
            },
            {
                "id": "silver",
                "name": "Silver Sponsor",
                "amount": 2500.0,
                "perks": (
                    "Everything in Bronze, plus named recognition in the "
                    "episode's promotional social cutdowns."
                ),
                "recognition": "Named credit in promotional cutdowns and campaign page.",
            },
            {
                "id": "gold",
                "name": "Gold Sponsor",
                "amount": 5000.0,
                "perks": (
                    "Everything in Silver, plus logo placement on the campaign page "
                    "and a mention in the episode's end-card credits."
                ),
                "recognition": "Logo + end-card credit (subject to ISTV approval).",
            },
            {
                "id": "presenting",
                "name": "Presenting Sponsor",
                "amount": 10000.0,
                "perks": (
                    "Everything above, plus 'Presented by' branding on all Birthright-"
                    "controlled promotion of the episode and a private thank-you call "
                    "with the founders."
                ),
                "recognition": "'Presented by' branding + private founder call.",
            },
        ],
        "created_at": now,
        "updated_at": now,
        "created_by": "system",
    }
    await db.sponsor_campaigns.insert_one(doc)
    logger.info("Seeded ISTV sponsor campaign.")
