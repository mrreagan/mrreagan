# Birthright Foundation Platform — PRD

## Original Problem Statement
Build a website using "birthright" branding with a storefront for merch and workshop resources. Features include workshop advertising, registration, and various partner roles. Phases 6B/6C scope added Partner Economy workflows and agentic AI capabilities. Phase 7 scope: Featured Artists rotation, platform-wide "Explore-before-Embrace" partner invitation framework across all 6 partner types, and Phase 7+ cross-site discovery.

## User Personas
- **Foundation Admin** — manages prospects across all partner types, issues tokenized invitations, fires refund cascades, manages AI Studio drafts, reviews Featured Artist rotation.
- **Partner (six roles)** — Artist, Vendor, Facilitator, Community, Research, Steward. Each gets a tailored Explore-before-Embrace preview before committing.
- **Participant** — registers for workshops, buys merch, joins community.

## Core Requirements (delivered)
- React + FastAPI + MongoDB full-stack platform.
- Stripe checkouts, WebSockets chat, AI Studio with POD fulfillment dispatch (Printful + Lulu).
- Gather/Gallery tabs, Featured Artists rotation, "Explore-before-Embrace" invitation system across all 6 partner roles.
- Comprehensive AI wallet with per-partner balance + per-foundation usage reporting.
- Cross-site global search across workshops, partners, shop, research, and gallery.

## Tech Stack
React, FastAPI, MongoDB, Emergent Integrations (Claude Sonnet 4.5, Gemini Nano Banana), Printful API, Lulu API, Stripe, JWT-based tokenized invitations.

## CHANGELOG

### 2026-06-01 — Backlog batch (5 items)

**(a) Token spend visibility ✅**
- New `GET /ai-wallet/me/summary` lightweight endpoint for dashboard tile
- Enhanced `GET /ai-wallet/me` with `spend_windows` (today/week/month + by_feature_30d)
- Enhanced `GET /admin/ai-wallet/usage-report` with email resolution + Foundation-wide window rollups + wallets sorted by lifetime spend
- New `AiSpendCard` component on partner dashboard (at-a-glance balance + this month spend, low-balance warning)
- AI Wallet page now has a "Recent spend" card with horizontal bar chart per feature
- Admin AI Usage page shows real emails + roles (was: raw UUIDs)

**(b) Refund picker polish ✅**
- New `GET /admin/refunds/refundable-transactions` endpoint with user-email enrichment, type counts, and search filter
- AdminRefunds modal now uses a scrollable transaction picker with type filter pills + search + "selected transaction" card
- Paste-by-ID kept as an escape hatch in collapsible details

**(b-original) Advanced Search & Discovery ✅**
- New `routers/search.py` with `GET /search/global?q=…&types=…&per_type_limit=…` fanout endpoint
- Searches workshops, products, partners, research artifacts, and gallery artists in one call
- New `GlobalSearch` modal component triggered by magnifier icon in the header (Cmd/Ctrl-K shortcut, Esc to close, 250ms debounce)
- Grouped results with section headings, type counts, image thumbnails, hover state
- Shop now has a vendor-source filter row (All sources / Foundation / Vendor partners) + per-vendor dropdown

**(e) AI cover variations ✅**
- New `POST /studio/drafts/{id}/reroll-cover?count=N&set_primary_index=…` endpoint that re-uses the saved brief + category to generate 1–4 new cover images
- New images are APPENDED to `image_gallery` so admin can compare; one can be promoted to primary atomically
- New `POST /studio/drafts/{id}/set-primary-image` endpoint to swap primary from any gallery image (no AI cost)
- AdminStudio draft cards now have a gold "Re-roll" button + inline 4-column gallery picker that shows all options with a checkmark on the current cover
- Surfaces a "regen PDFs" hint when the draft is Lulu-linked

**(f) More Lulu presets ✅**
- Added `pocket_journal_5x8_bw_pb` preset (5×8 pocket paperback journal, 96 default pages)
- 8.5×11 workbook and hardcover gift journal presets already existed
- 3 of 3 requested presets now available in `/api/lulu/presets`

**(d) Refund/clawback cascade ✅ (verified — already shipped in iter23)**
- Backend cascade logic (`utils/refund_cascade.py`), admin endpoints (`routers/refunds.py`), and admin UI (`pages/AdminRefunds.jsx`) were already complete; 17 cascade tests pass.

### 2026-06-01 (later) — Partnership Agreement v2 re-sign (P2) ✅

All 5 sub-items from the agreed plan shipped, tested by testing_agent_v3_fork (14/14 backend + 5/5 frontend pass, zero high/critical bugs).

**1. Admin UI** — New page `/admin/legal/agreements` (`pages/AdminAgreements.jsx`):
   - Three summary tiles (Active version · Active partners · % signed of active version)
   - Version list with signature counts, progress bars, and "View signers" ledger modal
   - "Draft & publish new version" modal with Markdown body editor
   - "Seed from Birthright v2.0 starter" button pulls the curated body (~7,150 chars)
   - Confirmation dialog before publish (lists what publish will do)
   - Linked from `/admin` dashboard quick-actions card

**2. Broader gate** — `utils/agreement_gate.py` now exports `require_active_agreement_partner` (admin-bypass variant). Applied to:
   - `POST /api/me/research` (research artifact create)
   - `POST /api/me/featured/checkout` (featured slot purchase)
   - `PUT /api/me/payouts/w9` (W9 form)
   - `PUT /api/me/payouts/method` (payout method change)
   - `POST /api/studio/generate` (AI Studio draft generation)

**3. Smarter banner** — `components/AgreementResignBanner.jsx` now shows a "What's blocked? (N)" toggle that reveals the per-partner list. The list is computed server-side in `GET /legal/indemnification/my-status` from the user's active partner profiles, so it's always honest.

**4. Email notification on publish** — `_notify_partners_of_new_version` helper in `routers/legal.py` fires a fire-and-forget asyncio task after a new version is activated; emails every user with at least one active non-sample partner profile, deduped by user_id.

**5. Real v2 body** — `agreements/v2_body.py` contains a ~7,150-char Markdown agreement covering: voluntary participation, per-role revenue share, 1.5× AI markup disclosure, content licensing with revocable non-exclusive grant, refund/clawback cascade, 12-month sunset clause, conduct standards, data + privacy, indemnification, termination, amendment + re-sign mechanics, and governing law. Counsel must replace dollar figures before live launch.

**Admin-bypass design decision** — `require_active_agreement_partner` exempts users with `role == "admin"` so admins can publish v2 without first signing v2 (bootstrap deadlock). `require_active_agreement` (gating all users including admins) remains unchanged on the DM and subscription flows.

- Featured Artists backend (12-month decay, locked statement position, 180-char limit)
- "Explore-before-Embrace" tokenized invitation system for ALL 6 partner types
- PreviewModeBanner + Public sandbox per role
- Mission Alignment BLUF + Highlight card with image upload on invites
- Claude AI 3-draft Mission Alignment suggestion endpoint
- Inline "View live preview" link on admin prospect cards (2026-06-01)
- Demo prospects for Research, Steward, and Artist roles (2026-06-01)

## Backlog

### P2
- ~~Partnership Agreement v2 re-sign~~ ✅ Shipped 2026-06-01 (see Changelog above)

### P3
- AI cost-recovery bundle — **DROPPED** (50% Foundation markup already does the job; double-dipping)
- Foundation revenue dashboard tile (Printful margin + Lulu margin + combined)

## Key API Endpoints

### Partner & Discovery
- `GET /api/partners/preview/types/{slug}` — Public sandbox per partner type
- `GET /api/partners/invite/{token}` — Tokenized invitation preview
- `POST /api/partners/invite/{token}/accept` — Atomic account + partner profile creation
- `GET /api/search/global?q=…` — Cross-site fanout search

### AI Wallet
- `GET /api/ai-wallet/me` — Full wallet (balance + events + spend windows)
- `GET /api/ai-wallet/me/summary` — Lightweight dashboard tile data
- `GET /api/admin/ai-wallet/usage-report?days=…` — Foundation-wide AI spend report

### Refunds
- `GET /api/admin/refunds/refundable-transactions?q=…&txn_type=…` — Picker data source
- `POST /api/admin/refunds` — Fire cascade
- `GET /api/admin/clawbacks` — Pending clawbacks

### Studio
- `POST /api/studio/drafts/{id}/reroll-cover?count=N&set_primary_index=I` — AI re-roll
- `POST /api/studio/drafts/{id}/set-primary-image?image_url=…` — Swap primary

### Lulu
- `GET /api/lulu/presets` — Now returns 4 presets (added pocket 5×8)

## Test Credentials
- Admin: `admin@birthright.org` / `birthright2026`
- Demo participant: `demo@birthright.org` / `birthright2026`
- (Credentials also live in `/app/memory/test_credentials.md`.)

## File Map (Reference)

### Backend
- `/app/backend/routers/search.py` — NEW global search
- `/app/backend/routers/ai_wallet.py` — Enhanced (spend_windows, summary, email-resolved admin report)
- `/app/backend/routers/refunds.py` — Enhanced (refundable-transactions picker endpoint)
- `/app/backend/routers/studio.py` — Enhanced (reroll-cover, set-primary-image)
- `/app/backend/routers/lulu.py` — Enhanced (pocket 5×8 preset)
- `/app/backend/routers/partner_prospects.py` — Generic prospect CRUD, AI drafts, invitations
- `/app/backend/scripts/seed_demo_prospects.py` — Idempotent demo seeder for all 6 partner types

### Frontend
- `/app/frontend/src/components/GlobalSearch.jsx` — NEW header search modal
- `/app/frontend/src/components/AiSpendCard.jsx` — NEW dashboard AI tile
- `/app/frontend/src/components/Layout.jsx` — Wires GlobalSearch into header
- `/app/frontend/src/components/shop/ShopParts.jsx` — Added ShopSourceFilters
- `/app/frontend/src/pages/Shop.jsx` — Vendor source filter integration
- `/app/frontend/src/pages/AiWallet.jsx` — Recent spend card + bar chart
- `/app/frontend/src/pages/AdminAiUsage.jsx` — Window rollups + email-resolved wallets
- `/app/frontend/src/pages/AdminRefunds.jsx` — Transaction picker
- `/app/frontend/src/pages/AdminStudio.jsx` — Re-roll button + gallery picker
- `/app/frontend/src/pages/AdminPartnerProspects.jsx` — Inline preview link
- `/app/frontend/src/pages/PartnerDashboard.jsx` — Mounts AiSpendCard
