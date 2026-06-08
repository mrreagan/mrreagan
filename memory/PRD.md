# Birthright Foundation Platform — PRD

## Original Problem Statement
Finalize Phase 6B/6C features, Partner Economy workflows, and Agentic AI capabilities for the Birthright Foundation web platform (React + FastAPI + MongoDB).

## Persona
- **Founder/Operator** — marketing assets, dashboards, governance.
- **Partners** (Vendors / Artists / Stewards / Researchers) — Partner Economy modules.
- **Members** — research, events, merch.

## Core Brand Aesthetic
- Cream / warm parchment / soft natural light
- Editorial serif italics (Cormorant Garamond) + bold-upright roman focal word
- Thin gold hairline rules + brand teal `#2C4E5A` ink
- Generous whitespace
- Sacred-but-secular tone

## What's Been Implemented (recent)
- Phase 1-7 platform (complete).
- **(2026-02) Patch Series marketing assets**:
  - v4 landscape 1920×1080 (canonical FB) + v4 portrait 1080×1920 + v4 hero 1024×1024
  - v4-multi: IG square 1080×1080, IG Story/Reel 1080×1920, Twitter/X 1600×900
  - Heroes use 3/4 perspective, alternating tilts, signature objects (ring · pen · cups · key · kintsugi), softer lighting.
  - v2/v3 retained as drafts behind disclosure.
- **(2026-02) Internal marketing section** (`/marketing` + `/fb-promo`, link-only, not in nav).
- **(2026-02) Foundation Revenue · POD Margin tile**:
  - Backend `GET /api/admin/foundation/revenue/pod-margin?days=N` aggregates Printful + Lulu revenue/cost/margin from `db.orders.items[*] ⋈ db.products`.
  - Surfaces `missing_cost_skus` for data hygiene.
  - Window toggle: all-time / 30 / 90 / 365.
  - Mounted on `/admin` below the StatsGrid.
  - Tests: `test_iter37_foundation_revenue.py` — 4 cases passing (auth gates, shape, math, windowing, missing-cost flag).

## P0 / Active
- *None* — patch pack accepted by founder; POD margin tile shipped and tested.

## P3 / Backlog
- Public "Patches" product landing page on birthright.live (linked from shop, destination for the FB ads).
- Additional marketing campaign packs under `/marketing`.
- Push & deploy to make `/marketing`, `/fb-promo` permanent at birthright.live.

## Key Files (current session)
- `/app/backend/routers/foundation_revenue.py` (new)
- `/app/backend/scripts/generate_fb_promo_assets_v4.py` (canonical hero pipeline)
- `/app/backend/scripts/generate_fb_promo_assets_v4_landscape.py` (FB landscape)
- `/app/backend/scripts/generate_fb_promo_variants.py` (IG + Twitter sizes)
- `/app/backend/tests/test_iter37_foundation_revenue.py` (new)
- `/app/frontend/src/pages/AdminDashboard.jsx` (added `<PodMarginTile />`)
- `/app/frontend/src/pages/FbPromoGallery.jsx` (added IG + Twitter tiles)
- `/app/frontend/src/pages/MarketingIndex.jsx` (new — `/marketing` index)
- `/app/frontend/public/fb-assets/v4/`, `v4-landscape/`, `v4-multi/` — output PNGs

## 3rd-Party Integrations
- Gemini Nano Banana (image-to-image) via Emergent LLM key
- Claude Sonnet 4.5 via Emergent LLM key
- Stripe / Printful / Lulu / Resend — user-provided keys

## Test Credentials
See `/app/memory/test_credentials.md`.
