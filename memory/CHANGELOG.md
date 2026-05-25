# Birthright Changelog

Day- and time-stamped record of releases and hotfixes. New entries go at the
TOP. Use UTC; localize only when a release is timed to a specific timezone.

Pre–May 22, 2026 entries are reconstructed from PRD.md and are month-level
because the git history was reinitialized on May 19, 2026.

---

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
