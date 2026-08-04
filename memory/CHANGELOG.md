# Birthright Changelog

Day- and time-stamped record of releases and hotfixes. New entries go at the
TOP. Use UTC; localize only when a release is timed to a specific timezone.

## 2026-02-04 — Domain migration · @birthright.org → @birthright.live
- **All seeded credential accounts moved** to the live domain:
  admin, demo, elena, marcus, counsel.
- **Sources updated**: `seed_data.py`, `utils/readonly_admin.py`
  (COUNSEL_EMAIL default), plus test fixtures across every counsel
  test suite. Test file `test_iter45_domain_migration.py` kept the
  `.org` addresses in its "should-401" list to guard against
  regressions.
- **Mongo migrated** in place — no dupes created (existence-check
  before renaming each account); old `.org` logins now correctly 401.
- **Content updates**: `memory/test_credentials.md`, counsel guide
  (`00a-counsel-user-guide.md` + rebuilt .docx), Legal Briefing
  contact block, `CLOUDFLARE_RESEND_SETUP.md`, plus latent
  references in `utils/order_dispatch.py` (fulfilment email),
  `routers/partner_prospects.py` (partner storefront copy), and
  `frontend/src/pages/PartnerInvite.jsx` (partner scenarios text).
- **Verification** (testing_agent iter 39 + local pytest): 16/16 new
  domain-migration tests pass, 65/65 counsel regressions pass.

## 2026-02-04 — Counsel-flow polish + hardening
- **AdminHub layout** — `container` → `container-page max-w-6xl` so
  `/admin` is centred (was left-flushed at ≥1280 px).
- **Session revocation** — `auth_utils.create_token` now embeds an
  `iat_ms` millisecond claim in every JWT; `get_current_user` checks it
  strict-< against `user_token_revocations.revoked_at` (microsecond
  precise). Legacy whole-second `iat` is still honoured as fallback for
  tokens minted before this change. Verified 5/5 same-second same-
  wall-clock rotate → old-token 401 across 3 consecutive test runs
  (65/65 counsel tests each).
- **Send-set-password flow** — new endpoints
  `POST /api/admin/settings/counsel/send-set-password-link` (admin
  strict-only) and `POST /api/admin/settings/counsel/set-password-from-token`
  (public, one-time-use, 24 h expiry). Admin never sees the plaintext.
  Tokens stored SHA-256-hashed in `counsel_password_tokens`. Success
  auto-revokes any active counsel session.
- **`/counsel/set-password`** (`CounselSetPasswordPage.jsx`) — public
  self-service page that consumes the emailed token, sets the counsel
  password, shows a success screen linking to `/login` (using
  `&nbsp;` non-breaking spaces so the preview build's `display:contents`
  babel wrapper cannot collapse the whitespace).
- **Admin UI** — new "Send set-password link" card on
  `/admin/settings/counsel` alongside the existing rotate form.
- **Setup guide** — new operator doc
  `legal_docs/CLOUDFLARE_RESEND_SETUP.md` walks Birthright's ED through
  (a) verifying `birthright.live` in Resend, (b) Cloudflare Email
  Routing `counsel@birthright.live` → firm inbox, (c) rotating the
  stored counsel email + (d) sending the set-password link.
- **Testing** — 65/65 counsel tests pass across
  test_iter32/33/34/35/36/36b/38 suites; 3 consecutive full re-runs.

## 2026-02-04 — /admin/settings/counsel · Credential rotation UI
- **New endpoints** `GET/POST /api/admin/settings/counsel[/rotate]` let
  a true admin (strict role check — counsel is 403'd) rotate the
  counsel account's email and password without editing `.env` and
  restarting.
- **Seeder refactored** (`utils/readonly_admin.py::ensure_counsel_account`)
  to look up by `role=readonly_admin` instead of by email, and to
  never overwrite `email` / `password_hash` after initial bootstrap.
  Rotations now survive backend restarts — verified in iter34 with a
  real `sudo supervisorctl restart backend` between rotate and login.
- **New frontend page** `AdminCounselSettings.jsx` at
  `/admin/settings/counsel` — shows current state (with amber warning
  when the password still matches the env default), lets admin change
  either or both credentials, and displays last-rotated timestamp +
  operator. Written with role gated to `["admin"]` only so counsel
  can't even navigate to it in the UI.
- **Admin Hub tile** added to Governance & System group in
  `AdminHub.jsx` (initial pass mistakenly landed on the deprecated
  `/admin/stats` page — moved to `/admin` in iter35).
- **Security hardening** — GET/POST now call an explicit
  `_require_true_admin(user)` gate at the top of the handler.
  Previously `require_roles('admin')` also admitted counsel
  (readonly_admin) for admin READ routes, which would have leaked
  `env_password_default_in_use` to counsel.
- **Tests** — 49/49 pass:
  `test_iter34_counsel_settings.py` (11), `test_iter35_counsel_settings_strict.py` (6),
  plus the earlier `test_iter32/33_counsel_*` regression suites (32).

## 2026-02-04 — Counsel-facing verification + hardening
- **Counsel User Guide** — new standalone doc
  `legal_docs/00a-counsel-user-guide.md` (+ .docx) with a
  per-function "Fast path (paper) vs Platform path" table for every
  counsel action; each function names what to push to Birthright's
  admin so counsel billable time stays low. Registered in
  `_manifest.py` and downloadable via `/api/legal/drafts/00a-counsel-user-guide`.
- **Briefing integration** — `LEGAL_BRIEFING_FOR_COUNSEL.md` gained
  a new `§ 0. Counsel Fast Path — Minimise Your Billable Time`
  section between the intro callout and § 1, so the same billable-
  time-minimising workflow appears when counsel opens the briefing
  by itself. Regenerated .docx contains it (verified in
  word/document.xml).
- **AI Help Assistant** — 5 new counsel KB entries in
  `data/help_kb.json` (counsel-fast-path, counsel-redline,
  counsel-ratify, counsel-roundtrip-status,
  counsel-scope-what-you-can-do) so the in-app assistant deflects
  counsel questions without hitting the LLM.
- **SECURITY FIX (privilege escalation)** — the read-only middleware
  allow-list was a prefix `/api/legal/comments/` which also matched
  the nested mutating sub-routes `/apply-roundtrip`,
  `/import-roundtrip`, `/{id}/resolve`, and `/export`. Replaced with
  an anchored regex `^/api/legal/comments/[A-Za-z0-9._-]+/?$` that
  matches only the exact comment-create route; nested writes now
  return HTTP 403 `{readonly:true}` for counsel sessions. Defence-
  in-depth: the "Import roundtrip (.docx)" button in
  `AdminLegalRatifications.jsx` is now `isAdmin && (...)` gated so
  counsel never sees the affordance either.
- **Password correction** — the counsel guide previously listed
  `counsel2026`; the seeded value is `counsel-review-2026`. Guide
  + briefing updated.
- **Testing** — testing_agent iter 32 flagged both critical defects;
  iter 33 verified fixes with 33/33 pytest cases + full Playwright
  counsel flow pass. Suites:
  `tests/test_iter32_counsel_guide.py`, `tests/test_iter33_counsel_allowlist.py`.

## 2026-02-04 — Auto-rebuild + Roundtrip email
- `apply-roundtrip` now fires TWO best-effort side-effects immediately
  after the source .md is written:
  1. **`.docx` bundle rebuild** — same script the manual Rebuild button
     runs, wrapped in `_run_docx_rebuild` with a 180s timeout. Result
     surfaces on the response as `rebuilt_docx: bool`.
  2. **Summary email** — `_email_roundtrip_summary` sends a short HTML
     summary to the applier + every user with `role=readonly_admin`
     (counsel). Subject includes the doc title and accepted/rejected
     counts; body has the count table and a note if the .docx rebuild
     failed so an admin knows to click Rebuild manually. Uses the
     shared `send_email` mailer (Resend when configured, dry-run to
     `outbound_emails` otherwise). Response includes `email_id`.
- Neither side-effect can fail the roundtrip — both catch and log.
- Verified end-to-end via curl + backend logs: apply-roundtrip returned
  `rebuilt_docx=true` and Resend queued the email to
  `[admin@birthright.org, counsel@birthright.org]`.

## 2026-02-04 — Ratified DOCX Rebuild + Roundtrip history
- **One-click `.docx` rebuild** — new admin endpoint
  `POST /api/legal/rebuild-docx` shells out to
  `scripts/eu_compliance_and_docx.py` and rebuilds all 22 draft `.docx`
  files plus `LEGAL_BRIEFING_FOR_COUNSEL.docx` from the current
  markdown. Returns a summary of the files touched. Timeout 180s.
- **Rebuild button** surfaced at the top of `/admin/legal/ratifications`
  with a spinning icon while the script runs.
- **Roundtrip history** — new collection `legal_doc_roundtrips` persists
  every `apply-roundtrip` call with `applied_at`, `applied_by_user_id`,
  `applied_by_user_email`, and `counts` (applied / rejected / skipped /
  unmatched / total). New endpoint `GET /api/legal/roundtrips/{slug}`
  returns the doc's roundtrip audit newest-first; counsel
  (`readonly_admin`) inherits admin read access.
- **UI**: Admin ratifications page now renders a per-doc "Roundtrip
  history" card showing each entry with timestamp, applier email, and
  colour-coded accepted / rejected / skipped counts.
- Verified end-to-end via curl: rebuild returned 23 .docx summary
  lines; apply-roundtrip persisted a history row with correct counts;
  roundtrips endpoint returned it.

## 2026-02-04 — Ratification RSS + Redline roundtrip import
- **RSS 2.0 feed** at `/api/legal/history.rss` mirrors the public
  `/legal/history` list — one item per ratification with title, version,
  link, GUID, pubDate, and description. `atom:link rel="self"` included
  for reader compatibility. Base URL prefers the `PUBLIC_SITE_URL`
  env var, falls back to the request host. XML-validated end-to-end.
- **Subscribe via RSS** button surfaced on `/legal/history`.
- **Redline roundtrip import** — new admin endpoints
  `POST /api/legal/comments/{slug}/import-roundtrip` (multipart .docx)
  and `POST /api/legal/comments/{slug}/apply-roundtrip`.
  - Parser walks the returned .docx paragraph-by-paragraph, honours
    Word revision semantics (drops `w:delText`, keeps `w:t` and `w:ins`
    contents), extracts each numbered redline block, and classifies
    counsel's decision as `accept` / `reject` / `edit` / `orphan`.
  - Apply endpoint takes `[{comment_id, action, final_text}]`,
    string-replaces `quoted_text → final_text` in the source .md for
    accepted redlines, marks all decided comments resolved (with a
    new `rejected` boolean when counsel threw them out), and returns
    counts of applied / rejected / skipped / unmatched.
- **Admin UI**: `/admin/legal/ratifications` now shows an "Import
  roundtrip (.docx)" upload button next to Export. Uploading opens
  a preview card with a per-redline action select (accept / reject /
  skip) and an editable final-text input for accepted rows. Apply
  writes the source and refreshes the comment list. Verified full
  round-trip with curl: export → re-upload → preview shows classifier
  action per redline → apply mutates source .md and marks comments
  resolved.

## 2026-02-04 — Ratification change-log + Redline .docx export
- New public endpoint `GET /api/legal/history` returns every ratification
  of a public doc, newest first (public slug + title + version + date +
  ratifying firm). Internal notes are stripped.
- New frontend route `/legal/history` (`LegalHistoryPage.jsx`) — a public
  change-log grouped by year, each row linking to the current live copy
  of that policy. Registered BEFORE `/legal/:slug` so React Router
  matches it exactly.
- `/legal` hub gains a "Ratification history →" link at the footer.
- New authed endpoint `GET /api/legal/comments/{source_slug}/export`
  emits a Word `.docx` with real `w:ins` / `w:del` OXML revision markup
  for every unresolved redline. Opens in Word / LibreOffice as tracked
  changes so counsel can accept / reject offline. Comment-only entries
  (no proposed replacement) are excluded.
- Admin ratifications page now shows "Export unresolved redlines (.docx)"
  when there's at least one open redline on the selected doc. Auth is
  Bearer token via axios blob download.

## 2026-02-04 — IC designations · Legal hub · Versioned ratification · Redlines
- **IC classification broadcast**: `partner_prospects.py` now exposes
  `is_independent_contractor`, `worker_classification`, and
  `worker_classification_note` on every preview spec. IC types =
  facilitator, steward, vendor, artist, community. Sponsor and Research
  remain non-IC.
- **UI chip surfaced** on `/partner/types` (5 IC rows) and
  `/partner/types/:type/try` (banner block on IC types only).
- **IC ack line** added to the agreement re-sign flow
  (`AgreementPage.jsx`); backend persists `ic_acknowledged` on the
  signature record; `my-status` returns `ic_partner_types` so the
  checkbox only appears when the user holds an IC partner profile.
- **`/legal` hub page** (`LegalIndex.jsx`) lists every allowlisted legal
  doc with a one-line preview.
- **Versioned publish flow**: `legal_doc_ratifications` Mongo collection +
  admin endpoints. Rendered pages now return `ratified`,
  `ratified_version`, `ratified_at`; `has_draft_disclaimer` auto-hides
  when a ratification matches the current body hash. Any edit changes
  the hash and the banner returns.
- **Inline counsel redlines**: `legal_doc_comments` collection +
  endpoints; counsel (`readonly_admin`) can POST via middleware
  allow-list.
- **Admin UI** `/admin/legal/ratifications` — ratify / revoke / redline
  from one screen. Linked from the Admin Dashboard.
- **New deliverable**: `legal_docs/00-counsel-review-plan.md` (+.docx)
  segments every instrument into Essential (Section A: public+revenue,
  635 min; B: governance, 320 min) and Optional (C: partner niches,
  200 min; D: internal plans, 170 min) with per-subsection minutes.
  **Total attorney time: 22 hrs** (recommend budgeting ~29 hrs
  including drafting gap-fills + wrap meetings).

## 2026-02-04 — Public Legal Renderer
- `GET /api/legal/pages` lists every public-facing legal doc (slug + title).
- `GET /api/legal/pages/{slug}` renders the Markdown source (`backend/legal_docs/*.md`)
  to sanitized HTML server-side using `markdown==3.10.3`, strips the leading
  `> ⚠️ AI-GENERATED FIRST DRAFT` blockquote and returns it as a
  `has_draft_disclaimer` flag so the frontend can surface it as a banner.
- Slugs are allowlisted (`terms`, `privacy`, `cookie-notice`, `refunds`,
  `scholarships`, `community-standards`); unknown slugs 404.
- New frontend route `/legal/:slug` → `LegalDocPage.jsx` renders the HTML
  with editorial `.legal-prose` typography, an amber "draft — pending
  counsel review" banner when applicable, a last-updated stamp, and a
  `.docx` download link. Unknown slugs bounce to `/`.
- `CookieConsentBanner` updated to link `/legal/cookie-notice`.

## 2026-02-04 — Checkout consent + AI-caption alt tags
- Cart / checkout now requires two mandatory tick-boxes (Terms of Service +
  Privacy Policy) before the "Proceed to checkout" button becomes enabled.
  Legally parallels the existing `/register` consent gate.
- Global site-search backend (`routers/search.py`) now returns an
  `image_alt` field for each hit (products, partners, workshops, research,
  gallery), pulling from the AI vision `image_caption` and falling back to
  the human name/title.
- Frontend `<img>` tags wired to prefer `image_caption`:
  `Cart` item thumb, `ProductDetail` hero, `PartnerProfilePage` avatar,
  `PartnersDirectory` avatar, `Research` cover, `PartnerOfferings` tile,
  `GlobalSearch` result thumb.

Pre–May 22, 2026 entries are reconstructed from PRD.md and are month-level
because the git history was reinitialized on May 19, 2026.

---

## Phase 6C.5 — May 25, 2026 · COMPLETE (AI UX hardening — escape paths, discoverability, welcome credit, auto-recharge wiring)
- **Fixes the user-reported critical bug**: AI Concierge panel was stuck open
  after navigation on mobile (masking the new page) AND error states had no
  escape path. After this round: every action that navigates auto-closes the
  panel + emits a "Navigated to /…" toast; every error state has a clearly
  labeled "Top up / Back to page" pair of buttons; close button is a larger
  "✕ Close" pill instead of a small icon.
- **Out-of-funds card** (`components/AiOutOfFundsCard.jsx`) — shared across
  Concierge, Research Collaborator, Vendor PDM. Renders inline when backend
  returns 402, with both Top-up (navigates) and Back-to-page (onClose) buttons.
- **Pre-flight balance pill** in Research + Vendor drawer headers — shows
  live wallet balance, clicking opens /dashboard/ai-wallet.
- **Welcome credit** — admin partner-application approval now grants $1 to
  the new partner's AI wallet (idempotent via `ref=welcome_{profile_id}`).
- **Auto-recharge wiring complete** — `record_usage` now fires an async task
  to build a Stripe Checkout session + email the partner a top-up link
  (4-hour cooldown).
- **Public /ai marketing page** — three tool cards, pricing pillars, cost
  table, CTAs for sign-in + partner apply.
- **System prompt update** — Claude now knows `/partners?partner_type=...`
  filtered routes + `/dashboard/ai-wallet` for top-ups.
- **PartnersDirectory** reads filter from URL searchParams + syncs back on
  change — enables Concierge deep links + shareable filtered views.
- **Test coverage**: backend 29/29 PASS (23 iter27 regression + 6 new iter28);
  frontend 100% PASS on bug-fix scenarios (navigate-and-auto-close, escape
  buttons visible on mobile 390x844, /ai page renders, balance pill renders
  in drawer for elena@, welcome credit confirmed end-to-end).

## Phase 6C.4 — May 25, 2026 · COMPLETE (AI Wallet + AI Research Collaborator + Vendor PDM AI)
- **AI cost metering & wallet** (`utils/ai_billing.py`, `routers/ai_wallet.py`):
  per-call cost computation from a model price table, partner wallet with
  balance/topup/spend ledgers, Stripe top-ups ($10/$25/$50/$100 packs),
  auto-recharge opt-in, admin grant + usage report endpoints. 1× passthrough.
- **AI Research Collaborator** (`routers/research_ai.py` at `/api/research-collab/*`)
  positioned as a peer collaborator (not secretary) per founder direction.
  7 capabilities in 2 groups:
    - **Inquiry**: synthesize-literature, map-landscape, generate-questions,
      critique-methodology (genuine scholar-grade prompts anchored to attachment
      theory, family systems, intergenerational trauma).
    - **Drafting**: summarize-notes, suggest-tags, polish-draft.
- **Vendor PDM AI** (`routers/vendor_ai.py` at `/api/vendor-ai/*`):
  write-description, suggest-price, marketing-blurb, generate-image (Nano Banana).
- **Concierge metering**: balance-gated only for partner/facilitator roles;
  participants & anonymous visitors remain foundation-funded.
- **Replay last conversation** button (`/api/assistant/my-sessions/last`).
- **Admin AI usage report** at `/admin/ai-usage` — per-user × feature breakdown
  + active-wallet table + day-window filter (7/30/90/365).
- **Test coverage**: backend `test_iter27_ai_billing.py` 23/23 PASS, including
  live Claude calls for synthesize-literature and write-description. Frontend
  iter-27 ~85% PASS — two lucide-react import bugs (`History`, `ImageIcon`)
  caught and fixed by the testing agent; live UI screenshot then confirmed
  the AI Research Collaborator panel renders correctly with the expected
  Inquiry/Drafting groupings + scholar-grade markdown output for "attachment
  repair in adoptive families" (Verrier, Rutter, Dozier, Juffer & van IJzendoorn,
  Zeanah, Brodzinsky — all real, real-cited, not fabricated).

## Phase 6B.6 — May 25, 2026 · COMPLETE (AI Concierge — agentic site-wide guide)
- **Pivoted away from static FAQ modals** at user request — replaced with a
  full agentic AI guide.
- **Backend**: `routers/assistant.py` wraps Claude Sonnet 4.5 via
  `emergentintegrations.LlmChat` + Emergent LLM Key. Endpoints:
  `/api/assistant/{meta,chat,execute,sessions/{id},my-sessions}`.
- **Action registry** with 3 tiers: `auto` (frontend executes immediately —
  navigate, scroll_to, prefill_form, search_*, lookup_*), `confirm` (yellow
  confirmation card — add_to_cart, send_dm, file_dispute, submit_research_draft,
  submit_partner_application, cancel_my_subscription, sign_agreement,
  bookmark, register_for_workshop), `forbidden` (server refuses — final
  payment, role changes, account deletion).
- **Frontend**: `<AssistantWidget>` floating button bottom-right on every page,
  also opens with `/` keyboard shortcut. Slide-in panel with conversation,
  yellow confirm cards w/ accept+decline, audit-logged execution.
- **Test coverage**: backend `test_iter26_assistant.py` 9/9 PASS (including
  2 live Claude round-trips); frontend testing agent 100% PASS (iter 26)
  across navigate / search / forbidden refusal / multi-turn memory paths.
- **Test Plan PDF generated**: `/app/backend/static/exports/birthright-test-plan.pdf`
  (775 KB) — 11 independent suites (A–K) with credentials, environment URLs,
  data-testids, manual + AI Concierge test paths for every flow. Generated
  via `python /app/scripts/build_test_plan.py`.

## Phase 6B.5 — May 25, 2026 · COMPLETE (Research Submissions Queue + Admin Moderation)
- Backend (iter 25): **8/8 PASS** — `test_iter25_research_moderation.py` covers
  partner-status-clamp (published→pending), submit-for-review flow, admin
  approve / request-changes / reject (with required-note validation),
  edit-on-published auto-requeue, non-admin 403, and only-pending guard.
- Three new admin endpoints under `/api/admin/research/{id}`:
  `POST /approve`, `POST /request-changes`, `POST /reject` (latter two require a
  note). New partner endpoint `POST /me/research/{id}/submit-for-review`.
- New statuses on `ResearchArtifactStatus`: `pending_review`,
  `changes_requested`, `rejected` (in addition to existing draft/published/
  archived). New stored fields: `moderation_note`, `moderated_by`,
  `moderated_at`, `submitted_at`.
- Frontend (iter 25): **36/36 UI assertions PASS** — new `AdminResearch.jsx`
  with 5 status tabs + moderation modal + counts; `PartnerResearch.jsx` form
  restricted to "Save as draft" / "Submit for review" + visible mod-note +
  Submit-for-review button on draft/changes_requested/rejected rows;
  Admin Dashboard gains "Research moderation" QuickActionCard.

## Mobile Menu Reorganization — May 25, 2026 · COMPLETE
- Mobile drawer (xl-and-below) now mirrors the footer grouping per the
  user-provided screenshot: gold uppercase EXPLORE and FOUNDATION section
  labels. EXPLORE = Workshops/Shop/Facilitators/Partners/Sponsorship.
  FOUNDATION = About/Mission/Education/Governance/Research/Join Us/Contact.
- Desktop horizontal nav unchanged (flat order: EXPLORE list → FOUNDATION list).

## v1.11.0 Step 10 — May 25, 2026 · COMPLETE (Refund/Clawback Cascade + Agreement v2)
- Backend (iter 23): 57/57 PASS — Stripe refund cascades, credit reversal,
  paid-credit clawback queue, agreement-gate middleware for partner-sensitive
  endpoints (DMs, disputes, subscription checkout). Endpoints:
  `POST /api/admin/refunds`, `GET /api/admin/refunds`, `GET /api/admin/clawbacks`,
  `POST /api/admin/clawbacks/{id}/resolve`,
  `GET /api/legal/indemnification/active|my-status`, `POST .../sign`.
- Frontend (iter 24): 15/15 testable UI flows PASS (1 not-testable due to empty
  pending-clawbacks state — acceptable). New pages: `/admin/refunds`,
  `/legal/agreement`. New `AgreementResignBanner` mounted in Layout (gated by
  unsigned active version, dismissable with localStorage). Admin Dashboard now
  shows a "Refunds & Clawbacks" QuickActionCard.
- Files added: `pages/AdminRefunds.jsx`, `pages/AgreementPage.jsx`,
  `components/AgreementResignBanner.jsx`, `utils/refund_cascade.py`,
  `utils/agreement_gate.py`, `routers/refunds.py`.

## Phase 6C (Communications) — May 25, 2026 · COMPLETE
- 6C.1 Direct Messaging: User↔Partner and Partner↔Partner threads with
  WebSocket reuse, `accepts_status` gating, ombudsman-flagging.
- 6C.2 Ombudsman Role + Queue (`/admin/ombudsman`) with disputes + flagged DMs.
- 6C.3 Disputes Workflow (`/dashboard/disputes`, `/admin/ombudsman`), with
  `trigger_refund_cascade` outcome wiring into v1.11.0 Step 10.

## v1.11.0 Steps 8, 8.5, 9 — May 24-25, 2026 · COMPLETE
- Step 8: Disbursement orchestration (admin-ready-to-pay queue + Stripe payout).
- Step 8.5: Universal Share & Save System (ShareButton w/ QR/Print/Download/
  Send-to-partner) wired across product/workshop/partner/proposal pages.
- Step 9: Subscription UI parity — cancel, change plan, view history.

## v1.11.0 Step 1 — May 24, 2026 ~05:15 UTC · IN PROGRESS
- LOCKED partner economy model committed (per pricing proposal v2):
  - 13 subscription plans seeded with new rates (pre-traction × 0.5 fees;
    Foundation IP share 50% → 42% → 35% by commitment; vendor 22 → 17 → 12;
    community 8/10/12/14% to partner; research free + paid promotion).
  - `seed_subscription_plans.py` rewritten with locked principles; idempotent
    upsert that removes stale plans.
  - New Pydantic models: `FeaturePartnerRequest`, `FoundingPartnerToggle`,
    `RevShareOverride`, `OutboundClickRecord`, `PartnerSalesReportSubmit`,
    `UserCreditEntry`.
  - PartnerProfile extended via `runtime_seed.backfill_partner_economy_fields`:
    14 new fields set with sensible defaults on every boot (idempotent).
- 77/77 regression tests PASS (iter5 + iter11 + iter12 + iter14).
- Bumped existing plan-count test from 12 → 13.

## v1.10.0 hotfix — May 23, 2026 ~11:00 UTC
- Production catalog self-heal (`runtime_seed.py`) — auto-restores missing
  catalog products + repairs stale image URLs on every backend boot.
- N+1 query fixes in `workshops.get_participants` + `community.chat_participants`.
- Complexity refactors: `chat_ws.chat_ws`, `workshops.list_workshops`,
  `products.get_product`, `runtime_seed.ensure_catalog_seeded`.
- Test credential env-var refactor; ruff F-rule cleanup.

## v1.10.0 — May 23, 2026 ~09:00 UTC
- Vendor Autonomous Catalog: vendor CRUD + admin moderation.
- "By vendor" badges on Shop + Product Detail.
- New routes: `/dashboard/vendor/products`, `/admin/vendor-products`.

## v1.9.0 — May 22, 2026
- Community Referrals: `/api/r/{code}` cookie attribution; ledger settled at
  checkout fulfilment.
- Reporting MVP: `/dashboard/reports`, `/admin/reports`, `/admin/payouts`.
- PartnerEarningsCard for community partners.

## v1.8.0 — May 2026 (day not recorded)
- Partner Subscriptions + dual-tier rev-share + auto-licensing.
- 12 plans (3 tiers × 4 partner types).

## v1.7.0 — May 2026 (day not recorded)
- Partner Onboarding Foundation: apply / approve / reject / invite.
- Public partner directory + profile pages.

## v1.6.0 — May 2026 (day not recorded)
- Governance + Legal architecture: proposals, voting, indemnification,
  audit log, global rev-share defaults, ombudsman role.

## v1.5.0 — May 2026 (day not recorded)
- Universal polymorphic reviews + aggregate badges.

## v1.4.0 — Mar 2026 (day not recorded)
- WebSocket chat per workshop + presence + typing + DM targeting.

## v1.3.0 — Feb 2026 (day not recorded)
- Workshop CRUD + facilitator dashboard + photo galleries + cancellations.

## v1.0–1.2 — Feb 2026 (day not recorded)
- Auth, workshops, Stripe checkout, check-in, merch, AI catalog,
  impact statements, storefront expansion, email + auth hardening + waitlist
  + AI image regen.
