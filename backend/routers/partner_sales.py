"""Partner self-reported off-site sales reconciliation — v1.11.0 Step 3.

Flow:
  1. Partner submits a sales report for a period via `POST /api/partner-sales-reports`
     (or via webhook with HMAC signature). Status starts `submitted`.
  2. Admin reviews in `/admin/partner-sales-reports`:
     - `approve` → status `approved`, credit ledger entry created using
       `resolve_off_site_pct(profile)`.
     - `dispute` → status `disputed`, no credit.
     - `revise` → status `submitted` again with admin_note attached.
  3. Approved credits show up alongside on-site referrals in the same payout
     ledger but with `source_type='off_site_sales_report'`.

HMAC webhook (`POST /api/webhooks/partner-sales/{slug}`):
  - Header `X-Birthright-Signature: sha256=<hex>`
  - Signature is `hmac.new(secret, raw_body, sha256).hexdigest()`
  - Per-partner secret stored on `partner_profiles.webhook_secret` and can be
    rotated by the partner via `POST /api/partner-sales-reports/my/webhook/regenerate`.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from auth_utils import get_current_user, require_roles
from models import (
    PartnerSalesReportDecision,
    PartnerSalesReportSubmit,
    gen_id,
    now_iso,
)
from utils.audit import log_action
from utils.rev_share import resolve_off_site_pct

logger = logging.getLogger("birthright.partner_sales")

my_router = APIRouter(prefix="/partner-sales-reports", tags=["partner-sales-reports"])
admin_router = APIRouter(prefix="/admin/partner-sales-reports", tags=["partner-sales-reports-admin"])
webhook_router = APIRouter(prefix="/webhooks/partner-sales", tags=["partner-sales-webhooks"])


# ============ HELPERS ============

VALID_STATUSES = ("submitted", "approved", "disputed", "revised")
TERMINAL_STATUSES = {"approved", "disputed"}


def _make_secret() -> str:
    return secrets.token_hex(32)  # 64-char hex


async def _ensure_webhook_secret(db, profile: dict) -> str:
    """Mint and persist a secret on the profile if missing. Returns the secret."""
    if profile.get("webhook_secret"):
        return profile["webhook_secret"]
    secret = _make_secret()
    await db.partner_profiles.update_one(
        {"id": profile["id"]},
        {"$set": {"webhook_secret": secret, "updated_at": now_iso()}},
    )
    return secret


def _build_report_doc(
    profile: dict,
    data: PartnerSalesReportSubmit,
    *,
    source: str,
    submitted_by: Optional[str],
) -> dict:
    return {
        "id": gen_id(),
        "partner_id": profile["id"],
        "partner_slug": profile["slug"],
        "partner_user_id": profile.get("user_id"),
        "partner_type": profile["partner_type"],
        "period_start": data.period_start,
        "period_end": data.period_end,
        "gross_revenue_usd": float(data.gross_revenue_usd),
        "attributed_orders": int(data.attributed_orders),
        "note": (data.note or "").strip(),
        "source": source,  # 'self_report' | 'webhook'
        "submitted_by": submitted_by,
        "status": "submitted",
        "admin_note": "",
        "reviewed_at": None,
        "reviewed_by": None,
        # Filled on approval:
        "approved_pct": None,
        "approved_pct_source": None,
        "approved_gross_usd": None,
        "approved_payout_usd": None,
        "credit_id": None,
        "created_at": now_iso(),
    }


def _validate_period(data: PartnerSalesReportSubmit) -> None:
    if data.period_end < data.period_start:
        raise HTTPException(status_code=400, detail="period_end must be on or after period_start")


# ============ PARTNER-FACING ============

@my_router.get("/my")
async def my_reports(
    partner_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List all sales reports submitted by any of the caller's partner profiles."""
    from database import db
    query: dict = {"partner_user_id": user["id"]}
    if partner_type:
        query["partner_type"] = partner_type
    rows = await db.partner_sales_reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return rows


@my_router.post("")
async def submit_my_report(
    data: PartnerSalesReportSubmit,
    partner_type: str = Query(..., description="Which of the caller's partner profiles to attribute this to"),
    user: dict = Depends(get_current_user),
):
    from database import db
    _validate_period(data)
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": partner_type, "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"No active {partner_type} partner profile")
    doc = _build_report_doc(profile, data, source="self_report", submitted_by=user["id"])
    await db.partner_sales_reports.insert_one(dict(doc))
    await log_action(
        db, user, "partner_sales_report.submit",
        target_type="partner_sales_report", target_id=doc["id"],
        metadata={"partner_id": profile["id"], "gross": doc["gross_revenue_usd"]},
    )
    doc.pop("_id", None)
    return doc


@my_router.get("/my/webhook")
async def my_webhook_info(
    partner_type: str = Query(...),
    user: dict = Depends(get_current_user),
):
    """Return the partner's webhook URL + current secret (auto-minted if absent)."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": partner_type, "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"No active {partner_type} partner profile")
    secret = await _ensure_webhook_secret(db, profile)
    return {
        "webhook_path": f"/api/webhooks/partner-sales/{profile['slug']}",
        "secret": secret,
        "signature_header": "X-Birthright-Signature",
        "signature_scheme": "sha256=<hex(hmac_sha256(secret, raw_body))>",
        "sample_payload": {
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
            "gross_revenue_usd": 1234.56,
            "attributed_orders": 12,
            "note": "May 2026 — Shopify export",
        },
    }


@my_router.post("/my/webhook/regenerate")
async def regenerate_my_webhook_secret(
    partner_type: str = Query(...),
    user: dict = Depends(get_current_user),
):
    from database import db
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": partner_type, "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"No active {partner_type} partner profile")
    secret = _make_secret()
    await db.partner_profiles.update_one(
        {"id": profile["id"]},
        {"$set": {"webhook_secret": secret, "updated_at": now_iso()}},
    )
    await log_action(
        db, user, "partner_sales_report.webhook_secret.rotate",
        target_type="partner_profile", target_id=profile["id"],
    )
    return {"secret": secret}


# ============ ADMIN ============

@admin_router.get("")
async def admin_list(
    status: Optional[str] = None,
    partner_id: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
        query["status"] = status
    if partner_id:
        query["partner_id"] = partner_id
    rows = await db.partner_sales_reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return rows


async def _approve_report(db, report: dict, profile: dict, data: PartnerSalesReportDecision, admin: dict) -> dict:
    """Compute payout, write a credit ledger row, and stamp the report as approved."""
    gross = float(data.override_gross_usd if data.override_gross_usd is not None else report["gross_revenue_usd"])
    if data.override_pct is not None:
        pct = float(data.override_pct)
        pct_source = "admin_override"
    else:
        off = await resolve_off_site_pct(db, profile)
        pct = float(off["pct"])
        pct_source = off["source"]
    payout = round(gross * pct / 100, 2)

    credit_doc = {
        "id": gen_id(),
        "partner_user_id": report["partner_user_id"],
        "partner_id": report["partner_id"],
        "amount_usd": payout,
        "source_type": "off_site_sales_report",
        "source_id": report["id"],
        "status": "earned",
        "earned_at": now_iso(),
        "paid_at": None,
        "rev_share_pct": pct,
        "pct_source": pct_source,
        "gross_revenue_usd": gross,
        "period_start": report["period_start"],
        "period_end": report["period_end"],
    }
    await db.partner_off_site_credits.insert_one(dict(credit_doc))

    await db.partner_sales_reports.update_one(
        {"id": report["id"]},
        {"$set": {
            "status": "approved",
            "admin_note": (data.admin_note or "").strip(),
            "reviewed_at": now_iso(),
            "reviewed_by": admin["id"],
            "approved_pct": pct,
            "approved_pct_source": pct_source,
            "approved_gross_usd": gross,
            "approved_payout_usd": payout,
            "credit_id": credit_doc["id"],
        }},
    )
    return {
        "approved_pct": pct,
        "approved_pct_source": pct_source,
        "approved_gross_usd": gross,
        "approved_payout_usd": payout,
        "credit_id": credit_doc["id"],
    }


@admin_router.post("/{report_id}/decision")
async def admin_decision(
    report_id: str,
    status: str,
    data: PartnerSalesReportDecision,
    user: dict = Depends(require_roles("admin")),
):
    """`status` must be 'approve' | 'dispute' | 'revise'."""
    from database import db
    if status not in ("approve", "dispute", "revise"):
        raise HTTPException(status_code=400, detail="status must be approve | dispute | revise")
    report = await db.partner_sales_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report["status"] in TERMINAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Report is already {report['status']}")
    profile = await db.partner_profiles.find_one({"id": report["partner_id"]})
    if not profile:
        raise HTTPException(status_code=400, detail="Partner profile not found for this report")

    result: dict = {}
    if status == "approve":
        result = await _approve_report(db, report, profile, data, user)
    elif status == "dispute":
        await db.partner_sales_reports.update_one(
            {"id": report_id},
            {"$set": {
                "status": "disputed",
                "admin_note": (data.admin_note or "").strip(),
                "reviewed_at": now_iso(),
                "reviewed_by": user["id"],
            }},
        )
    else:  # revise
        await db.partner_sales_reports.update_one(
            {"id": report_id},
            {"$set": {
                "status": "revised",
                "admin_note": (data.admin_note or "").strip(),
                "reviewed_at": now_iso(),
                "reviewed_by": user["id"],
            }},
        )

    await log_action(
        db, user, f"partner_sales_report.{status}",
        target_type="partner_sales_report", target_id=report_id,
        metadata={"partner_id": report["partner_id"], **result},
    )
    updated = await db.partner_sales_reports.find_one({"id": report_id}, {"_id": 0})
    return updated


# ============ WEBHOOK ============

def _verify_signature(secret: str, raw_body: bytes, header: Optional[str]) -> bool:
    if not header or not secret:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    # Constant-time comparison
    return hmac.compare_digest(expected.encode(), header.encode())


@webhook_router.post("/{slug}")
async def partner_sales_webhook(slug: str, request: Request):
    """HMAC-signed POST endpoint for partners on platforms that can POST automatically.

    The raw body is verified against `partner_profiles.webhook_secret` using SHA-256.
    On success a `partner_sales_reports` row is created with `source='webhook'`,
    awaiting admin reconciliation."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"slug": slug, "status": "active"}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Partner not found")
    secret = profile.get("webhook_secret")
    if not secret:
        raise HTTPException(status_code=400, detail="Partner has not minted a webhook secret yet")

    raw = await request.body()
    sig = request.headers.get("X-Birthright-Signature") or request.headers.get("x-birthright-signature")
    if not _verify_signature(secret, raw, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        import json
        payload = json.loads(raw or b"{}")
        data = PartnerSalesReportSubmit(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}") from e
    _validate_period(data)

    doc = _build_report_doc(profile, data, source="webhook", submitted_by=None)
    await db.partner_sales_reports.insert_one(dict(doc))
    doc.pop("_id", None)
    return {"received": True, "report_id": doc["id"], "status": doc["status"]}
