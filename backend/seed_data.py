"""Seed data for Birthright platform - idempotent. Split into helpers per data type."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from models import gen_id, now_iso
from auth_utils import hash_password


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _seed_user(email: str, name: tuple[str, str], role: str, profile: Optional[dict] = None) -> dict:
    """Build one user document. `name` is (first, last); `profile` carries optional fields."""
    profile = profile or {}
    first, last = name
    return {
        "id": gen_id(),
        "email": email,
        "password_hash": hash_password("birthright2026"),
        "first_name": first,
        "last_name": last,
        "phone": "",
        "role": role,
        "bio": profile.get("bio", ""),
        "avatar_url": profile.get("avatar_url", ""),
        "facilitator_slug": profile.get("slug"),
        "credentials": profile.get("credentials"),
        "created_at": now_iso(),
    }


# ---- USERS ----
def _build_seed_users() -> list[dict]:
    return [
        _seed_user(
            "admin@birthright.org", ("Birthright", "Admin"), "admin",
            {"bio": "Founding administrator of the Birthright Foundation."},
        ),
        _seed_user(
            "elena@birthright.org", ("Elena", "Hartwell"), "facilitator",
            {
                "bio": "Elena is a licensed therapist with over fifteen years guiding individuals and families through attachment work. She believes secure bonds are restorative, not aspirational.",
                "avatar_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600",
                "slug": "elena-hartwell",
                "credentials": "LMFT, EFT-Certified",
            },
        ),
        _seed_user(
            "marcus@birthright.org", ("Marcus", "Okafor"), "facilitator",
            {
                "bio": "Marcus weaves contemplative practice with relational science to help groups recover what was always theirs: the right to belong.",
                "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600",
                "slug": "marcus-okafor",
                "credentials": "PhD Psychology, Group Facilitator",
            },
        ),
        _seed_user("demo@birthright.org", ("Sam", "Rivera"), "participant"),
    ]


# ---- FOUNDATION CONTENT ----
def _build_foundation_content() -> dict:
    return {
        "key": "content",
        "mission_statement": "Secure bonds are our birthright. We exist to empower everyone with the tools and support we all occasionally need to claim and recover our secure bonds with our precious people. So we can all thrive.",
        "about_text": "Birthright is an educational foundation devoted to one quiet conviction: every person is born deserving of secure, nourishing relationships. We translate the science of attachment, the practice of emotional repair, and the wisdom of community into workshops anyone can attend. We are not therapy. We are the practice ground.",
        "education_structure": "Our work is organized in three concentric circles. Foundations introduces the language and felt-sense of secure bonds. Practice convenes small cohorts for live skills work with certified facilitators. Living the Work is an ongoing peer community that meets monthly to keep the practice alive between formal trainings.",
        "vision": "A world where reconnection is normal, repair is taught early, and every household has at least one person who knows what a secure bond feels like.",
        "values": [
            "Connection over performance",
            "Repair over perfection",
            "Practice over theory",
            "Belonging over fitting in",
            "Curiosity over certainty",
        ],
    }


# ---- GOVERNING MEMBERS ----
def _build_governing_members() -> list[dict]:
    return [
        {"id": gen_id(), "name": "Dr. Aurelia Mendez", "title": "Board Chair & Co-Founder", "bio": "Aurelia spent two decades in family medicine before turning her attention full-time to relational education. She holds a doctorate in clinical psychology.", "image_url": "https://images.unsplash.com/photo-1551836022-deb4988cc6c0?w=600", "order": 1},
        {"id": gen_id(), "name": "James Reagan", "title": "Executive Director", "bio": "James leads the foundation's operations and partnerships. A long-time advocate of attachment-informed community work.", "image_url": "/api/static/people/james-reagan.jpg", "order": 2},
        {"id": gen_id(), "name": "Reverend Tomas Ifeanyi", "title": "Director of Community Stewardship", "bio": "Tomas oversees facilitator training and ensures the work stays grounded in the lived experience of the people we serve.", "image_url": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=600", "order": 3},
        {"id": gen_id(), "name": "Dr. Hannah Lin", "title": "Research Advisor", "bio": "Hannah translates emerging attachment research into curriculum and program evaluation methodology.", "image_url": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=600", "order": 4},
    ]


_LOC_NAME = "Birthright Community Hall"
_LOC_ADDR = "2148 W Earll Dr, Phoenix, AZ 85015"
_LOC_MAP = "https://maps.google.com/?q=2148+W+Earll+Dr+Phoenix+AZ+85015"


def _make_workshop(**kw) -> dict:
    """Build a workshop document with sensible defaults."""
    base = {
        "id": gen_id(),
        "location_name": _LOC_NAME,
        "location_address": _LOC_ADDR,
        "map_url": _LOC_MAP,
        "directions_notes": "",
        "materials_included": [],
        "faq": [],
        "created_at": now_iso(),
    }
    base.update(kw)
    return base


def _foundations_workshop(now: datetime, fac_id: str) -> dict:
    return _make_workshop(
        title="Foundations of Secure Bonds",
        slug="foundations-of-secure-bonds",
        short_description="A weekend immersion in the language, felt-sense, and daily practice of attachment-secure relating.",
        full_description="Over two days, you'll learn to recognize the small moments where bonds either deepen or fray. Through guided exercises, dyad practice, and reflective journaling, you'll leave with a working vocabulary for what was previously instinct. Designed for newcomers to attachment work and seasoned practitioners alike.",
        facilitator_id=fac_id,
        directions_notes="Free street parking is available. Please use the side entrance on Earll Dr. Light refreshments provided. Bring a journal and comfortable clothing.",
        start_date=_iso(now + timedelta(days=21)),
        end_date=_iso(now + timedelta(days=22)),
        capacity=24, early_bird_price=285.00, regular_price=365.00,
        early_bird_until=_iso(now + timedelta(days=7)),
        image_url="https://images.unsplash.com/photo-1634155938686-24a26c55d71a?w=1200",
        materials_included=[
            "Foundations workbook (printed)",
            "Two days of facilitated practice",
            "Light meals and refreshments",
            "Access to alumni community channel",
        ],
        faq=[
            {"q": "Is this therapy?", "a": "No. This is educational practice. We hold a learning container, not a clinical one. Many participants are also in therapy; the two complement each other beautifully."},
            {"q": "What should I bring?", "a": "A journal, a refillable water bottle, and clothing you can move and sit comfortably in. Everything else is provided."},
            {"q": "Can I attend if I'm new to attachment language?", "a": "Yes. This is the on-ramp. We start with the basics and build from there."},
        ],
        check_in_code="BRIGHT24", status="upcoming",
    )


def _repair_workshop(now: datetime, fac_id: str) -> dict:
    return _make_workshop(
        title="Repair: The Conversation You Postponed",
        slug="repair-the-conversation-you-postponed",
        short_description="A focused day on the architecture of relational repair, for couples, family members, and close friends.",
        full_description="Most ruptures don't need a grand reckoning, they need a small, well-formed reentry. This single-day intensive teaches the three movements of repair and gives you supervised practice with a partner of your choosing or one assigned at the workshop. Includes optional follow-up coaching.",
        facilitator_id=fac_id,
        directions_notes="Doors open 30 minutes before start. Childcare available with 7 days notice (contact us).",
        start_date=_iso(now + timedelta(days=45)),
        end_date=_iso(now + timedelta(days=45, hours=8)),
        capacity=18, early_bird_price=195.00, regular_price=245.00,
        early_bird_until=_iso(now + timedelta(days=20)),
        image_url="https://images.unsplash.com/photo-1655337690436-98778f38d613?w=1200",
        materials_included=["Repair pocket guide", "Pair-practice worksheets", "Optional 30-min coaching follow-up (sold separately)"],
        faq=[{"q": "Do I need to bring a partner?", "a": "No. We'll pair you with another participant for practice. Many people prefer it this way."}],
        check_in_code="REPAIR45", status="upcoming",
    )


def _circle_workshop(now: datetime, fac_id: str) -> dict:
    return _make_workshop(
        title="Living the Work: Monthly Practice Circle",
        slug="living-the-work-monthly-circle",
        short_description="An ongoing monthly cohort for alumni. Keep the practice alive between formal trainings.",
        full_description="Once you've completed Foundations or Repair, this is where the work lives. A two-hour monthly gathering with rotating facilitators, peer practice, and a small library of advanced exercises that rotate through the year.",
        facilitator_id=fac_id,
        directions_notes="Held the second Saturday of every month.",
        start_date=_iso(now + timedelta(days=60)),
        end_date=_iso(now + timedelta(days=60, hours=2)),
        capacity=30, early_bird_price=35.00, regular_price=45.00,
        early_bird_until=_iso(now + timedelta(days=30)),
        image_url="https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=1200",
        materials_included=["Practice circle worksheet of the month"],
        check_in_code="CIRCLE12", status="upcoming",
    )


def _past_foundations_workshop(now: datetime, fac_id: str) -> dict:
    return _make_workshop(
        title="Foundations of Secure Bonds (Spring Cohort)",
        slug="foundations-spring-cohort-past",
        short_description="Our last spring cohort. Completed; reviews and impact statements live here.",
        full_description="A two-day immersion held this past spring. Reviews and participant impact statements are available below.",
        facilitator_id=fac_id,
        start_date=_iso(now - timedelta(days=45)),
        end_date=_iso(now - timedelta(days=44)),
        capacity=24, early_bird_price=285.00, regular_price=365.00,
        early_bird_until=_iso(now - timedelta(days=60)),
        image_url="https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?w=1200",
        materials_included=["Foundations workbook"],
        check_in_code="BRIGHT23", status="completed",
    )


# ---- WORKSHOPS ----
def _build_workshops(now: datetime, fac1_id: str, fac2_id: str) -> tuple[list[dict], str, str, str, str]:
    workshops = [
        _foundations_workshop(now, fac1_id),
        _repair_workshop(now, fac2_id),
        _circle_workshop(now, fac1_id),
        _past_foundations_workshop(now, fac1_id),
    ]
    return workshops, workshops[0]["id"], workshops[1]["id"], workshops[2]["id"], workshops[3]["id"]


# ---- PRODUCTS ----
def _build_products(w1_id: str, w2_id: str, w3_id: str) -> list[dict]:
    return [
        {"id": gen_id(), "name": "Birthright Hardcover Journal", "description": "A linen-bound journal with prompts designed to deepen daily reflective practice. 200 lined pages.", "price": 38.00, "type": "merch", "workshop_id": None, "image_url": "/api/static/products/birthright-hardcover-journal.png", "inventory": 50, "category": "journals", "created_at": now_iso()},
        {"id": gen_id(), "name": "Secure Bonds Mug (Ceramic)", "description": "Hand-glazed teal ceramic mug with the birthright flame stamped subtly on the base. 12oz.", "price": 24.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=800", "inventory": 75, "category": "home", "created_at": now_iso()},
        {"id": gen_id(), "name": "Organic Cotton Tote", "description": "Natural cotton tote bag, screen-printed locally. Holds a journal, water bottle, and a borrowed book.", "price": 22.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1591561954557-26941169b49e?w=800", "inventory": 60, "category": "bags", "created_at": now_iso()},
        {"id": gen_id(), "name": "Birthright Tee — Cream", "description": "Heavy-weight, garment-dyed cotton tee. Small flame embroidered at the chest.", "price": 32.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800", "inventory": 100, "category": "apparel", "created_at": now_iso()},
        {"id": gen_id(), "name": "Field Notes Pack (3-pack)", "description": "Pocket notebooks for the in-between moments. Three per pack, blank pages.", "price": 14.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=800", "inventory": 80, "category": "journals", "created_at": now_iso()},
        {"id": gen_id(), "name": "Enamel Pin — Flame", "description": "A small, quiet pin. For the lapel of someone doing the work.", "price": 12.00, "type": "merch", "workshop_id": None, "image_url": "/api/static/products/enamel-pin-flame.png", "inventory": 200, "category": "accessories", "created_at": now_iso()},
        {"id": gen_id(), "name": "Foundations Companion Audio (digital)", "description": "Audio companion exclusive to Foundations participants. Six guided practices, downloadable.", "price": 18.00, "type": "workshop_material", "workshop_id": w1_id, "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800", "inventory": 999, "category": "digital", "created_at": now_iso()},
        {"id": gen_id(), "name": "Foundations Extended Workbook", "description": "An extended workbook with 12 additional exercises, available only to Foundations participants.", "price": 28.00, "type": "workshop_material", "workshop_id": w1_id, "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800", "inventory": 50, "category": "books", "created_at": now_iso()},
        {"id": gen_id(), "name": "Repair Pocket Cards", "description": "A deck of 24 pocket cards: one for each repair phrase. Repair participants only.", "price": 22.00, "type": "workshop_material", "workshop_id": w2_id, "image_url": "https://images.unsplash.com/photo-1606326608606-aa0b62935f2b?w=800", "inventory": 100, "category": "decks", "created_at": now_iso()},
        {"id": gen_id(), "name": "Circle Practice Year-Set", "description": "A printed binder of all twelve monthly practice circle worksheets. Members only.", "price": 45.00, "type": "workshop_material", "workshop_id": w3_id, "image_url": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=800", "inventory": 30, "category": "books", "created_at": now_iso()},
    ]


# ---- DEMO REGISTRATION + REVIEW + IMPACT ----
def _build_demo_engagement(now: datetime, w4_id: str, participant_id: str) -> tuple[dict, dict, dict]:
    reg = {
        "id": gen_id(), "workshop_id": w4_id, "user_id": participant_id,
        "pricing_tier": "early_bird", "amount_paid": 285.00,
        "payment_session_id": "seed_demo", "payment_status": "paid",
        "checked_in": True, "checked_in_at": _iso(now - timedelta(days=45)),
        "created_at": now_iso(),
    }
    review = {
        "id": gen_id(), "workshop_id": w4_id, "user_id": participant_id,
        "user_name": "Sam Rivera", "rating": 5,
        "review_text": "Elena holds a room like nobody else. I came in skeptical and left with a vocabulary I didn't know I needed. Two days, and I'm still using what I learned, every day.",
        "anonymous": False, "created_at": now_iso(),
    }
    impact = {
        "id": gen_id(), "workshop_id": w4_id, "user_id": participant_id,
        "user_name": "Sam Rivera",
        "what_learned": "That a secure bond is built in small, repeatable moments — not in dramatic conversations.",
        "how_grew": "I stopped waiting for the 'right time' to repair. The right time is the next time we're together.",
        "benefits": "My partner and I have had three repair conversations since the workshop. All of them went somewhere new.",
        "improvements": "Maybe a third optional day for deeper dyad work. Two days felt short.",
        "is_public": True, "anonymous": False, "created_at": now_iso(),
    }
    return reg, review, impact


# ---- MAIN ENTRY ----
async def seed_if_empty(db) -> None:
    if await db.users.count_documents({}) > 0:
        return

    now = datetime.now(timezone.utc)

    users = _build_seed_users()
    await db.users.insert_many(users)
    admin, fac1, fac2, participant = users

    await db.foundation_content.insert_one(_build_foundation_content())
    await db.governing_members.insert_many(_build_governing_members())

    workshops, w1_id, w2_id, w3_id, w4_id = _build_workshops(now, fac1["id"], fac2["id"])
    await db.workshops.insert_many(workshops)

    await db.products.insert_many(_build_products(w1_id, w2_id, w3_id))

    reg, review, impact = _build_demo_engagement(now, w4_id, participant["id"])
    await db.registrations.insert_one(reg)
    await db.reviews.insert_one(review)
    await db.impact_statements.insert_one(impact)
