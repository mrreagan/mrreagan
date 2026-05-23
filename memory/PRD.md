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

## Iteration 3 — Email + auth + waitlist + AI regen (Feb 2026)
**Resend transactional email (dry-run fallback)**:
- `utils/mailer.py` thin async wrapper. When `RESEND_API_KEY` is blank OR `EMAIL_DRY_RUN=true`, queues emails to `db.outbound_emails` for inspection instead of sending.
- 8 brand-styled HTML templates: order_receipt, workshop_confirmation, waitlist_promotion, password_reset, qa_reply_notification, workshop_reminder, contact_autoreply, contact_admin_notify, newsletter_welcome (inline CSS, table layout, Cormorant Georgia serif fallback for max email-client compat).
- `utils/calendar_qr.py` builds .ics files + QR PNGs attached to workshop confirmations.
- `utils/scheduler.py` APScheduler runs `_send_workshop_reminders` every 30 min (window: workshops starting 23.5h-24.5h from now, paid registrations not yet reminded).

**Password reset**:
- `POST /api/auth/request-password-reset` — always returns success (no enumeration); creates 1h-expiry token in `db.password_reset_tokens` and emails reset link.
- `POST /api/auth/reset-password` — validates token, updates bcrypt hash, marks token used + invalidates all other outstanding tokens for the user.
- Frontend: `/forgot-password` + `/reset-password?token=...` pages, "Forgot your password?" link on Login.

**Registration cancel + waitlist auto-promotion**:
- `DELETE /api/registrations/{id}` — participant self-service (must be owner, not checked-in). Marks cancelled + emails first non-notified waitlister.
- `POST /api/registrations/{id}/release` — admin/facilitator manual seat release with same promotion path.
- `POST /api/registrations/promote-waitlist/{workshop_id}` — manual trigger.
- Frontend: "Cancel registration" button on Dashboard upcoming cards; "Release seat" button on FacilitatorDashboard participant rows.

**Side-effect emails wired in**:
- Stripe `_create_registration_from_txn` → workshop_confirmation w/ .ics + QR.
- Stripe `_create_order_from_txn` → order_receipt.
- Discussions `create_discussion` w/ parent_id + facilitator/admin role → qa_reply_notification (and auto-marks question answered).
- Contact form → contact_admin_notify (to support@birthright.live) + contact_autoreply (to sender, reply-to support@); optional newsletter_welcome on new opt-in.
- Newsletter signup → newsletter_welcome.

**Admin tooling**:
- `GET /api/admin/email-log` — combined sent + queued list with `real_send_enabled` flag.
- AdminDashboard `Email log` tab (4th tab) with status pills + dry-run banner.
- AdminProducts edit drawer: "Regenerate mockup with AI" section (prompt textarea + button) calling new `POST /api/products/{id}/regenerate-image` (admin only, uses EMERGENT_LLM_KEY + Nano Banana, saves to `/api/static/products/<slug>.png`).

**Env additions** (`/app/backend/.env`):
- `RESEND_API_KEY=` (blank for now)
- `SENDER_EMAIL=hello@birthright.live`
- `REPLY_TO_EMAIL=support@birthright.live`
- `ADMIN_NOTIFY_EMAIL=support@birthright.live`
- `PUBLIC_APP_URL=https://birthright.live`
- `EMAIL_DRY_RUN=true`

**Test status**: 25/25 iteration-4 backend tests pass (`/app/test_reports/iteration_4.json`); frontend self-verified via screenshots.

## Iteration 4 — Workshop CRUD + photo galleries (Feb 2026)
**Admin/Facilitator workshop management** (`/admin/workshops`):
- List, search, status filter (all/draft/upcoming/in-progress/completed/cancelled), create/edit drawer.
- `POST /workshops/{id}/duplicate` — clones a workshop into a new draft, dates shifted +30 days, new auto-generated check-in code, slug suffixed `-copy` (with `-copy-2` fallback on collision).
- `POST /workshops/{id}/cancel` — full pipeline: refunds all paid registrations via `stripe.Refund.create` against the original `payment_intent`, marks each registration cancelled with refund metadata, emails every registrant with the new `workshop_cancelled` template (includes refund amount + status), then flips workshop status. Seeded `payment_session_id='seed_demo'` short-circuits to status='manual' to avoid Stripe errors.
- `GET /workshops/{id}/revenue` — paid_count, cancelled_count, checked_in_count, gross/refunded/net.
- Hardened: `check_in_code` now auto-generated server-side via `_gen_check_in_code()` (6-char unambiguous alphanumeric) — never accepted from client. Facilitators auto-assign themselves as the workshop's facilitator on create.

**Workshop photo galleries** (new `Photos` tab in WorkshopHub):
- `POST /workshop-photos/{workshop_id}` multipart — paid attendees + workshop facilitator + admin allowed. Pillow pipeline strips EXIF, normalizes orientation, resizes to 1600px max, generates 400px thumb, saves as JPEG to `/app/backend/static/workshop_photos/<workshop_id>/<photo_id>.jpg`. Served at `/api/static/workshop_photos/...`. Participant uploads → status='pending'; facilitator/admin uploads → auto-approved. 8MB cap (pre-check via Content-Length, hard check after read).
- `GET /workshop-photos/{workshop_id}` — public list, defaults to approved only.
- `GET /workshop-photos` — cross-workshop pending queue (admin all; facilitator scoped to their workshops; participant 403).
- `POST /workshop-photos/{photo_id}/approve` and `/reject` (with reason) — facilitator-of-workshop or admin.
- `DELETE /workshop-photos/{photo_id}` — uploader can delete own pending/rejected; admin can delete any.
- Frontend: `/admin/photos` cross-workshop moderation queue; PhotosTab upload widget + status chip on pending uploads + approved photo grid.

**New email template**:
- `workshop_cancelled` — context-aware refund language (succeeded vs pending vs manual).

**Misc**:
- Bumped to `v1.3.0` (API root + FastAPI app version).
- Added "Manage workshops" + "Photo queue" quick-action buttons on FacilitatorDashboard.
- Added "Photo Moderation" quick-action card on AdminDashboard overview.

## Iteration 5 — Real-time chat over WebSocket (Mar 2026)
- `WS /api/ws/chat/{workshop_id}` — cookie or `?token=` JWT auth; in-memory `ws_manager` room registry; group + DM frame types; typing + presence broadcasts; 4000-char content cap; persists to `db.chat_messages` before broadcast; REST GET/POST endpoints retained for fallback.
- `useChatSocket` React hook — exponential 1/2/4/8s backoff capped 30s; 25s ping; `fallback` state after 3 failures so parent component can resume REST polling.
- ChatTab integrates own bubble alignment, presence dot, typing indicator with 3-dot animation, DM thread filter.
- Bumped to `v1.4.0`. 16/16 iter-5 pytest cases green (`/app/test_reports/iteration_5.json`).

## Iteration 6A.1 — Universal Polymorphic Reviews (May 2026)
- New `routers/reviews.py` — one collection covers workshops, products, future services. Each review carries `{subject_type, subject_id, subject_category, partner_id, verified_purchase, moderated, reports[]}`.
- Endpoints: `POST /reviews` (create or update, idempotent per user+subject), `GET /reviews` (list with `subject_type+subject_id` or legacy `workshop_id`), `GET /reviews/search` (cross-site browse with category/min_rating/q filters, debounced), `GET /reviews/aggregate` (count + avg + verified_count), `POST /reviews/{id}/report`, `POST /reviews/{id}/moderate` (admin + ombudsman).
- Workshops require paid registration to review; products allow any signed-in user but flag verified_purchase only for paid buyers.
- Frontend: `ReviewSection` component (used in WorkshopHub Review tab + ProductDetail) with star input, anonymous toggle, edit-in-place, report-with-reason, admin Hide/Restore; `AggregateRatingBadge` for compact display on shop cards; new `/reviews` `ReviewsBrowser` cross-site search page.
- Migration script `scripts/migrate_reviews_to_polymorphic.py` backfilled existing workshop reviews (already executed).
- Bug fixed: `ReviewSection` was destructuring a non-existent `isAuthenticated` from AuthContext; replaced with `!!user`. Edit flow now renders form correctly on click.
- Bumped to `v1.5.0`. Iter-6 testing: backend 16/16 PASS, frontend 8/8 flows verified after edit-flow fix (`/app/test_reports/iteration_6.json`).

## Phase 2 — Backlog (P0/P1)
- **P0 (DONE in Iter 3)**: Email infrastructure via Resend (currently dry-run; flip `EMAIL_DRY_RUN=false` + add `RESEND_API_KEY` to go live)
- **P0 (DONE in Iter 5)**: WebSocket real-time chat
- **P0 (DONE in Iter 6A.1)**: Universal polymorphic reviews
- **P0 (NEXT — 6A.2)**: Governance & Legal Architecture — 4 partner schema (Facilitator/Community/Research/Vendor), `governance_member` + `is_ombudsman` flags, admin console for global rev-share defaults, governance vote workflow, versioned universal indemnification, audit log
- **P0 (6B)**: Partner Onboarding & Revenue — facilitator licensing, community referral tracking + payouts, vendor subscriptions + listings queue, research submissions, public `/partners` profiles
- **P1 (6C)**: Communications — user↔partner messaging, partner↔partner messaging, ombudsman dashboard, dispute/escalation workflow
- **P1**: Domain verification for `birthright.live` on Resend (DNS records — user action, takes 5 min)
- **P1**: Photos & resources library per workshop; Workshop FAQ admin UI; Admin CRUD UIs for workshops/foundation content (products UI already shipped)
- **P1**: SMS check-in reminders (Twilio)
- **P1**: Sponsor recognition wall page; sponsorship upgrade flow (Amethyst → Ruby etc.)
- **P1**: Stripe webhook signature verification hardening; admin self-demotion guard
- **P1**: Image upload widget on Admin Products (alongside the regen button)
- **P2**: Inbound email parsing (e.g., reply-to-create-support-request); admin email-resend button on log rows; bulk product CSV import
- **P2**: Multi-language (en/es); Native mobile app; Advanced analytics dashboard; Refund / cancellation flow

## Test credentials
See `/app/memory/test_credentials.md`

## Known limitations
- Real-time chat is polling-based (4s interval) — functionally identical UX, swap for WebSocket in Phase 2
- Email/SMS notifications NOT WIRED — all communication is in-app only
- Stripe webhook endpoint registered but signature verification not strict — fine for MVP, harden before live launch
