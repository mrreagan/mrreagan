"""Backend tests for AI Studio Phase 3 — Vendor self-service + admin moderation.

Tests the full vendor → admin moderation lifecycle without spending AI dollars
(we use db fixture inserts to short-circuit the LLM-spending generate path).
"""
from __future__ import annotations

import os
import pathlib
import sys
import uuid

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.live"
VENDOR_EMAIL = "demo@birthright.live"  # has both community + vendor partner profile
FACILITATOR_EMAIL = "elena@birthright.live"  # no vendor profile
PASSWORD = "birthright2026"


async def _login(email: str) -> str:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        r = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
        r.raise_for_status()
        return r.json()["token"]


@pytest_asyncio.fixture
async def admin_token() -> str:
    return await _login(ADMIN_EMAIL)


@pytest_asyncio.fixture
async def vendor_token() -> str:
    return await _login(VENDOR_EMAIL)


@pytest_asyncio.fixture
async def facilitator_token() -> str:
    return await _login(FACILITATOR_EMAIL)


@pytest_asyncio.fixture
async def vendor_draft_id() -> str:
    """Seed a vendor draft directly via the DB so we don't burn AI dollars on every run."""
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: PLC0415
    from models import gen_id, now_iso  # noqa: PLC0415
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    vp = await db.partner_profiles.find_one({"partner_type": "vendor", "status": "active"})
    vendor_user_id = vp["user_id"]
    pid = gen_id()
    doc = {
        "id": pid,
        "slug": f"test-draft-{uuid.uuid4().hex[:8]}",
        "name": "Test Vendor Draft",
        "description": "A test vendor draft for moderation flow tests.",
        "price": 0.0,
        "type": "merch",
        "workshop_id": None,
        "image_url": "/api/static/products/studio-cap-3cb34801.png",
        "image_gallery": ["/api/static/products/studio-cap-3cb34801.png"],
        "inventory": 0,
        "category": "tote",
        "studio_draft": True,
        "studio_brief": "test",
        "studio_audiences": ["general_equip"],
        "studio_copy_variants": {"general_equip": {"name": "Test Vendor Draft", "description": "..."}},
        "moderation_status": "pending_review",
        "moderation_note": "Vendor AI Studio submission — awaiting admin moderation.",
        "is_vendor_product": True,
        "vendor_user_id": vendor_user_id,
        "vendor_partner_id": vp["id"],
        "vendor_name": vp.get("display_name"),
        "vendor_slug": vp.get("slug"),
        "created_at": now_iso(),
        "created_by": vendor_user_id,
    }
    await db.products.insert_one(dict(doc))
    try:
        yield pid
    finally:
        await db.products.delete_one({"id": pid})
        client.close()


@pytest.mark.asyncio
async def test_facilitator_without_vendor_profile_is_403(facilitator_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {facilitator_token}"}) as client:
        r = await client.post("/studio/estimate",
                              json={"brief": "test brief here", "category": "tote",
                                    "audiences": ["general_equip"], "image_count": 1})
        assert r.status_code == 403
        assert "vendor partner profile" in r.json()["detail"]


@pytest.mark.asyncio
async def test_vendor_can_estimate(vendor_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as client:
        r = await client.post("/studio/estimate",
                              json={"brief": "minimal cream tote bag", "category": "tote",
                                    "audiences": ["general_equip"], "image_count": 1})
        assert r.status_code == 200
        body = r.json()
        assert body["estimated_cost_usd"] > 0
        assert "disclosure" in body


@pytest.mark.asyncio
async def test_admin_queue_is_admin_only(vendor_token: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as client:
        r = await client.get("/admin/studio/queue")
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_my_drafts_vendor_scoped(vendor_token: str, vendor_draft_id: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as client:
        r = await client.get("/studio/my-drafts")
        assert r.status_code == 200
        ids = {row["id"] for row in r.json()}
        assert vendor_draft_id in ids


@pytest.mark.asyncio
async def test_admin_request_changes_then_approve(admin_token: str, vendor_draft_id: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        # 1) See pending
        r = await client.get("/admin/studio/queue?status=pending_review")
        assert r.status_code == 200
        assert vendor_draft_id in {row["id"] for row in r.json()}

        # 2) Request changes (note too short → 422 from pydantic min_length)
        r = await client.post(f"/admin/studio/queue/{vendor_draft_id}/request-changes",
                              json={"admin_note": "ok"})
        assert r.status_code == 422

        # 3) Request changes properly
        r = await client.post(f"/admin/studio/queue/{vendor_draft_id}/request-changes",
                              json={"admin_note": "Please regenerate with a softer color palette."})
        assert r.status_code == 200

        # 4) Should now appear in changes_requested
        r = await client.get("/admin/studio/queue?status=changes_requested")
        assert vendor_draft_id in {row["id"] for row in r.json()}

        # 5) Approve with price
        r = await client.post(f"/admin/studio/queue/{vendor_draft_id}/approve",
                              json={"price": 24.95, "admin_note": "Love it. Published."})
        assert r.status_code == 200

        # 6) Now in active
        r = await client.get("/admin/studio/queue?status=active")
        active_ids = {row["id"] for row in r.json()}
        assert vendor_draft_id in active_ids

        # 7) Product is published with price set
        r = await client.get(f"/products/{vendor_draft_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["price"] == 24.95
        assert body["moderation_status"] == "active"
        assert body["studio_draft"] is False

        # 8) Re-approve should 400 (terminal)
        r = await client.post(f"/admin/studio/queue/{vendor_draft_id}/approve",
                              json={"price": 30.0})
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_admin_reject_terminal(admin_token: str, vendor_draft_id: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as client:
        r = await client.post(f"/admin/studio/queue/{vendor_draft_id}/reject",
                              json={"admin_note": "Off-brand visuals."})
        assert r.status_code == 200

        r = await client.get("/admin/studio/queue?status=rejected")
        assert vendor_draft_id in {row["id"] for row in r.json()}

        # Re-approve after reject is allowed (back to pending lifecycle? No — must be in
        # pending_review|changes_requested). Rejected drafts should NOT be approvable.
        r = await client.post(f"/admin/studio/queue/{vendor_draft_id}/approve",
                              json={"price": 10.0})
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_vendor_can_discard_own_draft(vendor_token: str, vendor_draft_id: str) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as client:
        r = await client.delete(f"/studio/drafts/{vendor_draft_id}")
        assert r.status_code == 200
        assert r.json()["ok"] is True


@pytest.mark.asyncio
async def test_vendor_cannot_discard_others_draft(facilitator_token: str, vendor_draft_id: str) -> None:
    # Facilitator without vendor profile shouldn't even reach the discard logic
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {facilitator_token}"}) as client:
        r = await client.delete(f"/studio/drafts/{vendor_draft_id}")
        # Either 403 (ownership check) or 200 if admin/owner — facilitator isn't owner
        assert r.status_code in (403, 404)
