"""Legal drafts v2 — plain-English first drafts for every legal instrument.

Rewrites the 22 legal instruments under /app/backend/legal_docs/ using
accepted standard boilerplate, kept as short as possible while meeting
full disclosure. Regenerates the manifest and (via a second script)
the .docx versions.

The prior v1 generator produced usable placeholders. This v2 produces
first drafts a lawyer can start from — not placeholders.

Run:
    python /app/backend/scripts/generate_legal_drafts_v2.py
    python /app/backend/scripts/eu_compliance_and_docx.py   # rebuild .docx

Every draft opens with a "first draft — pending counsel ratification"
banner (kept legally honest without calling itself a placeholder) and,
where relevant, closes with a compact EU/UK compliance addendum.
"""
from pathlib import Path
from datetime import datetime

OUT = Path(__file__).resolve().parent.parent / "legal_docs"
OUT.mkdir(parents=True, exist_ok=True)

# Kept as a blockquote so the public renderer can strip it into an
# amber banner instead of showing it inline.
DISCLAIMER_TOP = """> **FIRST DRAFT — PENDING COUNSEL RATIFICATION**
>
> This document is a first draft prepared for outside counsel review.
> It uses accepted standard language for its type and is intended to
> be published in this form after ratification. Until counsel signs
> off, treat any specific figure, warranty, or jurisdictional choice
> as tentative.
>
> Version: February 2026 · Birthright Foundation (birthright.live) ·
> Executive Director: Amanda Reagan · Contact: legal@birthright.live
"""

DISCLAIMER_BOTTOM = """
---
*First draft — pending counsel ratification. Comments to
legal@birthright.live.*
"""

EU_ADDENDUM = """

---

## EU / UK Compliance Addendum

Where an EU or UK resident's mandatory local rights conflict with this
document, the local rules prevail. Key points:

- **GDPR (EU) 2016/679** and **UK GDPR** govern personal-data
  processing. Lawful bases: contract necessity, legitimate interests
  (with opt-out), consent (marketing / non-essential cookies), and
  legal obligation.
- **ePrivacy Directive (2002/58/EC)** — non-essential cookies require
  prior opt-in consent (see our Cookie Notice).
- **Consumer Rights Directive (2011/83/EU)** — 14-day right of
  withdrawal on distance sales of goods and most digital services.
  Fully-performed digital content with prior consent may lose that
  right.
- **Digital Services Act (Reg. 2022/2065)** — community features
  (posts, DMs, disputes) fall in scope. Single point of contact:
  eu-contact@birthright.live.
- **Cross-border transfers** — EU SCCs (2021/914) + UK IDTA with a
  transfer-impact assessment per sub-processor.
- **DSAR window** — 30 days (extendable to 90) at
  privacy@birthright.live.
- **Supervisory authority** — EU: your national DPA
  (https://edpb.europa.eu). UK: ICO (https://ico.org.uk).
"""


# ---------------------------------------------------------------------------
# Every entry: (slug, display_name, category, body_markdown, add_eu_addendum)
# ---------------------------------------------------------------------------
DOCS = [

# ============================================================
# 01 · TERMS OF SERVICE
# ============================================================
("01-terms-of-service", "Terms of Service (Draft)", "Public-facing", """
# Terms of Service

**Effective date:** February 2026 · **Entity:** Birthright Foundation
("Birthright," "we," "us"). Contact: hello@birthright.live.

## 1. Agreement
By creating an account, buying anything, registering for a workshop, or
posting content on birthright.live (the "Services"), you agree to these
Terms and to our [Privacy Policy](/legal/privacy) and
[Cookie Notice](/legal/cookie-notice). If you do not agree, do not use
the Services.

## 2. Eligibility
You must be at least eighteen (18) years old to create an account,
purchase, or become a partner. By using the Services you confirm you
meet that requirement.

## 3. Your Account
Keep your password confidential. You are responsible for everything
done through your account. Notify us immediately at
security@birthright.live if you suspect unauthorized use.

## 4. What We Sell
- **Products** (physical goods) — fulfilled by Birthright, print-on-
  demand partners (Printful, Lulu), or vendor partners. See our
  [Refund & Returns Policy](/legal/refunds).
- **Workshops** (live and recorded educational sessions). Sliding-scale
  pricing may apply — see [Scholarship Terms](/legal/scholarships).
- **Subscriptions** — recurring charges continue until you cancel from
  your dashboard. Cancellation is prospective; paid periods are
  non-refundable except where law requires otherwise.
- **AI Wallet credits** — prepaid, non-transferable, non-refundable
  once consumed.
- **Donations & sponsorships** — tax deductibility depends on our
  federal status at the time of your gift. Ask your tax advisor.

## 5. Your Conduct
Do not (a) impersonate anyone, (b) upload unlawful, harassing, or
infringing content, (c) scrape or reverse-engineer the Services,
(d) attack our security or availability, (e) spam our members, or
(f) violate any applicable law.

## 6. Your Content
You keep ownership of what you post (reviews, community posts, gallery
work, uploads). You grant Birthright a worldwide, non-exclusive,
royalty-free, sublicensable license to host, display, format, and
redistribute your content **for the purpose of operating and promoting
the Services**. You represent that you have the rights to post it.

## 7. Our Content & Marks
"Birthright Foundation," the flame mark, and our curricula, articles,
photographs, and videos are protected by copyright and trademark. We
grant you a limited, revocable licence to view them for personal,
non-commercial use.

## 8. AI Features
Our Help Assistant and image tools are AI-assisted. Outputs are
generated on request, may be imperfect, and are not professional
advice. You are responsible for any use you make of AI outputs.

## 9. Payments
Payments go through Stripe. We never see your full card number. We may
share order and shipping data with the fulfilling partner (Printful,
Lulu, or the named vendor) strictly to fulfil your order.

## 10. Termination
You may close your account any time. We may suspend or close accounts
that violate these Terms, on notice where practicable. Sections 6, 7,
11, 12, and 13 survive termination.

## 11. Warranty Disclaimer
The Services are provided **"as is"** without warranties of any kind,
express or implied, including merchantability, fitness for purpose,
and non-infringement, to the fullest extent permitted by law.

## 12. Limitation of Liability
To the fullest extent permitted by law, Birthright's aggregate
liability arising out of or relating to the Services is limited to
the greater of (a) the amount you paid us in the twelve (12) months
before the event giving rise to the claim, or (b) US $100. We are not
liable for indirect, incidental, consequential, or punitive damages.

## 13. Indemnity
You agree to defend and indemnify Birthright against claims arising
from your breach of these Terms or your unlawful use of the Services.

## 14. Governing Law & Disputes
These Terms are governed by the laws of the State of North Carolina,
USA, without regard to conflict-of-laws rules. Disputes are subject
to the exclusive jurisdiction of the state and federal courts sitting
in Mecklenburg County, North Carolina, except where local consumer
law grants you a different forum.

## 15. Changes
We may update these Terms. Material changes take effect thirty (30)
days after we post them and (for account holders) email you. Continued
use after the effective date is acceptance.

## 16. Contact
Legal: legal@birthright.live · General: hello@birthright.live ·
Mail: 2148 W Farill Dr, Phoenix, AZ 85015, USA.
""", True),


# ============================================================
# 02 · PRIVACY POLICY
# ============================================================
("02-privacy-policy", "Privacy Policy (Draft)", "Public-facing", """
# Privacy Policy

**Effective date:** February 2026. This policy explains what personal
information Birthright Foundation collects, why, how we protect it,
and your choices. Contact: privacy@birthright.live.

## 1. What We Collect
- **From you:** name, email, phone, shipping/billing address, account
  password (stored as a bcrypt hash), community posts, dispute
  messages, files you upload for vendor orders, workshop registrations,
  and questions you ask our AI Help Assistant.
- **Automatic:** IP address, device and browser metadata, referring
  URL, pages viewed. See our [Cookie Notice](/legal/cookie-notice).
- **From third parties:** Stripe payment metadata (charge id, last-4,
  status — never the full card number or CVV); Cloudflare routing
  metadata.
- **Partners:** if you sign up as a partner, we also collect payout
  method (encrypted; only type + last-4 kept in plaintext) and, when
  US thresholds require, W-9 information.

## 2. How We Use It
- Operate the Services (accounts, checkout, workshops, community).
- Communicate with you (receipts, reminders, dispute replies,
  newsletter — only with your consent).
- Fulfil orders (share address with Printful, Lulu, or the vendor).
- Pay partners and reconcile earnings.
- Improve the Services (analytics, image-caption search, security).
- Comply with law.

## 3. Legal Bases (EU / UK Users)
Contract necessity, legitimate interests (balanced by your opt-out),
your consent (marketing and non-essential cookies), and legal
obligation.

## 4. Who We Share With
- **Payment:** Stripe.
- **Fulfilment:** Printful, Lulu, and the specific vendor of your
  order.
- **Email:** Resend.
- **Hosting & security:** Emergent, Cloudflare, MongoDB Atlas.
- **AI features:** Anthropic (Claude) and Google (Gemini/Nano Banana).
  We send only the content needed to answer your request, not your
  account credentials.
- **Legal & safety:** when required by law or to protect people.

We do **not** sell your personal information.

## 5. Retention
- Account data: while your account is active + 3 years.
- Order data: 7 years (tax).
- Community posts: until you delete them or your account.
- Security-audit logs: 365 days.
- Marketing consent records: while your consent is active + 2 years.

## 6. Your Rights
Anywhere: request access, correction, deletion, or export at
privacy@birthright.live. We respond within 30 days.

EU/UK/CA residents additionally have the right to object to
processing, restrict processing, and complain to your local
supervisory authority (EU: https://edpb.europa.eu · UK:
https://ico.org.uk · California: https://oag.ca.gov/privacy).

California residents: we do not "sell" or "share" personal
information under the CCPA; we honour Global Privacy Control signals
where technically feasible.

## 7. Security
TLS in transit; encryption at rest for payout data; role-based
access; bcrypt hashing for passwords; audit logging of admin actions
and security-relevant user events. No system is perfectly secure — we
disclose confirmed material breaches without undue delay.

## 8. Children
Not for anyone under 18. If you believe a minor has an account,
email privacy@birthright.live and we will remove it.

## 9. Automated Decisions
We do not use automated decision-making that produces legal effects
about you. AI features are labelled as such and remain human-in-the-
loop.

## 10. Changes
Material changes take effect 30 days after posting; we email
account-holders as well.

## 11. Contact
privacy@birthright.live · Mail: 2148 W Farill Dr, Phoenix, AZ 85015.
DPO/EU rep contact (once designated): dpo@birthright.live.
""", True),


# ============================================================
# 03 · COOKIE & TRACKING NOTICE
# ============================================================
("03-cookie-notice", "Cookie & Tracking Notice (Draft)", "Public-facing", """
# Cookie & Tracking Notice

**Effective date:** February 2026. This notice explains the cookies
and similar technologies we use on birthright.live.

## 1. Categories We Use
- **Strictly necessary** (always on) — sign-in session, shopping cart,
  CSRF protection, load balancing. Cannot be disabled without breaking
  the site.
- **Preferences** — remember your consent choices and locale.
- **Analytics** (only with your consent) — anonymised page-view and
  performance metrics so we can improve the site.
- **No advertising cookies.** We do not run behavioural ad networks.

## 2. Your Controls
- The consent banner on your first visit lets you accept all or
  reject non-essential cookies. You can change your choice any time
  via **Cookie Settings** in the site footer.
- Your browser lets you delete cookies or block them by site.
- We honour Global Privacy Control (GPC) signals.

## 3. Third-Party Providers
| Purpose            | Provider        | Cookie type      |
|--------------------|-----------------|------------------|
| Payment            | Stripe          | Necessary        |
| Session security   | Cloudflare      | Necessary        |
| Product analytics  | (Self-hosted)   | Analytics (opt-in) |

## 4. Retention
Session cookies expire when you close the browser. Persistent cookies
expire in ≤ 12 months. Consent records: kept for 24 months to prove
compliance.

## 5. Contact
privacy@birthright.live.
""", True),


# ============================================================
# 04 · INDEMNIFICATION / HOLD-HARMLESS
# ============================================================
("04-indemnification-hold-harmless", "Universal Indemnification & Hold-Harmless Agreement (Draft)", "Public-facing", """
# Universal Indemnification & Hold-Harmless Agreement

**Version:** 1.0 · **Effective date:** February 2026. This
agreement supplements the Terms of Service and applies to workshop
participants, partners, and volunteers.

## 1. Voluntary Participation
Workshops, materials, community events, and partner services are
educational and self-development in nature. You participate at your
own discretion and are solely responsible for your physical,
emotional, and psychological wellbeing during and after
participation.

## 2. No Professional Advice
Content offered by Birthright, its facilitators, and its partners is
not a substitute for licensed mental-health, medical, legal, or
financial advice. If you need such advice, please consult a licensed
professional.

## 3. Hold Harmless
To the fullest extent permitted by law, you release and hold
harmless Birthright Foundation, its directors, officers, employees,
volunteers, facilitators, vendors, and community partners from any
claim, loss, or damage arising out of your participation, except
claims caused by our gross negligence or wilful misconduct.

## 4. Indemnity by You
You agree to defend and indemnify the parties in Section 3 against
third-party claims arising from your acts or omissions or from your
breach of this agreement.

## 5. Data & Privacy
Personal information you share in the course of participation is
governed by our [Privacy Policy](/legal/privacy).

## 6. Community Conduct
You agree to follow our
[Community Standards](/legal/community-standards) and to treat
facilitators, fellow participants, and partners with respect.

## 7. Versioning
This agreement is versioned. When we substantively change it, we
will notify you and ask you to review and accept the new version
before further participation.

## 8. Governing Law
Governed by the laws of the State of North Carolina, USA. Disputes
subject to the exclusive jurisdiction of courts sitting in
Mecklenburg County, NC.

**By signing (electronically or on paper) you confirm you have read
and accepted this agreement in its entirety.**
""", True),


# ============================================================
# 05 · FACILITATOR SERVICES AGREEMENT
# ============================================================
("05-facilitator-services-agreement", "Facilitator Services Agreement + IP Assignment (Draft)", "Partner agreements", """
# Facilitator Services Agreement

**Parties:** Birthright Foundation ("Birthright") and the facilitator
identified in the signature block ("Facilitator").

## 1. Independent Contractor Relationship
Facilitator is an **independent contractor**, not an employee, agent,
partner, or joint venturer of Birthright. Facilitator sets their own
schedule, uses their own methods, and is solely responsible for their
own taxes, insurance, and licences. Nothing in this agreement creates
an employment relationship.

## 2. Services
Facilitator will deliver Birthright-branded workshops as scheduled
through the platform. Each workshop's title, description, price,
seat count, and location will be recorded in the platform listing
and forms part of this agreement by reference.

## 3. Fees & Revenue Share
Facilitator earns **up to 65% of net workshop revenue** for
Birthright-IP workshops that Facilitator delivers, and **25%** on
sales attributed to their referral code from off-site channels,
unless otherwise agreed in writing. "Net" means gross revenue minus
processing fees, refunds, and taxes. Payouts run monthly when the
balance exceeds US $50.

## 4. Standards of Care
Facilitator will (a) deliver the workshop as described, (b) follow
Birthright's Community Standards, (c) hold a current professional
credential where required by state law, and (d) obtain any
personal-liability insurance customary for the practice.

## 5. Intellectual Property
- **Birthright IP** — the birthright curriculum, workbooks, brand,
  and platform tools are and remain Birthright's property. Facilitator
  is granted a non-exclusive licence to use them solely to deliver
  workshops under this agreement.
- **Facilitator-created materials** — where Facilitator creates
  slides, handouts, or worksheets specifically for a Birthright
  workshop and paid for out of workshop revenue, those materials are
  **assigned to Birthright** on creation (a "work made for hire"
  where applicable, and by present assignment otherwise). Facilitator
  retains a perpetual, non-exclusive licence to use them in their
  own practice outside Birthright-branded contexts.

## 6. Confidentiality
Facilitator will keep confidential (a) participant personal
information and (b) any Birthright non-public financial, product, or
strategic information. This obligation survives termination for
three (3) years, or indefinitely for participant personal data.

## 7. Term & Termination
Either party may terminate on 30 days' written notice, or
immediately for material breach or safeguarding concern.
Facilitator will complete workshops already scheduled unless
Birthright agrees otherwise.

## 8. Indemnity & Insurance
Facilitator will indemnify Birthright for third-party claims
arising from Facilitator's negligence or wilful misconduct in
delivering the workshops. Where required by local law, Facilitator
will maintain professional-liability insurance at customary limits
(no less than US $1,000,000 per claim, US $2,000,000 aggregate).

## 9. Non-solicitation
For 12 months after termination, Facilitator will not solicit
Birthright staff or contract facilitators for competing services.

## 10. Governing Law
North Carolina, USA. Disputes subject to exclusive jurisdiction of
courts in Mecklenburg County, NC.

## 11. Entire Agreement
This document, together with the signed IC acknowledgement, the
Universal Indemnification, and each workshop's platform listing,
is the entire agreement between the parties.
""", True),


# ============================================================
# 06 · ARTIST CONSIGNMENT / GALLERY PARTNER AGREEMENT
# ============================================================
("06-artist-consignment-agreement", "Artist Consignment / Gallery Partner Agreement (Draft)", "Partner agreements", """
# Artist Consignment / Gallery Partner Agreement

**Parties:** Birthright Foundation ("Birthright") and the artist
identified below ("Artist").

## 1. Relationship
Artist is an **independent contractor**. This agreement does not
create employment, joint venture, or agency. Artist retains full
ownership of their works and independently sets their studio process.

## 2. Consigned Works
Artist consigns to Birthright the works listed in the platform
gallery. Each work is described by title, medium, dimensions,
edition (if any), and Artist's list price. Title to consigned works
remains with the Artist until sale.

## 3. Pricing Model
The buyer pays the Artist's list price **plus a 20% Foundation gift**
added visibly at checkout. The full list price is remitted to the
Artist (less payment-processing fees); the 20% Foundation gift is
retained by Birthright. Artist may elect to absorb or waive the gift
by written notice.

## 4. Fulfilment
Artist ships each work directly from studio within seven (7) days of
sale. Birthright provides pre-paid shipping labels on request and
covers standard insurance up to declared value.

## 5. Returns
Because works are made-to-order or one-of-a-kind, returns are limited
to (a) damage in transit or (b) material misdescription. Claims must
be made within 14 days of delivery. See our
[Refund & Returns Policy](/legal/refunds).

## 6. Intellectual Property & Publicity
Artist retains all copyright in their works. Artist grants Birthright
a non-exclusive, royalty-free licence to reproduce images and short
excerpts of the works solely to (a) list them for sale and (b)
promote the Artist and Birthright programme through website, email,
and social channels. Any credit line requested by the Artist will be
used.

## 7. Payouts
Payouts run monthly when the Artist's balance exceeds US $50, paid
via the method the Artist selects (Stripe Connect, ACH, or check).
Artist provides a W-9 (or W-8BEN) before the first payout.

## 8. Term & Termination
Either party may terminate on 30 days' written notice. Artist may
withdraw any unsold work at any time on written notice; Birthright
will remove the listing within 3 business days. Sales already
committed will be honoured.

## 9. Indemnity
Artist warrants they own or have the rights to license the works and
that the works do not infringe third-party rights. Artist will
indemnify Birthright against claims of infringement.

## 10. Governing Law
North Carolina, USA; exclusive jurisdiction of courts in Mecklenburg
County, NC.
""", True),


# ============================================================
# 07 · VENDOR SUPPLIER / DROPSHIP AGREEMENT
# ============================================================
("07-vendor-supplier-agreement", "Vendor Supplier / Dropship Agreement (Draft, 7C's Farmstead first)", "Partner agreements", """
# Vendor Supplier / Dropship Agreement

**Parties:** Birthright Foundation ("Birthright") and the vendor
identified below ("Vendor"). This agreement governs Vendor's sale of
goods through birthright.live, whether fulfilled by Vendor
(dropship), by print partners on Vendor's behalf, or by Birthright
holding stock.

## 1. Independent Contractor
Vendor is an **independent contractor**. Nothing in this agreement
creates employment, agency, or partnership.

## 2. Product Listings
Vendor may list products approved by Birthright. Each listing states
name, description, SKU, retail price, wholesale price, fulfilment
mode (Vendor, print partner, or Birthright), and stock policy.
Vendor is responsible for the accuracy of listing content.

## 3. Wholesale Price & Retail
Birthright pays Vendor the wholesale price for each sold unit;
Birthright retains retail minus wholesale minus payment fees.
Retail price includes shipping unless otherwise noted. Founding
Partner vendors earn an additional 5% margin uplift for 5 years.

## 4. Order Fulfilment
- **Vendor dropship**: Vendor ships within 3 business days of a
  cleared order, or within Vendor's stated production time for
  made-to-order goods.
- **Vendor custom form** (e.g., 7C's Farmstead patches): Birthright
  sends Vendor a fully pre-filled order form; Vendor produces and
  ships.
- **Print partners** (Printful / Lulu): fulfilment is handled by the
  partner under Birthright's account.

## 5. Warranty & Returns
Vendor warrants goods are as described, fit for intended use, and
free from material defect. Buyer returns for defect or
misdescription are refunded by Birthright; Birthright is entitled to
recoup wholesale from Vendor. See
[Refund & Returns Policy](/legal/refunds).

## 6. Intellectual Property
Vendor retains ownership of Vendor's product designs and marks.
Vendor grants Birthright a non-exclusive, royalty-free licence to
list, market, and photograph the products for sale on the platform.

## 7. Payouts
Monthly payouts when Vendor's balance exceeds US $50. Vendor
provides a W-9 (or W-8BEN) before the first payout.

## 8. Indemnity & Insurance
Vendor warrants goods do not infringe third-party rights and comply
with applicable safety and labelling laws. Vendor will indemnify
Birthright against claims arising from the goods and will maintain
US $1,000,000 per-occurrence product-liability insurance if goods
are physical consumables or wearables.

## 9. Term & Termination
Either party may terminate on 30 days' written notice. On
termination, existing orders are fulfilled and pending payouts
settled.

## 10. Governing Law
North Carolina, USA.
""", True),


# ============================================================
# 08 · COMMUNITY PARTNER REFERRAL AGREEMENT
# ============================================================
("08-community-partner-referral-agreement", "Community Partner Referral Agreement (Draft)", "Partner agreements", """
# Community Partner Referral Agreement

**Parties:** Birthright Foundation ("Birthright") and the
organisation identified below ("Partner").

## 1. Independent Contractor
Partner is an **independent contractor**. This agreement creates no
employment, agency, or joint venture.

## 2. Referral Programme
Partner will refer members of its community to Birthright workshops,
products, or programmes using the referral code issued by Birthright.

## 3. Compensation
Birthright pays Partner **25% of net revenue** from purchases
attributed to Partner's referral code, unless otherwise agreed in
writing. Attribution runs 30 days from the referred visitor's first
click. "Net" excludes taxes, processing fees, refunds, and chargebacks.

## 4. Payouts
Monthly payouts when Partner's balance exceeds US $50. Partner
provides a W-9 (or W-8BEN) before the first payout.

## 5. Marketing Standards
Partner will use Birthright's approved copy or clearly identify
their communications as their own. Partner will not (a) spam,
(b) use false or misleading claims, (c) bid on Birthright's
trademarks in paid search, or (d) place referral links on adult or
unlawful sites.

## 6. Term & Termination
Either party may terminate on 30 days' written notice or immediately
for material breach. On termination, earnings accrued before the
termination date will be paid on the next scheduled cycle.

## 7. Intellectual Property
Partner may use the Birthright name and marks solely to describe the
referral relationship, subject to our brand guidelines.

## 8. Indemnity
Each party indemnifies the other for third-party claims arising from
its own acts or omissions or breach of this agreement.

## 9. Governing Law
North Carolina, USA.
""", True),


# ============================================================
# 09 · SPONSORSHIP AGREEMENT / RECOGNITION CONSENT
# ============================================================
("09-sponsorship-agreement", "Sponsorship Agreement / Sponsor Recognition Consent (Draft)", "Partner agreements", """
# Sponsorship Agreement & Recognition Consent

**Parties:** Birthright Foundation ("Birthright") and the sponsor
identified below ("Sponsor").

## 1. Pledge
Sponsor commits to the amount and campaign identified in the
signature block. Amounts are payable within 30 days of invoice.

## 2. Tax Status
Birthright's federal 501(c)(3) recognition is **not yet granted**.
Until it is, pledges are **not tax-deductible as charitable
contributions**. Birthright will issue a business receipt on payment.
Sponsor should consult a tax advisor.

## 3. Recognition
Birthright will recognise Sponsor at the level chosen (bronze /
silver / gold / presenting) with the benefits described on the
campaign page. Sponsor may opt out of public recognition in writing.

## 4. Use of Sponsor Name & Logo
Sponsor grants Birthright a limited, revocable licence to use
Sponsor's name and logo for recognition on the campaign page, the
sponsor directory, the Wall of Supporters, and related campaign
communications, in accordance with any Sponsor brand guidelines
provided. Any other use requires separate written permission.

## 5. Non-Endorsement
Recognition is acknowledgement of financial support only and does
not imply Birthright's endorsement of Sponsor's products or
services, or vice versa.

## 6. Refunds
Sponsorship payments are generally non-refundable. If Birthright
cancels the campaign before its scheduled start, unspent Sponsor
funds will be refunded.

## 7. Confidentiality
Non-public information exchanged between the parties is
confidential and will not be disclosed except as required by law.

## 8. Contingency Note
Where the campaign depends on a third-party event (e.g., a broadcast
partner), Sponsor understands that Birthright may terminate or
re-scope the campaign if commercial or safeguarding conditions are
not met, and will refund any unspent Sponsor funds.

## 9. Governing Law
North Carolina, USA.
""", True),


# ============================================================
# 10 · SLIDING-SCALE & SCHOLARSHIP TERMS
# ============================================================
("10-sliding-scale-scholarship-terms", "Sliding-Scale & Scholarship Terms (Draft)", "Public-facing", """
# Sliding-Scale & Scholarship Terms

**Effective date:** February 2026.

Birthright wants the work to be accessible. This page explains how
sliding-scale pricing and scholarships work.

## 1. Who It's For
Anyone whose participation would be significantly limited by full
price. We do not means-test; we trust you to self-assess.

## 2. Sliding-Scale Tiers
Where a workshop offers sliding scale, three prices appear at
checkout:
- **Full price** — the number that keeps the work funded.
- **Community price** — a partial subsidy, appropriate if full price
  is a stretch but doable.
- **Access price** — a deep subsidy, appropriate if full price would
  prevent you from attending.

## 3. Scholarships
For high-need cases, apply for a full scholarship at the workshop
listing page. Approvals are based on available funds and the
applicant's stated need. There is no essay.

## 4. Ethics
Please choose honestly. Every access-price seat is funded by a
full-price seat. If your situation improves, we welcome you to move
up a tier next time.

## 5. Refunds
Sliding-scale purchases follow the standard
[Refund & Returns Policy](/legal/refunds). Scholarship seats are
non-transferable and non-refundable but may be forfeited without
penalty if you cannot attend and notify us at least 7 days in
advance.

## 6. Contact
scholarships@birthright.live.
""", True),


# ============================================================
# 11 · BOARD MEMBER / OFFICER AGREEMENT + D&O
# ============================================================
("11-board-officer-agreement", "Board Member / Officer Agreement + D&O Coverage (Draft)", "Governance", """
# Board Member / Officer Agreement

**Parties:** Birthright Foundation ("Birthright") and the individual
identified below ("Director").

## 1. Role
Director agrees to serve on Birthright's Board of Directors
(or as an Officer of Birthright, as specified), subject to the
Articles of Incorporation and Bylaws.

## 2. Term
The term is [one] year, renewable at the pleasure of the Board.

## 3. Fiduciary Duties
Director will discharge their duties in good faith, with the care an
ordinarily prudent person would exercise in a like position, and in
a manner Director reasonably believes to be in the best interests of
the Foundation (duties of care, loyalty, and obedience).

## 4. Conflicts of Interest
Director will disclose any actual or potential conflict of interest
promptly and abstain from voting on affected matters. Director
signs the Foundation's Conflict-of-Interest Policy (part of the
Governance Bundle).

## 5. Confidentiality
Non-public information about the Foundation, its donors, its
partners, and its participants is confidential. Confidentiality
survives termination indefinitely for personal data and for three
(3) years for other information.

## 6. Compensation
Director service is **uncompensated** except for reimbursement of
reasonable expenses (travel, materials) pre-approved by the Board
Chair.

## 7. Time Commitment
Director agrees to attend at least [75%] of Board meetings each
year, prepare in advance, and serve on at least one committee.

## 8. Indemnification & D&O
Consistent with North Carolina Nonprofit Corporation Act and the
Bylaws, the Foundation will indemnify Director against expenses and
liabilities incurred in the good-faith performance of duties, and
will maintain Directors & Officers ("D&O") liability insurance at
customary limits (not less than US $1,000,000).

## 9. Removal
The Board may remove a Director for cause (breach of fiduciary duty,
material policy violation) by two-thirds vote, subject to due
process under the Bylaws.

## 10. Governing Law
North Carolina, USA.
""", False),


# ============================================================
# 12 · VOLUNTEER AGREEMENT
# ============================================================
("12-volunteer-agreement", "Foundation Working-Group Volunteer Agreement (Draft)", "Governance", """
# Volunteer Agreement

**Parties:** Birthright Foundation ("Birthright") and the volunteer
identified below ("Volunteer").

## 1. Role
Volunteer will contribute time and effort to the working group /
project identified in the signature block. Volunteer service is
**uncompensated** and is not employment or an independent-contractor
engagement.

## 2. Time Commitment
Approximate hours per month: as agreed with the working-group lead.
Volunteer may withdraw at any time on reasonable notice.

## 3. Standards
Volunteer will follow Birthright's Community Standards and the
policies specific to their working group (safeguarding, media,
communications). Volunteer will not represent Birthright externally
without written authorisation.

## 4. Intellectual Property
Any materials Volunteer creates for Birthright in the course of
volunteering (documents, slides, code contributions to open work) are
assigned to Birthright on creation, or, if Volunteer contributes
under an open-source licence, are licensed to Birthright under that
licence.

## 5. Confidentiality
Non-public information about the Foundation and its participants is
confidential. This obligation survives termination.

## 6. Safety & Insurance
Volunteers acting within the scope of their agreed role are covered
by the Foundation's volunteer-accident and general-liability
policies. Volunteer must not undertake activities outside their
agreed scope without written approval.

## 7. Data
Volunteer's contact details are held under the Privacy Policy and
purged 12 months after the volunteering ends unless retention is
required for records.

## 8. Governing Law
North Carolina, USA.
""", False),


# ============================================================
# 13 · OMBUDSMAN CHARTER
# ============================================================
("13-ombudsman-charter", "Ombudsman Charter (Draft)", "Governance", """
# Ombudsman Charter

**Effective date:** February 2026.

## 1. Purpose
The Ombudsman offers a confidential, independent, informal channel
for anyone connected to Birthright (participants, partners,
volunteers, staff, board) to raise concerns and seek fair resolution.

## 2. Standards
The Ombudsman operates by four IOA standards: **independence**,
**neutrality**, **confidentiality**, and **informality**.

## 3. Scope
The Ombudsman can hear any concern except (a) legally required
mandated reports, which are escalated in parallel, and (b) matters
already in binding arbitration or litigation, which are referred to
counsel.

## 4. Confidentiality
Communications with the Ombudsman are confidential except (a) an
imminent risk of serious harm, (b) a mandated report, or (c) the
visitor's written waiver.

## 5. Records
The Ombudsman keeps no personally identifying case files. Aggregate,
de-identified trend reports are provided to the Board annually.

## 6. Authority
The Ombudsman does not decide grievances or impose sanctions but
may (a) advise, (b) facilitate dialogue, (c) escalate systemic
concerns to the Board, and (d) recommend policy changes.

## 7. Independence
The Ombudsman reports functionally to the Board, not to the
Executive Director. The Ombudsman may not hold any other role in
Birthright.

## 8. Contact
ombudsman@birthright.live.
""", False),


# ============================================================
# 14 · COMMUNITY STANDARDS
# ============================================================
("14-community-standards", "Content Moderation & Community Standards Policy (Draft)", "Public-facing", """
# Community Standards

**Effective date:** February 2026. These standards apply anywhere
you interact with other people on birthright.live — reviews, posts,
direct messages, gallery submissions, workshop chats.

## 1. Our Commitment
We keep this space attentive, honest, and safe. We do not remove
content because it is uncomfortable; we do remove content that
harms.

## 2. Not Allowed
- Threats, harassment, or targeted abuse.
- Content sexualising minors.
- Content encouraging self-harm or suicide (safe-messaging resources
  are welcome).
- Illegal content, incitement to violence, or unlawful discrimination.
- Doxxing (posting private identifying information about others).
- Spam, scams, and impersonation.

## 3. Please Handle With Care
- Firsthand accounts of trauma, when relevant to the work. Add a
  brief content note.
- Political or religious content, when relevant to the work.
  Assume good faith; disagree without contempt.
- Health, legal, or financial claims. Cite sources; do not present
  as advice.

## 4. What We Do
- **Warn** — first infraction of Section 3, we contact you.
- **Remove content** — Section 2, or repeated Section 3.
- **Suspend account** — severe or repeated violations.
- **Report to authorities** — for imminent-harm and mandated-report
  categories.
- Actions are logged; users may appeal to the Ombudsman.

## 5. Reporting
Report a post through the "…" menu on the post, or email
trust@birthright.live. We respond within 3 business days.

## 6. Appeals
If your content or account is actioned, you may appeal in writing
within 14 days. Appeals are reviewed by a person who was not
involved in the original decision.
""", True),


# ============================================================
# 15 · REFUND & RETURNS POLICY
# ============================================================
("15-refund-returns-policy", "Refund & Returns Policy (Draft, Public)", "Public-facing", """
# Refund & Returns Policy

**Effective date:** February 2026.

## 1. Products (Physical Goods)
- **Made-to-order / print-on-demand** (most journals, apparel, mugs,
  patches): non-returnable except for **defect or damage**.
  Contact us within 14 days of delivery with photos and we will
  reprint or refund.
- **Stocked goods**: 30-day return for any reason if unused and in
  original packaging. Buyer pays return shipping unless the return
  is due to our error.

## 2. Workshops
- **≥ 7 days before start:** full refund or transfer to a later
  cohort.
- **< 7 days before start:** 50% refund or full transfer.
- **After start:** no refund; transfer at our discretion.
- Scholarship and access-tier seats are non-refundable but
  cancellable without penalty on ≥ 7 days notice.

## 3. Subscriptions
Cancel anytime from your dashboard. Cancellation is prospective;
already-paid periods are non-refundable unless required by law.

## 4. AI Wallet Credits
Prepaid credits are non-refundable once consumed. Unused credits are
refundable on request within 30 days of purchase.

## 5. Sponsorships & Donations
Sponsorship payments are non-refundable except where a campaign is
cancelled by Birthright before start (in which case unspent Sponsor
funds are refunded). Donations are non-refundable except for
manifest error.

## 6. EU / UK Consumers
The 14-day right of withdrawal applies to distance sales of goods
and most digital services, subject to the exceptions in Article 16
of the EU Consumer Rights Directive.

## 7. How to Request
Email support@birthright.live with your order number. We aim to
process refunds within 5 business days of approval.
""", True),


# ============================================================
# 16 · SALES-TAX REGISTRATION PLAN (INTERNAL)
# ============================================================
("16-sales-tax-registration-plan", "Sales-Tax Registration Plan (Draft)", "Internal / Compliance", """
# Sales-Tax Registration Plan

**Effective date:** February 2026. Internal planning document.

## 1. Approach
Register in the state where we have physical presence first
(nexus), then adopt an economic-nexus monitoring service to trigger
registrations in other states as thresholds are met.

## 2. Physical Nexus
- **Home state (NC)** — register immediately with the NC Department
  of Revenue. File monthly.

## 3. Economic Nexus
Most states use a $100k / 200-transaction threshold (some are $500k;
NY and CA differ). We will use TaxJar / Avalara / Stripe Tax to
monitor thresholds and file when triggered.

## 4. Product Taxability
- Physical merch: taxable.
- Digital workshops (live): typically not taxable; a few states
  differ (e.g., TN, DC).
- Print-on-demand: taxed where the buyer is, collected by the print
  partner in some cases (Printful).

## 5. Marketplace Facilitator Rules
Where a print partner acts as marketplace facilitator, they collect
and remit; we do not double-collect. Track exemption certificates on
file.

## 6. Records
Retain sales-tax records for 7 years.
""", False),


# ============================================================
# 17 · TRADEMARK FILINGS PLAN (INTERNAL)
# ============================================================
("17-trademark-filings-plan", "Trademark Filings Plan (Draft)", "Internal / IP", """
# Trademark Filings Plan

**Effective date:** February 2026. Internal planning document.

## 1. Marks to Register
1. **BIRTHRIGHT FOUNDATION** — standard character (word mark) and
   the flame logo (design mark).
2. Slogans in active use.
3. Any workshop-specific brand that we intend to franchise.

## 2. Classes
- 41 (Educational services — workshops, classes, retreats).
- 16 (Journals, workbooks).
- 25 (Apparel).
- 35 (Community organising, partner directory).
- 42 (Online platform services).

## 3. Filing Basis
File Section 1(a) use-based on marks with proven commercial use,
Section 1(b) intent-to-use for planned launches. USPTO application
fee ~$350 per class per mark.

## 4. Watch Service
Enrol in a watch service (e.g., Corsearch) to catch confusingly
similar filings.

## 5. International
File Madrid Protocol via WIPO once federal (US) is registered, for
key markets: UK, EU, CA, AU.

## 6. Common-Law Notice
Until federal registration issues, use "™" (not "®"); switch to "®"
on notice of registration.
""", False),


# ============================================================
# 18 · COPYRIGHT REGISTRATION STRATEGY (INTERNAL)
# ============================================================
("18-copyright-registration-strategy", "Copyright Registration Strategy (Draft)", "Internal / IP", """
# Copyright Registration Strategy

**Effective date:** February 2026. Internal planning document.

## 1. Assets to Register
- **Workshop curricula** — literary work; register per workshop.
- **Research articles** — quarterly batch registration.
- **Workshop video recordings** — audiovisual work.
- **Original photography** — annual group registration.

## 2. Do Not Register
- **AI-generated imagery** — under current US Copyright Office
  guidance, works without significant human authorship are not
  copyrightable. Document human authorship (curation, prompting,
  compositing) if we ever attempt registration on a composite piece.

## 3. Cadence
Quarterly for articles and photos; per-work for curricula on
completion.

## 4. Notice
Add "© Birthright Foundation [year]" to protected works.

## 5. Assignments
Each contributor (facilitator, writer, videographer, photographer)
signs a written work-for-hire clause or an IP assignment before
work is publicly released.
""", False),


# ============================================================
# 19 · DATA PROCESSING AGREEMENT TEMPLATE
# ============================================================
("19-data-processing-agreement-template", "Data Processing Agreement Template (Draft)", "Governance", """
# Data Processing Agreement (Template)

**Parties:** Birthright Foundation ("Controller") and the vendor
identified below ("Processor"). This template implements GDPR Art.
28 and equivalent US-state requirements.

## 1. Definitions
Terms have the meanings in GDPR (EU) 2016/679, UK GDPR, and the
CCPA/CPRA, as applicable.

## 2. Scope of Processing
Processor will process Personal Data only on Controller's documented
instructions and only for the purposes described in the underlying
service agreement.

## 3. Sub-processors
Processor will maintain a list of sub-processors and notify
Controller of changes with a right to object. Sub-processors are
bound by written terms no less protective than this DPA.

## 4. Security
Processor implements the technical and organisational measures set
out in Annex 2 (TLS in transit, encryption at rest for sensitive
data, access controls, audit logging, staff confidentiality,
vulnerability management, incident response).

## 5. Personal Data Breach
Processor will notify Controller of a Personal Data breach without
undue delay and no later than 48 hours after becoming aware.

## 6. Data-Subject Requests
Processor will assist Controller with data-subject requests (access,
correction, deletion, portability, objection) at no extra cost.

## 7. International Transfers
Where personal data is transferred outside the EEA or UK, the
parties enter into the EU Standard Contractual Clauses (2021/914)
and the UK IDTA, and complete a transfer-impact assessment.

## 8. Audit
Once per year, Controller may audit Processor's compliance on 30
days' notice, or accept a recent SOC 2 / ISO 27001 report.

## 9. Return / Deletion
On termination, Processor returns or deletes Personal Data at
Controller's option, unless retention is required by law.

## 10. Liability
Liability for breach of this DPA follows the underlying service
agreement's limitation-of-liability terms, except that neither
party may exclude liability for wilful misconduct or breach of
data-protection law where such exclusion is prohibited.

## 11. Governing Law
As in the underlying service agreement.

### Annex 1 — Description of Processing
(To be completed per Processor: categories of data subjects,
categories of data, purpose, retention.)

### Annex 2 — Security Measures
(To be completed per Processor: encryption, access, backups,
incident response, staff training.)
""", True),


# ============================================================
# 20 · NONPROFIT GOVERNANCE BUNDLE
# ============================================================
("20-nonprofit-governance-bundle", "Nonprofit Governance Bundle (Draft — Articles, Bylaws, COI, Whistleblower, Retention)", "Governance", """
# Nonprofit Governance Bundle

This bundle contains five plain-language first drafts a nonprofit
lawyer can adapt to Birthright's chosen state and entity form.

---

## A. Articles of Incorporation (Draft outline)
1. **Name.** Birthright Foundation.
2. **Type.** Nonprofit corporation under N.C. Gen. Stat. Ch. 55A.
3. **Duration.** Perpetual.
4. **Purpose.** Exclusively charitable and educational within the
   meaning of Section 501(c)(3) of the Internal Revenue Code,
   including educational programming on secure attachment,
   presence, and community wellbeing.
5. **Members.** No members; governance by a self-perpetuating Board.
6. **Board.** Not fewer than three (3) directors.
7. **Registered agent & office.** As designated on Form NC BE-01.
8. **Dissolution.** Upon dissolution, assets distributed to one or
   more organisations qualified under IRC 501(c)(3) or to a
   governmental entity for a public purpose.
9. **Non-inurement / non-political.** Standard 501(c)(3) clauses
   prohibiting private inurement, substantial lobbying, and any
   political-campaign intervention.

---

## B. Bylaws (Key sections)
- **Board size:** 3–11 directors.
- **Term:** two (2) years, staggered, up to three consecutive terms.
- **Meetings:** at least quarterly; annual meeting in Q1.
- **Quorum:** majority of directors then in office.
- **Officers:** Chair, Vice-Chair, Secretary, Treasurer. May be
  combined except Chair/Secretary.
- **Committees:** Executive, Finance & Audit, Governance,
  Programme, Ombudsman.
- **Indemnification:** to the fullest extent allowed by law; D&O
  insurance maintained.
- **Amendments:** two-thirds vote at a duly noticed meeting.

---

## C. Conflict-of-Interest Policy
- **Duty to disclose.** Directors, Officers, and key employees
  disclose actual or potential conflicts on appointment and
  annually.
- **Recusal.** The conflicted person leaves the room during
  deliberation and vote.
- **Independent review.** The disinterested Board members determine
  whether the transaction is fair and reasonable.
- **Documentation.** Meeting minutes record the disclosure,
  recusal, deliberation, and vote.
- **Annual statement.** Signed by every Director, Officer, and
  applicable staff.

---

## D. Whistleblower Policy
- **Anyone** may report suspected wrongdoing in good faith.
- **Channels:** ombudsman@birthright.live or the reporting portal.
- **Anti-retaliation.** No adverse action against a good-faith
  reporter.
- **Investigation.** By a person outside the reporting line;
  outcomes reported to the Board's Finance & Audit Committee.
- **Records** retained for seven (7) years.

---

## E. Records-Retention Schedule
| Record type              | Retention        |
|--------------------------|------------------|
| Articles, Bylaws         | Permanent        |
| Board minutes            | Permanent        |
| Tax filings (Form 990)   | Permanent        |
| Financial statements     | Permanent        |
| General ledger           | 7 years          |
| Contracts (active)       | Term + 7 years   |
| Payroll                  | 7 years          |
| Personnel                | Term + 7 years   |
| Grant files              | Term + 7 years   |
| Marketing consent        | Consent + 2 years|
| Security-audit logs      | 365 days         |
| Ordinary email           | 3 years          |

Records are destroyed by a documented, method-appropriate process
(secure shred for paper, cryptographic wipe or delete + retention
purge for electronic).
""", False),


# ============================================================
# 21 · STATE CHARITABLE SOLICITATION REGISTRATION PLAN
# ============================================================
("21-charitable-solicitation-plan", "State Charitable Solicitation Registration Plan (Draft)", "Internal / Compliance", """
# State Charitable Solicitation Registration Plan

**Effective date:** February 2026. Internal planning document.

## 1. Register-Where-You-Solicit
Forty (40) US states require charities that "solicit" (any ask, in
any medium) to register in that state, plus annual renewals. We
will register in the home state (NC) immediately and add additional
states as our national fundraising begins.

## 2. Home State Priority
- **North Carolina** — Charitable Solicitation Licensing Section,
  Form CSL-01. File within 30 days of first solicitation.

## 3. Big Traffic States (Phase 2)
Register within 30 days of first solicitation from residents of:
CA, NY, FL, TX, IL, PA, MA, NJ, VA, MD, WA, GA.

## 4. Disclosures
Add the required disclosure block to fundraising materials, e.g.:
> **North Carolina:** A copy of the license is available for the
> asking at the address above.
>
> **New York:** A copy of the latest annual report may be obtained
> from the organisation or from the Attorney General.
>
> (Full block library maintained by counsel or a compliance vendor.)

## 5. Vendor Option
Engage a compliance vendor (Harbor Compliance, Labyrinth, or
Foundation Group) for multi-state filings — typically $50–$150 per
state per year plus one-time onboarding.

## 6. Renewals
Annual, offset from fiscal-year end. Calendar reminders set 60 days
in advance of every renewal.
""", False),


# ============================================================
# 22 · ISTV CONTRACT ANALYSIS MEMO (already substantive; retained as-is)
# ============================================================
]  # end DOCS


def write_all():
    written = []
    for slug, display_name, category, body, use_eu in DOCS:
        path = OUT / f"{slug}.md"
        content = (
            DISCLAIMER_TOP
            + "\n\n"
            + body.strip()
            + "\n"
            + DISCLAIMER_BOTTOM
        )
        if use_eu:
            content += EU_ADDENDUM
        path.write_text(content)
        written.append((slug, display_name, category, path))
        print(f"  wrote {path.name}  ({len(content) // 1024} KB)")

    # Preserve ISTV memo in the manifest (kept separate — heavy legal analysis
    # already crafted, not re-templated here).
    written.append(("22-istv-contract-analysis-memo", "ISTV Contract — Full Text Review & Business Value Memo", "Advisory memos", OUT / "22-istv-contract-analysis-memo.md"))

    # Rewrite the manifest so routers/legal.py stays in sync.
    manifest_lines = [
        "# AUTO-GENERATED by scripts/generate_legal_drafts_v2.py — do not edit by hand.",
        "# Regenerate with: python scripts/generate_legal_drafts_v2.py",
        f"# Last generated: {datetime.utcnow().isoformat()}Z",
        "",
        "DRAFT_LEGAL_DOCS = [",
    ]
    for slug, display_name, category, _ in written:
        manifest_lines.append(
            f'    {{"slug": "{slug}", "display_name": "{display_name}", '
            f'"category": "{category}"}},'
        )
    manifest_lines.append("]\n")
    (OUT / "_manifest.py").write_text("\n".join(manifest_lines))
    print(f"\nWrote {len(written)} drafts + manifest to {OUT}")


if __name__ == "__main__":
    write_all()
