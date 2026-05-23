"""Engagement + financial reporting for participants, partners, and admin.

Public endpoints:
  GET /api/me/reports            — auto-detects caller's profile types and returns
                                   all relevant slices (participant + partner)
  GET /api/admin/reports         — org-wide rollups (admin only)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from auth_utils import get_current_user, require_roles

my_router = APIRouter(prefix="/me/reports", tags=["reports"])
admin_router = APIRouter(prefix="/admin/reports", tags=["reports-admin"])


# ============ HELPERS ============

async def _participant_engagement(db, user_id: str) -> dict:
    """Workshops attended (paid), reviews written, impact statements written."""
    paid_regs = await db.registrations.find(
        {"user_id": user_id, "payment_status": "paid"}, {"_id": 0}
    ).to_list(500)
    attended = sum(1 for r in paid_regs if r.get("checked_in"))
    review_count = await db.reviews.count_documents({"user_id": user_id})
    impact_count = await db.impact_statements.count_documents({"user_id": user_id})
    discussion_count = await db.discussions.count_documents({"user_id": user_id})
    return {
        "registrations": len(paid_regs),
        "workshops_attended": attended,
        "reviews_written": review_count,
        "impact_statements": impact_count,
        "discussions_posted": discussion_count,
    }


async def _participant_finance(db, user_id: str) -> dict:
    """How much the user has spent, by category."""
    spent_workshops = sum(r.get("amount_paid", 0) for r in await db.registrations.find(
        {"user_id": user_id, "payment_status": "paid"}, {"_id": 0, "amount_paid": 1}
    ).to_list(500))
    orders = await db.orders.find({"user_id": user_id}, {"_id": 0, "total": 1}).to_list(500)
    spent_orders = sum(o.get("total", 0) for o in orders)
    sponsorships = await db.sponsorships.find({"user_id": user_id}, {"_id": 0, "amount": 1}).to_list(100)
    spent_sponsorship = sum(s.get("amount", 0) for s in sponsorships)
    donations = await db.donations.find({"user_id": user_id}, {"_id": 0, "amount": 1}).to_list(200)
    spent_donations = sum(d.get("amount", 0) for d in donations)
    total = spent_workshops + spent_orders + spent_sponsorship + spent_donations
    return {
        "lifetime_spend": round(total, 2),
        "by_category": {
            "workshops": round(spent_workshops, 2),
            "shop": round(spent_orders, 2),
            "sponsorship": round(spent_sponsorship, 2),
            "donations": round(spent_donations, 2),
        },
    }


async def _partner_finance(db, user_id: str) -> Optional[dict]:
    """Earnings summary if the user has any referral activity OR a partner profile."""
    profiles = await db.partner_profiles.find({"user_id": user_id}, {"_id": 0}).to_list(10)
    if not profiles:
        return None
    referrals = await db.referrals.find({"partner_user_id": user_id}, {"_id": 0}).to_list(2000)
    earned = round(sum(r["payout_amount"] for r in referrals if r["status"] == "earned"), 2)
    paid = round(sum(r["payout_amount"] for r in referrals if r["status"] == "paid"), 2)
    # Active subscriptions
    now = datetime.now(timezone.utc).isoformat()
    active_subs = await db.partner_subscriptions.find(
        {"user_id": user_id, "status": "active", "expires_at": {"$gt": now}},
        {"_id": 0},
    ).to_list(10)
    # Click activity for context
    codes = [p["referral_code"] for p in profiles if p.get("referral_code")]
    clicks = await db.referral_clicks.count_documents({"code": {"$in": codes}}) if codes else 0
    return {
        "profiles": [
            {
                "partner_type": p["partner_type"],
                "status": p["status"],
                "referral_code": p.get("referral_code"),
                "slug": p["slug"],
            }
            for p in profiles
        ],
        "active_subscriptions": [
            {"partner_type": s["partner_type"], "plan_id": s["plan_id"], "expires_at": s["expires_at"]}
            for s in active_subs
        ],
        "referrals": {
            "count": len(referrals),
            "clicks": clicks,
            "pending_payout": earned,
            "paid_to_date": paid,
            "lifetime_total": round(earned + paid, 2),
        },
    }


@my_router.get("")
async def my_reports(user: dict = Depends(get_current_user)) -> dict:
    """Auto-detect: all signed-in users see participant engagement+finance.
    Partner users also see partner_finance."""
    from database import db
    return {
        "engagement": await _participant_engagement(db, user["id"]),
        "finance": await _participant_finance(db, user["id"]),
        "partner": await _partner_finance(db, user["id"]),
    }


# ============ ADMIN AGGREGATES ============

async def _revenue_rollup(db) -> dict:
    total_workshops = await db.registrations.aggregate([
        {"$match": {"payment_status": "paid"}},
        {"$group": {"_id": None, "sum": {"$sum": "$amount_paid"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    total_orders = await db.orders.aggregate([
        {"$group": {"_id": None, "sum": {"$sum": "$total"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    total_subs = await db.partner_subscriptions.aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": None, "sum": {"$sum": "$amount_paid"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    sponsor_sum = await db.sponsorships.aggregate([
        {"$group": {"_id": None, "sum": {"$sum": "$amount"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    donations_sum = await db.donations.aggregate([
        {"$group": {"_id": None, "sum": {"$sum": "$amount"}, "n": {"$sum": 1}}},
    ]).to_list(1)

    def _v(rows, key="sum"):
        return float((rows[0] if rows else {}).get(key, 0) or 0)

    return {
        "workshops":    {"revenue": round(_v(total_workshops), 2), "count": _v(total_workshops, "n")},
        "shop":         {"revenue": round(_v(total_orders), 2),     "count": _v(total_orders, "n")},
        "subscriptions":{"revenue": round(_v(total_subs), 2),       "count": _v(total_subs, "n")},
        "sponsorship":  {"revenue": round(_v(sponsor_sum), 2),      "count": _v(sponsor_sum, "n")},
        "donations":    {"revenue": round(_v(donations_sum), 2),    "count": _v(donations_sum, "n")},
        "gross_total": round(_v(total_workshops) + _v(total_orders) + _v(total_subs) + _v(sponsor_sum) + _v(donations_sum), 2),
    }


async def _payout_liability(db) -> dict:
    pipeline = [
        {"$group": {"_id": "$status", "sum": {"$sum": "$payout_amount"}, "n": {"$sum": 1}}},
    ]
    by_status = {"earned": {"sum": 0.0, "n": 0}, "paid": {"sum": 0.0, "n": 0}}
    async for r in db.referrals.aggregate(pipeline):
        if r["_id"] in by_status:
            by_status[r["_id"]] = {"sum": round(float(r["sum"] or 0), 2), "n": int(r["n"])}
    return {"pending_payouts": by_status["earned"], "paid_to_date": by_status["paid"]}


async def _engagement_rollup(db) -> dict:
    now = datetime.now(timezone.utc)
    last_30 = (now - timedelta(days=30)).isoformat()
    return {
        "users": await db.users.count_documents({}),
        "workshops": await db.workshops.count_documents({}),
        "products": await db.products.count_documents({}),
        "reviews": await db.reviews.count_documents({}),
        "discussions": await db.discussions.count_documents({}),
        "active_subscriptions": await db.partner_subscriptions.count_documents({
            "status": "active",
            "expires_at": {"$gt": now.isoformat()},
        }),
        "partners_active": await db.partner_profiles.count_documents({"status": "active"}),
        "new_registrations_30d": await db.registrations.count_documents({
            "payment_status": "paid", "created_at": {"$gt": last_30},
        }),
        "new_signups_30d": await db.users.count_documents({"created_at": {"$gt": last_30}}),
    }


async def _top_partners_by_referrals(db, limit: int = 10) -> list[dict]:
    pipeline = [
        {"$group": {
            "_id": "$partner_user_id",
            "total": {"$sum": "$payout_amount"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"total": -1}},
        {"$limit": limit},
    ]
    rows = []
    async for r in db.referrals.aggregate(pipeline):
        rows.append(r)
    ids = [r["_id"] for r in rows]
    users = await db.users.find(
        {"id": {"$in": ids}}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}
    ).to_list(len(ids) or 1)
    name_by = {u["id"]: f"{u['first_name']} {u['last_name']}" for u in users}
    return [
        {"partner_user_id": r["_id"], "name": name_by.get(r["_id"], "(unknown)"),
         "total": round(r["total"], 2), "count": r["count"]}
        for r in rows
    ]


async def _top_workshops_by_revenue(db, limit: int = 10) -> list[dict]:
    pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {"_id": "$workshop_id", "total": {"$sum": "$amount_paid"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": limit},
    ]
    rows = []
    async for r in db.registrations.aggregate(pipeline):
        rows.append(r)
    ids = [r["_id"] for r in rows]
    workshops = await db.workshops.find(
        {"id": {"$in": ids}}, {"_id": 0, "id": 1, "title": 1, "slug": 1}
    ).to_list(len(ids) or 1)
    label_by = {w["id"]: w["title"] for w in workshops}
    slug_by = {w["id"]: w.get("slug") for w in workshops}
    return [
        {"workshop_id": r["_id"], "title": label_by.get(r["_id"], "(unknown)"),
         "slug": slug_by.get(r["_id"]),
         "revenue": round(r["total"], 2), "registrations": r["count"]}
        for r in rows
    ]


@admin_router.get("")
async def admin_reports(user: dict = Depends(require_roles("admin"))) -> dict:
    from database import db
    return {
        "engagement": await _engagement_rollup(db),
        "revenue": await _revenue_rollup(db),
        "payouts": await _payout_liability(db),
        "top_partners": await _top_partners_by_referrals(db, limit=10),
        "top_workshops": await _top_workshops_by_revenue(db, limit=10),
    }
