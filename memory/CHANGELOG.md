# Birthright Changelog

Day- and time-stamped record of releases and hotfixes. New entries go at the
TOP. Use UTC; localize only when a release is timed to a specific timezone.

Pre–May 22, 2026 entries are reconstructed from PRD.md and are month-level
because the git history was reinitialized on May 19, 2026.

---

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
