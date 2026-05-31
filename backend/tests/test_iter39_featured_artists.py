"""Backend tests for Featured Artists — monthly cadence, lifecycle, mini-gallery
curation, anti-gaming, pipeline visibility."""
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
VENDOR_EMAIL = "demo@birthright.org"
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
    """Demo user gets an Artist profile; cleaned up after."""
    vendor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
    pid = f"test-artist-{uuid.uuid4().hex[:8]}"
    slug = f"feat-artist-{uuid.uuid4().hex[:8]}"
    await db.partner_profiles.insert_one({
        "id": pid, "user_id": vendor["id"], "partner_type": "artist",
        "status": "active", "public": True, "slug": slug,
        "display_name": "Featured Test Artist", "headline": "Plein-air oils",
        "bio": "x" * 80, "photo_url": None, "location": "Santa Cruz",
        "approved_at": "2026-05-31T00:00:00+00:00", "approved_by": "test",
        "created_at": "2026-05-31T00:00:00+00:00", "updated_at": "2026-05-31T00:00:00+00:00",
    })
    yield {"slug": slug, "id": pid, "user_id": vendor["id"]}
    await db.partner_profiles.delete_one({"id": pid})
    await db.featured_artist_slots.delete_many({"artist_slug": slug})
    await db.featured_nominations.delete_many({"artist_slug": slug})
    await db.gallery_spaces.delete_one({"user_id": vendor["id"]})


# ============ Pure helpers ============
def test_month_label():
    from routers.gallery import _month_label, _next_month_label
    assert _month_label("2026-08-14") == "2026-08"
    assert _next_month_label("2026-12") == "2027-01"
    assert _next_month_label("2026-06") == "2026-07"


def test_human_month_label():
    from routers.gallery import _human_month_label
    assert _human_month_label("2026-08-01") == "August 2026"


# ============ Nomination basics ============
@pytest.mark.asyncio
async def test_nominate_basic(vendor_token, artist_profile, db):
    """User nominates another artist; record stored with weight + period."""
    # Create a SEPARATE user as the artist's actual owner so the vendor (different user) can nominate
    artist_owner = f"other-artist-owner-{uuid.uuid4().hex[:8]}"
    await db.users.insert_one({
        "id": artist_owner, "email": f"{artist_owner}@birthright.test",
        "first_name": "Other", "last_name": "Artist", "role": "user",
        "created_at": "2020-01-01T00:00:00+00:00",
    })
    await db.partner_profiles.update_one({"id": artist_profile["id"]}, {"$set": {"user_id": artist_owner}})
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {vendor_token}"}) as c:
            r = await c.post("/gallery/featured/nominate", json={
                "artist_slug": artist_profile["slug"],
                "reason": "Their plein-air work invited me to slow down for an afternoon",
            })
            assert r.status_code == 200, r.text
            body = r.json()
            # Public response strips trust signals
            assert "weight" not in body
            assert "trust_flags" not in body
            assert body["period_target"]  # YYYY-MM
            assert len(body["period_target"]) == 7
    finally:
        await db.users.delete_one({"id": artist_owner})


@pytest.mark.asyncio
async def test_self_nomination_blocked(vendor_token, artist_profile, db):
    """Artist cannot nominate themselves (block by user_id)."""
    # artist_profile.user_id IS the demo vendor user
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        r = await c.post("/gallery/featured/nominate", json={
            "artist_slug": artist_profile["slug"], "reason": "x" * 30,
        })
        assert r.status_code == 400
        assert "themselves" in r.text.lower() or "self" in r.text.lower()


@pytest.mark.asyncio
async def test_nomination_reason_length(vendor_token, artist_profile, db):
    """150-char ceiling, 10-char floor."""
    artist_owner = f"len-owner-{uuid.uuid4().hex[:8]}"
    await db.users.insert_one({
        "id": artist_owner, "email": f"{artist_owner}@birthright.test",
        "first_name": "Owner", "last_name": "Artist", "role": "user",
        "created_at": "2020-01-01T00:00:00+00:00",
    })
    await db.partner_profiles.update_one({"id": artist_profile["id"]}, {"$set": {"user_id": artist_owner}})
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {vendor_token}"}) as c:
            r = await c.post("/gallery/featured/nominate", json={
                "artist_slug": artist_profile["slug"], "reason": "short",
            })
            assert r.status_code == 422
            r = await c.post("/gallery/featured/nominate", json={
                "artist_slug": artist_profile["slug"], "reason": "x" * 151,
            })
            assert r.status_code == 422
    finally:
        await db.users.delete_one({"id": artist_owner})


# ============ Admin shortlist & scheduling ============
@pytest.mark.asyncio
async def test_shortlist_uses_weighted_score(admin_token, artist_profile, db):
    """Weighted aggregation works; admins see weights + flags."""
    # Inject two nominations with different weights for this month
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    month = today[:7]
    await db.featured_nominations.insert_many([
        {"id": uuid.uuid4().hex, "artist_slug": artist_profile["slug"],
         "nominator_user_id": "u1", "nominator_name": "User 1",
         "reason": "full weight", "period_target": month,
         "weight": 1.0, "trust_flags": [], "rolled_forward_from": None,
         "created_at": today + "T00:00:00+00:00"},
        {"id": uuid.uuid4().hex, "artist_slug": artist_profile["slug"],
         "nominator_user_id": "u2", "nominator_name": "User 2",
         "reason": "discount", "period_target": month,
         "weight": 0.25, "trust_flags": ["new_account_under_30d_no_engagement"],
         "rolled_forward_from": None,
         "created_at": today + "T00:00:00+00:00"},
    ])
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.get("/gallery/admin/featured/shortlist")
        assert r.status_code == 200, r.text
        row = next(x for x in r.json()["shortlist"] if x["artist_slug"] == artist_profile["slug"])
        assert row["raw_count"] == 2
        assert row["weighted_score"] == 1.25
        assert row["flag_count"] == 1
        assert row["eligible_for_period"] is True


@pytest.mark.asyncio
async def test_admin_schedule_lifecycle_proposed(admin_token, artist_profile, db):
    """Scheduling creates a slot in 'proposed' state, NOT publicly visible yet."""
    starts = (datetime.now(timezone.utc).date() + timedelta(days=45)).isoformat()
    ends = (datetime.now(timezone.utc).date() + timedelta(days=75)).isoformat()
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": starts, "ends_at": ends, "period_label": "Test Month",
            "source": "editorial",
            "editorial_reason": "Founding artist for the test",
        })
        assert r.status_code == 200, r.text
        slot = r.json()
        assert slot["status"] == "proposed"
        assert slot["signature_image_url"] is None
        assert slot["featured_work_ids"] == []
    # Public endpoint does NOT show it yet
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/gallery/featured?include_upcoming=true")
        body = r.json()
        assert not any(s.get("id") == slot["id"] for s in body["upcoming"] + body["current"])


@pytest.mark.asyncio
async def test_cooling_off_blocks_re_feature(admin_token, artist_profile, db):
    """Artist featured 2 months ago can't be re-scheduled within 3-month cooling-off."""
    today = datetime.now(timezone.utc).date()
    # Insert a past slot that ended 30 days ago (within cooling-off)
    await db.featured_artist_slots.insert_one({
        "id": uuid.uuid4().hex, "artist_user_id": artist_profile["user_id"],
        "artist_slug": artist_profile["slug"], "artist_display_name": "Past",
        "starts_at": (today - timedelta(days=60)).isoformat(),
        "ends_at": (today - timedelta(days=30)).isoformat(),
        "period_label": "Old month", "source": "editorial",
        "status": "accepted", "created_by": "admin", "created_at": today.isoformat(),
    })
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": (today + timedelta(days=30)).isoformat(),
            "ends_at": (today + timedelta(days=60)).isoformat(),
            "period_label": "Too soon", "source": "editorial",
            "editorial_reason": "Trying to re-feature in cooling-off",
        })
        assert r.status_code == 400
        assert "cooling" in r.text.lower()


@pytest.mark.asyncio
async def test_monthly_cap_enforced(admin_token, artist_profile, db):
    """Cap of 5 slots per month enforced. Use a far-future month for safe seed."""
    today = datetime.now(timezone.utc).date()
    far = today + timedelta(days=365)
    month_str = far.strftime("%Y-%m")
    # Insert 5 dummy active slots in that month
    fillers = []
    for i in range(5):
        fillers.append({
            "id": uuid.uuid4().hex,
            "artist_user_id": f"u{i}", "artist_slug": f"filler-{uuid.uuid4().hex[:6]}",
            "artist_display_name": f"F{i}",
            "starts_at": f"{month_str}-0{i+1}",
            "ends_at": f"{month_str}-2{i+5}",
            "period_label": f"F{i}", "source": "editorial",
            "status": "accepted", "created_at": today.isoformat(),
        })
    await db.featured_artist_slots.insert_many(fillers)
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {admin_token}"}) as c:
            r = await c.post("/gallery/admin/featured", json={
                "artist_slug": artist_profile["slug"],
                "starts_at": f"{month_str}-15", "ends_at": f"{month_str}-25",
                "period_label": "Sixth", "source": "editorial",
                "editorial_reason": "should be blocked by cap",
            })
            assert r.status_code == 400
            assert "cap" in r.text.lower() or "already" in r.text.lower()
    finally:
        await db.featured_artist_slots.delete_many({"id": {"$in": [f["id"] for f in fillers]}})


# ============ Artist lifecycle (accept / decline / curate / copy) ============
@pytest.mark.asyncio
async def test_artist_accept_with_curation(vendor_token, admin_token, artist_profile, db):
    """Artist accepts → status flips to 'accepted' → mini-gallery fields persist."""
    today = datetime.now(timezone.utc).date()
    starts = (today + timedelta(days=30)).isoformat()
    ends = (today + timedelta(days=60)).isoformat()
    # Admin schedules
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": starts, "ends_at": ends, "period_label": "Curation Test",
            "source": "editorial", "editorial_reason": "test",
        })
        slot_id = r.json()["id"]
    # Artist accepts with curation
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        r = await c.post(f"/gallery/me/featured/{slot_id}/accept", json={
            "signature_image_url": "https://example.com/hero.jpg",
            "signature_statement": "Slow down. Look closer.",
            "statement": "I paint mornings on the bluffs above town.",
            "layout": "two-column",
            "accent_color": "moss",
            "presentation_note": "Open studio every Sunday in June. Come by.",
        })
        assert r.status_code == 200, r.text
        slot = r.json()
        assert slot["status"] == "accepted"
        assert slot["signature_statement"] == "Slow down. Look closer."
        assert slot["layout"] == "two-column"
        assert slot["accent_color"] == "moss"
        # featured_work_ids defaulted (probably empty since this artist has no works)
        assert isinstance(slot["featured_work_ids"], list)

        # Edit curation later
        r = await c.put(f"/gallery/me/featured/{slot_id}/curation", json={
            "signature_statement": "Slow down. Look closer. Stay awhile.",
        })
        assert r.status_code == 200
        assert r.json()["signature_statement"] == "Slow down. Look closer. Stay awhile."


@pytest.mark.asyncio
async def test_artist_decline(vendor_token, admin_token, artist_profile, db):
    """Decline path."""
    today = datetime.now(timezone.utc).date()
    starts = (today + timedelta(days=30)).isoformat()
    ends = (today + timedelta(days=60)).isoformat()
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": starts, "ends_at": ends, "period_label": "Decline Test",
            "source": "editorial", "editorial_reason": "test",
        })
        slot_id = r.json()["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        r = await c.post(f"/gallery/me/featured/{slot_id}/decline")
        assert r.status_code == 200
    slot = await db.featured_artist_slots.find_one({"id": slot_id}, {"_id": 0})
    assert slot["status"] == "declined"
    # Already-declined can't be re-declined
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        r = await c.post(f"/gallery/me/featured/{slot_id}/decline")
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_copy_curation_to_gallery(vendor_token, admin_token, artist_profile, db):
    """copy-to-gallery promotes featured curation back to regular gallery_space."""
    today = datetime.now(timezone.utc).date()
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": (today + timedelta(days=30)).isoformat(),
            "ends_at": (today + timedelta(days=60)).isoformat(),
            "period_label": "Copy Test", "source": "editorial", "editorial_reason": "test",
        })
        sid = r.json()["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        await c.post(f"/gallery/me/featured/{sid}/accept", json={
            "signature_image_url": "https://example.com/hero.jpg",
            "statement": "My month's statement",
            "layout": "salon-hang", "accent_color": "indigo",
            "open_studio_text": "Sundays in June",
        })
        r = await c.post(f"/gallery/me/featured/{sid}/copy-to-gallery")
        assert r.status_code == 200, r.text
        space = r.json()
        assert space["hero_image_url"] == "https://example.com/hero.jpg"
        assert space["statement"] == "My month's statement"
        assert space["layout"] == "salon-hang"
        assert space["accent_color"] == "indigo"
        assert space["open_studio_text"] == "Sundays in June"


@pytest.mark.asyncio
async def test_copy_curation_from_gallery(vendor_token, admin_token, artist_profile, db):
    """copy-from-gallery resets the slot to current gallery defaults."""
    today = datetime.now(timezone.utc).date()
    # Set up gallery_space with values
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        await c.put("/gallery/me/space", json={
            "statement": "Regular statement",
            "hero_image_url": "https://example.com/regular.jpg",
            "layout": "single-wall", "accent_color": "ochre",
        })
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": (today + timedelta(days=30)).isoformat(),
            "ends_at": (today + timedelta(days=60)).isoformat(),
            "period_label": "Reset Test", "source": "editorial", "editorial_reason": "test",
        })
        sid = r.json()["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        # Customize then reset
        await c.post(f"/gallery/me/featured/{sid}/accept", json={
            "statement": "Something different", "accent_color": "moss",
        })
        r = await c.post(f"/gallery/me/featured/{sid}/copy-from-gallery")
        assert r.status_code == 200, r.text
        slot = r.json()
        assert slot["statement"] == "Regular statement"
        assert slot["accent_color"] == "ochre"
        assert slot["signature_image_url"] == "https://example.com/regular.jpg"


# ============ Roll-forward ============
@pytest.mark.asyncio
async def test_roll_forward_unfeatured_nominations(admin_token, artist_profile, db):
    """Previous-month nominations for non-featured artists roll to next month at 50% weight."""
    today = datetime.now(timezone.utc).date()
    # Compute prev month label
    prev = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    nid = uuid.uuid4().hex
    await db.featured_nominations.insert_one({
        "id": nid, "artist_slug": artist_profile["slug"],
        "nominator_user_id": "u-roll", "nominator_name": "Roll User",
        "reason": "Loved their oils — should be featured",
        "period_target": prev, "weight": 1.0, "trust_flags": [],
        "rolled_forward_from": None,
        "created_at": today.isoformat() + "T00:00:00+00:00",
    })
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {admin_token}"}) as c:
            r = await c.post("/gallery/admin/featured/roll-forward")
            assert r.status_code == 200, r.text
            assert r.json()["rolled"] >= 1
            # Idempotent: second call rolls 0 (the just-rolled record is detected)
            r2 = await c.post("/gallery/admin/featured/roll-forward")
            assert r2.json()["rolled"] == 0 or r2.json()["rolled"] < r.json()["rolled"]

        rolled = await db.featured_nominations.find_one(
            {"rolled_forward_from": nid}, {"_id": 0},
        )
        assert rolled is not None
        assert rolled["weight"] == 0.5
        assert "rolled_forward" in rolled["trust_flags"]
    finally:
        await db.featured_nominations.delete_many({"rolled_forward_from": nid})
        await db.featured_nominations.delete_one({"id": nid})


# ============ Public pipeline visibility ============
@pytest.mark.asyncio
async def test_public_pipeline_returns_three_horizons():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/gallery/featured/pipeline")
        assert r.status_code == 200
        body = r.json()
        for k in ("current_month", "next_month", "nominations_open", "how_it_works"):
            assert k in body
        # Critical: nominations_open NEVER returns per-artist counts
        assert "distinct_artists_nominated" in body["nominations_open"]
        assert "total_nominations" in body["nominations_open"]
        no_perartist_in_open = "shortlist" not in body["nominations_open"]
        assert no_perartist_in_open
        # how_it_works exposes the rules transparently
        rules = body["how_it_works"]
        assert rules["cooling_off_months"] == 3
        assert rules["min_per_month"] == 3
        assert rules["max_per_month"] == 5
        assert rules["roll_forward_weight"] == 0.5


@pytest.mark.asyncio
async def test_pipeline_next_month_shows_only_accepted_curation(vendor_token, admin_token, artist_profile, db):
    """For next month, proposed slots show preparation_status=preparing; accepted
    slots show signature_statement + signature_image."""
    today = datetime.now(timezone.utc).date()
    next_month_start = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    next_month_end = (next_month_start + timedelta(days=28))
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": next_month_start.isoformat(),
            "ends_at": next_month_end.isoformat(),
            "period_label": "Next month test", "source": "editorial",
            "editorial_reason": "test",
        })
        sid = r.json()["id"]

    # While proposed, pipeline shows the artist with preparing status
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/gallery/featured/pipeline")
        nm = r.json()["next_month"]
        slot = next((s for s in nm["slots"] if s["artist_slug"] == artist_profile["slug"]), None)
        assert slot is not None
        assert slot["preparation_status"] == "preparing"
        assert slot["signature_statement"] is None  # hidden until accepted

    # After accept with signature_statement
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        await c.post(f"/gallery/me/featured/{sid}/accept", json={
            "signature_statement": "Slow down with me",
            "signature_image_url": "https://example.com/hero.jpg",
        })

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/gallery/featured/pipeline")
        nm = r.json()["next_month"]
        slot = next(s for s in nm["slots"] if s["artist_slug"] == artist_profile["slug"])
        assert slot["preparation_status"] == "accepted"
        assert slot["signature_statement"] == "Slow down with me"
        assert slot["signature_image_url"] == "https://example.com/hero.jpg"


@pytest.mark.asyncio
async def test_public_artist_page_merges_featured_curation(vendor_token, admin_token, artist_profile, db):
    """During an active featured slot, /gallery/{slug} merges the slot curation
    into the returned space + reorders works + exposes nomination_quotes."""
    today = datetime.now(timezone.utc).date()
    starts = (today - timedelta(days=1)).isoformat()  # active right now
    ends = (today + timedelta(days=14)).isoformat()
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/gallery/admin/featured", json={
            "artist_slug": artist_profile["slug"],
            "starts_at": starts, "ends_at": ends,
            "period_label": "Live now", "source": "editorial",
            "editorial_reason": "live merge test",
        })
        sid = r.json()["id"]
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        await c.post(f"/gallery/me/featured/{sid}/accept", json={
            "signature_image_url": "https://example.com/feat-hero.jpg",
            "signature_statement": "Live this month",
            "statement": "I'm featured right now — here's my month",
            "accent_color": "river",
        })
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get(f"/gallery/{artist_profile['slug']}")
        body = r.json()
        assert body["featured"] is not None
        assert body["featured"]["status"] in ("accepted", "active")
        # Slot overrides space
        assert body["space"]["hero_image_url"] == "https://example.com/feat-hero.jpg"
        assert body["space"]["statement"] == "I'm featured right now — here's my month"
        assert body["space"]["accent_color"] == "river"
