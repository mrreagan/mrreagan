"""Legal: versioned universal indemnification + signature tracking.

Anyone authenticated can view the active version and sign it. Admin can publish
new versions; activating a new version automatically deactivates prior ones and
updates the global_defaults pointer. Signatures are append-only and tied to a
specific version, so we have evidence of WHAT each user signed.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from auth_utils import get_current_user, require_roles
from models import IndemnificationCreate, gen_id, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.legal")
router = APIRouter(prefix="/legal", tags=["legal"])


DEFAULT_INDEMNIFICATION_BODY = """# Universal Indemnification & Hold-Harmless Agreement

**Placeholder text — not legal advice.** Birthright Foundation will replace this with counsel-reviewed copy before launch.

By accepting this agreement, you acknowledge that:

1. **Voluntary participation.** Workshops, materials, and partner services are educational in nature. You participate at your own discretion.
2. **No professional advice.** Content is not a substitute for licensed mental-health, medical, or legal advice.
3. **Hold harmless.** You agree not to hold Birthright Foundation, its governing board, facilitators, vendors, or community partners liable for outcomes arising from your participation, except in cases of gross negligence.
4. **Respectful conduct.** You agree to abide by the community standards and to engage facilitators, fellow participants, and partners with respect.
5. **Data & privacy.** Personal information you provide is governed by the Birthright privacy policy.

This agreement is versioned. If we substantively change it, you will be asked to review and sign the new version before further participation in workshops or partner programs.
"""


# ============ VERSIONS ============

@router.get("/indemnification/active")
async def get_active_version():
    from database import db
    v = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not v:
        # Bootstrap: create v1.0 placeholder
        v = {
            "id": gen_id(),
            "version": "1.0",
            "body": DEFAULT_INDEMNIFICATION_BODY,
            "summary_of_changes": "Initial placeholder text.",
            "active": True,
            "created_by": "system",
            "created_at": now_iso(),
            "activated_at": now_iso(),
        }
        await db.indemnification_versions.insert_one(dict(v))
        v.pop("_id", None)
    return v


@router.get("/indemnification/versions")
async def list_versions(user: dict = Depends(require_roles("admin"))):
    from database import db
    versions = await db.indemnification_versions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return versions


@router.post("/indemnification/versions")
async def create_version(
    data: IndemnificationCreate,
    user: dict = Depends(require_roles("admin")),
):
    """Publish a new version. It becomes active immediately and deactivates the prior one."""
    from database import db
    existing = await db.indemnification_versions.find_one({"version": data.version})
    if existing:
        raise HTTPException(status_code=400, detail=f"Version {data.version} already exists")
    # deactivate all prior
    await db.indemnification_versions.update_many({"active": True}, {"$set": {"active": False}})
    version_id = gen_id()
    doc = {
        "id": version_id,
        "version": data.version.strip(),
        "body": data.body,
        "summary_of_changes": (data.summary_of_changes or "").strip(),
        "active": True,
        "created_by": user["id"],
        "created_at": now_iso(),
        "activated_at": now_iso(),
    }
    await db.indemnification_versions.insert_one(dict(doc))
    # also update global_defaults pointer for convenience
    await db.foundation_settings.update_one(
        {"key": "global_defaults"},
        {"$set": {"indemnification_active_version_id": version_id, "updated_at": now_iso()}},
        upsert=True,
    )
    await log_action(
        db, user, "legal.indemnification.activate",
        target_type="indemnification_version", target_id=version_id,
        metadata={"version": data.version},
    )
    doc.pop("_id", None)
    return doc


# ============ SIGNATURES ============

@router.post("/indemnification/sign")
async def sign_active(request: Request, user: dict = Depends(get_current_user)):
    from database import db
    active = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not active:
        raise HTTPException(status_code=400, detail="No active indemnification version")
    existing = await db.indemnification_signatures.find_one({
        "user_id": user["id"], "version_id": active["id"],
    })
    if existing:
        return {"already_signed": True, "version": active["version"], "signed_at": existing.get("signed_at")}
    sig = {
        "id": gen_id(),
        "version_id": active["id"],
        "version": active["version"],
        "user_id": user["id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "user_role": user.get("role", "participant"),
        "signed_at": now_iso(),
        "ip": (request.client.host if request and request.client else None),
    }
    await db.indemnification_signatures.insert_one(dict(sig))
    await log_action(
        db, user, "legal.indemnification.sign",
        target_type="indemnification_version", target_id=active["id"],
        metadata={"version": active["version"]},
    )
    sig.pop("_id", None)
    return {"already_signed": False, **sig}


@router.get("/indemnification/my-status")
async def my_status(user: dict = Depends(get_current_user)):
    """Check whether the signed-in user has accepted the active version."""
    from database import db
    active = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not active:
        return {"active_version": None, "signed": False}
    sig = await db.indemnification_signatures.find_one(
        {"user_id": user["id"], "version_id": active["id"]}, {"_id": 0}
    )
    return {
        "active_version": {"id": active["id"], "version": active["version"]},
        "signed": bool(sig),
        "signed_at": sig.get("signed_at") if sig else None,
    }


@router.get("/indemnification/signatures")
async def list_signatures(
    version_id: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query = {"version_id": version_id} if version_id else {}
    sigs = await db.indemnification_signatures.find(query, {"_id": 0}).sort("signed_at", -1).to_list(2000)
    return sigs
