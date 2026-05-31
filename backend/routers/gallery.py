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
    """Public — full gallery space + works (grouped by collection). If the artist
    has an active featured slot for today, the curated mini-gallery from that slot
    overrides the regular gallery_space fields and the featured_work_ids are
    highlighted at the top of the works grid."""
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

    # Check for an active featured slot — if present, merge into the returned view
    today = _today_iso_date()
    featured = await db.featured_artist_slots.find_one(
        {"artist_slug": slug, "status": {"$in": ["accepted", "active"]},
         "starts_at": {"$lte": today}, "ends_at": {"$gte": today}},
        {"_id": 0},
    )
    nomination_quotes: list = []
    if featured:
        # Hydrate the slot with nomination narratives
        nom_ids = featured.get("nominations_referenced") or []
        if nom_ids:
            async for n in db.featured_nominations.find(
                {"id": {"$in": nom_ids}}, {"_id": 0, "reason": 1, "nominator_name": 1, "created_at": 1},
            ):
                nomination_quotes.append(n)
        # Merge slot curation over the base space (slot wins where set)
        for k in _FEATURED_SHARED_FIELDS:
            if featured.get(k) is not None:
                space[k] = featured[k]
        # Signature image becomes the hero for the month
        if featured.get("signature_image_url"):
            space["hero_image_url"] = featured["signature_image_url"]
        # Reorder works so featured_work_ids come first
        ids = featured.get("featured_work_ids") or []
        if ids:
            id_set = set(ids)
            head = [w for w in works if w["id"] in id_set]
            head.sort(key=lambda w: ids.index(w["id"]))
            tail = [w for w in works if w["id"] not in id_set]
            works = head + tail

    return {
        "artist": profile,
        "space": space,
        "works": works,
        "collections": collections,
        "markup_pct": GALLERY_MARKUP_PCT * 100,
        "featured": featured,
        "nomination_quotes": nomination_quotes,
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


# ============ Featured Artists ============
# Quarterly rotation with two on-ramps: editorial picks (board curates) and
# community nominations (any signed-in user can nominate, board confirms final
# from a top-N shortlist). All slots have explicit start/end dates so the public
# always knows who's featured *right now* and *when next*.

# ============ Featured Artists ============
# Monthly rotation with two on-ramps (editorial + community nominations).
# Lifecycle: proposed (admin scheduled, artist hasn't accepted yet)
#         → accepted (artist agreed + curated their presentation)
#         → active   (accepted + today is within [starts_at, ends_at])
#         → past     (accepted + ends_at < today)
#         → declined (artist said no)
#         → cancelled (admin pulled the slot)
# Only `accepted` and `active` slots appear publicly. Each featured slot carries
# the artist's curated `signature_image_url` (for the scrolling pill on Gallery
# landing) + a `featured_work_ids[]` list (which pieces they want highlighted)
# + a short `presentation_note`.

FEATURED_MIN_PER_MONTH = 3
FEATURED_MAX_PER_MONTH = 5
FEATURED_COOLING_OFF_MONTHS = 3
NEW_ACCOUNT_DAYS = 30
NEW_ACCOUNT_WEIGHT = 0.25
NOMINATION_HALF_LIFE_DAYS = 365  # 12 months
SCHEDULE_HORIZON_DAYS = 60  # public schedule shows next 60 days only


def _today_iso_date() -> str:
    return now_iso()[:10]


def _month_label(d: str) -> str:
    """Turn '2026-08-14' into '2026-08' for nomination grouping."""
    return d[:7]


def _next_month_label(month: str) -> str:
    """'2026-12' → '2027-01'."""
    y, m = month.split("-")
    yy, mm = int(y), int(m)
    if mm == 12:
        return f"{yy + 1}-01"
    return f"{yy}-{mm + 1:02d}"


def _human_month_label(d: str) -> str:
    """Turn '2026-08-14' into 'August 2026' (default for `period_label`)."""
    from datetime import datetime
    try:
        return datetime.fromisoformat(d).strftime("%B %Y")
    except ValueError:
        return d


def _decay_factor(created_at: str, today: Optional[str] = None) -> float:
    """Time decay for a nomination's contribution to an artist's queue rank.
    Half-life of NOMINATION_HALF_LIFE_DAYS. Recent love is fresh, old love
    quietly fades but never vanishes entirely.
    """
    from datetime import datetime, timezone
    try:
        ts = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return 1.0
    now = datetime.now(timezone.utc) if today is None else datetime.fromisoformat(today + "T00:00:00+00:00")
    days_old = max(0, (now - ts).days)
    return 0.5 ** (days_old / NOMINATION_HALF_LIFE_DAYS)


async def _compute_nomination_weight(db, user: dict) -> tuple[float, list[str]]:
    """Returns (weight, flags). 0.25× for brand-new accounts with no other
    engagement; 1.0× otherwise. Nominator never sees their own weight."""
    from datetime import datetime, timezone
    flags: list[str] = []
    weight = 1.0
    created_raw = user.get("created_at")
    if created_raw:
        try:
            created = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created).days
        except (ValueError, AttributeError):
            age_days = 999
    else:
        age_days = 999
    if age_days < NEW_ACCOUNT_DAYS:
        engaged = False
        for collection, query in [
            ("orders", {"user_id": user["id"]}),
            ("community_posts", {"author_id": user["id"]}),
            ("community_members", {"user_id": user["id"]}),
            ("partner_applications", {"user_id": user["id"]}),
        ]:
            if await db[collection].find_one(query, {"_id": 0, "id": 1}):
                engaged = True
                break
        if not engaged:
            weight = NEW_ACCOUNT_WEIGHT
            flags.append(f"new_account_under_{NEW_ACCOUNT_DAYS}d_no_engagement")
    return weight, flags


class FeaturedSlotCreate(BaseModel):
    artist_slug: str = Field(min_length=2, max_length=120)
    starts_at: str = Field(description="ISO date, e.g. 2026-06-01")
    ends_at: str = Field(description="ISO date, e.g. 2026-06-30")
    period_label: str = Field(min_length=2, max_length=60, description="Human label, e.g. 'June 2026'")
    source: Literal["foundation", "editorial", "community"] = "editorial"
    editorial_reason: Optional[str] = Field(default=None, max_length=2000,
                                             description="Required when source is 'foundation' or 'editorial'; published on the artist card.")
    nominations_referenced: Optional[list[str]] = Field(default=None,
        description="When source=community, the nomination IDs being honored.")


class FeaturedNomination(BaseModel):
    artist_slug: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=10, max_length=150,
                         description="Up to 150 characters. Why should this artist be featured?")
    allow_artist_contact: bool = Field(default=True,
        description="If True, the artist may reach back through Birthright to thank or connect.")


class ReachBackMessage(BaseModel):
    message: str = Field(min_length=10, max_length=4000)


class NominationEmailPref(BaseModel):
    preference: Literal["immediate", "weekly", "none"] = "immediate"


class FeaturedCuration(BaseModel):
    """Artist-controlled presentation fields for their featured slot. Mirrors
    `GalleryProfileUpdate` so each featured month is a self-contained mini-gallery
    the artist can curate independently of their regular space (and optionally
    copy back into their regular gallery if they like the result).
    """
    # Signature elements — what shows in the scrolling pill on Gallery landing
    signature_image_url: Optional[str] = Field(default=None, max_length=600)
    signature_statement: Optional[str] = Field(default=None, max_length=280,
        description="Short tagline (≤280 chars) for the scrolling pill + featured-month banner.")

    # Long-form (mirrors gallery_space.statement)
    statement: Optional[str] = Field(default=None, max_length=4000)
    layout: Optional[Literal["single-wall", "two-column", "salon-hang", "audio-forward"]] = None
    accent_color: Optional[Literal["flame", "moss", "river", "ochre", "indigo", "graphite"]] = None
    studio_photo_url: Optional[str] = Field(default=None, max_length=600)
    audio_intro_url: Optional[str] = Field(default=None, max_length=600)
    video_reel_url: Optional[str] = Field(default=None, max_length=600)
    open_studio_text: Optional[str] = Field(default=None, max_length=2000)
    performance_schedule: Optional[str] = Field(default=None, max_length=4000)
    commissions_open: Optional[bool] = None
    commission_inquiry_text: Optional[str] = Field(default=None, max_length=2000)

    # Curation specific to the featured slot
    featured_work_ids: Optional[list[str]] = Field(default=None, max_length=8,
        description="Which works (product IDs) to highlight. Defaults to the artist's 3 most recent.")
    presentation_note: Optional[str] = Field(default=None, max_length=500,
        description="A short note from the artist for visitors during their featured month.")


def _slot_sort_key(slot: dict) -> tuple:
    """Foundation slots first (top billing), then by start date, then alphabetical."""
    foundation_first = 0 if slot.get("source") == "foundation" else 1
    return (foundation_first, slot.get("starts_at", ""), (slot.get("artist_display_name") or "").lower())


@router.get("/featured")
async def list_featured(include_upcoming: bool = True, include_past: bool = False, limit: int = Query(20, ge=1, le=100)):
    """Public — current accepted featured artists + upcoming accepted slots + (optionally) past.

    Slots in `proposed` / `declined` / `cancelled` are hidden from the public.
    """
    from database import db
    today = _today_iso_date()
    visible_statuses = {"$in": ["accepted", "active"]}
    current = await db.featured_artist_slots.find(
        {"starts_at": {"$lte": today}, "ends_at": {"$gte": today}, "status": visible_statuses},
        {"_id": 0},
    ).sort("starts_at", 1).to_list(limit)
    upcoming = []
    if include_upcoming:
        upcoming = await db.featured_artist_slots.find(
            {"starts_at": {"$gt": today}, "status": visible_statuses},
            {"_id": 0},
        ).sort("starts_at", 1).limit(limit).to_list(limit)
    past = []
    if include_past:
        past = await db.featured_artist_slots.find(
            {"ends_at": {"$lt": today}, "status": visible_statuses},
            {"_id": 0},
        ).sort("ends_at", -1).limit(limit).to_list(limit)
    # Hydrate with artist display fields + the nomination reasons being honored
    slugs = list({s["artist_slug"] for s in current + upcoming + past})
    profiles = {}
    if slugs:
        async for p in db.partner_profiles.find(
            {"slug": {"$in": slugs}, "partner_type": "artist"},
            {"_id": 0, "slug": 1, "display_name": 1, "headline": 1, "photo_url": 1, "location": 1},
        ):
            profiles[p["slug"]] = p

    async def _hydrate(slot):
        prof = profiles.get(slot["artist_slug"]) or {}
        # Look up the nomination narratives referenced (community-sourced slots)
        nom_quotes = []
        nom_ids = slot.get("nominations_referenced") or []
        if nom_ids:
            async for n in db.featured_nominations.find(
                {"id": {"$in": nom_ids}}, {"_id": 0, "reason": 1, "nominator_name": 1},
            ):
                nom_quotes.append({"reason": n["reason"], "nominator_name": n.get("nominator_name")})
        return {
            **slot,
            "display_name": prof.get("display_name"),
            "headline": prof.get("headline"),
            "photo_url": prof.get("photo_url"),
            "location": prof.get("location"),
            "nomination_quotes": nom_quotes,
        }
    return {
        "current": sorted([await _hydrate(s) for s in current], key=_slot_sort_key),
        "upcoming": sorted([await _hydrate(s) for s in upcoming], key=_slot_sort_key),
        "past": [await _hydrate(s) for s in past] if include_past else [],
        "today": today,
        "min_per_month": FEATURED_MIN_PER_MONTH,
        "max_per_month": FEATURED_MAX_PER_MONTH,
    }


@router.get("/featured/by-artist/{slug}")
async def featured_history_for_artist(slug: str):
    """Public — list a single artist's accepted/active featured slots.
    Used by the per-artist Gallery page to render the FEATURED pill + nomination quotes."""
    from database import db
    today = _today_iso_date()
    visible_statuses = {"$in": ["accepted", "active"]}
    slots = await db.featured_artist_slots.find(
        {"artist_slug": slug, "status": visible_statuses}, {"_id": 0},
    ).sort("starts_at", -1).to_list(50)
    current = next((s for s in slots if s["starts_at"] <= today <= s["ends_at"]), None)
    # Hydrate current with nomination quotes for the "what people are saying" panel
    if current and current.get("nominations_referenced"):
        quotes = []
        async for n in db.featured_nominations.find(
            {"id": {"$in": current["nominations_referenced"]}},
            {"_id": 0, "reason": 1, "nominator_name": 1, "created_at": 1},
        ):
            quotes.append(n)
        current["nomination_quotes"] = quotes
    return {
        "current": current,
        "upcoming": [s for s in slots if s["starts_at"] > today],
        "past": [s for s in slots if s["ends_at"] < today],
        "today": today,
    }


@router.post("/featured/nominate")
async def nominate_artist(data: FeaturedNomination, user: dict = Depends(get_current_user)):
    """Nominate an artist for featuring overall (no calendar period).

    Each user may nominate each artist once. If you nominate the same artist
    again, your reason is refreshed and `created_at` resets — so your love
    counts as fresh in the decay calculation.

    Defends: no self-nomination, new-account weighting (silent), only the
    nominator and admins see who voted for whom. Artist gets an immediate
    email (or batched, per their preference) so they can reach back.
    """
    from database import db
    artist = await db.partner_profiles.find_one(
        {"slug": data.artist_slug, "partner_type": "artist", "status": "active"},
        {"_id": 0, "slug": 1, "user_id": 1, "display_name": 1},
    )
    if not artist:
        raise HTTPException(404, "Artist not found")
    if artist["user_id"] == user["id"]:
        raise HTTPException(400, "Artists cannot nominate themselves for featuring.")
    weight, flags = await _compute_nomination_weight(db, user)
    nominator_email = (user.get("email") or "").lower()
    nominator_name = f"{user.get('first_name','')} {user.get('last_name','')}".strip() or nominator_email or "anon"
    now = now_iso()
    # Upsert per (artist, nominator) — keeps it one-per-user-per-artist
    existing = await db.featured_nominations.find_one(
        {"artist_slug": data.artist_slug, "nominator_user_id": user["id"]},
        {"_id": 0, "id": 1},
    )
    if existing:
        await db.featured_nominations.update_one(
            {"id": existing["id"]},
            {"$set": {
                "reason": data.reason.strip(),
                "weight": weight,
                "trust_flags": flags,
                "allow_artist_contact": data.allow_artist_contact,
                "nominator_email": nominator_email,
                "nominator_name": nominator_name,
                "refreshed_at": now,
                "created_at": now,  # decay resets to "fresh"
            }},
        )
        doc = await db.featured_nominations.find_one({"id": existing["id"]}, {"_id": 0})
        action = "refreshed"
    else:
        doc = {
            "id": gen_id(),
            "artist_slug": data.artist_slug,
            "artist_user_id": artist["user_id"],
            "nominator_user_id": user["id"],
            "nominator_name": nominator_name,
            "nominator_email": nominator_email,
            "reason": data.reason.strip(),
            "weight": weight,
            "trust_flags": flags,
            "allow_artist_contact": data.allow_artist_contact,
            "artist_acknowledged_at": None,
            "created_at": now,
        }
        await db.featured_nominations.insert_one(dict(doc))
        action = "created"

    # Fire-and-forget nomination notification email
    try:
        space = await db.gallery_spaces.find_one(
            {"user_id": artist["user_id"]},
            {"_id": 0, "nomination_email_preference": 1},
        ) or {}
        pref = space.get("nomination_email_preference") or "immediate"
        if pref == "immediate":
            artist_user = await db.users.find_one(
                {"id": artist["user_id"]}, {"_id": 0, "email": 1, "first_name": 1},
            )
            if artist_user and artist_user.get("email"):
                from utils.mailer import send_email
                app_url = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
                inbox_url = f"{app_url}/gallery/me/featured#nominations"
                html = (
                    f"<div style=\"font-family:Georgia,serif;color:#1A2424;max-width:560px;line-height:1.6\">"
                    f"<h2 style=\"font-weight:400\">Hi {artist_user.get('first_name') or 'friend'},</h2>"
                    f"<p>Someone moved by your practice just nominated you for Birthright's Featured Artist program.</p>"
                    f"<blockquote style=\"border-left:3px solid #C9A961;padding-left:12px;color:#5C6B6B;"
                    f"font-style:italic;margin:16px 0\">{data.reason.strip()}</blockquote>"
                    f"<p>It's from <strong>{nominator_name}</strong>"
                    f"{' — they agreed to be contacted if you want to reach back to thank them.' if data.allow_artist_contact else ' (they preferred to remain quiet).'}</p>"
                    f"<p><a href=\"{inbox_url}\" style=\"display:inline-block;background:#9E3C3C;"
                    f"color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px\">See your nominations</a></p>"
                    f"<p style=\"color:#5C6B6B;font-size:12px;margin-top:24px\">You can switch this to a weekly digest or turn it off in your Gallery space settings.</p>"
                    f"</div>"
                )
                await send_email(
                    to=artist_user["email"],
                    subject="A nomination for your featuring",
                    html=html,
                    text=f"You were nominated as a Featured Artist. They wrote: \"{data.reason.strip()}\"\nSee it: {inbox_url}",
                    template_name="artist_nomination_received",
                    metadata={"nomination_id": doc["id"], "artist_slug": data.artist_slug},
                )
    except Exception as ex:
        logger.warning("nomination email failed: %s", ex)

    public = {k: v for k, v in doc.items() if k not in ("weight", "trust_flags", "nominator_email")}
    public["action"] = action
    return public


@router.get("/me/nominations-received")
async def artist_nominations_received(user: dict = Depends(get_current_user)):
    """Artist-only inbox: nominations received with reasons + nominator name +
    (if consented) nominator email so the artist can reach back through
    Birthright's reach-back endpoint."""
    from database import db
    await _get_artist_profile(db, user["id"])
    rows = await db.featured_nominations.find(
        {"artist_user_id": user["id"]}, {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    out = []
    today = _today_iso_date()
    for n in rows:
        contactable = n.get("allow_artist_contact", True)
        out.append({
            "id": n["id"],
            "reason": n["reason"],
            "nominator_name": n.get("nominator_name"),
            "nominator_email": n.get("nominator_email") if contactable else None,
            "allow_artist_contact": contactable,
            "created_at": n.get("created_at"),
            "refreshed_at": n.get("refreshed_at"),
            "decay_factor": round(_decay_factor(n.get("created_at", today), today), 3),
            "acknowledged_at": n.get("artist_acknowledged_at"),
        })
    return out


@router.post("/me/nominations/{nomination_id}/reach-back")
async def reach_back_to_nominator(nomination_id: str, data: ReachBackMessage, user: dict = Depends(get_current_user)):
    """Artist sends a private thank-you / connection message to the nominator
    through Birthright's mailer (we never expose the nominator's email
    directly; instead we relay). Records the outreach so the artist sees
    history and we have an audit trail.
    """
    from database import db
    await _get_artist_profile(db, user["id"])
    nom = await db.featured_nominations.find_one(
        {"id": nomination_id, "artist_user_id": user["id"]}, {"_id": 0},
    )
    if not nom:
        raise HTTPException(404, "Nomination not found")
    if not nom.get("allow_artist_contact", True):
        raise HTTPException(400, "This nominator opted out of being contacted.")
    nominator = await db.users.find_one(
        {"id": nom["nominator_user_id"]}, {"_id": 0, "email": 1, "first_name": 1},
    )
    if not nominator or not nominator.get("email"):
        raise HTTPException(404, "Nominator email not on file")
    artist_space = await db.gallery_spaces.find_one(
        {"user_id": user["id"]}, {"_id": 0},
    ) or {}
    artist_profile = await db.partner_profiles.find_one(
        {"user_id": user["id"], "partner_type": "artist"}, {"_id": 0, "slug": 1, "display_name": 1},
    ) or {}
    try:
        from utils.mailer import send_email
        app_url = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
        gallery_url = f"{app_url}/gallery/{artist_profile.get('slug', '')}"
        html = (
            f"<div style=\"font-family:Georgia,serif;color:#1A2424;max-width:560px;line-height:1.6\">"
            f"<h2 style=\"font-weight:400\">A note from {artist_profile.get('display_name', 'the artist')}</h2>"
            f"<p>You nominated this artist for Birthright's Featured Artist program. They wanted to reach back:</p>"
            f"<blockquote style=\"border-left:3px solid #C9A961;padding-left:12px;color:#5C6B6B;"
            f"font-style:italic;margin:16px 0\">{data.message.strip()}</blockquote>"
            f"<p><a href=\"{gallery_url}\" style=\"display:inline-block;background:#9E3C3C;"
            f"color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px\">Visit {artist_profile.get('display_name', 'their')} gallery</a></p>"
            f"</div>"
        )
        await send_email(
            to=nominator["email"],
            subject=f"A note from {artist_profile.get('display_name', 'a Birthright artist')}",
            html=html, text=data.message.strip(),
            reply_to=None,  # we keep the artist's email private; replies route to support
            template_name="artist_reach_back",
            metadata={"nomination_id": nomination_id, "artist_slug": artist_profile.get("slug")},
        )
    except Exception as ex:
        logger.exception("reach-back email failed: %s", ex)
        raise HTTPException(502, "Couldn't deliver the message. Please try again.") from ex

    outreach = {
        "id": gen_id(),
        "nomination_id": nomination_id,
        "artist_user_id": user["id"],
        "nominator_user_id": nom["nominator_user_id"],
        "message": data.message.strip(),
        "created_at": now_iso(),
    }
    await db.artist_outreach.insert_one(dict(outreach))
    await db.featured_nominations.update_one(
        {"id": nomination_id}, {"$set": {"artist_acknowledged_at": now_iso()}},
    )
    outreach.pop("_id", None)
    return outreach


@router.put("/me/nomination-email-preference")
async def set_nomination_email_pref(data: NominationEmailPref, user: dict = Depends(get_current_user)):
    """Artist sets how they want to be notified of new nominations."""
    from database import db
    await _get_artist_profile(db, user["id"])
    space = await _get_gallery_space(db, user["id"])
    await db.gallery_spaces.update_one(
        {"id": space["id"]},
        {"$set": {"nomination_email_preference": data.preference, "updated_at": now_iso()}},
    )
    return {"preference": data.preference}


@router.get("/featured/nominations")
async def my_nominations(user: dict = Depends(get_current_user), limit: int = Query(50, ge=1, le=200)):
    """List the current user's own nominations (across periods)."""
    from database import db
    rows = await db.featured_nominations.find(
        {"nominator_user_id": user["id"]}, {"_id": 0},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return rows


# ============ Admin — featured slot management ============
@router.get("/admin/featured/shortlist")
async def featured_shortlist(period: Optional[str] = None, user: dict = Depends(require_roles("admin"))):
    """Weighted shortlist of nominees for a target month. Sorted by weighted
    score (raw count × per-nomination weight, including roll-forward residue).

    Admin-only diagnostics included: trust flags, recent reasons, account-age
    signals, cooling-off eligibility per artist.
    """
    from database import db
    today = _today_iso_date()
    target_period = period or _month_label(today)
    pipeline = [
        {"$match": {"period_target": target_period}},
        {"$group": {
            "_id": "$artist_slug",
            "raw_count": {"$sum": 1},
            "weighted_score": {"$sum": {"$ifNull": ["$weight", 1.0]}},
            "reasons": {"$push": {
                "id": "$id", "reason": "$reason", "nominator": "$nominator_name",
                "weight": "$weight", "trust_flags": "$trust_flags",
                "created_at": "$created_at", "rolled_forward_from": "$rolled_forward_from",
            }},
            "first_nominated_at": {"$min": "$created_at"},
            "flag_count": {"$sum": {"$size": {"$ifNull": ["$trust_flags", []]}}},
        }},
        {"$sort": {"weighted_score": -1, "first_nominated_at": 1}},
    ]
    rows = await db.featured_nominations.aggregate(pipeline).to_list(200)
    out = []
    for r in rows:
        prof = await db.partner_profiles.find_one(
            {"slug": r["_id"], "partner_type": "artist"},
            {"_id": 0, "slug": 1, "display_name": 1, "headline": 1, "photo_url": 1, "user_id": 1},
        ) or {}
        # Cooling-off check: was this artist featured in the last 3 months?
        last_featured = await db.featured_artist_slots.find_one(
            {"artist_slug": r["_id"], "status": {"$in": ["accepted", "active"]},
             "ends_at": {"$lt": _today_iso_date()}},
            {"_id": 0, "ends_at": 1}, sort=[("ends_at", -1)],
        )
        cooling_off_until = None
        if last_featured:
            try:
                from datetime import datetime, timezone, timedelta
                ends = datetime.fromisoformat(last_featured["ends_at"])
                cooling = ends + timedelta(days=30 * FEATURED_COOLING_OFF_MONTHS)
                cooling_off_until = cooling.date().isoformat()
            except (ValueError, TypeError):
                cooling_off_until = None
        eligible = (cooling_off_until is None) or (cooling_off_until <= target_period + "-01")
        out.append({
            "artist_slug": r["_id"],
            "display_name": prof.get("display_name"),
            "headline": prof.get("headline"),
            "photo_url": prof.get("photo_url"),
            "raw_count": r["raw_count"],
            "weighted_score": round(r["weighted_score"], 2),
            "reasons": r["reasons"][:10],
            "first_nominated_at": r["first_nominated_at"],
            "flag_count": r["flag_count"],
            "cooling_off_until": cooling_off_until,
            "eligible_for_period": eligible,
        })
    return {
        "period": target_period,
        "shortlist": out,
        "today": today,
        "min_per_month": FEATURED_MIN_PER_MONTH,
        "max_per_month": FEATURED_MAX_PER_MONTH,
        "cooling_off_months": FEATURED_COOLING_OFF_MONTHS,
    }


@router.post("/admin/featured")
async def schedule_featured_slot(data: FeaturedSlotCreate, user: dict = Depends(require_roles("admin"))):
    """Schedule an artist for a featured month. Slot starts in `proposed` state;
    the artist must accept it (and curate their presentation) before it's visible
    to the public.

    - `editorial` source → admin reason required, published on the artist card.
    - `community` source → nomination IDs referenced; their narratives show in
      the "what people are saying" panel on the artist's featured page.

    Sends an invitation email to the artist with a link to accept + curate.
    """
    from database import db
    if data.source in ("foundation", "editorial") and not (data.editorial_reason or "").strip():
        raise HTTPException(400, f"{data.source.title()} picks require a published reason so the audience knows why.")
    if data.starts_at >= data.ends_at:
        raise HTTPException(400, "starts_at must be before ends_at")
    artist = await db.partner_profiles.find_one(
        {"slug": data.artist_slug, "partner_type": "artist", "status": "active"},
        {"_id": 0, "slug": 1, "user_id": 1, "display_name": 1},
    )
    if not artist:
        raise HTTPException(404, "Artist not found")
    # Overlap check
    overlap = await db.featured_artist_slots.find_one({
        "artist_slug": data.artist_slug,
        "status": {"$nin": ["cancelled", "declined"]},
        "starts_at": {"$lte": data.ends_at},
        "ends_at": {"$gte": data.starts_at},
    }, {"_id": 0, "id": 1})
    if overlap:
        raise HTTPException(400, f"Artist already has an overlapping featured slot ({overlap['id']}).")

    # Cooling-off: was this artist featured in the previous COOLING_OFF_MONTHS?
    from datetime import datetime, timedelta
    try:
        new_start = datetime.fromisoformat(data.starts_at).date()
        cool_threshold = new_start - timedelta(days=30 * FEATURED_COOLING_OFF_MONTHS)
        recent_feature = await db.featured_artist_slots.find_one(
            {"artist_slug": data.artist_slug,
             "status": {"$in": ["accepted", "active"]},
             "ends_at": {"$gte": cool_threshold.isoformat(), "$lt": data.starts_at}},
            {"_id": 0, "ends_at": 1, "period_label": 1},
        )
        if recent_feature:
            raise HTTPException(
                400,
                f"Cooling-off: this artist was featured during {recent_feature.get('period_label')} "
                f"(ends {recent_feature['ends_at']}). Wait until {(datetime.fromisoformat(recent_feature['ends_at']).date() + timedelta(days=30 * FEATURED_COOLING_OFF_MONTHS)).isoformat()} "
                f"so others get a turn first.",
            )
    except (ValueError, TypeError):
        pass
    # Cap: max accepted/proposed slots per month
    month = _month_label(data.starts_at)
    active_count = await db.featured_artist_slots.count_documents({
        "starts_at": {"$regex": f"^{month}"},
        "status": {"$in": ["accepted", "active", "proposed"]},
    })
    if active_count >= FEATURED_MAX_PER_MONTH:
        raise HTTPException(400, f"Month {month} already has {FEATURED_MAX_PER_MONTH} featured slots scheduled. Cap is {FEATURED_MAX_PER_MONTH}/month.")
    # Foundation-source cap: 1 per month, top-billed
    if data.source == "foundation":
        foundation_count = await db.featured_artist_slots.count_documents({
            "starts_at": {"$regex": f"^{month}"},
            "source": "foundation",
            "status": {"$in": ["accepted", "active", "proposed"]},
        })
        if foundation_count >= 1:
            raise HTTPException(400, f"Month {month} already has a Foundation-nominated artist. Only one foundation slot per month.")

    doc = {
        "id": gen_id(),
        "artist_user_id": artist["user_id"],
        "artist_slug": artist["slug"],
        "artist_display_name": artist.get("display_name"),
        "starts_at": data.starts_at,
        "ends_at": data.ends_at,
        "period_label": data.period_label.strip(),
        "source": data.source,
        "editorial_reason": (data.editorial_reason or "").strip() or None,
        "nominations_referenced": data.nominations_referenced or [],
        "status": "proposed",
        # Artist-curated presentation (filled in on accept)
        "signature_image_url": None,
        "featured_work_ids": [],
        "presentation_note": None,
        "responded_at": None,
        "created_by": user["id"],
        "created_at": now_iso(),
    }
    await db.featured_artist_slots.insert_one(dict(doc))
    await log_action(
        db, user, f"gallery.featured.{data.source}",
        target_type="featured_slot", target_id=doc["id"],
        metadata={"artist_slug": artist["slug"], "period": data.period_label,
                  "starts_at": data.starts_at, "ends_at": data.ends_at},
    )
    # Fire-and-forget invitation email
    try:
        artist_user = await db.users.find_one({"id": artist["user_id"]}, {"_id": 0, "email": 1, "first_name": 1})
        if artist_user and artist_user.get("email"):
            from utils.mailer import send_email
            app_url = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
            accept_url = f"{app_url}/gallery/me/featured/{doc['id']}"
            html = _featured_invite_html(
                artist_name=artist.get("display_name") or artist_user.get("first_name") or "Friend",
                period_label=data.period_label,
                starts_at=data.starts_at,
                ends_at=data.ends_at,
                source=data.source,
                reason=doc["editorial_reason"],
                accept_url=accept_url,
            )
            await send_email(
                to=artist_user["email"],
                subject=f"You've been invited to be a Birthright Featured Artist — {data.period_label}",
                html=html,
                text=f"You've been invited to be a Birthright Featured Artist for {data.period_label}.\nAccept and curate your presentation here: {accept_url}",
                template_name="featured_artist_invite",
                metadata={"slot_id": doc["id"], "artist_slug": artist["slug"]},
            )
    except Exception as ex:
        logger.warning("Featured invite email failed: %s", ex)

    doc.pop("_id", None)
    return doc


def _featured_invite_html(artist_name: str, period_label: str, starts_at: str, ends_at: str,
                          source: str, reason: Optional[str], accept_url: str) -> str:
    src_blurb = (
        "Our editorial team chose to feature your practice." if source == "editorial"
        else "Your community nominated you — what they wrote about your work moved us."
    )
    reason_block = ""
    if reason:
        reason_block = (
            f"<blockquote style=\"border-left:3px solid #C9A961;padding-left:12px;color:#5C6B6B;"
            f"font-style:italic;margin:16px 0\">{reason}</blockquote>"
        )
    return (
        f"<div style=\"font-family:Georgia,serif;color:#1A2424;max-width:560px;line-height:1.6\">"
        f"<h2 style=\"font-weight:400\">Hi {artist_name},</h2>"
        f"<p>We'd love to feature you in Birthright's Gallery for <strong>{period_label}</strong> "
        f"({starts_at} → {ends_at}).</p>"
        f"<p>{src_blurb}</p>"
        f"{reason_block}"
        f"<p>This is your room, so it's up to you. Open the link below to accept and curate how you'd like to be presented — "
        f"signature image, featured works, a short note for visitors. You can also decline if the timing isn't right.</p>"
        f"<p><a href=\"{accept_url}\" style=\"display:inline-block;background:#9E3C3C;color:#fff;"
        f"padding:10px 20px;text-decoration:none;border-radius:4px\">Accept + curate your feature</a></p>"
        f"<p style=\"color:#5C6B6B;font-size:13px;margin-top:32px\">Thank you for the work you make. — Birthright</p>"
        f"</div>"
    )


@router.get("/me/featured")
async def my_featured_slots(user: dict = Depends(get_current_user)):
    """List the signed-in artist's own featured slots (all statuses)."""
    from database import db
    await _get_artist_profile(db, user["id"])
    slots = await db.featured_artist_slots.find(
        {"artist_user_id": user["id"]}, {"_id": 0},
    ).sort("starts_at", -1).to_list(50)
    # Hydrate proposed/community slots with nomination quotes (so the artist
    # sees what was said about them when accepting)
    from database import db as _db
    for slot in slots:
        nom_ids = slot.get("nominations_referenced") or []
        if nom_ids:
            quotes = []
            async for n in _db.featured_nominations.find(
                {"id": {"$in": nom_ids}}, {"_id": 0, "reason": 1, "nominator_name": 1, "created_at": 1},
            ):
                quotes.append(n)
            slot["nomination_quotes"] = quotes
    return slots


def _resolve_active_status(slot: dict) -> str:
    today = _today_iso_date()
    if slot["status"] != "accepted":
        return slot["status"]
    if slot["starts_at"] <= today <= slot["ends_at"]:
        return "active"
    return "accepted"


@router.post("/me/featured/{slot_id}/accept")
async def accept_featured_slot(slot_id: str, data: FeaturedCuration, user: dict = Depends(get_current_user)):
    """Artist accepts a proposed slot and submits their curated presentation.

    Any field left None in the request is filled from the artist's current
    `gallery_space` (suggested defaults). This way the artist can accept with
    zero customization and still get a sensible mini-gallery.
    """
    from database import db
    slot = await db.featured_artist_slots.find_one(
        {"id": slot_id, "artist_user_id": user["id"]}, {"_id": 0},
    )
    if not slot:
        raise HTTPException(404, "Featured slot not found")
    if slot["status"] not in ("proposed", "accepted", "active"):
        raise HTTPException(400, f"Cannot accept a slot that's already {slot['status']}")
    space = await _get_gallery_space(db, user["id"])
    submitted = data.model_dump(exclude_none=True)

    # Default `featured_work_ids` to the 3 most recent if not provided
    work_ids = submitted.get("featured_work_ids")
    if work_ids is None:
        recent = await db.products.find(
            {"gallery_artist_user_id": user["id"], "is_gallery_artwork": True,
             "moderation_status": "active", "availability": "available"},
            {"_id": 0, "id": 1},
        ).sort("created_at", -1).limit(3).to_list(3)
        work_ids = [r["id"] for r in recent]

    # Merge: submitted > current slot value > gallery_space default
    def pick(key: str, space_key: Optional[str] = None):
        if key in submitted:
            return submitted[key]
        if slot.get(key) is not None:
            return slot[key]
        return space.get(space_key or key)

    updates = {
        "status": "accepted",
        "responded_at": now_iso(),
        "signature_image_url": pick("signature_image_url", "hero_image_url"),
        "signature_statement": pick("signature_statement"),
        "statement": pick("statement"),
        "layout": pick("layout") or "single-wall",
        "accent_color": pick("accent_color") or "flame",
        "studio_photo_url": pick("studio_photo_url"),
        "audio_intro_url": pick("audio_intro_url"),
        "video_reel_url": pick("video_reel_url"),
        "open_studio_text": pick("open_studio_text"),
        "performance_schedule": pick("performance_schedule"),
        "commissions_open": pick("commissions_open"),
        "commission_inquiry_text": pick("commission_inquiry_text"),
        "featured_work_ids": work_ids[:8],
        "presentation_note": pick("presentation_note"),
    }
    await db.featured_artist_slots.update_one({"id": slot_id}, {"$set": updates})
    await log_action(
        db, user, "gallery.featured.accept",
        target_type="featured_slot", target_id=slot_id,
        metadata={"period_label": slot.get("period_label")},
    )
    return await db.featured_artist_slots.find_one({"id": slot_id}, {"_id": 0})


@router.post("/me/featured/{slot_id}/decline")
async def decline_featured_slot(slot_id: str, user: dict = Depends(get_current_user)):
    """Artist declines a proposed slot."""
    from database import db
    slot = await db.featured_artist_slots.find_one(
        {"id": slot_id, "artist_user_id": user["id"]}, {"_id": 0},
    )
    if not slot:
        raise HTTPException(404, "Featured slot not found")
    if slot["status"] != "proposed":
        raise HTTPException(400, f"Cannot decline a slot that's already {slot['status']}")
    await db.featured_artist_slots.update_one(
        {"id": slot_id}, {"$set": {"status": "declined", "responded_at": now_iso()}},
    )
    await log_action(
        db, user, "gallery.featured.decline",
        target_type="featured_slot", target_id=slot_id,
    )
    return {"ok": True}


@router.put("/me/featured/{slot_id}/curation")
async def update_my_curation(slot_id: str, data: FeaturedCuration, user: dict = Depends(get_current_user)):
    """Artist edits their featured presentation after accepting (any field, any time)."""
    from database import db
    slot = await db.featured_artist_slots.find_one(
        {"id": slot_id, "artist_user_id": user["id"]}, {"_id": 0},
    )
    if not slot:
        raise HTTPException(404, "Featured slot not found")
    if slot["status"] not in ("proposed", "accepted", "active"):
        raise HTTPException(400, f"Can only edit curation on proposed/accepted/active slots (status: {slot['status']})")
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if "featured_work_ids" in updates:
        updates["featured_work_ids"] = updates["featured_work_ids"][:8]
    if not updates:
        raise HTTPException(400, "Nothing to update")
    updates["updated_at"] = now_iso()
    await db.featured_artist_slots.update_one({"id": slot_id}, {"$set": updates})
    return await db.featured_artist_slots.find_one({"id": slot_id}, {"_id": 0})


# Fields shared between gallery_space and a featured slot (used by copy endpoints)
_FEATURED_SHARED_FIELDS = (
    "statement", "layout", "accent_color", "studio_photo_url", "audio_intro_url",
    "video_reel_url", "open_studio_text", "performance_schedule",
    "commissions_open", "commission_inquiry_text",
)


@router.post("/me/featured/{slot_id}/copy-to-gallery")
async def copy_curation_to_gallery(slot_id: str, user: dict = Depends(get_current_user)):
    """Promote this featured month's curated presentation to the artist's regular
    gallery space. Use after a featured month if you want the curated look to stick.
    """
    from database import db
    slot = await db.featured_artist_slots.find_one(
        {"id": slot_id, "artist_user_id": user["id"]}, {"_id": 0},
    )
    if not slot:
        raise HTTPException(404, "Featured slot not found")
    space = await _get_gallery_space(db, user["id"])
    updates = {k: slot.get(k) for k in _FEATURED_SHARED_FIELDS if slot.get(k) is not None}
    # Signature image on the slot becomes the gallery's hero image
    if slot.get("signature_image_url"):
        updates["hero_image_url"] = slot["signature_image_url"]
    if not updates:
        raise HTTPException(400, "Nothing on this featured slot to copy yet.")
    updates["updated_at"] = now_iso()
    await db.gallery_spaces.update_one({"id": space["id"]}, {"$set": updates})
    await log_action(
        db, user, "gallery.featured.copy_to_gallery",
        target_type="featured_slot", target_id=slot_id,
        metadata={"fields": list(updates.keys())},
    )
    return await db.gallery_spaces.find_one({"id": space["id"]}, {"_id": 0})


@router.post("/me/featured/{slot_id}/copy-from-gallery")
async def copy_curation_from_gallery(slot_id: str, user: dict = Depends(get_current_user)):
    """Reset this featured slot's curation back to the artist's current regular
    gallery defaults. Useful if the artist wants to start curation over."""
    from database import db
    slot = await db.featured_artist_slots.find_one(
        {"id": slot_id, "artist_user_id": user["id"]}, {"_id": 0},
    )
    if not slot:
        raise HTTPException(404, "Featured slot not found")
    if slot["status"] not in ("proposed", "accepted", "active"):
        raise HTTPException(400, f"Cannot reset curation on a slot that's {slot['status']}")
    space = await _get_gallery_space(db, user["id"])
    updates = {k: space.get(k) for k in _FEATURED_SHARED_FIELDS if space.get(k) is not None}
    if space.get("hero_image_url"):
        updates["signature_image_url"] = space["hero_image_url"]
    updates["updated_at"] = now_iso()
    await db.featured_artist_slots.update_one({"id": slot_id}, {"$set": updates})
    return await db.featured_artist_slots.find_one({"id": slot_id}, {"_id": 0})


@router.delete("/admin/featured/{slot_id}")
async def cancel_featured_slot(slot_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    slot = await db.featured_artist_slots.find_one({"id": slot_id}, {"_id": 0})
    if not slot:
        raise HTTPException(404, "Slot not found")
    await db.featured_artist_slots.update_one(
        {"id": slot_id}, {"$set": {"status": "cancelled", "cancelled_at": now_iso(), "cancelled_by": user["id"]}},
    )
    await log_action(
        db, user, "gallery.featured.cancel",
        target_type="featured_slot", target_id=slot_id,
        metadata={"artist_slug": slot.get("artist_slug")},
    )
    return {"ok": True}


@router.get("/admin/featured")
async def admin_list_all_slots(user: dict = Depends(require_roles("admin")), limit: int = Query(100, ge=1, le=500)):
    """Admin — every featured slot ever scheduled (current/upcoming/past/cancelled)."""
    from database import db
    rows = await db.featured_artist_slots.find({}, {"_id": 0}).sort("starts_at", -1).to_list(limit)
    return rows


@router.post("/admin/featured/roll-forward")
async def roll_forward_unfeatured_nominations(user: dict = Depends(require_roles("admin"))):
    """End-of-month action: nominations for the just-closed month whose artists
    weren't selected get carried forward to next month at 50% weight. Should be
    run once after the board finalizes the slate for month N.

    Idempotent: a roll-forward record's `rolled_forward_from` field prevents
    double-rolling.
    """
    from database import db
    today = _today_iso_date()
    current_month = _month_label(today)
    # The PREVIOUS month is the one we're closing
    prev_month_dt = datetime.fromisoformat(today + "T00:00:00").date()
    from datetime import timedelta
    # First day of current month minus 1 → last day of prev month
    last_day_prev = (prev_month_dt.replace(day=1) - timedelta(days=1)).isoformat()
    prev_month = _month_label(last_day_prev)
    next_month = _next_month_label(current_month)

    # Artists who were featured this month (and so shouldn't roll forward)
    featured_slugs: set[str] = set()
    async for s in db.featured_artist_slots.find(
        {"starts_at": {"$regex": f"^{current_month}"}, "status": {"$in": ["accepted", "active"]}},
        {"_id": 0, "artist_slug": 1},
    ):
        featured_slugs.add(s["artist_slug"])

    rolled = 0
    skipped = 0
    async for nom in db.featured_nominations.find(
        {"period_target": prev_month, "rolled_forward_from": None}, {"_id": 0},
    ):
        if nom["artist_slug"] in featured_slugs:
            continue  # Don't roll featured artists' nominations forward
        # Already rolled? skip
        already = await db.featured_nominations.find_one(
            {"rolled_forward_from": nom["id"]}, {"_id": 0, "id": 1},
        )
        if already:
            skipped += 1
            continue
        new_weight = round((nom.get("weight", 1.0) or 1.0) * ROLL_FORWARD_WEIGHT, 3)
        await db.featured_nominations.insert_one({
            "id": gen_id(),
            "artist_slug": nom["artist_slug"],
            "nominator_user_id": nom["nominator_user_id"],
            "nominator_name": nom["nominator_name"],
            "reason": nom["reason"],
            "period_target": next_month,
            "weight": new_weight,
            "trust_flags": (nom.get("trust_flags") or []) + ["rolled_forward"],
            "rolled_forward_from": nom["id"],
            "created_at": now_iso(),
        })
        rolled += 1
    await log_action(
        db, user, "gallery.featured.roll_forward",
        target_type="period", target_id=prev_month,
        metadata={"rolled": rolled, "skipped": skipped, "to_period": next_month},
    )
    return {"rolled": rolled, "skipped": skipped, "from_period": prev_month, "to_period": next_month}


# ============ Public pipeline visibility ============
@router.get("/featured/pipeline")
async def featured_pipeline():
    """Public-facing 3-month outlook for featured artists. Designed to be both
    artist-friendly and community-friendly.

    Returns:
      current_month    — full reveal (artist + signature image + statement + works)
      next_month       — locked slate (artist name + signature_statement only,
                         no detailed counts; curating in private)
      nominations_open — month after next: how many artists nominated total,
                         but NO per-artist counts (anti-bandwagon)
      how_it_works     — the rules (cooling-off, weighting, source disclosure)
    """
    from database import db
    today = _today_iso_date()
    current_month = _month_label(today)
    next_month = _next_month_label(current_month)
    after_next = _next_month_label(next_month)

    current_slots = await db.featured_artist_slots.find(
        {"starts_at": {"$regex": f"^{current_month}"},
         "status": {"$in": ["accepted", "active"]}},
        {"_id": 0},
    ).sort("starts_at", 1).to_list(10)

    # Hydrate current with display fields
    slugs_current = list({s["artist_slug"] for s in current_slots})
    profiles_current: dict[str, dict] = {}
    if slugs_current:
        async for p in db.partner_profiles.find(
            {"slug": {"$in": slugs_current}, "partner_type": "artist"},
            {"_id": 0, "slug": 1, "display_name": 1, "headline": 1, "photo_url": 1, "location": 1},
        ):
            profiles_current[p["slug"]] = p
    for s in current_slots:
        p = profiles_current.get(s["artist_slug"]) or {}
        s["display_name"] = p.get("display_name")
        s["headline"] = p.get("headline")
        s["photo_url"] = p.get("photo_url")
        s["location"] = p.get("location")
    current_slots = sorted(current_slots, key=_slot_sort_key)

    # Next month: only artist names + signature_statement (curating in private)
    next_slots_raw = await db.featured_artist_slots.find(
        {"starts_at": {"$regex": f"^{next_month}"},
         "status": {"$in": ["accepted", "active", "proposed"]}},
        {"_id": 0},
    ).sort("starts_at", 1).to_list(10)
    slugs_next = list({s["artist_slug"] for s in next_slots_raw})
    profiles_next: dict[str, dict] = {}
    if slugs_next:
        async for p in db.partner_profiles.find(
            {"slug": {"$in": slugs_next}, "partner_type": "artist"},
            {"_id": 0, "slug": 1, "display_name": 1, "photo_url": 1, "location": 1},
        ):
            profiles_next[p["slug"]] = p
    next_slots = []
    for s in next_slots_raw:
        p = profiles_next.get(s["artist_slug"]) or {}
        next_slots.append({
            "artist_slug": s["artist_slug"],
            "display_name": p.get("display_name"),
            "photo_url": p.get("photo_url"),
            "location": p.get("location"),
            "period_label": s.get("period_label"),
            "source": s.get("source"),
            "signature_statement": s.get("signature_statement") if s["status"] == "accepted" else None,
            "signature_image_url": s.get("signature_image_url") if s["status"] == "accepted" else None,
            "preparation_status": "accepted" if s["status"] == "accepted" else "preparing",
            "starts_at": s.get("starts_at"),
            "artist_display_name": p.get("display_name"),
        })
    next_slots = sorted(next_slots, key=_slot_sort_key)

    # Nominations open: aggregate count only, no per-artist horse race
    nominations_open_total = await db.featured_nominations.count_documents({
        "period_target": after_next,
    })
    distinct_artists = await db.featured_nominations.distinct(
        "artist_slug", {"period_target": after_next},
    )

    return {
        "today": today,
        "current_month": {
            "period_label": _human_month_label(today),
            "slots": current_slots,
            "count": len(current_slots),
        },
        "next_month": {
            "period_key": next_month,
            "period_label": _human_month_label(next_month + "-01"),
            "slots": next_slots,
            "count": len(next_slots),
            "min_per_month": FEATURED_MIN_PER_MONTH,
            "max_per_month": FEATURED_MAX_PER_MONTH,
            "explainer": "Curating in private. The full presentation goes live on the 1st.",
        },
        "nominations_open": {
            "period_key": after_next,
            "period_label": _human_month_label(after_next + "-01"),
            "total_nominations": nominations_open_total,
            "distinct_artists_nominated": len(distinct_artists),
            "explainer": "Specific counts are hidden during the nomination window so the process isn't a horse race. Nominate the artists whose practice has moved you.",
        },
        "how_it_works": {
            "cooling_off_months": FEATURED_COOLING_OFF_MONTHS,
            "min_per_month": FEATURED_MIN_PER_MONTH,
            "max_per_month": FEATURED_MAX_PER_MONTH,
            "roll_forward_weight": ROLL_FORWARD_WEIGHT,
            "process": "Anyone signed-in can nominate. At the end of each month, the board picks the next month's 3-5 features from the highest-weighted shortlist. Featured artists then have ~30 days to prepare. After a feature, an artist cools off for 3 months so everyone gets a turn.",
        },
    }


# A small import block for datetime to keep grouped at top of helpers
from datetime import datetime  # noqa: E402
