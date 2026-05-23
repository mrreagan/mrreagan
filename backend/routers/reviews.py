"""Universal review/rating system.

Every transactional offering — workshops, products, vendor services — can be reviewed
by users who actually purchased it (verified_purchase=True) and by anyone else, with
a clear visual distinction between the two. Reviews are cross-searchable so a shopper
can see all reviews of similar items (same subject_category) at a glance.

This router supersedes the old workshop-only reviews path in routers/community.py.
The legacy POST/GET /reviews endpoints there remain to avoid breaking the existing
WorkshopHub frontend during rollout; the legacy endpoints internally write into the
new polymorphic schema.

Endpoints:
    POST   /reviews                       — create or update one user's review on a subject
    GET    /reviews?subject_type&subject_id            — list reviews on one subject
    GET    /reviews/search?subject_category&min_rating&q  — cross-site review search
    GET    /reviews/aggregate?subject_type&subject_id  — count + avg rating
    POST   /reviews/{id}/report           — any user can flag for ombudsman
    POST   /reviews/{id}/moderate         — admin/ombudsman hide/restore
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user, require_roles
from models import ReviewCreate, ReviewReport, ReviewModerate, gen_id, now_iso

logger = logging.getLogger("birthright.reviews")
router = APIRouter(prefix="/reviews", tags=["reviews"])


# ============ HELPERS ============

async def _resolve_subject(db, subject_type: str, subject_id: str) -> dict:
    """Verify the subject exists and return its enrichment fields (category, partner_id)."""
    if subject_type == "workshop":
        doc = await db.workshops.find_one({"id": subject_id}, {"_id": 0, "title": 1, "slug": 1, "facilitator_id": 1})
        if not doc:
            raise HTTPException(status_code=404, detail="Workshop not found")
        return {"subject_category": "workshop", "partner_id": doc.get("facilitator_id"), "subject_label": doc.get("title")}
    if subject_type == "product":
        doc = await db.products.find_one({"id": subject_id}, {"_id": 0, "name": 1, "category": 1, "vendor_id": 1})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"subject_category": doc.get("category", "general"), "partner_id": doc.get("vendor_id"), "subject_label": doc.get("name")}
    if subject_type == "service":
        doc = await db.services.find_one({"id": subject_id}, {"_id": 0, "name": 1, "category": 1, "vendor_id": 1}) if hasattr(db, "services") else None
        if not doc:
            raise HTTPException(status_code=404, detail="Service not found")
        return {"subject_category": doc.get("category", "general"), "partner_id": doc.get("vendor_id"), "subject_label": doc.get("name")}
    raise HTTPException(status_code=400, detail=f"Unknown subject_type: {subject_type}")


async def _has_purchased(db, user_id: str, subject_type: str, subject_id: str) -> bool:
    if subject_type == "workshop":
        reg = await db.registrations.find_one(
            {"workshop_id": subject_id, "user_id": user_id, "payment_status": "paid"}
        )
        return bool(reg)
    if subject_type == "product":
        order = await db.orders.find_one(
            {"user_id": user_id, "status": "paid", "items.product_id": subject_id}
        )
        return bool(order)
    return False


def _anonymize(doc: dict) -> dict:
    if doc.get("anonymous"):
        doc["user_name"] = "Anonymous"
        doc["user_id"] = None
    return doc


# ============ ENDPOINTS ============

@router.post("")
async def create_review(data: ReviewCreate, user: dict = Depends(get_current_user)):
    from database import db
    # Back-compat: workshop_id → subject_type/subject_id
    subject_type = data.subject_type
    subject_id = data.subject_id
    if not subject_type and data.workshop_id:
        subject_type = "workshop"
        subject_id = data.workshop_id
    if not subject_type or not subject_id:
        raise HTTPException(status_code=400, detail="subject_type and subject_id required (or workshop_id)")

    info = await _resolve_subject(db, subject_type, subject_id)
    verified = await _has_purchased(db, user["id"], subject_type, subject_id)
    # Workshops require purchase to review; products allow any logged-in user but flag verified.
    if subject_type == "workshop" and not verified and user["role"] not in ("admin", "facilitator"):
        raise HTTPException(status_code=403, detail="Only registered participants can review this workshop")

    existing = await db.reviews.find_one({
        "subject_type": subject_type, "subject_id": subject_id, "user_id": user["id"],
    })
    if existing:
        await db.reviews.update_one(
            {"id": existing["id"]},
            {"$set": {
                "rating": data.rating,
                "review_text": data.review_text,
                "anonymous": data.anonymous,
                "verified_purchase": verified,
                "updated_at": now_iso(),
            }},
        )
        updated = await db.reviews.find_one({"id": existing["id"]}, {"_id": 0})
        return _anonymize(updated)

    review = {
        "id": gen_id(),
        "subject_type": subject_type,
        "subject_id": subject_id,
        "subject_category": info["subject_category"],
        "partner_id": info["partner_id"],
        "workshop_id": subject_id if subject_type == "workshop" else None,  # back-compat read
        "user_id": user["id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "rating": data.rating,
        "review_text": data.review_text,
        "anonymous": data.anonymous,
        "verified_purchase": verified,
        "moderated": False,
        "moderation_reason": None,
        "reported_count": 0,
        "created_at": now_iso(),
    }
    await db.reviews.insert_one(review)
    review.pop("_id", None)
    return _anonymize(review)


@router.get("")
async def list_reviews(
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
    workshop_id: Optional[str] = None,  # back-compat alias
    include_moderated: bool = False,
):
    from database import db
    if workshop_id and not subject_id:
        subject_type = "workshop"
        subject_id = workshop_id
    if not subject_type or not subject_id:
        raise HTTPException(status_code=400, detail="subject_type & subject_id (or workshop_id) required")
    query: dict = {"subject_type": subject_type, "subject_id": subject_id}
    if not include_moderated:
        query["moderated"] = {"$ne": True}
    reviews = await db.reviews.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return [_anonymize(r) for r in reviews]


@router.get("/search")
async def search_reviews(
    subject_category: Optional[str] = None,
    subject_type: Optional[str] = None,
    min_rating: int = Query(0, ge=0, le=5),
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """Cross-subject review search. Useful for shoppers comparing reviews across vendors."""
    from database import db
    query: dict = {"moderated": {"$ne": True}}
    if subject_category:
        query["subject_category"] = subject_category
    if subject_type:
        query["subject_type"] = subject_type
    if min_rating:
        query["rating"] = {"$gte": min_rating}
    if q and len(q) >= 2:
        query["review_text"] = {"$regex": q, "$options": "i"}
    reviews = await db.reviews.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    # enrich with subject label so the UI can show "Review of: <product/workshop name>"
    enriched = []
    for r in reviews:
        info = None
        try:
            info = await _resolve_subject(db, r["subject_type"], r["subject_id"])
        except HTTPException:
            pass  # subject deleted; keep review but no label
        r["subject_label"] = info["subject_label"] if info else "(deleted)"
        enriched.append(_anonymize(r))
    return enriched


@router.get("/aggregate")
async def aggregate(
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
    workshop_id: Optional[str] = None,
):
    from database import db
    if workshop_id and not subject_id:
        subject_type = "workshop"
        subject_id = workshop_id
    if not subject_type or not subject_id:
        raise HTTPException(status_code=400, detail="subject_type & subject_id (or workshop_id) required")
    pipeline = [
        {"$match": {"subject_type": subject_type, "subject_id": subject_id, "moderated": {"$ne": True}}},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "avg": {"$avg": "$rating"},
            "verified_count": {"$sum": {"$cond": ["$verified_purchase", 1, 0]}},
        }},
    ]
    cursor = db.reviews.aggregate(pipeline)
    result = await cursor.to_list(1)
    if not result:
        return {"count": 0, "avg": 0.0, "verified_count": 0}
    r = result[0]
    return {"count": r["count"], "avg": round(r["avg"], 2), "verified_count": r["verified_count"]}


@router.post("/{review_id}/report")
async def report_review(
    review_id: str,
    data: ReviewReport,
    user: dict = Depends(get_current_user),
):
    """Any signed-in user can flag a review for ombudsman attention."""
    from database import db
    r = await db.reviews.find_one({"id": review_id})
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.reviews.update_one(
        {"id": review_id},
        {"$inc": {"reported_count": 1}, "$push": {
            "reports": {
                "reporter_id": user["id"],
                "reason": data.reason.strip(),
                "reported_at": now_iso(),
            }
        }},
    )
    return {"success": True}


@router.post("/{review_id}/moderate")
async def moderate_review(
    review_id: str,
    data: ReviewModerate,
    user: dict = Depends(require_roles("admin", "ombudsman")),
):
    from database import db
    r = await db.reviews.find_one({"id": review_id})
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.reviews.update_one(
        {"id": review_id},
        {"$set": {
            "moderated": bool(data.moderated),
            "moderation_reason": (data.reason or "").strip() or None,
            "moderated_by": user["id"],
            "moderated_at": now_iso(),
        }},
    )
    return {"success": True}
