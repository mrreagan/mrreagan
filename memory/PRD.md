# Birthright Foundation Platform — PRD

## Original Problem Statement
Finalize Phase 6B/6C features, Partner Economy workflows, and Agentic AI capabilities for the Birthright Foundation web platform (React + FastAPI + MongoDB). Recent focus has shifted to marketing-asset production for the brand's first physical product line — laser-engraved leather patches carrying 5 attachment-theory phrases.

## Persona
- **Founder/Operator** — building marketing assets for FB, IG, and the storefront.
- **Partners** (Vendors / Artists / Stewards / Researchers) — Partner Economy modules.
- **Members** — research, events, merch.

## Core Brand Aesthetic
- Cream / warm parchment / soft natural light
- Editorial serif italics (Cormorant Garamond) + bold-upright roman focal word
- Thin gold hairline rules
- Generous whitespace
- Sacred but secular tone

## What's Been Implemented (recent)
- Phase 1-7 platform: complete (admin, partners, payouts, AI Studio, POD fulfillment, refunds/clawbacks, global search, AI spend visibility, Partnership Agreement v2, public Partners directory, hidden `/engraving` gallery).
- **(2026-02) Facebook Promo Pack — Patch Series**:
  - v1: paraphrased copy, mixed angles.
  - v2: flat-lay top-down heroes, paraphrased copy, brand teal+gold cards.
  - v3: verbatim "What this means" summaries, 1080×1920 portrait, brand teal+gold.
  - v4: 3/4 perspective heroes with signature objects (signet ring / pen / paired cups / key / kintsugi dish), alternating tilts (corrected so #1 + #3 + #5 share consistent direction), softer lighting, locked rounded-rectangle patch shape.
  - **v4-landscape (1920×1080) — recommended canonical format**, hero on left + verbatim copy on right.
- **(2026-02) Internal Marketing Section**:
  - `/marketing` — index page listing campaign packs (link-only, not in nav, not indexed).
  - `/fb-promo` — the FB Patch Pack gallery (link-only, not in nav).
  - Future campaigns slot in via single entry in `MarketingIndex.jsx::CAMPAIGNS`.

## P0 / Active
- *None* — FB Patch Pack accepted by founder. Pending deploy to make URLs permanent.

## P3 / Backlog
- Foundation revenue dashboard tile (Printful margin + Lulu margin + combined).
- Multi-platform variants of Patch Pack (IG 1:1, Reels/Stories 9:16, Twitter/X 1600×900) on demand.
- Future marketing campaign packs added under `/marketing`.

## Key Files (current session)
- `/app/backend/scripts/generate_fb_promo_assets.py` (v1 — historical)
- `/app/backend/scripts/generate_fb_promo_assets_v2.py` (v2 — historical)
- `/app/backend/scripts/generate_fb_promo_assets_v3.py` (v3 — cards only, verbatim copy)
- `/app/backend/scripts/generate_fb_promo_assets_v4.py` (v4 — current canonical hero + portrait card pipeline)
- `/app/backend/scripts/generate_fb_promo_assets_v4_landscape.py` (v4 landscape — current canonical 1920×1080)
- `/app/frontend/public/fb-assets/v4/` — v4 portrait heroes & cards
- `/app/frontend/public/fb-assets/v4-landscape/` — v4 landscape cards
- `/app/frontend/src/pages/MarketingIndex.jsx` (new — `/marketing` index)
- `/app/frontend/src/pages/FbPromoGallery.jsx` (new — `/fb-promo` gallery)
- `/app/scripts/fonts/CormorantGaramond-*.ttf` — pipeline fonts

## 3rd-Party Integrations
- Gemini Nano Banana (gemini-3.1-flash-image-preview) — image-to-image heroes via Emergent LLM key
- Claude Sonnet 4.5 — text/agentic via Emergent LLM key
- Stripe, Printful, Lulu, Resend — user-provided keys

## Test Credentials
See `/app/memory/test_credentials.md`.
