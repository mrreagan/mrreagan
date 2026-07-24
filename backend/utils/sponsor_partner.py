"""Sponsor Partner elevation logic.

Auto-elevates a sponsor to Sponsor Partner status once their cumulative,
confirmed contributions cross the threshold. Called from:
  - Campaign pledge status → "paid" (routers/campaigns.py)
  - Sponsorship subscription webhook → "active" (checkout / stripe webhook)

Thresholds (kept as constants so they can be tuned in one place):
  - Contributor: any paid contribution.
  - Sponsor Partner: $100+ single OR $25+/mo × 3+ months of active recurring.
  - Presenting Sponsor: $5,000+ single OR $250+/mo of active recurring.

Lifetime:
  - Status renews annually (last_paid_at gets refreshed on any new payment).
  - After 18 months of no new payment, auto-degrades to `alumni_contributor`
    by the nightly scheduler (see scheduler task `sponsor_partner_maintenance`).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from models import gen_id, now_iso

logger = logging.getLogger("birthright.sponsor_partner")

# ---- Thresholds ----
SPONSOR_PARTNER_ONE_TIME_USD = 100.0
SPONSOR_PARTNER_MONTHLY_USD = 25.0
SPONSOR_PARTNER_MONTHLY_MONTHS = 3
PRESENTING_ONE_TIME_USD = 5000.0
PRESENTING_MONTHLY_USD = 250.0
ALUMNI_DEGRADE_DAYS = 18 * 30  # ~18 months


_slug_re = re.compile(r"[^a-z0-9]+")


def _slug(s: str) -> str:
    return _slug_re.sub("-", (s or "").strip().lower()).strip("-") or "sponsor"


def _determine_level(cumulative_one_time: float, active_monthly: float, monthly_months: int) -> str:
    """Returns one of: contributor | sponsor_partner | presenting."""
    if cumulative_one_time >= PRESENTING_ONE_TIME_USD or active_monthly >= PRESENTING_MONTHLY_USD:
        return "presenting"
    meets_one_time = cumulative_one_time >= SPONSOR_PARTNER_ONE_TIME_USD
    meets_monthly = (
        active_monthly >= SPONSOR_PARTNER_MONTHLY_USD
        and monthly_months >= SPONSOR_PARTNER_MONTHLY_MONTHS
    )
    if meets_one_time or meets_monthly:
        return "sponsor_partner"
    return "contributor"


async def _totals_for_email(db, email: str) -> tuple[float, float, int]:
    """
    Returns (cumulative_one_time_usd, current_monthly_recurring_usd, months_active).
    Sums:
      - `sponsor_pledges` where status in ("paid",) matched by sponsor_email
      - `sponsorships` (existing Stripe-based recurring) where email matches and status active
    """
    one_time = 0.0
    async for p in db.sponsor_pledges.find({"sponsor_email": email, "status": "paid"}):
        one_time += float(p.get("amount") or 0)

    monthly_amount = 0.0
    months_active = 0
    try:
        async for s in db.sponsorships.find({"email": email}):
            if s.get("status") in ("active", "trialing"):
                monthly_amount += float(s.get("monthly_amount") or 0)
                # If the record has a `started_at`, calculate months of activity.
                started = s.get("started_at") or s.get("created_at")
                if started:
                    try:
                        if isinstance(started, str):
                            started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                        else:
                            started_dt = started
                        months_active = max(
                            months_active,
                            int((datetime.now(timezone.utc) - started_dt).days / 30),
                        )
                    except Exception:
                        pass
    except Exception:
        # Collection may not exist yet in dev.
        pass
    return round(one_time, 2), round(monthly_amount, 2), months_active


async def maybe_elevate_sponsor_partner(
    db,
    sponsor_email: str,
    sponsor_name: str,
    organization: Optional[str] = None,
    display_publicly: bool = False,
) -> Optional[dict]:
    """
    Upserts a `sponsor_partner_records` row for the sponsor and, if the
    computed level is `sponsor_partner` or `presenting`, also upserts a
    `partner_profiles` row with `partner_type = "sponsor"` so the sponsor
    appears in the partner directory.

    Returns the sponsor_partner_records doc, or None if the sponsor could
    not be resolved to an email.

    Idempotent — safe to call from webhooks and admin actions.
    """
    if not sponsor_email:
        return None
    email = sponsor_email.strip().lower()

    one_time, monthly_amount, months_active = await _totals_for_email(db, email)
    level = _determine_level(one_time, monthly_amount, months_active)

    now = now_iso()

    # Upsert sponsor_partner_records
    record = await db.sponsor_partner_records.find_one({"email": email}, {"_id": 0})
    prev_level = record.get("level") if record else None
    if not record:
        record = {
            "id": gen_id(),
            "email": email,
            "sponsor_name": sponsor_name,
            "organization": organization,
            "display_publicly": bool(display_publicly),
            "cumulative_one_time_usd": one_time,
            "current_monthly_usd": monthly_amount,
            "monthly_months_active": months_active,
            "level": level,
            "created_at": now,
            "last_paid_at": now,
            "updated_at": now,
        }
        await db.sponsor_partner_records.insert_one(dict(record))
    else:
        # Only overwrite name/org on upgrade or if missing.
        update = {
            "cumulative_one_time_usd": one_time,
            "current_monthly_usd": monthly_amount,
            "monthly_months_active": months_active,
            "level": level,
            "last_paid_at": now,
            "updated_at": now,
        }
        if display_publicly and not record.get("display_publicly"):
            update["display_publicly"] = True
        if organization and not record.get("organization"):
            update["organization"] = organization
        if sponsor_name and (not record.get("sponsor_name") or record.get("sponsor_name") == "Anonymous"):
            update["sponsor_name"] = sponsor_name
        await db.sponsor_partner_records.update_one({"email": email}, {"$set": update})
        record.update(update)

    # If we crossed into Sponsor Partner or Presenting, ensure a partner profile exists.
    if level in ("sponsor_partner", "presenting"):
        # Attach to a user account if one exists with this email.
        user = await db.users.find_one({"email": email}, {"_id": 0, "id": 1})
        user_id = user["id"] if user else f"sponsor-{email}"

        existing = await db.partner_profiles.find_one(
            {"user_id": user_id, "partner_type": "sponsor"}, {"_id": 0}
        )
        if existing:
            await db.partner_profiles.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "status": "active",
                    "sponsor_level": level,
                    "updated_at": now,
                }},
            )
        else:
            display_name = sponsor_name.strip() if sponsor_name else "Sponsor"
            if not display_publicly:
                display_name = "Anonymous Sponsor"
            base = _slug(display_name if display_publicly else "anonymous-sponsor")
            slug = base
            i = 1
            while await db.partner_profiles.find_one({"slug": slug}, {"_id": 0, "id": 1}):
                i += 1
                slug = f"{base}-{i}"
            profile = {
                "id": gen_id(),
                "user_id": user_id,
                "partner_type": "sponsor",
                "status": "active",
                "public": bool(display_publicly),
                "slug": slug,
                "display_name": display_name,
                "headline": "Presenting Sponsor" if level == "presenting" else "Sponsor Partner",
                "bio": (
                    f"Underwrites the mission of Birthright Foundation."
                    + (f" — {organization}" if organization else "")
                ),
                "source": "auto_elevated_from_sponsorship",
                "sponsor_level": level,
                "approved_at": now,
                "approved_by": "system",
                "approval_note": (
                    f"Auto-elevated to {level} on {now}. "
                    f"Cumulative one-time ${one_time:,.2f}, "
                    f"active recurring ${monthly_amount:,.2f}/mo × {months_active} months."
                ),
                "agreed_to_partnership_terms_at": now,
                "created_at": now,
                "updated_at": now,
            }
            await db.partner_profiles.insert_one(dict(profile))

    if prev_level != level:
        logger.info(
            "Sponsor %s elevated: %s -> %s (one_time=$%.2f, monthly=$%.2f/mo × %dm)",
            email, prev_level, level, one_time, monthly_amount, months_active,
        )
    return record


async def degrade_stale_sponsors(db) -> int:
    """Called by the scheduler. Any sponsor_partner_records with `last_paid_at`
    older than 18 months is marked `alumni_contributor` and their partner
    profile is set to `alumni` status."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ALUMNI_DEGRADE_DAYS)).isoformat()
    count = 0
    async for rec in db.sponsor_partner_records.find({
        "level": {"$in": ["sponsor_partner", "presenting"]},
        "last_paid_at": {"$lt": cutoff},
    }):
        await db.sponsor_partner_records.update_one(
            {"id": rec["id"]},
            {"$set": {"level": "alumni_contributor", "updated_at": now_iso()}},
        )
        # Downgrade partner profile
        await db.partner_profiles.update_many(
            {"user_id": rec.get("user_id") or f"sponsor-{rec['email']}", "partner_type": "sponsor"},
            {"$set": {"status": "alumni", "sponsor_level": "alumni_contributor", "updated_at": now_iso()}},
        )
        count += 1
    if count:
        logger.info("Degraded %d sponsor(s) to alumni_contributor.", count)
    return count
