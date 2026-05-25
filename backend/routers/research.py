"""Research artifacts + paid promotion — v1.11.0 Step 6.

Research partners publish artifacts (briefs or peer-reviewed papers). Any
published artifact appears on `/research`. Partners can pay to promote a
specific artifact to the top of `/research` for 30 days. Two tiers:

  brief  — $49 / 30 days
  paper  — $149 / 30 days (peer-reviewed, wider distribution rationale)

Admins can:
  - Override an artifact's tier (e.g. comp a journal-grade brief to paper tier)
  - Grant or revoke a promotion window for free
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from auth_utils import get_current_user, require_roles
from models import (
    ResearchArtifactCreate,
    ResearchArtifactUpdate,
    ResearchPromoteCheckout,
    gen_id,
    now_iso,
)
from utils.audit import log_action

logger = logging.getLogger("birthright.research")

TIER_PRICING = {"brief": 49.0, "paper": 149.0}
DEFAULT_PROMOTION_DAYS = 30

public_router = APIRouter(prefix="/research", tags=["research"])
my_router = APIRouter(prefix="/me/research", tags=["research-partner"])
admin_router = APIRouter(prefix="/admin/research", tags=["research-admin"])


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_promoted(artifact: dict) -> bool:
    until = artifact.get("promoted_until")
    if not until:
        return False
    try:
        return datetime.fromisoformat(until) > datetime.now(timezone.utc)
    except Exception:
        return False


async def _require_research_profile(db, user: dict) -> dict:
    profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": "research", "status": "active"}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="No active research partner profile")
    if profile.get("is_sample"):
        raise HTTPException(status_code=400, detail="Sample profiles cannot publish research artifacts")
    return profile


# ============ PUBLIC ============

@public_router.get("/pricing")
async def pricing():
    return {"tiers": TIER_PRICING, "duration_days": DEFAULT_PROMOTION_DAYS}


@public_router.get("")
async def list_artifacts(
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(60, ge=1, le=200),
):
    """Public research feed. Published artifacts only. Promoted first, then newest."""
    from database import db
    import re
    query: dict = {"status": "published"}
    if category:
        query["categories"] = category
    if q and len(q.strip()) >= 2:
        rx = re.escape(q.strip())
        query["$or"] = [
            {"title": {"$regex": rx, "$options": "i"}},
            {"abstract": {"$regex": rx, "$options": "i"}},
            {"authors": {"$regex": rx, "$options": "i"}},
        ]
    rows = await db.research_artifacts.find(query, {"_id": 0}).to_list(limit)
    # Promoted first (by promoted_until desc), then by publication_date desc.
    now = _now_utc_iso()
    promoted, others = [], []
    for r in rows:
        is_promoted = bool(r.get("promoted_until") and r["promoted_until"] > now)
        (promoted if is_promoted else others).append(r)
    promoted.sort(key=lambda r: r.get("promoted_until") or "", reverse=True)
    others.sort(key=lambda r: r.get("publication_date") or "", reverse=True)
    return promoted + others


@public_router.get("/promoted")
async def list_promoted(limit: int = Query(20, ge=1, le=100)):
    """Currently-promoted artifacts only."""
    from database import db
    rows = await db.research_artifacts.find(
        {"status": "published", "promoted_until": {"$gt": _now_utc_iso()}},
        {"_id": 0},
    ).sort("promoted_until", -1).to_list(limit)
    return rows


@public_router.get("/{artifact_id}")
async def get_artifact(artifact_id: str):
    from database import db
    a = await db.research_artifacts.find_one({"id": artifact_id, "status": "published"}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return a


def _cite_apa7(a: dict) -> str:
    """Build an APA 7th-edition reference string. Best-effort given freeform authors field."""
    authors = (a.get("authors") or "").strip()
    year = ""
    if a.get("publication_date"):
        year = a["publication_date"][:4]
    title = (a.get("title") or "").strip().rstrip(".")
    doi = (a.get("doi") or "").strip()
    url = (a.get("full_text_url") or "").strip()
    pub = "Birthright Foundation."
    parts = []
    if authors:
        parts.append(authors + ".")
    if year:
        parts.append(f"({year}).")
    if title:
        parts.append(f"{title}.")
    parts.append(pub)
    if doi:
        parts.append(f"https://doi.org/{doi}" if not doi.lower().startswith("http") else doi)
    elif url:
        parts.append(url)
    return " ".join(parts)


def _cite_bibtex(a: dict) -> str:
    """Build a BibTeX @article (or @misc for briefs) entry."""
    authors = (a.get("authors") or "").strip()
    year = (a.get("publication_date") or "")[:4]
    title = (a.get("title") or "").replace("{", "").replace("}", "")
    doi = (a.get("doi") or "").strip()
    url = (a.get("full_text_url") or "").strip()
    tier = a.get("tier", "brief")
    entry = "article" if tier == "paper" else "misc"
    # citekey: first author surname + year + first word of title
    first_author = authors.split(",")[0].strip().split(" ")[-1].lower() if authors else "anon"
    first_title = (title.split(" ")[0] if title else "untitled").lower()
    key = f"{first_author}{year}{first_title}".replace(".", "").replace("'", "")
    lines = [f"@{entry}{{{key},"]
    if authors:
        lines.append(f"  author = {{{authors}}},")
    if title:
        lines.append(f"  title = {{{title}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    lines.append("  publisher = {Birthright Foundation},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    if url:
        lines.append(f"  url = {{{url}}},")
    lines.append("}")
    return "\n".join(lines)


@public_router.get("/{artifact_id}/cite")
async def cite_artifact(
    artifact_id: str,
    format: str = Query("apa7", regex="^(apa7|bibtex)$"),
):
    """Return a formatted citation string. Increments view counter (best-effort)."""
    from database import db
    a = await db.research_artifacts.find_one({"id": artifact_id, "status": "published"}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")
    citation = _cite_apa7(a) if format == "apa7" else _cite_bibtex(a)
    return {"format": format, "citation": citation, "artifact_id": artifact_id}


# ============ PARTNER-FACING ============

@my_router.get("")
async def my_artifacts(user: dict = Depends(get_current_user)):
    from database import db
    profile = await _require_research_profile(db, user)
    rows = await db.research_artifacts.find(
        {"partner_id": profile["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return rows


@my_router.post("")
async def create_artifact(data: ResearchArtifactCreate, user: dict = Depends(get_current_user)):
    from database import db
    profile = await _require_research_profile(db, user)
    doc = {
        "id": gen_id(),
        "partner_id": profile["id"],
        "partner_slug": profile["slug"],
        "partner_display_name": profile["display_name"],
        "user_id": user["id"],
        **data.model_dump(),
        "promoted_until": None,
        "view_count": 0,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.research_artifacts.insert_one(dict(doc))
    await log_action(
        db, user, "research_artifact.create",
        target_type="research_artifact", target_id=doc["id"],
        metadata={"tier": doc["tier"]},
    )
    doc.pop("_id", None)
    return doc


@my_router.put("/{artifact_id}")
async def update_artifact(
    artifact_id: str,
    data: ResearchArtifactUpdate,
    user: dict = Depends(get_current_user),
):
    from database import db
    profile = await _require_research_profile(db, user)
    artifact = await db.research_artifacts.find_one({"id": artifact_id, "partner_id": profile["id"]})
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    # Only admin can change tier — silently drop tier from partner-side updates
    updates.pop("tier", None)
    updates["updated_at"] = now_iso()
    await db.research_artifacts.update_one({"id": artifact_id}, {"$set": updates})
    out = await db.research_artifacts.find_one({"id": artifact_id}, {"_id": 0})
    return out


@my_router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: str, user: dict = Depends(get_current_user)):
    from database import db
    profile = await _require_research_profile(db, user)
    artifact = await db.research_artifacts.find_one({"id": artifact_id, "partner_id": profile["id"]})
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if _is_promoted(artifact):
        raise HTTPException(status_code=400, detail="Cannot delete a currently-promoted artifact. Wait for the promotion to end.")
    await db.research_artifacts.delete_one({"id": artifact_id})
    return {"deleted": True, "id": artifact_id}


@my_router.post("/{artifact_id}/promote/checkout")
async def promote_checkout(
    artifact_id: str,
    data: ResearchPromoteCheckout,
    request: Request,
    user: dict = Depends(get_current_user),
):
    from database import db
    from routers.checkout import get_stripe
    profile = await _require_research_profile(db, user)
    artifact = await db.research_artifacts.find_one({"id": artifact_id, "partner_id": profile["id"]})
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact.get("status") != "published":
        raise HTTPException(status_code=400, detail="Only published artifacts can be promoted")
    tier = artifact.get("tier", "brief")
    amount = TIER_PRICING.get(tier, TIER_PRICING["brief"])

    success_url = f"{data.origin_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&type=research_promotion"
    cancel_url = f"{data.origin_url}/dashboard/partner/research"
    metadata = {
        "type": "research_promotion",
        "user_id": user["id"],
        "artifact_id": artifact_id,
        "partner_id": profile["id"],
        "tier": tier,
    }
    req = CheckoutSessionRequest(amount=amount, currency="usd", success_url=success_url, cancel_url=cancel_url, metadata=metadata)
    session = await get_stripe(request).create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "id": gen_id(),
        "session_id": session.session_id,
        "user_id": user["id"],
        "type": "research_promotion",
        "amount": amount,
        "currency": "usd",
        "metadata": metadata,
        "artifact_id": artifact_id,
        "partner_id": profile["id"],
        "tier": tier,
        "payment_status": "initiated",
        "status": "open",
        "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id}


async def activate_research_promotion(db, txn: dict) -> None:
    """Stripe webhook — extend or set promoted_until on payment success."""
    artifact_id = txn.get("artifact_id") or txn.get("metadata", {}).get("artifact_id")
    if not artifact_id:
        return
    artifact = await db.research_artifacts.find_one({"id": artifact_id})
    if not artifact:
        return
    now = datetime.now(timezone.utc)
    current = None
    if artifact.get("promoted_until"):
        try:
            current = datetime.fromisoformat(artifact["promoted_until"])
        except Exception:
            current = None
    start = current if (current and current > now) else now
    new_until = (start + timedelta(days=DEFAULT_PROMOTION_DAYS)).isoformat()
    await db.research_artifacts.update_one(
        {"id": artifact_id},
        {"$set": {"promoted_until": new_until, "updated_at": now_iso()}},
    )
    await db.research_promotion_purchases.insert_one({
        "id": gen_id(),
        "artifact_id": artifact_id,
        "partner_id": txn.get("partner_id"),
        "user_id": txn.get("user_id"),
        "session_id": txn["session_id"],
        "amount": float(txn["amount"]),
        "tier": txn.get("tier"),
        "promoted_until": new_until,
        "created_at": now_iso(),
    })


# ============ ADMIN ============

@admin_router.get("")
async def admin_list(
    status: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query: dict = {}
    if status:
        query["status"] = status
    rows = await db.research_artifacts.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return rows


@admin_router.put("/{artifact_id}/tier")
async def admin_set_tier(
    artifact_id: str,
    tier: str = Query(..., regex="^(brief|paper)$"),
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    a = await db.research_artifacts.find_one({"id": artifact_id})
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")
    await db.research_artifacts.update_one(
        {"id": artifact_id}, {"$set": {"tier": tier, "updated_at": now_iso()}}
    )
    await log_action(
        db, user, "research_artifact.tier.set",
        target_type="research_artifact", target_id=artifact_id,
        metadata={"tier": tier},
    )
    return await db.research_artifacts.find_one({"id": artifact_id}, {"_id": 0})


@admin_router.post("/{artifact_id}/promote/grant")
async def admin_grant_promotion(
    artifact_id: str,
    days: int = Query(DEFAULT_PROMOTION_DAYS, ge=1, le=365),
    user: dict = Depends(require_roles("admin")),
):
    """Comp a promotion window (no payment)."""
    from database import db
    a = await db.research_artifacts.find_one({"id": artifact_id})
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")
    until = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    await db.research_artifacts.update_one(
        {"id": artifact_id}, {"$set": {"promoted_until": until, "updated_at": now_iso()}}
    )
    await log_action(
        db, user, "research_artifact.promotion.grant",
        target_type="research_artifact", target_id=artifact_id,
        metadata={"days": days, "until": until},
    )
    return await db.research_artifacts.find_one({"id": artifact_id}, {"_id": 0})


@admin_router.post("/{artifact_id}/promote/revoke")
async def admin_revoke_promotion(
    artifact_id: str,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    a = await db.research_artifacts.find_one({"id": artifact_id})
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")
    await db.research_artifacts.update_one(
        {"id": artifact_id}, {"$set": {"promoted_until": None, "updated_at": now_iso()}}
    )
    await log_action(
        db, user, "research_artifact.promotion.revoke",
        target_type="research_artifact", target_id=artifact_id,
    )
    return await db.research_artifacts.find_one({"id": artifact_id}, {"_id": 0})
