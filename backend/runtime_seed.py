"""Runtime seed helpers — run on EVERY startup, idempotent by design.

Distinct from `seed_data.seed_if_empty` which only fires on a fresh DB.
This module handles two production-critical jobs:

1. `ensure_catalog_seeded` — backfills the 50 AI-generated catalog items from
   `data/catalog.json` whenever they're missing (keyed on product `slug`).
   Uses the committed PNGs under `static/products/<slug>.png`; never calls
   the image generator at runtime. Safe to call on every boot.

2. `repair_known_broken_images` — heals two specific seeded products whose
   original Unsplash CDN URLs went stale. Looks them up by NAME (since
   product IDs differ across environments) and rewrites `image_url` to the
   stable committed-PNG path.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from models import gen_id, now_iso

logger = logging.getLogger("birthright.runtime_seed")

BACKEND_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BACKEND_DIR / "data" / "catalog.json"
STATIC_DIR = BACKEND_DIR / "static" / "products"

# Mapping of product NAME -> stable committed PNG filename. Add entries here
# any time a seeded product's image_url needs to be self-healed across deploys.
KNOWN_IMAGE_REPAIRS: dict[str, str] = {
    "Birthright Hardcover Journal": "birthright-hardcover-journal.png",
    "Enamel Pin — Flame": "enamel-pin-flame.png",
}


def _load_catalog_items() -> tuple[list[dict] | None, dict | None]:
    """Read catalog.json. Returns (items, error_summary)."""
    if not CATALOG_PATH.exists():
        logger.warning(f"catalog.json not found at {CATALOG_PATH} — skipping catalog seed")
        return None, {"inserted": 0, "skipped": 0, "missing_catalog": True}
    try:
        catalog = json.loads(CATALOG_PATH.read_text())
        return catalog.get("items", []), None
    except Exception as e:
        logger.error(f"catalog.json parse failed: {e}")
        return None, {"inserted": 0, "skipped": 0, "parse_error": True}


async def _existing_slugs(db) -> set[str]:
    """Return the set of product slugs already present in MongoDB."""
    existing: set[str] = set()
    async for p in db.products.find({"slug": {"$exists": True}}, {"slug": 1, "_id": 0}):
        if p.get("slug"):
            existing.add(p["slug"])
    return existing


def _resolve_image_url(slug: str) -> str:
    """Point at the committed per-slug PNG, falling back to a placeholder."""
    if (STATIC_DIR / f"{slug}.png").exists():
        return f"/api/static/products/{slug}.png"
    return "/api/static/products/_placeholder.png"


def _build_catalog_product(item: dict) -> dict:
    """Compose a catalog product document for insert."""
    slug = item["slug"]
    return {
        "id": gen_id(),
        "slug": slug,
        "name": item["name"],
        "description": item["description"],
        "price": float(item["price"]),
        "type": item.get("type_override") or "merch",
        "workshop_id": None,
        "image_url": _resolve_image_url(slug),
        "inventory": int(item.get("inventory", 75)),
        "category": item["category"],
        "created_at": now_iso(),
    }


async def ensure_catalog_seeded(db) -> dict:
    """Insert any items from catalog.json whose `slug` is missing in DB.

    Returns a small summary dict for logging. Never raises — log + skip on error.
    """
    items, error = _load_catalog_items()
    if error is not None:
        return error

    existing = await _existing_slugs(db)
    to_insert = [
        _build_catalog_product(item)
        for item in items
        if item.get("slug") and item["slug"] not in existing
    ]

    if to_insert:
        await db.products.insert_many(to_insert)
        logger.info(f"catalog seed: inserted {len(to_insert)} products; {len(existing)} already present")
    else:
        logger.info(f"catalog seed: nothing to insert ({len(existing)} slug-tagged products in DB)")
    return {"inserted": len(to_insert), "skipped": len(existing)}


async def repair_known_broken_images(db) -> int:
    """Rewrite image_url for products whose CDN-hosted images went stale.

    Matches by product NAME (stable across environments) — only updates rows
    whose current image_url still points at the legacy host.
    Returns the number of repaired rows.
    """
    repaired = 0
    for name, filename in KNOWN_IMAGE_REPAIRS.items():
        new_url = f"/api/static/products/{filename}"
        result = await db.products.update_many(
            {
                "name": name,
                "$or": [
                    {"image_url": {"$regex": "^https?://"}},  # any external URL
                    {"image_url": {"$exists": False}},
                    {"image_url": ""},
                    {"image_url": {"$ne": new_url}},  # also re-point old self-hosted IDs
                ],
            },
            {"$set": {"image_url": new_url}},
        )
        if result.modified_count:
            logger.info(f"image repair: {result.modified_count}x {name!r} -> {new_url}")
            repaired += result.modified_count
    return repaired


# ============ v1.11.0 PARTNER ECONOMY BACKFILL ============

PARTNER_ECONOMY_DEFAULTS = {
    "is_founding_partner": False,
    "founding_rate_expires_at": None,
    "featured_until": None,
    "featured_mission_alignment": None,
    "featured_signature_content": None,
    "featured_video_url": None,
    "featured_image_urls": [],
    "featured_custom_cta": None,
    "external_site_url": None,
    "external_platform": None,
    "rev_share_overrides": None,  # dict or null
    "w9_status": "not_collected",  # not_collected | submitted | verified
    "payout_threshold_usd": 50.0,
    "payout_method": None,
    "payout_address_snapshot": None,
}


async def backfill_partner_economy_fields(db) -> int:
    """Add v1.11.0 partner-economy fields to any partner_profiles row missing them.
    Idempotent — uses `$set` with `$exists: False` guards so existing values are untouched.
    """
    backfilled = 0
    for field, default in PARTNER_ECONOMY_DEFAULTS.items():
        result = await db.partner_profiles.update_many(
            {field: {"$exists": False}},
            {"$set": {field: default}},
        )
        backfilled += result.modified_count
    # Phase 6C.1 — DM opt-in default depends on partner_type
    open_types = ["facilitator", "community"]
    closed_types = ["research", "vendor"]
    r1 = await db.partner_profiles.update_many(
        {"accepts_new_dms": {"$exists": False}, "partner_type": {"$in": open_types}},
        {"$set": {"accepts_new_dms": True}},
    )
    r2 = await db.partner_profiles.update_many(
        {"accepts_new_dms": {"$exists": False}, "partner_type": {"$in": closed_types}},
        {"$set": {"accepts_new_dms": False}},
    )
    backfilled += r1.modified_count + r2.modified_count
    if backfilled:
        logger.info(f"partner economy backfill: set {backfilled} field-rows to defaults")
    return backfilled


# ============ FOUNDATION ROLES + SAMPLE PARTNERS (Phase 6B.4.5b / 6B.4.5c) ============

FOUNDATION_ROLES_SEED = [
    {
        "slug": "board-chair-cofounder",
        "title": "Board Chair & Co-Founder",
        "headline": "Senior clinical practitioner ready to chair a foundation devoted to secure bonds.",
        "who_you_are": (
            "A senior practitioner whose career bridges clinical work and community building. "
            "You hold (or have held) a clinical credential — psychiatry, psychology, family "
            "medicine, social work, or a comparable license — and you've moved from individual "
            "practice toward systems-level relational education. You're comfortable with "
            "governance: chairing meetings, mediating board disagreements, shepherding "
            "strategic direction."
        ),
        "what_youll_do": (
            "Chair the governing board. Sign off on major strategic decisions, partnership "
            "agreements above material thresholds, and final approvals on the rev-share "
            "governance defaults. Be the public face of the foundation alongside the executive "
            "director. Recruit board successors."
        ),
        "what_you_bring": (
            "Doctorate in clinical psychology, psychiatry, family medicine, or related field. "
            "15+ years of practice. Demonstrated nonprofit board experience. Capacity to commit 5+ years."
        ),
        "time_commitment": "~6–8 hrs/month + quarterly board meetings",
        "compensation_summary": "Equity in mission — Birthright is a not-for-profit and does not currently provide monetary compensation. Stipends, honoraria, and grant-funded engagement may emerge as funding allows.",
        "order": 1,
        "seeded_member_name": "Dr. Aurelia Mendez",
    },
    {
        "slug": "research-advisor",
        "title": "Research Advisor",
        "headline": "Peer-reviewed scholar ready to chair the foundation's research council.",
        "who_you_are": (
            "A scholar of attachment, developmental psychology, family systems, or "
            "trauma-informed practice. Active or recently active in academic or applied "
            "research — peer-reviewed publications, IRB-supervised studies, or "
            "methodologically serious practitioner work. You believe the foundation's "
            "curriculum and impact claims should be grounded in evidence, and you're willing "
            "to shepherd that translation."
        ),
        "what_youll_do": (
            "Chair the foundation's research council. Vet incoming research-partner "
            "applications. Co-author the foundation's annual evidence brief. Advise on "
            "outcome-measurement instruments embedded in the workshop platform "
            "(pre/post surveys, longitudinal follow-up cadence). Guide the foundation's "
            "standards for what counts as a publishable Birthright research artifact and how "
            "DOIs are minted."
        ),
        "what_you_bring": (
            "Doctorate in psychology, social work, family medicine, or related field. "
            "Active peer-reviewed publication record in attachment, relational, or "
            "developmental research. Comfortable with both quantitative and qualitative "
            "methods. Capacity to commit 3+ years."
        ),
        "time_commitment": "~4–6 hrs/month + quarterly research-council meetings",
        "compensation_summary": "Equity in mission — Birthright is a not-for-profit and does not currently provide monetary compensation. Stipends, honoraria, and grant-funded engagement may emerge as funding allows.",
        "order": 2,
        "seeded_member_name": "Dr. Hannah Lin",
    },
    {
        "slug": "director-community-stewardship",
        "title": "Director of Community Stewardship",
        "headline": "Community elder ready to hold the relational center of the foundation.",
        "who_you_are": (
            "A community elder — ordained, lay, or both — with a track record of holding "
            "space for groups doing hard relational work. You're comfortable training "
            "facilitators, mediating disputes between partners, and ensuring the foundation's "
            "work remains rooted in the lived experience of the people we serve rather than "
            "drifting into academic abstraction."
        ),
        "what_youll_do": (
            "Oversee facilitator training and certification. Serve as the foundation's "
            "first-line ombudsman for participant and partner concerns. Curate the "
            "foundation's relationships with faith communities, recovery communities, and "
            "other partner organizations whose work overlaps with ours. Provide pastoral / "
            "elder presence at major foundation events."
        ),
        "what_you_bring": (
            "Ordained ministry, chaplaincy, or comparable community-elder credential preferred. "
            "Demonstrated experience training group facilitators. Capacity to model the "
            "relational presence the work itself requires."
        ),
        "time_commitment": "~10 hrs/week",
        "compensation_summary": "Equity in mission — Birthright is a not-for-profit and does not currently provide monetary compensation. Stipends, honoraria, and grant-funded engagement may emerge as funding allows.",
        "order": 3,
        "seeded_member_name": "Reverend Tomas Ifeanyi",
    },
]


async def ensure_foundation_roles_seeded(db) -> int:
    """Insert the 3 open foundation roles if absent (idempotent by slug).
    Also links each role to its existing governing_member by name."""
    inserted = 0
    for spec in FOUNDATION_ROLES_SEED:
        if await db.foundation_roles.find_one({"slug": spec["slug"]}):
            continue
        member = await db.governing_members.find_one({"name": spec["seeded_member_name"]}, {"id": 1, "_id": 0})
        now = now_iso()
        doc = {
            "id": gen_id(),
            "slug": spec["slug"],
            "title": spec["title"],
            "headline": spec["headline"],
            "who_you_are": spec["who_you_are"],
            "what_youll_do": spec["what_youll_do"],
            "what_you_bring": spec["what_you_bring"],
            "time_commitment": spec["time_commitment"],
            "compensation_summary": spec["compensation_summary"],
            "order": spec["order"],
            "open": True,
            "seeded_member_id": member["id"] if member else None,
            "created_at": now,
            "updated_at": now,
        }
        await db.foundation_roles.insert_one(doc)
        inserted += 1
    if inserted:
        logger.info(f"foundation roles seed: inserted {inserted} roles")
    return inserted


# ---- Sample Partner Profiles (8 total, 2 per partner type) ----

SAMPLE_PARTNER_PROFILES = [
    # ---- Facilitators ----
    {
        "slug": "sample-maya-chen",
        "partner_type": "facilitator",
        "display_name": "Dr. Maya Chen, LCSW",
        "headline": "Trauma-informed facilitator bringing Birthright IP workshops to weekend retreats.",
        "bio": "Fifteen years of clinical practice with adult children of relational trauma. Hosts Foundation IP workshops at a partner studio in the Columbia Gorge. Maya represents the practitioner who already has a thriving private practice and wants Birthright's curriculum, community, and virtual venue to extend her reach without rebuilding infrastructure herself.",
        "location": "Portland, OR",
        "website_url": "https://example.com/maya-chen",
        "photo_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=600",
        "is_founding_partner": True,
    },
    {
        "slug": "sample-aaron-kalu",
        "partner_type": "facilitator",
        "display_name": "Aaron Kalu",
        "headline": "Movement & somatic facilitator blending Authentic Movement with relational frameworks.",
        "bio": "Background in dance and Authentic Movement. Hosts non-IP workshops blending somatic exploration with Birthright's relational frameworks. Represents the facilitator who mostly runs their own content but values Birthright as venue, checkout layer, and cross-pollination with other facilitators' participants.",
        "location": "Brooklyn, NY",
        "website_url": "https://example.com/aaron-kalu",
        "photo_url": "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=600",
        "is_founding_partner": False,
    },
    # ---- Vendors ----
    {
        "slug": "sample-quiet-hours-studio",
        "partner_type": "vendor",
        "display_name": "Quiet Hours Studio",
        "headline": "Linen-bound journals, prints, and reflection cards aligned with relational practice.",
        "bio": "One-person bindery making journals and prompt decks aligned with relational practice. Sam represents the small-batch craft vendor: 12 products in the catalog, three of which are bundled into Foundation workshop checkouts as optional supplements. Customer experience integrated end-to-end so participants don't bounce off-platform for workshop supplies.",
        "location": "Asheville, NC",
        "website_url": "https://example.com/quiet-hours",
        "photo_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600",
        "is_founding_partner": True,
    },
    {
        "slug": "sample-hearth-practice",
        "partner_type": "vendor",
        "display_name": "Hearth Practice",
        "headline": "Guided audio meditations and downloadable workbooks — digital studio.",
        "bio": "Digital-only vendor producing audio meditations and supplementary workbooks. Represents the lower-overhead vendor type — no physical inventory, instant fulfilment, sells through Birthright as primary distribution. Listed external site URL routes outbound clicks through Birthright's attribution tracker.",
        "location": "Remote",
        "website_url": "https://example.com/hearth-practice",
        "photo_url": "https://images.unsplash.com/photo-1507608616759-54f48f0af0ee?w=600",
        "is_founding_partner": False,
    },
    # ---- Community ----
    {
        "slug": "sample-pat-lindholm",
        "partner_type": "community",
        "display_name": "Reverend Pat Lindholm",
        "headline": "Lutheran pastor referring congregants to Birthright workshops.",
        "bio": "Senior pastor whose congregation runs grief and trauma support groups. Refers congregants to Birthright workshops as a complementary resource. Represents the faith-leader community partner: high-trust, low-volume, mission-aligned referrals from a single congregation network of about 300 active families.",
        "location": "Madison, WI",
        "website_url": "https://example.com/pat-lindholm",
        "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600",
        "is_founding_partner": True,
    },
    {
        "slug": "sample-liz-okonkwo",
        "partner_type": "community",
        "display_name": "Liz Okonkwo",
        "headline": "Wellness podcaster amplifying Birthright workshops with UTM-tagged referrals.",
        "bio": "Independent podcaster on healing and relationship work, 28K Instagram followers. Mentions Birthright workshops on the podcast with a UTM-tagged referral link. Represents the digital-creator community partner: higher volume, paid Plus tier for custom UTM analytics, drives 25–40 conversions per quarter when she actively promotes.",
        "location": "Atlanta, GA",
        "website_url": "https://example.com/liz-okonkwo",
        "photo_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600",
        "is_founding_partner": False,
    },
    # ---- Research ----
    {
        "slug": "sample-imani-okafor",
        "partner_type": "research",
        "display_name": "Dr. Imani Okafor",
        "headline": "Tenure-track developmental psychologist studying attachment in adoptive families.",
        "bio": "Tenure-track in developmental psychology at the University of Michigan. Studies attachment outcomes in adoptive and foster families. Publishes peer-reviewed findings through Birthright as one of several distribution channels. Represents the academic research partner: eminence-driven, foundation gains credibility from her affiliation, she gains a public-facing channel and DOI minting through the foundation.",
        "location": "Ann Arbor, MI",
        "website_url": "https://example.com/imani-okafor",
        "photo_url": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=600",
        "is_founding_partner": True,
    },
    {
        "slug": "sample-daniel-brookes",
        "partner_type": "research",
        "display_name": "Daniel Brookes, LMFT",
        "headline": "Practitioner-researcher publishing case studies from clinical work.",
        "bio": "Family therapist who publishes case studies and practice briefs distilled from his clinical work. Not affiliated with any university; uses Birthright as his sole publishing platform. Represents the practitioner-researcher persona — publishes 2–4 briefs per year, no monetization, contributes to the foundation's library of practitioner wisdom in exchange for credibility and discoverability.",
        "location": "Independent · Remote",
        "website_url": "https://example.com/daniel-brookes",
        "photo_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600",
        "is_founding_partner": False,
    },
]


async def ensure_sample_partners_seeded(db) -> int:
    """Insert sample partner profiles if absent (idempotent by slug).
    Marked is_sample: true; hidden from default /partners listing."""
    inserted = 0
    for spec in SAMPLE_PARTNER_PROFILES:
        if await db.partner_profiles.find_one({"slug": spec["slug"]}):
            continue
        now = now_iso()
        doc = {
            "id": gen_id(),
            "user_id": None,  # samples are not linked to a real user
            "partner_type": spec["partner_type"],
            "status": "active",
            "public": True,
            "is_sample": True,
            "slug": spec["slug"],
            "display_name": spec["display_name"],
            "headline": spec["headline"],
            "bio": spec["bio"],
            "website_url": spec.get("website_url"),
            "location": spec.get("location"),
            "photo_url": spec.get("photo_url"),
            "meta": {},
            "approved_at": now,
            "approved_by": "system-seed",
            "created_at": now,
            "updated_at": now,
            # v1.11.0 economy defaults
            "is_founding_partner": spec.get("is_founding_partner", False),
            "founding_rate_expires_at": None,
            "featured_until": None,
            "featured_mission_alignment": None,
            "featured_signature_content": None,
            "featured_video_url": None,
            "featured_image_urls": [],
            "featured_custom_cta": None,
            "external_site_url": spec.get("website_url"),
            "external_platform": None,
            "rev_share_overrides": None,
            "w9_status": "not_collected",
            "payout_threshold_usd": 50.0,
            "payout_method": None,
            "payout_address_snapshot": None,
        }
        await db.partner_profiles.insert_one(doc)
        inserted += 1
    if inserted:
        logger.info(f"sample partners seed: inserted {inserted} sample profiles")
    return inserted


# ---- Sample Research Artifacts (v1.11.0 step 6) ----

SAMPLE_RESEARCH_ARTIFACTS = [
    {
        "slug": "sample-attachment-adoptive-families-2024",
        "partner_slug": "sample-imani-okafor",
        "title": "Attachment Patterns in Adoptive Families: A Five-Year Longitudinal Study",
        "abstract": "We followed 312 adoptive families across the first five years post-placement. Children placed before age 18 months showed attachment-pattern outcomes statistically indistinguishable from biological-family controls by year 4 when caregivers received structured relational education in the first 90 days. Findings suggest that early relational intervention — not biological connection — is the dominant predictor of secure attachment in adoptive contexts.",
        "authors": "Imani Okafor, PhD; Sarah Mendez, MA; Daniel Thompson, MSW",
        "publication_date": "2024-11-15",
        "full_text_url": "https://example.com/research/attachment-adoptive-families",
        "doi": "10.1234/birthright.2024.imani.001",
        "cover_image_url": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=900",
        "categories": ["attachment", "adoption", "longitudinal"],
        "tags": ["peer-reviewed", "longitudinal", "adoptive-families", "secure-attachment"],
        "estimated_read_minutes": 32,
        "tier": "paper",
    },
    {
        "slug": "sample-co-regulation-brief-2025",
        "partner_slug": "sample-daniel-brookes",
        "title": "Co-Regulation Practices for Adult Children of Relational Trauma: A Practitioner Brief",
        "abstract": "Drawing on 14 years of clinical practice with adults processing childhood relational trauma, this brief offers four evidence-anchored co-regulation practices clinicians can introduce in the first three sessions. Each practice maps to a specific dysregulation pattern (hypervigilance, dissociation, somatic shutdown, anxious activation) and includes patient-friendly framings.",
        "authors": "Daniel Brookes, LMFT",
        "publication_date": "2025-02-20",
        "full_text_url": "https://example.com/research/co-regulation-brief",
        "doi": None,
        "cover_image_url": "https://images.unsplash.com/photo-1518578953934-78c01892a213?w=900",
        "categories": ["clinical-practice", "co-regulation", "trauma"],
        "tags": ["practitioner-brief", "co-regulation", "adult-survivors", "session-tools"],
        "estimated_read_minutes": 12,
        "tier": "brief",
    },
]


async def ensure_sample_research_artifacts(db) -> int:
    """Seed two illustrative research artifacts linked to the sample research partners.
    These give the /research page something to show during outreach demos."""
    inserted = 0
    for spec in SAMPLE_RESEARCH_ARTIFACTS:
        existing = await db.research_artifacts.find_one({"id": spec["slug"]})
        if existing:
            continue
        partner = await db.partner_profiles.find_one({"slug": spec["partner_slug"]}, {"_id": 0})
        if not partner:
            continue
        now = now_iso()
        doc = {
            "id": spec["slug"],
            "partner_id": partner["id"],
            "partner_slug": partner["slug"],
            "partner_display_name": partner["display_name"],
            "user_id": None,
            "title": spec["title"],
            "abstract": spec["abstract"],
            "authors": spec["authors"],
            "publication_date": spec["publication_date"],
            "full_text_url": spec["full_text_url"],
            "doi": spec["doi"],
            "cover_image_url": spec["cover_image_url"],
            "categories": spec["categories"],
            "tags": spec["tags"],
            "estimated_read_minutes": spec["estimated_read_minutes"],
            "tier": spec["tier"],
            "status": "published",
            "promoted_until": None,
            "view_count": 0,
            "is_sample": True,
            "created_at": now,
            "updated_at": now,
        }
        await db.research_artifacts.insert_one(doc)
        inserted += 1
    if inserted:
        logger.info(f"sample research artifacts seed: inserted {inserted} artifacts")
    return inserted




AGREEMENT_V2_BODY = """# Universal Indemnification & Hold-Harmless Agreement (v2.0)

**Updated May 25, 2026 — Birthright Foundation will replace this with counsel-reviewed copy before launch.**

By accepting this agreement, you acknowledge that:

1. **Voluntary participation.** Workshops, materials, and partner services are educational in nature. You participate at your own discretion.
2. **No professional advice.** Content is not a substitute for licensed mental-health, medical, or legal advice.
3. **Hold harmless.** You agree not to hold Birthright Foundation, its governing board, facilitators, vendors, research partners, or community partners liable for outcomes arising from your participation, except in cases of gross negligence or willful misconduct.
4. **Respectful conduct.** You agree to abide by the community standards and to engage facilitators, fellow participants, and partners with respect. Boundary violations may be reported to the ombudsman.
5. **Dispute resolution.** Disputes are first reviewed by the Birthright ombudsman. Resolution may include refunds via the platform's clawback cascade.
6. **Refund cascade (v2 addition).** When a payment is refunded via dispute resolution or admin action, derived partner credits are reversed automatically. Already-paid credits are queued for recovery; you agree to good-faith cooperation in any such recovery.
7. **Data & privacy.** Personal information you provide is governed by the Birthright privacy policy. Direct messages remain private unless flagged for ombudsman review.
8. **Versioning.** This agreement is versioned. Substantive changes require re-signing before further partner-facing activity.
"""


async def ensure_agreement_v2_published(db) -> bool:
    """Publish indemnification v2.0 if not already present. Idempotent. v1.0
    remains in the version history; v2.0 becomes active. Existing v1.0
    signatures are NOT auto-migrated — users must re-sign v2.
    """
    existing = await db.indemnification_versions.find_one({"version": "2.0"})
    if existing:
        return False
    # Deactivate any prior versions
    await db.indemnification_versions.update_many({"active": True}, {"$set": {"active": False}})
    v2 = {
        "id": gen_id(),
        "version": "2.0",
        "body": AGREEMENT_V2_BODY,
        "summary_of_changes": (
            "Adds explicit dispute-resolution / ombudsman language, the refund "
            "cascade clause, DM privacy reference, and good-faith clawback "
            "cooperation. Prior signatures (v1.0) do NOT carry over — partners "
            "and active workshop participants must re-sign on next session."
        ),
        "active": True,
        "created_by": "system",
        "created_at": now_iso(),
        "activated_at": now_iso(),
    }
    await db.indemnification_versions.insert_one(dict(v2))
    logger.info("Published indemnification agreement v2.0 as active")
    return True
