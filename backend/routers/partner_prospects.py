"""Generic Partner Prospects + Explore-before-Embrace Invitations.

Companion to /app/backend/routers/gallery.py — gallery defined the pattern for
Artists; this module generalizes it to every other partner_type:
facilitator, community, research, vendor, steward, and artist (so the
Foundation has ONE prospect tracker covering all six).

Pattern recap:
  1. Foundation leaders log a prospect (with contact info + interaction history)
  2. They issue a tokenized invite — no user account exists yet
  3. The invited person browses a fully pre-curated mock of their dashboard
     + sees all options + sees what acceptance means — no commitment to look
  4. They click Accept → atomically: create user account + partner profile
     + (optional) subscription stub + JWT auto-login. Decline is one click.

The per-type preview spec (defaults, options, obligations, what they keep,
foundation share) lives in PREVIEW_SPECS below — easy to tune per type.
"""
from __future__ import annotations

import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user, require_roles, hash_password, create_token
from models import gen_id, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.partner_prospects")

# All endpoints live under /partners/admin/* or /partners/invite/* — same
# prefix as routers.partners (so server.py only mounts one root)
router = APIRouter(prefix="/partners", tags=["partner-prospects"])

PARTNER_TYPES = ("facilitator", "community", "research", "vendor", "artist", "steward")
PROSPECT_CHANNELS = (
    "email", "phone", "text", "in_person", "studio_visit",
    "social_dm", "referral", "event", "other",
)


# ============ Per-type preview specs ============
# Each spec is what an invited prospect SEES on the public preview page,
# rendered without auth. It models the role: defaults the foundation has
# picked for them, the menu of options they can configure, what they're
# agreeing to, and what stays in their control. Tweak freely.

def _layout_choices():
    return ["single-wall", "two-column", "salon-hang", "audio-forward"]

def _accents():
    return [
        {"key": "flame", "label": "Flame", "hex": "#9E3C3C"},
        {"key": "moss", "label": "Moss", "hex": "#476B6B"},
        {"key": "river", "label": "River", "hex": "#3F5C73"},
        {"key": "ochre", "label": "Ochre", "hex": "#C9A961"},
        {"key": "indigo", "label": "Indigo", "hex": "#3A3A6B"},
        {"key": "graphite", "label": "Graphite", "hex": "#3A3A3A"},
    ]


PREVIEW_SPECS: dict[str, dict] = {
    "facilitator": {
        "title": "Facilitator",
        "blurb": "Lead workshops in the Birthright tradition. Bring Birthright IP into your room, or your own materials, or both — pricing tiers reflect the mix.",
        "default_headline": "Workshop facilitator",
        "default_bio_hint": "Two or three sentences about your work and what brings you to facilitating.",
        "options": {
            "subscription_tiers": [
                {"key": "monthly", "label": "Monthly · $99", "rev_share_birthright_ip": 70, "rev_share_other": 50},
                {"key": "annual", "label": "Annual · $999", "rev_share_birthright_ip": 65, "rev_share_other": 45, "ribbon": "Most chosen"},
                {"key": "two_year", "label": "2-year · $1,799", "rev_share_birthright_ip": 60, "rev_share_other": 40},
            ],
            "presents_birthright_ip_choice": "Choose at enrollment: do you present Birthright IP, your own materials, or both?",
            "media": [
                "Profile photo + headline + bio",
                "Sample curriculum URL",
                "Training history",
                "Workshop calendar (your published events)",
                "Public reviews on your facilitator profile",
            ],
        },
        "what_acceptance_means": {
            "summary": "Enrolling creates your Birthright Facilitator account + partner profile. You sign the universal Partnership Agreement + Indemnification once, choose a subscription tier, and can immediately list workshops.",
            "obligations": [
                "Sign the universal Partnership Agreement + Indemnification (one-time).",
                "Honestly declare whether each workshop presents Birthright IP or your own materials (drives the dual-tier rev share).",
                "Hold yourself to the Birthright facilitator ethics framework.",
            ],
            "you_keep": [
                "Your own intellectual property and curricula — Birthright never claims them.",
                "Your teaching calendar and your pricing on your own materials.",
                "The ability to pause your subscription or step back at any time.",
            ],
            "foundation_share": "30% on Birthright IP workshops (per dual-tier rev share); 50% on workshops using your own materials at the monthly tier (rates improve with longer subscription).",
        },
    },

    "community": {
        "title": "Community partner",
        "blurb": "Refer your audience to Birthright. Every order attributed to you pays a commission. No quotas, no exclusivity, no inventory.",
        "default_headline": "Community partner",
        "default_bio_hint": "Where does your audience hang out? Newsletter? Podcast? Local circles?",
        "options": {
            "subscription_tiers": [
                {"key": "monthly", "label": "Monthly · $29", "rev_share": 12},
                {"key": "annual", "label": "Annual · $299", "rev_share": 10, "ribbon": "Most chosen"},
                {"key": "two_year", "label": "2-year · $549", "rev_share": 8},
            ],
            "media": [
                "Per-user referral code + per-workshop affiliate links",
                "Earnings dashboard (pending + lifetime + paid)",
                "Recent attributions table",
                "Optional: featured organization page",
            ],
        },
        "what_acceptance_means": {
            "summary": "Enrolling creates your Birthright Community Partner account. You get a personal referral code and per-workshop affiliate links. Every order attributed to your code pays the commission tier above.",
            "obligations": [
                "Sign the universal Partnership Agreement + Indemnification (one-time).",
                "Represent Birthright honestly to your audience — no misleading claims.",
                "Self-attribution is blocked (you can't earn commission on your own purchases).",
            ],
            "you_keep": [
                "Your own audience, channels, mailing list — unchanged.",
                "100% control of how you talk about Birthright (within the truth).",
                "The option to leave at any time; earned but unpaid commissions still pay out.",
            ],
            "foundation_share": "88% — 92% of the order goes to the foundation; you keep the commission tier (12% / 10% / 8% with longer subscriptions).",
        },
    },

    "research": {
        "title": "Research collaborator",
        "blurb": "Submit research artifacts to a moderated, attributed catalog. By default this is a grant-funded role — no rev share, but full intellectual ownership and visibility.",
        "default_headline": "Research collaborator",
        "default_bio_hint": "Affiliation, area of research, recent publications.",
        "options": {
            "subscription_tiers": [
                {"key": "monthly", "label": "Monthly · $49", "rev_share": 0, "blurb": "Optional — most research collaborators are grant-funded."},
                {"key": "annual", "label": "Annual · $499", "rev_share": 0},
                {"key": "two_year", "label": "2-year · $899", "rev_share": 0},
            ],
            "media": [
                "Artifact submissions (paper, dataset, study summary)",
                "Public profile w/ institution + ORCID-style ID",
                "Moderation queue → published listing on /partners?tab=research",
                "Co-author + attribution metadata preserved through publication",
            ],
        },
        "what_acceptance_means": {
            "summary": "Enrolling creates your Research Collaborator account. You can submit artifacts immediately; they enter the admin moderation queue for review before public listing.",
            "obligations": [
                "Sign the universal Partnership Agreement (one-time).",
                "Adhere to Birthright's research attribution standards.",
                "Disclose conflicts of interest when relevant.",
            ],
            "you_keep": [
                "Full intellectual ownership of your work.",
                "Your institutional affiliation and identity.",
                "The option to remove your artifact at any time (publication-history note preserved).",
            ],
            "foundation_share": "0% — research is a grant-funded role in v1. Optional subscription supports operations.",
        },
    },

    "vendor": {
        "title": "Vendor partner",
        "blurb": "Sell physical goods through Birthright. AI-designed mockups, POD fulfillment via Printful or Lulu, or referral-mode back to your own shop. You set list prices; Birthright handles the customer side.",
        "default_headline": "Maker · Vendor partner",
        "default_bio_hint": "What do you make? What story does it tell?",
        "options": {
            "subscription_tiers": [
                {"key": "monthly", "label": "Monthly · $49", "rev_share": 82},
                {"key": "annual", "label": "Annual · $499", "rev_share": 78, "ribbon": "Most chosen"},
                {"key": "two_year", "label": "2-year · $899", "rev_share": 75},
            ],
            "fulfillment_modes": [
                {"key": "printful", "label": "Print-on-demand (Printful)", "blurb": "Apparel, mugs — Birthright handles fulfillment."},
                {"key": "lulu", "label": "Print-on-demand (Lulu)", "blurb": "Journals, notebooks — Birthright handles fulfillment."},
                {"key": "off_site", "label": "Referral to your own store", "blurb": "We send buyers to you with a ?via= attribution tag."},
                {"key": "manual", "label": "Foundation-fulfilled", "blurb": "Inventory + ship through Birthright (case-by-case)."},
            ],
            "media": [
                "AI Studio (Claude copy + Nano Banana mockups) for new product drafts",
                "Vendor catalog moderation status pills",
                "Sales report + earnings dashboard",
                "Per-product Buy-on-vendor-site CTA in off-site mode",
            ],
        },
        "what_acceptance_means": {
            "summary": "Enrolling creates your Vendor Partner account + AI Studio access. Every draft enters admin moderation before going live. You set list prices; Birthright adds shipping/checkout on top.",
            "obligations": [
                "Sign the universal Partnership Agreement + Indemnification (one-time).",
                "Attest that list prices here match your own gallery / external store (no Birthright undercut).",
                "Comply with product moderation policy (no harmful, deceptive, or trademark-infringing goods).",
            ],
            "you_keep": [
                "Your brand, your store, your customer relationships outside Birthright.",
                "100% of the gross on off-site referrals (we don't touch the money).",
                "The option to pause or unlist products at any time.",
            ],
            "foundation_share": "18%–25% on POD orders (you keep 82% / 78% / 75% with longer subscriptions). 0% on off-site referrals — we're paid only by your subscription.",
        },
    },

    "artist": {
        "title": "Artist partner",
        "blurb": "Show your practice in the Birthright Gallery. Sell at YOUR list price; we add a 20% foundation markup transparently at checkout. The buyer sees the math.",
        "default_headline": "Artist · Gallery partner",
        "default_bio_hint": "Mediums, what your practice circles around, why you make.",
        "options": {
            "media": [
                "Curated gallery space (single-wall / two-column / salon-hang / audio-forward layout)",
                "Up to 8 featured works at a time",
                "Hero image, studio photo, audio intro, video reel",
                "Commission inquiries + open studio schedule",
                "Eligible for monthly Featured Artist slot (foundation or community-nominated)",
            ],
            "accent_colors": _accents(),
            "layouts": _layout_choices(),
        },
        "what_acceptance_means": {
            "summary": "Enrolling creates your Artist Partner account + gallery space. You can list works immediately; Birthright adds the 20% foundation markup at checkout (buyer sees the breakdown).",
            "obligations": [
                "Sign the universal Partnership Agreement (one-time).",
                "Attest that your Birthright list price matches your own gallery's list price (no undercut).",
                "Honestly represent medium, edition, dimensions on each work.",
            ],
            "you_keep": [
                "100% ownership of work and image.",
                "Your own external gallery, social, mailing list — untouched.",
                "Pricing, availability, commission policy — all yours.",
            ],
            "foundation_share": "20% added on top of your list price at checkout. Buyer sees the breakdown. The 20% funds the foundation's free programming.",
        },
    },

    "steward": {
        "title": "Community Steward",
        "blurb": "Moderate a specific Gather community. Volunteer role — not monetary — but core to keeping the space safe and warm. You set hours, escalate hard cases, and step back any time.",
        "default_headline": "Community Steward",
        "default_bio_hint": "Your ties to the community you'd steward — neighborhood, group, organization.",
        "options": {
            "media": [
                "Stewardship dashboard for the assigned community",
                "Post moderation queue (flag, hide, remove)",
                "Member directory + privacy controls",
                "Escalation channel to Foundation ombudsman",
            ],
            "policies": [
                "Choose your moderation hours per week (commitment-free flex)",
                "Set automatic-flag rules (slurs, doxx, scam patterns)",
                "Configure community-specific posting rules",
            ],
        },
        "what_acceptance_means": {
            "summary": "Enrolling creates your Steward account scoped to the community you've been invited to moderate. No subscription, no rev share — you sign the Partnership Agreement + Stewardship Code of Conduct.",
            "obligations": [
                "Sign the Partnership Agreement + Stewardship Code of Conduct (one-time).",
                "Apply moderation policies fairly + transparently — log every action.",
                "Escalate disputes you can't resolve to the Foundation ombudsman.",
            ],
            "you_keep": [
                "The ability to step back at any time — no contractual lock-in.",
                "Recusal rights when you have a conflict of interest.",
                "Anonymity from your moderation logs in public-facing views.",
            ],
            "foundation_share": "Not a monetary role. The foundation supports stewards through training, ombudsman backing, and recognition (your stewardship history travels with you).",
        },
    },
}


def get_preview_spec(partner_type: str) -> dict:
    if partner_type not in PREVIEW_SPECS:
        raise HTTPException(404, f"Unknown partner type: {partner_type}")
    spec = dict(PREVIEW_SPECS[partner_type])
    spec["partner_type"] = partner_type
    return spec


# ============ Models ============

class ProspectCreate(BaseModel):
    partner_type: Literal["facilitator", "community", "research", "vendor", "artist", "steward"]
    display_name: str = Field(min_length=2, max_length=200)
    contact_email: Optional[str] = Field(default=None, max_length=200)
    contact_phone: Optional[str] = Field(default=None, max_length=80)
    location: Optional[str] = Field(default=None, max_length=200)
    headline_excerpt: Optional[str] = Field(default=None, max_length=400)
    bio_excerpt: Optional[str] = Field(default=None, max_length=4000)
    portfolio_url: Optional[str] = Field(default=None, max_length=600)
    social_url: Optional[str] = Field(default=None, max_length=600)
    referred_by: Optional[str] = Field(default=None, max_length=200)
    internal_notes: Optional[str] = Field(default=None, max_length=4000)
    initial_interaction_channel: Optional[Literal[
        "email", "phone", "text", "in_person", "studio_visit",
        "social_dm", "referral", "event", "other",
    ]] = None
    initial_interaction_notes: Optional[str] = Field(default=None, max_length=4000)


class ProspectUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    contact_email: Optional[str] = Field(default=None, max_length=200)
    contact_phone: Optional[str] = Field(default=None, max_length=80)
    location: Optional[str] = Field(default=None, max_length=200)
    headline_excerpt: Optional[str] = Field(default=None, max_length=400)
    bio_excerpt: Optional[str] = Field(default=None, max_length=4000)
    portfolio_url: Optional[str] = Field(default=None, max_length=600)
    social_url: Optional[str] = Field(default=None, max_length=600)
    referred_by: Optional[str] = Field(default=None, max_length=200)
    internal_notes: Optional[str] = Field(default=None, max_length=4000)
    foundation_score: Optional[int] = Field(default=None, ge=0, le=5)
    status: Optional[Literal[
        "outreach_sent", "responded_interested", "in_conversation",
        "invited", "responded_declined", "dormant",
        "promoted", "archived",
    ]] = None


class ProspectInteraction(BaseModel):
    channel: Literal[
        "email", "phone", "text", "in_person", "studio_visit",
        "social_dm", "referral", "event", "other",
    ]
    notes: str = Field(min_length=2, max_length=8000)
    occurred_at: Optional[str] = None
    response_received: Optional[bool] = False


class ProspectPromote(BaseModel):
    """Issue an Explore-before-Embrace invitation. We do NOT create the user
    account here — that happens only on Accept."""
    note_to_prospect: Optional[str] = Field(default=None, max_length=2000,
        description="Optional personalized note shown in the email + at top of the preview.")
    suggested_subscription_tier: Optional[str] = Field(default=None,
        description="One of the spec's subscription_tier keys (e.g. 'annual'). Surfaces as the default on the preview.")


class InviteAccept(BaseModel):
    password: str = Field(min_length=8, max_length=200)
    agreed_to_partnership_terms: bool = Field(
        description="Must be true. Confirms the prospect has read and accepted the partner-type's terms.")
    display_name_confirm: Optional[str] = Field(default=None, max_length=200)
    selected_subscription_tier: Optional[str] = Field(default=None,
        description="One of the spec's subscription_tier keys.")
    selected_options: Optional[dict] = Field(default=None,
        description="Free-form per-type option snapshot (e.g. fulfillment_mode for vendors, presents_birthright_ip for facilitators).")


class InviteDecline(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=4000)


# ============ Helpers ============

def _slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:80] or "partner"


def _prospect_doc(p: dict) -> dict:
    return {k: v for k, v in p.items() if k != "_id"}


def _invite_public_slice(inv: dict) -> dict:
    """What the public sees when they hit GET /partners/invite/{token}."""
    return {
        "partner_type": inv.get("partner_type"),
        "display_name": inv.get("display_name"),
        "note_to_prospect": inv.get("note_to_prospect"),
        "suggested_subscription_tier": inv.get("suggested_subscription_tier"),
        "default_headline": inv.get("default_headline"),
        "default_bio": inv.get("default_bio"),
        "status": inv.get("status"),
        "expires_at": inv.get("expires_at"),
        "preview_count": inv.get("preview_count", 0),
        "accepted_at": inv.get("accepted_at"),
        "accepted_partner_slug": inv.get("accepted_partner_slug"),
        "declined_at": inv.get("declined_at"),
    }


async def _resolve_invite(db, token: str, mark_preview: bool = False) -> dict:
    inv = await db.partner_invites.find_one({"token": token}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Invitation not found")
    try:
        if inv.get("expires_at"):
            exp = datetime.fromisoformat(inv["expires_at"])
            now_utc = datetime.now(exp.tzinfo or timezone.utc)
            if exp < now_utc and inv.get("status") not in ("accepted", "declined", "expired"):
                await db.partner_invites.update_one(
                    {"token": token}, {"$set": {"status": "expired"}},
                )
                inv["status"] = "expired"
    except (ValueError, TypeError):
        pass
    if mark_preview and inv.get("status") in ("sent", "previewed"):
        await db.partner_invites.update_one(
            {"token": token},
            {"$inc": {"preview_count": 1},
             "$set": {"status": "previewed", "preview_last_at": now_iso()}},
        )
        inv["status"] = "previewed"
        inv["preview_count"] = (inv.get("preview_count") or 0) + 1
    return inv


def _email_subject(partner_type: str, display_name: str) -> str:
    spec = PREVIEW_SPECS.get(partner_type, {})
    title = spec.get("title") or partner_type.title()
    return f"You're invited — Birthright {title}"


def _email_html(partner_type: str, prospect_name: str, note: Optional[str], preview_url: str) -> str:
    spec = PREVIEW_SPECS.get(partner_type, {})
    title = spec.get("title", partner_type.title())
    blurb = spec.get("blurb", "")
    note_block = (
        f"<blockquote style=\"border-left:3px solid #C9A961;padding:8px 14px;"
        f"color:#1A2424;font-style:italic;margin:18px 0;background:#FAF8F5\">{note}</blockquote>"
    ) if note else ""
    return (
        f"<div style=\"font-family:Georgia,serif;color:#1A2424;max-width:580px;line-height:1.6\">"
        f"<h2 style=\"font-weight:400;font-size:24px\">Hi {prospect_name},</h2>"
        f"<p>The Birthright Foundation would like to invite you to partner with us as a <strong>{title}</strong>.</p>"
        f"<p style=\"font-size:14px;color:#5C6B6B\">{blurb}</p>"
        f"{note_block}"
        f"<div style=\"background:#FAF8F5;border:1px solid #E5DDD0;border-radius:8px;padding:18px;margin:24px 0\">"
        f"<p style=\"font-size:13px;color:#5C6B6B;margin:0 0 6px 0\">Default selections you can change:</p>"
        f"<ul style=\"font-size:13px;color:#1A2424;padding-left:20px;line-height:1.7;margin:0\">"
        f"<li>A pre-filled dashboard ready for you to explore</li>"
        f"<li>Suggested subscription tier (you pick your own)</li>"
        f"<li>Sample bio + headline drawn from what we know about your practice</li>"
        f"<li>Every option you can configure, displayed up front</li>"
        f"</ul></div>"
        f"<div style=\"background:#FAF8F5;border-left:3px solid #C9A961;padding:14px 18px;margin:24px 0;"
        f"font-size:13px;color:#5C6B6B\">"
        f"<strong style=\"color:#1A2424\">No commitment to look around.</strong> Explore the role first. You only enroll when "
        f"you click <em>Accept &amp; enroll</em> on the preview."
        f"</div>"
        f"<p style=\"text-align:center;margin:32px 0\">"
        f"<a href=\"{preview_url}\" style=\"display:inline-block;background:#9E3C3C;"
        f"color:#fff;padding:14px 28px;text-decoration:none;border-radius:4px;font-family:Georgia,serif;font-size:16px\">"
        f"Open your {title} preview →</a>"
        f"</p>"
        f"<p style=\"font-size:12px;color:#8A9494;margin-top:32px\">"
        f"This link is private to you. It expires in 30 days. Decline directly from the preview if it's not a fit. "
        f"Reply to this email — a real person will read it. — Birthright Foundation</p>"
        f"</div>"
    )


def _email_text(partner_type: str, prospect_name: str, preview_url: str) -> str:
    spec = PREVIEW_SPECS.get(partner_type, {})
    title = spec.get("title", partner_type.title())
    blurb = spec.get("blurb", "")
    return (
        f"Hi {prospect_name},\n\n"
        f"The Birthright Foundation would like to invite you to partner with us as a {title}.\n\n"
        f"{blurb}\n\n"
        f"We've drafted a full preview of your dashboard with sensible default selections.\n"
        f"Explore it freely — no commitment to look. You only enroll when you click 'Accept & enroll' on the preview.\n\n"
        f"Open your preview: {preview_url}\n\n"
        f"This link is private. It expires in 30 days. Reply to this email if anything's off.\n— Birthright Foundation\n"
    )


# ============ Admin — Prospects CRUD + Interactions ============

@router.get("/admin/prospects")
async def list_prospects(
    user: dict = Depends(require_roles("admin")),
    partner_type: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
):
    from database import db
    query: dict = {}
    if partner_type and partner_type != "all":
        if partner_type not in PARTNER_TYPES:
            raise HTTPException(400, f"Unknown partner_type: {partner_type}")
        query["partner_type"] = partner_type
    if status and status != "all":
        query["status"] = status
    if q and len(q.strip()) >= 2:
        rx = re.escape(q.strip())
        query["$or"] = [
            {"display_name": {"$regex": rx, "$options": "i"}},
            {"location": {"$regex": rx, "$options": "i"}},
            {"headline_excerpt": {"$regex": rx, "$options": "i"}},
            {"bio_excerpt": {"$regex": rx, "$options": "i"}},
            {"internal_notes": {"$regex": rx, "$options": "i"}},
        ]
    rows = await db.partner_prospects.find(query, {"_id": 0}).sort("updated_at", -1).to_list(limit)
    counts_by_type: dict[str, int] = {}
    counts_by_status: dict[str, int] = {}
    async for r in db.partner_prospects.aggregate([
        {"$group": {"_id": {"t": "$partner_type", "s": "$status"}, "n": {"$sum": 1}}},
    ]):
        t = (r["_id"] or {}).get("t") or "unknown"
        s = (r["_id"] or {}).get("s") or "unknown"
        counts_by_type[t] = counts_by_type.get(t, 0) + r["n"]
        counts_by_status[s] = counts_by_status.get(s, 0) + r["n"]
    return {"prospects": rows, "counts_by_type": counts_by_type, "counts_by_status": counts_by_status}


@router.post("/admin/prospects")
async def create_prospect(data: ProspectCreate, user: dict = Depends(require_roles("admin"))):
    from database import db
    now = now_iso()
    interactions: list[dict] = []
    if data.initial_interaction_channel:
        interactions.append({
            "id": gen_id(),
            "channel": data.initial_interaction_channel,
            "notes": (data.initial_interaction_notes or "Initial outreach").strip(),
            "occurred_at": now,
            "response_received": False,
            "by_user_id": user["id"],
            "by_user_name": (f"{user.get('first_name','')} {user.get('last_name','')}".strip() or user.get("email")),
            "created_at": now,
        })
    doc = {
        "id": gen_id(),
        "partner_type": data.partner_type,
        "display_name": data.display_name.strip(),
        "contact_email": (data.contact_email or "").strip().lower() or None,
        "contact_phone": (data.contact_phone or "").strip() or None,
        "location": (data.location or "").strip() or None,
        "headline_excerpt": (data.headline_excerpt or "").strip() or None,
        "bio_excerpt": (data.bio_excerpt or "").strip() or None,
        "portfolio_url": (data.portfolio_url or "").strip() or None,
        "social_url": (data.social_url or "").strip() or None,
        "referred_by": (data.referred_by or "").strip() or None,
        "internal_notes": (data.internal_notes or "").strip() or None,
        "status": "outreach_sent",
        "foundation_score": None,
        "interactions": interactions,
        "promoted_to_user_id": None,
        "promoted_to_partner_id": None,
        "active_invite_id": None,
        "active_invite_token": None,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.partner_prospects.insert_one(dict(doc))
    await log_action(
        db, user, "partner.prospect.create",
        target_type="partner_prospect", target_id=doc["id"],
        metadata={"display_name": doc["display_name"], "partner_type": data.partner_type},
    )
    return _prospect_doc(doc)


@router.get("/admin/prospects/{prospect_id}")
async def get_prospect(prospect_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    p = await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Prospect not found")
    return _prospect_doc(p)


@router.put("/admin/prospects/{prospect_id}")
async def update_prospect(prospect_id: str, data: ProspectUpdate,
                          user: dict = Depends(require_roles("admin"))):
    from database import db
    p = await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Prospect not found")
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(400, "Nothing to update")
    updates["updated_at"] = now_iso()
    await db.partner_prospects.update_one({"id": prospect_id}, {"$set": updates})
    return _prospect_doc(await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0}))


@router.delete("/admin/prospects/{prospect_id}")
async def delete_prospect(prospect_id: str, user: dict = Depends(require_roles("admin"))):
    from database import db
    p = await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Prospect not found")
    await db.partner_prospects.delete_one({"id": prospect_id})
    return {"ok": True}


@router.post("/admin/prospects/{prospect_id}/interactions")
async def add_interaction(prospect_id: str, data: ProspectInteraction,
                          user: dict = Depends(require_roles("admin"))):
    from database import db
    p = await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Prospect not found")
    now = now_iso()
    interaction = {
        "id": gen_id(),
        "channel": data.channel,
        "notes": data.notes.strip(),
        "occurred_at": data.occurred_at or now,
        "response_received": bool(data.response_received),
        "by_user_id": user["id"],
        "by_user_name": (f"{user.get('first_name','')} {user.get('last_name','')}".strip() or user.get("email")),
        "created_at": now,
    }
    set_doc = {"updated_at": now}
    if data.response_received and p.get("status") in (None, "outreach_sent", "dormant"):
        set_doc["status"] = "responded_interested"
    await db.partner_prospects.update_one(
        {"id": prospect_id},
        {"$push": {"interactions": interaction}, "$set": set_doc},
    )
    return _prospect_doc(await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0}))


@router.post("/admin/prospects/{prospect_id}/promote")
async def promote_prospect(prospect_id: str, data: ProspectPromote,
                           user: dict = Depends(require_roles("admin"))):
    """Issue a tokenized Explore-before-Embrace invitation."""
    from database import db
    p = await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Prospect not found")
    if not (p.get("contact_email") or "").strip():
        raise HTTPException(400, "Add a contact_email to the prospect before issuing an invitation.")
    spec = PREVIEW_SPECS.get(p["partner_type"]) or {}
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    invite = {
        "id": gen_id(),
        "token": secrets.token_urlsafe(32),
        "prospect_id": prospect_id,
        "partner_type": p["partner_type"],
        "display_name": p["display_name"],
        "contact_email": p["contact_email"],
        "default_headline": p.get("headline_excerpt") or spec.get("default_headline"),
        "default_bio": p.get("bio_excerpt") or "",
        "note_to_prospect": (data.note_to_prospect or "").strip() or None,
        "suggested_subscription_tier": data.suggested_subscription_tier,
        "status": "sent",
        "preview_count": 0,
        "preview_last_at": None,
        "accepted_at": None,
        "accepted_user_id": None,
        "accepted_partner_id": None,
        "accepted_partner_slug": None,
        "declined_at": None,
        "declined_reason": None,
        "created_by": user["id"],
        "created_at": now_iso(),
        "expires_at": expires_at,
    }
    await db.partner_invites.insert_one(dict(invite))
    await db.partner_prospects.update_one(
        {"id": prospect_id},
        {"$set": {
            "status": "invited",
            "active_invite_id": invite["id"],
            "active_invite_token": invite["token"],
            "updated_at": now_iso(),
        }},
    )
    # Email (dry-run safe)
    try:
        from utils.mailer import send_email
        app_url = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
        preview_url = f"{app_url}/partner/invite/{invite['token']}"
        await send_email(
            to=p["contact_email"],
            subject=_email_subject(p["partner_type"], p["display_name"]),
            html=_email_html(p["partner_type"], p["display_name"], invite["note_to_prospect"], preview_url),
            text=_email_text(p["partner_type"], p["display_name"], preview_url),
            template_name="partner_foundation_invite",
            metadata={"invite_id": invite["id"], "partner_type": p["partner_type"]},
        )
    except Exception as ex:
        logger.warning("Partner invite email failed: %s", ex)
    await log_action(
        db, user, "partner.prospect.invite_sent",
        target_type="partner_prospect", target_id=prospect_id,
        metadata={"invite_id": invite["id"], "partner_type": p["partner_type"]},
    )
    return {
        "prospect": _prospect_doc(await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0})),
        "invite": {k: v for k, v in invite.items() if k != "_id"},
        "preview_url": f"/partner/invite/{invite['token']}",
    }


@router.get("/admin/invites")
async def list_invites(
    user: dict = Depends(require_roles("admin")),
    partner_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
):
    from database import db
    query: dict = {}
    if partner_type and partner_type != "all":
        query["partner_type"] = partner_type
    if status and status != "all":
        query["status"] = status
    rows = await db.partner_invites.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    counts: dict[str, int] = {}
    async for r in db.partner_invites.aggregate([
        {"$group": {"_id": "$status", "n": {"$sum": 1}}},
    ]):
        counts[r["_id"] or "unknown"] = r["n"]
    return {"invites": rows, "counts": counts}


# ============ Public — Per-type preview specs (no auth) ============

@router.get("/preview-specs")
async def public_preview_index():
    """Public — full preview index for the /partner/types comparison page."""
    return {pt: PREVIEW_SPECS[pt] for pt in PARTNER_TYPES}


@router.get("/preview-specs/{partner_type}")
async def public_preview_spec(partner_type: str):
    """Public — return the per-type spec used by /partner/types/{type}/try."""
    return get_preview_spec(partner_type)


# ============ Public — Tokenized Invite Preview / Accept / Decline ============

@router.get("/invite/{token}")
async def view_invite(token: str):
    """PUBLIC — Explore-before-Embrace preview. Increments preview_count."""
    from database import db
    inv = await _resolve_invite(db, token, mark_preview=True)
    spec = get_preview_spec(inv["partner_type"])
    return {
        "invite": _invite_public_slice(inv),
        "spec": spec,
    }


@router.post("/invite/{token}/accept")
async def accept_invite(token: str, data: InviteAccept):
    """PUBLIC — Atomically: create user account + partner_profile (status=active, source=foundation) + return JWT."""
    from database import db
    inv = await _resolve_invite(db, token)
    if inv.get("status") == "accepted":
        raise HTTPException(400, "This invitation has already been accepted.")
    if inv.get("status") in ("declined", "expired"):
        raise HTTPException(400, f"This invitation is {inv['status']} and cannot be accepted.")
    if not data.agreed_to_partnership_terms:
        raise HTTPException(400, "You must agree to the Partnership terms to enroll.")
    contact_email = (inv.get("contact_email") or "").strip().lower()
    if not contact_email:
        raise HTTPException(400, "This invitation is missing a contact email.")

    # Step 1: user
    existing_user = await db.users.find_one({"email": contact_email}, {"_id": 0})
    if existing_user:
        target_user_id = existing_user["id"]
    else:
        display_name = (data.display_name_confirm or inv["display_name"]).strip()
        first, last = (display_name.split(" ", 1) + [""])[:2]
        user_doc = {
            "id": gen_id(),
            "email": contact_email,
            "first_name": first or "Partner",
            "last_name": last or "",
            "password_hash": hash_password(data.password),
            "role": "user",
            "created_at": now_iso(),
        }
        await db.users.insert_one(dict(user_doc))
        target_user_id = user_doc["id"]

    # Step 2: partner profile (unique per user_id + partner_type)
    profile = await db.partner_profiles.find_one(
        {"user_id": target_user_id, "partner_type": inv["partner_type"]}, {"_id": 0},
    )
    if not profile:
        display_name = (data.display_name_confirm or inv["display_name"]).strip()
        base = _slugify(display_name)
        slug = base
        i = 1
        while await db.partner_profiles.find_one({"slug": slug}, {"_id": 0, "id": 1}):
            i += 1
            slug = f"{base}-{i}"
        spec = PREVIEW_SPECS.get(inv["partner_type"], {})
        profile = {
            "id": gen_id(),
            "user_id": target_user_id,
            "partner_type": inv["partner_type"],
            "status": "active",
            "public": True,
            "slug": slug,
            "display_name": display_name,
            "headline": inv.get("default_headline") or spec.get("default_headline"),
            "bio": (inv.get("default_bio") or "")[:2000],
            "source": "foundation",
            "approved_at": now_iso(),
            "approved_by": inv.get("created_by"),
            "approval_note": "Foundation-curated invitation accepted via Explore-before-Embrace flow.",
            "agreed_to_partnership_terms_at": now_iso(),
            "selected_subscription_tier": data.selected_subscription_tier,
            "selected_options": data.selected_options or {},
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.partner_profiles.insert_one(dict(profile))

    # Step 3: mark invite + prospect accepted
    await db.partner_invites.update_one(
        {"id": inv["id"]},
        {"$set": {
            "status": "accepted",
            "accepted_at": now_iso(),
            "accepted_user_id": target_user_id,
            "accepted_partner_id": profile["id"],
            "accepted_partner_slug": profile["slug"],
        }},
    )
    if inv.get("prospect_id"):
        await db.partner_prospects.update_one(
            {"id": inv["prospect_id"]},
            {"$set": {
                "status": "promoted",
                "promoted_to_user_id": target_user_id,
                "promoted_to_partner_id": profile["id"],
                "promoted_at": now_iso(),
                "updated_at": now_iso(),
            }},
        )

    # Step 4: session JWT
    try:
        token_jwt = create_token(target_user_id, "user")
    except Exception:
        token_jwt = None

    return {
        "ok": True,
        "user_id": target_user_id,
        "partner_profile": profile,
        "session_token": token_jwt,
        "next": f"/dashboard/partner",
    }


@router.post("/invite/{token}/decline")
async def decline_invite(token: str, data: InviteDecline):
    """PUBLIC — politely decline."""
    from database import db
    inv = await _resolve_invite(db, token)
    if inv.get("status") in ("accepted", "declined", "expired"):
        raise HTTPException(400, f"This invitation is {inv['status']} and cannot be declined again.")
    await db.partner_invites.update_one(
        {"id": inv["id"]},
        {"$set": {
            "status": "declined",
            "declined_at": now_iso(),
            "declined_reason": (data.reason or "").strip() or None,
        }},
    )
    if inv.get("prospect_id"):
        await db.partner_prospects.update_one(
            {"id": inv["prospect_id"]},
            {"$set": {"status": "responded_declined", "updated_at": now_iso()}},
        )
    return {"ok": True}
