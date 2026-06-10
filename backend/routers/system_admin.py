"""Admin: system settings + on-demand migration runner.

  - GET  /admin/system/settings           — read the singleton settings doc
  - PUT  /admin/system/settings           — admin updates support_email etc.
  - GET  /system/settings/public          — public read of safe fields (no auth)
  - GET  /admin/system/migrations         — list applied vs pending
  - POST /admin/system/run-migrations     — apply all pending now
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth_utils import require_roles
from models import now_iso
from utils.data_migrations import MIGRATIONS, applied_ids, apply_pending

admin_router = APIRouter(prefix="/admin/system", tags=["admin-system"])
public_router = APIRouter(prefix="/system", tags=["system-public"])


class SystemSettings(BaseModel):
    support_email: EmailStr = "support@birthright.live"
    hello_email: EmailStr = "hello@birthright.live"


@admin_router.get("/settings")
async def get_settings(user: dict = Depends(require_roles("admin"))):
    from database import db
    doc = await db.system_settings.find_one({"id": "global"}, {"_id": 0})
    return doc or {"id": "global",
                    "support_email": "support@birthright.live",
                    "hello_email": "hello@birthright.live"}


class SettingsUpdate(BaseModel):
    support_email: Optional[EmailStr] = None
    hello_email: Optional[EmailStr] = None


@admin_router.put("/settings")
async def update_settings(body: SettingsUpdate,
                          user: dict = Depends(require_roles("admin"))):
    from database import db
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if not upd:
        raise HTTPException(400, "No fields to update")
    upd["updated_at"] = now_iso()
    upd["updated_by"] = user.get("email", "admin")
    await db.system_settings.update_one(
        {"id": "global"},
        {"$set": upd, "$setOnInsert": {"id": "global"}},
        upsert=True,
    )
    doc = await db.system_settings.find_one({"id": "global"}, {"_id": 0})
    return doc


@public_router.get("/settings/public")
async def public_settings():
    """Anyone can read the site's currently-configured support/hello
    addresses — the frontend uses these in 'Contact a human' UI."""
    from database import db
    doc = await db.system_settings.find_one({"id": "global"}, {"_id": 0}) or {}
    return {
        "support_email": doc.get("support_email", "support@birthright.live"),
        "hello_email": doc.get("hello_email", "hello@birthright.live"),
    }


@admin_router.get("/migrations")
async def list_migrations(user: dict = Depends(require_roles("admin"))):
    """Show which data migrations have been applied to THIS environment's
    database, and which are pending. Pending means: the code knows about
    them but the DB has not yet been written to."""
    from database import db
    seen = await applied_ids(db)
    rows = []
    for mid, _fn in MIGRATIONS:
        applied = mid in seen
        meta = await db.system_migrations.find_one({"id": mid}, {"_id": 0}) \
            if applied else None
        rows.append({
            "id": mid,
            "applied": applied,
            "applied_at": (meta or {}).get("applied_at"),
            "result": (meta or {}).get("result"),
        })
    return {"migrations": rows,
             "pending_count": sum(1 for r in rows if not r["applied"])}


class RunMigrationsBody(BaseModel):
    force: bool = Field(default=False,
                         description="If true, re-runs every migration "
                                     "(idempotent). Use sparingly.")


@admin_router.post("/run-migrations")
async def run_migrations(body: RunMigrationsBody = RunMigrationsBody(),
                          user: dict = Depends(require_roles("admin"))):
    from database import db
    log = await apply_pending(db, force=body.force)
    return {"ok": True, "log": log}
