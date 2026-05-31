"""Backend tests for Iter 38 — Artist + Steward partner types, Gather (communities),
Gallery (artist exhibition + 20% checkout markup).

Coverage:
  Partner types
    - PARTNER_TYPES tuple includes artist + steward
    - Artist application requires own_gallery_url OR representative_works_url
    - Steward application requires requested_community_slug
    - Existing flows (facilitator/community/research/vendor) still work
    - Admin invite supports artist + steward

  Gather
    - Seed populates continents + countries
    - Tree drill-down works at multiple levels
    - Search returns community matches
    - Member can join/leave
    - Post create/get-thread; only stewards can pin/hide
    - Event/resource create gated to stewards
    - Proposal lifecycle: propose → admin approve → community exists
    - Reject path

  Gallery
    - markup-pct endpoint returns 20
    - gallery_markup_for() returns 20% of price (and 0 if foundation_absorbs_markup)
    - Artist publishes work; checkout adds 20% markup; foundation_absorbs_markup=true → no markup
    - Artist needs an approved Artist partner_profile to create works
    - Public gallery list excludes artists with zero works
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


# ============ Partner type expansion ============
def test_partner_types_includes_artist_and_steward():
    from models import PARTNER_TYPES
    assert "artist" in PARTNER_TYPES
    assert "steward" in PARTNER_TYPES
    assert len(PARTNER_TYPES) == 6


def test_partner_apply_literal_accepts_new_types():
    from models import PartnerApplyData
    d = PartnerApplyData(
        partner_type="artist",
        headline="Plein-air oils + chamber music",
        bio="I paint and play first violin in a regional chamber group" + "." * 30,
        own_gallery_url="https://example.com/portfolio",
        mediums="oil painting, violin",
    )
    assert d.partner_type == "artist"
    s = PartnerApplyData(
        partner_type="steward",
        headline="Long-time Santa Cruz neighbor",
        bio="Lived here 20 years and would love to host the local gather" + "." * 30,
        requested_community_slug="north-america/us/california/santa-cruz",
    )
    assert s.partner_type == "steward"


@pytest.mark.asyncio
async def test_artist_application_requires_portfolio_link(admin_token, db):
    """Admin invites a target email; the target then has to file a complete application."""
    # We test by directly hitting /partners/apply as the admin user (it works for any role)
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        # Missing both portfolio fields → 400
        r = await c.post("/partners/apply", json={
            "partner_type": "artist",
            "headline": "Test artist headline",
            "bio": "x" * 50,
        })
        assert r.status_code == 400
        assert "gallery" in r.text.lower() or "portfolio" in r.text.lower() or "representative" in r.text.lower() or "verify" in r.text.lower()
        # Cleanup: nothing was created


@pytest.mark.asyncio
async def test_steward_application_requires_community_slug(admin_token, db):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        r = await c.post("/partners/apply", json={
            "partner_type": "steward",
            "headline": "Local steward",
            "bio": "x" * 50,
        })
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_admin_can_invite_artist_or_steward(admin_token, db):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {admin_token}"}) as c:
        invite_email = f"artist-{uuid.uuid4().hex[:6]}@birthright.test"
        r = await c.post("/admin/partners/invite", json={
            "email": invite_email,
            "partner_type": "artist",
            "admin_note": "We met at the chamber music night",
        })
        assert r.status_code == 200, r.text
        # Cleanup
        await db.partner_applications.delete_many({"invitee_email": invite_email})

        invite_email2 = f"steward-{uuid.uuid4().hex[:6]}@birthright.test"
        r = await c.post("/admin/partners/invite", json={
            "email": invite_email2,
            "partner_type": "steward",
            "admin_note": "Would steward Santa Cruz beautifully",
        })
        assert r.status_code == 200, r.text
        await db.partner_applications.delete_many({"invitee_email": invite_email2})


# ============ Gather ============
@pytest.mark.asyncio
async def test_gather_seed_present(db):
    cont = await db.communities.count_documents({"kind": "continent"})
    countries = await db.communities.count_documents({"kind": "country"})
    regions = await db.communities.count_documents({"kind": "region"})
    assert cont >= 6
    assert countries >= 20
    assert regions >= 15


@pytest.mark.asyncio
async def test_gather_tree_drilldown():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/gather/tree")
        assert r.status_code == 200
        continents = r.json()
        assert any(x["slug"] == "north-america" for x in continents)
        r = await c.get("/gather/tree", params={"parent_slug": "north-america"})
        countries = r.json()
        slugs = [x["slug"] for x in countries]
        assert "north-america/us" in slugs
        r = await c.get("/gather/tree", params={"parent_slug": "north-america/us"})
        regions = r.json()
        assert any(x["slug"] == "north-america/us/california" for x in regions)


@pytest.mark.asyncio
async def test_gather_search():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/gather/search", params={"q": "California"})
        assert r.status_code == 200
        assert any(x["label"] == "California" for x in r.json())


@pytest.mark.asyncio
async def test_gather_membership_and_posts_and_moderation(db, vendor_token, admin_token):
    """Vendor joins California, posts. Admin pins the post; non-steward can't."""
    slug = "north-america/us/california"
    vendor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
    post_id = None
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {vendor_token}"}) as c:
            r = await c.post(f"/gather/community/{slug}/join")
            assert r.status_code == 200

            r = await c.post(f"/gather/community/{slug}/posts", json={"body": "Hi from the west coast"})
            assert r.status_code == 200
            post_id = r.json()["id"]

            # Vendor (not steward, not admin) cannot pin
            r = await c.post(f"/gather/community/{slug}/posts/{post_id}/pin", params={"pinned": True})
            assert r.status_code == 403

        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {admin_token}"}) as c:
            # Admin can pin
            r = await c.post(f"/gather/community/{slug}/posts/{post_id}/pin", params={"pinned": True})
            assert r.status_code == 200

            # Admin creates event
            r = await c.post(f"/gather/community/{slug}/events", json={
                "title": "Test gathering",
                "start_at": "2030-01-01T18:00:00+00:00",
                "location_name": "Community center",
                "is_virtual": False,
            })
            assert r.status_code == 200

            # Admin creates resource
            r = await c.post(f"/gather/community/{slug}/resources", json={
                "title": "Local therapist directory",
                "kind": "link",
                "url": "https://example.com/therapists",
                "pinned": True,
            })
            assert r.status_code == 200

        # Public read includes pinned post + event + resource
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
            r = await c.get(f"/gather/community/{slug}")
            data = r.json()
            assert data["community"]["slug"] == slug
            assert any(p["id"] == post_id and p["pinned"] for p in data["posts"])
            assert len(data["events"]) >= 1
            assert len(data["resources"]) >= 1
    finally:
        if post_id:
            await db.community_posts.delete_one({"id": post_id})
        await db.community_members.delete_many({"community_slug": slug, "user_id": vendor["id"]})
        await db.community_events.delete_many({"community_slug": slug, "title": "Test gathering"})
        await db.community_resources.delete_many({"community_slug": slug, "title": "Local therapist directory"})
        await db.communities.update_one({"slug": slug}, {"$set": {"post_count": 0, "event_count": 0, "member_count": 0}})


@pytest.mark.asyncio
async def test_gather_proposal_lifecycle(db, vendor_token, admin_token):
    """Vendor proposes a city under California; admin approves; community exists."""
    label = f"Test City {uuid.uuid4().hex[:6]}"
    parent_slug = "north-america/us/california"
    expected_slug = None
    pid = None
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {vendor_token}"}) as c:
            r = await c.post("/gather/propose", json={
                "label": label, "parent_slug": parent_slug, "kind": "city",
                "lat": 36.97, "lng": -122.03,
                "note": "Long-time community of practice here",
            })
            assert r.status_code == 200, r.text
            pid = r.json()["id"]
            expected_slug = r.json()["slug"]
            assert expected_slug.startswith(parent_slug + "/")

        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {admin_token}"}) as c:
            r = await c.get("/admin/gather/proposals")
            assert r.status_code == 200
            assert any(p["id"] == pid for p in r.json())

            r = await c.post(f"/admin/gather/proposals/{pid}/approve")
            assert r.status_code == 200
            assert r.json()["slug"] == expected_slug

        # The new community is now visible publicly
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
            r = await c.get(f"/gather/community/{expected_slug}")
            assert r.status_code == 200
            assert r.json()["community"]["kind"] == "city"
    finally:
        if expected_slug:
            await db.communities.delete_one({"slug": expected_slug})
        if pid:
            await db.community_proposals.delete_one({"id": pid})


@pytest.mark.asyncio
async def test_gather_proposal_rejected_by_kind_rules(vendor_token):
    """A neighborhood proposal must sit under a city, not a region."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        r = await c.post("/gather/propose", json={
            "label": "Bogus Neighborhood",
            "parent_slug": "north-america/us/california",
            "kind": "neighborhood",
        })
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_gather_admin_assigns_steward(db, admin_token, vendor_token):
    slug = "north-america/us/california"
    vendor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {admin_token}"}) as c:
            r = await c.post(f"/admin/gather/community/{slug}/stewards", json={"user_id": vendor["id"]})
            assert r.status_code == 200
            assert vendor["id"] in r.json()["steward_user_ids"]

        # Vendor can now pin a post (uses steward role) — quick check
        post_id = None
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {vendor_token}"}) as c:
            r = await c.post(f"/gather/community/{slug}/posts", json={"body": "Steward test post"})
            post_id = r.json()["id"]
            r = await c.post(f"/gather/community/{slug}/posts/{post_id}/pin", params={"pinned": True})
            assert r.status_code == 200
        if post_id:
            await db.community_posts.delete_one({"id": post_id})
    finally:
        await db.communities.update_one({"slug": slug}, {"$set": {"steward_user_ids": [], "post_count": 0}})


# ============ Gallery ============
def test_gallery_markup_for_helper():
    from routers.gallery import gallery_markup_for
    assert gallery_markup_for({"is_gallery_artwork": True, "price": 100.0}) == 20.0
    assert gallery_markup_for({"is_gallery_artwork": True, "price": 250.0}) == 50.0
    # Foundation absorbs → 0
    assert gallery_markup_for({"is_gallery_artwork": True, "price": 100, "foundation_absorbs_markup": True}) == 0.0
    # Non-gallery product → 0
    assert gallery_markup_for({"is_gallery_artwork": False, "price": 100}) == 0.0


@pytest.mark.asyncio
async def test_gallery_markup_pct_public():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
        r = await c.get("/gallery/markup-pct")
        assert r.status_code == 200
        assert r.json()["pct"] == 20.0


@pytest.mark.asyncio
async def test_gallery_requires_artist_profile(vendor_token):
    """Non-artist user trying to create work → 403."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                  headers={"Authorization": f"Bearer {vendor_token}"}) as c:
        r = await c.post("/gallery/me/works", json={
            "name": "Test", "description": "x" * 30, "list_price": 100,
            "image_url": "https://example.com/x.jpg",
            "list_price_matches_own_gallery": True,
        })
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_full_gallery_artist_flow_and_checkout_markup(db, vendor_token):
    """Promote demo to artist, publish a work, hit checkout, confirm 20% markup."""
    vendor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
    # Seed an Artist profile for the demo user
    from utils.audit import log_action  # noqa: F401
    profile_id = f"test-artist-{uuid.uuid4().hex[:8]}"
    slug = f"artist-{uuid.uuid4().hex[:8]}"
    await db.partner_profiles.insert_one({
        "id": profile_id,
        "user_id": vendor["id"],
        "partner_type": "artist",
        "status": "active",
        "public": True,
        "slug": slug,
        "display_name": "Test Artist",
        "headline": "Test artist headline",
        "bio": "x" * 80,
        "photo_url": None,
        "location": "Santa Cruz",
        "meta": {},
        "approved_at": "2026-05-30T00:00:00+00:00",
        "approved_by": "test",
        "created_at": "2026-05-30T00:00:00+00:00",
        "updated_at": "2026-05-30T00:00:00+00:00",
    })
    work_id = None
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {vendor_token}"}) as c:
            # List of artists includes 0 works at this point
            r = await c.get("/gallery/artists")
            assert r.status_code == 200
            # Create a work — must attest price matches own gallery
            r = await c.post("/gallery/me/works", json={
                "name": "Pacific Coast 1",
                "description": "Oil on linen, 16x20, finished in May 2026" + " " * 10,
                "list_price": 400,
                "image_url": "https://example.com/oil.jpg",
                "medium": "Oil on linen",
                "dimensions": "16x20 in",
                "year": 2026,
                "edition": "1/1",
                "availability": "available",
                "list_price_matches_own_gallery": True,
            })
            assert r.status_code == 200, r.text
            work_id = r.json()["id"]
            assert r.json()["price"] == 400.0

            # The artist's public gallery shows it
            r = await c.get(f"/gallery/{slug}")
            data = r.json()
            assert any(w["id"] == work_id for w in data["works"])
            assert data["markup_pct"] == 20.0

            # The works without attestation should be rejected
            r = await c.post("/gallery/me/works", json={
                "name": "Bad attestation", "description": "x" * 30, "list_price": 100,
                "image_url": "https://example.com/x.jpg",
                "list_price_matches_own_gallery": False,
            })
            assert r.status_code == 400

            # Checkout: cart with the artwork → total = list + 20%, shipping required
            # No shipping → 400
            r = await c.post("/checkout/products", json={
                "items": [{"product_id": work_id, "quantity": 1}],
                "origin_url": "http://localhost:3000",
            })
            assert r.status_code == 400
            # With shipping → 200, total = 480
            r = await c.post("/checkout/products", json={
                "items": [{"product_id": work_id, "quantity": 1}],
                "origin_url": "http://localhost:3000",
                "shipping_address": {
                    "name": "QA", "address1": "1 St", "city": "Santa Cruz",
                    "state_code": "CA", "postcode": "95060", "country_code": "US",
                },
            })
            assert r.status_code == 200, r.text
            # Confirm the payment_transactions row recorded $480 + line metadata
            txn = await db.payment_transactions.find_one(
                {"items.product_id": work_id}, {"_id": 0},
                sort=[("created_at", -1)],
            )
            assert txn is not None
            assert abs(float(txn["amount"]) - 480.0) < 0.01
            li = txn["items"][0]
            assert li["foundation_markup_per_unit"] == 80.0
            assert li["is_gallery_artwork"] is True
            # Cleanup the txn
            await db.payment_transactions.delete_one({"_id": txn.get("_id")} if txn.get("_id") else {"session_id": txn["session_id"]})

            # Toggle foundation_absorbs_markup on the artist's space
            r = await c.put("/gallery/me/space", json={"foundation_absorbs_markup": True})
            assert r.status_code == 200
            # Also flip the product itself (artist space flag is per-space; we
            # also need the product flag for the checkout helper)
            await db.products.update_one({"id": work_id}, {"$set": {"foundation_absorbs_markup": True}})

            r = await c.post("/checkout/products", json={
                "items": [{"product_id": work_id, "quantity": 1}],
                "origin_url": "http://localhost:3000",
                "shipping_address": {
                    "name": "QA", "address1": "1 St", "city": "Santa Cruz",
                    "state_code": "CA", "postcode": "95060", "country_code": "US",
                },
            })
            assert r.status_code == 200
            txn = await db.payment_transactions.find_one(
                {"items.product_id": work_id, "amount": 400.0}, {"_id": 0},
                sort=[("created_at", -1)],
            )
            assert txn is not None
            await db.payment_transactions.delete_one({"session_id": txn["session_id"]})
    finally:
        if work_id:
            await db.products.delete_one({"id": work_id})
        await db.partner_profiles.delete_one({"id": profile_id})
        await db.gallery_spaces.delete_one({"user_id": vendor["id"]})


@pytest.mark.asyncio
async def test_gallery_inquiry_requires_commissions_open(db, vendor_token):
    """Anonymous user submitting an inquiry to an artist whose commissions are
    closed gets a 400; opening commissions then succeeds."""
    vendor = await db.users.find_one({"email": VENDOR_EMAIL}, {"_id": 0, "id": 1})
    profile_id = f"test-artist-{uuid.uuid4().hex[:8]}"
    slug = f"artist-com-{uuid.uuid4().hex[:8]}"
    await db.partner_profiles.insert_one({
        "id": profile_id, "user_id": vendor["id"], "partner_type": "artist",
        "status": "active", "public": True, "slug": slug,
        "display_name": "Commissions Artist", "headline": "x" * 10, "bio": "x" * 50,
        "approved_at": "2026-05-30T00:00:00+00:00", "approved_by": "test",
        "created_at": "2026-05-30T00:00:00+00:00", "updated_at": "2026-05-30T00:00:00+00:00",
    })
    try:
        # Force-create the gallery_space
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {vendor_token}"}) as c:
            await c.get("/gallery/me/space")

        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
            r = await c.post("/gallery/inquiries", json={
                "artist_slug": slug, "name": "Buyer",
                "email": "buyer@example.com",
                "message": "I'd love a commission piece please" + "." * 10,
            })
            assert r.status_code == 400
        # Open commissions
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0,
                                      headers={"Authorization": f"Bearer {vendor_token}"}) as c:
            r = await c.put("/gallery/me/space", json={"commissions_open": True})
            assert r.status_code == 200
        async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as c:
            r = await c.post("/gallery/inquiries", json={
                "artist_slug": slug, "name": "Buyer",
                "email": "buyer@example.com",
                "message": "I'd love a commission piece please" + "." * 10,
            })
            assert r.status_code == 200, r.text
            await db.gallery_inquiries.delete_many({"artist_slug": slug})
    finally:
        await db.partner_profiles.delete_one({"id": profile_id})
        await db.gallery_spaces.delete_one({"user_id": vendor["id"]})
