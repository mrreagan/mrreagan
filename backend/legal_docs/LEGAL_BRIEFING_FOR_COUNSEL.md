# Birthright Foundation — Legal Briefing for Counsel

_February 2026 — reflecting the platform in production at **https://birthright.live**._
_Prepared by platform engineering as a technical dossier; nothing herein is legal analysis._

---

# 1 · Engagement Snapshot

**What Birthright is.** A remote, mission-driven community + education platform that
combines an online storefront (physical + digital goods), live and recorded workshops,
a peer-artist gallery, a facilitator directory and paid partner program, long-form
research content, and a member-facing AI Help Assistant. Live production traffic and
Stripe LIVE-mode revenue on all streams below.

**Where counsel comes in.** Entity formation is not yet complete; no counsel-ratified
public agreements are live. All draft agreements exist as `.docx` in the Counsel
Console download hub. Priorities are laid out in §5.

**How we work with counsel.** All redlines are round-tripped through the Counsel
Console; the Executive Director does every platform click. Full workflow, per-function
fast-path, and the read-only review account are in `00a-counsel-user-guide.docx`.

**Point of contact.** James Reagan, Executive Director — `mr.reagan@gmail.com`.

---

# 2 · Business Overview

## 2.1 Entity

- **Common name:** Birthright Foundation (public brand: `birthright.live`).
- **Positioning:** charitable/educational mission (secure attachment as a birthright)
  layered on top of commercial revenue streams (goods, workshops, subscriptions,
  sponsorship). Structure choice — pure 501(c)(3), hybrid with a taxable subsidiary,
  or PBC/LLC — is open for counsel's recommendation.
- **State of incorporation, Form 1023 timing, and state charitable-solicitation
  strategy** are all open.

## 2.2 Revenue streams (all live on Stripe today)

| Stream | Surface |
|---|---|
| Product sales (Founder Collection, apparel, prints, engraved leather) | `/equip` |
| Workshops (paid registrations, sliding-scale) | `/gather`, `/workshops/{slug}` |
| Sponsorships (recurring tiers) | `/sponsor` |
| One-time donations (not yet tax-deductible) | `/support` |
| Subscriptions (content-access memberships) | `/subscribe` |
| Gallery patronage (20% Foundation hospitality markup) | `/gallery` |
| Featured artist slot purchases | `/dashboard/partner/featured` |
| AI passthrough (prepaid wallet; retail 1.5× LLM cost) | `/dashboard/ai-wallet` |
| Foundation membership (paid board/working-group roles) | `/join` |
| Referral payouts (outbound; Stripe Connect built, not yet activated) | `/dashboard/partner/payouts` |
| Wholesale to foundation members | `is_foundation` flag on user |
| Vendor-middleman fulfillment (7C's Farmstead first) | `/equip/founder-patch-*` |

## 2.3 People & roles

Codified in `users.role` and enforced by `auth_utils.require_roles(...)`. Present:
Admin, Facilitator, Participant, Artist Partner, Vendor Partner, Community Referrer,
Sponsor (auto-promoted to Sponsor Partner at $100 one-time or $25/mo × 3 months),
Foundation Member, Ombudsman. Contract coverage today = **none**; every role above
needs a written instrument (see §5).

## 2.4 Fulfillment paths

Six coexist (`products.fulfillable_via`): `printful`, `lulu`,
`vendor_custom_form` (7C's), `is_off_site` (partner referral), `is_gallery_artwork`,
and sample/display-only. Each implies distinct product-liability, warranty, and
refund posture. Birthright is currently the merchant of record on every Stripe
receipt, including third-party fulfilled items.

---

# 3 · Data, Privacy, and Audit Posture

## 3.1 Data footprint

MongoDB, ~90 collections. Sensitive categories:

- **Account credentials** — bcrypt hashes, JWT sessions.
- **PII** — names, emails, phones, shipping addresses across users, applications,
  and orders.
- **Payment records** — Stripe session IDs and metadata only; no PAN/CVV
  (Stripe Checkout hosts card entry).
- **Payout banking** — encrypted at rest with `PAYOUT_ENCRYPTION_KEY`; only
  method type + last-4 stored plaintext.
- **Health-adjacent journaling** — attachment/relational content in
  discussions, DMs, disputes, research artifacts. Not PHI, but sensitive.
- **AI conversation logs** — help-assistant transcripts, image-caption prompts.
- **Audit / analytics** — IP, user-agent, referrers, share/referral events.

## 3.2 Sub-processors

| Vendor | Purpose | DPA in place |
|---|---|---|
| Stripe | Payments; Stripe Connect (planned) | Standard TOS only |
| Resend | Transactional email | Standard TOS only |
| Printful | Apparel/print POD | Merchant TOS |
| Lulu | Book POD | Merchant TOS |
| Google Gemini (via Emergent LLM Key) | Image generation, vision captions | Umbrella TOS |
| Anthropic Claude (via Emergent LLM Key) | Help Assistant | Umbrella TOS |
| Cloudflare | DNS, email routing, DDoS | TOS only |
| Emergent Labs | Application hosting + CI/CD | Platform TOS |
| GitHub | Source hosting (no customer data) | TOS only |

## 3.3 Audit trail (recently added)

Three internal collections; disclosed in the draft Privacy Policy and referenced by
the draft Counsel Terms of Access:

| Collection | Purpose | Retention |
|---|---|---|
| `user_activity_log` | Auth events + admin URL trace | 365 days rolling |
| `counsel_activity_log` | Every request from a counsel session | Manual admin purge |
| `counsel_review_status` | Counsel's per-doc sign-off (initials, notes) | Indefinite |

Audit rows survive account deletion as a legitimate-interests carve-out — flagged
explicitly in the draft Privacy Policy. Counsel sessions cannot view any activity
log, including their own; requests return 403.

## 3.4 Regulatory frames already flagged in drafts

All draft agreements carry an EU/UK compliance addendum covering GDPR/UK-GDPR
lawful bases, ePrivacy cookie consent, the CRD 14-day right of withdrawal, the DSA
single-point-of-contact (`eu-contact@birthright.live`), EU AI Act transparency, SCC
+ UK IDTA for cross-border transfers, and DPO trigger criteria. US frameworks
touched: CCPA/CPRA, VCDPA, CPA, TDPSA, and state breach-notification statutes. No
COPPA age gate is in place today.

---

# 4 · Intellectual Property Landscape

## 4.1 Brand marks in active commerce (unregistered)

- **Wordmark:** `birthright` (lowercase, primary); `birthright.live` (domain-mark);
  `birthright Foundation` (organizational, pending formation).
- **Composite mark:** wordmark + interlocking ember/teal flame device +
  `SECURE BONDS > THRIVE` tagline lockup. Embedded below (§4.3).

## 4.2 Taglines and short-form marks in active public use

| # | Mark | Where |
|---|---|---|
| 1 | "Secure bonds are your birthright." | Homepage hero |
| 2 | "We are the practice ground." | Practice page hero |
| 3 | "A practice that grows with you" | Practice / membership |
| 4 | "Born for connection" | Homepage; about |
| 5 | "Secure bonds are our birthright." | Mission statement |
| 6 | "A practice, not a curriculum" | Practice page |
| 7 | "Made to live with the work" | Founder Collection |
| 8 | "Artists in the room" | Gallery |
| 9 | "Help someone claim their birthright." | Sponsorship pages |
| 10 | "The people behind the work." | Board/team |
| 11 | "Help us build the foundation." | Capital fundraising |
| 12 | "Communities of practice" | Gather / community |

Legacy in-use taglines (verify current usage): _"You are the founder of your own
love story"_, _"Secure connection is your birthright"_, _"The bond is the cure"_,
_"Repair is older than rupture"_, _"We are created for connection"_.

## 4.3 Embedded brand assets

**Figure 1 — Primary composite mark:**

![Primary composite mark](brand_assets/logo_composite.jpeg)

**Figure 2 — Mission-statement flame lockup:**

![Mission statement lockup](brand_assets/mission_statement.jpeg)

## 4.4 Content — authored, AI, and user-generated

- **In-house:** workshop scripts, `/research` articles, product copy, SKU names,
  engraving phrases (some printed by POD vendors).
- **AI-generated (Emergent LLM Key):** ~55 storefront product images (Gemini),
  vision captions, help-assistant responses. Emergent LLM Key TOS governs
  ownership and warranty.
- **User-generated:** `order_attachments`, community posts, discussions, DMs,
  disputes, reviews, gallery submissions. Terms of Service needs an explicit
  license-grant.
- **Third-party licensed:** stock imagery has largely been retired in favor of
  AI originals; a few remain.

---

# 5 · Priority One (immediate exposure)

The Priority One work stream is one bucket — the seven public-facing agreements
plus the foundational compliance, incorporation, IP-protection, and governance
instruments that must land before the platform can operate cleanly with real
counterparties.

Draft `.docx` for each item is available in the Counsel Console. One-line
summaries only; the drafts speak for themselves.

## 5.1 Public-facing documents (all seven)

| # | Document | One-line summary |
|---|---|---|
| P1-a | **Terms of Service** (draft `01-terms-of-service`) | Master contract for every account and purchase; currently no signed instrument at all. |
| P1-b | **Privacy Policy** (draft `02-privacy-policy`) | Sub-processor list, retention schedule, audit-log carve-out, DSAR workflow. |
| P1-c | **Cookie & Tracking Notice** (draft `03-cookie-notice`) | EU/UK opt-in banner posture; currently only strictly-necessary cookies fire. |
| P1-d | **Universal Indemnification & Hold-Harmless** (draft `04-indemnification-hold-harmless`) | Replaces the self-disclaiming placeholder live at `/legal/indemnification`. |
| P1-e | **Sliding-Scale & Scholarship Terms** (draft `10-sliding-scale-scholarship-terms`) | Public terms for tiered/scholarship workshop pricing. |
| P1-f | **Content Moderation & Community Standards** (draft `14-community-standards`) | Prohibited conduct, enforcement ladder, appeals. Nothing published today. |
| P1-g | **Refund & Returns Policy** (draft `15-refund-returns-policy`) | Digital vs. physical vs. workshop refund posture; public copy. |

## 5.2 Compliance, incorporation, IP, and governance (non-document)

| # | Work item | One-line summary |
|---|---|---|
| P1-h | **Entity formation + tax status** | Choice of 501(c)(3), hybrid, or PBC; state of incorporation; Form 1023 timing. Driving decision for everything else. |
| P1-i | **Sales-Tax Registration Plan** (draft `16-sales-tax-registration-plan`) | Nexus analysis by state; registration timeline. |
| P1-j | **Trademark Filings Plan** (draft `17-trademark-filings-plan`) | USPTO Classes 41, 45, 25 (+ 09 pending). Composite mark + priority taglines. |
| P1-k | **Copyright Registration Strategy** (draft `18-copyright-registration-strategy`) | Workshop curricula, research articles, and the founder's manuscript. |
| P1-l | **Data Processing Agreement template** (draft `19-data-processing-agreement-template`) | Sub-processor DPA base with SCCs + UK IDTA. |
| P1-m | **Nonprofit Governance Bundle** (draft `20-nonprofit-governance-bundle`) | Articles, Bylaws, COI Policy, Whistleblower Policy, Document Retention Policy. |
| P1-n | **State Charitable Solicitation Plan** (draft `21-charitable-solicitation-plan`) | Priority-state registrations ahead of any public fundraising. |

---

# 6 · Priority Two (structural, follow-on)

Partner instruments and governance charters that formalize existing money flows
and can proceed in parallel with Priority One as counsel's bandwidth allows.

| # | Document | One-line summary |
|---|---|---|
| P2-a | **Facilitator Services Agreement + IP Assignment** (draft `05-facilitator-services-agreement`) | Contractor status, scope, IP assignment for Birthright-branded workshop content. |
| P2-b | **Artist Consignment / Gallery Partner Agreement** (draft `06-artist-consignment-agreement`) | Consignment, warranty of originality, 20% Foundation hospitality markup. |
| P2-c | **Vendor Supplier / Dropship Agreement** (draft `07-vendor-supplier-agreement`) | 7C's Farmstead first; product-liability + IP indemnity from vendor. |
| P2-d | **Community Partner Referral Agreement** (draft `08-community-partner-referral-agreement`) | 25% commission, W-9/1099 process, misrepresentation guardrails. |
| P2-e | **Sponsorship Agreement + Sponsor Recognition Consent** (draft `09-sponsorship-agreement`) | Non-deductibility disclosure, public-recognition opt-in, no quid-pro-quo. |
| P2-f | **Board Member / Officer Agreement + D&O Coverage** (draft `11-board-officer-agreement`) | Fiduciary duties, COI disclosure, indemnification, admin-console audit acknowledgement. |
| P2-g | **Foundation Working-Group Volunteer Agreement** (draft `12-volunteer-agreement`) | Volunteer status, confidentiality, IP assignment, injury waiver. |
| P2-h | **Ombudsman Charter** (draft `13-ombudsman-charter`) | Independence, confidentiality, scope, remedies. |
| P2-i | **Counsel Terms of Access** (draft in §7.1 below) | New — countersigned by counsel; acknowledges session logging. |
| P2-j | **ISTV Contract Analysis Memo** (draft `22-istv-contract-analysis-memo`) | One-off business-value + risk memo on the ISTV contract. |

---

# 7 · Existing Legal Surfaces in the Product

## 7.1 Indemnification (versioned + signed)

Path `/legal/indemnification`; backend `routers/legal.py` handles version publishing,
signature capture, and enforcement. Copy today is the self-disclaiming placeholder
(P1-d replaces it).

## 7.2 Foundation-role acceptance

Path `/admin/foundation-roles`; role-acceptance workflow ready to accept real
agreement text (P2-f/g).

## 7.3 Partner onboarding

`/partner/apply` + `/dashboard/partner|vendor/*`. Application forms only — no
enforceable contract yet (P2-a/b/c/d).

## 7.4 Referrals, disputes, refunds

Referral cookie window and payout share are implemented (`routers/referrals.py`).
Dispute flow + ombudsman queue + refund cascade with partner-clawback are all built
(`routers/disputes.py`, `routers/refunds.py`, `/admin/refunds`). No written policy
codifies the rules of the road (P1-g, P2-h).

## 7.5 Community

Community, DMs, gallery all live at `/gather` and `/community/*`. No moderation
policy published; content reporting not yet built (P1-f).

---

# 8 · Financial Controls & Money Movement

- **Card charges** — Stripe Checkout hosted, LIVE keys.
- **Webhooks** — `POST /api/webhook/stripe` handles `checkout.session.completed`,
  `payment_intent.succeeded`, `charge.refunded`.
- **Refunds** — full or partial via `/admin/refunds`; cascade to clawback partner payouts.
- **Partner payouts** — manual outbound today; Stripe Connect wiring exists and is
  deferred until the first artist completes KYC (this is what unlocks
  agent-of-payee posture for money-transmission analysis).
- **AI cost passthrough** — wallet ledger (`ai_wallet_entries`); retail 1.5× actual
  cost, at-cost for foundation members.
- **Vendor middleman** — buyer pays Birthright retail + shipping; Birthright pays
  vendor wholesale + shipping out-of-band from Stripe payout balance.
- **PCI posture** — Stripe Checkout hosts card entry; SAQ-A is the intended scope.

---

# 9 · AI-Specific Considerations

The platform actively uses generative AI for storefront imagery, image captions,
help-assistant responses, and facilitator/executive-director-persona bios.
Live-checkout gating and payments are NOT AI-mediated. Points for counsel:

- EU AI Act transparency labelling and disclosure obligations.
- Emergent LLM Key TOS — AI-output ownership and warranty language.
- Voice/likeness risk on AI-generated imagery.
- Liability posture when the help assistant answers a member's attachment/trauma
  question (placeholder indemnification gestures at this).

---

# 10 · Live Platform — URL Map

## 10.1 Public / marketing

- Home: `https://birthright.live/`
- Founder Collection: `https://birthright.live/collection/founder`
- Storefront: `https://birthright.live/equip`
- Gallery: `https://birthright.live/gallery`
- Workshops: `https://birthright.live/gather`
- Research: `https://birthright.live/research`
- Partner application: `https://birthright.live/partner/apply`
- Sponsor / donate: `https://birthright.live/sponsor`
- Contact: `https://birthright.live/connect`

## 10.2 Existing legal surfaces

- Placeholder indemnification: `https://birthright.live/legal/indemnification`
- Agreement acceptance: `https://birthright.live/legal/agreement`

## 10.3 Admin surfaces (counsel account can inspect)

- Counsel Console (all drafts, working-draft workflow): `https://birthright.live/counsel`
- Admin hub: `https://birthright.live/admin`
- Counsel review checklist: `https://birthright.live/admin/counsel-review`
- Counsel activity log (admin-only): `https://birthright.live/admin/counsel-activity`
- User activity / admin trace: `https://birthright.live/admin/user-activity`
- Legal agreements manager: `https://birthright.live/admin/legal/agreements`
- Ombudsman queue: `https://birthright.live/admin/ombudsman`
- Refunds / Disputes: `/admin/refunds`, `/admin/disputes/*`

## 10.4 API endpoints of legal interest

- `GET /api/legal/indemnification/active`, `/versions`
- `GET /api/audit/*` (admin)
- `GET /api/system-admin/emails` (admin)

---

# 11 · Read-Only Counsel Account

- **Sign-in:** `https://birthright.live/login`
- **Email:** `counsel@birthright.live`
- **Password:** `counsel-review-2026`
- **Role:** `readonly_admin`

Every request from the counsel session (URL, method, response status, IP,
user-agent, timestamp) is logged to an internal audit trail visible to Foundation
administrators; the counsel account itself cannot view any log. Full detail lives
in the draft Counsel Terms of Access (P2-i).

The **Counsel User Guide** (`00a-counsel-user-guide.docx`) covers the full
review workflow, per-function fast paths (redline, roundtrip, ratify, revoke,
checklist, activity log, change log), and how to hand work back to Birthright.

---

# 12 · Contacts

| Role | Person | Email |
|---|---|---|
| Executive Director / point of contact | James Reagan | `mr.reagan@gmail.com` |
| Public contact address | Birthright team | `hello@birthright.live` |
| Legal work inbox | Counsel review | `legal@birthright.live` |
| Data protection (when applicable) | DPO placeholder | `dpo@birthright.live` |
| EU point of contact (DSA) | EU liaison placeholder | `eu-contact@birthright.live` |

Engineering can provide: the live read-only counsel account (already provisioned
above), a `git`-tracked copy of the source code, and sample data exports on
request.


## 8b. Draft documents — public download links

| # | Draft | Category | Public download |
|---|---|---|---|
| 1 | **Counsel Review Plan — Priority One & Priority Two** | Briefing | https://birthright.live/api/legal/drafts/00-counsel-review-plan |
| 2 | **Counsel User Guide** | Briefing | https://birthright.live/api/legal/drafts/00a-counsel-user-guide |
| 3 | **Terms of Service (Draft)** | Public-facing | https://birthright.live/api/legal/drafts/01-terms-of-service |
| 4 | **Privacy Policy (Draft)** | Public-facing | https://birthright.live/api/legal/drafts/02-privacy-policy |
| 5 | **Cookie & Tracking Notice (Draft)** | Public-facing | https://birthright.live/api/legal/drafts/03-cookie-notice |
| 6 | **Universal Indemnification & Hold-Harmless Agreement (Draft)** | Public-facing | https://birthright.live/api/legal/drafts/04-indemnification-hold-harmless |
| 7 | **Facilitator Services Agreement + IP Assignment (Draft)** | Partner agreements | https://birthright.live/api/legal/drafts/05-facilitator-services-agreement |
| 8 | **Artist Consignment / Gallery Partner Agreement (Draft)** | Partner agreements | https://birthright.live/api/legal/drafts/06-artist-consignment-agreement |
| 9 | **Vendor Supplier / Dropship Agreement (Draft, 7C's Farmstead first)** | Partner agreements | https://birthright.live/api/legal/drafts/07-vendor-supplier-agreement |
| 10 | **Community Partner Referral Agreement (Draft)** | Partner agreements | https://birthright.live/api/legal/drafts/08-community-partner-referral-agreement |
| 11 | **Sponsorship Agreement / Sponsor Recognition Consent (Draft)** | Partner agreements | https://birthright.live/api/legal/drafts/09-sponsorship-agreement |
| 12 | **Sliding-Scale & Scholarship Terms (Draft)** | Public-facing | https://birthright.live/api/legal/drafts/10-sliding-scale-scholarship-terms |
| 13 | **Board Member / Officer Agreement + D&O Coverage (Draft)** | Governance | https://birthright.live/api/legal/drafts/11-board-officer-agreement |
| 14 | **Foundation Working-Group Volunteer Agreement (Draft)** | Governance | https://birthright.live/api/legal/drafts/12-volunteer-agreement |
| 15 | **Ombudsman Charter (Draft)** | Governance | https://birthright.live/api/legal/drafts/13-ombudsman-charter |
| 16 | **Content Moderation & Community Standards Policy (Draft)** | Public-facing | https://birthright.live/api/legal/drafts/14-community-standards |
| 17 | **Refund & Returns Policy (Draft, Public)** | Public-facing | https://birthright.live/api/legal/drafts/15-refund-returns-policy |
| 18 | **Sales-Tax Registration Plan (Draft)** | Internal / Compliance | https://birthright.live/api/legal/drafts/16-sales-tax-registration-plan |
| 19 | **Trademark Filings Plan (Draft)** | Internal / IP | https://birthright.live/api/legal/drafts/17-trademark-filings-plan |
| 20 | **Copyright Registration Strategy (Draft)** | Internal / IP | https://birthright.live/api/legal/drafts/18-copyright-registration-strategy |
| 21 | **Data Processing Agreement Template (Draft)** | Governance | https://birthright.live/api/legal/drafts/19-data-processing-agreement-template |
| 22 | **Nonprofit Governance Bundle (Draft — Articles, Bylaws, COI, Whistleblower, Retention)** | Governance | https://birthright.live/api/legal/drafts/20-nonprofit-governance-bundle |
| 23 | **State Charitable Solicitation Registration Plan (Draft)** | Internal / Compliance | https://birthright.live/api/legal/drafts/21-charitable-solicitation-plan |
| 24 | **ISTV Contract — Full Text Review & Business Value Memo** | Advisory memos | https://birthright.live/api/legal/drafts/22-istv-contract-analysis-memo |
