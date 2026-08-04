"""Tests for iter 43 — mission alignment BLUF + highlight URL + AI 3-draft suggestions."""
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


@pytest.mark.asyncio
async def test_prospect_persists_highlight_and_mission_fields(admin_token, db):
    """Highlight URL/label/excerpt/reason + mission_alignment all persist."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects", json={
            "partner_type": "vendor",
            "display_name": "Highlight Test Maker",
            "contact_email": f"hl-{uuid.uuid4().hex[:6]}@birthright.test",
            "bio_excerpt": "Wheel-thrown ceramics.",
            "highlight_url": "https://example.com/bowls/two-hands",
            "highlight_label": "product",
            "highlight_excerpt": "This bowl asks you to slow down. Two hands required.",
            "highlight_reason": "Their product literally enforces presence.",
            "mission_alignment": "Your work already makes presence ordinary. Birthright recognizes it.",
        })
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["highlight_url"] == "https://example.com/bowls/two-hands"
        assert r.json()["highlight_label"] == "product"
        assert r.json()["highlight_excerpt"].startswith("This bowl")
        assert r.json()["highlight_reason"].startswith("Their product")
        assert "presence" in r.json()["mission_alignment"]

        # PUT update preserves mission_alignment
        r = await c.put(f"/partners/admin/prospects/{pid}", json={
            "mission_alignment": "Updated alignment text.",
        })
        assert r.status_code == 200
        assert r.json()["mission_alignment"] == "Updated alignment text."

    await db.partner_prospects.delete_one({"id": pid})


@pytest.mark.asyncio
async def test_invite_preview_surfaces_highlight_and_mission(admin_token, db):
    """When invite is issued, public preview shows mission_alignment + highlight fields."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects", json={
            "partner_type": "artist",
            "display_name": "Preview Surface Test",
            "contact_email": f"ps-{uuid.uuid4().hex[:6]}@birthright.test",
            "bio_excerpt": "Painter.",
            "highlight_url": "https://example.com/gallery",
            "highlight_label": "page",
            "highlight_excerpt": "Slow looking is its own devotion.",
            "highlight_reason": "Echoes our mission directly.",
            "mission_alignment": "Your gallery already teaches the slow looking we want to make ordinary.",
        })
        pid = r.json()["id"]
        r = await c.post(f"/partners/admin/prospects/{pid}/promote", json={})
        token = r.json()["invite"]["token"]

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get(f"/partners/invite/{token}")
        assert r.status_code == 200
        inv = r.json()["invite"]
        assert inv["mission_alignment"].startswith("Your gallery")
        assert inv["highlight_url"] == "https://example.com/gallery"
        assert inv["highlight_label"] == "page"
        assert inv["highlight_excerpt"] == "Slow looking is its own devotion."
        assert inv["highlight_reason"] == "Echoes our mission directly."

    await db.partner_invites.delete_one({"token": token})
    await db.partner_prospects.delete_one({"id": pid})


@pytest.mark.asyncio
async def test_draft_suggest_mission_returns_three_voices(admin_token):
    """The draft endpoint returns exactly 3 drafts with distinct voices."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects/draft-suggest-mission", json={
            "partner_type": "vendor",
            "bio_excerpt": "I make small ceramic bowls for everyday meals.",
            "highlight_label": "product",
            "highlight_excerpt": "This bowl asks you to slow down.",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] in ("ai", "fallback")
        assert len(body["drafts"]) == 3
        voices = [d["voice"] for d in body["drafts"]]
        assert set(voices) == {"warm", "formal", "poetic"}
        for d in body["drafts"]:
            assert d["text"] and len(d["text"]) > 30


@pytest.mark.asyncio
async def test_draft_suggest_requires_minimum_context(admin_token):
    """The endpoint rejects requests with no headline/bio/highlight content."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects/draft-suggest-mission", json={
            "partner_type": "vendor",
        })
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_draft_suggest_requires_partner_type(admin_token):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects/draft-suggest-mission", json={
            "bio_excerpt": "Sample.",
        })
        assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_suggest_endpoint_on_existing_prospect(admin_token, db):
    """The id-scoped suggest endpoint pulls context from the saved prospect."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/admin/prospects", json={
            "partner_type": "artist",
            "display_name": "Saved Prospect",
            "bio_excerpt": "I make work that asks viewers to wait.",
            "highlight_label": "statement",
            "highlight_excerpt": "Patience is the form.",
        })
        pid = r.json()["id"]
        r = await c.post(f"/partners/admin/prospects/{pid}/suggest-mission-alignment", json={})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["drafts"]) == 3
    await db.partner_prospects.delete_one({"id": pid})


@pytest.mark.asyncio
async def test_anon_blocked_from_suggest_endpoints():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.post("/partners/admin/prospects/draft-suggest-mission", json={
            "partner_type": "vendor", "bio_excerpt": "test",
        })
        assert r.status_code in (401, 403)
