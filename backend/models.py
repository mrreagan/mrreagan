"""Pydantic models for the Birthright platform."""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ USERS ============
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    first_name: str
    last_name: str
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    facilitator_slug: Optional[str] = None
    credentials: Optional[str] = None
    governance_member: bool = False
    is_ombudsman: bool = False
    created_at: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    credentials: Optional[str] = None


# ============ WORKSHOPS ============
class WorkshopCreate(BaseModel):
    title: str
    slug: str
    short_description: str
    full_description: str
    facilitator_id: str
    location_name: str
    location_address: str
    directions_notes: Optional[str] = ""
    map_url: Optional[str] = ""
    start_date: str  # ISO datetime
    end_date: str
    capacity: int
    early_bird_price: float
    regular_price: float
    early_bird_until: Optional[str] = None
    image_url: Optional[str] = ""
    materials_included: List[str] = []
    faq: List[dict] = []
    check_in_code: Optional[str] = None  # auto-generated server-side if omitted
    status: Literal["draft", "upcoming", "in_progress", "completed", "cancelled"] = "upcoming"


class Workshop(WorkshopCreate):
    id: str
    created_at: str


class WorkshopUpdate(BaseModel):
    title: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    directions_notes: Optional[str] = None
    map_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    capacity: Optional[int] = None
    early_bird_price: Optional[float] = None
    regular_price: Optional[float] = None
    early_bird_until: Optional[str] = None
    image_url: Optional[str] = None
    materials_included: Optional[List[str]] = None
    faq: Optional[List[dict]] = None
    check_in_code: Optional[str] = None
    status: Optional[str] = None


# ============ REGISTRATIONS ============
class Registration(BaseModel):
    id: str
    workshop_id: str
    user_id: str
    pricing_tier: Literal["early_bird", "regular"]
    amount_paid: float
    payment_session_id: Optional[str] = None
    payment_status: Literal["pending", "paid", "failed", "refunded"] = "pending"
    checked_in: bool = False
    checked_in_at: Optional[str] = None
    created_at: str


class WaitlistEntry(BaseModel):
    id: str
    workshop_id: str
    user_id: str
    created_at: str
    notified: bool = False


# ============ PRODUCTS / STORE ============
class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    type: Literal["merch", "workshop_material"]
    workshop_id: Optional[str] = None
    image_url: Optional[str] = ""
    inventory: int = 100
    category: Optional[str] = "general"
    # Vendor catalog (Phase 6B.4)
    is_vendor_product: bool = False
    vendor_partner_id: Optional[str] = None
    vendor_user_id: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_slug: Optional[str] = None
    moderation_status: Literal["active", "flagged", "unpublished"] = "active"
    moderation_note: Optional[str] = None


class Product(ProductCreate):
    id: str
    created_at: str


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    inventory: Optional[int] = None
    category: Optional[str] = None


# ============ VENDOR CATALOG (Phase 6B.4) ============

class VendorProductCreate(BaseModel):
    """Vendor-facing product create — vendor cannot set workshop_id, type is
    forced to 'merch', and moderation fields are server-controlled."""
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    price: float = Field(ge=0)
    image_url: Optional[str] = ""
    category: Optional[str] = Field(default="general", max_length=60)


class VendorProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    price: Optional[float] = Field(default=None, ge=0)
    image_url: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=60)


class VendorModerationAction(BaseModel):
    moderation_note: Optional[str] = Field(default="", max_length=2000)


# ============ CART / CHECKOUT ============
class CartItem(BaseModel):
    product_id: str
    quantity: int = 1


class CheckoutRequest(BaseModel):
    items: List[CartItem]
    origin_url: str
    shipping_address: Optional[dict] = None


class WorkshopCheckoutRequest(BaseModel):
    workshop_id: str
    origin_url: str


class DonationRequest(BaseModel):
    amount: float
    origin_url: str
    note: Optional[str] = ""


class SponsorshipRequest(BaseModel):
    tier_id: str  # amethyst, ruby, sapphire, emerald, diamond
    origin_url: str
    note: Optional[str] = ""


# ============ DISCUSSIONS / Q&A ============
class DiscussionCreate(BaseModel):
    workshop_id: str
    content: str
    parent_id: Optional[str] = None
    is_question: bool = False
    is_private: bool = False  # private = only facilitator+author can see


class Discussion(DiscussionCreate):
    id: str
    user_id: str
    user_name: str
    user_role: str
    created_at: str
    answered: bool = False


# ============ CHAT ============
class ChatMessageCreate(BaseModel):
    workshop_id: str
    content: str
    recipient_id: Optional[str] = None  # None = group chat


class ChatMessage(ChatMessageCreate):
    id: str
    sender_id: str
    sender_name: str
    created_at: str


# ============ REVIEWS ============
class ReviewCreate(BaseModel):
    # Universal review. Either supply workshop_id (back-compat) or {subject_type, subject_id}.
    workshop_id: Optional[str] = None
    subject_type: Optional[Literal["workshop", "product", "service"]] = None
    subject_id: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    review_text: str = Field(min_length=10, max_length=4000)
    anonymous: bool = False


class Review(BaseModel):
    id: str
    subject_type: Literal["workshop", "product", "service"]
    subject_id: str
    subject_category: Optional[str] = None
    partner_id: Optional[str] = None
    workshop_id: Optional[str] = None  # mirrored when subject_type='workshop' for legacy queries
    user_id: Optional[str] = None
    user_name: str
    rating: int
    review_text: str
    anonymous: bool = False
    verified_purchase: bool = False
    moderated: bool = False
    moderation_reason: Optional[str] = None
    reported_count: int = 0
    created_at: str


class ReviewReport(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ReviewModerate(BaseModel):
    moderated: bool
    reason: Optional[str] = None


# ============ IMPACT STATEMENTS ============
class ImpactStatementCreate(BaseModel):
    workshop_id: str
    what_learned: str
    how_grew: str
    benefits: str
    improvements: Optional[str] = ""
    is_public: bool = False
    anonymous: bool = False


class ImpactStatement(ImpactStatementCreate):
    id: str
    user_id: str
    user_name: str
    created_at: str


# ============ SUPPORT REQUESTS ============
class SupportRequestCreate(BaseModel):
    workshop_id: str
    subject: str
    content: str
    urgency: Literal["low", "normal", "high"] = "normal"


class SupportRequest(SupportRequestCreate):
    id: str
    user_id: str
    user_name: str
    status: Literal["open", "in_progress", "resolved"] = "open"
    response: Optional[str] = None
    responded_by: Optional[str] = None
    responded_at: Optional[str] = None
    created_at: str


class SupportResponse(BaseModel):
    response: str


# ============ GOVERNANCE / FOUNDATION ============
class GoverningMember(BaseModel):
    id: str
    name: str
    title: str
    bio: str
    image_url: Optional[str] = ""
    order: int = 0


class GoverningMemberCreate(BaseModel):
    name: str
    title: str
    bio: str
    image_url: Optional[str] = ""
    order: int = 0


class FoundationContent(BaseModel):
    """Stored as singleton document with key='content'."""
    mission_statement: str
    about_text: str
    education_structure: str
    vision: str
    values: List[str]


# ============ CONTACT / NEWSLETTER ============
class ContactMessageCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = ""
    email: EmailStr
    phone: Optional[str] = ""
    subject: Optional[str] = ""
    message: str
    newsletter_opt_in: bool = False


class NewsletterSubscribe(BaseModel):
    email: EmailStr
    name: Optional[str] = ""


# ============ WORKSHOP PHOTOS ============
class WorkshopPhotoCreate(BaseModel):
    caption: Optional[str] = ""


class WorkshopPhoto(BaseModel):
    id: str
    workshop_id: str
    uploader_id: str
    uploader_name: str
    uploader_role: str
    image_url: str
    thumb_url: Optional[str] = None
    caption: str = ""
    status: Literal["pending", "approved", "rejected"] = "pending"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: str


class PhotoModerationAction(BaseModel):
    reason: Optional[str] = None



# ============ PARTNERS / GOVERNANCE / LEGAL (Phase 6A.2) ============

PARTNER_TYPES = ("facilitator", "community", "research", "vendor")
PROPOSAL_CATEGORIES = ("rev_share", "policy", "membership", "indemnification", "other")


class RevShareTier(BaseModel):
    name: str  # e.g. 'bronze', 'silver', 'gold'
    pct: float = Field(ge=0, le=100)
    description: Optional[str] = ""


class GlobalDefaults(BaseModel):
    """Singleton document (key='global_defaults') for org-wide defaults."""
    rev_share: dict  # {partner_type: [RevShareTier...]}
    min_listing_rating: float = 0.0
    indemnification_active_version_id: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None


class GlobalDefaultsUpdate(BaseModel):
    rev_share: Optional[dict] = None
    min_listing_rating: Optional[float] = Field(default=None, ge=0, le=5)


class ProposalCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    summary: str = Field(min_length=10, max_length=500)
    body: str = Field(min_length=20, max_length=20000)
    category: Literal["rev_share", "policy", "membership", "indemnification", "other"] = "policy"
    voting_closes_at: Optional[str] = None  # ISO datetime; default = +14 days set server-side
    implementation_notes: Optional[str] = ""


class Proposal(BaseModel):
    id: str
    title: str
    summary: str
    body: str
    category: str
    proposer_id: str
    proposer_name: str
    status: Literal["draft", "open", "passed", "failed", "withdrawn"] = "open"
    created_at: str
    voting_closes_at: str
    closed_at: Optional[str] = None
    closed_by: Optional[str] = None
    implementation_notes: Optional[str] = ""
    yes_count: int = 0
    no_count: int = 0
    abstain_count: int = 0


class VoteCast(BaseModel):
    vote: Literal["yes", "no", "abstain"]
    comment: Optional[str] = Field(default="", max_length=2000)


class GovernanceVote(BaseModel):
    id: str
    proposal_id: str
    voter_id: str
    voter_name: str
    vote: str
    comment: str = ""
    created_at: str


class MemberFlagsUpdate(BaseModel):
    governance_member: Optional[bool] = None
    is_ombudsman: Optional[bool] = None


class IndemnificationCreate(BaseModel):
    version: str = Field(min_length=1, max_length=20)  # semantic-ish, e.g. "1.0", "1.1-draft"
    body: str = Field(min_length=50)
    summary_of_changes: Optional[str] = ""


class IndemnificationVersion(BaseModel):
    id: str
    version: str
    body: str
    summary_of_changes: str = ""
    active: bool = False
    created_by: str
    created_at: str
    activated_at: Optional[str] = None


class IndemnificationSignature(BaseModel):
    id: str
    version_id: str
    version: str
    user_id: str
    user_name: str
    user_role: str
    signed_at: str
    ip: Optional[str] = None


class AuditLogEntry(BaseModel):
    id: str
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    actor_name: Optional[str] = None
    action: str  # e.g. 'governance.defaults.update', 'governance.proposal.create', 'legal.indemnification.activate'
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    metadata: dict = {}
    created_at: str



# ============ PARTNERS (Phase 6B.1) ============

PARTNER_STATUS = ("pending", "approved", "rejected", "revoked")


class PartnerApplyData(BaseModel):
    """Per-type application payload. Self-apply uses `partner_type` to pick fields."""
    partner_type: Literal["facilitator", "community", "research", "vendor"]
    headline: str = Field(min_length=5, max_length=160)
    bio: str = Field(min_length=20, max_length=4000)
    website_url: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=120)
    # Facilitator-specific
    presents_birthright_ip: Optional[bool] = None
    credentials: Optional[str] = Field(default=None, max_length=2000)
    training_history: Optional[str] = Field(default=None, max_length=4000)
    sample_curriculum_url: Optional[str] = None
    # Community-specific
    organization: Optional[str] = Field(default=None, max_length=200)
    audience_size: Optional[int] = Field(default=None, ge=0)
    referral_plan: Optional[str] = Field(default=None, max_length=2000)
    # Research-specific
    institution: Optional[str] = Field(default=None, max_length=200)
    area_of_research: Optional[str] = Field(default=None, max_length=500)
    sample_publications_url: Optional[str] = None
    # Vendor-specific
    business_name: Optional[str] = Field(default=None, max_length=200)
    product_categories: Optional[str] = Field(default=None, max_length=500)


class PartnerInviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    partner_type: Literal["facilitator", "community", "research", "vendor"]
    admin_note: Optional[str] = Field(default="", max_length=1000)


class PartnerApplicationDecision(BaseModel):
    admin_note: Optional[str] = Field(default="", max_length=2000)


class PartnerProfileUpdate(BaseModel):
    headline: Optional[str] = Field(default=None, min_length=5, max_length=160)
    bio: Optional[str] = Field(default=None, min_length=20, max_length=4000)
    website_url: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=120)
    photo_url: Optional[str] = None
    public: Optional[bool] = None
    # v1.11.0 — outbound attribution
    external_site_url: Optional[str] = None
    external_platform: Optional[str] = Field(default=None, max_length=80)


# ============ PARTNER ECONOMY (v1.11.0) ============

class FeaturePartnerRequest(BaseModel):
    """Admin: mark a partner profile as 'featured' for a window."""
    until: str  # ISO datetime
    mission_alignment: str = Field(default="", max_length=2000)
    signature_content: Optional[str] = Field(default=None, max_length=4000)
    video_url: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list, max_length=3)
    custom_cta: Optional[str] = Field(default=None, max_length=200)


class FoundingPartnerToggle(BaseModel):
    expires_at: str  # ISO datetime — 5 years from grant by default


class RevShareOverride(BaseModel):
    """Per-partner override. Requires reason; audit-logged; respects 35% floor unless reason explicitly bypasses."""
    foundation_ip_pct: Optional[float] = Field(default=None, ge=0, le=100)
    non_ip_pct: Optional[float] = Field(default=None, ge=0, le=100)
    off_site_pct: Optional[float] = Field(default=None, ge=0, le=100)
    reason: str = Field(min_length=10, max_length=2000)
    bypass_floor: bool = False


class OutboundClickRecord(BaseModel):
    """Single click-through to a partner's external site. Used for attribution + estimation."""
    id: str
    partner_id: str
    partner_slug: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    dest_url: str
    referrer: Optional[str] = None
    utm_params: dict = {}
    created_at: str


class PartnerSalesReportSubmit(BaseModel):
    """Partner self-reports a period of off-site sales attributable to Birthright."""
    period_start: str  # ISO date
    period_end: str
    gross_revenue_usd: float = Field(ge=0)
    attributed_orders: int = Field(default=0, ge=0)
    note: Optional[str] = Field(default="", max_length=2000)


class UserCreditEntry(BaseModel):
    """Store credit ledger entry. Positive = credit added; negative = redeemed."""
    id: str
    user_id: str
    amount_usd: float  # signed
    reason: Literal["referral_earned", "redeemed", "admin_adjustment", "refund"]
    source_id: Optional[str] = None  # referral_id / order_id / etc.
    created_at: str



# ============ FOUNDATION ROLES (Phase 6B.4.5b) ============

class FoundationRoleCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=3, max_length=200)
    headline: str = Field(min_length=5, max_length=400)
    who_you_are: str = Field(min_length=10, max_length=4000)
    what_youll_do: str = Field(min_length=10, max_length=4000)
    what_you_bring: str = Field(min_length=10, max_length=4000)
    time_commitment: Optional[str] = Field(default="", max_length=200)
    compensation_summary: str = Field(default="Equity in mission — Birthright is a not-for-profit and does not currently provide monetary compensation.", max_length=600)
    order: int = 0
    open: bool = True
    seeded_member_id: Optional[str] = None  # link to existing governing_member row for SAMPLE ribbon


class FoundationRoleUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    headline: Optional[str] = Field(default=None, min_length=5, max_length=400)
    who_you_are: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    what_youll_do: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    what_you_bring: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    time_commitment: Optional[str] = Field(default=None, max_length=200)
    compensation_summary: Optional[str] = Field(default=None, max_length=600)
    order: Optional[int] = None
    open: Optional[bool] = None


class FoundationRole(FoundationRoleCreate):
    id: str
    created_at: str
    updated_at: str


class FoundationRoleApplicationSubmit(BaseModel):
    role_slug: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    current_role: Optional[str] = Field(default="", max_length=300)
    why_drawn: str = Field(min_length=20, max_length=6000)
    resume_url: Optional[str] = Field(default=None, max_length=600)
    linkedin_url: Optional[str] = Field(default=None, max_length=600)
    phone: Optional[str] = Field(default=None, max_length=40)


class FoundationRoleApplicationDecision(BaseModel):
    admin_note: Optional[str] = Field(default="", max_length=2000)


# ============ SUBSCRIPTIONS (Phase 6B.2) ============

class SubscriptionCheckoutRequest(BaseModel):
    plan_id: str
    origin_url: str



# ============ REFERRALS / PAYOUTS (Phase 6B.3) ============

class PayoutMarkPaid(BaseModel):
    method: Optional[str] = Field(default="manual", max_length=40)
    reference: Optional[str] = Field(default="", max_length=200)
    note: Optional[str] = Field(default="", max_length=2000)
