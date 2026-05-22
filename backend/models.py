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
    workshop_id: str
    rating: int = Field(ge=1, le=5)
    review_text: str
    anonymous: bool = False


class Review(ReviewCreate):
    id: str
    user_id: str
    user_name: str
    created_at: str


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
