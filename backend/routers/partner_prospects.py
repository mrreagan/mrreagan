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

# Partner types that operate as independent contractors of the Foundation.
# Surfacing this on every partner-facing page and re-sign flow keeps the
# worker-classification honest for tax + liability. Research is a paid-
# honoraria basis only (not otherwise 1099-eligible).
IC_PARTNER_TYPES = {"facilitator", "steward", "vendor", "artist", "community"}
IC_LABEL = "Independent contractor"
IC_TOOLTIP = (
    "You act as an independent contractor of Birthright Foundation. "
    "You set your own hours, methods, and business decisions; you are "
    "responsible for your own taxes and any licences your practice requires. "
    "This is not an employment relationship."
)
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
                {"key": "monthly", "label": "Monthly", "price_display": "$99 / month",
                 "monthly_equivalent": "$99 / mo",
                 "summary": "Lowest commitment. Foundation takes 40% on workshops using Birthright IP and 50% on workshops using your own materials."},
                {"key": "annual", "label": "Annual", "price_display": "$999 / year",
                 "monthly_equivalent": "$83.25 / mo effective", "ribbon": "Most chosen",
                 "summary": "Mid commitment. Foundation takes 35% on Birthright IP workshops and 45% on workshops using your own materials."},
                {"key": "two_year", "label": "2-year", "price_display": "$1,799 / 24 months",
                 "monthly_equivalent": "$74.96 / mo effective",
                 "summary": "Longest commitment. Foundation takes 30% on Birthright IP workshops and 40% on workshops using your own materials."},
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
            "foundation_share": "On Birthright IP workshops: 30%–40% to the foundation (less with longer subscriptions). On your own-material workshops: 40%–50%. Foundation share decreases with commitment.",
        },
    },

    "community": {
        "title": "Community partner",
        "blurb": "Refer your audience to Birthright. Every order attributed to you pays a commission. No quotas, no exclusivity, no inventory.",
        "default_headline": "Community partner",
        "default_bio_hint": "Where does your audience hang out? Newsletter? Podcast? Local circles?",
        "options": {
            "subscription_tiers": [
                {"key": "monthly", "label": "Monthly", "price_display": "$29 / month",
                 "monthly_equivalent": "$29 / mo",
                 "summary": "Lowest commitment. You earn an 8% commission on every order attributed to your referral code."},
                {"key": "annual", "label": "Annual", "price_display": "$299 / year",
                 "monthly_equivalent": "$24.92 / mo effective", "ribbon": "Most chosen",
                 "summary": "Mid commitment. You earn a 10% commission on every order attributed to your referral code."},
                {"key": "two_year", "label": "2-year", "price_display": "$549 / 24 months",
                 "monthly_equivalent": "$22.88 / mo effective",
                 "summary": "Longest commitment. You earn a 12% commission on every order attributed to your referral code."},
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
            "foundation_share": "You keep 8%-12% of each attributed order (commission grows with longer subscription). Foundation keeps the rest of the order revenue.",
        },
    },

    "research": {
        "title": "Research collaborator",
        "blurb": "Submit research artifacts to a moderated, attributed catalog. By default this is a grant-funded role — no rev share, but full intellectual ownership and visibility.",
        "default_headline": "Research collaborator",
        "default_bio_hint": "Affiliation, area of research, recent publications.",
        "options": {
            "subscription_tiers": [
                {"key": "monthly", "label": "Monthly", "price_display": "$49 / month",
                 "monthly_equivalent": "$49 / mo",
                 "summary": "Optional subscription supports operations. Research is grant-funded — foundation takes 0% of your published work."},
                {"key": "annual", "label": "Annual", "price_display": "$499 / year",
                 "monthly_equivalent": "$41.58 / mo effective", "ribbon": "Most chosen",
                 "summary": "Optional subscription supports operations. Research is grant-funded — foundation takes 0% of your published work."},
                {"key": "two_year", "label": "2-year", "price_display": "$899 / 24 months",
                 "monthly_equivalent": "$37.46 / mo effective",
                 "summary": "Optional subscription supports operations. Research is grant-funded — foundation takes 0% of your published work."},
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
            # All percentages reward longer commitment with a BETTER vendor split.
            # Monthly is the foundation's highest cut; 2-year is the lowest.
            # Off-site referrals are always 100% to the vendor — Birthright is
            # paid only by the subscription on those orders.
            "subscription_tiers": [
                {
                    "key": "monthly",
                    "label": "Monthly",
                    "price_display": "$49 / month",
                    "monthly_equivalent": "$49 / mo",
                    "pod_vendor_pct": 75,
                    "pod_foundation_pct": 25,
                    "offsite_referred_vendor_pct": 90,
                    "offsite_referred_foundation_pct": 10,
                    "offsite_direct_vendor_pct": 100,
                    "offsite_direct_foundation_pct": 0,
                    "summary": "Lowest commitment. Foundation takes 25% on Birthright-fulfilled orders and 10% on traffic we send to your store.",
                },
                {
                    "key": "annual",
                    "label": "Annual",
                    "price_display": "$499 / year",
                    "monthly_equivalent": "$41.58 / mo effective",
                    "pod_vendor_pct": 78,
                    "pod_foundation_pct": 22,
                    "offsite_referred_vendor_pct": 92,
                    "offsite_referred_foundation_pct": 8,
                    "offsite_direct_vendor_pct": 100,
                    "offsite_direct_foundation_pct": 0,
                    "ribbon": "Most chosen",
                    "summary": "Lower subscription/mo plus a smaller foundation cut on every Birthright-driven order.",
                },
                {
                    "key": "two_year",
                    "label": "2-year",
                    "price_display": "$899 / 24 months",
                    "monthly_equivalent": "$37.46 / mo effective",
                    "pod_vendor_pct": 82,
                    "pod_foundation_pct": 18,
                    "offsite_referred_vendor_pct": 95,
                    "offsite_referred_foundation_pct": 5,
                    "offsite_direct_vendor_pct": 100,
                    "offsite_direct_foundation_pct": 0,
                    "summary": "Best monthly rate and the smallest foundation share on every channel.",
                },
            ],
            # Per-line clarity about what 'rev share' actually means in context.
            "revenue_breakdown_headers": {
                "subscription": "What you pay Birthright",
                "pod": "Order on birthright.live (we fulfill via Printful/Lulu)",
                "offsite": "Order on your own store (we send buyer to you with ?via= tag)",
            },
            "fulfillment_modes": [
                {"key": "printful", "label": "Print-on-demand (Printful)", "blurb": "Apparel, mugs — Birthright handles fulfillment.", "channel": "pod"},
                {"key": "lulu", "label": "Print-on-demand (Lulu)", "blurb": "Journals, notebooks — Birthright handles fulfillment.", "channel": "pod"},
                {"key": "off_site", "label": "Referral to your own store", "blurb": "We send buyers to you with a ?via= attribution tag. You keep 100%.", "channel": "offsite"},
                {"key": "manual", "label": "Foundation-fulfilled", "blurb": "Inventory + ship through Birthright (case-by-case).", "channel": "pod"},
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
            "foundation_share": "Three scenarios: on birthright.org we keep 18%-25% (POD orders we fulfill); on off-site orders where Birthright sent the visitor (?via= tag) we keep 5%-10% as a referral fee; on your direct customers we keep 0%. All foundation shares DECREASE the longer you commit. Every order shows the breakdown to the buyer.",
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
            "subscription_tiers": [
                {"key": "volunteer", "label": "Volunteer", "price_display": "Free",
                 "monthly_equivalent": "No subscription",
                 "summary": "Volunteer role. No subscription, no rev share. Foundation supports you with training, ombudsman backing, and a portable stewardship history."},
            ],
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

    "sponsor": {
        "title": "Sponsor Partner",
        "blurb": (
            "Underwrite the mission. Sponsors fund what operating capital can't — "
            "specific campaigns (like a media placement or scholarship cohort), or "
            "the general work of building Birthright. Sponsors are named on campaign "
            "pages and the partner directory, with your permission."
        ),
        "default_headline": "Sponsor partner",
        "default_bio_hint": "A sentence about why this work matters to you or your organization.",
        "options": {
            "subscription_tiers": [
                {
                    "key": "contributor",
                    "label": "Contributor",
                    "price_display": "Any amount",
                    "monthly_equivalent": "One-time or recurring",
                    "summary": (
                        "Thank-you email + optional named listing on the Wall of Supporters. "
                        "No partner profile at this level — Sponsor Partner status starts at $100+ one-time or $25/mo × 3+ months."
                    ),
                },
                {
                    "key": "sponsor_partner",
                    "label": "Sponsor Partner",
                    "price_display": "$100+ one-time / $25+ per month × 3",
                    "monthly_equivalent": "$25 / mo min",
                    "ribbon": "Most chosen",
                    "summary": (
                        "Full partner profile in the directory. Logo/link. Named on campaign pages "
                        "you underwrite. Auto-elevates once threshold is met and payment is confirmed."
                    ),
                },
                {
                    "key": "presenting",
                    "label": "Presenting Sponsor",
                    "price_display": "$5k+ one-time / $250+ per month",
                    "monthly_equivalent": "$250 / mo min",
                    "summary": (
                        "Top-of-directory placement + homepage recognition + 'Presented by' "
                        "credit on any campaign you underwrite."
                    ),
                },
            ],
            "media": [
                "Sponsor partner profile (photo/logo, bio, link)",
                "Named recognition on campaigns you underwrite (opt-in)",
                "Business receipts for every contribution",
                "Optional Wall of Supporters listing",
                "Annual sponsor recognition report",
            ],
            "policies": [
                "Set whether your name/logo is displayed publicly or kept anonymous",
                "Choose which campaigns your contribution supports",
                "Update your business receipt details at any time",
            ],
        },
        "what_acceptance_means": {
            "summary": (
                "Sponsor Partner status is earned by contribution, not applied for. Any pledge that "
                "reaches $100+ one-time (or a $25/mo recurring for 3 months) automatically elevates "
                "your account to Sponsor Partner once the payment is confirmed. Sponsor Partner status "
                "renews annually; if no renewed contribution is made for 18 months, status gracefully "
                "converts to Alumni Contributor (you remain listed as a past supporter)."
            ),
            "obligations": [
                "Accept that contributions are not currently tax-deductible (Birthright has not yet received IRS 501(c)(3) determination).",
                "Confirm whether your name/logo may be displayed publicly (opt-in).",
                "Update Birthright if your contact or business receipt details change.",
            ],
            "you_keep": [
                "The right to withdraw a pledge before payment is confirmed.",
                "Full control over whether your name is listed publicly.",
                "A business receipt for every confirmed contribution.",
                "Your Alumni Contributor listing after status ends (unless you request removal).",
            ],
            "foundation_share": (
                "Not a monetary partnership — you give, we receipt. No revenue share is paid to sponsors. "
                "Not currently tax-deductible: Birthright Foundation has not yet submitted or received "
                "IRS 501(c)(3) determination. No representation is made about future tax status."
            ),
        },
    },
}


def get_preview_spec(partner_type: str) -> dict:
    if partner_type not in PREVIEW_SPECS:
        raise HTTPException(404, f"Unknown partner type: {partner_type}")
    spec = dict(PREVIEW_SPECS[partner_type])
    spec["partner_type"] = partner_type
    # Broadcast IC classification so every consumer (Types page,
    # Try/Explore page, Invite preview, profile) can render the chip
    # without hard-coding the list on the frontend.
    spec["is_independent_contractor"] = partner_type in IC_PARTNER_TYPES
    spec["worker_classification"] = IC_LABEL if partner_type in IC_PARTNER_TYPES else None
    spec["worker_classification_note"] = IC_TOOLTIP if partner_type in IC_PARTNER_TYPES else None
    return spec


# ============ Models ============

class ProspectCreate(BaseModel):
    partner_type: Literal["facilitator", "community", "research", "vendor", "artist", "steward", "sponsor"]
    display_name: str = Field(min_length=2, max_length=200)
    contact_email: Optional[str] = Field(default=None, max_length=200)
    contact_phone: Optional[str] = Field(default=None, max_length=80)
    location: Optional[str] = Field(default=None, max_length=200)
    headline_excerpt: Optional[str] = Field(default=None, max_length=400)
    bio_excerpt: Optional[str] = Field(default=None, max_length=4000)
    portfolio_url: Optional[str] = Field(default=None, max_length=600)
    social_url: Optional[str] = Field(default=None, max_length=600)
    # "This is what caught the foundation's eye" — the specific thing on the
    # prospect's site/profile that's the *reason* for the invitation. Surfaces
    # prominently on the invitation preview so the artist knows why they were
    # picked, not just that they were.
    highlight_url: Optional[str] = Field(default=None, max_length=600,
        description="Primary link to the prospect's site OR the specific page/product/service/comment that motivated the invitation.")
    highlight_image_url: Optional[str] = Field(default=None, max_length=600,
        description="Optional image (e.g., a photo of the product or a screenshot of the page) that visually anchors the highlight on the invitation preview.")
    highlight_label: Optional[Literal[
        "site", "product", "service", "page", "item",
        "comment", "post", "mission", "statement", "about", "other",
    ]] = Field(default=None,
        description="What kind of thing is at highlight_url — used to label it on the preview.")
    highlight_excerpt: Optional[str] = Field(default=None, max_length=4000,
        description="A short excerpt of the specific content (quote, product description, statement of mission) so the artist knows exactly what the foundation responded to.")
    highlight_reason: Optional[str] = Field(default=None, max_length=2000,
        description="Why this specific thing — one or two sentences from the foundation explaining what resonated.")
    # The mission-alignment BLUF — leads the entire invitation. Equity in
    # mission is the real benefit of partnership; finance is just what makes
    # it viable. Required for a high-quality invitation, but optional at the
    # API level so leaders can save drafts and add it before promoting.
    mission_alignment: Optional[str] = Field(default=None, max_length=6000,
        description="How this partner's work aligns with and supports the Birthright mission. Leads every invitation as the BLUF — comes BEFORE the role description, the financial terms, or the highlight link. This is the heart of why we extend an invitation.")
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
    highlight_url: Optional[str] = Field(default=None, max_length=600)
    highlight_image_url: Optional[str] = Field(default=None, max_length=600)
    highlight_label: Optional[Literal[
        "site", "product", "service", "page", "item",
        "comment", "post", "mission", "statement", "about", "other",
    ]] = None
    highlight_excerpt: Optional[str] = Field(default=None, max_length=4000)
    highlight_reason: Optional[str] = Field(default=None, max_length=2000)
    mission_alignment: Optional[str] = Field(default=None, max_length=6000)
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
        "contact_email": inv.get("contact_email"),
        "note_to_prospect": inv.get("note_to_prospect"),
        "suggested_subscription_tier": inv.get("suggested_subscription_tier"),
        "default_headline": inv.get("default_headline"),
        "default_bio": inv.get("default_bio"),
        "highlight_url": inv.get("highlight_url"),
        "highlight_image_url": inv.get("highlight_image_url"),
        "highlight_label": inv.get("highlight_label"),
        "highlight_excerpt": inv.get("highlight_excerpt"),
        "highlight_reason": inv.get("highlight_reason"),
        "mission_alignment": inv.get("mission_alignment"),
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


def _email_html(partner_type: str, prospect_name: str, note: Optional[str],
                preview_url: str, highlight: Optional[dict] = None,
                mission_alignment: Optional[str] = None) -> str:
    spec = PREVIEW_SPECS.get(partner_type, {})
    title = spec.get("title", partner_type.title())
    blurb = spec.get("blurb", "")
    note_block = (
        f"<blockquote style=\"border-left:3px solid #C9A961;padding:8px 14px;"
        f"color:#1A2424;font-style:italic;margin:18px 0;background:#FAF8F5\">{note}</blockquote>"
    ) if note else ""
    # Mission alignment BLUF — LEADS the invitation. Equity in mission is the
    # real benefit; finance is just viability. This card sits BEFORE the role
    # description, the highlight, and the tier picker.
    mission_block = ""
    if mission_alignment:
        mission_block = (
            f"<div style=\"background:linear-gradient(135deg,#FAF8F5 0%,#F4F1EA 100%);"
            f"border:1px solid #C9A961;border-radius:8px;padding:22px 24px;margin:22px 0 18px 0\">"
            f"<p style=\"font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#9E3C3C;margin:0 0 10px 0\">"
            f"Why we're reaching out</p>"
            f"<p style=\"font-family:Georgia,serif;font-size:17px;line-height:1.5;color:#1A2424;margin:0\">"
            f"{mission_alignment}</p>"
            f"</div>"
        )
    highlight_block = ""
    if highlight and highlight.get("url"):
        label = (highlight.get("label") or "site").replace("_", " ")
        excerpt = (
            f"<blockquote style=\"margin:8px 0 4px 0;font-style:italic;color:#1A2424;"
            f"border-left:2px solid #C9A961;padding-left:10px;font-size:14px\">&ldquo;{highlight['excerpt']}&rdquo;</blockquote>"
        ) if highlight.get("excerpt") else ""
        reason = (
            f"<p style=\"font-size:13px;color:#5C6B6B;margin:8px 0 0 0\">{highlight['reason']}</p>"
        ) if highlight.get("reason") else ""
        highlight_block = (
            f"<div style=\"background:#F4F1EA;border:1px solid #E5DDD0;border-radius:8px;"
            f"padding:16px 20px;margin:0 0 22px 0\">"
            f"<p style=\"font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#476B6B;margin:0 0 6px 0\">"
            f"What we saw — your {label}</p>"
            f"{excerpt}"
            f"<a href=\"{highlight['url']}\" style=\"color:#9E3C3C;font-size:13px;font-family:Georgia,serif;word-break:break-all\">"
            f"{highlight['url']}</a>"
            f"{reason}"
            f"</div>"
        )
    return (
        f"<div style=\"font-family:Georgia,serif;color:#1A2424;max-width:580px;line-height:1.6\">"
        f"<h2 style=\"font-weight:400;font-size:24px;margin-bottom:6px\">Hi {prospect_name},</h2>"
        # Mission BLUF LEADS the entire invitation
        f"{mission_block}"
        # The specific thing the foundation responded to
        f"{highlight_block}"
        # Optional personal note
        f"{note_block}"
        # Then — and only then — the role description
        f"<p style=\"font-size:15px\">For these reasons, we'd like to invite you to partner with us as a "
        f"<strong>{title}</strong>.</p>"
        f"<p style=\"font-size:14px;color:#5C6B6B\">{blurb}</p>"
        f"<div style=\"background:#FAF8F5;border:1px solid #E5DDD0;border-radius:8px;padding:18px;margin:22px 0\">"
        f"<p style=\"font-size:13px;color:#5C6B6B;margin:0 0 6px 0\">Default selections you can change:</p>"
        f"<ul style=\"font-size:13px;color:#1A2424;padding-left:20px;line-height:1.7;margin:0\">"
        f"<li>A pre-filled dashboard ready for you to explore</li>"
        f"<li>Suggested subscription tier (you pick your own)</li>"
        f"<li>Every option you can configure, displayed up front</li>"
        f"</ul></div>"
        f"<div style=\"background:#FAF8F5;border-left:3px solid #C9A961;padding:14px 18px;margin:22px 0;"
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
        "highlight_url": (data.highlight_url or "").strip() or None,
        "highlight_image_url": (data.highlight_image_url or "").strip() or None,
        "highlight_label": data.highlight_label,
        "highlight_excerpt": (data.highlight_excerpt or "").strip() or None,
        "highlight_reason": (data.highlight_reason or "").strip() or None,
        "mission_alignment": (data.mission_alignment or "").strip() or None,
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


class MissionSuggestRequest(BaseModel):
    # Optional override fields — if not provided, we read them from the prospect.
    partner_type: Optional[Literal["facilitator", "community", "research", "vendor", "artist", "steward", "sponsor"]] = None
    highlight_url: Optional[str] = Field(default=None, max_length=600)
    highlight_label: Optional[str] = Field(default=None, max_length=40)
    highlight_excerpt: Optional[str] = Field(default=None, max_length=4000)
    highlight_reason: Optional[str] = Field(default=None, max_length=2000)
    headline_excerpt: Optional[str] = Field(default=None, max_length=400)
    bio_excerpt: Optional[str] = Field(default=None, max_length=4000)


@router.post("/admin/prospects/draft-suggest-mission")
async def draft_suggest_mission(
    data: MissionSuggestRequest,
    user: dict = Depends(require_roles("admin")),
):
    """Generate 3 mission-alignment drafts WITHOUT requiring a saved prospect.
    Used while the foundation leader is still filling out the new-prospect form."""
    if not data.partner_type or data.partner_type not in PARTNER_TYPES:
        raise HTTPException(400, "partner_type is required and must be a known type.")
    spec = PREVIEW_SPECS.get(data.partner_type, {})
    fields = {
        "display_name": None,
        "headline": data.headline_excerpt,
        "bio": data.bio_excerpt,
        "highlight_url": data.highlight_url,
        "highlight_label": data.highlight_label,
        "highlight_excerpt": data.highlight_excerpt,
        "highlight_reason": data.highlight_reason,
        "location": None,
    }
    if not any([fields["headline"], fields["bio"], fields["highlight_excerpt"]]):
        raise HTTPException(400,
            "Provide at least one of headline, bio, or highlight excerpt before requesting suggestions.")
    return await _generate_mission_drafts(data.partner_type, spec, fields)


@router.post("/admin/prospects/{prospect_id}/suggest-mission-alignment")
async def suggest_mission_alignment(
    prospect_id: str,
    data: Optional[MissionSuggestRequest] = None,
    user: dict = Depends(require_roles("admin")),
):
    """Return 3 Claude-drafted candidates for the mission-alignment BLUF —
    one warm, one formal, one poetic — so the foundation leader picks the voice
    that fits the prospect.

    Inference inputs (in priority order):
      1. The fields on the request body if provided (live, before save)
      2. The fields on the saved prospect document
    Plus:
      3. The per-partner-type mission/blurb from PREVIEW_SPECS
      4. Birthright Foundation's core mission language (constant below)
    """
    from database import db
    p = await db.partner_prospects.find_one({"id": prospect_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Prospect not found")
    payload = data or MissionSuggestRequest()
    partner_type = payload.partner_type or p.get("partner_type")
    if partner_type not in PARTNER_TYPES:
        raise HTTPException(400, "Unknown partner_type")
    spec = PREVIEW_SPECS.get(partner_type, {})

    fields = {
        "display_name": p.get("display_name"),
        "headline": payload.headline_excerpt or p.get("headline_excerpt"),
        "bio": payload.bio_excerpt or p.get("bio_excerpt"),
        "highlight_url": payload.highlight_url or p.get("highlight_url"),
        "highlight_label": payload.highlight_label or p.get("highlight_label"),
        "highlight_excerpt": payload.highlight_excerpt or p.get("highlight_excerpt"),
        "highlight_reason": payload.highlight_reason or p.get("highlight_reason"),
        "location": p.get("location"),
    }

    return await _generate_mission_drafts(partner_type, spec, fields)


# Core Birthright Foundation mission language — used as the Claude grounding.
BIRTHRIGHT_MISSION_GROUNDING = (
    "The Birthright Foundation exists to make the practice of secure presence — "
    "between parents and children, between partners, between neighbors — "
    "ordinary, durable, and beautiful. We support workshops, gatherings, "
    "research, and the makers who hold the work with dignity. Partnership "
    "with Birthright is equity in this mission first; financial scaffolding "
    "second. We invite people whose existing work already moves toward "
    "presence, repair, and quiet, unsentimental love of one's own people."
)


async def _generate_mission_drafts(partner_type: str, spec: dict, fields: dict) -> dict:
    """Call Claude (via emergentintegrations) for 3 mission-alignment drafts
    in distinct voices. Falls back to deterministic templates if the API
    fails (so the admin UI never blocks on a network hiccup)."""
    grounding = (
        f"Partner type: {spec.get('title') or partner_type}\n"
        f"Role blurb: {spec.get('blurb') or ''}\n"
        f"Mission grounding for this role: {(spec.get('what_acceptance_means') or {}).get('summary', '')}\n"
        f"Prospect: {fields.get('display_name') or ''}\n"
        f"Headline: {fields.get('headline') or ''}\n"
        f"Bio excerpt: {(fields.get('bio') or '')[:1200]}\n"
        f"What we noticed on their {fields.get('highlight_label') or 'site'}: "
        f"{(fields.get('highlight_excerpt') or '')[:1200]}\n"
        f"Why this resonated for us: {(fields.get('highlight_reason') or '')[:600]}\n"
        f"Foundation mission language: {BIRTHRIGHT_MISSION_GROUNDING}"
    )
    system_prompt = (
        "You write the opening Bottom Line Up Front (BLUF) of a Birthright Foundation "
        "partnership invitation. The BLUF is two to four sentences that explain to the "
        "prospect, on the basis of THIS specific person's work, how their existing practice "
        "already aligns with and supports Birthright's mission of making secure presence "
        "ordinary, durable, and beautiful. \n"
        "\n"
        "Constraints:\n"
        " - 2-4 sentences. No more than ~80 words.\n"
        " - Specific. Reference what you noticed about them, not abstract platitudes.\n"
        " - Second person, addressed TO them.\n"
        " - No exclamation marks. No sales-y language. No 'we love what you do'.\n"
        " - Mission alignment FIRST. Don't talk about money, tiers, or features.\n"
        " - Don't introduce yourself ('Hi, we're the Birthright Foundation'). Assume context.\n"
        "\n"
        "Return ONLY a JSON array of three objects, no preamble, no markdown fence. Each object:\n"
        "  { \"voice\": \"warm|formal|poetic\", \"text\": \"the BLUF\" }\n"
    )
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise RuntimeError("No EMERGENT_LLM_KEY available")
        chat = LlmChat(
            api_key=api_key,
            session_id=f"mission-bluf-{gen_id()[:8]}",
            system_message=system_prompt,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        msg = UserMessage(text=grounding)
        out = await chat.send_message(msg)
        import json as _json
        # Be tolerant of common Claude wrapping
        cleaned = (out or "").strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-z]*", "", cleaned).rstrip("` \n")
        drafts = _json.loads(cleaned)
        if not isinstance(drafts, list) or len(drafts) < 3:
            raise ValueError("Unexpected shape from Claude")
        # Normalize
        out_drafts = []
        for d in drafts[:3]:
            voice = (d.get("voice") or "warm").lower().strip()
            text = (d.get("text") or "").strip()
            if not text:
                continue
            out_drafts.append({"voice": voice, "text": text})
        if len(out_drafts) >= 3:
            return {"source": "ai", "drafts": out_drafts}
        raise ValueError("Not enough non-empty drafts")
    except Exception as ex:
        logger.warning("Mission-alignment AI suggestion failed (%s); using fallback templates.", ex)
        return {"source": "fallback", "drafts": _fallback_mission_drafts(partner_type, spec, fields)}


def _fallback_mission_drafts(partner_type: str, spec: dict, fields: dict) -> list[dict]:
    """Deterministic alignment drafts when Claude is unavailable. Use the
    prospect's noticed-content + per-type mission as scaffolding."""
    name = fields.get("display_name") or "you"
    label = fields.get("highlight_label") or "work"
    excerpt = (fields.get("highlight_excerpt") or "").strip()
    quote = f' "{excerpt[:140]}"' if excerpt else ""
    title = (spec.get("title") or partner_type).lower()
    return [
        {"voice": "warm", "text": (
            f"What we saw in your {label}{quote} is already the work Birthright tries to make ordinary — "
            f"steady, undefended attention to the people in front of you. Partnering as a {title} would put "
            f"institutional scaffolding behind a practice you are clearly already doing."
        )},
        {"voice": "formal", "text": (
            f"Your {label} demonstrates the kind of disciplined, present-tense practice the Birthright Foundation "
            f"is constituted to support. We extend this {title} partnership on the basis that your existing work "
            f"already advances our shared aim of making secure presence durable and beautiful."
        )},
        {"voice": "poetic", "text": (
            f"There is a quiet in what you make. The {label} shows it. Birthright tends a small fire that wants "
            f"more keepers like you — people whose work is already a slow form of love. Partner with us as a "
            f"{title} and the fire grows by exactly one room."
        )},
    ]


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
        # Carry the highlight to the public preview so the prospect sees WHY
        # they were chosen, not just THAT they were chosen.
        "highlight_url": p.get("highlight_url"),
        "highlight_image_url": p.get("highlight_image_url"),
        "highlight_label": p.get("highlight_label"),
        "highlight_excerpt": p.get("highlight_excerpt"),
        "highlight_reason": p.get("highlight_reason"),
        # Mission alignment leads every invitation — equity in mission is the
        # real benefit; finance is just viability scaffolding.
        "mission_alignment": p.get("mission_alignment"),
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
            html=_email_html(
                p["partner_type"], p["display_name"], invite["note_to_prospect"], preview_url,
                highlight={
                    "url": p.get("highlight_url"),
                    "label": p.get("highlight_label"),
                    "excerpt": p.get("highlight_excerpt"),
                    "reason": p.get("highlight_reason"),
                } if p.get("highlight_url") else None,
                mission_alignment=p.get("mission_alignment"),
            ),
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
    return {pt: get_preview_spec(pt) for pt in PARTNER_TYPES}


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

    # Audit: partner agreement accepted (Tier 1 signing event)
    try:
        from utils.user_activity import log_event, CAT_SIGN
        await log_event(
            db, user_id=target_user_id, email=contact_email, role="user",
            event_type="signing.partner_agreement_signed", category=CAT_SIGN,
            method="POST", path="/api/partners/invite/{token}/accept", status_code=200,
            metadata={
                "partner_type": inv.get("partner_type"),
                "profile_id": profile["id"],
                "selected_subscription_tier": data.selected_subscription_tier,
            },
        )
    except Exception:
        pass

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
