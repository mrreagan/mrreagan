"""Idempotent seed for demo Explore-before-Embrace prospects.

Companion to /app/backend/seed_data.py — extends the existing facilitator,
community, and vendor demo prospects with Research, Steward, and Artist
exemplars so admins see a fully-populated demo across all six partner types
on /admin/partners/prospects.

Each prospect is created in `invited` state with an active token so the
"View live preview" inline link is exercisable end-to-end without any
extra admin actions. Re-running this script is safe: it skips any prospect
whose email or display_name already exists.

Run: `python -m scripts.seed_demo_prospects` from /app/backend (or invoked
on server startup via routers.partner_prospects helper — TBD if desired).
"""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load env before importing app modules that read it at import time.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import gen_id, now_iso  # noqa: E402

logger = logging.getLogger("seed_demo_prospects")


def _interaction(channel: str, notes: str, by_name: str = "Birthright Admin",
                 by_id: str = "seed", responded: bool = False, days_ago: int = 0) -> dict:
    when = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return {
        "id": gen_id(),
        "channel": channel,
        "notes": notes,
        "occurred_at": when,
        "response_received": responded,
        "by_user_id": by_id,
        "by_user_name": by_name,
        "created_at": when,
    }


DEMO_PROSPECTS = [
    # --- Research ---
    {
        "partner_type": "research",
        "display_name": "Dr. Priya Raghavan",
        "contact_email": "priya.raghavan@example.org",
        "contact_phone": "",
        "location": "Toronto, ON",
        "headline_excerpt": "Attachment researcher — longitudinal repair studies",
        "bio_excerpt": (
            "Priya runs a small academic lab studying the micro-mechanics of "
            "relational repair across the lifespan. Her published work has "
            "shaped how a generation of clinicians think about rupture-and-repair "
            "cycles in adult attachment."
        ),
        "portfolio_url": "https://example.org/raghavan-lab",
        "social_url": "",
        "highlight_url": "https://example.org/raghavan-lab/papers/2025-repair",
        "highlight_image_url": "https://images.unsplash.com/photo-1532153975070-2e9ab71f1b14?w=1200",
        "highlight_label": "page",
        "highlight_excerpt": (
            "Repair is not a corrective conversation; it is the resumption of "
            "regulated co-presence after a measurable rupture. Our data suggest "
            "the half-life of a good repair sequence is roughly seventy-two hours."
        ),
        "highlight_reason": (
            "We've quietly cited this paragraph in three facilitator trainings. "
            "Her framing of repair as resumed co-presence — not a conversation — "
            "is the exact language Birthright uses, arrived at independently."
        ),
        "mission_alignment": (
            "Your work already does what Birthright tries to make ordinary: it "
            "treats repair as a measurable, teachable shape rather than a feeling. "
            "Partnering with us as a Research Partner would put a small institutional "
            "frame around scholarship you are clearly already producing, and give "
            "your findings a non-academic audience who needs them weekly."
        ),
        "referred_by": "Dr. Hannah Lin (Research Advisor)",
        "internal_notes": (
            "Two phone conversations. Open to a 12-month research collaboration "
            "if we cover IRB amendment costs. Wants editorial independence on "
            "any co-published material — agreed in principle."
        ),
        "initial_interactions": [
            ("email", "Sent intro email referencing the 2025 repair paper. Included our facilitator-training citation as proof of impact.", False, 28),
            ("phone", "30-min call. Priya was warm — asked thoughtful questions about how we'd handle data sharing and authorship.", True, 18),
            ("email", "Sent draft scope: 12-month observational collaboration on Birthright cohorts (opt-in only). She's reviewing with her co-PI.", False, 9),
        ],
        "suggested_tier": "annual",
    },

    # --- Steward ---
    {
        "partner_type": "steward",
        "display_name": "Joaquín Estrada",
        "contact_email": "joaquin.estrada@example.com",
        "contact_phone": "+1 (602) 555-0144",
        "location": "Phoenix, AZ",
        "headline_excerpt": "Master carpenter & community elder — Maryvale neighborhood",
        "bio_excerpt": (
            "Joaquín has spent forty-one years building, repairing, and "
            "occasionally rebuilding the homes of his neighbors. He runs a "
            "Saturday-morning open shop where anyone can bring a broken chair "
            "or a broken conversation and leave with both repaired."
        ),
        "portfolio_url": "",
        "social_url": "https://example.com/estrada-saturday-shop",
        "highlight_url": "https://example.com/estrada-saturday-shop/about",
        "highlight_image_url": "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=1200",
        "highlight_label": "mission",
        "highlight_excerpt": (
            "Nobody gets turned away from the shop. If you bring something "
            "broken and you stay long enough to drink one cup of coffee, you "
            "leave with it fixed. That is the whole rule. It has been the "
            "whole rule for forty-one years."
        ),
        "highlight_reason": (
            "This is stewardship in its plainest form — a person quietly holding "
            "open a doorway for four decades. He is already doing what we ask "
            "Stewards to do; the only thing we can add is recognition and a "
            "small monthly honorarium to keep the doors open."
        ),
        "mission_alignment": (
            "What you have kept alive for forty-one years is the exact thing "
            "Birthright tries to teach in two-day workshops: undefended presence, "
            "the patience to let people show up broken, and the steady hands to "
            "send them home a little less so. Joining as a Steward formalizes a "
            "role you have already carried for half your life — and lets the "
            "Foundation stand behind your Saturday-morning doorway."
        ),
        "referred_by": "Reverend Tomas Ifeanyi (Community Stewardship)",
        "internal_notes": (
            "Tomas has known Joaquín for 11 years. Joaquín is uncomfortable with "
            "the word 'mentor' but accepted 'steward' on second mention. Prefers "
            "phone over email. Will not accept a fee structure that exceeds his "
            "shop's monthly utilities (~$240/mo)."
        ),
        "initial_interactions": [
            ("in_person", "Tomas brought us to the Saturday shop. We watched for three hours. Joaquín repaired a dining chair while a teenager talked about his father. No one rushed.", False, 35),
            ("phone", "Called to thank him for the visit and ask if he'd consider a Steward role. He laughed; said he'd think on it.", True, 22),
            ("in_person", "Second visit. Joaquín agreed in principle to a Steward role — provided we never use the words 'mentor', 'coach', or 'curriculum' to describe what he does.", True, 11),
        ],
        "suggested_tier": "annual",
    },

    # --- Artist ---
    {
        "partner_type": "artist",
        "display_name": "Ines Whitfield",
        "contact_email": "ines.whitfield@example.com",
        "contact_phone": "",
        "location": "Asheville, NC",
        "headline_excerpt": "Textile artist — repair as visible craft",
        "bio_excerpt": (
            "Ines makes large-scale woven panels from her family's discarded "
            "linens. Each piece foregrounds the seam, the mend, the place where "
            "the cloth was almost lost. Her studio is open one Sunday a month."
        ),
        "portfolio_url": "https://example.com/ines-whitfield",
        "social_url": "https://example.com/ines-whitfield/journal",
        "highlight_url": "https://example.com/ines-whitfield/works/seam-series",
        "highlight_image_url": "https://images.unsplash.com/photo-1528459801416-a9e53bbf4e17?w=1200",
        "highlight_label": "product",
        "highlight_excerpt": (
            "The Seam Series began the year my grandmother died. I could not "
            "bear to discard her bedsheets and I could not bear to use them. "
            "So I cut them, and I sewed them, and I let the mending show."
        ),
        "highlight_reason": (
            "The Seam Series is the most precise visual rendering of repair-as-"
            "practice we've encountered. Three of our facilitators independently "
            "sent us the link in the same month."
        ),
        "mission_alignment": (
            "What you have been making since your grandmother died is a visual "
            "vocabulary for the work Birthright tries to teach in language: that "
            "the mend is the point, not the hiding of it. Partnering with us as "
            "a Featured Artist would let your work do its quiet teaching inside "
            "the spaces where our facilitators are doing theirs."
        ),
        "referred_by": "",
        "internal_notes": (
            "Three facilitators independently flagged her work. Ines has not yet "
            "responded to our email — sent two weeks ago. Soft outreach; she is "
            "famously private. Considering reaching out through her gallery."
        ),
        "initial_interactions": [
            ("email", "Sent introductory email with a single line: 'Three of our facilitators sent us your Seam Series in the same month. Would you be open to a conversation?'", False, 14),
            ("referral", "Gallery owner offered to forward our note personally. We accepted gratefully.", False, 6),
        ],
        "suggested_tier": "annual",
    },
]


async def _seed(db) -> dict:
    created, skipped = [], []
    admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0, "id": 1})
    created_by = admin_user["id"] if admin_user else "seed"

    for tpl in DEMO_PROSPECTS:
        # Idempotency: skip if email OR display_name already exists.
        q = {"$or": [{"display_name": tpl["display_name"]}]}
        if tpl.get("contact_email"):
            q["$or"].append({"contact_email": tpl["contact_email"].lower()})
        if await db.partner_prospects.find_one(q, {"_id": 0, "id": 1}):
            skipped.append(tpl["display_name"])
            continue

        now = now_iso()
        interactions = [
            _interaction(ch, notes, responded=resp, days_ago=days)
            for (ch, notes, resp, days) in tpl["initial_interactions"]
        ]

        # Build the prospect doc directly in the same shape as the
        # create_prospect endpoint produces (see routers/partner_prospects.py).
        prospect_id = gen_id()
        invite_id = gen_id()
        invite_token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        prospect = {
            "id": prospect_id,
            "partner_type": tpl["partner_type"],
            "display_name": tpl["display_name"],
            "contact_email": (tpl.get("contact_email") or "").lower() or None,
            "contact_phone": tpl.get("contact_phone") or None,
            "location": tpl.get("location") or None,
            "headline_excerpt": tpl.get("headline_excerpt") or None,
            "bio_excerpt": tpl.get("bio_excerpt") or None,
            "portfolio_url": tpl.get("portfolio_url") or None,
            "social_url": tpl.get("social_url") or None,
            "highlight_url": tpl.get("highlight_url") or None,
            "highlight_image_url": tpl.get("highlight_image_url") or None,
            "highlight_label": tpl.get("highlight_label") or "site",
            "highlight_excerpt": tpl.get("highlight_excerpt") or None,
            "highlight_reason": tpl.get("highlight_reason") or None,
            "mission_alignment": tpl.get("mission_alignment") or None,
            "referred_by": tpl.get("referred_by") or None,
            "internal_notes": tpl.get("internal_notes") or None,
            "status": "invited",
            "foundation_score": None,
            "interactions": interactions,
            "promoted_to_user_id": None,
            "promoted_to_partner_id": None,
            "active_invite_id": invite_id,
            "active_invite_token": invite_token,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }

        invite = {
            "id": invite_id,
            "token": invite_token,
            "prospect_id": prospect_id,
            "partner_type": tpl["partner_type"],
            "display_name": tpl["display_name"],
            "contact_email": prospect["contact_email"],
            "default_headline": prospect["headline_excerpt"],
            "default_bio": prospect["bio_excerpt"] or "",
            "highlight_url": prospect["highlight_url"],
            "highlight_image_url": prospect["highlight_image_url"],
            "highlight_label": prospect["highlight_label"],
            "highlight_excerpt": prospect["highlight_excerpt"],
            "highlight_reason": prospect["highlight_reason"],
            "mission_alignment": prospect["mission_alignment"],
            "note_to_prospect": None,
            "suggested_subscription_tier": tpl.get("suggested_tier"),
            "status": "sent",
            "preview_count": 0,
            "preview_last_at": None,
            "accepted_at": None,
            "accepted_user_id": None,
            "accepted_partner_id": None,
            "accepted_partner_slug": None,
            "declined_at": None,
            "declined_reason": None,
            "created_by": created_by,
            "created_at": now,
            "expires_at": expires_at,
        }

        await db.partner_prospects.insert_one(dict(prospect))
        await db.partner_invites.insert_one(dict(invite))
        created.append({
            "type": tpl["partner_type"],
            "name": tpl["display_name"],
            "preview_url": f"/partner/invite/{invite_token}",
        })

    return {"created": created, "skipped": skipped}


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    result = await _seed(db)
    print("SEED RESULT:")
    print(f"  Created: {len(result['created'])}")
    for c in result["created"]:
        print(f"    [{c['type']:>11}] {c['name']}  →  {c['preview_url']}")
    print(f"  Skipped (already present): {len(result['skipped'])}")
    for s in result["skipped"]:
        print(f"    - {s}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
