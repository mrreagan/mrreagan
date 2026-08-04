"""Backend tests for the statement-position lock + 5-option statement composer
introduced after iter39 featured artists shipped."""
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
ADMIN_EMAIL = "admin@birthright.live"
VENDOR_EMAIL = "demo@birthright.live"
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
async def vendor_token() -> str:
    return await _login(VENDOR_EMAIL)


@pytest_asyncio.fixture
async def db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()


@pytest_asyncio.fixture
async def artist_profile(db):
    vendor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
    pid = f"test-artist-{uuid.uuid4().hex[:8]}"
    slug = f"feat-artist-{uuid.uuid4().hex[:8]}"
    await db.partner_profiles.insert_one({
        "id": pid, "user_id": vendor["id"], "partner_type": "artist",
        "status": "active", "public": True, "slug": slug,
        "display_name": "Statement Test Artist",
        "headline": "Painter of slow mornings",
        "bio": "I work in oils on raw linen and have been a painter for fifteen years. "
               "My practice centers on patience. I paint each morning before the noise of the day. "
               "Looking is the first act of love.",
        "photo_url": None, "location": "Santa Cruz",
        "approved_at": "2026-05-31T00:00:00+00:00", "approved_by": "test",
        "created_at": "2026-05-31T00:00:00+00:00", "updated_at": "2026-05-31T00:00:00+00:00",
    })
    await db.gallery_spaces.insert_one({
        "id": uuid.uuid4().hex,
        "user_id": vendor["id"],
        "statement": "I paint mornings on the bluffs above town. "
                     "Slow looking is its own form of devotion. "
                     "Each canvas asks me to stay longer than I want to.",
        "layout": "single-wall", "accent_color": "flame",
        "created_at": "2026-05-31T00:00:00+00:00",
        "updated_at": "2026-05-31T00:00:00+00:00",
    })
    yield {"slug": slug, "id": pid, "user_id": vendor["id"]}
    await db.partner_profiles.delete_one({"id": pid})
    await db.featured_artist_slots.delete_many({"artist_slug": slug})
    await db.featured_nominations.delete_many({"artist_slug": slug})
    await db.gallery_spaces.delete_one({"user_id": vendor["id"]})


# ============ Statement position cycle ============
def test_statement_position_cycle():
    from routers.gallery import _statement_position_for_index, STATEMENT_POSITIONS
    # First five indices map to all five distinct positions in order
    assert [_statement_position_for_index(i) for i in range(5)] == list(STATEMENT_POSITIONS)
    # Index 5 wraps back to the first
    assert _statement_position_for_index(5) == STATEMENT_POSITIONS[0]
    # Adjacent indices never share a position
    for i in range(20):
        assert _statement_position_for_index(i) != _statement_position_for_index(i + 1)


@pytest.mark.asyncio
async def test_statement_position_locked_on_first_active_view(admin_token, vendor_token, artist_profile, db):
    """When a slot becomes active and the public endpoint reads it, position is
    assigned + persisted + never changes."""
    today = datetime.now(timezone.utc).date()
    starts = (today - timedelta(days=1)).isoformat()
    ends = (today + timedelta(days=14)).isoformat()
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": starts, "ends_at": ends,
            "period_label": "Position Test", "source": "editorial",
            "editorial_reason": "test position lock",
        })
        slot_id = r.json()["id"]
    # Artist accepts
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        await c.post(f"/gallery/me/featured/{slot_id}/accept", json={
            "signature_statement": "Slow looking is its own devotion.",
            "signature_statement_source": "freeform",
        })
    # First public read locks the position
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get(f"/gallery/{artist_profile['slug']}")
        feat = r.json()["featured"]
        assert feat["statement_position"] in {"tl", "tr", "bl", "br", "cb"}
        assert feat["statement_position_locked_at"]
        position_first = feat["statement_position"]
        locked_at_first = feat["statement_position_locked_at"]
    # Second read does NOT change the position or the timestamp
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get(f"/gallery/{artist_profile['slug']}")
        feat = r.json()["featured"]
        assert feat["statement_position"] == position_first
        assert feat["statement_position_locked_at"] == locked_at_first


# ============ Statement options ============
@pytest.mark.asyncio
async def test_statement_options_returns_all_five(admin_token, vendor_token, artist_profile, db):
    """All 5 option keys returned, with 180-char cap surfaced."""
    today = datetime.now(timezone.utc).date()
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": (today + timedelta(days=30)).isoformat(),
            "ends_at": (today + timedelta(days=60)).isoformat(),
            "period_label": "Options Test", "source": "editorial",
            "editorial_reason": "test",
        })
        sid = r.json()["id"]
    # Seed a few nominations so quote options have content
    await db.featured_nominations.insert_many([
        {"id": uuid.uuid4().hex,
         "artist_slug": artist_profile["slug"],
         "artist_user_id": artist_profile["user_id"],
         "nominator_user_id": f"u1-{uuid.uuid4().hex[:6]}",
         "nominator_name": "Quiet Visitor",
         "reason": "Her mornings paintings ask me to stop and look longer than I'm used to.",
         "weight": 1.0, "trust_flags": [],
         "period_target": "2026-12", "rolled_forward_from": None,
         "created_at": "2026-05-31T00:00:00+00:00"},
        {"id": uuid.uuid4().hex,
         "artist_slug": artist_profile["slug"],
         "artist_user_id": artist_profile["user_id"],
         "nominator_user_id": f"u2-{uuid.uuid4().hex[:6]}",
         "nominator_name": "Open Studio Neighbor",
         "reason": "x" * 200,  # over the 180-char cap on purpose
         "weight": 1.0, "trust_flags": [],
         "period_target": "2026-12", "rolled_forward_from": None,
         "created_at": "2026-05-31T00:00:00+00:00"},
    ])
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        r = await c.get(f"/gallery/me/featured/{sid}/statement-options")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["max_length"] == 180
        for k in ("freeform", "ai_summary", "nomination_quotes", "own_statement", "blank"):
            assert k in body
        # Own-statement extraction picked up sentence(s) from the seeded gallery_space
        own_texts = [s["text"] for s in body["own_statement"]]
        assert any("Slow looking" in t for t in own_texts) or any("mornings" in t.lower() for t in own_texts)
        # Nomination quotes include both — one fits and one doesn't
        quote_fits = [q["fits"] for q in body["nomination_quotes"]]
        assert True in quote_fits
        assert False in quote_fits


@pytest.mark.asyncio
async def test_statement_options_requires_owner(admin_token, artist_profile, db):
    """A non-owner cannot read another artist's statement-options."""
    today = datetime.now(timezone.utc).date()
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": (today + timedelta(days=30)).isoformat(),
            "ends_at": (today + timedelta(days=60)).isoformat(),
            "period_label": "Owner Test", "source": "editorial",
            "editorial_reason": "test",
        })
        sid = r.json()["id"]
        # Admin is NOT the artist owner here — endpoint scopes by artist_user_id
        r = await c.get(f"/gallery/me/featured/{sid}/statement-options")
        assert r.status_code in (403, 404)


# ============ Statement length cap ============
@pytest.mark.asyncio
async def test_signature_statement_max_180(admin_token, vendor_token, artist_profile, db):
    today = datetime.now(timezone.utc).date()
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": (today + timedelta(days=30)).isoformat(),
            "ends_at": (today + timedelta(days=60)).isoformat(),
            "period_label": "Length Test", "source": "editorial",
            "editorial_reason": "test",
        })
        sid = r.json()["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        r = await c.post(f"/gallery/me/featured/{sid}/accept", json={
            "signature_statement": "x" * 181,  # one over the cap
        })
        assert r.status_code == 422
        r = await c.post(f"/gallery/me/featured/{sid}/accept", json={
            "signature_statement": "x" * 180,
            "signature_statement_source": "freeform",
        })
        assert r.status_code == 200, r.text
        slot = r.json()
        assert slot["signature_statement_source"] == "freeform"


# ============ Adjacent positions differ across same-month lineup ============
@pytest.mark.asyncio
async def test_adjacent_slots_get_different_positions(admin_token, vendor_token, artist_profile, db):
    """If three artists share a month, their locked statement_position values
    should all differ (cycle of 5)."""
    today = datetime.now(timezone.utc).date()
    starts = (today - timedelta(days=1)).isoformat()
    ends = (today + timedelta(days=14)).isoformat()
    # Reuse the existing artist as one slot; create 2 more synthetic artist profiles
    extra_user_ids: list[str] = []
    extra_slugs: list[str] = []
    extra_pids: list[str] = []
    extra_slot_ids: list[str] = []
    try:
        for i in range(2):
            uid = f"extra-art-user-{uuid.uuid4().hex[:8]}"
            slug = f"extra-art-{uuid.uuid4().hex[:8]}"
            pid = f"extra-art-pp-{uuid.uuid4().hex[:8]}"
            await db.users.insert_one({
                "id": uid, "email": f"{uid}@birthright.test", "first_name": f"X{i}",
                "last_name": "Artist", "role": "user",
                "created_at": "2020-01-01T00:00:00+00:00",
            })
            await db.partner_profiles.insert_one({
                "id": pid, "user_id": uid, "partner_type": "artist",
                "status": "active", "public": True, "slug": slug,
                "display_name": f"Extra Artist {i}", "headline": "Test",
                "bio": "x" * 80, "approved_at": "2026-05-31T00:00:00+00:00",
                "approved_by": "test", "created_at": "2026-05-31T00:00:00+00:00",
                "updated_at": "2026-05-31T00:00:00+00:00",
            })
            extra_user_ids.append(uid)
            extra_slugs.append(slug)
            extra_pids.append(pid)

        # Schedule + accept all three slots in the same active month
        all_slugs = [artist_profile["slug"]] + extra_slugs
        all_users = [artist_profile["user_id"]] + extra_user_ids
        for slug, uid in zip(all_slugs, all_users):
            sid = uuid.uuid4().hex
            await db.featured_artist_slots.insert_one({
                "id": sid, "artist_user_id": uid, "artist_slug": slug,
                "artist_display_name": slug,
                "starts_at": starts, "ends_at": ends,
                "period_label": "Multi", "source": "editorial",
                "editorial_reason": "test",
                "status": "accepted",
                "signature_statement": "Test statement",
                "created_at": today.isoformat(),
            })
            extra_slot_ids.append(sid)

        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
            r = await c.get("/gallery/featured/pipeline")
            body = r.json()
            positions = [s.get("statement_position") for s in body["current_month"]["slots"]
                         if s["artist_slug"] in all_slugs]
            assert len(positions) == 3
            assert len(set(positions)) == 3, f"All three should differ, got {positions}"
    finally:
        for sid in extra_slot_ids:
            await db.featured_artist_slots.delete_one({"id": sid})
        for pid in extra_pids:
            await db.partner_profiles.delete_one({"id": pid})
        for uid in extra_user_ids:
            await db.users.delete_one({"id": uid})
