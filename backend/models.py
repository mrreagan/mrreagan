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
    track: Optional[Literal["foundations", "practice", "living_the_work"]] = None
    is_foundation: bool = False


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
    track: Optional[Literal["foundations", "practice", "living_the_work"]] = None
    is_foundation: Optional[bool] = None


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
    # Extra angles / detail shots for the product detail gallery. The first
    # image_url is always the hero; these render as clickable thumbnails so
    # buyers can see details mentioned in the description that the hero shot
    # can't show (e.g., a flame stamped inside a mug).
    additional_images: List[str] = Field(default_factory=list)
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
    # Curated collections (e.g., "founder_collection"). Free-form slug so the
    # foundation can add new collections without a code release.
    collection: Optional[str] = None
    # Max units of this SKU a single customer can put in their cart, or None
    # for unlimited. Used by the Founder Collection hat pair (one per buyer).
    max_per_order: Optional[int] = None
    # When True, this product becomes the featured item in the homepage
    # Founder Collection teaser. Kept for backward-compatibility; new
    # control surface is `carousel_rank` below.
    is_homepage_feature: bool = False
    # Founder Collection carousel rank (1, 2, 3). Lower = appears earlier in
    # the swipeable teaser on the Equip page. None / 0 means the product is
    # NOT featured in the carousel (it still appears in the full /equip/
    # collection/founder grid). Up to 3 products at a time.
    carousel_rank: Optional[int] = None
    # Foundation-member wholesale price (board members, paid staff, etc. —
    # anyone with user.is_foundation = True). When None, foundation members
    # see the retail `price` like everyone else. Always strictly ≤ retail.
    wholesale_price: Optional[float] = None


class Product(ProductCreate):
    id: str
    created_at: str


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    additional_images: Optional[List[str]] = None
    inventory: Optional[int] = None
    category: Optional[str] = None
    collection: Optional[str] = None
    max_per_order: Optional[int] = None
    is_homepage_feature: Optional[bool] = None
    carousel_rank: Optional[int] = None
    wholesale_price: Optional[float] = None


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

PARTNER_TYPES = ("facilitator", "community", "research", "vendor", "artist", "steward")
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
    partner_type: Literal["facilitator", "community", "research", "vendor", "artist", "steward"]
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
    # Artist-specific
    mediums: Optional[str] = Field(default=None, max_length=500, description="Comma-separated: painting, photography, ceramics, chamber music…")
    artist_statement: Optional[str] = Field(default=None, max_length=4000)
    own_gallery_url: Optional[str] = Field(default=None, max_length=600)
    representative_works_url: Optional[str] = Field(default=None, max_length=600)
    accepts_commissions: Optional[bool] = None
    # Steward-specific
    requested_community_slug: Optional[str] = Field(default=None, max_length=200, description="Geographic path e.g. north-america/us/california/santa-cruz")
    community_ties: Optional[str] = Field(default=None, max_length=4000, description="How are you rooted in this community?")
    moderation_experience: Optional[str] = Field(default=None, max_length=2000)
    # Founding-partner request flag (v1.11.0 step 5)
    apply_as_founding_partner: bool = False


class PartnerInviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    partner_type: Literal["facilitator", "community", "research", "vendor", "artist", "steward"]
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
    # Phase 6C.1 — DM opt-in
    accepts_new_dms: Optional[bool] = None


# ============ PARTNER ECONOMY (v1.11.0) ============

class FeaturePartnerRequest(BaseModel):
    """Admin: mark a partner profile as 'featured' for a window."""
    until: str  # ISO datetime
    mission_alignment: str = Field(default="", max_length=2000)
    signature_content: Optional[str] = Field(default=None, max_length=4000)
    video_url: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list, max_length=3)
    custom_cta: Optional[str] = Field(default=None, max_length=200)


class FeaturedContentUpdate(BaseModel):
    """Partner-facing: edit their own featured content while the window is active."""
    mission_alignment: Optional[str] = Field(default=None, max_length=2000)
    signature_content: Optional[str] = Field(default=None, max_length=4000)
    video_url: Optional[str] = Field(default=None, max_length=600)
    image_urls: Optional[list[str]] = Field(default=None, max_length=3)
    custom_cta: Optional[str] = Field(default=None, max_length=200)
    custom_cta_url: Optional[str] = Field(default=None, max_length=600)


class FeatureCheckoutRequest(BaseModel):
    partner_type: str  # which of caller's profiles to feature
    origin_url: str
    # The partner can pre-fill content here so it's ready the moment payment clears
    mission_alignment: Optional[str] = Field(default="", max_length=2000)
    signature_content: Optional[str] = Field(default=None, max_length=4000)
    video_url: Optional[str] = Field(default=None, max_length=600)
    image_urls: list[str] = Field(default_factory=list, max_length=3)
    custom_cta: Optional[str] = Field(default=None, max_length=200)
    custom_cta_url: Optional[str] = Field(default=None, max_length=600)


class FoundingPartnerCapUpdate(BaseModel):
    cap: int = Field(ge=1, le=10000)


# ============ RESEARCH ARTIFACTS (Phase v1.11.0 step 6) ============

ResearchArtifactTier = Literal["brief", "paper"]
ResearchArtifactStatus = Literal["draft", "pending_review", "changes_requested", "rejected", "published", "archived"]


class ResearchArtifactCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    abstract: str = Field(min_length=10, max_length=4000)
    authors: str = Field(min_length=2, max_length=500)
    publication_date: str  # ISO date
    full_text_url: str = Field(min_length=4, max_length=600)
    doi: Optional[str] = Field(default=None, max_length=200)
    cover_image_url: Optional[str] = Field(default=None, max_length=600)
    categories: list[str] = Field(default_factory=list, max_length=8)
    tags: list[str] = Field(default_factory=list, max_length=12)
    estimated_read_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    tier: ResearchArtifactTier = "brief"
    status: ResearchArtifactStatus = "draft"


class ResearchArtifactUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=300)
    abstract: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    authors: Optional[str] = Field(default=None, min_length=2, max_length=500)
    publication_date: Optional[str] = None
    full_text_url: Optional[str] = Field(default=None, min_length=4, max_length=600)
    doi: Optional[str] = Field(default=None, max_length=200)
    cover_image_url: Optional[str] = Field(default=None, max_length=600)
    categories: Optional[list[str]] = Field(default=None, max_length=8)
    tags: Optional[list[str]] = Field(default=None, max_length=12)
    estimated_read_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    tier: Optional[ResearchArtifactTier] = None
    status: Optional[ResearchArtifactStatus] = None


class ResearchModerationDecision(BaseModel):
    """Admin decision body for approve / request-changes / reject."""
    note: Optional[str] = Field(default=None, max_length=2000)


class ResearchPromoteCheckout(BaseModel):
    artifact_id: str
    origin_url: str


# ============ PAYOUTS / W9 / METHOD (Phase v1.11.0 step 7) ============

W9Classification = Literal[
    "individual", "sole_proprietor", "c_corporation", "s_corporation",
    "partnership", "trust_estate", "llc",
]
TinType = Literal["SSN", "EIN"]
PayoutMethodType = Literal["stripe_connect", "manual_ach"]


class W9Form(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    business_name: Optional[str] = Field(default=None, max_length=200)
    classification: W9Classification
    exempt_payee_code: Optional[str] = Field(default=None, max_length=10)
    address_line1: str = Field(min_length=3, max_length=200)
    address_line2: Optional[str] = Field(default=None, max_length=200)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=50)
    zip_code: str = Field(min_length=4, max_length=20)
    country: str = Field(default="US", max_length=2)
    tin: str = Field(min_length=9, max_length=11)  # SSN: 9 digits + 2 dashes
    tin_type: TinType
    signature_name: str = Field(min_length=2, max_length=200)


class PayoutMethodSet(BaseModel):
    method_type: PayoutMethodType
    # Stripe Connect
    stripe_account_id: Optional[str] = Field(default=None, max_length=200)
    # Manual ACH — sensitive, encrypted at rest
    bank_name: Optional[str] = Field(default=None, max_length=200)
    account_holder_name: Optional[str] = Field(default=None, max_length=200)
    routing_number: Optional[str] = Field(default=None, min_length=9, max_length=9)
    account_number: Optional[str] = Field(default=None, min_length=4, max_length=20)


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


class PartnerSalesReportDecision(BaseModel):
    """Admin reviews a submitted partner sales report. Approving credits the partner
    at off_site_pct (overrides first, else global default for that partner_type).
    Disputing requires a reason."""
    admin_note: Optional[str] = Field(default="", max_length=2000)
    override_gross_usd: Optional[float] = Field(default=None, ge=0)
    override_pct: Optional[float] = Field(default=None, ge=0, le=100)


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


class SubscriptionPlanChangeRequest(BaseModel):
    """Mid-flight plan change. Pro-rates the unused remainder of the active
    subscription as credit toward the new plan's Stripe checkout amount."""
    new_plan_id: str
    origin_url: str


class SubscriptionCancelRequest(BaseModel):
    """Partner-initiated cancel. The paid window stays active to expires_at;
    no auto-prompts to renew after that. Optional reason for retention insight."""
    reason: Optional[str] = Field(default="", max_length=2000)


class AdminSubscriptionRevokeRequest(BaseModel):
    """Admin revoke. Optional refund flag. Reason is required."""
    reason: str = Field(min_length=3, max_length=2000)
    refund: bool = False



# ============ REFERRALS / PAYOUTS (Phase 6B.3) ============

class PayoutMarkPaid(BaseModel):
    method: Optional[str] = Field(default="manual", max_length=40)
    reference: Optional[str] = Field(default="", max_length=200)
    note: Optional[str] = Field(default="", max_length=2000)


# ============ DIRECT MESSAGES (Phase 6C.1) ============

DmThreadStatus = Literal["pending", "active", "blocked", "archived"]


class DmThreadCreate(BaseModel):
    """Open or fetch a thread with another user. First message body is optional —
    if provided, we attempt to send it immediately (rejected with `pending` if the
    recipient has `accepts_new_dms=False`)."""
    recipient_id: str = Field(min_length=1, max_length=120)
    initial_message: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    # Optional context — the share URL or surface that triggered the message
    share_url: Optional[str] = Field(default=None, max_length=600)


class DmMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class DmThreadFlag(BaseModel):
    """Anyone in the thread can flag it for ombudsman review."""
    reason: str = Field(min_length=3, max_length=2000)


class DmAcceptsToggle(BaseModel):
    accepts_new_dms: bool


# ============ END Phase 6C.1 ============


# ============ DISPUTES (Phase 6C.3) ============

DisputeStatus = Literal["open", "under_review", "resolved", "dismissed"]
DisputeCategory = Literal["payment", "conduct", "content", "other"]


class DisputeCreate(BaseModel):
    """File a dispute. `against_user_id` is who the dispute is about.
    `transaction_id` optionally ties it to a specific Stripe payment_transactions
    row (sets up Step 10 clawback cascade)."""
    against_user_id: str = Field(min_length=1, max_length=120)
    category: DisputeCategory
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=20, max_length=8000)
    transaction_id: Optional[str] = Field(default=None, max_length=120)
    thread_id: Optional[str] = Field(default=None, max_length=120)


class DisputeAssign(BaseModel):
    ombudsman_user_id: str = Field(min_length=1, max_length=120)


class DisputeStatusUpdate(BaseModel):
    status: DisputeStatus
    note: str = Field(min_length=3, max_length=4000)


class DisputeResolution(BaseModel):
    """Final resolution. `outcome` is dismissed | upheld | partial. Optional
    `financial_credit_usd` records that a refund or credit should follow when
    Step 10 (clawback cascade) lands."""
    outcome: Literal["dismissed", "upheld", "partial"]
    resolution_note: str = Field(min_length=10, max_length=8000)
    financial_credit_usd: Optional[float] = Field(default=None, ge=0)
    trigger_refund_cascade: bool = False


class RefundCascadeRequest(BaseModel):
    """Admin-initiated refund. Triggers full cascade (Stripe + side-effects + clawback)."""
    txn_id: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=5, max_length=2000)
    skip_stripe: bool = False


class ClawbackResolve(BaseModel):
    """Mark a clawback_pending row as resolved (recovered or written off)."""
    status: Literal["recovered", "written_off"]
    note: str = Field(min_length=3, max_length=2000)


class AgreementSignGate(BaseModel):
    """Check + force whether the active agreement requires fresh signing."""
    force_resign: bool = False


# ============ END Phase 6C.3 ============


# ============ SHARES & BOOKMARKS (v1.11.0 Step 8.5) ============

BookmarkableType = Literal[
    "workshop", "product", "research", "partner", "facilitator",
    "foundation_role", "proposal", "impact_statement",
]
ShareSurface = Literal[
    "workshop", "product", "research", "partner", "facilitator",
    "foundation_role", "proposal", "impact_statement", "page",
]
ShareChannel = Literal[
    "copy_link", "qr", "email", "sms", "ics", "cite", "download",
    "native_share", "facebook", "twitter", "linkedin", "messenger",
    "whatsapp", "bookmark",
]


class ShareLogCreate(BaseModel):
    """Anon or auth event — caller hits this when a share affordance is used,
    or when a page loads with `?via=` to attribute the inbound visit."""
    surface: ShareSurface
    surface_id: Optional[str] = Field(default=None, max_length=200)
    channel: ShareChannel
    via: Optional[str] = Field(default=None, max_length=100)  # referral code OR user id OR anon-XXX
    path: Optional[str] = Field(default=None, max_length=600)
    session_id: Optional[str] = Field(default=None, max_length=100)


class BookmarkCreate(BaseModel):
    subject_type: BookmarkableType
    subject_id: str = Field(min_length=1, max_length=120)
    label: Optional[str] = Field(default=None, max_length=300)
    note: Optional[str] = Field(default=None, max_length=1000)


# ============ DISBURSEMENT (v1.11.0 Step 8) ============

class DisbursementSettings(BaseModel):
    """Admin-set foundation-wide disbursement schedule."""
    next_disbursement_date: Optional[str] = Field(default=None, max_length=40)  # ISO date
    cadence: Optional[str] = Field(default="monthly", max_length=40)
    notes: Optional[str] = Field(default="", max_length=600)
