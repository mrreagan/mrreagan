# Birthright Foundation Platform — PRD

## Original Problem Statement
Finalize Phase 6B/6C features, Partner Economy workflows, and Agentic AI capabilities for the Birthright Foundation web platform (React + FastAPI + MongoDB). Recent focus has shifted to marketing-asset production for the brand's first physical product line — laser-engraved leather patches carrying 5 attachment-theory phrases.

## Persona
- **Founder/Operator (primary user of this session)** — building marketing assets for FB, IG, and the storefront.
- **Partners (Vendors / Artists / Stewards / Researchers)** — using the Partner Economy modules.
- **Members (general public)** — reading research, attending events, buying merch.

## Core Brand Aesthetic
- Cream / warm parchment / soft natural light
- Editorial serif italics with a single bold-upright-roman focal word
- Thin gold hairline rules
- Generous whitespace
- Sacred but secular tone

## What's Been Implemented (current session highlights)
- Phase 1-7 platform: complete (admin, partners, payouts, AI Studio, POD fulfillment, refunds/clawbacks, global search, AI spend visibility, Partnership Agreement v2, public Partners directory, hidden `/engraving` gallery).
- **(2026-02-07) Facebook Promotional Composite Pack** — `/app/backend/scripts/generate_fb_promo_assets.py` produces:
  - 5 hero shots: Nano Banana 2 image-to-image takes each physical patch photo, replaces the paper-towel background with a per-phrase brand-aligned scene, and slightly deepens the engraving so `birthright.live` is legible at thumbnail size.
  - 5 social cards: Pillow code-composite at 1080×1350 (FB portrait feed). Cormorant Garamond italic + semibold focal + gold hairline rule + long-form "beautiful explanation" paragraph. Served from `/fb-assets/*.png`.

## P0 / Active
- *None* — pending user review of FB promo assets.

## P3 / Backlog
- Foundation revenue dashboard tile (Printful margin + Lulu margin + combined). (Carried from prior session.)

## Key Files (this session)
- `/app/backend/scripts/generate_fb_promo_assets.py` (new) — hero + social-card pipeline
- `/app/frontend/public/fb-assets/` — output PNGs (hero-XX-*.png, fb-XX-*.png)
- `/tmp/fonts/CormorantGaramond-*.ttf` — runtime fonts (downloaded from gstatic)

## 3rd-Party Integrations
- Gemini Nano Banana (gemini-3.1-flash-image-preview) via Emergent LLM key — image-to-image hero generation
- Claude Sonnet 4.5 — agentic/text
- Stripe, Printful, Lulu, Resend — user-provided keys

## Test Credentials
See `/app/memory/test_credentials.md`.
