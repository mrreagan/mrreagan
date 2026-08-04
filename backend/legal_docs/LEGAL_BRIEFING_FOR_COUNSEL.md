# Birthright Foundation — Legal Briefing for Counsel
_Prepared for: outside counsel forming the entity and drafting agreements._
_Prepared by: platform engineering (technical scoping only — not legal analysis)._
_Version: February 2026. All figures below reflect the state of the platform in production at **https://birthright.live**._

> How to use this document: each section describes what exists in the product today, then flags the concrete legal instruments we believe need to be drafted, reviewed, or updated. URLs point to live pages counsel can inspect directly. Nothing in this document is legal advice; it is a technical dossier.

---

## 0. Counsel Fast Path — Minimise Your Billable Time

**Cheapest workflow.** Ask us to email you the two `.docx` files —
`LEGAL_BRIEFING_FOR_COUNSEL.docx` (this file) and
`00a-counsel-user-guide.docx`. Redline in Word with Track Changes.
Email the marked-up files to `legal@birthright.live`. Birthright's
Executive Director does every platform click. **You never need to log
in for a normal review pass.**

**Push these to Birthright's admin (they cost billable time and are clerical):**

- Transcribing your redlines into the platform (~30 s per redline).
- Applying accepted / rejected roundtrip decisions.
- Marking documents as counsel-ratified after your one-line ratification email.
- Rebuilding the counsel-briefing bundle after edits.
- Ticking off the manual review checklist and recording your initials.

**Do these personally (they are legal work, not clerical):**

- Substantive legal analysis of every draft.
- Rewording of proposed replacement text in each redline.
- The final one-line ratification email per document.
- Advice on licensing, insurance, and dispute-jurisdiction choices.

The full per-function fast-path table (redline, roundtrip, ratify,
revoke, checklist, activity log, change-log) lives in the standalone
Counsel User Guide — `00a-counsel-user-guide.docx`.

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
2. UBI (unrelated business income taxation under Internal Revenue Code Section 512) implications if 501(c)(3).
3. Donations vs. purchases distinction on receipts (needed for donor tax deduction if 501(c)(3)).
4. "Foundation" naming — is it a regulated term in the state of incorporation?
5. Sponsorship tiers with perks — quid-pro-quo disclosure rules.

---

## 3. People & Parties — Every Human Role the Platform Recognizes

Codified in the `users.role` field and gated in `auth_utils.require_roles(...)`.

**Glossary — Type column abbreviations (multi-select):**
- **L = Lead / Leader.** Applies to roles with governance, executive, or platform-administration authority (Admin, Foundation member, Ombudsman).
- **M = Member.** Applies universally to every role — everyone with an account is a member of the Birthright ecosystem and is subject to the participant-level agreements (Terms of Service, Privacy Policy, Universal Indemnification).
- **P = Partner.** Applies to roles where the person or organization has a contractual working relationship with the foundation beyond simple participation — facilitators, artists, vendors, community referrers, and sponsors (Sponsor is now a partner type).

**Other abbreviations in this table:** *(spelled out here to avoid ambiguity elsewhere in this document)* IP = intellectual property; D&O = directors and officers liability insurance; W-9 / 1099-NEC / 1099-K = Internal Revenue Service (IRS) tax forms; PII = personally identifiable information; PHI = protected health information; HIPAA = Health Insurance Portability and Accountability Act; JWT = JSON Web Token; DPA = data processing agreement; POD = print-on-demand; TOS = terms of service; DNS = domain name system; DDoS = distributed denial of service; SCC = Standard Contractual Clause; IDTA = International Data Transfer Agreement.

| Role | Type | Description | Existing agreements? |
|---|---|---|---|
| **Admin** | L, M | Full platform control. Currently one person (executive director) plus engineering. | None. Need admin/board conduct policy. |
| **Facilitator** | M, P | Leads workshops, has a public bio at `/facilitators/{slug}`. Paid per session or salaried. | None. Need facilitator services agreement plus intellectual-property assignment for workshop materials. |
| **Participant (member)** | M | Standard end user. Signs up at `/register`. | Placeholder **Universal Indemnification & Hold-Harmless Agreement** at `/legal/indemnification` (see §8). Terms of Service and Privacy Policy do NOT yet exist in publish-ready form. |
| **Partner (artist)** | M, P | Sells artwork via the platform gallery. Onboarded via `/partner/apply`. Handles fulfillment directly. | None. Need consignment/gallery agreement, artist warranty of authenticity, revenue-share terms. |
| **Partner (vendor)** | M, P | Sells physical goods (e.g., 7C's Farmstead patches) fulfilled by them. Onboarded via `/dashboard/vendor/*`. | None. Need supplier / dropship agreement, wholesale pricing terms, intellectual-property indemnity from vendor. |
| **Community partner (referrer)** | M, P | Non-vendor partners who refer traffic and earn a commission. | Placeholder referral terms in-app. Need formal referral agreement plus Internal Revenue Service Form W-9 / 1099-NEC process. |
| **Sponsor** | M, P | Financial supporter — recurring subscription OR one-time campaign pledge. Auto-elevated to Sponsor Partner (with a public partner profile) once cumulative contributions cross the threshold ($100 one-time or $25/mo × 3 months minimum). Not currently tax-deductible; Birthright has not yet received 501(c)(3) determination from the IRS. | None. Need sponsorship agreement, sponsor recognition consent language, and non-deductible-contribution disclosure that already appears site-wide. |
| **Foundation member** | L, M | Paid governance / working-group role. `is_foundation=true`. | None. Need officer/director agreement plus directors and officers (D&O) liability insurance plus conflict-of-interest disclosure. |
| **Ombudsman** | L, M | Handles disputes. Access at `/admin/ombudsman`. | None. Need ombudsman charter plus confidentiality clause. |

**Key legal questions:**
1. Independent-contractor versus employee classification for facilitators.
2. Internal Revenue Service Form W-9 collection and Form 1099-NEC / 1099-K threshold compliance for partner payouts.
3. Standard board/officer indemnification clauses plus directors and officers (D&O) liability insurance.
4. Volunteer waivers (facilitators occasionally host free sessions).
5. Sponsor recognition consent and public-listing opt-in language (needed before displaying any real sponsor's name or logo publicly).

---

## 4. Data & Privacy Footprint

MongoDB stores ~90 collections. High-sensitivity data includes:

| Data type | Collections | Notes |
|---|---|---|
| Account credentials | `users` (bcrypt-hashed password), `password_reset_tokens` | Auth via JWT. |
| PII | `users`, `partner_applications`, `foundation_role_applications`, shipping addresses in `payment_transactions`, `orders`, `vendor_orders` | Names, emails, phones, addresses. |
| Payment records | `payment_transactions`, `refund_cascades`, `ai_wallet_entries` | We store Stripe session IDs and metadata; **no card numbers or CVV** (Stripe Checkout hosts card entry). |
| Payout banking info | `partner_payout_methods` | Method type + last-4 identifier only; sensitive fields encrypted with `PAYOUT_ENCRYPTION_KEY`. |
| Health-adjacent content | `discussions`, `community_posts`, `dm_messages`, `chat_messages`, `research_artifacts`, `disputes` | Members journal about relational trauma, attachment history. **This is arguably sensitive personal data** even though it isn't Health Insurance Portability and Accountability Act (HIPAA)-covered protected health information (PHI). |
| Uploaded files | `order_attachments`, `workshop_photos`, gallery images | Any file the buyer uploads for custom orders. |
| AI conversation logs | Chat context stored server-side and forwarded to Google Gemini / Anthropic Claude via Emergent LLM Key. | See §5. |
| Analytics / audit | `audit_log`, `share_events`, `referral_clicks`, `ai_usage_events`, `email_log` | Includes IPs and referrers. |
| Email log | `email_log`, `outbound_emails` | Every outbound email content is retained. |

**Key legal questions:**
1. **Privacy policy** covering all of the above — currently missing.
2. **Privacy law applicability across jurisdictions** — buyers can transact from anywhere. Right-of-access and deletion workflows are not yet built. Applicable frameworks include:
   - General Data Protection Regulation (GDPR — European Union)
   - United Kingdom GDPR (UK-GDPR)
   - California Consumer Privacy Act / California Privacy Rights Act (CCPA / CPRA)
   - Virginia Consumer Data Protection Act (VCDPA)
   - Colorado Privacy Act (CPA)
   - Texas Data Privacy and Security Act (TDPSA)
3. **Age gate.** No Children's Online Privacy Protection Act (COPPA) age-gate today; workshops describe attachment work aimed at adults but nothing prevents a minor from signing up.
4. **Data processing agreements (DPAs)** with each sub-processor (see §5).
5. **Retention schedule** for chat/DM/journaling content.
6. **Breach-notification obligations** (state-by-state).
7. **Health-adjacent content** — decide whether platform copy needs an explicit "this is not therapy" disclaimer beyond what's in the indemnification agreement.

### 4b. Audit & activity logging (added: current release)

The platform now maintains three internal audit collections to give admin, counsel, and regulators forensic visibility. Counsel should be aware these exist because they materially affect the Privacy Policy (IP + user-agent are personal data) and because counsel's own review session activity is logged.

| Collection | Purpose | Data captured | Retention |
|---|---|---|---|
| `user_activity_log` | Tier 1 security events for all authenticated users (logins, logouts, password events, sensitive document signings, payments) plus Tier 2 URL trace for admin sessions | user_id, email, role, event_type, category, method, path, status_code, IP address, user-agent, metadata, timestamp | **365 days rolling** — enforced by nightly scheduler job `user_activity_retention` |
| `counsel_activity_log` | Every request made by any `readonly_admin` (counsel) session | user_id, email, method, path, status_code, IP address, user-agent, timestamp | **Manual purge only** — admin can purge from `/admin/counsel-activity` after a review cycle closes |
| `counsel_review_status` | Counsel's manual sign-off on each legal draft (initials, notes, timestamp), plus auto-derived indicator of whether counsel actually opened each document URL | slug, user_id, email, manual_reviewed, manual_initials, notes, updated_at | **Retained indefinitely** — this is the durable audit trail of counsel's review |

**Erasure policy for audit data:** Per product decision, audit rows are retained even after the underlying user account is deleted. This preserves the security timeline for legal defense (e.g., a former admin later disputes an action they took). This is a deliberate carve-out from the general right-of-erasure under GDPR Article 17 and CCPA §1798.105 and MUST be surfaced explicitly in the Privacy Policy as a legitimate-interests processing basis.

**User transparency:** Every authenticated user can view their own Tier 1 events at `/account/activity`. Admin URL traces (Tier 2) are hidden from user-facing view.

**Counsel access to the audit:** Counsel accounts are blocked from viewing any activity log — including their own. The endpoints return HTTP 403 with an explanatory message. This protects the audit trail from a compromised counsel session and is called out in draft §8b, item 22 below (Counsel Terms of Access).

**Key legal questions for counsel:**
1. Confirm the Privacy Policy adequately discloses IP + user-agent capture on login and admin activity as personal data under GDPR/CCPA.
2. Confirm the "audit rows retained after account deletion" carve-out is defensible under a "legitimate interests" balancing test (Article 6(1)(f) GDPR) and CCPA's exception for legal compliance.
3. Decide whether counsel should countersign a short "Counsel Terms of Access" acknowledging their session is logged (see draft §8b item 22).
4. Decide whether the Board Member / Officer Agreement (draft #11) needs a "no expectation of privacy on admin console" clause acknowledging admin URL trace.

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
- **International data transfers** rely on the 2021 Standard Contractual Clauses (SCCs) plus the United Kingdom International Data Transfer Agreement (UK IDTA).
  Every sub-processor data processing agreement (DPA) (§5) must incorporate these where applicable.
- **DPO** — designate `dpo@birthright.live` when the threshold criteria
  in GDPR Art. 37 are met (systematic large-scale monitoring or large-
  scale processing of special-category data).
- **EU VAT** — evaluate One-Stop-Shop registration for cross-border B2C
  sales of digital services (workshops, subscriptions) and physical
  goods.
- **Supervisory authority** — publish the right of EU/UK residents to
  lodge complaints with local supervisory authorities.

---

## 8b. Draft documents — public download links

| # | Draft | Category | Public download |
|---|---|---|---|
| 1 | **Counsel Review Plan — Segmented Effort & Time Budget** | Briefing | https://birthright.live/api/legal/drafts/00-counsel-review-plan |
| 2 | **Counsel User Guide — Minimise Billable Time** | Briefing | https://birthright.live/api/legal/drafts/00a-counsel-user-guide |
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

### 8b.1 Recommended operative language for each draft — key clauses to modify or ratify

Below is a first-draft summary of the operative language for each drafted agreement. Each clause is stated as recommended language for counsel to redline, tighten, or ratify. Full draft text lives at the plaintext URL above.

**1. Terms of Service** — Recommended core clauses:
- **Acceptance.** *"By creating an account or making a purchase on birthright.live, you agree to these Terms of Service and to our Privacy Policy."*
- **Service description.** Platform offers workshops, community access, digital and physical goods, and (as applicable) facilitator services. Not a substitute for medical, therapeutic, or legal advice.
- **Age.** Users must be 18 or older; parental consent required for minors under 18 where lawful.
- **Prohibited conduct.** Harassment, unauthorized commercial solicitation, scraping, and circumvention of platform controls.
- **Termination.** Foundation may suspend or terminate for material breach of these Terms or the Community Standards.
- **Limitation of liability.** Cap at aggregate fees paid in the prior 12 months, subject to jurisdictional limits.
- **Governing law and venue.** [To be set by counsel once entity formation is complete.]
- **Dispute resolution.** Informal negotiation → mediation → binding arbitration; class-action waiver only if permitted by counsel and disclosed prominently.

**2. Privacy Policy** — Recommended core clauses:
- **Categories of data collected** (account, PII, transactional, health-adjacent journaling, uploaded files, AI conversation logs, cookies/analytics, **security-audit data including IP address, user-agent, timestamps of every login and every admin session URL**).
- **Purposes of processing** (service delivery, communications, billing, moderation, analytics, legal compliance, **security monitoring and fraud prevention**).
- **Legal bases** (contract performance, consent for marketing, **legitimate interests (GDPR Article 6(1)(f)) for security audit logging**).
- **Sharing with sub-processors** (Stripe, Resend, Printful, Lulu, Google, Anthropic, Cloudflare, Emergent) with links to each vendor's policy.
- **Retention schedule** by data category, including:
  - Security audit logs (`user_activity_log`): **365 days rolling**
  - Counsel activity logs (`counsel_activity_log`): retained until manual admin purge
  - Counsel review sign-offs (`counsel_review_status`): retained indefinitely as a durable audit record
- **User rights** — access, correction, deletion, portability, objection, opt-out of sale/share (California Consumer Privacy Act / California Privacy Rights Act — CCPA / CPRA).
- **Erasure carve-out for audit logs** — *"When you delete your account, we will remove your personal profile and account records. Certain security audit entries (records of your sign-ins, password changes, and consent to legal agreements) will be retained for 365 days as part of our security-audit log, on the basis of our legitimate interests in maintaining a defensible security posture and complying with legal obligations. After 365 days, these entries are automatically purged."*
- **International transfers** — Standard Contractual Clauses (SCCs) for European Union / United Kingdom users.
- **Contact** — privacy@birthright.live plus mailing address.

**3. Cookie & Tracking Notice** — Recommended core clauses:
- Categories: strictly necessary, functional, analytics, and marketing.
- **Consent** — Opt-in banner required for non-strictly-necessary cookies in the European Union and United Kingdom. "Reject all" option must be as prominent as "Accept all."
- Vendor list with cookie names, purposes, retention.
- Instructions to withdraw consent and clear cookies.

**4. Universal Indemnification & Hold-Harmless Agreement** — Recommended core clauses:
- **Acknowledgement of nature of the work.** *"I understand that Birthright's workshops, community, and content address relational, attachment, and repair themes and are not a substitute for medical, mental-health, or crisis care."*
- **Release and hold-harmless** for foreseeable participation risks.
- **Indemnity to foundation** for injuries or claims arising from participant's own conduct.
- **No release for gross negligence or willful misconduct** — carved out explicitly.
- **Consent to emergency care** and to platform contacting an emergency contact if provided.
- **Governing law and venue.**

**5. Facilitator Services Agreement plus Intellectual-Property Assignment** — Recommended core clauses:
- **Independent contractor** status; facilitator responsible for their own taxes and insurance.
- **Scope of services** — deliver workshops per program materials, adhere to Community Standards.
- **Compensation** — up to 65% of Birthright-intellectual-property workshop revenue; monthly payout per §9 policy.
- **Intellectual-property assignment or exclusive license** for materials produced under Birthright's brand while performing services; facilitator retains pre-existing intellectual property.
- **Confidentiality** — participant lists, minor children's names, mental-health disclosures.
- **Non-disparagement** (mutual).
- **Termination** — 30 days for convenience; immediate for cause.
- **Insurance** — facilitator to maintain professional liability at a minimum coverage to be set by counsel.

**6. Artist Consignment / Gallery Partner Agreement** — Recommended core clauses:
- **Consignment relationship** — artist retains title to unsold works.
- **Warranty of originality and authenticity** — artist represents each work is original and unencumbered.
- **Revenue-share model** — 20% foundation gift added at checkout (not deducted from artist).
- **Right of first refusal** on commissioned commissions? [Counsel to decide.]
- **Termination and return of unsold work** upon 30 days' notice.
- **Intellectual-property indemnity** from artist for third-party rights claims.

**7. Vendor Supplier / Dropship Agreement** — Recommended core clauses:
- **Ordering flow** — buyer purchases on birthright.live; vendor is notified; vendor fulfills directly.
- **Wholesale pricing** and payment schedule.
- **Product warranty** — vendor warrants goods are as described.
- **Product-liability indemnity** — vendor indemnifies foundation for product-defect claims.
- **Compliance representations** — vendor represents compliance with applicable labor, food-safety (where relevant), and consumer-protection laws.
- **Insurance** — vendor to maintain product liability at a level set by counsel.

**8. Community Partner Referral Agreement** — Recommended core clauses:
- **Independent-contractor status.**
- **Commission** — 25% of referred revenue with attribution via referral code.
- **Payout threshold** — $50 minimum, paid monthly.
- **Internal Revenue Service Form W-9 requirement** — no payout without a completed W-9; Form 1099-NEC issued annually where required.
- **No misrepresentation** — referrer may not make claims beyond Birthright's own marketing copy.
- **Termination** at will, subject to earned but unpaid commissions.

**9. Sponsorship Agreement / Sponsor Recognition Consent** — Recommended core clauses:
- **Non-deductibility disclosure** — *"Birthright Foundation has not yet submitted or received Internal Revenue Service 501(c)(3) determination. This contribution is not currently tax-deductible as a charitable donation. No representation is made about future tax status."*
- **Public recognition consent** — sponsor opts in explicitly to be named or displayed publicly; may opt out at any time.
- **Sponsor Partner status** — auto-elevation at $100 one-time or $25/mo × 3+ months; presenting sponsor at $5,000 or $250/mo. Renews annually; auto-degrades to Alumni Contributor after 18 months of no renewed contribution.
- **No quid-pro-quo** — sponsorship does not confer editorial control, governance rights, or preferential treatment on the platform.
- **Refund policy** — pledges may be withdrawn before payment is confirmed; after payment, refunds are at the foundation's discretion consistent with law.

**10. Sliding-Scale & Scholarship Terms** — Recommended core clauses:
- **Eligibility** — self-attested financial need at time of application.
- **No formal means-testing** — foundation reserves discretion.
- **Non-transferability** of scholarship seats.
- **Confidentiality** of scholarship status among participants.

**11. Board Member / Officer Agreement plus Directors and Officers (D&O) Coverage** — Recommended core clauses:
- **Fiduciary duties** — duty of care, loyalty, and obedience to mission.
- **Conflict-of-interest disclosure** — required at appointment and annually.
- **Indemnification by foundation** for acts within scope of duties, subject to statutory limits and directors and officers (D&O) insurance policy.
- **Confidentiality** — board deliberations, personnel matters, participant data.
- **Term and removal** — three-year staggered terms; removal with two-thirds vote of remaining board.
- **No expectation of privacy on the admin console** — *"You acknowledge that all activity on the Birthright administrative console (URLs under `/admin/*`, mutating API calls, sign-ins from admin accounts) is automatically logged to an internal audit trail visible to other administrators and to Board members with governance oversight duties. This logging is part of the Foundation's security posture and is retained for 365 days on a rolling basis. You have no expectation of privacy in these logs when acting in your administrative capacity."*

**12. Foundation Working-Group Volunteer Agreement** — Recommended core clauses:
- **Volunteer status** — not an employee; no compensation beyond reimbursed expenses.
- **Confidentiality** and code-of-conduct affirmations.
- **Intellectual-property assignment** for volunteer contributions produced under Birthright's brand.
- **Waiver of injury claims** consistent with state volunteer-protection acts.

**13. Ombudsman Charter** — Recommended core clauses:
- **Independence** — ombudsman reports to the board, not to the executive director.
- **Confidentiality** — communications with ombudsman are confidential except where safety, criminal conduct, or mandatory reporting triggers apply.
- **Scope** — disputes among members, complaints against facilitators or staff, and integrity concerns.
- **Remedies** — mediation, facilitated apology, corrective action recommendations to leadership.

**14. Content Moderation & Community Standards Policy** — Recommended core clauses:
- **Prohibited content** — harassment, hate speech, doxxing, spam, unauthorized commercial solicitation, sexual content, disclosed minors' identities.
- **Enforcement ladder** — warning → temporary suspension → permanent removal.
- **Appeals** — one round of appeal to the ombudsman.
- **Transparency** — quarterly moderation summary published anonymously.

**15. Refund & Returns Policy (Public)** — Recommended core clauses:
- **Digital products** — non-refundable once accessed, except where required by law.
- **Physical goods** — 30-day return for defect or non-conformance; buyer pays return shipping unless foundation's error.
- **Workshops** — full refund up to 7 days before start; 50% up to 48 hours; forfeited thereafter unless a documented emergency, at foundation's discretion.
- **Sponsorships** — see §9 above.

**16. Sales-Tax Registration Plan** — Recommended core clauses (internal plan document):
- Nexus analysis by state — physical, economic (sales thresholds), and click-through nexus.
- Timeline for sales-tax registration in priority states.
- Cadence for periodic re-analysis as revenue grows.

**17. Trademark Filings Plan** — Recommended core actions:
- File United States Patent and Trademark Office (USPTO) applications for "birthright" wordmark (Classes 41 — education; 45 — social services; 25 — apparel).
- File for the flame-plus-wordmark logo as a composite mark.
- Consider filing key taglines (e.g., "Secure connection is your birthright") as separate marks.

**18. Copyright Registration Strategy** — Recommended core actions:
- Register all published workshop curricula with the United States Copyright Office within 90 days of first publication.
- Register the founder's book manuscript prior to any distribution.
- Aggregate registration of website content on a rolling annual basis.

**19. Data Processing Agreement Template** — Recommended core clauses:
- **Purpose limitation** — sub-processor may process only for the specified services.
- **Technical and organizational measures** — encryption at rest, encryption in transit, access controls, breach-notification obligations.
- **Sub-processor onboarding** requires prior written notice and right to object.
- **International-transfer mechanism** — Standard Contractual Clauses (SCCs) for European Union / United Kingdom transfers.
- **Term** — coterminous with underlying services agreement.

**20. Nonprofit Governance Bundle** — Recommended documents:
- **Articles of Incorporation** — purpose clause narrow enough to satisfy IRS Section 501(c)(3) but broad enough to cover workshops, community, and publications.
- **Bylaws** — board composition, meeting cadence, officer roles, indemnification.
- **Conflict of Interest (COI) Policy** — annual disclosure, recusal procedure.
- **Whistleblower Policy** — protected reporting channel to the ombudsman and to the board chair.
- **Document Retention Policy** — schedules by record category with legal-hold override procedure.

**21. State Charitable Solicitation Registration Plan** — Recommended core actions:
- Prioritize registration in California, New York, Florida, Illinois, Pennsylvania, and Texas ahead of any public fundraising campaign.
- Register through the Unified Registration Statement where accepted; state-specific forms elsewhere.
- Track annual renewals and financial reporting thresholds.

**22. Counsel Terms of Access (new — recommended)** — Recommended core clauses:
- **Scope of access.** Foundation grants counsel a personal, non-transferable, read-only account (role `readonly_admin`) for the sole purpose of reviewing the platform in support of the engagement.
- **Session logging acknowledgement.** *"You acknowledge that every request made from your session is logged to an internal audit trail (URL, HTTP method, response status, IP address, user-agent, and timestamp). This log is visible to Foundation administrators; you are not permitted to view or modify it from your own session."*
- **No modification of platform data.** All modification attempts (POST/PUT/PATCH/DELETE) are automatically rejected by server-side middleware; counsel represents they will not attempt to circumvent this control.
- **Confidentiality.** Counsel treats all data observed on the platform as confidential and privileged and will not extract, screenshot, or share any member, partner, or transaction data without prior written consent from the Foundation, except as required by applicable rules of professional conduct.
- **Termination and credential rotation.** Access terminates at the conclusion of the engagement; the Foundation will rotate or archive the counsel credential at that time.
- **Non-privileged nature of the audit log.** The audit log is a business record, not privileged work product; the Foundation may produce it if compelled in litigation or by regulator.

## 5. Third-Party Integrations (Sub-processors)

| Vendor | Purpose | Data shared | Contract / data processing agreement (DPA) in place? |
|---|---|---|---|
| **Stripe** (`stripe`, `emergentintegrations.payments.stripe`) | Payment processing, Stripe Connect (planned for artist payouts) | Buyer name, email, shipping address, order metadata | Stripe standard TOS + connected-account terms. **No custom DPA.** |
| **Resend** (`resend`) | Transactional email (receipts, workshop confirmations, vendor reorders) | Buyer name, email, order details, uploaded file attachments | Resend TOS. **No custom DPA.** |
| **Printful** (`printful_client`) | Print-on-demand apparel/prints fulfillment | Buyer name, address, product variant | Printful merchant TOS. |
| **Lulu** (`lulu_client`) | Print-on-demand book fulfillment | Buyer name, address, product | Lulu merchant TOS. |
| **Google Gemini** (via Emergent LLM Key, model `gemini-3.1-flash-image-preview`) | AI image generation, image captioning, vision analysis | Product descriptions, images | Emergent LLM key umbrella TOS. **Confirm Google's data-retention terms for API use.** |
| **Anthropic Claude** (via Emergent LLM Key, model `claude-sonnet-4-5`) | Help Assistant, prompt analysis for image queue | Platform DB context (team bios, product catalog), user questions | Same as above. |
| **Cloudflare** | DNS, email routing (`hello@birthright.live` → Gmail), DDoS mitigation | Domain traffic metadata, email routing metadata | Cloudflare TOS. |
| **Formester** (via 7C's Farmstead custom-order form) | Third-party form submission for vendor reorders | Buyer name, email, phone, shipping address, order details | 7C's has a merchant relationship with Formester; birthright has no direct contract. |
| **Emergent** (hosting platform) | Application hosting, continuous integration and continuous deployment (CI/CD) | All of the above (they host the environment) | Emergent platform TOS. |
| **GitHub** (via Emergent's "Save to Github") | Source code hosting | Source code, not customer data | GitHub TOS. |

**Key legal questions:**
1. Which of these require a written data processing agreement (DPA) under General Data Protection Regulation (GDPR) or California Consumer Privacy Act (CCPA)?
2. Sub-processor list needs to be published in the privacy policy.
3. Cross-border data transfer mechanisms (SCCs) for EU users if applicable.

---

## 6. Intellectual Property Landscape

### 6.1 Brand — logos, wordmark, and marks in active use

#### Logos (visual marks)
- **Primary composite mark:** birthright wordmark with the interlocking ember-and-teal flame device and the tagline lockup "SECURE BONDS > THRIVE." Embedded below (also stored at `/app/backend/legal_docs/brand_assets/logo_composite.jpeg`).
- **Mission-statement flame lockup:** the gold flame icon paired with the italic mission-statement typography ("Secure bonds are our birthright."). Embedded below (also stored at `/app/backend/legal_docs/brand_assets/mission_statement.jpeg`).

*(Both images are embedded in this document under §6.1a below and are considered the current canonical visual identity as of the date of this briefing.)*

#### Wordmark / textual marks
- **birthright** (lowercase wordmark, primary)
- **birthright.live** (domain-mark)
- **birthright Foundation** (organizational mark, pending entity formation)

#### Taglines and marks in active public use across birthright.live

The following short-form marks appear on public pages of birthright.live (URLs listed for counsel to verify context). Each is in use in commerce and is a candidate for trademark protection under the Trademark Filings Plan (draft §8b, item 17).

| # | Mark / tagline | Where it appears | Nature of use |
|---|---|---|---|
| 1 | **"Secure bonds are your birthright."** | Homepage hero and marketing rotations | Consumer-facing brand promise (second-person) |
| 2 | **"We are the practice ground."** | Practice page hero; about-us section | Positioning line for the platform's core offering |
| 3 | **"A practice that grows with you"** | Practice page sub-hero; membership pages | Descriptor for the recurring/subscription nature of the work |
| 4 | **"Born for connection"** | Homepage; about section; brand imagery | Origin-story tagline |
| 5 | **"Secure bonds are our birthright."** | Mission statement page; about page | Corporate mission statement (first-person plural) |
| 6 | **"A practice, not a curriculum"** | Practice page; how-it-works section | Positioning — differentiates from typical program/course model |
| 7 | **"Made to live with the work"** | Shop / Founder Collection page; product marketing | Product-line tagline for merchandise and everyday-carry goods |
| 8 | **"Artists in the room"** | Gallery page; artist partner pages | Positioning for the artist-partner program |
| 9 | **"Help someone claim their birthright."** | Sponsorship page; general sponsorship call-to-action | Fundraising / sponsorship marketing line |
| 10 | **"The people behind the work."** | Board / team page; leadership section | Governance / people-page heading |
| 11 | **"Help us build the foundation."** | Foundation sponsorship pages; capital-fundraising calls-to-action | Founding-supporter and capital-campaign marketing line |
| 12 | **"Communities of practice"** | Gather / community page; local-node pages | Positioning for the community-partner and local-node offering |

#### Prior single-line marks (retained from earlier brief; still in use)
- **"You are the founder of your own love story"** — legacy tagline; verify current usage before filing
- **"Secure connection is your birthright"** — precursor to Mark #1 above; verify overlap
- **"The bond is the cure"** — motto used in practice-page copy
- **"Repair is older than rupture"** — motto used on practice-page copy
- **"We are created for connection"** — precursor to Mark #4 above; verify overlap

#### Legal status of the above
- **No trademark filings yet.** All marks above are used in commerce but unregistered.
- **Recommended filings** (see also draft §8b, item 17 — Trademark Filings Plan):
  - USPTO Class 41 (education services — workshops, community of practice)
  - USPTO Class 45 (social services — attachment / connection support)
  - USPTO Class 25 (apparel — Founder Collection merchandise)
  - USPTO Class 09 (downloadable software, digital media) — pending platform strategy
- **Priority for filing:** Marks 1, 2, 5, 6, 8 have the strongest source-identifier character and are most exposed to third-party adoption. Marks 3, 4, 7, 9, 10, 11, 12 are descriptive-suggestive and should be evaluated for distinctiveness with counsel.
- **Composite logo mark** (birthright wordmark + flame device) should be filed as a single composite mark in Classes 41 and 45.
- **International (Madrid Protocol)** filing to be considered after United States registration, given EU customer base already visible in traffic.

### 6.1a Embedded brand assets

*The two images below are the canonical current visual identity as of the date of this briefing. Counsel may reproduce them for filing-preparation purposes.*

**Figure 1 — Primary composite mark (wordmark + flame device + "SECURE BONDS > THRIVE" tagline lockup):**

![Primary composite mark — birthright wordmark, flame device, and SECURE BONDS > THRIVE tagline lockup](brand_assets/logo_composite.jpeg)

**Figure 2 — Mission-statement flame lockup ("Secure bonds are our birthright."):**

![Mission statement lockup — gold flame icon and "Secure bonds are our birthright." italic typography](brand_assets/mission_statement.jpeg)

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
2. **Privacy Policy** (with sub-processor list, retention schedule, data subject access request (DSAR) workflow)
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

### Admin (requires admin account — a read-only counsel account is now provisioned; see §13 for credentials)
- Admin hub: `https://birthright.live/admin`
- Users: `https://birthright.live/admin/users`
- Products: `https://birthright.live/admin/products`
- Partners: `https://birthright.live/admin/partners`
- Sponsor campaigns (includes pledges, sponsor partner directory, 18-month degrade sweep): `https://birthright.live/admin/campaigns`
- Legal document downloads: `https://birthright.live/admin/legal-docs`
- Foundation roles: `https://birthright.live/admin/foundation-roles`
- Foundation applications: `https://birthright.live/admin/foundation-applications`
- Ombudsman queue: `https://birthright.live/admin/ombudsman`
- Disputes: `https://birthright.live/admin/disputes/*`
- Refunds: `https://birthright.live/admin/refunds`
- Payouts: `https://birthright.live/admin/payouts`
- Legal agreements manager: `https://birthright.live/admin/legal/agreements`
- AI usage: `https://birthright.live/admin/ai-usage`
- Reports: `https://birthright.live/admin/reports`
- **Counsel review checklist (per-doc manual + auto tracking):** `https://birthright.live/admin/counsel-review`
- **Counsel activity log (admin-only; counsel blocked from own log):** `https://birthright.live/admin/counsel-activity`
- **User activity & admin trace (Tier 1 + Tier 2 audit view):** `https://birthright.live/admin/user-activity`

### User-facing (any authenticated user)
- **My activity (security events on my own account):** `https://birthright.live/account/activity`

### API endpoints of legal interest (JSON responses inspectable at these URLs when authenticated)
- Terms/indemnification versions: `GET /api/legal/indemnification/active`
- Signatures: `GET /api/legal/indemnification/versions` (admin)
- Audit log: `GET /api/audit/*` (admin)
- Outbound emails: `GET /api/system-admin/emails` (admin)

---

## 12. Suggested Priority for Counsel Engagement

Ordered by risk exposure today:

1. **Terms of Service + Privacy Policy** — every purchase and account creation currently happens without a signed agreement. Highest immediate exposure.
2. **Entity formation + tax status** — driving decision for everything else (donation deductibility, unrelated business income taxation (UBI), board indemnification).
3. **Real indemnification agreement text** — the placeholder currently disclaims itself as "not legal advice."
4. **Facilitator + Artist + Vendor agreements** — real money flows to third parties today with no written contract.
5. **Sales-tax nexus + charitable-solicitation registration analysis** — state-by-state.
6. **Trademark filings** for the birthright wordmark and flame logo.
7. **Board/Officer agreements + D&O policy** before recruiting real (non-sample) board members to replace the current placeholders.
8. **Data privacy framework** (privacy policy, data processing agreements (DPAs), data subject access request (DSAR) workflow).
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
- **A live read-only admin account on the production platform** (already provisioned — see credentials below)
- Access to a `git`-tracked copy of the source code including all router files referenced above (`/app/backend/routers/*.py`)
- Sample data exports for review

### Read-only counsel review account

Counsel may sign in to inspect every admin and public surface on the platform. All modification attempts (POST / PUT / PATCH / DELETE requests) are rejected by server-side middleware with HTTP 403; a persistent "Counsel review · read-only" banner appears at the top of every page during the session.

- **Sign-in URL:** `https://birthright.live/login`
- **Email:** `counsel@birthright.live`
- **Password:** `counsel-review-2026`
- **Role:** `readonly_admin`

**One important disclosure:** every request from the counsel session (URL visited, HTTP method, response status, IP address, user-agent, and timestamp) is logged to an internal audit trail visible to Foundation administrators. This is a normal security measure and is described more fully in §4b and in the recommended Counsel Terms of Access (draft §8b item 22). Counsel accounts are themselves blocked from viewing the audit log, so a compromised counsel session cannot inspect or alter its own record.

A companion **review checklist** at `https://birthright.live/admin/counsel-review` (visible to counsel and admin) lets counsel check off each document as reviewed with initials and notes; that record persists indefinitely as the durable sign-off trail.

Please notify engineering (via the executive director) when the review is complete so the account can be rotated or archived.

Please direct clarifying questions to James, who will loop in engineering as needed.
