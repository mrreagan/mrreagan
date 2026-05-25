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

## Backlog — prioritized

### Phase 6C (multi-iteration roadmap)
1. ~~**6C.1** — User↔Partner + Partner↔Partner DMs~~ ✅ **SHIPPED in Iter 21**
2. ~~**6C.2** — Ombudsman queue at `/admin/ombudsman`~~ ✅ **SHIPPED in Iter 22**
3. ~~**6C.3** — Disputes workflow~~ ✅ **SHIPPED in Iter 22**

### v1.11.0 wrap-up (sequencing locked)
1. ~~**`v1.11.0-step8`** — Disbursement orchestration~~ ✅ **SHIPPED in Iter 19**
2. ~~**`v1.11.0-step8.5`** — **Universal Share & Save System**~~ ✅ **SHIPPED in Iter 19 + completed in Iter 20**
3. ~~**`v1.11.0-step9`** — Subscription UI parity~~ ✅ **SHIPPED in Iter 20**
4. **`v1.11.0-step10`** — Refund/clawback cascade + Partnership Agreement v2 with re-sign requirement — **NEXT**

### After v1.11.0
5. **Phase 6B.5** — Research moderation queue (scope PDF exists; benefits from share/cite icons being live on artifacts already)
6. **Phase 6C** — Communications (user↔partner DMs, partner↔partner DMs, ombudsman, disputes). The "Share to DM" pathway hooks the Step 8.5 share component
7. **Phase 6B.6** — "More Info" / FAQ contextual modals site-wide
8. **Advanced cross-site search & comparisons** — relies on shareable filter URLs from Step 8.5
9. **`/music`** curated mood/activation playlist library
10. **Email live mode flip** (`EMAIL_DRY_RUN=false`) once Resend DNS clears on birthright.live
11. **Tech hardening** — rate limits, Redis pub/sub for WS scaling, admin self-demotion guard, Stripe webhook signature verification audit, sponsorship tier upgrade flow, Twilio SMS check-in reminders, multi-language (en/es)

## Iteration 18 — v1.11.0 Step 6 + Step 7: Paid Research Promotion + Payouts Scaffolding (May 25, 2026)
- **Goal**: Research artifacts with tiered paid promotion + first piece of payouts infrastructure (ledger + W9 + payout method).
- **User decisions**: `/research` = general listing + Promoted top section; tiered pricing $49 brief / $149 paper / 30 days; `/partners` minimal polish (Featured strip); payouts scaffolding = ledger + W9 + Stripe Connect or encrypted ACH.
- **Backend**: research public/partner/admin endpoints; payouts partner/admin endpoints; `_PAID_HANDLERS["research_promotion"]` extends `promoted_until` on payment; new collections `research_artifacts`, `research_promotion_purchases`, `partner_w9_forms`, `partner_payout_methods`; Fernet-encrypted ACH `account_number` via `PAYOUT_ENCRYPTION_KEY`; 2 sample artifacts seeded.
- **Frontend**: `/research` page with promoted top + listing/search; `/dashboard/partner/research` CRUD + promote checkout; `/dashboard/partner/payouts` 3 tabs (Ledger / W9 / Method); `/partners` Featured strip at top; nav tightened to `xl:flex` + `gap-0.5` to fit 11 items.
- **Test coverage**: `/app/test_reports/iteration_18.json` — backend 32/32 PASS, frontend 100%. Pre-existing iter17 header overlap fixed.
- **Documentation**: `birthright-v1.11-step6-7-scope-v1.pdf` (171 KB) + refreshed `birthright-versions.pdf` (266 KB).

## Iteration 22 — Phase 6C.2 + 6C.3 Ombudsman Queue + Disputes Workflow (May 25, 2026)
- **Goal**: Close out Phase 6C (the user-protection layer) by giving the platform a formal way to file, route, and resolve conflicts between members. Sets up Step 10's clawback cascade by recording optional `financial_credit_usd` on resolutions.
- **Disputes model** (`disputes` collection):
  - id, filed_by, against_user_id, category (`payment|conduct|content|other`), title, description
  - status (`open|under_review|resolved|dismissed`), assigned_ombudsman_id
  - Optional `transaction_id` (FK to payment_transactions, validated as caller's own) + `thread_id` (FK to dm_threads, validated as participant)
  - `events[]` audit-trail (filed → assigned → status_change → resolved), `resolution` snapshot when terminal
- **REST surface**:
  - `POST /api/disputes` — file (self-dispute rejected; FK validations)
  - `GET /api/me/disputes?role=all|filed|against` — my involved disputes
  - `GET /api/me/disputes/{id}` — caller must be filer or respondent
  - `GET /api/admin/disputes` (filter status, assigned_to=me|unassigned) — admin OR `is_ombudsman=true` required
  - `POST /api/admin/disputes/{id}/assign` — target must have `is_ombudsman=true`
  - `POST /api/admin/disputes/{id}/status` — non-terminal status changes; note ≥ 3 chars
  - `POST /api/admin/disputes/{id}/resolve` — outcome (`dismissed|upheld|partial`) + resolution_note ≥ 10 chars + optional `financial_credit_usd`
- **Ombudsman queue** (Phase 6C.2):
  - `GET /api/admin/ombudsman/queue` — aggregates open + under_review disputes plus flagged DM threads from iter 21. Ombudsmen see only their assigned + unassigned; admin sees all.
  - `GET /api/admin/ombudsman/users` — list of users with `is_ombudsman=true` (powers assign dropdown).
- **Frontend**:
  - `/dashboard/disputes` MyDisputes page with type filter chips (All/Filed by me/About me) and status pills.
  - `/dashboard/disputes/{id}` DisputeDetail with timeline, linked thread/transaction, resolution block.
  - `/admin/ombudsman` OmbudsmanQueue with 3 stat cards (open / under_review / flagged_threads) and 2 lists (disputes + flagged threads).
  - `/admin/disputes/{id}` reuses DisputeDetail with `adminMode=true`, exposing Assign + Move-status + Resolve action cards.
  - `FileDisputeModal` drop-in component — wired from thread header (pre-fills thread_id + recipient) and from `/partners/{slug}` bottom link.
  - Layout user menu adds **My Disputes**; users with `is_ombudsman=true` also see **Ombudsman queue** styled with accent color.
  - Admin Dashboard gains an **Ombudsman queue** QuickActionCard.
  - `ProtectedRoute` now supports `allowOmbudsman` prop so non-admin ombudsmen can access `/admin/ombudsman` + `/admin/disputes/{id}`.
- **Models**: `DisputeCreate`, `DisputeAssign`, `DisputeStatusUpdate`, `DisputeResolution`, `DisputeStatus`, `DisputeCategory` Literals.
- **Test coverage** — `/app/backend/tests/test_iter22_disputes.py` 34/34 PASS. Full flow tested: file → invalid inputs (self, missing respondent, bad txn/thread, short title/description) → admin list → assign (rejects non-ombudsman target) → status update (rejects terminal statuses) → resolve (3 outcomes, with/without credit) → idempotency (rejects double-resolve). Ombudsman queue scoping tested for admin vs ombudsman-only visibility. No regressions in iter 17-21.
- **Iter-22 report**: `/app/test_reports/iteration_22.json` — zero issues, no retest needed.
- **Documentation**: `birthright-versions.pdf` refreshed (362 KB), `_index.md` updated.

## Iteration 21 — Phase 6C.1 Direct Messaging (May 25, 2026)
- **Goal**: User↔Partner and Partner↔Partner direct messages with privacy patterns set up for ombudsman + disputes work in later iterations.
- **User decisions locked**: 1b opt-in (per-type defaults), 2c ombudsman metadata-only by default, 3b disputes tied to transactions (deferred to 6C.2/6C.3), 4b ship DMs first.
- **Threading model**:
  - New collections `dm_threads` (participants[2], status: pending/active/blocked/archived, last_message_*, unread_<user_id>, ombudsman_flagged, ombudsman_flags[]) and `dm_messages` (thread_id, sender, content, read_by[]).
  - Eligibility: at least one participant must hold an active partner_profile.
  - Sorted canonical participant order ensures (a,b) and (b,a) return the same thread (idempotent open).
- **Opt-in flow**:
  - `PartnerProfile.accepts_new_dms` field (added to PartnerProfileUpdate model).
  - Backfill in `runtime_seed.backfill_partner_economy_fields`: facilitator+community → True, research+vendor → False (existing rows updated idempotently).
  - First message to a recipient with `accepts_new_dms=False` creates a `pending` thread. Recipient must Accept, Block, or reply (which auto-flips to active) before sender can post further messages.
- **Ombudsman privacy (2c)**:
  - Any participant can flag a thread; flag entry stored in `ombudsman_flags[]` with reason + actor + timestamp.
  - `GET /api/admin/dm/threads` always returns metadata. `last_message_preview` is masked as `[hidden — not flagged]` for non-flagged threads.
  - `GET /api/admin/dm/threads/{id}` returns `messages=null + bodies_locked=true` until flagged. When flagged, full message list returned. Admin views are audit-logged (`dm.admin_view`).
- **WebSocket**: `/api/ws/dm/{thread_id}` reuses `Connection` from `utils/ws_manager` via a new `dm_registry` singleton (so workshop chat rooms and DM rooms don't collide). Chat sends still go through REST POST for consistent ACL + accepts-gate enforcement; the REST handler broadcasts to the same WS room.
- **REST surface**:
  - `POST /api/dm/threads` — open/fetch (idempotent)
  - `GET /api/dm/threads` — inbox
  - `GET /api/dm/threads/{id}` — thread + messages
  - `POST /api/dm/threads/{id}/messages` — send
  - `POST /api/dm/threads/{id}/{accept|block|archive|flag|read}` — actions
  - `GET/PUT /api/me/dm/preferences` — toggle accepts_new_dms across all my active partner profiles
  - `GET /api/admin/dm/threads[?flagged_only=true]` — admin metadata-only inbox
  - `GET /api/admin/dm/threads/{id}` — bodies only when flagged
- **Frontend**:
  - `/dashboard/messages` Messages inbox (avatar, partner_type label, status badges, unread badges, last_message_preview).
  - `/dashboard/messages/{thread_id}` MessageThread with realtime WS, bubble-style message list, composer (Enter/Shift+Enter), Accept/Block/Archive/Flag actions, and pending-state banners.
  - `MessageButton` component placed on partner profile pages, facilitator profiles, governance board cards (with user_id), partner directory cards. Hidden when viewing your own profile.
  - **ShareButton 'To a partner' channel** — clicking opens a popover listing active+pending partner-typed threads; selecting one POSTs the share URL into that thread.
  - PartnerDashboard gets a `DmPreferencesCard` with single-button toggle ("Pause new DMs" ↔ "Accept new DMs").
  - Layout user menu adds **Messages** + **My Bookmarks** links.
- **Models**: `DmThreadCreate`, `DmMessageCreate`, `DmThreadFlag`, `DmAcceptsToggle`, `DmThreadStatus` Literal.
- **Test coverage** — `/app/backend/tests/test_iter21_dm.py` 23/23 PASS. All REST + WS endpoints verified. Per-type defaults verified. Pending → Accept transitions verified. Admin metadata-only + bodies-on-flag verified. No regressions in iter 17-20 suites.
- **Iter-21 report**: `/app/test_reports/iteration_21.json` — zero issues, no retest needed, no action items.
- **Documentation**: `birthright-versions.pdf` refreshed (361 KB), `_index.md` updated.

## Iteration 20 — v1.11.0 Step 9 + Universal Share Placement Audit (May 25, 2026)
- **Goal**: Two combined deliverables. (A) Close out the universal Share/Print/Download coverage user demanded — every public-facing surface (cards + details) gets a ShareButton, plus universal Print and Download QR PNG channels. (B) v1.11.0 Step 9 — Subscription UI parity: partner cancel/change + admin revoke/refund.
- **Step 9 — Subscription UI Parity**:
  - **Partner-side cancel** — `POST /api/subscriptions/{id}/cancel`. Non-destructive: license stays active until `expires_at`; status flips to `cancelled`; optional reason recorded for retention insight.
  - **Mid-flight plan change** — `GET /api/subscriptions/{id}/change-preview?new_plan_id=X` returns prorated math; `POST /api/subscriptions/{id}/change-plan` either (a) fulfills synthetically with no Stripe call when credit ≥ new price (free upgrade), or (b) opens a Stripe checkout for the delta. Webhook handler now respects `supersedes_subscription_id` and marks the predecessor `superseded`.
  - **Admin panel** — `GET /api/admin/subscriptions` (filter by status/partner_type) + `POST /api/admin/subscriptions/{id}/revoke` (reason ≥ 3 chars required, optional Stripe refund). Status pills: active / cancelling / superseded / expired / revoked.
  - Frontend: `SubscriptionStatusCard` extended with **Manage** button → opens panel with Change plan + Cancel renewal flows. New `/admin/subscriptions` page (table + filter chips + revoke modal). Admin Dashboard gains Subscriptions QuickAction.
- **Universal Share/Print/Download placement audit**:
  - `ShareButton` now also on: **partner directory cards** (non-sample), **governance board member cards**, **join-us list cards**, **workshops list cards**, **shop product cards** (non-material), **facilitators list + detail**, in addition to the iter-19 placements.
  - `ShareButton` gained **Print** (window.print, paired with @media print CSS in App.css that hides nav/footer/share menu) and **Download QR PNG** (rasterizes the hidden SVG to a 4× canvas PNG so first click always works).
  - `stopPropagation` prop on `ShareButton` for cases where it sits inside a clickable card.
  - Workshops list converted from `<Link>` cards to `role="link"` divs with `useNavigate` so ShareButton can stop click propagation.
- **Models**: `SubscriptionCancelRequest`, `SubscriptionPlanChangeRequest`, `AdminSubscriptionRevokeRequest`.
- **Test coverage** — `/app/backend/tests/test_iter20_subs_step9.py` 16/16 PASS. ShareButton placement verified across all listed surfaces (partners=3, governance=4, join-us=3, workshops=3, shop=56 card+detail buttons, facilitators, research). No regressions. Zero issues in `/app/test_reports/iteration_20.json`.
- **Documentation**: `birthright-versions.pdf` refreshed (340 KB), `_index.md` updated.

## Iteration 19 — v1.11.0 Step 8 + Step 8.5: Disbursement Orchestration + Universal Share & Save System (May 25, 2026)
- **Goal**: Close the loop on partner financial operations (admin can run real disbursements with a CSV export gated to W9+method on file) AND launch the universal share/save flywheel that ties social sharing to community-partner referral attribution.
- **Step 8 — Disbursement Orchestration**:
  - Foundation-wide schedule stored in `foundation_settings.disbursement_settings` (next_disbursement_date, cadence, notes). Admin endpoints: `GET/PUT /api/admin/payouts/disbursement-settings`.
  - `GET /api/admin/payouts/ready-to-pay[?format=json|csv]` — partitions earned credits into `ready` (W9 + payout method on file) vs `blocked` with reason. CSV streams only the ready set.
  - `POST /api/admin/payouts/credits/{id}/mark-paid` now fires `disbursement_notification` email to the partner (best-effort, dry-run queues to `db.outbound_emails`).
  - Partner-side `/api/me/payouts` now returns `next_disbursement_date`, `cadence`, `ready_for_payout`, `w9_on_file`, `method_on_file`. `GET /api/me/payouts/next-disbursement` exposes just the schedule.
  - `AdminPayouts.jsx` extended with disbursement-settings card + ready-to-pay tables + CSV export button.
  - `PartnerPayouts.jsx` Ledger tab shows next-disbursement callout + ready/blocked chip.
- **Step 8.5 — Universal Share & Save System**:
  - New router `routers/shares.py`:
    - `POST /api/shares/log` — anon-friendly. When `via` matches an active community-partner referral_code, sets `birthright_ref` cookie for downstream checkout attribution.
    - `GET /api/me/share-token` — community partner → referral_code (pays_out:true); else user_id (pays_out:false).
    - `GET/POST/DELETE /api/me/bookmarks` — polymorphic on subject_type (workshop, product, research, partner, facilitator, foundation_role, proposal, impact_statement). Idempotent create per (user, subject_type, subject_id).
  - `GET /api/research/{id}/cite?format=apa7|bibtex` — best-effort citation builder for the freeform `authors` field.
  - `GET /api/workshops/{id}/ics` — public .ics download (already had calendar_qr utility).
  - New email template `disbursement_notification`.
  - New frontend component `components/ShareButton.jsx` — drop-in menu with Copy/Native share/Email/SMS/QR/Bookmark/Calendar/Cite icons, context-narrowed by `surface` prop. Uses `qrcode.react` for client-side QR.
  - `lib/shareUtils.js` — token resolution (cached in sessionStorage), URL building, log + inbound `?via=` capture.
  - `pages/Bookmarks.jsx` at `/dashboard/bookmarks` — type-filtered list with Open/Remove actions.
  - Share buttons placed on: workshop detail, product detail (non-material only), /research artifact cards, partner profile pages (non-sample only), join-us role detail.
  - Inbound capture in `App.js` — `captureInboundVia()` on mount strips `?via=` from URL and logs the landing event (sets cookie if applicable).
- **Privacy matrix respected**: no share affordances on workshop materials, ledger rows, W9 form, payout methods, admin dashboards, sample partner profiles.
- **Models**: `BookmarkCreate`, `ShareLogCreate`, `DisbursementSettings`, plus `BookmarkableType`/`ShareSurface`/`ShareChannel` Literals.
- **Bumped to `v1.11.0`** (FastAPI `app.version` + `/api/` root).
- **Test coverage** — `/app/backend/tests/test_iter19_disbursement_shares.py` 23/23 PASS. Frontend smoke verified all share surfaces + bookmarks page + admin disbursement UI + partner ledger callout. Inbound `?via=` capture verified (cookie set, URL stripped). Pre-existing iter17/18 suites 51 passed.
- **Iter-19 report**: `/app/test_reports/iteration_19.json` — zero critical/minor backend issues, zero integration issues, no action items, retest_needed: false.
- **Documentation refreshed**:
  - `birthright-versions.pdf` (282 KB) — version index now includes iter 19 / step 8+8.5
  - `_index.md` updated
- **Goal**: Research artifacts with tiered paid promotion + first piece of payouts infrastructure (ledger + W9 + payout method)
- **User decisions**:
  - `/research` = general listing + Promoted top section (both)
  - Artifact metadata = full set (title/authors/abstract/date/url/DOI/cover + categories[] + tags[] + read time)
  - Pricing = tiered: **$49 brief / $149 peer-reviewed paper / 30 days** (admin can override tier per-artifact)
  - `/partners` = minimal polish — Featured strip at top, no tab restructure
  - Payouts scaffolding = full: ledger + W9 + payout method (Stripe Connect OR encrypted ACH)
- **New backend endpoints**:
  - Research public: `GET /api/research[?q=&category=]`, `GET /api/research/promoted`, `GET /api/research/{id}`, `GET /api/research/pricing`
  - Research partner (auth): `GET/POST /api/me/research`, `PUT/DELETE /api/me/research/{id}`, `POST /api/me/research/{id}/promote/checkout`
  - Research admin: `GET /api/admin/research`, `PUT /api/admin/research/{id}/tier`, `POST /api/admin/research/{id}/promote/grant`, `POST /api/admin/research/{id}/promote/revoke`
  - Payouts partner (auth): `GET /api/me/payouts`, `GET/PUT /api/me/payouts/w9`, `GET/PUT /api/me/payouts/method`
  - Payouts admin: `GET /api/admin/payouts/credits`, `POST /api/admin/payouts/credits/{id}/mark-paid?source=...`, `GET /api/admin/payouts/w9/{user_id}` (audit-logged)
- **Stripe fulfillment**: `_PAID_HANDLERS["research_promotion"] = activate_research_promotion` — extends or sets `promoted_until = now + 30 days`, writes `research_promotion_purchases` audit row
- **New collections**: `research_artifacts`, `research_promotion_purchases`, `partner_w9_forms`, `partner_payout_methods`. New env var: `PAYOUT_ENCRYPTION_KEY` (Fernet)
- **Encryption**: ACH account_number is Fernet-encrypted at rest with a per-deployment key. Only last4 visible on GET. TIN is plain-text in DB but masked on partner-side GET; admin view audit-logged
- **Sample data**: 2 published research artifacts seeded (1 brief by Daniel Brookes, 1 paper by Imani Okafor with DOI) so `/research` has demo content from day one
- **Frontend new pages**:
  - `/research` — promoted top section + general listing with search, tier icons, read-time, tags, DOI, "Read full text" external link
  - `/dashboard/partner/research` — CRUD modal for artifacts, status pills, "Promote $X" button (tier-priced), tier-select on new (drop on edit)
  - `/dashboard/partner/payouts` — 3 tabs (Ledger / W9 form / Payout method)
- **Frontend updates**:
  - `/partners` directory got a Featured strip at top (auto-hidden in samples mode), "See all featured" link
  - PartnerDashboard now shows 3 new tiles (Featured slot, Research artifacts, Payouts) gated to relevant partner_type/profile state
  - Nav: "Research" link added between Featured and Join Us; nav layout tightened to `xl:flex` (was `lg:flex`) and `gap-0.5` (was `gap-1`) so the now-11-item nav fits 1280px+ without overlap
- **Test coverage** — `/app/test_reports/iteration_18.json`. Backend 32/32 PASS, frontend 100%. One pre-existing cosmetic flag from iter 17 (header logo/nav overlap) fixed alongside this iteration
- **Documentation refreshed**:
  - `birthright-v1.11-step6-7-scope-v1.pdf` (171 KB) — iter 18 scope doc (new)
  - `birthright-versions.pdf` (266 KB) — version index now includes iter 18

## Iteration 17 — v1.11.0 Step 4 + Step 5: Featured Showcase + Founding Partner Gating (May 25, 2026)
- **Goal**: Self-serve featured slots (revenue + visibility) and a public Founding-Partner program with a visible cap.
- **User decisions**:
  - Featured = **self-serve paid at $99 / 30 days flat**, Stripe checkout, admin can revoke or comp
  - Featured sort = **random shuffle** on every page load (no auction)
  - Founding Partner = **public CTA + visible "X/cap" counter** on `/partners/apply`; default cap = 50; locked rate for 5 years on approval
- **New backend endpoints**:
  - Featured public: `GET /api/featured`, `GET /api/featured/pricing`
  - Featured partner (auth): `GET /api/me/featured?partner_type=...`, `PUT /api/me/featured?partner_type=...`, `POST /api/me/featured/checkout`
  - Featured admin: `POST /api/admin/featured/{profile_id}/grant`, `POST /api/admin/featured/{profile_id}/revoke[?reason=]`, `GET /api/admin/featured[?include_expired=true]`
  - Founding public: `GET /api/founding-partners/stats` → `{cap, taken, available, is_open}`
  - Founding admin: `PUT /api/admin/founding-partners/cap`, `POST /api/admin/founding-partners/{profile_id}/grant`, `POST /api/admin/founding-partners/{profile_id}/revoke`
- **Stripe fulfillment**: `_PAID_HANDLERS["featured_slot"] = activate_featured_from_txn` extends `featured_until` by `duration_days` (preserving any remaining time if already featured) and writes a `featured_slot_purchases` audit row. Content captured in checkout payload is applied to the profile on payment success.
- **Approval auto-grant**: When admin approves a partner application that has `apply_as_founding_partner=true`, the profile flag flips to `is_founding_partner=True` with `founding_rate_expires_at = now + 5y` — but only if `_taken_count < cap`. Otherwise approval still succeeds without the flag; response includes `founding_granted: bool`.
- **New collections**: `featured_slot_purchases`. New fields on `partner_profiles`: `featured_revoke_reason`. New field on `foundation_settings`: keys `featured_pricing` and `founding_partner_cap`.
- **Frontend**:
  - `/featured` — public showcase with random shuffle, sparkle-styled cards, mission-alignment block, signature content, video link, image gallery (up to 3), custom CTA
  - `/partners` directory — gold Featured ribbon (with `ring-2 ring-[#C9A961]` border), gold Sample ribbon, green ★ Founding ribbon. Cards now use a `role="link"` div instead of `<Link>` to avoid nested-anchor warnings while keeping inner outbound `<a>` clickable
  - `/partners/<slug>` — Featured + Founding badges next to the partner name
  - `/partners/apply` — Founding-Partner opt-in section with cap progress bar; "all seats filled" lockout when full
  - `/dashboard/partner/featured` — buy/extend slot card + editable content form (tabs if multiple partner types); sample partners blocked server-side
  - `/admin/featured` — founding stats card with cap-update control, active featured slots list with revoke, "Grant comped slot" modal taking profile_id + days + mission
  - `/admin/partners` application card now shows "★ Applicant requested Founding Partner" banner when set
  - Nav: "Featured" added between Partners and Join Us; partner-dashboard tile linking to featured slot management
- **Test coverage** — `/app/test_reports/iteration_17.json`. Backend 20/20 PASS (2 documented skips for paths requiring fresh fixtures); frontend 100% after fixing two issues flagged by the testing agent:
  1. Founding badge now appears on sample personas (gated incorrectly before)
  2. Nested `<a>` warning eliminated by converting `PartnerCard` wrapper to a `role="link"` div
- **PDF index refreshed**: `birthright-versions.pdf` (256 KB) now lists iter-15/16/17 as shipped with steps 6+7 in progress.

## Iteration 16 — v1.11.0 Step 2 + Step 3: Outbound Attribution + Off-Site Sales Reconciliation (May 25, 2026)
- **Goal**: Capture revenue when users click through to a partner's external site, and let partners self-report off-site sales for credit.
- **User decisions before build**:
  - Outbound link visible on partner cards + detail pages, **only for vendor + community partner types**
  - Self-reporting cadence: **free-form date range with monthly defaults** (1st → last day of current month pre-populated)
  - Approval credits partner at `rev_share_overrides.off_site_pct` if set, else `resolve_rev_share` fallback (active subscription → global default)
  - Webhook uses **HMAC SHA-256** signing with per-partner secret in `X-Birthright-Signature: sha256=<hex>` header (standard Stripe/GitHub/Shopify pattern)
- **Backend new endpoints**:
  - Outbound: `GET /api/out/{slug}` (302 redirect + log click with UTM/referrer/IP/UA), `GET /api/admin/outbound-clicks`, `GET /api/admin/outbound-clicks/summary`
  - Partner sales (auth): `POST /api/partner-sales-reports?partner_type=...`, `GET /api/partner-sales-reports/my`, `GET /api/partner-sales-reports/my/webhook?partner_type=...`, `POST /api/partner-sales-reports/my/webhook/regenerate?partner_type=...`
  - Admin: `GET /api/admin/partner-sales-reports?status=...`, `POST /api/admin/partner-sales-reports/{id}/decision?status=approve|dispute|revise`
  - Webhook (public, HMAC-signed): `POST /api/webhooks/partner-sales/{slug}`
- **New collections**: `outbound_clicks`, `partner_sales_reports`, `partner_off_site_credits`. New field on `partner_profiles`: `webhook_secret` (lazily minted on first webhook-info request).
- **Approval logic**: `_approve_report()` resolves off_site_pct via `resolve_off_site_pct()` (`rev_share_overrides.off_site_pct` → active subscription pct → global default), computes payout, writes a `partner_off_site_credits` row with `source_type='off_site_sales_report'`, status='earned'. Admin can override gross or pct at approval time. Disputed and revised statuses don't credit. Approved/disputed are terminal.
- **Outbound redirect safety**: `dest` query param honored ONLY if it shares the host of partner's `external_site_url` (prevents open-redirect abuse). Falls back to `/partners/<slug>` when no external URL is set. Unknown slug → `/partners`. Sample partners log clicks with `is_sample: true` for filtering analytics.
- **HMAC signature flow**: Secret is `secrets.token_hex(32)` (64-char). Verified with `hmac.compare_digest` (constant-time). Partner can rotate anytime; old signatures immediately invalidated.
- **Frontend**:
  - Partner cards (`PartnersDirectory.jsx`) + detail (`PartnerProfilePage.jsx`) render outbound link **only for vendor + community** partner types; other types use plain `website_url` anchor
  - `/dashboard/partner/sales-reports` — listing, monthly-defaulted submit modal, webhook card with hidden/reveal/copy/rotate
  - `/admin/partner-sales-reports` — status tabs (submitted/approved/disputed/revised), detail modal with override fields, approve/revise/dispute actions
  - Quick-action tiles added on `PartnerDashboard` (vendor+community only) and `AdminDashboard`
- **Test coverage** — `/app/backend/tests/test_iter16_outbound_sales.py` 25/25 PASS. Full frontend flow verified (card gating, sales-reports UI end-to-end, webhook info reveal/rotate, admin decision actions, terminal-state guard).
- **Iter-16 report**: `/app/test_reports/iteration_16.json` — backend 100% (25/25), frontend 100%, zero defects.

## Iteration 15 — Phase 6B.4.5b + 6B.4.5c "Join Us" + Sample Partner Profiles (May 24, 2026)
- **Goal**: Sales-tool readiness for upcoming founding-partner outreach. Two related additions, one UI pass.
- **Scope PDF**: `/app/backend/static/exports/birthright-join-us-scope-v1.pdf` (approved by user before build).
- **3 open foundation roles** (all equity-in-mission, no compensation amounts shown) seeded idempotently at startup, linked to existing governing_members via `seeded_member_id`:
  - `board-chair-cofounder` → Dr. Aurelia Mendez
  - `research-advisor` → Dr. Hannah Lin
  - `director-community-stewardship` → Reverend Tomas Ifeanyi
  (James Reagan / Executive Director left without SAMPLE ribbon — not on the recruit-now list.)
- **8 sample partner profiles** (2 per partner type, `is_sample: true`, `user_id: null`) hidden from default `/partners` listing and surfaced only via `/partners?samples=1`:
  - Facilitators: sample-maya-chen (founding), sample-aaron-kalu
  - Vendors: sample-quiet-hours-studio (founding), sample-hearth-practice
  - Community: sample-pat-lindholm (founding), sample-liz-okonkwo
  - Research: sample-imani-okafor (founding), sample-daniel-brookes
- **Backend**: new `routers/foundation_roles.py` with 4 sub-routers (public list/detail, public application submission, admin CRUD, admin applications queue). `runtime_seed.py` extended with `ensure_foundation_roles_seeded` + `ensure_sample_partners_seeded`. `routers/partners.py` `list_public_partners` updated to support `samples=0|1` query param (default excludes samples).
- **New models**: `FoundationRoleCreate`, `FoundationRoleUpdate`, `FoundationRole`, `FoundationRoleApplicationSubmit`, `FoundationRoleApplicationDecision`.
- **New API endpoints**:
  - Public: `GET /api/foundation-roles[?open_only=true]`, `GET /api/foundation-roles/{slug}`
  - Public (no auth): `POST /api/foundation-role-applications`
  - Admin: `GET/POST /api/admin/foundation-roles`, `PUT/DELETE /api/admin/foundation-roles/{slug}`, `GET /api/admin/foundation-role-applications`, `POST /api/admin/foundation-role-applications/{app_id}/decision?status=…`
- **Partner directory update**: `GET /api/partners` defaults to non-samples; `GET /api/partners?samples=1` returns ONLY the 8 sample profiles.
- **Frontend pages**: `/join-us` (lists roles), `/join-us/:slug` (detail + apply form with thank-you screen), `/admin/foundation-roles` (CRUD), `/admin/foundation-applications` (6-status triage queue with applicant detail modal). Layout nav + footer updated with "Join Us" link.
- **Governance page**: shows open-seats banner when ≥1 role is open; cards belonging to the 3 currently-recruited seats get a gold SAMPLE ribbon, opacity-reduced photo, italic "We're looking for someone like this:" framing on the bio, and an "Apply for this role →" CTA targeting `/join-us/{slug}`.
- **Partners directory**: gold "View sample profiles" pill + URL-state `?samples=1` toggle; sample mode shows gold SAMPLE ribbons on every card and a banner explaining what samples are. Sample partner detail pages (`/partners/sample-*`) render a sample banner with "Apply to become a partner" CTA.
- **Best-effort confirmation email** on application submit (uses existing dry-run mailer; never blocks the response).
- **Test coverage** — `/app/backend/tests/test_iter15_foundation_roles.py` 21/21 PASS; full frontend flow verified (list, detail, application submission, governance ribbons + open-seats banner, partners samples toggle, sample detail banner, admin roles CRUD UI, admin apps queue with submitted test app visible).
- **Iter-15 report**: `/app/test_reports/iteration_15.json` — backend 100% (21/21), frontend 100%, zero defects.

## Iteration 12+13 — Phase 6B.4 Vendor Autonomous Catalog (May 2026)
- **Design decisions** (per user): vendors set prices freely; auto-publish; admin can flag/unpublish anytime; print-on-demand assumption (no inventory tracking); products clearly identify their vendor on the storefront. Cross-vendor sort/filter for the public store was DEFERRED to advanced search backlog.
- **Models extended** (`models.py`) — `ProductCreate` gained `is_vendor_product`, `vendor_partner_id`, `vendor_user_id`, `vendor_name`, `vendor_slug`, `moderation_status` (active|flagged|unpublished), `moderation_note`. New `VendorProductCreate`/`VendorProductUpdate`/`VendorModerationAction` request models.
- **`routers/vendor_catalog.py`** — Vendor self-serve: `GET/POST /api/vendor/products`, `PUT/DELETE /api/vendor/products/{id}` (gated by active vendor `PartnerProfile`; 400 on delete if any paid orders reference the product; 400 on edit if product is unpublished). Admin moderation: `GET /api/admin/vendor-products?status=&vendor_user_id=`, `POST .../flag` + `/unflag` + `/unpublish` + `/restore`. All write actions audit-logged. `vendor_name` snapshots from `profile.meta.business_name` (fallback `display_name`) at create time.
- **`routers/products.py`** — Public listing (`GET /api/products`) HIDES vendor products where `moderation_status != active`. Foundation products (no `is_vendor_product`) are unaffected. `GET /api/products/{id}` 404s flagged/unpublished vendor products for the public but admin + owner can still see. Added `?vendor_id=` filter.
- **Frontend pages** — `/dashboard/vendor/products` (vendor CRUD w/ live/flagged/unpublished filters, drawer-based create/edit, delete confirm, status badges, admin moderation notes shown to vendor); `/admin/vendor-products` (cross-vendor moderation table with Flag/Unflag/Unpublish/Restore actions, status tabs, search). Public Shop ProductCard + ProductDetail show "By <vendor_name>" badge linking to `/partners/<slug>`.
- **UX gating** — `/dashboard/vendor/products` pre-checks `/api/partners/my-profiles` and renders the `vendor-access-denied` empty state with Apply CTA for users without an active vendor profile (fix from iter12→iter13).
- **AdminDashboard quick-actions** updated: Vendor catalog, Partner payouts, Foundation reports cards added.
- **Bumped to `v1.10.0`.** Iter-12 backend **22/22 PASS**, iter-13 frontend retest **100% PASS** (`/app/test_reports/iteration_12.json` + `/app/test_reports/iteration_13.json`). Zero outstanding defects.

## Phase 6C.4 — AI Wallet + AI Research Collaborator + Vendor PDM AI (May 25, 2026)
- **Metering & wallet** (`utils/ai_billing.py`, `routers/ai_wallet.py`): per-model price table (Claude Sonnet 4.5 = $3/$15 per MTok, Nano Banana = $0.04/image). Per-call cost compute, partner wallet with balance + lifetime topup + lifetime spend, Stripe one-time top-ups ($10/$25/$50/$100), opt-in auto-recharge, admin grant + usage report, idempotent crediting via `ref` field. Webhook integration in `routers/checkout.py` dispatches `ai_wallet_topup` to credit the wallet on payment success.
- **AI Research Collaborator** (`routers/research_ai.py` at `/api/research-collab/*` — repositioned as peer-level collaborator, not secretary, per founder direction): 7 capabilities in 2 groups. **Inquiry**: `synthesize-literature` (brief/standard/deep markdown synthesis), `map-landscape` (structured JSON of key concepts/seminal authors/modern voices/debates/shifts/adjacent fields), `generate-questions` (tractable research questions for a small nonprofit lab, with feasibility ratings), `critique-methodology` (markdown critique with strengths/gaps/confounds/robustness checks). **Drafting**: `summarize-notes`, `suggest-tags`, `polish-draft`. System prompts include a `COLLAB_PREAMBLE` that explicitly establishes peer relationship and forbids fabricated citations.
- **Vendor PDM AI** (`routers/vendor_ai.py` at `/api/vendor-ai/*`): `write-description`, `suggest-price`, `marketing-blurb`, `generate-image` (Nano Banana via emergentintegrations Gemini SDK; saves PNG to `/app/backend/static/products/`).
- **Concierge metering**: balance gate + usage debit only for `role in (partner, facilitator)` — participants & anonymous visitors remain foundation-funded.
- **Replay last conversation**: `GET /api/assistant/my-sessions/last` + new History icon button on the Concierge panel header (`data-testid=assistant-replay-btn`) for signed-in users.
- **Admin usage report**: `/admin/ai-usage` page (data-testid=admin-ai-usage-page) — totals + per-user × feature breakdown + wallets table + day-window chips (7/30/90/365).
- **Frontend surfaces**: new pages `/dashboard/ai-wallet` (data-testid=ai-wallet-page) + `/admin/ai-usage`; new drawer components `ResearchAIPanel` (titled "AI Research Collaborator", 7 tabs in 2 groups) and `VendorPDMPanel` (4 tabs); "AI Wallet" link in user menu; "Research Collaborator" button on PartnerResearch; "Product AI" button on VendorProducts.
- **Test coverage**: backend `test_iter27_ai_billing.py` 23/23 PASS (live Claude calls for synthesize-literature and write-description included); frontend iter-27 ~85% PASS after testing agent fixed two critical lucide-react import bugs (`History`, `ImageIcon`); live UI screenshot post-fix confirms the panel renders correctly with scholar-grade markdown output anchored to real research (Verrier, Rutter, Dozier, Juffer & van IJzendoorn, Zeanah, Brodzinsky).

## Phase 6B.6 — AI Concierge (Agentic Site-Wide Guide) (May 25, 2026)
- **Decision pivot**: the originally-planned static FAQ modal feature was cancelled mid-build at user request and replaced with a full agentic AI Concierge powered by Claude Sonnet 4.5 (via Emergent LLM Key).
- **Backend** `routers/assistant.py` (~530 lines):
  - `POST /api/assistant/chat` — accepts `{session_id, message, page_context}`, streams a Claude reply, parses `<<ACTION>>{...json}<<END>>` blocks the LLM emits, returns clean reply text + structured `proposed_actions[]`. Persists conversation in `db.assistant_messages`.
  - `POST /api/assistant/execute` — runs an approved action. Backend tier-`auto` actions (search_workshops, search_products, search_partners, search_research, lookup_my_subscriptions, lookup_my_registrations) execute server-side; tier-`auto` frontend-execute actions (navigate, scroll_to, prefill_form, open_modal, add_to_cart, register_for_workshop) return a directive the frontend runs; tier-`confirm` write actions (send_dm, file_dispute, submit_research_draft, submit_partner_application, cancel_my_subscription, sign_agreement, bookmark) run only after the user clicks the yellow Confirm card.
  - Forbidden tier (checkout_payment, change_user_role, delete_account) → 403 at execute time regardless of LLM intent.
  - `GET /api/assistant/meta` exposes the action registry to the frontend.
  - `GET /api/assistant/sessions/{id}` + `GET /api/assistant/my-sessions` for history.
  - Every action execution audit-logged in `db.assistant_audit` + `db.audit_log`.
- **System prompt** embeds the full site map, the current user's role/sign-in state, the current page path, and the structured action protocol. Replays prior user turns into `LlmChat` for multi-turn memory.
- **Frontend** `components/AssistantWidget.jsx`:
  - Floating "Ask Birthright" pill bottom-right of every page (positioned `bottom-20 right-5` to clear the Emergent badge). Also opens on `/` keyboard press (anywhere except inside an input/textarea). Esc closes.
  - Slide-in panel with chat history, action confirm cards, decline-state UI, system success/error messages.
  - Auto-runs tier=`auto` actions immediately, renders yellow confirm card for tier=`confirm` actions.
  - Persists `session_id` and `open` state in localStorage.
- **Test Plan PDF**: `/app/scripts/build_test_plan.py` generates `birthright-test-plan.pdf` (775 KB) into `/app/backend/static/exports/`. Eleven independent test suites (A Auth · B Storefront · C Workshops · D Comms · E Partners/Subs · F Vendor/Refs/Reports · G Research · H Admin · I Governance · J Mobile · K AI Concierge full agentic coverage) with assignment sheet, env URLs, Stripe test cards, full data-testid index, and manual + Assistant test paths for every flow.
- **Test coverage**: backend `test_iter26_assistant.py` 9/9 PASS (2 of which make live Claude calls); frontend iter-26 100% PASS (navigate, search, refused-forbidden, multi-turn memory, confirm-card render+decline, error-stringification, session persistence, PDF download all verified).

## Phase 6B.5 — Research Submissions Queue + Admin Moderation (May 25, 2026)
- **Moderation gate**: partners can save a research artifact as `draft` OR submit it for review, but the `published`/`archived` statuses are now reachable only via admin moderation. Existing partner PUT on a published artifact's content fields auto-requeues it to `pending_review`.
- **New statuses** on `ResearchArtifactStatus`: `pending_review`, `changes_requested`, `rejected`. New stored fields: `moderation_note`, `moderated_by`, `moderated_at`, `submitted_at`.
- **Endpoints** (admin-only): `POST /api/admin/research/{id}/approve`, `.../request-changes` (note required), `.../reject` (note required). Partner: `POST /api/me/research/{id}/submit-for-review`.
- **Frontend**: new `/admin/research` queue with 5 status tabs (Pending review, Changes requested, Rejected, Published, Drafts), action buttons per row, moderation modal w/ note textarea; PartnerResearch page updated to (a) restrict the form's status dropdown to "Save as draft" / "Submit for review", (b) display the admin's `moderation_note` block when status is `changes_requested` or `rejected`, (c) expose a "Submit for review" button on rows that can be re-submitted. Admin Dashboard gains a "Research moderation" QuickActionCard.
- **Test coverage**: backend `test_iter25_research_moderation.py` 8/8 PASS; frontend iter-25 36/36 UI assertions PASS.

## Mobile Menu — EXPLORE / FOUNDATION Tab Reorganization (May 25, 2026)
- Mobile drawer (xl-and-below) now renders TWO grouped sections matching the existing footer grouping per the user-supplied screenshot. Gold-uppercase section labels. `Layout.jsx` exports `NAV_EXPLORE` and `NAV_FOUNDATION` and the desktop horizontal nav still consumes the flattened list. Section testids: `mobile-section-explore`, `mobile-section-foundation`. Individual link testids: `mobile-nav-{slug}` (unchanged).

## v1.11.0 Step 10 — Refund/Clawback Cascade + Agreement v2 (May 25, 2026)
- **Refund cascade engine** (`utils/refund_cascade.py`): given a `payment_transactions.id`, refunds the Stripe charge AND undoes all side-effects of the original payment (registrations, subscriptions, featured slots, promotions). Reverses derived partner credits in `user_credit_ledger`; already-paid credits are queued in `paid_credit_clawbacks` (status `pending_recovery`) for admin to resolve as recovered/written-off.
- **Endpoints**: `POST /api/admin/refunds` (admin-only, requires `{txn_id, reason, skip_stripe?}`), `GET /api/admin/refunds`, `GET /api/admin/clawbacks`, `POST /api/admin/clawbacks/{id}/resolve` (`{status: recovered|written_off, note}`). All actions audit-logged.
- **Agreement v2 gate** (`utils/agreement_gate.py`): `require_active_agreement` dependency on sensitive partner routes — `POST /api/dm/threads`, `POST /api/disputes`, `POST /api/subscriptions/checkout`. Blocks with 412 until partner signs the active version. Endpoints: `GET /api/legal/indemnification/active`, `GET /api/legal/indemnification/my-status`, `POST /api/legal/indemnification/sign`.
- **Frontend**: `/admin/refunds` (cascades table + pending-clawbacks list + "Fire refund cascade" modal + "Resolve clawback" modal); `/legal/agreement` (full body, summary-of-changes card, accept button or already-signed badge); top-of-layout `AgreementResignBanner` for users with unsigned active version (dismissable via localStorage). Admin Dashboard gains a "Refunds & Clawbacks" QuickActionCard (RotateCcw icon).
- **Test coverage**: backend iter-23 57/57 PASS (`test_iter23_refunds_agreement.py`); frontend iter-24 15/15 testable flows PASS (1 not-testable due to empty pending-clawbacks DB state — acceptable empty-state).

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

## v1.11.x — AI Wallet Error Polish (May 2026)
- **AiWallet.jsx** now distinguishes `404` (backend missing — typical of a lagging production deploy), `401/403` (session expired), and generic load failures. Each renders a dedicated error card with a contextual action: Retry, "Sign in again" (links to `/login`), or a link to `/ai` to learn about AI tools.
- Removes the generic "Could not load AI wallet" toast that previously hid the underlying cause from end users.
- Verified happy-path render in preview (admin@birthright.org logged in, balance $50.00 displays correctly).
- **User action required**: To resolve the production wallet error on `birthright.live`, click "Save to GitHub" and redeploy so the AI Wallet routers ship to prod.


## Test credentials

## v1.12.x — Experiences IA Consolidation + Mobile Sign-in (May 2026)
- **New `/experiences` page** combining old Workshops + Education tabs.
  - **Hero**: "A practice, not a curriculum" — pulls `education_structure` foundation copy.
  - **Section 1 — Foundation library**: three-tier framework (Foundations / Practice / Living the Work) as the lead. Each tier card shows tagged foundation workshops; empty tiers show "in development" copy.
  - **Foundation IP teaser**: "Seven Conversations in a Day" placeholder card in the Foundations tier until the workshop is created via the admin UI (one-day couples workshop, distilled from research-backed material; AI-assisted prompts; intentionally unbranded vs. external IP).
  - **Section 2 — Community workshops**: all non-Foundation workshops (status filter + search) using the existing WorkshopCard.
- **Workshop schema**: added optional `track` (`foundations|practice|living_the_work`) and `is_foundation` (bool, default False) to `WorkshopCreate`, `Workshop`, `WorkshopUpdate`.
- **Admin Workshop form**: new "Foundation library tagging" panel with `is_foundation` checkbox + tier select (disabled until checkbox is on).
- **Routes**: `/workshops` and `/education` now redirect to `/experiences`. `/workshops/:slug` detail page is unchanged. Removed "Workshops" and "Education" nav items; added single "Experiences" item.
- **Mobile sign-in**: `Sign in` link is now always visible in the header (was previously hidden behind the hamburger on screens below 640px). `Join` button still hides on mobile to preserve room for the brand mark + cart + hamburger.
- **Files**: new `/app/frontend/src/pages/Experiences.jsx`; edits to `App.js`, `Layout.jsx`, `WorkshopFormDrawer.jsx`, `models.py`.
- **Verified**: `/experiences` renders cleanly desktop + mobile; tier teaser + 3 existing workshops appear in the right buckets; both redirects work; mobile menu lists "Experiences" only; mobile Sign in tappable at top-right (46x48 hit area).

See `/app/memory/test_credentials.md`
