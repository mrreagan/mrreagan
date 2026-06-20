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

### Iter 49 — Wholesale pricing for foundation members + Admin Hub
- **Foundation-member pricing model.** Per-product `wholesale_price` field added to the Product model + AdminProducts UI (next to retail price, with retail-cap validation). When a user with `is_foundation = True` checks out, every line item with a non-null wholesale_price is billed at the wholesale value; products without wholesale stay at retail. Patronage / gallery markup is also zeroed out for foundation users.
- **AI billing at 1:1 passthrough.** `compute_cost()` accepts a `multiplier` override; `record_usage()` passes `1.0` when `user.is_foundation`, dropping the 50% Foundation markup. Verified math: retail $0.090 → foundation $0.060 (exact 1.5×).
- **Admin Users page (`/admin/users`)** — searchable list of all users with the **Foundation member** toggle inline; filter pills (All · Foundation · Admin); top-right counter of current foundation members. `PATCH /admin/users/{id}/foundation-status` endpoint added to `routers/foundation.py`.
- **Operations Hub at `/admin`** — single canonical home for every admin tool. 28 tiles grouped into 5 sections (Content & Catalog · Partners & People · Commerce & Payouts · AI/Email/Ops · Governance & System). Replaces the "remember which admin URL does what" problem. The previous AdminDashboard stats page moved to `/admin/stats` (still accessible from the hub).
- **End-to-end pricing verification:** demo user marked foundation + journal wholesale=$12.50 → 2 × journal at checkout returns $25.00 with `wholesale_applied=True` on each line, `foundation_markup_per_unit=$0.00`. Flipped foundation off → same cart returns $76.00 with `wholesale_applied=False`. Pipeline is correct.

### Iter 48 — AI Help Assistant retrained on full platform context
- **Root cause of yesterday's demo embarrassment** (asked "who is the executive director?" → assistant deferred to humans): the assistant only ever saw the static `help_kb.json` and the top-2 KB snippets in its LLM context. It had zero visibility into governing members, partner profiles, equip catalog, workshops, or published research — so any question that depended on live content fell through to a generic "I can flag a human."
- **New `utils/help_context.py`** — compiles a single compact "platform fact pack" from `foundation_content`, `governing_members`, `partner_profiles` (public, includes sample profiles since they render publicly), `products` (active, top-30 by feature/rank), `workshops`, `research_artifacts`, plus a canonical site map. Cached for 5 min in-memory with admin-callable invalidation. ~8KB injected into every LLM-fallback turn so the assistant knows about every human-readable thing on the site.
- **Rewrote LLM system prompt** to lead with confidence: "Almost every question about the foundation, its people, its programs, its products, its research, or its site structure can be answered directly. Only escalate to support@ for account-specific issues (billing disputes, refund requests, stuck payouts, data deletion)." Added explicit rule to use slug paths verbatim (e.g. `/partner/sample-rosa-mendieta`, not `/partner/rosa-mendieta`).
- **KB additions**: `leadership-executive-director` (James Reagan), `leadership-team` (full governing team), `what-is-birthright` (mission), `partner-apply`, `partner-types`. All deflect at the lexical layer for zero LLM cost.
- **Tightened lexical matcher**: added question-prefix stopwords (`tell, me, about, please, show, give, find, etc.`); removed `answer[:300]` from the scoring blob so incidental answer-text tokens stop creating false positives.
- **20-question regression** all routed correctly: identity, catalog, workshops, mission, login, share-account → KB at $0; specific-partner queries, longitudinal research, refund nuance → LLM with rich context giving on-point answers. Out-of-scope queries (sourdough, SSRIs) gracefully decline.

### Iter 47 — Manual payout flow polished + latent partner-ledger bug fixed
- **Disbursement email now fires from BOTH mark-paid endpoints** — `/admin/referrals/{id}/mark-paid` was previously silent (only `/admin/payouts/credits/{id}/mark-paid?source=off_site_credit` notified). Both now send the same `disbursement_notification` Resend email so partners always learn about a payout the moment an admin marks it paid.
- **Fixed latent partner-ledger bug** — `GET /api/me/payouts` was reading from `db.referral_payouts` (a legacy projection collection with 1 stale doc) while the live attribution flow writes to `db.referrals` (richer schema). Partners would have seen zero earned credits even after real referrals landed. Switched the ledger to read from `db.referrals`, mapping `payout_amount → amount_usd` for frontend compatibility.
- **Partner ledger now exposes** `payout_method`, `payout_reference`, `payout_note` per entry — previously the API stripped them.
- **`PartnerPayouts.jsx`** redesigned the paid row to show inline pill badges (`VIA ZELLE`, `ref ZELLE-TXN-7842-91`) plus an italic foundation note — partners can match the reference against their bank statement at a glance.
- **End-to-end verified on preview:** synthetic $15 earned → admin POST mark-paid (method=zelle, ref=ZELLE-TXN-7842-91, note) → totals shift $125→$110 unpaid / $100→$115 paid → live Resend email sent to demo@birthright.org (resend_id `966a6da3-...`) → partner UI renders the new pill design correctly. Decouples the platform from Stripe Connect for the first artist cohort.

### Iter 46 — Stripe LIVE money flow verified end-to-end
- **Live key applied** (`STRIPE_API_KEY=rk_live_51TgpjzQ...NESHDZ`, restricted key). Permissions probed: checkout/customers/refunds/subscriptions/products/prices all green; Stripe Connect scopes intentionally deferred (artist payouts unlock when first artist is ready).
- **Live webhook secret applied** (`STRIPE_WEBHOOK_SECRET=whsec_Lre6z8...t7FE`).
- **Webhook handler rewritten** in `routers/checkout.py` to bypass a latent bug in `emergentintegrations.StripeCheckout.handle_webhook` — when `webhook_secret` is provided, the lib's `stripe.Event` return type has a `__getattr__` that traps `.get`/`.to_dict_recursive` as key lookups, causing `AttributeError`. New handler verifies the signature with `stripe.Webhook.construct_event`, then re-parses the raw body as plain JSON for safe access. Handles `checkout.session.completed`, `async_payment_succeeded/failed`, `payment_intent.succeeded/failed`, `charge.refunded`, gracefully ignores unknown event types.
- Same fix applied to `routers/subscriptions.py`.
- **End-to-end live verification (real $1 charge):**
  - Session `cs_live_a12YQsDTINGsBmZGes1S8g8d0vKdaKiHB8oj2iycupo4SpBRI6NBqdMb7y` created via live API.
  - User paid with Visa ····2187. Stripe charge `ch_3TguOkQzY4Y8maAP0Yo4kZk4` succeeded.
  - Preview DB txn marked `paid`, `_process_paid_transaction` dispatched, donation record `398e8a7e...` persisted to `donations` collection.
  - Webhook signature enforcement verified with synthetic signed events on preview (200 on valid, 400 on tampered/missing).
- **Pending after next deploy:** verify production webhook endpoint responds correctly to a tampered-signature probe (confirms env vars + new code are live on prod).

### Iter 45 — Resend live + Partner offerings on-site rail
- **Resend live email VERIFIED end-to-end.** DKIM TXT was being blocked by a legacy NameBright NS delegation (`_domainkey.birthright.live` and `_dmarc.birthright.live` were pointing away from Cloudflare to namebrightdns). Removed those NS records → DKIM resolved → Resend domain status flipped to verified → live test email sent successfully to `admin@birthright.org` (Resend send id `eed6a6f6-89e0-4589-af99-0e75d907c8f5`).
- **Partner offerings rail (on-site revenue retention)** — new endpoint `GET /api/partners/{slug}/offerings` lists every product whose `vendor_slug` matches the partner, on-site fulfilled products ranked above partner-fulfilled. `PartnerOfferings.jsx` renders an image grid on `/partner/<slug>` showing all the partner's birthright listings as tiles linking to `/equip/<product-slug>`. Per the core principle "first and foremost for us," visitors are kept on birthright (where the foundation captures attribution + partnership share) before any external link is offered.
- **Directory cards** now show a green `★ N on birthright` pill linking into the profile's offerings anchor, with the legacy "Visit external site" link demoted to small secondary text ("or visit external site"). 7C's Farmstead pill shows `★ 6 ON BIRTHRIGHT`.
- **`GET /api/partners` enriched** with `offering_count` per profile via a single aggregation pipeline — no N+1.

### Iter 44 — Resend live email key wired; Stripe activation guide
- **Resend API key applied** (`RESEND_API_KEY=re_9As...`) and `EMAIL_DRY_RUN=false` set in `/app/backend/.env`. Backend restarted.
- API key proven healthy via SDK sanity check (sending from `onboarding@resend.dev` to the account owner address succeeds).
- **Domain `birthright.live` status: `failed`** on Resend — SPF (MX + TXT on `send.birthright.live`) is verified ✅; **DKIM TXT on `resend._domainkey.birthright.live` is missing from DNS**. User needs to add the single DKIM TXT record in Cloudflare; once propagated, live transactional sends will start automatically without further code changes.
- **Stripe activation guide** written to `/app/memory/STRIPE_ACTIVATION_GUIDE.md` — covers live key, checkout webhook, Connect platform, Connect webhook, and a live $1 verification flow. Awaiting three secrets from user: `STRIPE_API_KEY` (live), `STRIPE_WEBHOOK_SECRET`, `STRIPE_CONNECT_WEBHOOK_SECRET`.

### Iter 43 — Data migration framework + admin system console
- **`utils/data_migrations.py`** — append-only registry of idempotent data migrations. Each migration has a stable string ID, runs at most once per environment, and records its application in `db.system_migrations`.
- **Auto-runs on backend startup** via the existing `@app.on_event("startup")` hook. New environments catch up automatically; existing environments only get net-new migrations.
- **Admin console at `/admin/system`** (linked from Admin home):
  - **Support email addresses** panel: site-wide editable `support_email` + `hello_email`, surfaced via `GET /api/system/settings/public` so frontend reads dynamically.
  - **Data migrations** panel: shows applied vs. pending list with timestamps, "Run pending now" button, "Force re-run all" escape hatch.
- **Five migrations seeded** to lock in the founder collection state (vendor profile, patches, bundle, carousel default ranks, research-pollution cleanup, system_settings defaults).
- **HelpPage now reads `support_email` from settings** so changing the address in admin propagates everywhere without a code deploy.

### Iter 42 — Founders Collection cleanup, $10 pricing, 5-patch bundle, Help close UX, brand casing pass
- **Pricing & framework correction**: all 5 patches dropped to $10 (was $38 placeholder). Revenue framework set to **15% affiliate revenue share** from 7C's Farmstead (no Foundation patronage markup on top — that framing was inaccurate for off-site fulfillment). Stamped via existing `?via=birthright_7cs-farmstead` outbound attribution. Storefront copy now says "+ shipping at checkout".
- **Long-form descriptions** verbatim from `/shop/patches` for all 5 patches (no shortened blurbs).
- **Bundle SKU added**: `founder-patch-bundle-all-five` at $40 (saves $10 vs 5×$10), minimal copy with pointer to individual product pages for the full narratives.
- **Founder rail reorder**: patches and bundle now lead the rail; patch-02 ("founder of love story") is the homepage feature (Hat Pair flag cleared).
- **Hat image fit** on ProductDetail: aspect-square → aspect-[4/3], removed inner padding.
- **Help close UX** — 5 close affordances: bigger X (40×40 hit target), backdrop tap-outside, ESC key, swipe-down grab handle, "Close chat" link in footer.
- **Research artifact pollution** removed — 24 regression-test "Admin-Approve-Me" rows wiped from `research_artifacts`.
- **Brand casing pass**: 79 mid-sentence "Birthright" → "birthright" replacements across 37 files (sentence-start instances preserved). Help agent name lowercased to "birthright Help".
- **Help KB expanded**: 9 new entries (patch-bundle, patch-shipping, patch-revenue-share, donate, careers, sponsorship, press-media, data-privacy, gift-purchase, homepage-tour) — now 24 total entries, raising deflection rate.

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
