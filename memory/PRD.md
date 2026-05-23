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

## Iteration 7 — Phase 6A.2 Governance & Legal Architecture (May 2026)
- **Backend models** (appended to `models.py`): `RevShareTier`, `GlobalDefaults*`, `Proposal`/`ProposalCreate`/`VoteCast`/`GovernanceVote`, `MemberFlagsUpdate`, `IndemnificationCreate`/`IndemnificationVersion`/`IndemnificationSignature`, `AuditLogEntry`. UserProfile now exposes `governance_member` + `is_ombudsman`.
- **`utils/audit.py`** — append-only `log_action(db, actor, action, target_type, target_id, metadata)`. Fire-and-forget: never blocks the originating action.
- **`routers/governance.py`** — `GET/PUT /api/governance/defaults` (admin write, public read); `GET/PUT /api/governance/members/{id}` (admin write, signed-in read; ombudsman implies member); `POST/GET /api/governance/proposals` + `/{id}` + `/{id}/vote` (re-cast updates same row) + `/{id}/close` (admin/ombudsman → passed/failed; proposer → withdrawn) + `/{id}/votes`. Default rev-share: facilitator 70 / community 10 / research 0 / vendor 80.
- **`routers/legal.py`** — versioned universal indemnification. `GET /api/legal/indemnification/active` auto-bootstraps v1.0; `POST /versions` (admin) publishes new version + deactivates prior + updates global_defaults pointer; `POST /sign` is idempotent; `GET /my-status` flips signed→false when a new version is published (signatures bind to version_id).
- **`routers/audit.py`** — `GET /api/audit?action_prefix=&actor_id=&target_type=&target_id=` (admin OR ombudsman only).
- **`scripts/seed_governance_v1.py`** — idempotent: promotes admin + facilitators to `governance_member=True`, admin to `is_ombudsman=True`, seeds v1.0 indemnification placeholder, inserts global_defaults singleton.
- **Frontend** — three new pages: `/governance/proposals` (list + create modal + detail modal with vote/withdraw/close + vote log), `/legal/indemnification` (active body + sign-with-checkbox + signed badge), `/admin/governance` (4 tabs: Defaults editor with add/remove tier per partner type; Members panel with toggle flags + user search via `/admin/users`; Indemnification panel with version list + publish new; Audit log viewer with action_prefix filter). Public `/governance` page now has two callout cards linking to the new screens; Admin Dashboard has a new "Governance & Legal" quick-action card.
- **Bumped to `v1.6.0`.** Iter-7 testing: backend 30/30 PASS, frontend ~95% (all critical flows verified; only cosmetic data-testid renaming requests). Report at `/app/test_reports/iteration_7.json`.

## Iteration 8 — Refactor / cleanup (May 2026)
- **No new features.** Addresses code-review findings without changing public API contracts.
- **Backend extractions:**
  - `routers/community.py` — `_notify_question_author_of_reply` lifted out of `create_discussion`; orchestrator now ~12 lines, complexity drops from 16 to 4.
  - `routers/workshops.py` — `_refund_registration`, `_mark_registration_cancelled`, `_email_registrant_cancellation` split from `cancel_workshop`. Loop body in `cancel_workshop` is now 3 calls + tally append.
  - `utils/mailer.py` — `_build_log_doc` + `_real_send_via_resend` split from `send_email`. Public signature unchanged.
- **Type hints:** added to `server.py` (root/health/startup/shutdown/stripe_webhook_endpoint) and `seed_data.py` (every public + helper function).
- **Frontend component splits:**
  - `components/ReviewSection.jsx` (was 291 LOC) → orchestrator at 158 LOC + `components/reviews/{StarRow,ReviewItem,ReviewForm,AggregateRatingBadge}.jsx`. `AggregateRatingBadge` re-exported from `ReviewSection` for back-compat.
  - `components/workshop-hub/ChatTab.jsx` (was 274 LOC) → orchestrator at ~180 LOC + `components/workshop-hub/chat/{ConnectionPill,ParticipantsSidebar,MessagesList,TypingIndicator}.jsx`. View-match logic moved to top-level helpers; silent catches replaced with `console.error` carrying context.
  - `components/admin/WorkshopFormDrawer.jsx` — extracted `buildWorkshopPayload`, `validateWorkshopPayload`, `persistWorkshop`. `submit()` is now 12 lines. Removed native `required` from title/slug/short-desc so the explicit Sonner toast actually runs.
- **Hook polish:** `useChatSocket.js` empty `catch {}` blocks (×3) replaced with `console.debug/warn` tagged `[chat-ws]`. `useWorkshop.js` empty catches (×4) replaced with `console.error/warn` carrying the resource id.
- **Iter-8 testing:** backend 98/98 PASS (87 prior-iter regression + 11 new refactor-specific), frontend ~98% (only minor: chat sub-components had testids correctly, agent's note was a misread). Report `/app/test_reports/iteration_8.json`.

## Iteration 9 — Phase 6B.1 Partner Onboarding Foundation (May 2026)
- **Models** (appended to `models.py`): `PartnerApplyData` (per-type fields incl. facilitator `presents_birthright_ip` boolean), `PartnerInviteCreate`, `PartnerApplicationDecision`, `PartnerProfileUpdate`.
- **`routers/partners.py`**:
  - Self-serve: `POST /api/partners/apply` (with per-type validation; facilitator must declare Birthright IP intent), `GET /api/partners/my-applications`, `GET /api/partners/my-profiles`, `PUT /api/partners/my-profiles/{type}`.
  - Public directory: `GET /api/partners?partner_type=&q=&limit=` (regex search over headline/bio/location/display_name), `GET /api/partners/{slug}`.
  - Admin: `GET /api/admin/partners/applications` (enriched with applicant_email/name), `POST /api/admin/partners/invite` (creates pending app + dry-run invite email), `POST /api/admin/partners/applications/{id}/{approve|reject}`, `POST /api/admin/partners/profiles/{id}/{revoke|reinstate}`.
  - Slug uniquification via `_unique_slug`. All write actions audit-logged via `log_action`.
  - One profile per (user_id, partner_type); pending-app deduplication.
- **Frontend pages**:
  - `/partners` — tabbed public directory (all/facilitator/community/research/vendor) + debounced search + per-card link.
  - `/partners/:slug` — public detail page (headline, bio, location, website link, photo).
  - `/partners/apply` — auth-gated multi-type form; type picker swaps subforms; facilitator subform has explicit yes/no "Presents Birthright IP?" buttons + Phase 6B.2 callout.
  - `/dashboard/partner` — applicant workspace: status of own applications + inline editor for approved profile cards (headline/bio/location/photo/website/public toggle).
  - `/admin/partners` — status tabs + type filter + expandable row showing every applied field + approve/reject with admin_note + "Invite partner" modal.
- **Navigation**: "Partners" link added to main navbar + footer; participant Dashboard gains a partner CTA card; AdminDashboard gains a "Partner applications" quick-action card.
- **Bug fix**: PartnersDirectory card badge no longer clips trailing letter ("RESEARC"/"COMMUNIT" → now full "RESEARCH"/"COMMUNITY"); replaced `cfg.label.slice(0, -1)` with explicit `singular` per type.
- **Bumped to `v1.7.0`.** Iter-9 testing: backend **34/34 PASS**, frontend ~95% (badge bug fixed post-test; all other findings were testid-naming nits where the testids do exist). Report at `/app/test_reports/iteration_9.json`.

## Phase 6B sub-phases — still to do
- **6B.2** — Stripe subscriptions + auto-licensing + rev-share tier resolution (facilitator dual-tier: Birthright IP vs other materials; shorter sub = higher %, longer = lower %)
- **6B.3** — Community referrals: per-user code + per-workshop affiliate link + attribution + payout records
- **6B.4** — Vendor autonomous catalog (vendor CRUD on own products) + admin override
- **6B.5** — Research submissions queue + public listing

## Iteration 10 — Phase 6B.2 Partner Subscriptions, Auto-Licensing, Dual-Tier Rev-Share (May 2026)
- **Design decision**: v1 uses one-time Stripe payments for fixed-duration plans (NOT recurring Stripe Subscriptions). On payment success `partner_subscription.expires_at = now + duration_months`. License is active while `expires_at > now`. Clean upgrade path to true Stripe Subscriptions later.
- **`routers/subscriptions.py`**: `GET /api/subscriptions/plans?partner_type=`, `POST /api/subscriptions/checkout` (gated: caller must have approved partner_profile of matching type), `GET /api/subscriptions/my` (hydrates plan + computed is_active). `create_subscription_from_txn` is **idempotent** by `payment_session_id`.
- **`routers/checkout.py`**: registered `"subscription"` in `_PAID_HANDLERS` so existing Stripe webhook fulfilment dispatches to the subscriptions module without duplication.
- **`utils/rev_share.py`**: `resolve_rev_share(db, user_id, partner_type, *, presents_birthright_ip=False)`. Precedence: active subscription → global_defaults → 0%. Facilitator dual-tier branching (`birthright_ip_pct` vs `other_content_pct`).
- **`routers/partners.py`**: new `GET /api/partners/my-rev-share/{partner_type}?presents_birthright_ip=` for caller-visible rate preview.
- **`scripts/seed_subscription_plans.py`** (idempotent): seeded 12 plans — Facilitator/Community/Research/Vendor × Monthly/Annual/2-Year. Examples:
  - Facilitator: $99/mo (70/50%) · $999/yr (65/45%) · $1799/2yr (60/40%)
  - Community: $29/mo (12%) · $299/yr (10%) · $549/2yr (8%)
  - Research: $49/mo (0%) · $499/yr (0%) · $899/2yr (0%) — grant-funded by default
  - Vendor: $49/mo (82%) · $499/yr (78%) · $899/2yr (75%)
- **Frontend**:
  - `/partners/subscribe?type=...` — plan picker with per-type tabs, "Most chosen" annual ribbon, facilitator dual-tier display (Birthright IP green, Own/other neutral). Banner when caller lacks approved profile.
  - `SubscriptionStatusCard` exported from PartnerSubscribe — rendered in `/dashboard/partner` per profile: shows LICENSED + days-remaining countdown + Renew CTA when ≤30 days OR "NO ACTIVE SUBSCRIPTION" + View plans CTA.
  - `/partners/apply` facilitator subform banner updated to link to `/partners/subscribe?type=facilitator` (no longer "coming soon").
- **Bumped to `v1.8.0`.** Iter-10 testing: backend **19/19 PASS**, frontend **100%** (`/app/test_reports/iteration_10.json`). Zero defects.

## Phase 6B sub-phases — remaining
- **6B.5** — Research submissions queue + public listing on `/partners?tab=research`

## Iteration 14 — Production catalog self-heal (May 2026)
- **Problem:** Production `birthright.live` was missing 50 of the 60 AI-generated merch items, plus two items (Birthright Hardcover Journal, Enamel Pin — Flame) showed broken thumbnails. Root cause: the 50-item catalog was originally seeded via a manual one-time migration (`scripts/seed_merch_catalog.py`) that was never wired into the startup hook, so it never ran in production. The two items with broken thumbnails had legacy Unsplash CDN URLs in their `image_url` that had since 404'd.
- **Fix:** New module `backend/runtime_seed.py` runs on EVERY startup (not just empty-DB):
  - `ensure_catalog_seeded(db)` — reads `data/catalog.json`, inserts any items whose `slug` is missing from the products collection. Idempotent. Points `image_url` at the committed PNGs in `backend/static/products/<slug>.png` (no Gemini calls at runtime).
  - `repair_known_broken_images(db)` — matches products by NAME (stable across environments since IDs differ) and rewrites `image_url` for any whose URL is external/empty/wrong. Currently heals "Birthright Hardcover Journal" and "Enamel Pin — Flame".
- **Bonus:** Both regenerated PNGs renamed from `<slug>-<id_prefix>.png` to stable `<slug>.png` so the seed paths are stable across deploys.
- **Wired** into `server.py` startup hook right after `seed_if_empty(db)`. Logs `inserted/skipped` and per-name repair counts.
- All 52 product PNGs are committed to git, so production filesystem gets them automatically on deploy. No CDN dependency.

## Iteration 11 — Phase 6B.3 Community Referrals + Reporting MVP (May 2026)
- **`routers/referrals.py`** — `GET /api/r/{code}` redirect-and-set-cookie (30-day max-age, samesite=lax, secure), `GET /api/referrals/my-link/{partner_type}`, `GET /api/referrals/my-earnings`, admin: `GET /api/admin/referrals?status=` filter, `GET /api/admin/referrals/payout-summary` per-partner aggregate w/ user enrichment, `POST /api/admin/referrals/{id}/mark-paid` (idempotent — 400 if already paid).
- **`routers/reports.py`** — `GET /api/me/reports` returns `{engagement, finance, partner}` (partner is null when caller has no profile); `GET /api/admin/reports` returns `{engagement, revenue, payouts, top_partners, top_workshops}` (admin only).
- **Checkout integration** — `routers/checkout.py` reads `birthright_ref` cookie and writes it into `payment_transactions.metadata.referral_code`. On fulfilment, `record_referral` inserts a `referrals` row idempotently keyed on payment_session_id with `payout_amount = order_total * rev_share_pct / 100`. Community partners are the only type that earns referrals in v1; self-attribution is blocked.
- **Frontend** — `/dashboard/reports` (MyReports, engagement + spending + optional partner earnings), `/admin/reports` (Foundation reports), `/admin/payouts` (per-partner liability + earned/paid tabs + inline mark-paid form). `PartnerEarningsCard` shows pending/lifetime/paid + referral link + Copy + recent attributions — rendered only for community partner profiles.
- **Bumped to `v1.9.0`.** Iter-11 testing: backend **25/25 PASS**, frontend **100%** (`/app/test_reports/iteration_11.json`). Zero defects.

## Iteration 12+13 — Phase 6B.4 Vendor Autonomous Catalog (May 2026)
- **Design decisions** (per user): vendors set prices freely; auto-publish; admin can flag/unpublish anytime; print-on-demand assumption (no inventory tracking); products clearly identify their vendor on the storefront. Cross-vendor sort/filter for the public store was DEFERRED to advanced search backlog.
- **Models extended** (`models.py`) — `ProductCreate` gained `is_vendor_product`, `vendor_partner_id`, `vendor_user_id`, `vendor_name`, `vendor_slug`, `moderation_status` (active|flagged|unpublished), `moderation_note`. New `VendorProductCreate`/`VendorProductUpdate`/`VendorModerationAction` request models.
- **`routers/vendor_catalog.py`** — Vendor self-serve: `GET/POST /api/vendor/products`, `PUT/DELETE /api/vendor/products/{id}` (gated by active vendor `PartnerProfile`; 400 on delete if any paid orders reference the product; 400 on edit if product is unpublished). Admin moderation: `GET /api/admin/vendor-products?status=&vendor_user_id=`, `POST .../flag` + `/unflag` + `/unpublish` + `/restore`. All write actions audit-logged. `vendor_name` snapshots from `profile.meta.business_name` (fallback `display_name`) at create time.
- **`routers/products.py`** — Public listing (`GET /api/products`) HIDES vendor products where `moderation_status != active`. Foundation products (no `is_vendor_product`) are unaffected. `GET /api/products/{id}` 404s flagged/unpublished vendor products for the public but admin + owner can still see. Added `?vendor_id=` filter.
- **Frontend pages** — `/dashboard/vendor/products` (vendor CRUD w/ live/flagged/unpublished filters, drawer-based create/edit, delete confirm, status badges, admin moderation notes shown to vendor); `/admin/vendor-products` (cross-vendor moderation table with Flag/Unflag/Unpublish/Restore actions, status tabs, search). Public Shop ProductCard + ProductDetail show "By <vendor_name>" badge linking to `/partners/<slug>`.
- **UX gating** — `/dashboard/vendor/products` pre-checks `/api/partners/my-profiles` and renders the `vendor-access-denied` empty state with Apply CTA for users without an active vendor profile (fix from iter12→iter13).
- **AdminDashboard quick-actions** updated: Vendor catalog, Partner payouts, Foundation reports cards added.
- **Bumped to `v1.10.0`.** Iter-12 backend **22/22 PASS**, iter-13 frontend retest **100% PASS** (`/app/test_reports/iteration_12.json` + `/app/test_reports/iteration_13.json`). Zero outstanding defects.

## Phase 2 — Backlog (P0/P1)
- **P0 (DONE in Iter 3)**: Email infrastructure via Resend (dry-run)
- **P0 (DONE in Iter 5)**: WebSocket real-time chat
- **P0 (DONE in Iter 6A.1)**: Universal polymorphic reviews
- **P0 (DONE in Iter 7 / 6A.2)**: Governance & Legal Architecture
- **P0 (DONE in Iter 8)**: Code-review cleanup (component splits + helper extractions + type hints)
- **P0 (NEXT — 6B)**: Partner Onboarding & Revenue — facilitator licensing, community referral tracking + payouts, vendor subscriptions + listings queue, research submissions, public `/partners` profiles
- **P1 (6C)**: Communications — user↔partner messaging, partner↔partner messaging, ombudsman dashboard, dispute/escalation workflow
- **P2 (Tech debt)**: Rate-limit auth + chat WS; flip `EMAIL_DRY_RUN=false` once Resend DNS verified; Redis pub/sub for `ws_manager.py` for horizontal scaling.
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
