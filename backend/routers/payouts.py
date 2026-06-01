"""Payouts, W9 collection, and payout-method capture — v1.11.0 Step 7.

Partners see a combined ledger of earnings from both on-site referrals
(`referral_payouts`) and off-site sales credits (`partner_off_site_credits`).

W9 form is captured and stored on `partner_w9_forms` (one row per partner_user).
Payout method (Stripe Connect account ID or manual ACH) is stored on
`partner_payout_methods`; ACH account_number is encrypted at rest using Fernet
(key from `PAYOUT_ENCRYPTION_KEY` env var).

Admins can mark credits as paid via `POST /api/admin/payouts/credits/{id}/mark-paid`.

v1.11.0 Step 8 extensions:
- `GET /api/admin/payouts/disbursement-settings` + PUT — admin-set next disbursement date
- `GET /api/me/payouts/next-disbursement` — partner-visible date
- `GET /api/admin/payouts/ready-to-pay[?source=&format=csv|json]` — gated to W9+method on file
- Mark-paid now triggers a partner notification email (best-effort)
"""
from __future__ import annotations

import csv
import io
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from auth_utils import get_current_user, require_roles
from utils.agreement_gate import require_active_agreement_partner
from models import DisbursementSettings, PayoutMarkPaid, PayoutMethodSet, W9Form, gen_id, now_iso
from utils.audit import log_action
from utils.mailer import send_email

logger = logging.getLogger("birthright.payouts")

my_router = APIRouter(prefix="/me/payouts", tags=["payouts"])
admin_router = APIRouter(prefix="/admin/payouts", tags=["payouts-admin"])


def _fernet() -> Fernet:
    key = os.environ.get("PAYOUT_ENCRYPTION_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="PAYOUT_ENCRYPTION_KEY not configured")
    return Fernet(key.encode())


def _encrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return _fernet().encrypt(value.encode()).decode()


def _mask_account(account_number_enc: Optional[str]) -> Optional[str]:
    if not account_number_enc:
        return None
    try:
        plain = _fernet().decrypt(account_number_enc.encode()).decode()
    except Exception:
        return "****"
    return "****" + plain[-4:] if len(plain) >= 4 else "****"


def _redact_method(method: Optional[dict]) -> Optional[dict]:
    if not method:
        return None
    out = {k: v for k, v in method.items() if k not in {"account_number_enc", "_id"}}
    out["account_number_last4"] = _mask_account(method.get("account_number_enc"))
    return out


# ============ PARTNER-FACING ============

@my_router.get("")
async def my_ledger(user: dict = Depends(get_current_user)):
    """Combined earnings ledger across all the partner's profiles."""
    from database import db
    referrals = await db.referral_payouts.find(
        {"partner_user_id": user["id"]}, {"_id": 0}
    ).sort("earned_at", -1).to_list(1000)
    off_site = await db.partner_off_site_credits.find(
        {"partner_user_id": user["id"]}, {"_id": 0}
    ).sort("earned_at", -1).to_list(1000)

    def _to_entry(r: dict, source: str) -> dict:
        return {
            "id": r["id"],
            "source": source,
            "amount_usd": float(r.get("amount_usd", 0)),
            "status": r.get("status", "earned"),
            "earned_at": r.get("earned_at"),
            "paid_at": r.get("paid_at"),
            "rev_share_pct": r.get("rev_share_pct"),
            "gross_revenue_usd": r.get("gross_revenue_usd"),
            "source_type": r.get("source_type"),
            "source_id": r.get("source_id"),
        }

    entries = [_to_entry(r, "on_site_referral") for r in referrals] + [_to_entry(r, "off_site_credit") for r in off_site]
    entries.sort(key=lambda e: e.get("earned_at") or "", reverse=True)

    earned = sum(e["amount_usd"] for e in entries if e["status"] == "earned")
    paid = sum(e["amount_usd"] for e in entries if e["status"] == "paid")

    # Surface upcoming disbursement date if admin has set one
    settings_doc = await db.foundation_settings.find_one(
        {"key": "disbursement_settings"}, {"_id": 0}
    )
    next_disbursement = (settings_doc or {}).get("next_disbursement_date")
    cadence = (settings_doc or {}).get("cadence", "monthly")

    # W9 + method status for the partner's own awareness
    w9_on_file = await db.partner_w9_forms.find_one({"user_id": user["id"]}) is not None
    method_on_file = await db.partner_payout_methods.find_one({"user_id": user["id"]}) is not None

    return {
        "totals": {"earned_unpaid": round(earned, 2), "paid_lifetime": round(paid, 2), "all_time": round(earned + paid, 2)},
        "entries": entries,
        "next_disbursement_date": next_disbursement,
        "cadence": cadence,
        "ready_for_payout": w9_on_file and method_on_file,
        "w9_on_file": w9_on_file,
        "method_on_file": method_on_file,
    }


@my_router.get("/next-disbursement")
async def my_next_disbursement(user: dict = Depends(get_current_user)):
    from database import db
    doc = await db.foundation_settings.find_one(
        {"key": "disbursement_settings"}, {"_id": 0}
    )
    return {
        "next_disbursement_date": (doc or {}).get("next_disbursement_date"),
        "cadence": (doc or {}).get("cadence", "monthly"),
        "notes": (doc or {}).get("notes", ""),
    }


@my_router.get("/w9")
async def get_my_w9(user: dict = Depends(get_current_user)):
    from database import db
    w9 = await db.partner_w9_forms.find_one({"user_id": user["id"]}, {"_id": 0})
    if w9 and w9.get("tin"):
        # Mask TIN for display
        tin = w9["tin"]
        w9["tin_masked"] = "***-**-" + tin[-4:] if len(tin) >= 4 else "***"
        w9.pop("tin", None)
    return w9 or None


@my_router.put("/w9")
async def upsert_my_w9(data: W9Form,
                       user: dict = Depends(get_current_user),
                       _gated: dict = Depends(require_active_agreement_partner)):
    from database import db
    doc = {
        **data.model_dump(),
        "user_id": user["id"],
        "signed_at": now_iso(),
        "updated_at": now_iso(),
    }
    existing = await db.partner_w9_forms.find_one({"user_id": user["id"]})
    if existing:
        await db.partner_w9_forms.update_one({"user_id": user["id"]}, {"$set": doc})
    else:
        doc["id"] = gen_id()
        doc["created_at"] = now_iso()
        await db.partner_w9_forms.insert_one(dict(doc))
    await log_action(db, user, "partner.w9.update", metadata={"classification": data.classification})
    return {"saved": True, "signed_at": doc["signed_at"]}


@my_router.get("/method")
async def get_my_payout_method(user: dict = Depends(get_current_user)):
    from database import db
    m = await db.partner_payout_methods.find_one({"user_id": user["id"]}, {"_id": 0})
    return _redact_method(m)


@my_router.put("/method")
async def set_my_payout_method(data: PayoutMethodSet,
                                user: dict = Depends(get_current_user),
                                _gated: dict = Depends(require_active_agreement_partner)):
    from database import db
    if data.method_type == "stripe_connect":
        if not data.stripe_account_id:
            raise HTTPException(status_code=400, detail="stripe_account_id required for stripe_connect method")
    else:  # manual_ach
        if not all([data.bank_name, data.account_holder_name, data.routing_number, data.account_number]):
            raise HTTPException(status_code=400, detail="All ACH fields required for manual_ach method")

    doc = {
        "user_id": user["id"],
        "method_type": data.method_type,
        "stripe_account_id": data.stripe_account_id if data.method_type == "stripe_connect" else None,
        "bank_name": data.bank_name if data.method_type == "manual_ach" else None,
        "account_holder_name": data.account_holder_name if data.method_type == "manual_ach" else None,
        "routing_number": data.routing_number if data.method_type == "manual_ach" else None,
        "account_number_enc": _encrypt(data.account_number) if data.method_type == "manual_ach" else None,
        "updated_at": now_iso(),
    }
    existing = await db.partner_payout_methods.find_one({"user_id": user["id"]})
    if existing:
        await db.partner_payout_methods.update_one({"user_id": user["id"]}, {"$set": doc})
    else:
        doc["id"] = gen_id()
        doc["created_at"] = now_iso()
        await db.partner_payout_methods.insert_one(dict(doc))
    await log_action(
        db, user, "partner.payout_method.update",
        metadata={"method_type": data.method_type},
    )
    out = await db.partner_payout_methods.find_one({"user_id": user["id"]}, {"_id": 0})
    return _redact_method(out)


# ============ ADMIN ============

@admin_router.get("/credits")
async def admin_credits(
    status: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    on_site = await db.referral_payouts.find(query, {"_id": 0}).sort("earned_at", -1).to_list(1000)
    off_site = await db.partner_off_site_credits.find(query, {"_id": 0}).sort("earned_at", -1).to_list(1000)
    for r in on_site:
        r["source"] = "on_site_referral"
    for r in off_site:
        r["source"] = "off_site_credit"
    return sorted(on_site + off_site, key=lambda r: r.get("earned_at") or "", reverse=True)


@admin_router.post("/credits/{credit_id}/mark-paid")
async def admin_mark_paid(
    credit_id: str,
    data: PayoutMarkPaid,
    source: str,  # 'on_site_referral' | 'off_site_credit'
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    collection = db.referral_payouts if source == "on_site_referral" else db.partner_off_site_credits
    existing = await collection.find_one({"id": credit_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Credit not found")
    if existing.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Credit already paid")
    await collection.update_one(
        {"id": credit_id},
        {"$set": {
            "status": "paid",
            "paid_at": now_iso(),
            "paid_by": user["id"],
            "payout_method": data.method,
            "payout_reference": data.reference,
            "payout_note": (data.note or "").strip(),
        }},
    )
    await log_action(
        db, user, "payout.mark_paid",
        target_type=source, target_id=credit_id,
        metadata={"amount": existing.get("amount_usd"), "reference": data.reference, "method": data.method},
    )

    # Fire-and-forget partner notification email
    try:
        partner_user_id = existing.get("partner_user_id")
        if partner_user_id:
            partner = await db.users.find_one({"id": partner_user_id}, {"_id": 0})
            if partner:
                from utils.email_templates import disbursement_notification
                app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
                subj, html, text = disbursement_notification(
                    first_name=partner.get("first_name", "there"),
                    amount=float(existing.get("amount_usd") or 0),
                    method=data.method or "manual",
                    reference=data.reference or "",
                    note=(data.note or "").strip(),
                    source=source,
                    app_url=app_url,
                )
                await send_email(
                    to=partner["email"], subject=subj, html=html, text=text,
                    template_name="disbursement_notification",
                    metadata={"credit_id": credit_id, "source": source},
                )
    except Exception as e:
        logger.warning(f"disbursement notification email failed: {e}")

    return await collection.find_one({"id": credit_id}, {"_id": 0})


@admin_router.get("/w9/{user_id}")
async def admin_get_w9(user_id: str, user: dict = Depends(require_roles("admin"))):
    """Admin view of a partner's W9 (full TIN visible — audit logged)."""
    from database import db
    w9 = await db.partner_w9_forms.find_one({"user_id": user_id}, {"_id": 0})
    if not w9:
        raise HTTPException(status_code=404, detail="No W9 on file for this user")
    await log_action(
        db, user, "admin.w9.view",
        target_type="partner_w9_form", target_id=w9["id"],
        metadata={"viewed_user_id": user_id},
    )
    return w9


# ============ DISBURSEMENT ORCHESTRATION (v1.11.0 Step 8) ============

@admin_router.get("/disbursement-settings")
async def admin_get_disbursement_settings(user: dict = Depends(require_roles("admin"))):
    from database import db
    doc = await db.foundation_settings.find_one(
        {"key": "disbursement_settings"}, {"_id": 0}
    )
    return {
        "next_disbursement_date": (doc or {}).get("next_disbursement_date"),
        "cadence": (doc or {}).get("cadence", "monthly"),
        "notes": (doc or {}).get("notes", ""),
    }


@admin_router.put("/disbursement-settings")
async def admin_set_disbursement_settings(
    data: DisbursementSettings,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    payload = {
        "next_disbursement_date": data.next_disbursement_date,
        "cadence": data.cadence or "monthly",
        "notes": (data.notes or "").strip(),
        "updated_at": now_iso(),
        "updated_by": user["id"],
    }
    await db.foundation_settings.update_one(
        {"key": "disbursement_settings"},
        {"$set": {"key": "disbursement_settings", **payload}},
        upsert=True,
    )
    await log_action(
        db, user, "admin.disbursement_settings.update",
        metadata=payload,
    )
    return payload


@admin_router.get("/ready-to-pay")
async def admin_ready_to_pay(
    format: str = Query("json", regex="^(json|csv)$"),
    user: dict = Depends(require_roles("admin")),
):
    """Returns earned credits whose partner has BOTH W9 + payout method on file.

    Optionally returns CSV stream for direct disbursement run.
    """
    from database import db

    on_site = await db.referral_payouts.find(
        {"status": "earned"}, {"_id": 0}
    ).sort("earned_at", 1).to_list(5000)
    off_site = await db.partner_off_site_credits.find(
        {"status": "earned"}, {"_id": 0}
    ).sort("earned_at", 1).to_list(5000)
    for r in on_site:
        r["source"] = "on_site_referral"
    for r in off_site:
        r["source"] = "off_site_credit"
    raw = on_site + off_site

    # Determine which partners are ready (W9 + method on file)
    partner_ids = list({r.get("partner_user_id") for r in raw if r.get("partner_user_id")})
    w9_set = set()
    method_set = set()
    if partner_ids:
        async for w in db.partner_w9_forms.find({"user_id": {"$in": partner_ids}}, {"user_id": 1}):
            w9_set.add(w["user_id"])
        async for m in db.partner_payout_methods.find({"user_id": {"$in": partner_ids}}, {"user_id": 1, "method_type": 1}):
            method_set.add(m["user_id"])
    ready_ids = w9_set & method_set

    users = {}
    if partner_ids:
        async for u in db.users.find(
            {"id": {"$in": partner_ids}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "email": 1},
        ):
            users[u["id"]] = u
    methods = {}
    if partner_ids:
        async for m in db.partner_payout_methods.find(
            {"user_id": {"$in": partner_ids}}, {"_id": 0}
        ):
            methods[m["user_id"]] = m.get("method_type") or "manual_ach"

    rows = []
    for r in raw:
        pid = r.get("partner_user_id")
        u = users.get(pid, {})
        is_ready = pid in ready_ids
        rows.append({
            "credit_id": r["id"],
            "source": r["source"],
            "partner_user_id": pid,
            "partner_name": f"{u.get('first_name','')} {u.get('last_name','')}".strip(),
            "partner_email": u.get("email", ""),
            "amount_usd": float(r.get("amount_usd") or 0),
            "earned_at": r.get("earned_at"),
            "rev_share_pct": r.get("rev_share_pct"),
            "source_type": r.get("source_type"),
            "source_id": r.get("source_id"),
            "method_type": methods.get(pid, ""),
            "w9_on_file": pid in w9_set,
            "method_on_file": pid in method_set,
            "ready_to_pay": is_ready,
        })

    if format == "csv":
        ready_rows = [r for r in rows if r["ready_to_pay"]]
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=[
                "credit_id", "source", "partner_user_id", "partner_name",
                "partner_email", "amount_usd", "earned_at", "rev_share_pct",
                "source_type", "source_id", "method_type",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        for r in ready_rows:
            writer.writerow(r)
        await log_action(
            db, user, "admin.ready_to_pay.export_csv",
            metadata={"row_count": len(ready_rows), "total_usd": round(sum(r["amount_usd"] for r in ready_rows), 2)},
        )
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="birthright-disbursement-ready.csv"'},
        )

    ready = [r for r in rows if r["ready_to_pay"]]
    blocked = [r for r in rows if not r["ready_to_pay"]]
    return {
        "ready_total_usd": round(sum(r["amount_usd"] for r in ready), 2),
        "blocked_total_usd": round(sum(r["amount_usd"] for r in blocked), 2),
        "ready_count": len(ready),
        "blocked_count": len(blocked),
        "ready": ready,
        "blocked": blocked,
    }
