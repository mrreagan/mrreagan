"""Tests for the Foundation Prospects + Featured Artist Invitations + the
Explore-before-Embrace preview flow."""
from __future__ import annotations

import os
import pathlib
import sys
import uuid
from datetime import datetime, timezone, timedelta

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

API_BASE = "http://localhost:8001/api"
ADMIN_EMAIL = "admin@birthright.org"
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


@pytest.mark.asyncio
async def test_prospect_crud_and_interactions(admin_token, db):
    """Create prospect → add interaction → list → update → archive."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        # Create
        r = await c.post("/gallery/admin/prospects", json={
            "display_name": "Paige Test",
            "contact_email": f"paige-{uuid.uuid4().hex[:6]}@birthright.test",
            "location": "Sausalito, CA",
            "mediums": "plein-air oils, watercolor",
            "statement_excerpt": "I paint slow mornings on the bluffs above town.",
            "referred_by": "Founders' studio visit · May",
            "initial_interaction_channel": "studio_visit",
            "initial_interaction_notes": "Met at her open studio; she was warm and curious about partnering.",
        })
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["status"] == "outreach_sent"
        assert len(r.json()["interactions"]) == 1
        assert r.json()["interactions"][0]["channel"] == "studio_visit"

        # Add a second interaction (positive response)
        r = await c.post(f"/gallery/admin/prospects/{pid}/interactions", json={
            "channel": "email",
            "notes": "Replied within an hour — interested.",
            "response_received": True,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["interactions"]) == 2
        assert body["status"] == "responded_interested"  # auto-advanced

        # Update field
        r = await c.put(f"/gallery/admin/prospects/{pid}", json={
            "foundation_score": 4, "internal_notes": "Strong fit — high priority.",
        })
        assert r.status_code == 200
        assert r.json()["foundation_score"] == 4

        # List with filter
        r = await c.get("/gallery/admin/prospects", params={"status": "responded_interested"})
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json()["prospects"])

        # Hard delete (cleanup)
        r = await c.delete(f"/gallery/admin/prospects/{pid}")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_invite_explore_then_accept(admin_token, db):
    """Foundation issues invite → preview is public → artist accepts + enrolls."""
    contact_email = f"jules-{uuid.uuid4().hex[:6]}@birthright.test"
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        # Create prospect with email
        r = await c.post("/gallery/admin/prospects", json={
            "display_name": "Jules Riverstone",
            "contact_email": contact_email,
            "location": "Mendocino",
            "statement_excerpt": "I make slow, listening photographs.",
        })
        pid = r.json()["id"]

        # Promote → issues invite, schedules a far-future Foundation month
        future = (datetime.now(timezone.utc).date() + timedelta(days=180))
        month_str = future.strftime("%Y-%m")
        r = await c.post(f"/gallery/admin/prospects/{pid}/promote", json={
            "feature_in_month": month_str,
            "period_label": f"Test Month {month_str}",
            "editorial_reason": "Her listening photographs match the foundation's mission.",
        })
        assert r.status_code == 200, r.text
        token = r.json()["invite"]["token"]
        assert token
        assert r.json()["preview_url"].startswith("/gallery/invite/")

    # Public preview (no auth headers)
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get(f"/gallery/invite/{token}")
        assert r.status_code == 200, r.text
        body = r.json()
        # Status moves to 'previewed' on first view
        assert body["invite"]["status"] == "previewed"
        # Full option menu surfaced
        assert "statement" in body["options"]
        assert len(body["options"]["statement"]["choices"]) == 5
        assert body["options"]["statement"]["max_length"] == 180
        assert len(body["options"]["layouts"]) == 4
        assert len(body["options"]["accent_colors"]) == 6
        assert len(body["options"]["statement_positions"]) == 5
        # "What acceptance means" surfaced
        assert "obligations" in body["what_acceptance_means"]
        assert "foundation_share" in body["what_acceptance_means"]

        # Second view increments preview_count
        r = await c.get(f"/gallery/invite/{token}")
        assert r.json()["invite"]["preview_count"] == 2

    # Accept WITHOUT agreeing → rejected
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.post(f"/gallery/invite/{token}/accept", json={
            "password": "explorer-2026!",
            "agreed_to_partnership_terms": False,
        })
        assert r.status_code == 400

        # Accept WITH agreement → enroll
        r = await c.post(f"/gallery/invite/{token}/accept", json={
            "password": "explorer-2026!",
            "agreed_to_partnership_terms": True,
            "signature_statement": "Listening, then looking.",
            "signature_statement_source": "freeform",
            "accent_color": "river",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["partner_profile"]["partner_type"] == "artist"
        assert body["partner_profile"]["status"] == "active"
        assert body["partner_profile"]["source"] == "foundation"
        assert body["featured_slot_id"]
        assert body["session_token"]

    # Invite cannot be re-accepted
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.post(f"/gallery/invite/{token}/accept", json={
            "password": "explorer-2026!",
            "agreed_to_partnership_terms": True,
        })
        assert r.status_code == 400
        assert "already been accepted" in r.text.lower()

    # Cleanup
    await db.users.delete_one({"email": contact_email})
    await db.partner_profiles.delete_many({"user_id": body["user_id"]})
    await db.featured_artist_slots.delete_many({"id": body["featured_slot_id"]})
    await db.featured_artist_invites.delete_one({"token": token})
    await db.featured_artist_prospects.delete_one({"id": pid})


@pytest.mark.asyncio
async def test_invite_decline(admin_token, db):
    """Invitation can be declined publicly."""
    contact_email = f"decline-{uuid.uuid4().hex[:6]}@birthright.test"
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/prospects", json={
            "display_name": "Maya Decline-Test",
            "contact_email": contact_email,
            "statement_excerpt": "I draw quietly.",
        })
        pid = r.json()["id"]
        future = (datetime.now(timezone.utc).date() + timedelta(days=210))
        r = await c.post(f"/gallery/admin/prospects/{pid}/promote", json={
            "feature_in_month": future.strftime("%Y-%m"),
            "editorial_reason": "Test decline path",
        })
        token = r.json()["invite"]["token"]

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.post(f"/gallery/invite/{token}/decline", json={
            "reason": "Timing isn't right for me this season. Thank you."
        })
        assert r.status_code == 200
        # Re-decline blocked
        r = await c.post(f"/gallery/invite/{token}/decline", json={})
        assert r.status_code == 400

    # Cleanup
    await db.featured_artist_invites.delete_one({"token": token})
    await db.featured_artist_prospects.delete_one({"id": pid})


@pytest.mark.asyncio
async def test_admin_list_invites(admin_token, db):
    """Admin list/count endpoint surfaces invite stats."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.get("/gallery/admin/invites")
        assert r.status_code == 200
        body = r.json()
        assert "invites" in body
        assert "counts" in body


@pytest.mark.asyncio
async def test_non_admin_cannot_access_prospects(db):
    """Anonymous request blocked."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/gallery/admin/prospects")
        assert r.status_code in (401, 403)
        r = await c.post("/gallery/admin/prospects", json={"display_name": "Hack"})
        assert r.status_code in (401, 403)
