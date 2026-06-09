# Birthright Foundation Platform — PRD

## Original Problem Statement
React + FastAPI + MongoDB platform for the Birthright Foundation — attachment-theory research, artist gallery, partner economy, AI-powered patron experiences, and merch.

## Persona
- **Founder/Operator** — governance, payouts, content, dashboards.
- **Artists** — gallery partnership, patronage payouts, tiered referral economics.
- **Partners** (Vendors / Stewards / Researchers / Community) — Partner Economy modules.
- **Members** — research, events, merch.

## Core Brand Aesthetic
- Cream `#F8F2E5` + brand teal `#2C4E5A` + gold `#A87A4A`
- Cormorant Garamond italic + bold-upright roman focal word
- Generous whitespace, gold hairline rules, sacred-but-secular tone

## What's Been Implemented (recent — Feb 2026)

### Iter 41 — Agentic Concierge removed; Founder Collection patches; lightweight Help assistant
- **Patches in storefront**: 5 leather-engraved patches added to Founder Collection under collection=`founder_collection`, fulfilled off-site by **7C's Farmstead** (custom-order URL). Reused existing `is_off_site` + outbound-click attribution. Editorial intro paragraph added above the rail. "Founder of your love story" patch promoted to `is_homepage_feature`.
- **Research sample fix**: broken Unsplash cover for the Co-Regulation Practices brief replaced with a stable URL.
- **Help assistant** (new): KB-first deflection (free for ~70% of questions) + Claude Haiku 4.5 fallback (~$0.001/turn). Floating "Need help?" pill bottom-left on every page, full-page UI at `/help`, footer link "Help · Ask the AI", session persistence in localStorage, escalate-to-human button.
  - Files: `backend/routers/help_assistant.py`, `backend/data/help_kb.json` (14 entries), `frontend/src/components/HelpAssistant.jsx`, `frontend/src/pages/HelpPage.jsx`
  - 9 pytests passing (`tests/test_iter40_help_assistant.py`)
- **Agentic Concierge removed**: deleted `routers/assistant.py`, `components/AssistantWidget.jsx`, `tests/test_iter26_assistant.py`, and the assistant test class from `test_iter27_ai_billing.py`. Full source archived at `/app/archive/agentic_concierge/` with a learning-oriented README covering the `<<ACTION>>` block protocol, tier-based executor, and restore recipe.

### Iter 39 — Tier-history audit timeline + Shareable tier achievement
- `db.artist_tier_history` ledger logging tier transitions going forward (initial baseline pre-dismissed, real UP/DOWN transitions tracked)
- `utils/artist_tier.log_tier_change()` invoked from `resolve_artist_tier` — fires once per tier_key change
- `GET /api/partner/me/tier-history` — rows + `pending_share` (unacknowledged UP transition)
- `POST /api/partner/me/tier-history/{id}/dismiss-share` — owner-checked acknowledgement
- `GET /api/share/artist/{slug}/tier-card.png` and `.svg` — public Open-Graph-friendly 1200×630 share card, Pillow-rendered (no external service cost), referral_url funneled through `/api/r/{code}` so any visit drives inbound attribution back to the artist
- `ArtistStudio.jsx` — celebration banner with Share / Download PNG / Download SVG / Copy share text buttons + vertical tier-history timeline
- 6 pytest cases passing (`tests/test_iter39_tier_history_share.py`)

### Patch Series marketing assets
- v4 + v4-landscape + v4-multi (IG square / IG Story / Twitter)
- `/marketing` index page + `/fb-promo` gallery (link-only, not in nav)

### Foundation Revenue · POD Margin tile
- `GET /api/admin/foundation/revenue/pod-margin?days=N` (admin-gated)
- Mounted on `/admin` dashboard below StatsGrid
- 4 pytest cases passing

### Artist Partnership — Tracks 1+2+3 + tier system (this session)
- **Patronage payouts** (artist gets list price, Foundation kept 20% buyer markup): `db.artist_sale_payouts` ledger, checkout hook in `_create_order_from_txn`, idempotent
- **Tiered economics**:
  - 🌱 Emerging $0–$5K, 10% in, 0% out
  - 🌿 Sustaining $5K–$15K, 8% in, 2% out
  - 🌳 Established $15K–$40K, 6% in, 4% out
  - 🌸 Thriving $40K–$100K, 5% in, 6% out
  - 🌟 Flourishing $100K+, 5% in, 8% out
- Outbound = marginal brackets (progressive-tax style)
- Basis = trailing-12-month Birthright-attributed revenue (on-site at list + off-site self-reported with `?via=birthright`)
- **Inbound referrals** for artists: extended `resolve_referral_for_checkout` to accept artist partner type, uses tier-based pct, first-purchase-only guard per (artist, buyer) pair
- **Off-site (outbound)** flow: lifted `is_off_site` + `external_url` allowance to artworks via `ArtworkCreate.is_off_site/external_url`; quarterly self-reporting via existing `partner_sales_reports`
- **Admin tools**: `GET /admin/artist/payouts`, `POST /admin/artist/payouts/{id}/mark-paid`, `GET/POST /admin/artist/tier-overrides`
- **Artist dashboard tier card** on `/artist/studio` (current tier + basis + runway to next + override reason if applicable)
- **Public clarity page** `/partner/artist` — exhaustive Artist Partnership Terms with live tier table, worked examples, attribution rules, non-negotiables. Clarity-before-commitment honored.
- **6 pytest cases passing** (boundary tier math, marginal bracket math at all tiers incl. $250K Flourishing example landing at $16,800, public tier-table endpoint shape, patronage payout creation & idempotency)

## P0 / Active
- *None* — Tracks 1+2+3+tier system shipped, tested, and documented to user.

## P3 / Backlog
- Artist `/partner/me/off-site-report` UI page (data layer already exists via `partner_sales_reports`).
- Stripe Connect for auto-payout to artists (currently manual admin-disbursement).
- Public artwork detail UI surfacing of "Ships from artist's studio" badge + dual CTA (patronage / off-site).
- Push & deploy preview → birthright.live.
- Foundation revenue dashboard tile sparkline.
- Additional marketing campaign packs under `/marketing`.

## Key Files (this session)
- `/app/backend/utils/artist_tier.py` (new — tier resolver + marginal-bracket math)
- `/app/backend/routers/artist_partnership.py` (new — payouts + tier + admin)
- `/app/backend/routers/checkout.py` (added patronage payout hook)
- `/app/backend/routers/referrals.py` (artist-aware attribution + first-purchase guard)
- `/app/backend/routers/gallery.py` (added artist_external_url + is_off_site to ArtworkCreate/Update)
- `/app/backend/server.py` (router registration)
- `/app/backend/tests/test_iter38_artist_partnership.py` (new — 6 cases)
- `/app/frontend/src/pages/ArtistPartnershipTerms.jsx` (new — public clarity page)
- `/app/frontend/src/pages/ArtistStudio.jsx` (added ArtistTierCard)
- `/app/frontend/src/App.js` (route `/partner/artist`)

## 3rd-Party Integrations
- Gemini Nano Banana via Emergent LLM key
- Claude Sonnet 4.5 via Emergent LLM key
- Stripe / Printful / Lulu / Resend — user keys

## Test Credentials
See `/app/memory/test_credentials.md`.
