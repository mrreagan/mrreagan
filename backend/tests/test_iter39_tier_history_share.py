"""Backend tests for the tier-history audit timeline + shareable tier
achievement assets (P3 iteration).

  - log_tier_change records initial baseline only once
  - log_tier_change records UP / DOWN transitions with direction
  - GET /partner/artist/tier-table still serves
  - GET /share/artist/{slug}/tier-card.svg returns SVG with expected content
  - GET /share/artist/{slug}/tier-card.png returns a real PNG
"""
from __future__ import annotations

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

from utils.artist_tier import log_tier_change  # noqa: E402
from utils.tier_share_card import render_tier_share_png, render_tier_share_svg  # noqa: E402

API_BASE = "http://localhost:8001/api"


@pytest_asyncio.fixture
async def db_handle():
    """Create a *fresh* motor client per test so pytest-asyncio's
    per-test event loop owns the connection. Re-using the module-level
    singleton from `database.py` produces 'Event loop is closed' when
    a second test issues a query."""
    import os
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    yield db
    client.close()


@pytest_asyncio.fixture
async def artist_user_id(db_handle):
    db = db_handle
    aid = f"test-artist-{uuid.uuid4().hex[:8]}"
    yield aid
    await db.artist_tier_history.delete_many({"user_id": aid})


# ---------- log_tier_change ---------------------------------------------
@pytest.mark.asyncio
async def test_log_tier_change_initial_then_up(db_handle, artist_user_id):
    """First call inserts an `initial` row that does NOT count as a
    real transition; the second call (with a higher tier) records an
    UP transition with direction='up'."""
    db = db_handle
    aid = artist_user_id

    # Initial — should insert baseline but return None (no celebration).
    rv = await log_tier_change(db, aid, basis=0.0, tier_key="emerging")
    assert rv is None
    rows = await db.artist_tier_history.find(
        {"user_id": aid}, {"_id": 0},
    ).to_list(10)
    assert len(rows) == 1
    assert rows[0]["direction"] == "initial"
    assert rows[0]["share_dismissed"] is True

    # Calling again with the same tier — nothing inserted.
    rv2 = await log_tier_change(db, aid, basis=2_500.0, tier_key="emerging")
    assert rv2 is None
    assert await db.artist_tier_history.count_documents({"user_id": aid}) == 1

    # Crossing into sustaining — records UP, returns the doc.
    rv3 = await log_tier_change(db, aid, basis=6_000.0, tier_key="sustaining")
    assert rv3 is not None
    assert rv3["direction"] == "up"
    assert rv3["from_tier_key"] == "emerging"
    assert rv3["to_tier_key"] == "sustaining"
    assert rv3["share_dismissed"] is False
    assert await db.artist_tier_history.count_documents({"user_id": aid}) == 2


@pytest.mark.asyncio
async def test_log_tier_change_down(db_handle, artist_user_id):
    """Tier going down records direction='down' (no celebration banner)."""
    db = db_handle
    aid = artist_user_id
    await log_tier_change(db, aid, basis=0.0, tier_key="established")
    rv = await log_tier_change(db, aid, basis=8_000.0, tier_key="sustaining")
    assert rv["direction"] == "down"
    assert rv["from_tier_key"] == "established"
    assert rv["to_tier_key"] == "sustaining"


# ---------- Share card renderers ----------------------------------------
def test_tier_share_card_png_is_real_png():
    b = render_tier_share_png(
        tier_label="Sustaining",
        tier_icon="🌿",
        tier_key="sustaining",
        artist_name="Demo Artist",
        referral_url="https://birthright.live/api/r/ABCD?dest=/partners/demo",
    )
    # PNG magic bytes.
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
    # Reasonable size for a 1200×630 quasi-vector composition.
    assert 5_000 < len(b) < 5_000_000


def test_tier_share_card_svg_contains_text():
    s = render_tier_share_svg(
        tier_label="Flourishing",
        tier_icon="🌟",
        tier_key="flourishing",
        artist_name="Toby Greene",
        referral_url="https://birthright.live/api/r/XYZ?dest=/partners/toby",
    )
    assert "<svg" in s
    assert "Flourishing" in s
    assert "Toby Greene" in s
    assert "birthright.live" in s


# ---------- Live HTTP — share card endpoints ----------------------------
@pytest.mark.asyncio
async def test_share_card_png_via_http(db_handle):
    """If at least one active public artist exists, the PNG endpoint
    must return a 200 with content-type image/png. Otherwise skip."""
    db = db_handle
    prof = await db.partner_profiles.find_one(
        {"partner_type": "artist", "status": "active", "public": True},
        {"_id": 0, "slug": 1},
    )
    if not prof:
        pytest.skip("No active public artist profile to share-test.")
    slug = prof["slug"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15.0) as c:
        r = await c.get(f"/share/artist/{slug}/tier-card.png")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "image/png"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"

        r2 = await c.get(f"/share/artist/{slug}/tier-card.svg")
        assert r2.status_code == 200
        assert r2.headers["content-type"].startswith("image/svg")
        assert "<svg" in r2.text


@pytest.mark.asyncio
async def test_share_card_png_missing_artist():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/share/artist/this-artist-does-not-exist/tier-card.png")
        assert r.status_code == 404
