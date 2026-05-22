"""Seed data for Birthright platform - idempotent."""
from datetime import datetime, timezone, timedelta
from models import gen_id, now_iso
from auth_utils import hash_password


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def seed_if_empty(db):
    # Check if already seeded
    if await db.users.count_documents({}) > 0:
        return

    now = datetime.now(timezone.utc)

    # ===== USERS =====
    admin = {
        "id": gen_id(),
        "email": "admin@birthright.org",
        "password_hash": hash_password("birthright2026"),
        "first_name": "Birthright",
        "last_name": "Admin",
        "phone": "",
        "role": "admin",
        "bio": "Founding administrator of the Birthright Foundation.",
        "avatar_url": "",
        "facilitator_slug": None,
        "credentials": None,
        "created_at": now_iso(),
    }
    fac1 = {
        "id": gen_id(),
        "email": "elena@birthright.org",
        "password_hash": hash_password("birthright2026"),
        "first_name": "Elena",
        "last_name": "Hartwell",
        "phone": "",
        "role": "facilitator",
        "bio": "Elena is a licensed therapist with over fifteen years guiding individuals and families through attachment work. She believes secure bonds are restorative, not aspirational.",
        "avatar_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600",
        "facilitator_slug": "elena-hartwell",
        "credentials": "LMFT, EFT-Certified",
        "created_at": now_iso(),
    }
    fac2 = {
        "id": gen_id(),
        "email": "marcus@birthright.org",
        "password_hash": hash_password("birthright2026"),
        "first_name": "Marcus",
        "last_name": "Okafor",
        "phone": "",
        "role": "facilitator",
        "bio": "Marcus weaves contemplative practice with relational science to help groups recover what was always theirs: the right to belong.",
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600",
        "facilitator_slug": "marcus-okafor",
        "credentials": "PhD Psychology, Group Facilitator",
        "created_at": now_iso(),
    }
    participant = {
        "id": gen_id(),
        "email": "demo@birthright.org",
        "password_hash": hash_password("birthright2026"),
        "first_name": "Sam",
        "last_name": "Rivera",
        "phone": "",
        "role": "participant",
        "bio": "",
        "avatar_url": "",
        "facilitator_slug": None,
        "credentials": None,
        "created_at": now_iso(),
    }
    await db.users.insert_many([admin, fac1, fac2, participant])

    # ===== FOUNDATION CONTENT =====
    await db.foundation_content.insert_one(
        {
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
    )

    # ===== GOVERNING MEMBERS =====
    await db.governing_members.insert_many(
        [
            {
                "id": gen_id(),
                "name": "Dr. Aurelia Mendez",
                "title": "Board Chair & Co-Founder",
                "bio": "Aurelia spent two decades in family medicine before turning her attention full-time to relational education. She holds a doctorate in clinical psychology.",
                "image_url": "https://images.unsplash.com/photo-1551836022-deb4988cc6c0?w=600",
                "order": 1,
            },
            {
                "id": gen_id(),
                "name": "James Reagan",
                "title": "Executive Director",
                "bio": "James leads the foundation's operations and partnerships. A long-time advocate of attachment-informed community work.",
                "image_url": "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=600",
                "order": 2,
            },
            {
                "id": gen_id(),
                "name": "Reverend Tomas Ifeanyi",
                "title": "Director of Community Stewardship",
                "bio": "Tomas oversees facilitator training and ensures the work stays grounded in the lived experience of the people we serve.",
                "image_url": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=600",
                "order": 3,
            },
            {
                "id": gen_id(),
                "name": "Dr. Hannah Lin",
                "title": "Research Advisor",
                "bio": "Hannah translates emerging attachment research into curriculum and program evaluation methodology.",
                "image_url": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=600",
                "order": 4,
            },
        ]
    )

    # ===== WORKSHOPS =====
    w1_id = gen_id()
    w2_id = gen_id()
    w3_id = gen_id()
    w4_id = gen_id()
    workshops = [
        {
            "id": w1_id,
            "title": "Foundations of Secure Bonds",
            "slug": "foundations-of-secure-bonds",
            "short_description": "A weekend immersion in the language, felt-sense, and daily practice of attachment-secure relating.",
            "full_description": "Over two days, you'll learn to recognize the small moments where bonds either deepen or fray. Through guided exercises, dyad practice, and reflective journaling, you'll leave with a working vocabulary for what was previously instinct. Designed for newcomers to attachment work and seasoned practitioners alike.",
            "facilitator_id": fac1["id"],
            "location_name": "Birthright Community Hall",
            "location_address": "2148 W Earll Dr, Phoenix, AZ 85015",
            "directions_notes": "Free street parking is available. Please use the side entrance on Earll Dr. Light refreshments provided. Bring a journal and comfortable clothing.",
            "map_url": "https://maps.google.com/?q=2148+W+Earll+Dr+Phoenix+AZ+85015",
            "start_date": _iso(now + timedelta(days=21)),
            "end_date": _iso(now + timedelta(days=22)),
            "capacity": 24,
            "early_bird_price": 285.00,
            "regular_price": 365.00,
            "early_bird_until": _iso(now + timedelta(days=7)),
            "image_url": "https://images.unsplash.com/photo-1634155938686-24a26c55d71a?w=1200",
            "materials_included": [
                "Foundations workbook (printed)",
                "Two days of facilitated practice",
                "Light meals and refreshments",
                "Access to alumni community channel",
            ],
            "faq": [
                {"q": "Is this therapy?", "a": "No. This is educational practice. We hold a learning container, not a clinical one. Many participants are also in therapy; the two complement each other beautifully."},
                {"q": "What should I bring?", "a": "A journal, a refillable water bottle, and clothing you can move and sit comfortably in. Everything else is provided."},
                {"q": "Can I attend if I'm new to attachment language?", "a": "Yes. This is the on-ramp. We start with the basics and build from there."},
            ],
            "check_in_code": "BRIGHT24",
            "status": "upcoming",
            "created_at": now_iso(),
        },
        {
            "id": w2_id,
            "title": "Repair: The Conversation You Postponed",
            "slug": "repair-the-conversation-you-postponed",
            "short_description": "A focused day on the architecture of relational repair, for couples, family members, and close friends.",
            "full_description": "Most ruptures don't need a grand reckoning, they need a small, well-formed reentry. This single-day intensive teaches the three movements of repair and gives you supervised practice with a partner of your choosing or one assigned at the workshop. Includes optional follow-up coaching.",
            "facilitator_id": fac2["id"],
            "location_name": "Birthright Community Hall",
            "location_address": "2148 W Earll Dr, Phoenix, AZ 85015",
            "directions_notes": "Doors open 30 minutes before start. Childcare available with 7 days notice (contact us).",
            "map_url": "https://maps.google.com/?q=2148+W+Earll+Dr+Phoenix+AZ+85015",
            "start_date": _iso(now + timedelta(days=45)),
            "end_date": _iso(now + timedelta(days=45, hours=8)),
            "capacity": 18,
            "early_bird_price": 195.00,
            "regular_price": 245.00,
            "early_bird_until": _iso(now + timedelta(days=20)),
            "image_url": "https://images.unsplash.com/photo-1655337690436-98778f38d613?w=1200",
            "materials_included": [
                "Repair pocket guide",
                "Pair-practice worksheets",
                "Optional 30-min coaching follow-up (sold separately)",
            ],
            "faq": [
                {"q": "Do I need to bring a partner?", "a": "No. We'll pair you with another participant for practice. Many people prefer it this way."},
            ],
            "check_in_code": "REPAIR45",
            "status": "upcoming",
            "created_at": now_iso(),
        },
        {
            "id": w3_id,
            "title": "Living the Work: Monthly Practice Circle",
            "slug": "living-the-work-monthly-circle",
            "short_description": "An ongoing monthly cohort for alumni. Keep the practice alive between formal trainings.",
            "full_description": "Once you've completed Foundations or Repair, this is where the work lives. A two-hour monthly gathering with rotating facilitators, peer practice, and a small library of advanced exercises that rotate through the year.",
            "facilitator_id": fac1["id"],
            "location_name": "Birthright Community Hall",
            "location_address": "2148 W Earll Dr, Phoenix, AZ 85015",
            "directions_notes": "Held the second Saturday of every month.",
            "map_url": "https://maps.google.com/?q=2148+W+Earll+Dr+Phoenix+AZ+85015",
            "start_date": _iso(now + timedelta(days=60)),
            "end_date": _iso(now + timedelta(days=60, hours=2)),
            "capacity": 30,
            "early_bird_price": 35.00,
            "regular_price": 45.00,
            "early_bird_until": _iso(now + timedelta(days=30)),
            "image_url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=1200",
            "materials_included": ["Practice circle worksheet of the month"],
            "faq": [],
            "check_in_code": "CIRCLE12",
            "status": "upcoming",
            "created_at": now_iso(),
        },
        {
            "id": w4_id,
            "title": "Foundations of Secure Bonds (Spring Cohort)",
            "slug": "foundations-spring-cohort-past",
            "short_description": "Our last spring cohort. Completed; reviews and impact statements live here.",
            "full_description": "A two-day immersion held this past spring. Reviews and participant impact statements are available below.",
            "facilitator_id": fac1["id"],
            "location_name": "Birthright Community Hall",
            "location_address": "2148 W Earll Dr, Phoenix, AZ 85015",
            "directions_notes": "",
            "map_url": "https://maps.google.com/?q=2148+W+Earll+Dr+Phoenix+AZ+85015",
            "start_date": _iso(now - timedelta(days=45)),
            "end_date": _iso(now - timedelta(days=44)),
            "capacity": 24,
            "early_bird_price": 285.00,
            "regular_price": 365.00,
            "early_bird_until": _iso(now - timedelta(days=60)),
            "image_url": "https://images.unsplash.com/photo-1582213782179-e0d53f98f2ca?w=1200",
            "materials_included": ["Foundations workbook"],
            "faq": [],
            "check_in_code": "BRIGHT23",
            "status": "completed",
            "created_at": now_iso(),
        },
    ]
    await db.workshops.insert_many(workshops)

    # ===== PRODUCTS =====
    products = [
        # Merch (public)
        {"id": gen_id(), "name": "Birthright Hardcover Journal", "description": "A linen-bound journal with prompts designed to deepen daily reflective practice. 200 lined pages.", "price": 38.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1517091756889-bfa90c9ad4c2?w=800", "inventory": 50, "category": "journals", "created_at": now_iso()},
        {"id": gen_id(), "name": "Secure Bonds Mug (Ceramic)", "description": "Hand-glazed teal ceramic mug with the birthright flame stamped subtly on the base. 12oz.", "price": 24.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=800", "inventory": 75, "category": "home", "created_at": now_iso()},
        {"id": gen_id(), "name": "Organic Cotton Tote", "description": "Natural cotton tote bag, screen-printed locally. Holds a journal, water bottle, and a borrowed book.", "price": 22.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1591561954557-26941169b49e?w=800", "inventory": 60, "category": "bags", "created_at": now_iso()},
        {"id": gen_id(), "name": "Birthright Tee — Cream", "description": "Heavy-weight, garment-dyed cotton tee. Small flame embroidered at the chest.", "price": 32.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800", "inventory": 100, "category": "apparel", "created_at": now_iso()},
        {"id": gen_id(), "name": "Field Notes Pack (3-pack)", "description": "Pocket notebooks for the in-between moments. Three per pack, blank pages.", "price": 14.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=800", "inventory": 80, "category": "journals", "created_at": now_iso()},
        {"id": gen_id(), "name": "Enamel Pin — Flame", "description": "A small, quiet pin. For the lapel of someone doing the work.", "price": 12.00, "type": "merch", "workshop_id": None, "image_url": "https://images.unsplash.com/photo-1611652022417-a551ec99c0a8?w=800", "inventory": 200, "category": "accessories", "created_at": now_iso()},
        # Workshop materials (gated)
        {"id": gen_id(), "name": "Foundations Companion Audio (digital)", "description": "Audio companion exclusive to Foundations participants. Six guided practices, downloadable.", "price": 18.00, "type": "workshop_material", "workshop_id": w1_id, "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800", "inventory": 999, "category": "digital", "created_at": now_iso()},
        {"id": gen_id(), "name": "Foundations Extended Workbook", "description": "An extended workbook with 12 additional exercises, available only to Foundations participants.", "price": 28.00, "type": "workshop_material", "workshop_id": w1_id, "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800", "inventory": 50, "category": "books", "created_at": now_iso()},
        {"id": gen_id(), "name": "Repair Pocket Cards", "description": "A deck of 24 pocket cards: one for each repair phrase. Repair participants only.", "price": 22.00, "type": "workshop_material", "workshop_id": w2_id, "image_url": "https://images.unsplash.com/photo-1606326608606-aa0b62935f2b?w=800", "inventory": 100, "category": "decks", "created_at": now_iso()},
        {"id": gen_id(), "name": "Circle Practice Year-Set", "description": "A printed binder of all twelve monthly practice circle worksheets. Members only.", "price": 45.00, "type": "workshop_material", "workshop_id": w3_id, "image_url": "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=800", "inventory": 30, "category": "books", "created_at": now_iso()},
    ]
    await db.products.insert_many(products)

    # ===== Demo registration for the past workshop =====
    reg = {
        "id": gen_id(),
        "workshop_id": w4_id,
        "user_id": participant["id"],
        "pricing_tier": "early_bird",
        "amount_paid": 285.00,
        "payment_session_id": "seed_demo",
        "payment_status": "paid",
        "checked_in": True,
        "checked_in_at": _iso(now - timedelta(days=45)),
        "created_at": now_iso(),
    }
    await db.registrations.insert_one(reg)

    # ===== Demo review + impact statement =====
    await db.reviews.insert_one(
        {
            "id": gen_id(),
            "workshop_id": w4_id,
            "user_id": participant["id"],
            "user_name": "Sam Rivera",
            "rating": 5,
            "review_text": "Elena holds a room like nobody else. I came in skeptical and left with a vocabulary I didn't know I needed. Two days, and I'm still using what I learned, every day.",
            "anonymous": False,
            "created_at": now_iso(),
        }
    )
    await db.impact_statements.insert_one(
        {
            "id": gen_id(),
            "workshop_id": w4_id,
            "user_id": participant["id"],
            "user_name": "Sam Rivera",
            "what_learned": "That a secure bond is built in small, repeatable moments — not in dramatic conversations.",
            "how_grew": "I stopped waiting for the 'right time' to repair. The right time is the next time we're together.",
            "benefits": "My partner and I have had three repair conversations since the workshop. All of them went somewhere new.",
            "improvements": "Maybe a third optional day for deeper dyad work. Two days felt short.",
            "is_public": True,
            "anonymous": False,
            "created_at": now_iso(),
        }
    )
