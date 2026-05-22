# Birthright Foundation Platform — PRD

## Original problem statement
Build a website using birthright branding (teal/gold flame logo, motto "SECURE BONDS > THRIVE", mission "Secure bonds are our birthright. We exist to empower everyone with the tools and support we all occasionally need to claim and recover our secure bonds with our precious people. So we can all thrive.") featuring:
- Educational foundation site (about, contact, mission, governing members, education structure)
- Storefront for merch and workshop resources
- Workshop event advertising, registration, participant-only purchase of workshop materials
- Participant communication with fellow participants and facilitators
- Participant directions and check-in
- Public/private Q&A, comments, support requests to facilitators (before/during/after)
- Ratings and reviews of their workshop
- Personal impact statements (what they learned, how they grew, how they benefited, ideas to improve)

Domain: birthright.live · Address: 2148 W Earll Dr, Phoenix, AZ 85015

## Architecture
- **Backend**: FastAPI + MongoDB (Motor), modular routers (auth, workshops, products, checkout, community, foundation), JWT auth + bcrypt, Stripe via emergentintegrations
- **Frontend**: React + React Router + Tailwind, sonner toasts, lucide-react icons, Cormorant Garamond + Work Sans fonts
- **Payments**: Stripe Checkout (test mode `sk_test_emergent`) — workshop registrations, product orders, donations, sponsorships
- **Branding**: teal `#476B6B` primary, gold `#C9A961` accent, cream `#FAF8F5` background, light theme

## User personas
- **Guest** — browses workshops, public merch, foundation pages; can donate/sponsor; can submit contact form & newsletter signup
- **Participant** — registers for workshops, accesses workshop hub (directions/check-in/discussions/Q&A/chat/materials/review/impact/support), buys gated workshop materials
- **Facilitator** — manages assigned workshops, sees participants, answers Q&A & support requests, owns check-in code
- **Admin** — manages users (role changes), sees full stats, reviews contact messages

## Phase 1 — Implemented (Feb 2026)
**Public**: Home, About, Mission, Governance, Education, Contact, Workshops list/detail, Shop list/detail, Cart, Checkout success, Login, Register, Sponsorship (5 gemstone tiers + freeform donations), Facilitators list/profile, Newsletter
**Authenticated**: Participant Dashboard (My Workshops upcoming/past, My Journey, Order history), Workshop Hub with 8 tabs (Directions+QR check-in, Discussion board, Public/Private Q&A, polling-based Chat with DMs, Materials shop, Reviews with anonymous, Impact statements with public/anonymous toggles, Support requests), Profile editing
**Facilitator**: Dashboard with workshop list, participant roster, open Q&A (mark answered), open support requests (reply), check-in code display
**Admin**: Stats overview, user role management, contact message inbox

**Key features delivered**: Workshop capacity + early-bird/regular pricing; Stripe checkout for 4 transaction types; workshop_material gating (only registered participants); .ics calendar download after registration; QR + code-based check-in; waitlist; public impact statements feed homepage/workshop pages; facilitator profile pages with aggregated reviews

**Seeded demo data**: Admin + 2 facilitators + 1 demo participant; 4 workshops (3 upcoming, 1 past with review/impact); **60 products** (56 merch + 4 gated materials, including 50 AI-generated mission-inspired items); 4 governing members; full mission/about/education content

**Test status**: 68/70 backend tests pass + 13/13 iteration-2 product tests pass. Critical security fix applied (check_in_code stripped from public list endpoint).

## Iteration 2 — Storefront expansion & Admin UI (Feb 2026)
- **50 AI-generated thematic merch items** seeded into MongoDB via one-time idempotent migration `scripts/seed_merch_catalog.py`. Catalog defined in `data/catalog.json` (apparel 14, journals 3, books 4, prints 4, stickers 3, decks 3, home 12, bags 7). Price range $5–$95 (stickers cheap, blankets/hoodies/robes premium). Each item has a `slug` field for idempotency.
- **Image generation**: Gemini Nano Banana (gemini-3.1-flash-image-preview) via emergentintegrations + EMERGENT_LLM_KEY. Images saved to `/app/backend/static/products/<slug>.png` and served by FastAPI StaticFiles mounted at `/api/static/*`. 49/50 generated cleanly on first pass; 1 (`claim-your-birthright-hoodie-forest`) regenerated successfully.
- **Admin Products UI** at `/admin/products` (ADMIN_ROLES protected): list/search/filter (all/merch/material), create via slide-in drawer (full ProductCreate form incl. workshop linking for materials), edit (PUT with ProductUpdate subset), delete with confirm. Image URL field accepts both external URLs and `/api/static/products/...` paths with live preview.

## Phase 2 — Backlog (P0/P1)
- **P0**: True WebSocket real-time chat; Email notifications (Resend) for registration/payment/Q&A reply
- **P0**: Partner roles — facilitator partners, merchandise partners, community/service partners
- **P1**: Photos & resources library per workshop; Workshop FAQ admin UI; Admin CRUD UIs for workshops/products/foundation content (currently API-only); SMS check-in reminders (Twilio)
- **P1**: Sponsor recognition wall page; sponsorship upgrade flow (Amethyst → Ruby etc.)
- **P1**: Stripe webhook signature verification hardening; admin self-demotion guard
- **P2**: Multi-language (en/es); Native mobile app; Advanced analytics dashboard; Refund / cancellation flow

## Test credentials
See `/app/memory/test_credentials.md`

## Known limitations
- Real-time chat is polling-based (4s interval) — functionally identical UX, swap for WebSocket in Phase 2
- Email/SMS notifications NOT WIRED — all communication is in-app only
- Stripe webhook endpoint registered but signature verification not strict — fine for MVP, harden before live launch
