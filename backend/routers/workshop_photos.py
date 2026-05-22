"""Workshop photo gallery: upload, moderate, view.

Permissions:
- Upload: registered (paid) participants, the workshop's facilitator, admin.
- Approve / reject: workshop's facilitator OR admin.
- Delete: admin (and facilitator can delete photos they personally rejected).
- Public list: only approved photos.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from auth_utils import get_current_user, require_roles
from models import PhotoModerationAction, gen_id, now_iso
from utils.images import ALLOWED_MIME, ImageProcessingError, process_upload

logger = logging.getLogger("birthright.photos")
router = APIRouter(prefix="/workshop-photos", tags=["workshop-photos"])

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB
STATIC_ROOT = Path(__file__).resolve().parent.parent / "static" / "workshop_photos"


async def _ensure_can_upload(db, workshop_id: str, user: dict) -> dict:
    """Return the workshop doc if user is allowed to upload, else raise."""
    w = await db.workshops.find_one({"id": workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    role = user.get("role")
    if role == "admin":
        return w
    if role == "facilitator" and w.get("facilitator_id") == user["id"]:
        return w
    # paid participant?
    reg = await db.registrations.find_one(
        {"workshop_id": workshop_id, "user_id": user["id"], "payment_status": "paid"}
    )
    if reg:
        return w
    raise HTTPException(
        status_code=403,
        detail="Only registered participants, the workshop's facilitator, or admin can upload photos.",
    )


async def _ensure_can_moderate(db, workshop_id: str, user: dict) -> dict:
    w = await db.workshops.find_one({"id": workshop_id})
    if not w:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if user.get("role") == "admin":
        return w
    if user.get("role") == "facilitator" and w.get("facilitator_id") == user["id"]:
        return w
    raise HTTPException(status_code=403, detail="Only the workshop facilitator or admin can moderate photos.")


@router.post("/{workshop_id}")
async def upload_photo(
    workshop_id: str,
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: dict = Depends(get_current_user),
):
    from database import db
    await _ensure_can_upload(db, workshop_id, user)

    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    # Cheap pre-check: trust Content-Length header so we reject oversize uploads without buffering.
    declared_size = getattr(file, "size", None)
    if declared_size is not None and declared_size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 8 MB)")

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 8 MB)")

    photo_id = gen_id()
    dest = STATIC_ROOT / workshop_id
    try:
        full_name, thumb_name = process_upload(raw, dest, photo_id)
    except ImageProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Facilitator/admin uploads are auto-approved; participant uploads go to moderation queue.
    role = user.get("role")
    auto_approve = role in ("facilitator", "admin")
    photo = {
        "id": photo_id,
        "workshop_id": workshop_id,
        "uploader_id": user["id"],
        "uploader_name": f"{user['first_name']} {user['last_name']}",
        "uploader_role": role,
        "image_url": f"/api/static/workshop_photos/{workshop_id}/{full_name}",
        "thumb_url": f"/api/static/workshop_photos/{workshop_id}/{thumb_name}",
        "caption": caption.strip()[:280],
        "status": "approved" if auto_approve else "pending",
        "reviewed_by": user["id"] if auto_approve else None,
        "reviewed_at": now_iso() if auto_approve else None,
        "rejection_reason": None,
        "created_at": now_iso(),
    }
    await db.workshop_photos.insert_one(photo)
    photo.pop("_id", None)
    return photo


@router.get("/{workshop_id}")
async def list_workshop_photos(
    workshop_id: str,
    status: str = "approved",
):
    """Public list. Defaults to approved photos only."""
    from database import db
    if status not in ("approved", "pending", "rejected", "all"):
        raise HTTPException(status_code=400, detail="Invalid status filter")
    query: dict = {"workshop_id": workshop_id}
    if status != "all":
        query["status"] = status
    photos = await db.workshop_photos.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return photos


@router.get("/{workshop_id}/pending")
async def list_pending_for_workshop(
    workshop_id: str,
    user: dict = Depends(require_roles("facilitator", "admin")),
):
    from database import db
    await _ensure_can_moderate(db, workshop_id, user)
    photos = await db.workshop_photos.find(
        {"workshop_id": workshop_id, "status": "pending"}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    return photos


@router.get("")
async def list_all_pending(user: dict = Depends(require_roles("facilitator", "admin"))):
    """Cross-workshop moderation queue. Facilitator sees their workshops; admin sees all."""
    from database import db
    if user["role"] == "admin":
        scope = {"status": "pending"}
    else:
        my_workshops = await db.workshops.find(
            {"facilitator_id": user["id"]}, {"id": 1, "_id": 0}
        ).to_list(500)
        ids = [w["id"] for w in my_workshops]
        scope = {"status": "pending", "workshop_id": {"$in": ids}}
    photos = await db.workshop_photos.find(scope, {"_id": 0}).sort("created_at", 1).to_list(500)
    # enrich with workshop title for display
    for p in photos:
        w = await db.workshops.find_one({"id": p["workshop_id"]}, {"_id": 0, "title": 1, "slug": 1})
        p["workshop_title"] = w["title"] if w else "(deleted workshop)"
        p["workshop_slug"] = w["slug"] if w else None
    return photos


@router.post("/{photo_id}/approve")
async def approve_photo(
    photo_id: str,
    user: dict = Depends(require_roles("facilitator", "admin")),
):
    from database import db
    p = await db.workshop_photos.find_one({"id": photo_id})
    if not p:
        raise HTTPException(status_code=404, detail="Photo not found")
    await _ensure_can_moderate(db, p["workshop_id"], user)
    await db.workshop_photos.update_one(
        {"id": photo_id},
        {"$set": {"status": "approved", "reviewed_by": user["id"], "reviewed_at": now_iso(),
                  "rejection_reason": None}},
    )
    return {"success": True}


@router.post("/{photo_id}/reject")
async def reject_photo(
    photo_id: str,
    data: PhotoModerationAction,
    user: dict = Depends(require_roles("facilitator", "admin")),
):
    from database import db
    p = await db.workshop_photos.find_one({"id": photo_id})
    if not p:
        raise HTTPException(status_code=404, detail="Photo not found")
    await _ensure_can_moderate(db, p["workshop_id"], user)
    await db.workshop_photos.update_one(
        {"id": photo_id},
        {"$set": {"status": "rejected", "reviewed_by": user["id"], "reviewed_at": now_iso(),
                  "rejection_reason": (data.reason or "").strip()[:280]}},
    )
    return {"success": True}


@router.delete("/{photo_id}")
async def delete_photo(photo_id: str, user: dict = Depends(get_current_user)):
    """Admin can delete any photo. Uploader can delete their own pending or rejected photo."""
    from database import db
    p = await db.workshop_photos.find_one({"id": photo_id})
    if not p:
        raise HTTPException(status_code=404, detail="Photo not found")
    if user["role"] != "admin" and (p["uploader_id"] != user["id"] or p["status"] == "approved"):
        raise HTTPException(status_code=403, detail="Cannot delete this photo")
    # Best-effort: remove files from disk
    for fname in (Path(p["image_url"]).name, Path(p.get("thumb_url") or "").name):
        if fname:
            (STATIC_ROOT / p["workshop_id"] / fname).unlink(missing_ok=True)
    await db.workshop_photos.delete_one({"id": photo_id})
    return {"success": True}
