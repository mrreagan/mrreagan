"""Tests for the generic partner prospects + Explore-before-Embrace
invitation system spanning all 6 partner types."""
from __future__ import annotations

import os
import pathlib
import sys
import uuid

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.live"
PASSWORD = "birthright2026"


async def _login(email: str) -> str:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.post("/auth/login", json={"email": email, "password": PASSWORD})
        r.raise_for_status()
        return r.json()["token"]


@pytest_asyncio.fixture
async def admin_token() -> str:
    return await _login(ADMIN_EMAIL)


@pytest_asyncio.fixture
async def db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


# ============ Per-type preview spec ============

@pytest.mark.asyncio
@pytest.mark.parametrize("partner_type", ["facilitator", "community", "research", "vendor", "artist", "steward"])
async def test_public_preview_spec_per_type(partner_type):
    """All 6 partner types expose a complete preview spec publicly."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get(f"/partners/preview-specs/{partner_type}")
        assert r.status_code == 200, r.text
        spec = r.json()
        assert spec["partner_type"] == partner_type
        assert spec["title"]
        assert spec["blurb"]
        assert spec["default_headline"]
        assert "options" in spec
        wam = spec["what_acceptance_means"]
        assert wam["summary"]
        assert isinstance(wam["obligations"], list) and len(wam["obligations"]) >= 2
        assert isinstance(wam["you_keep"], list) and len(wam["you_keep"]) >= 2
        assert wam["foundation_share"]


@pytest.mark.asyncio
async def test_public_preview_index_lists_all_types():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/partners/preview-specs")
        assert r.status_code == 200
        body = r.json()
        for pt in ("facilitator", "community", "research", "vendor", "artist", "steward"):
            assert pt in body
            assert body[pt]["title"]


# ============ Prospect CRUD + Interactions ============

@pytest.mark.asyncio
@pytest.mark.parametrize("partner_type", ["facilitator", "community", "research", "vendor", "steward"])
async def test_create_and_interact_with_prospect(admin_token, partner_type, db):
    """One prospect per type — full create + interaction + auto-advance flow."""
    email = f"prospect-{partner_type}-{uuid.uuid4().hex[:6]}@birthright.test"
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects", json={
            "partner_type": partner_type,
            "display_name": f"Test {partner_type.title()}",
            "contact_email": email,
            "headline_excerpt": f"Sample {partner_type} headline",
            "bio_excerpt": "Two sentences of bio. Just a sample.",
            "initial_interaction_channel": "email",
            "initial_interaction_notes": "Initial outreach sent.",
        })
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["partner_type"] == partner_type
        assert r.json()["status"] == "outreach_sent"

        # Log a positive response → auto-advances to responded_interested
        r = await c.post(f"/partners/admin/prospects/{pid}/interactions", json={
            "channel": "email",
            "notes": "Replied — interested in learning more.",
            "response_received": True,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "responded_interested"

        # Filter by partner_type returns it
        r = await c.get("/partners/admin/prospects", params={"partner_type": partner_type})
        assert any(p["id"] == pid for p in r.json()["prospects"])

    await db.partner_prospects.delete_one({"id": pid})


# ============ Promote → Invite preview → Accept ============

@pytest.mark.asyncio
@pytest.mark.parametrize("partner_type", ["facilitator", "community", "research", "vendor", "steward"])
async def test_explore_then_embrace_per_type(admin_token, partner_type, db):
    """End-to-end Explore-before-Embrace per partner type."""
    email = f"e2e-{partner_type}-{uuid.uuid4().hex[:6]}@birthright.test"
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects", json={
            "partner_type": partner_type,
            "display_name": f"Sample {partner_type.title()} Person",
            "contact_email": email,
            "headline_excerpt": "Sample headline",
            "bio_excerpt": "Sample bio.",
        })
        pid = r.json()["id"]

        # Promote → issue invitation
        r = await c.post(f"/partners/admin/prospects/{pid}/promote", json={
            "note_to_prospect": "Looking forward to working with you.",
            "suggested_subscription_tier": "annual",
        })
        assert r.status_code == 200, r.text
        token = r.json()["invite"]["token"]
        assert r.json()["preview_url"].startswith("/partner/invite/")

    # Public preview — no auth
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get(f"/partners/invite/{token}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["invite"]["status"] == "previewed"
        assert body["invite"]["partner_type"] == partner_type
        assert body["spec"]["title"]
        assert body["spec"]["what_acceptance_means"]["foundation_share"]

        # Refuse without agreement
        r = await c.post(f"/partners/invite/{token}/accept", json={
            "password": "discoverer-2026!", "agreed_to_partnership_terms": False,
        })
        assert r.status_code == 400

        # Accept properly
        r = await c.post(f"/partners/invite/{token}/accept", json={
            "password": "discoverer-2026!",
            "agreed_to_partnership_terms": True,
            "selected_subscription_tier": "annual",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["partner_profile"]["partner_type"] == partner_type
        assert body["partner_profile"]["status"] == "active"
        assert body["partner_profile"]["source"] == "foundation"
        assert body["partner_profile"]["selected_subscription_tier"] == "annual"
        assert body["session_token"]
        user_id = body["user_id"]
        partner_id = body["partner_profile"]["id"]

        # Re-accept blocked
        r = await c.post(f"/partners/invite/{token}/accept", json={
            "password": "discoverer-2026!", "agreed_to_partnership_terms": True,
        })
        assert r.status_code == 400

    # Cleanup
    await db.users.delete_one({"id": user_id})
    await db.partner_profiles.delete_one({"id": partner_id})
    await db.partner_invites.delete_one({"token": token})
    await db.partner_prospects.delete_one({"id": pid})


@pytest.mark.asyncio
async def test_invite_decline_path(admin_token, db):
    email = f"decline-{uuid.uuid4().hex[:6]}@birthright.test"
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects", json={
            "partner_type": "community",
            "display_name": "Maybe Not",
            "contact_email": email,
        })
        pid = r.json()["id"]
        r = await c.post(f"/partners/admin/prospects/{pid}/promote", json={})
        token = r.json()["invite"]["token"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.post(f"/partners/invite/{token}/decline", json={"reason": "Not the right time."})
        assert r.status_code == 200
        r = await c.post(f"/partners/invite/{token}/decline", json={})
        assert r.status_code == 400
    await db.partner_invites.delete_one({"token": token})
    await db.partner_prospects.delete_one({"id": pid})


@pytest.mark.asyncio
async def test_anon_blocked_from_admin_endpoints():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        for path in ("/partners/admin/prospects", "/partners/admin/invites"):
            r = await c.get(path)
            assert r.status_code in (401, 403)
        r = await c.post("/partners/admin/prospects", json={"partner_type": "vendor", "display_name": "Hack"})
        assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_promote_requires_contact_email(admin_token, db):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects", json={
            "partner_type": "research", "display_name": "No Email Person",
        })
        pid = r.json()["id"]
        r = await c.post(f"/partners/admin/prospects/{pid}/promote", json={})
        assert r.status_code == 400
        assert "contact_email" in r.text.lower() or "email" in r.text.lower()
    await db.partner_prospects.delete_one({"id": pid})
