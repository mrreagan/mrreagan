# Birthright Foundation Platform — PRD

## Original Problem Statement
Build a website using "birthright" branding with a storefront for merch and workshop resources. Features include workshop advertising, registration, and various partner roles. Phases 6B/6C scope added Partner Economy workflows and agentic AI capabilities. Most recent scope: finalize Featured Artists rotation system and a platform-wide "Explore-before-Embrace" partner invitation framework across all 6 partner types (Artist, Vendor, Facilitator, Community, Research, Steward), featuring Claude AI-generated Mission Alignment BLUFs and highlight cards.

## User Personas
- **Foundation Admin** — manages prospects across all partner types, issues tokenized invitations, oversees governance, reviews Featured Artist rotation.
- **Partner (six roles)** — Artist, Vendor, Facilitator, Community, Research, Steward. Each gets a tailored Explore-before-Embrace preview before committing.
- **Participant** — registers for workshops, buys merch, joins community.

## Core Requirements (delivered)
- React + FastAPI + MongoDB full-stack platform.
- Stripe checkouts, WebSockets chat, AI Studio with POD fulfillment dispatch (Printful + Lulu).
- Gather/Gallery tabs, complete Featured Artists 12-month decay rotation with locked statement positions.
- Comprehensive "Explore-before-Embrace" tokenized invitation system covering all 6 partner roles, with AI-assisted Mission Alignment drafting.

## Tech Stack
React, FastAPI, MongoDB, Emergent Integrations (Claude Sonnet 4.5, Gemini Nano Banana), Printful API, Lulu API, Stripe, JWT-based tokenized invitations.

## What's Implemented (CHANGELOG)
### 2026-06-01
- Added inline "View live preview ↗" link on collapsed prospect cards in `AdminPartnerProspects.jsx` (saves admins a click per prospect).
- Created idempotent demo seed `backend/scripts/seed_demo_prospects.py` adding three new exemplar prospects:
  - **Research** — Dr. Priya Raghavan (Toronto, ON)
  - **Steward** — Joaquín Estrada (Phoenix, AZ)
  - **Artist** — Ines Whitfield (Asheville, NC)
- All six partner types now have demo prospects with working invite tokens.

### Prior session highlights
- Featured Artists backend logic: 12-month decay, 60-day horizon, Foundation slot sorting.
- Artist statement position lock (5 randomized safe UI spots) + 180-char limit.
- "Explore-before-Embrace" tokenized invitation system for ALL 6 partner types.
- Universal "Modeling vs. Committing" PreviewModeBanner.
- Public "Try the dashboard" sandbox per role.
- Mission Alignment BLUF + Highlight card with image upload on invites.
- Claude AI 3-draft Mission Alignment suggestion endpoint.
- Refined, concise tier pricing descriptions across all partner types.

## Backlog (Prioritized)
### P2
- Token spend visibility for wallets — show token balance/spend directly in the Birthright platform.
- Advanced Search & Discovery — cross-site search, vendor filters.
- AI cost-recovery bundle — one-click "+$25/mo AI" addition on partner subscription plans.
- Refund/clawback cascade + Partnership Agreement v2 re-sign.

### P3
- AI cover variations button — re-roll image + regenerate PDFs.
- More Lulu presets — hardcover gift journal, 8.5×11 workbook, 5×8 pocket.
- Foundation revenue dashboard tile — Printful margin + Lulu margin + combined.

## Key API Endpoints
- `GET /api/partners/preview/types/{slug}` — Public sandbox per partner type.
- `GET /api/partners/invite/{token}` — Tokenized invitation preview (public, increments preview_count).
- `POST /api/partners/invite/{token}/accept` — Atomic account + partner profile creation.
- `POST /api/partners/admin/prospects` — Admin creates prospect.
- `POST /api/partners/admin/prospects/draft-suggest-mission` — Claude 3-draft generation.
- `POST /api/partners/admin/prospects/{id}/promote` — Issue tokenized invitation.

## Test Credentials
- Admin: `admin@birthright.org` / `birthright2026`
- Demo participant: `demo@birthright.org` / `birthright2026`
- (Test credentials live in `/app/memory/test_credentials.md`.)

## File Map (Reference)
- `/app/backend/routers/partner_prospects.py` — generic prospect CRUD, AI drafts, invitations.
- `/app/backend/routers/gallery.py` — Featured Artists rotation logic.
- `/app/backend/scripts/seed_demo_prospects.py` — idempotent demo prospect seeder.
- `/app/frontend/src/pages/AdminPartnerProspects.jsx` — admin tracker with inline preview link.
- `/app/frontend/src/pages/PartnerInvite.jsx` — public Explore-before-Embrace page.
- `/app/frontend/src/pages/PartnerTypeTry.jsx` — public sandbox by role.
- `/app/frontend/src/components/PreviewModeBanner.jsx` — universal modeling-vs-committing banner.
