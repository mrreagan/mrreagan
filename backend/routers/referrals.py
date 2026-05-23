"""Community partner referrals + payout ledger.

Flow:
  1. Each approved PartnerProfile gets a unique referral_code (auto-generated
     on approval; backfilled by `scripts/backfill_referral_codes.py`).
  2. Public redirect `GET /api/r/{code}?workshop=&product=&dest=` sets a short-lived
     cookie `birthright_ref={code}` and 302s to the destination URL.
  3. At Stripe checkout, the cookie is attached to `payment_transactions.metadata.referral_code`.
  4. On fulfilment (workshop registration or product order), if metadata has a
     referral_code we insert a `referrals` row with computed `payout_amount =
     order_total * partner.rev_share_pct / 100`. Status starts 'earned'.
  5. Admin can mark referrals 'paid' (records payout method + reference).
"""
from __future__ import annotations

import logging
import secrets
import string
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from auth_utils import get_current_user, require_roles
from models import PayoutMarkPaid, gen_id, now_iso
from utils.audit import log_action
from utils.rev_share import resolve_rev_share

logger = logging.getLogger("birthright.referrals")

# Top-level router so /api/r/{code} stays at the application root (clean affiliate URL).
public_router = APIRouter(prefix="/r", tags=["referrals-public"])
my_router = APIRouter(prefix="/referrals", tags=["referrals"])
admin_router = APIRouter(prefix="/admin/referrals", tags=["referrals-admin"])

REFERRAL_COOKIE = "birthright_ref"
REFERRAL_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


# ============ CODE GENERATION ============

def generate_referral_code(seed: str = "") -> str:
    """8-char alphanumeric code (upper). Seed is just for entropy; the random
    bit ensures uniqueness."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


async def ensure_referral_code(db, profile: dict) -> str:
    """Assign a unique code if missing, or return the existing one."""
    if profile.get("referral_code"):
        return profile["referral_code"]
    # Generate-then-check loop (extremely unlikely collision on 8-char base36 = 2.8T combos)
    for _ in range(8):
        code = generate_referral_code(profile["id"])
        existing = await db.partner_profiles.find_one({"referral_code": code})
        if not existing:
            await db.partner_profiles.update_one(
                {"id": profile["id"]}, {"$set": {"referral_code": code, "updated_at": now_iso()}}
            )
            return code
    raise RuntimeError("Could not generate unique referral code after 8 attempts.")


# ============ PUBLIC REDIRECT ============

@public_router.get("/{code}")
async def referral_redirect(
    code: str,
    workshop: Optional[str] = Query(default=None, description="Workshop slug to land on"),
    product: Optional[str] = Query(default=None, description="Product slug or id to land on"),
    dest: Optional[str] = Query(default=None, description="Custom destination path (relative)"),
):
    """Cookie + 302. Code is case-insensitive."""
    from database import db
    code_up = code.strip().upper()
    profile = await db.partner_profiles.find_one(
        {"referral_code": code_up, "status": "active"}, {"_id": 0}
    )
    if not profile:
        # Don't leak whether the code exists or just isn't active — just send to home.
        return RedirectResponse(url="/", status_code=302)

    # Resolve destination (relative path, joined with frontend origin by browser).
    if workshop:
        target = f"/workshops/{workshop}"
    elif product:
        target = f"/shop/{product}"
    elif dest and dest.startswith("/"):
        target = dest
    else:
        target = f"/partners/{profile['slug']}"

    resp = RedirectResponse(url=target, status_code=302)
    resp.set_cookie(
        key=REFERRAL_COOKIE,
        value=code_up,
        max_age=REFERRAL_COOKIE_MAX_AGE,
        httponly=False,  # frontend may want to surface "referred by"
        samesite="lax",
        secure=True,
    )
    # Fire-and-forget click log
    try:
        await db.referral_clicks.insert_one({
            "id": gen_id(),
            "code": code_up,
            "partner_profile_id": profile["id"],
            "target": target,
            "created_at": now_iso(),
        })
    except Exception as e:
        logger.warning(f"referral click log failed: {e}")
    return resp


# ============ ATTRIBUTION CAPTURE (called from checkout) ============

async def resolve_referral_for_checkout(db, referral_code: Optional[str]) -> Optional[dict]:
    """Return {code, partner_profile_id, partner_user_id, partner_type, pct} if
    `referral_code` resolves to an active community partner with active subscription;
    otherwise None."""
    if not referral_code:
        return None
    code_up = referral_code.strip().upper()
    profile = await db.partner_profiles.find_one(
        {"referral_code": code_up, "status": "active"}, {"_id": 0}
    )
    if not profile or profile["partner_type"] != "community":
        return None
    rev = await resolve_rev_share(db, profile["user_id"], "community")
    return {
        "code": code_up,
        "partner_profile_id": profile["id"],
        "partner_user_id": profile["user_id"],
        "partner_type": profile["partner_type"],
        "pct": float(rev["pct"]),
        "rev_share_source": rev["source"],
    }


async def record_referral(db, txn: dict, attribution: dict, subject: dict) -> Optional[str]:
    """Insert a referral row after fulfilment. Idempotent on payment_session_id."""
    existing = await db.referrals.find_one({"payment_session_id": txn["session_id"]})
    if existing:
        return None
    amount = float(txn.get("amount") or 0)
    payout = round(amount * float(attribution["pct"]) / 100, 2)
    doc = {
        "id": gen_id(),
        "payment_session_id": txn["session_id"],
        "referral_code": attribution["code"],
        "partner_profile_id": attribution["partner_profile_id"],
        "partner_user_id": attribution["partner_user_id"],
        "buyer_user_id": txn.get("user_id"),
        "subject_type": subject["type"],   # 'workshop' or 'order'
        "subject_id": subject["id"],
        "subject_label": subject.get("label", ""),
        "order_total": amount,
        "rev_share_pct": attribution["pct"],
        "payout_amount": payout,
        "status": "earned",
        "earned_at": now_iso(),
        "paid_at": None,
        "payout_method": None,
        "payout_reference": None,
        "payout_note": None,
    }
    await db.referrals.insert_one(dict(doc))
    return doc["id"]


# ============ PARTNER-FACING ENDPOINTS ============

@my_router.get("/my-earnings")
async def my_earnings(user: dict = Depends(get_current_user)):
    """All-time earnings for the caller across their partner profiles."""
    from database import db
    referrals = await db.referrals.find(
        {"partner_user_id": user["id"]}, {"_id": 0}
    ).sort("earned_at", -1).to_list(2000)
    earned = sum(r["payout_amount"] for r in referrals if r["status"] == "earned")
    paid = sum(r["payout_amount"] for r in referrals if r["status"] == "paid")
    by_subject = {"workshop": 0.0, "order": 0.0}
    for r in referrals:
        by_subject[r["subject_type"]] = by_subject.get(r["subject_type"], 0) + r["payout_amount"]
    return {
        "summary": {
            "count": len(referrals),
            "lifetime_total": round(earned + paid, 2),
            "pending_payout": round(earned, 2),
            "paid_to_date": round(paid, 2),
            "by_subject_type": {k: round(v, 2) for k, v in by_subject.items()},
        },
        "recent": referrals[:50],
    }


@my_router.get("/my-link/{partner_type}")
async def my_referral_link(partner_type: str, user: dict = Depends(get_current_user)):
    """Returns the referral code + canonical link for the caller's profile of this type."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": partner_type, "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="No active partner profile of that type")
    code = await ensure_referral_code(db, profile)
    return {
        "code": code,
        "base_path": f"/api/r/{code}",  # frontend will prepend origin
    }


# ============ ADMIN ENDPOINTS ============

@admin_router.get("")
async def list_referrals(
    status: Optional[str] = None,
    partner_user_id: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    if partner_user_id:
        query["partner_user_id"] = partner_user_id
    rows = await db.referrals.find(query, {"_id": 0}).sort("earned_at", -1).to_list(limit)
    return rows


@admin_router.get("/payout-summary")
async def payout_summary(user: dict = Depends(require_roles("admin"))):
    """Per-partner aggregate: earned (pending) and lifetime paid."""
    from database import db
    pipeline = [
        {"$group": {
            "_id": {"partner_user_id": "$partner_user_id", "status": "$status"},
            "total": {"$sum": "$payout_amount"},
            "count": {"$sum": 1},
        }},
    ]
    rows = []
    async for r in db.referrals.aggregate(pipeline):
        rows.append(r)
    # Reduce into per-partner map
    per_partner: dict[str, dict] = {}
    for r in rows:
        pid = r["_id"]["partner_user_id"]
        if pid not in per_partner:
            per_partner[pid] = {"partner_user_id": pid, "earned": 0.0, "paid": 0.0, "count": 0}
        if r["_id"]["status"] == "earned":
            per_partner[pid]["earned"] += r["total"]
        elif r["_id"]["status"] == "paid":
            per_partner[pid]["paid"] += r["total"]
        per_partner[pid]["count"] += r["count"]
    # Enrich with names
    user_ids = list(per_partner.keys())
    users = await db.users.find(
        {"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1}
    ).to_list(len(user_ids) or 1)
    name_by = {u["id"]: f"{u['first_name']} {u['last_name']}" for u in users}
    email_by = {u["id"]: u["email"] for u in users}
    for pid, row in per_partner.items():
        row["partner_name"] = name_by.get(pid, "(unknown)")
        row["partner_email"] = email_by.get(pid, "")
        row["earned"] = round(row["earned"], 2)
        row["paid"] = round(row["paid"], 2)
    return sorted(per_partner.values(), key=lambda r: r["earned"], reverse=True)


@admin_router.post("/{referral_id}/mark-paid")
async def mark_referral_paid(
    referral_id: str,
    data: PayoutMarkPaid,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    r = await db.referrals.find_one({"id": referral_id})
    if not r:
        raise HTTPException(status_code=404, detail="Referral not found")
    if r["status"] != "earned":
        raise HTTPException(status_code=400, detail=f"Referral is already {r['status']}")
    await db.referrals.update_one(
        {"id": referral_id},
        {"$set": {
            "status": "paid",
            "paid_at": now_iso(),
            "payout_method": data.method or "manual",
            "payout_reference": (data.reference or "").strip(),
            "payout_note": (data.note or "").strip(),
            "paid_by": user["id"],
        }},
    )
    await log_action(
        db, user, "referral.payout.mark_paid",
        target_type="referral", target_id=referral_id,
        metadata={"amount": r["payout_amount"], "partner_user_id": r["partner_user_id"]},
    )
    updated = await db.referrals.find_one({"id": referral_id}, {"_id": 0})
    return updated
