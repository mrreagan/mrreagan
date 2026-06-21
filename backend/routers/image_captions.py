"""Admin endpoints for managing image captions across collections.

Captions are surfaced to the AI help assistant via `utils/help_context.py` so
that visitor questions about photos ("what's in James Reagan's lap?", "what
does the founder collection patch look like?") can be answered confidently
from authored human descriptions.

Only collections whose images are visitor-facing live here:
  - governing_members (the /lead bios)
  - partner_profiles (the /partner directory)
  - products (the /equip catalog)
  - research_artifacts (the /research detail pages)

Adding a new collection? Add it to ALLOWED_COLLECTIONS + extend the GET
mapper to project the right name/image fields.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth_utils import require_roles
from models import now_iso

router = APIRouter(prefix="/admin/image-captions", tags=["admin"])

ALLOWED_COLLECTIONS = {
    "governing_members": {
        "label": "Leadership (/lead)",
        "name_field": "name",
        "image_field": "image_url",
        "subtitle_field": "title",
    },
    "partner_profiles": {
        "label": "Partners (/partner)",
        "name_field": "display_name",
        "image_field": "avatar_url",
        "subtitle_field": "partner_type",
        "filter": {"status": "active"},
    },
    "products": {
        "label": "Equip products (/equip)",
        "name_field": "name",
        "image_field": "image_url",
        "subtitle_field": "category",
        "filter": {"moderation_status": "active"},
    },
    "research_artifacts": {
        "label": "Research (/research)",
        "name_field": "title",
        "image_field": "image_url",
        "subtitle_field": "kind",
        "filter": {"status": "published"},
    },
}


@router.get("")
async def list_all_captionable_images(_=Depends(require_roles("admin"))):
    """Return every captionable record (records with an image present) from
    every allowed collection."""
    from database import db
    out = []
    for col_name, cfg in ALLOWED_COLLECTIONS.items():
        projection = {
            "_id": 0,
            "id": 1,
            cfg["name_field"]: 1,
            cfg["image_field"]: 1,
            cfg["subtitle_field"]: 1,
            "image_caption": 1,
        }
        projection["slug"] = 1
        query = dict(cfg.get("filter") or {})
        # Only records that actually have an image — captioning needs a source.
        query[cfg["image_field"]] = {"$nin": [None, ""]}
        cursor = db[col_name].find(query, projection)
        async for doc in cursor:
            out.append({
                "collection": col_name,
                "collection_label": cfg["label"],
                "id": doc.get("id"),
                "name": doc.get(cfg["name_field"]) or "(untitled)",
                "subtitle": doc.get(cfg["subtitle_field"]) or "",
                "image_url": doc.get(cfg["image_field"]),
                "slug": doc.get("slug"),
                "caption": doc.get("image_caption") or "",
                "captioned": bool(doc.get("image_caption")),
            })
    # Uncaptioned first so the admin sees what's missing.
    out.sort(key=lambda r: (r["captioned"], r["collection_label"], r["name"].lower()))
    return {
        "total": len(out),
        "captioned": sum(1 for r in out if r["captioned"]),
        "items": out,
    }


@router.put("/{collection}/{record_id}")
async def set_image_caption(
    collection: str,
    record_id: str,
    payload: dict,
    _=Depends(require_roles("admin")),
):
    """Manual override — useful if the AI caption is wrong and you want to fix it."""
    if collection not in ALLOWED_COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"caption not supported for collection={collection}")
    from database import db
    caption = (payload.get("caption") or "").strip()
    res = await db[collection].update_one(
        {"id": record_id},
        {"$set": {"image_caption": caption or None, "updated_at": now_iso()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="record not found")
    try:
        from utils.help_context import invalidate_cache
        invalidate_cache()
    except Exception:
        pass
    return {"collection": collection, "id": record_id, "caption": caption}


@router.post("/auto-caption")
async def run_auto_captioning(
    limit: int = 25,
    force: bool = False,
    _=Depends(require_roles("admin")),
):
    """Trigger the AI vision agent to caption images that don't have captions yet.

    Captions are stored on the record under `image_caption` and read by the
    help assistant via `utils/help_context.py`. The agent uses Claude Sonnet
    4.5 vision (≈$0.003 per image with Foundation markup). Setting
    `force=true` regenerates captions even for records that already have one
    (useful after a bulk image swap).
    """
    from database import db
    from utils.image_caption_agent import auto_caption_pending
    return await auto_caption_pending(db, limit=max(1, min(int(limit), 100)), force=bool(force))
