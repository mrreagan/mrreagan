"""Gallery — public exhibition + sales for approved Artist partners.

Each Artist's gallery is a curated space (statement, hero, layout choice, accent
color, optional audio/video, collections, etc.) that points to `products` rows
flagged `is_gallery_artwork=True`. At checkout we add a fixed 20% foundation
markup on top of the artist's list price. The buyer sees the math explicitly:

    Artist receives: $400  ·  Foundation receives: $80  ·  Total: $480
    Thank you for generously supporting both the artist and the foundation.

The 20% is enforced server-side in routers/checkout.py via gallery_markup_for().
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user, require_roles, get_current_user_optional
from models import gen_id, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.gallery")
router = APIRouter(prefix="/gallery", tags=["gallery"])

GALLERY_MARKUP_PCT = 0.20  # 20% added at checkout to fund the foundation


LAYOUT_OPTIONS = ("single-wall", "two-column", "salon-hang", "audio-forward")
ACCENT_COLORS = ("flame", "moss", "river", "ochre", "indigo", "graphite")


# ============ Models ============
class GalleryProfileUpdate(BaseModel):
    """The artist's gallery space configuration (per artist, one row)."""
    statement: Optional[str] = Field(default=None, max_length=4000)
    layout: Optional[Literal["single-wall", "two-column", "salon-hang", "audio-forward"]] = None
    accent_color: Optional[Literal["flame", "moss", "river", "ochre", "indigo", "graphite"]] = None
    hero_image_url: Optional[str] = Field(default=None, max_length=600)
    studio_photo_url: Optional[str] = Field(default=None, max_length=600)
    audio_intro_url: Optional[str] = Field(default=None, max_length=600)
    video_reel_url: Optional[str] = Field(default=None, max_length=600)
    open_studio_text: Optional[str] = Field(default=None, max_length=2000)
    performance_schedule: Optional[str] = Field(default=None, max_length=4000)
    commissions_open: Optional[bool] = None
    commission_inquiry_text: Optional[str] = Field(default=None, max_length=2000)
    newsletter_signup_url: Optional[str] = Field(default=None, max_length=600)
    own_gallery_url: Optional[str] = Field(default=None, max_length=600)
    donate_proceeds_to_foundation: Optional[bool] = None  # rare; artist gifts their share
    foundation_absorbs_markup: Optional[bool] = None  # rarer; foundation gifts the 20% back


class ArtworkCreate(BaseModel):
    """Vendor-style create on the products collection w/ gallery extras."""
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    list_price: float = Field(ge=0, description="Same price as on the artist's own gallery — attested by artist.")
    image_url: str = Field(min_length=4, max_length=600)
    image_gallery: list[str] = Field(default_factory=list, max_length=8)
    medium: Optional[str] = Field(default=None, max_length=200)
    dimensions: Optional[str] = Field(default=None, max_length=200)
    year: Optional[int] = Field(default=None, ge=1800, le=2100)
    edition: Optional[str] = Field(default=None, max_length=120, description="e.g. 1/1, 12/100, open edition, AP")
    availability: Literal["available", "sold", "not_for_sale"] = "available"
    collection_slug: Optional[str] = Field(default=None, max_length=120)
    process_notes: Optional[str] = Field(default=None, max_length=4000)
    living_with_text: Optional[str] = Field(default=None, max_length=4000)
    list_price_matches_own_gallery: bool = Field(description="Required attestation: same price as on artist's own gallery.")


class ArtworkUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    list_price: Optional[float] = Field(default=None, ge=0)
    image_url: Optional[str] = Field(default=None, max_length=600)
    image_gallery: Optional[list[str]] = Field(default=None, max_length=8)
    medium: Optional[str] = None
    dimensions: Optional[str] = None
    year: Optional[int] = None
    edition: Optional[str] = None
    availability: Optional[Literal["available", "sold", "not_for_sale"]] = None
    collection_slug: Optional[str] = None
    process_notes: Optional[str] = None
    living_with_text: Optional[str] = None


class CollectionCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120)
    label: str = Field(min_length=2, max_length=200)
    description: Optional[str] = Field(default="", max_length=4000)
    order: int = 0


# ============ Helpers ============
def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:80] or "artwork"


async def _get_artist_profile(db, user_id: str) -> dict:
    profile = await db.partner_profiles.find_one(
        {"user_id": user_id, "partner_type": "artist", "status": "active"},
        {"_id": 0},
    )
    if not profile:
        raise HTTPException(403, "You need an approved Artist partner profile to manage a gallery.")
    return profile


async def _get_gallery_space(db, artist_user_id: str) -> dict:
    """Get or create the gallery space (singleton per artist)."""
    g = await db.gallery_spaces.find_one({"user_id": artist_user_id}, {"_id": 0})
    if g:
        return g
    # Lazy-create on first access
    doc = {
        "id": gen_id(),
        "user_id": artist_user_id,
        "statement": "",
        "layout": "single-wall",
        "accent_color": "flame",
        "hero_image_url": None,
        "studio_photo_url": None,
        "audio_intro_url": None,
        "video_reel_url": None,
        "open_studio_text": None,
        "performance_schedule": None,
        "commissions_open": False,
        "commission_inquiry_text": None,
        "newsletter_signup_url": None,
        "own_gallery_url": None,
        "donate_proceeds_to_foundation": False,
        "foundation_absorbs_markup": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.gallery_spaces.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


def gallery_markup_for(product: dict) -> float:
    """Server-side markup helper used by checkout. Returns a positive USD amount
    to add on top of the artist's list price. Zero if the foundation has been
    asked to absorb the markup as a gift.
    """
    if not product.get("is_gallery_artwork"):
        return 0.0
    if product.get("foundation_absorbs_markup"):
        return 0.0
    return round(float(product.get("price", 0.0)) * GALLERY_MARKUP_PCT, 2)


# ============ Public — gallery landing + per-artist ============
@router.get("/markup-pct")
async def markup_pct():
    """Public — used by frontend to display the foundation markup % consistently."""
    return {"pct": GALLERY_MARKUP_PCT * 100}


@router.get("/artists")
async def list_galleries(
    q: Optional[str] = None,
    limit: int = Query(60, ge=1, le=200),
):
    """Public — list all artists with at least one available artwork."""
    from database import db
    query = {"partner_type": "artist", "status": "active", "public": True}
    if q and len(q.strip()) >= 2:
        rx = re.escape(q.strip())
        query["$or"] = [
            {"display_name": {"$regex": rx, "$options": "i"}},
            {"headline": {"$regex": rx, "$options": "i"}},
            {"bio": {"$regex": rx, "$options": "i"}},
        ]
    profiles = await db.partner_profiles.find(query, {"_id": 0}).sort("approved_at", -1).to_list(limit)
    # Attach available-artwork count + hero image from the gallery_space
    out = []
    for p in profiles:
        space = await db.gallery_spaces.find_one({"user_id": p["user_id"]}, {"_id": 0, "hero_image_url": 1, "statement": 1, "accent_color": 1, "layout": 1})
        count = await db.products.count_documents({
            "is_gallery_artwork": True, "gallery_artist_user_id": p["user_id"],
            "availability": "available", "moderation_status": "active",
        })
        out.append({
            "slug": p["slug"],
            "display_name": p.get("display_name"),
            "headline": p.get("headline"),
            "bio": (p.get("bio") or "")[:240],
            "photo_url": p.get("photo_url"),
            "location": p.get("location"),
            "available_count": count,
            "hero_image_url": (space or {}).get("hero_image_url"),
            "statement": ((space or {}).get("statement") or "")[:240],
            "accent_color": (space or {}).get("accent_color", "flame"),
            "layout": (space or {}).get("layout", "single-wall"),
        })
    return out


@router.get("/{slug}")
async def get_artist_gallery(slug: str):
    """Public — full gallery space + works (grouped by collection)."""
    from database import db
    profile = await db.partner_profiles.find_one(
        {"slug": slug, "partner_type": "artist", "status": "active", "public": True}, {"_id": 0},
    )
    if not profile:
        raise HTTPException(404, "Artist gallery not found")
    space = await _get_gallery_space(db, profile["user_id"])
    works = await db.products.find(
        {"is_gallery_artwork": True, "gallery_artist_user_id": profile["user_id"],
         "moderation_status": "active"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    collections = await db.gallery_collections.find(
        {"user_id": profile["user_id"]}, {"_id": 0},
    ).sort("order", 1).to_list(50)
    return {
        "artist": profile,
        "space": space,
        "works": works,
        "collections": collections,
        "markup_pct": GALLERY_MARKUP_PCT * 100,
    }


# ============ Artist self-management ============
@router.get("/me/space")
async def my_space(user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    return await _get_gallery_space(db, user["id"])


@router.put("/me/space")
async def update_my_space(data: GalleryProfileUpdate, user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    space = await _get_gallery_space(db, user["id"])
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(400, "Nothing to update")
    updates["updated_at"] = now_iso()
    await db.gallery_spaces.update_one({"id": space["id"]}, {"$set": updates})
    return await db.gallery_spaces.find_one({"id": space["id"]}, {"_id": 0})


@router.get("/me/works")
async def my_works(user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    rows = await db.products.find(
        {"gallery_artist_user_id": user["id"], "is_gallery_artwork": True}, {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    return rows


@router.post("/me/works")
async def create_work(data: ArtworkCreate, user: dict = Depends(get_current_user)):
    """Artist publishes a new work. Stored as a product with gallery flags."""
    from database import db
    profile = await _get_artist_profile(db, user["id"])
    if not data.list_price_matches_own_gallery:
        raise HTTPException(
            400,
            "Please confirm your list price matches the price on your own gallery. "
            "(Birthright adds a 20% foundation markup on top at checkout, so undercutting "
            "Birthright would unfairly disadvantage the foundation that supports your work.)",
        )
    slug = _slugify(f"{profile['display_name']}-{data.name}")
    # uniquify
    base = slug
    i = 1
    while await db.products.find_one({"slug": slug}, {"_id": 0, "id": 1}):
        i += 1
        slug = f"{base}-{i}"
    doc = {
        "id": gen_id(),
        "slug": slug,
        "name": data.name.strip(),
        "description": data.description.strip(),
        "price": float(data.list_price),
        "type": "merch",
        "category": "art",
        "image_url": data.image_url,
        "image_gallery": list(data.image_gallery or []),
        "inventory": 1 if data.edition and "/" not in data.edition else (1 if data.availability == "available" else 0),
        # Gallery flags
        "is_gallery_artwork": True,
        "gallery_artist_user_id": user["id"],
        "gallery_artist_slug": profile["slug"],
        "gallery_artist_name": profile.get("display_name"),
        "medium": data.medium,
        "dimensions": data.dimensions,
        "year": data.year,
        "edition": data.edition,
        "availability": data.availability,
        "collection_slug": data.collection_slug,
        "process_notes": data.process_notes,
        "living_with_text": data.living_with_text,
        "list_price_attested": True,
        # Reuse vendor moderation surface — admin can flag works after the fact
        "is_vendor_product": False,
        "moderation_status": "active",
        "moderation_note": None,
        "created_at": now_iso(),
    }
    await db.products.insert_one(dict(doc))
    await log_action(
        db, user, "gallery.work.create",
        target_type="product", target_id=doc["id"],
        metadata={"slug": slug, "list_price": data.list_price},
    )
    doc.pop("_id", None)
    return doc


@router.put("/me/works/{work_id}")
async def update_my_work(work_id: str, data: ArtworkUpdate, user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    work = await db.products.find_one({"id": work_id, "gallery_artist_user_id": user["id"]}, {"_id": 0})
    if not work:
        raise HTTPException(404, "Work not found in your gallery")
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if "list_price" in updates:
        updates["price"] = float(updates.pop("list_price"))
    if not updates:
        raise HTTPException(400, "Nothing to update")
    await db.products.update_one({"id": work_id}, {"$set": updates})
    return await db.products.find_one({"id": work_id}, {"_id": 0})


@router.delete("/me/works/{work_id}")
async def delete_my_work(work_id: str, user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    r = await db.products.delete_one({"id": work_id, "gallery_artist_user_id": user["id"]})
    return {"ok": True, "deleted": bool(r.deleted_count)}


# ============ Collections ============
@router.get("/me/collections")
async def my_collections(user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    rows = await db.gallery_collections.find({"user_id": user["id"]}, {"_id": 0}).sort("order", 1).to_list(50)
    return rows


@router.post("/me/collections")
async def create_collection(data: CollectionCreate, user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    slug = _slugify(data.slug)
    if await db.gallery_collections.find_one({"user_id": user["id"], "slug": slug}, {"_id": 0, "id": 1}):
        raise HTTPException(400, "Collection with this slug already exists")
    doc = {
        "id": gen_id(),
        "user_id": user["id"],
        "slug": slug,
        "label": data.label.strip(),
        "description": (data.description or "").strip(),
        "order": data.order,
        "created_at": now_iso(),
    }
    await db.gallery_collections.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.delete("/me/collections/{cid}")
async def delete_collection(cid: str, user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    await db.gallery_collections.delete_one({"id": cid, "user_id": user["id"]})
    # Detach works from the deleted collection
    await db.products.update_many(
        {"gallery_artist_user_id": user["id"], "collection_slug": cid},
        {"$set": {"collection_slug": None}},
    )
    return {"ok": True}


# ============ Commission inquiries (lightweight contact form) ============
class CommissionInquiry(BaseModel):
    artist_slug: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=10, max_length=4000)


@router.post("/inquiries")
async def submit_inquiry(data: CommissionInquiry, user: Optional[dict] = Depends(get_current_user_optional)):
    from database import db
    artist = await db.partner_profiles.find_one(
        {"slug": data.artist_slug, "partner_type": "artist", "status": "active"}, {"_id": 0},
    )
    if not artist:
        raise HTTPException(404, "Artist not found")
    space = await db.gallery_spaces.find_one({"user_id": artist["user_id"]}, {"_id": 0, "commissions_open": 1})
    if not (space or {}).get("commissions_open"):
        raise HTTPException(400, "This artist isn't accepting commissions right now.")
    doc = {
        "id": gen_id(),
        "artist_user_id": artist["user_id"],
        "artist_slug": artist["slug"],
        "from_name": data.name.strip(),
        "from_email": data.email.strip().lower(),
        "from_user_id": user["id"] if user else None,
        "message": data.message.strip(),
        "status": "open",
        "created_at": now_iso(),
    }
    await db.gallery_inquiries.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.get("/me/inquiries")
async def my_inquiries(user: dict = Depends(get_current_user)):
    from database import db
    await _get_artist_profile(db, user["id"])
    return await db.gallery_inquiries.find({"artist_user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
