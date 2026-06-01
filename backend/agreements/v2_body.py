"""Birthright Foundation — Universal Partner Agreement v2.0 body.

This is the placeholder copy the admin tools seed when no version is
present and the default new-draft body in the admin UI. **Counsel must
review and replace before live launch.** The structure (numbered
sections + summary of changes) is the part we want to be production-ready;
specific dollar figures and percentages are illustrative only.
"""
from __future__ import annotations

V2_VERSION = "2.0"

V2_SUMMARY_OF_CHANGES = (
    "v2.0 clarifies (1) the 50% AI usage markup; (2) the revenue-share "
    "structure for each partner role and how off-site sales are credited; "
    "(3) content licensing on user-uploaded artifacts; (4) a 12-month "
    "partner-sunset clause; (5) refund + clawback cascade language. "
    "Existing partners must re-sign before publishing new products, "
    "artifacts, featured slots, or AI Studio drafts."
)

V2_BODY = """# Birthright Foundation — Universal Partner Agreement
## Version 2.0

> **Status:** Placeholder copy. Legal counsel must review and replace
> the dollar figures, percentages, and jurisdiction-specific language
> before this agreement is presented to live partners.

This agreement governs your participation with Birthright Foundation
("**Birthright**", "**we**", "**us**") as a partner across any of the six
recognized partner roles: Facilitator, Vendor, Community, Research, Artist,
or Steward. It supersedes any earlier version on the day you accept it.

### 1. Voluntary, educational participation
Birthright's workshops, materials, partner services, and digital products
are **educational** in nature. They are not a substitute for licensed
mental-health, medical, financial, or legal advice. You participate at your
own discretion and acknowledge that outcomes vary by individual.

### 2. Revenue share and viability
Birthright is, first and foremost, a **mission-aligned partnership**.
Financial terms exist only to keep the work viable.

  * **Facilitators** retain 60% of revenue on workshops using Birthright IP;
    50% on workshops using their own materials.
  * **Vendors** retain 70% of net revenue on direct sales through the
    Birthright storefront. Off-site sales (via attributable referral links)
    are credited at a 15% revenue share.
  * **Community partners** earn 15% on attributable referrals over a
    30-day attribution window.
  * **Research partners** retain 100% of editorial control on artifacts
    they publish; Birthright takes 0% on free artifacts and 30% on paid
    promotions.
  * **Artists** retain 100% of original-work sales; the foundation takes
    0% on artist statements and 20% on featured-slot purchases.
  * **Stewards** receive a monthly honorarium agreed in writing; no
    revenue share applies.

Exact percentages may be adjusted by mutual written amendment. The
amendment process is described in §11.

### 3. AI usage and the Foundation markup
Where Birthright provides AI features (AI Studio, AI Concierge, Research
Collaborator, Vendor PDM), the per-call cost passed through to you is
the underlying provider cost **multiplied by 1.50×**. The additional 50%
directly supports Birthright Foundation's continuing operations. This
markup is disclosed at every surface where you see an AI cost: top-up
flows, usage tables, and the AI Wallet ledger.

You may top up your AI Wallet in increments of $10, $25, $50, or $100,
or enable auto-recharge. Unused balance is non-refundable except in the
event of partnership termination by Birthright.

### 4. Content licensing
For any artifact you upload to Birthright (product images, journal text,
research papers, featured-artist statements, workshop materials):

  a. **You retain copyright.** Nothing in this agreement transfers
     ownership of your work to Birthright.
  b. **You grant Birthright a non-exclusive, revocable, royalty-free
     license** to display, store, and distribute that artifact on
     Birthright surfaces (web, email, print collateral) for the duration
     of your active partnership plus 90 days.
  c. Promotional use of your work outside Birthright surfaces (e.g.,
     conference presentations, press) requires your separate written
     consent.
  d. You warrant that you have the right to upload everything you upload.

### 5. Refund and clawback cascade
When a transaction is refunded — by you, by the customer, or by Stripe
dispute resolution — the following cascade runs automatically:

  1. The Stripe charge is reversed.
  2. All side-effects are undone (registrations cancelled, subscriptions
     ended, featured slots removed, research promotions reversed, AI
     wallet top-ups voided).
  3. Any partner credit already issued is reversed where unpaid; where
     already paid out, it moves to a "pending recovery" ledger.
  4. Birthright will contact you in writing within 7 days to arrange
     recovery of paid-out funds. Failure to respond within 30 days
     authorizes Birthright to net the amount against future payouts.

### 6. Partnership sunset (12-month inactivity clause)
A partner profile is considered **dormant** if there has been no revenue
event, content publication, or admin-logged interaction for **12
consecutive months**. Dormant partners receive a written notice and a
90-day window to reactivate. If no reactivation occurs, the partner
profile is automatically transitioned to "archived" status — the public
page is hidden, future payouts are paused, and any active subscription
is cancelled (without prejudice to previously earned credits).

### 7. Conduct standards
Partners commit to engaging participants, facilitators, fellow partners,
and Birthright staff with respect, professional curiosity, and
attachment-aware language. Behavior incompatible with these standards
(harassment, discrimination, exploitation, or knowingly false claims of
clinical authority) is grounds for immediate partnership termination
under §10.

### 8. Data and privacy
Personal information you provide is governed by Birthright's privacy
policy (available at /privacy). Customer information you receive through
your partnership is **confidential**: you may not share, resell, or
contact customers outside the Birthright platform without their
documented consent.

### 9. Indemnification
You agree to hold Birthright Foundation, its governing board, employees,
facilitators, vendors, community partners, and contractors **harmless**
from claims arising out of (a) your services or products offered through
Birthright surfaces; (b) your conduct toward participants or other
partners; or (c) the truthfulness of credentials and warranties you
provide on your partner profile. This indemnity does not extend to
claims arising solely from Birthright's gross negligence or willful
misconduct.

### 10. Termination
Either party may terminate this partnership with **30 days' written
notice**. Birthright may terminate **immediately** for cause under §7
(conduct), §8 (data), or material breach of §4 (licensing). On
termination: future revenue events stop being credited; previously
earned but unpaid credits are paid on the next regular cycle; your
public partner page is unpublished within 7 days.

### 11. Amendments and re-sign
Birthright may amend this agreement from time to time. Substantive
amendments (those changing revenue share, licensing scope, or
indemnification) require your **re-acceptance**. You will be notified by
email and via an in-product banner. Continued use of write-side partner
features (publishing products, artifacts, featured slots, AI Studio
drafts, subscription changes) is conditioned on accepting the current
version. Read-side access (browsing, viewing your earnings ledger) is
never gated.

### 12. Governing law
This agreement is governed by the laws of the State of Arizona. Disputes
will be resolved through good-faith mediation before any legal action,
unless Birthright is entitled to seek immediate injunctive relief to
protect §4 or §8.

---

By clicking "I accept agreement v2.0" you confirm that you have read,
understood, and agreed to be bound by the terms above.
"""
