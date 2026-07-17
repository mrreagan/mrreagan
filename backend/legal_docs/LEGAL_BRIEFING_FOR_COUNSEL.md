# Birthright Foundation — Legal Briefing for Counsel
_Prepared for: outside counsel forming the entity and drafting agreements._
_Prepared by: platform engineering (technical scoping only — not legal analysis)._
_Version: February 2026. All figures below reflect the state of the platform in production at **https://birthright.live**._

> How to use this document: each section describes what exists in the product today, then flags the concrete legal instruments we believe need to be drafted, reviewed, or updated. URLs point to live pages counsel can inspect directly. Nothing in this document is legal advice; it is a technical dossier.

---

## 1. Entity Overview

| Attribute | Description |
|---|---|
| Common name | **Birthright Foundation** (also referred to as “birthright” in copy) |
| Public brand | birthright.live |
| Product | A community + education platform combining: (a) an online storefront (physical + digital goods), (b) live and recorded workshops, (c) a peer-artist gallery, (d) a facilitator directory and paid partner program, (e) research and long-form content, and (f) an AI Help Assistant that answers members' questions using platform DB context. |
| Positioning | Blends **charitable / educational mission** ("secure attachment as a birthright") with **commercial revenue streams** (product sales, workshops, subscriptions). |
| Locations | Fully remote / online. No physical retail. |
| Executive Director | James Reagan (`mr.reagan@gmail.com`). Other governing members are currently sample/placeholder profiles flagged `is_sample=true` in the DB pending real board recruitment. |
| Target incorporation | To be determined by counsel. The name and copy suggest **501(c)(3) educational foundation**, but the platform also sells goods and pays partners, so counsel should assess whether a **dual structure** (nonprofit + a for-profit subsidiary or fiscal sponsorship) is warranted. |

**Key legal questions:**
1. Entity form: 501(c)(3) public charity vs. LLC/PBC vs. hybrid (nonprofit + wholly-owned taxable subsidiary for commercial goods).
2. State of incorporation.
3. Federal tax-exempt application (Form 1023 or 1023-EZ) timing.
4. State charitable solicitation registrations in all states where donations are accepted (currently unrestricted geographic reach via Stripe).

---

## 2. Business Model — Revenue Streams the Platform Already Collects

Each of the following flows real money today via Stripe (LIVE mode).

| Stream | Where it lives | Notes for counsel |
|---|---|---|
| **Product sales (Equip / Founder Collection)** | `/equip`, `/equip/{id}` | Hard goods (apparel, mugs, journals, engraved leather patches, art prints). |
| **Workshops (paid registrations)** | `/gather`, `/workshops/{slug}` | Live-facilitated or self-paced sessions. Sliding-scale pricing exists. |
| **Sponsorships (recurring tiers)** | `/sponsor` | Monthly/annual patron tiers with recognition perks. |
| **Donations (one-time)** | `/support`, `/donate` (in-app) | Currently NOT tax-deductible until 501(c)(3) status is granted. Copy needs a disclaimer. |
| **Subscriptions** | `/subscribe`, admin at `/admin/subscriptions` | Content-access memberships. |
| **Gallery patronage (artist works)** | `/gallery`, `/gallery/artist/{slug}` | Buyer pays artist's list price + a **20% "Foundation hospitality markup"** kept by birthright. |
| **Featured artist slot purchases** | `/dashboard/partner/featured` | Artists pay birthright to be featured on the homepage carousel. |
| **AI passthrough (AI Wallet)** | `/dashboard/ai-wallet` | Buyer tops up a prepaid wallet consumed by AI 1:1 sessions; retail is 1.5× actual LLM cost (1.0× "at-cost" for foundation members). |
| **Foundation membership** | `/join`, `/admin/foundation-applications` | Paid roles (board, working groups). |
| **Referral payouts (outbound)** | `/dashboard/partner/payouts`, `/admin/payouts` | Community partners earn commissions on referred sales/registrations. Currently paid **manually** (Stripe Connect flow is built but deferred pending KYC of first artist). |
| **Wholesale to foundation members** | Admin `is_foundation` flag | Foundation members automatically get wholesale pricing on merch. |
| **Vendor middleman (7C's Farmstead)** | `/equip/founder-patch-*` | Buyer pays birthright retail; birthright forwards prefilled reorder to vendor + pays vendor wholesale + shipping out-of-band. |

**Key legal questions:**
1. Sales tax nexus — Stripe collects payments but we do **not** currently collect sales tax. Which states require registration given remote sales of tangible personal property?
2. UBI (unrelated business income) implications if 501(c)(3).
3. Donations vs. purchases distinction on receipts (needed for donor tax deduction if 501(c)(3)).
4. "Foundation" naming — is it a regulated term in the state of incorporation?
5. Sponsorship tiers with perks — quid-pro-quo disclosure rules.

---

## 3. People & Parties — Every Human Role the Platform Recognizes

Codified in the `users.role` field and gated in `auth_utils.require_roles(...)`.

| Role | Description | Existing agreements? |
|---|---|---|
| **Admin** | Full platform control. Currently one person (executive director) + engineering. | None. Need admin/board conduct policy. |
| **Facilitator** | Leads workshops, has a public bio at `/facilitators/{slug}`. Paid per session or salaried. | None. Need facilitator services agreement + IP assignment for workshop materials. |
| **Participant (member)** | Standard end user. Signs up at `/register`. | Placeholder **Universal Indemnification & Hold-Harmless Agreement** at `/legal/indemnification` (see §8). Terms of Service and Privacy Policy do NOT yet exist in publish-ready form. |
| **Partner (artist)** | Sells artwork via the platform gallery. Onboarded via `/partner/apply`. Handles fulfillment directly. | None. Need consignment/gallery agreement, artist warranty of authenticity, revenue-share terms. |
| **Partner (vendor)** | Sells physical goods (e.g., 7C's Farmstead patches) fulfilled by them. Onboarded via `/dashboard/vendor/*`. | None. Need supplier / dropship agreement, wholesale pricing terms, IP indemnity from vendor. |
| **Community partner (referrer)** | Non-vendor partners who refer traffic and earn a commission. | Placeholder referral terms in-app. Need formal referral agreement + Form W-9/1099 process. |
| **Sponsor** | Recurring financial supporter. | None. Public recognition needs sponsor consent language. |
| **Foundation member** | Paid governance / working-group role. `is_foundation=true`. | None. Need officer/director agreement + D&O policy + conflict-of-interest disclosure. |
| **Ombudsman** | Handles disputes. Access at `/admin/ombudsman`. | None. Need ombudsman charter + confidentiality clause. |

**Key legal questions:**
1. Independent-contractor vs. employee classification for facilitators.
2. W-9 collection and 1099-NEC/1099-K threshold compliance for partner payouts.
3. Standard board/officer indemnification clauses + D&O insurance.
4. Volunteer waivers (facilitators occasionally host free sessions).

---

## 4. Data & Privacy Footprint

MongoDB stores ~90 collections. High-sensitivity data includes:

| Data type | Collections | Notes |
|---|---|---|
| Account credentials | `users` (bcrypt-hashed password), `password_reset_tokens` | Auth via JWT. |
| PII | `users`, `partner_applications`, `foundation_role_applications`, shipping addresses in `payment_transactions`, `orders`, `vendor_orders` | Names, emails, phones, addresses. |
| Payment records | `payment_transactions`, `refund_cascades`, `ai_wallet_entries` | We store Stripe session IDs and metadata; **no card numbers or CVV** (Stripe Checkout hosts card entry). |
| Payout banking info | `partner_payout_methods` | Method type + last-4 identifier only; sensitive fields encrypted with `PAYOUT_ENCRYPTION_KEY`. |
| Health-adjacent content | `discussions`, `community_posts`, `dm_messages`, `chat_messages`, `research_artifacts`, `disputes` | Members journal about relational trauma, attachment history. **This is arguably sensitive personal data** even though it isn't HIPAA-covered PHI. |
| Uploaded files | `order_attachments`, `workshop_photos`, gallery images | Any file the buyer uploads for custom orders. |
| AI conversation logs | Chat context stored server-side and forwarded to Google Gemini / Anthropic Claude via Emergent LLM Key. | See §5. |
| Analytics / audit | `audit_log`, `share_events`, `referral_clicks`, `ai_usage_events`, `email_log` | Includes IPs and referrers. |
| Email log | `email_log`, `outbound_emails` | Every outbound email content is retained. |

**Key legal questions:**
1. **Privacy policy** covering all of the above — currently missing.
2. **GDPR / UK-GDPR / CCPA / CPRA / VCDPA / CPA / TDPSA** applicability — buyers can transact from anywhere. Right-of-access and deletion workflows are not yet built.
3. **Age gate.** No COPPA age-gate today; workshops describe attachment work aimed at adults but nothing prevents a minor from signing up.
4. **Data processing agreements (DPAs)** with each sub-processor (see §5).
5. **Retention schedule** for chat/DM/journaling content.
6. **Breach-notification obligations** (state-by-state).
7. **Health-adjacent content** — decide whether platform copy needs an explicit "this is not therapy" disclaimer beyond what's in the indemnification agreement.

---


---

## 4a. EU / UK Compliance Considerations (added Feb 2026)

All draft agreements have been generated with EU/UK alignment in mind and
carry an EU/UK Compliance Addendum. The concrete implications for the
platform:

- **GDPR/UK-GDPR** apply to any EEA/UK data subject. Lawful bases mapped:
  contract necessity, legitimate interests (with opt-out), consent
  (marketing / non-essential cookies), legal obligation.
- **Cookie consent (ePrivacy)** — a consent banner is required before
  non-essential cookies fire. Currently: banner not implemented; only
  strictly-necessary cookies are set (Cloudflare, Stripe at checkout).
- **14-day right of withdrawal (Consumer Rights Directive 2011/83/EU)**
  needs to appear in the Refund & Returns Policy for EU consumers and
  the workshop registration flow.
- **Digital Services Act (Reg. 2022/2065)** — community features are in
  scope. Designate a single point of contact `eu-contact@birthright.live`
  and publish a transparency report annually if traffic thresholds are
  crossed.
- **EU AI Act (Reg. 2024/1689)** — AI Help Assistant and AI image
  generation are labeled as AI-assisted. Not used for automated
  decisions with legal effect. Transparency notice is already present in
  the Terms of Service draft §9.
- **International data transfers** rely on the 2021 SCCs + UK IDTA.
  Every sub-processor DPA (§5) must incorporate these where applicable.
- **DPO** — designate `dpo@birthright.live` when the threshold criteria
  in GDPR Art. 37 are met (systematic large-scale monitoring or large-
  scale processing of special-category data).
- **EU VAT** — evaluate One-Stop-Shop registration for cross-border B2C
  sales of digital services (workshops, subscriptions) and physical
  goods.
- **Supervisory authority** — publish the right of EU/UK residents to
  lodge complaints with local supervisory authorities.

---

## 8b. Draft documents — direct download links (added Feb 2026)

The 21 instruments listed in §8 now have first-draft representative
documents available for counsel to review. Every draft is admin-only and
downloadable via the doc-shelf at `/admin/legal-docs`. Direct links:

## 5. Third-Party Integrations (Sub-processors)

| Vendor | Purpose | Data shared | Contract / DPA in place? |
|---|---|---|---|
| **Stripe** (`stripe`, `emergentintegrations.payments.stripe`) | Payment processing, Stripe Connect (planned for artist payouts) | Buyer name, email, shipping address, order metadata | Stripe standard TOS + connected-account terms. **No custom DPA.** |
| **Resend** (`resend`) | Transactional email (receipts, workshop confirmations, vendor reorders) | Buyer name, email, order details, uploaded file attachments | Resend TOS. **No custom DPA.** |
| **Printful** (`printful_client`) | Print-on-demand apparel/prints fulfillment | Buyer name, address, product variant | Printful merchant TOS. |
| **Lulu** (`lulu_client`) | Print-on-demand book fulfillment | Buyer name, address, product | Lulu merchant TOS. |
| **Google Gemini** (via Emergent LLM Key, model `gemini-3.1-flash-image-preview`) | AI image generation, image captioning, vision analysis | Product descriptions, images | Emergent LLM key umbrella TOS. **Confirm Google's data-retention terms for API use.** |
| **Anthropic Claude** (via Emergent LLM Key, model `claude-sonnet-4-5`) | Help Assistant, prompt analysis for image queue | Platform DB context (team bios, product catalog), user questions | Same as above. |
| **Cloudflare** | DNS, email routing (`hello@birthright.live` → Gmail), DDoS mitigation | Domain traffic metadata, email routing metadata | Cloudflare TOS. |
| **Formester** (via 7C's Farmstead custom-order form) | Third-party form submission for vendor reorders | Buyer name, email, phone, shipping address, order details | 7C's has a merchant relationship with Formester; birthright has no direct contract. |
| **Emergent** (hosting platform) | Application hosting, CI/CD | All of the above (they host the environment) | Emergent platform TOS. |
| **GitHub** (via Emergent's "Save to Github") | Source code hosting | Source code, not customer data | GitHub TOS. |

**Key legal questions:**
1. Which of these require a written **DPA** under GDPR/CCPA?
2. Sub-processor list needs to be published in the privacy policy.
3. Cross-border data transfer mechanisms (SCCs) for EU users if applicable.

---

## 6. Intellectual Property Landscape

### 6.1 Brand
- Marks in use: **"birthright"**, **"birthright.live"**, tagline **"You are the founder of your own love story"**, **"Secure connection is your birthright"**, **"The bond is the cure"**, **"Repair is older than rupture"**, **"We are created for connection"**.
- Logo: an ember-gold flame + wordmark. Asset URL: `https://customer-assets.emergentagent.com/job_c61b4345-eef4-4783-a5af-85e8af10eaf3/artifacts/s0oix25k_image.png`.
- No trademark filings yet.

### 6.2 Content authored in-house
- Workshop scripts and materials (`workshops`, `workshop_photos`).
- Article/long-form content ("Research" collection, `/research`).
- Product descriptions, homepage copy, all UX text.
- Founder Collection SKU names + engraving phrases (registered as products; some are printed on physical goods sold by third-party POD vendors).

### 6.3 AI-generated content stored on the platform
- **Hero and additional product images** generated by Gemini Nano Banana (~55 images published so far). Stored under `/backend/static/products/`.
- **AI vision captions** on those images, used for SEO alt tags and search.
- **AI Help Assistant responses** shown to users. Not stored per-user permanently, but conversation transcripts pass through server memory.
- Emergent LLM Key TOS should be reviewed for **ownership and warranty language** on AI outputs.

### 6.4 User-generated content
- Uploaded files in `order_attachments` (design files for custom vendor orders — retained on our server before being forwarded to the vendor).
- Community posts, discussions, DMs, dispute submissions, reviews.
- Artist gallery submissions.
- Any content Terms of Service will need clear grant-of-license language.

### 6.5 Third-party licensed content
- Product mock-up photos originally sourced from Unsplash-style stock; most have since been replaced by AI-generated originals.
- Stock imagery on the homepage.

**Key legal questions:**
1. Trademark search + USPTO filings for wordmark and logo.
2. Copyright registration strategy for workshop materials + Research articles.
3. Facilitator work-for-hire vs. license-back for workshop content they author.
4. Artist gallery consignment: does birthright get resale rights, marketing rights, digital-reproduction rights?
5. Terms of Service license grant for user-generated content (community posts, reviews, DMs).
6. AI output ownership — do we warrant to buyers that the AI-generated product image on the storefront doesn't infringe a third party's copyright?

---

## 7. Fulfillment & Product Liability

Six distinct fulfillment paths coexist today (indicated by `products.fulfillable_via`):

| Path | Physical risk | Notes |
|---|---|---|
| `printful` | Apparel, mugs, prints. Printful ships direct to buyer. | Standard consumer goods. |
| `lulu` | Books/journals. Lulu ships direct. | Standard consumer goods. |
| `vendor_custom_form` (7C's Farmstead) | Leather-engraved patches. 7C's ships direct. | Small-batch artisanal item. |
| `is_off_site` (partner referral) | Partner sells and ships on their own site; birthright takes referral fee. | Contract determines liability. |
| `is_gallery_artwork` | Artist ships directly. | Artist owns any product-safety risk. |
| Sample / display-only | Concept SKUs not for sale. Cart gated. | No fulfillment. |

Each path implies different **product liability, warranty, and refund** obligations.

**Key legal questions:**
1. Product liability insurance for physical goods sold under the birthright brand.
2. Merchant-of-record status — is birthright the merchant on the Stripe receipt for every SKU? (Yes, today, including third-party fulfilled items.)
3. Return/refund policy: current in-app policy is placeholder.
4. Recall procedure.
5. Sales tax on marked-up POD orders.

---

## 8. Existing Agreements & Legal Copy in the App

### 8.1 Indemnification Agreement (placeholder)
- Path: `/legal/indemnification`
- Backend: `routers/legal.py` (`indemnification_versions`, `indemnification_signatures`)
- Admin console: `/admin/legal/agreements`
- Current text is placeholder marked "not legal advice." Versioning + signature tracking is fully built and ready for real content.

### 8.2 Foundation-role Agreements
- Path: `/admin/foundation-roles`, `/admin/foundation-applications`
- Backend: `routers/foundation_roles.py`, `routers/foundation.py`
- Signable role acceptance workflow exists; agreement text is TBD.

### 8.3 Partner / Facilitator / Vendor onboarding
- Frontend flows exist at `/partner/apply`, `/dashboard/partner`, `/dashboard/vendor/*`.
- No enforceable agreement is served today — application forms collect intent but no signed contract binds the partner.

### 8.4 Referral terms
- Backend: `routers/referrals.py`
- 30-day cookie window is implemented; payout share is admin-configurable per partner. **Not disclosed to referrers or purchasers in a signed agreement.**

### 8.5 Disputes & Ombudsman
- Path: `/dashboard/disputes`, `/admin/ombudsman`, `/admin/disputes/{id}`
- Backend: `routers/disputes.py`
- Fully-built two-party dispute flow with admin adjudication and refund cascade. **The rules of the road** (what a dispute is, who arbitrates, timelines) are not codified in a policy document.

### 8.6 Refund handling
- Backend: `routers/refunds.py`, admin at `/admin/refunds`
- Payment-level refunds via Stripe are automated; cascade rules for partner-payout clawback are implemented (`refund_cascades`, `clawback_pending`) but not disclosed to partners in writing.

### 8.7 Community conduct
- Community features live at `/gather`, `/dashboard/messages`, `/community/*`.
- No community-standards or content-moderation policy is currently published. Content reporting is not implemented.

**Instruments we believe counsel needs to draft or ratify:**

1. **Terms of Service** (with mandatory-arbitration and class-waiver clauses if desired)
2. **Privacy Policy** (with sub-processor list, retention schedule, DSAR workflow)
3. **Cookie / Tracking Notice** (currently: no banner, minimal cookies used)
4. **Universal Indemnification & Hold-Harmless** — real text to replace placeholder at `/legal/indemnification`
5. **Facilitator Services Agreement + IP Assignment**
6. **Artist Consignment / Gallery Partner Agreement**
7. **Vendor Supplier / Dropship Agreement** (specifically for 7C's Farmstead first)
8. **Community Partner Referral Agreement** (with W-9/1099 language)
9. **Sponsorship Agreement / Sponsor Recognition Consent**
10. **Sliding-Scale & Scholarship Terms** (for workshop tiered pricing)
11. **Board Member / Officer Agreement + D&O Coverage**
12. **Foundation Working-Group Volunteer Agreement**
13. **Ombudsman Charter**
14. **Content Moderation & Community Standards Policy**
15. **Refund & Returns Policy** (public-facing)
16. **Sales-Tax Registration Plan** (state-by-state)
17. **Trademark filings** (birthright wordmark + flame logo)
18. **Copyright registration** strategy for workshop and Research materials
19. **Data Processing Agreements** with sub-processors (§5)
20. **Nonprofit governance instruments**: Articles of Incorporation, Bylaws, Conflict-of-Interest Policy, Whistleblower Policy, Document Retention Policy (required for 1023 filing)
21. **State charitable-solicitation registrations** (in states where donations are accepted)

---

## 9. Financial Controls & Money Movement

| Flow | How it works |
|---|---|
| Card charges | Stripe Checkout hosted, LIVE keys. |
| Webhooks | `POST /api/webhook/stripe` (routers/checkout.py) processes `checkout.session.completed`, `payment_intent.succeeded`, `charge.refunded`. |
| Refunds | Full or partial via `/admin/refunds`. Cascades to clawback partner payouts. |
| Partner payouts | Manual outbound today (`/admin/payouts`). Stripe Connect wiring exists but is not activated (deferred until first artist completes KYC). |
| AI cost passthrough | Wallet ledger (`ai_wallet_entries`) with retail 1.5× the actual LLM cost billed by Emergent LLM Key. Foundation members pay at-cost. |
| Vendor middleman | Buyer pays retail + shipping to birthright via Stripe; birthright pays vendor wholesale + shipping out-of-band from the Stripe payout balance. |
| Sponsorship recurring | Stripe Subscriptions. |

**Key legal questions:**
1. Written **payout policy** and **1099 reporting** procedure.
2. **PCI-DSS SAQ-A** applicability (Stripe Checkout hosts card entry, so SAQ-A is generally sufficient; confirm with counsel).
3. **Money transmitter** analysis — birthright collects funds on behalf of artists/vendors before paying them out. This may trigger money transmission law in some states unless structured as agent-of-payee under Stripe Connect (which is why Part D activation matters).

---

## 10. AI-Specific Legal Considerations

The platform actively uses generative AI for:
- Storefront product images (hero + additional angle shots)
- Product image captions (used as SEO alt-text and for search)
- AI Help Assistant answering member questions with platform DB context injected
- Facilitator/executive-director-persona bios pulled from DB into the assistant

**Key legal questions:**
1. Disclosure obligations — do EU AI Act transparency requirements apply?
2. Ownership + warranty of AI outputs (Emergent LLM Key TOS).
3. Right-to-appeal automated decisions? (We use LLMs for image mismatch detection, not for gating people or payments.)
4. Voice / likeness risk — AI-generated images may inadvertently resemble real individuals.
5. If the Help Assistant answers a member's question about attachment or trauma incorrectly, what's the liability posture? (Current indemnification placeholder gestures at this but is not counsel-reviewed.)

---

## 11. Reference URL Map (for counsel to inspect the live platform)

### Public / marketing
- Home: https://birthright.live/
- Founder Collection landing: https://birthright.live/collection/founder
- Storefront: https://birthright.live/equip
- Individual product example (7C's patch): https://birthright.live/equip/founder-patch-04-bond-is-the-cure
- Gallery: https://birthright.live/gallery
- Workshops: https://birthright.live/gather
- Research articles: https://birthright.live/research
- Partner application: https://birthright.live/partner/apply
- Facilitator directory: https://birthright.live/facilitators
- Sponsor / donate: https://birthright.live/sponsor
- Contact / connect: https://birthright.live/connect

### Existing legal surfaces
- Placeholder indemnification: https://birthright.live/legal/indemnification
- Agreement acceptance flow: https://birthright.live/legal/agreement

### Member experience (requires account)
- Register: https://birthright.live/register
- Dashboard: https://birthright.live/dashboard
- AI wallet: https://birthright.live/dashboard/ai-wallet
- Messages: https://birthright.live/dashboard/messages
- Disputes: https://birthright.live/dashboard/disputes
- Bookmarks: https://birthright.live/dashboard/bookmarks

### Partner surfaces (requires partner account)
- Partner dashboard: https://birthright.live/dashboard/partner
- Payouts: https://birthright.live/dashboard/partner/payouts
- Featured slot purchase: https://birthright.live/dashboard/partner/featured
- Vendor product catalog: https://birthright.live/dashboard/vendor/products
- Sales reports: https://birthright.live/dashboard/partner/sales-reports

### Admin (requires admin account — engineering can provision read-only counsel access on request)
- Admin hub: https://birthright.live/admin
- Users: https://birthright.live/admin/users
- Products: https://birthright.live/admin/products
- Partners: https://birthright.live/admin/partners
- Foundation roles: https://birthright.live/admin/foundation-roles
- Foundation applications: https://birthright.live/admin/foundation-applications
- Ombudsman queue: https://birthright.live/admin/ombudsman
- Disputes: https://birthright.live/admin/disputes/*
- Refunds: https://birthright.live/admin/refunds
- Payouts: https://birthright.live/admin/payouts
- Legal agreements manager: https://birthright.live/admin/legal/agreements
- AI usage: https://birthright.live/admin/ai-usage
- Reports: https://birthright.live/admin/reports

### API endpoints of legal interest (JSON responses inspectable at these URLs when authenticated)
- Terms/indemnification versions: `GET /api/legal/indemnification/active`
- Signatures: `GET /api/legal/indemnification/versions` (admin)
- Audit log: `GET /api/audit/*` (admin)
- Outbound emails: `GET /api/system-admin/emails` (admin)

---

## 12. Suggested Priority for Counsel Engagement

Ordered by risk exposure today:

1. **Terms of Service + Privacy Policy** — every purchase and account creation currently happens without a signed agreement. Highest immediate exposure.
2. **Entity formation + tax status** — driving decision for everything else (donation deductibility, UBI, board indemnification).
3. **Real indemnification agreement text** — the placeholder currently disclaims itself as "not legal advice."
4. **Facilitator + Artist + Vendor agreements** — real money flows to third parties today with no written contract.
5. **Sales-tax nexus + charitable-solicitation registration analysis** — state-by-state.
6. **Trademark filings** for the birthright wordmark and flame logo.
7. **Board/Officer agreements + D&O policy** before recruiting real (non-sample) board members to replace the current placeholders.
8. **Data privacy framework** (privacy policy, DPAs, DSAR workflow).
9. **Refund / community-standards / dispute-arbitration** policies.
10. **AI transparency + IP posture** on generated content.

---

## 13. Contacts on our side

| Role | Person | Email |
|---|---|---|
| Executive Director / point of contact | James Reagan | mr.reagan@gmail.com |
| Platform / engineering | Emergent Labs (contractor) | via ED |
| Public contact address | hello@birthright.live | routed via Cloudflare to Gmail |

Engineering can provide counsel with:
- A read-only admin account on the production platform
- Access to a `git`-tracked copy of the source code including all router files referenced above (`/app/backend/routers/*.py`)
- Sample data exports for review

Please direct clarifying questions to James, who will loop in engineering as needed.
