"""Regenerate birthright-versions.pdf — tight version index of every shipped iteration.

Run: python /app/scripts/build_versions.py
Output: /app/backend/static/exports/birthright-versions.pdf
"""
from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

OUT = Path("/app/backend/static/exports")
TMP = Path("/tmp")
TS = dt.datetime.utcnow().strftime("%b %d, %Y %H:%M UTC")

CSS = """
@page { size: Letter; margin: 0.55in; }
body { font-family:-apple-system,"Helvetica Neue",Arial,sans-serif; color:#1A2424;
       background:#FAF8F5; padding:24px 32px; line-height:1.45;
       -webkit-print-color-adjust:exact; print-color-adjust:exact; }
h1 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:30px;
     border-bottom:2px solid #C9A961; padding-bottom:8px; margin:0 0 6px 0; }
.subtitle { font-size:11px; letter-spacing:.13em; text-transform:uppercase;
            color:#5C6B6B; margin-bottom:22px; }
h2 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:20px;
     color:#2E5C46; margin:24px 0 8px 0; border-left:4px solid #C9A961; padding-left:10px; }
p,li,td,th { font-size:12px; }
table { width:100%; border-collapse:collapse; margin:8px 0 18px 0; background:#fff;
        box-shadow:0 1px 2px rgba(0,0,0,.05); }
thead th { background:#476B6B; color:#FAF8F5; text-align:left; padding:7px 9px;
           font-size:10px; text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
td { padding:7px 9px; border-bottom:1px solid #E5E1D8; vertical-align:top; }
tr:nth-child(even) td { background:#F4F1EA; }
.ver { font-family:"Cormorant Garamond",Georgia,serif; font-size:14px; color:#476B6B;
       font-weight:600; white-space:nowrap; }
.date { font-size:10.5px; color:#5C6B6B; white-space:nowrap; }
.pill { display:inline-block; padding:2px 8px; border-radius:10px; font-size:9px;
        text-transform:uppercase; letter-spacing:.07em; font-weight:600; margin-right:4px; }
.p-shipped { background:#2E5C46; color:#FAF8F5; }
.p-progress { background:#C9A961; color:#1A2424; }
.p-backlog { background:#E5E1D8; color:#5C6B6B; }
.callout { background:#FFFBEF; border-left:4px solid #C9A961; padding:10px 14px;
           margin:10px 0; font-size:12px; }
.callout-mission { background:#ECF3EE; border-left:4px solid #2E5C46;
                   padding:10px 14px; margin:10px 0; font-size:12px; }
ul { margin:4px 0 8px 18px; }
code { background:#F4F1EA; padding:1px 5px; border-radius:3px; font-size:10.5px; }
footer { margin-top:18px; font-size:9.5px; color:#5C6B6B; text-align:center;
         border-top:1px solid #E5E1D8; padding-top:9px; }
.pagebreak { page-break-before: always; }
"""

# Each row: (version, date, phase/iter label, headline)
SHIPPED = [
    ("v1.0.0",  "Feb 2026", "Phase 1",
     "Foundation MVP — public site, workshops, shop, sponsorship, registrations, participant dashboard, workshop hub (8 tabs), facilitator dashboard, admin dashboard."),
    ("v1.1.0",  "Mar 2026", "Iter 2",
     "Stripe webhook signature verification, refund flow, polymorphic order model, audit improvements."),
    ("v1.2.0",  "Mar 2026", "Iter 3 — Email infra",
     "Resend integration with EMAIL_DRY_RUN flag, transactional templates (registration, reminder, refund, support, contact, sponsorship), audit logging."),
    ("v1.3.0",  "Mar 2026", "Iter 4",
     "Workshop photos: participant uploads, moderation queue (approved/pending/rejected), thumbnails, S3-style storage path."),
    ("v1.4.0",  "Apr 2026", "Iter 5 — Realtime chat",
     "WebSocket chat (group + DMs), per-workshop ws_manager, presence, JWT cookie handshake, soft-delete, profanity guard."),
    ("v1.5.0",  "Apr 2026", "Iter 6A — Reviews",
     "Universal polymorphic reviews (workshop/product/service), anonymous mode, verified-purchase flag, moderation, reporting, /reviews browser."),
    ("v1.6.0",  "Apr 2026", "Iter 7 — Governance & Legal",
     "Governance defaults, proposals + voting, universal indemnification versioning, audit log, governance/ombudsman role flags."),
    ("v1.6.1",  "Apr 2026", "Iter 8 — Hardening",
     "Code-review cleanup: component splits, helper extractions, type hints throughout, large-function decomposition where it added clarity."),
    ("v1.7.0",  "Apr 2026", "Iter 9 — Phase 6B.1",
     "Partner foundation: applications (4 types — facilitator, community, research, vendor), profiles, public directory, admin queue, partner dashboard."),
    ("v1.8.0",  "May 2026", "Iter 10 — Phase 6B.2",
     "Partner subscriptions: tiered plans, Stripe-checkout-as-recurring with manual renewal, tier perks, plan picker, admin subscription view."),
    ("v1.9.0",  "May 2026", "Iter 11 — Phase 6B.3",
     "Community referrals + reporting MVP: /api/r/{code} redirect-and-cookie, referral attribution on checkout, payout ledger, /admin/payouts, MyReports."),
    ("v1.10.0", "May 2026", "Iter 12+13 — Phase 6B.4",
     "Vendor autonomous catalog: vendor CRUD on own products, admin moderation (flag/unpublish/restore), public store badges, vendor dashboard tab."),
    ("v1.10.1", "May 2026", "Iter 14 — Runtime hardening",
     "runtime_seed.py for production self-heal: catalog backfill from data/catalog.json, known broken-image repair, partner economy backfill defaults."),
    ("v1.11.0-step1", "May 23, 2026", "Phase 6B.4.5a",
     "Partner economy model overhaul: PartnerProfile gained 13 new fields (founding partner, featured-until, rev-share overrides, external site URL, payout fields, W9 status). Subscription tables regenerated with inverted pricing (longer commitment = lower fee and lower foundation take rate)."),
    ("v1.11.0-step1.5", "May 24, 2026", "Phase 6B.4.5b + 6B.4.5c (Iter 15)",
     "Join Us + Sample Partner Profiles. 3 open foundation roles (Board Chair & Co-Founder, Research Advisor, Director of Community Stewardship) with public /join-us listing, application form, and admin triage queue (6-status pipeline). 8 sample partner personas (2 per partner type) marked is_sample:true, hidden from default /partners directory, surfaced at /partners?samples=1 as a sales tool for founding-partner outreach. Governance page got SAMPLE ribbons on the 3 recruited-for board cards. Backend 21/21 PASS, frontend 100%."),
    ("v1.11.0-step2+3", "May 25, 2026", "Iter 16",
     "Outbound-click attribution + Off-site sales reconciliation. GET /api/out/{slug} redirect endpoint with UTM capture, IP/UA logging, host-locked dest param, fallback to /partners on 404. Outbound links surfaced on vendor + community partner cards/profile pages only. Partner self-report flow at /dashboard/partner/sales-reports with monthly defaults + HMAC webhook (per-partner secret, SHA-256 signed payload, rotate-anytime). Admin reconciliation at /admin/partner-sales-reports with approve/dispute/revise actions and optional override_gross/override_pct. Credits land in partner_off_site_credits with pct sourced from rev_share_overrides.off_site_pct → active subscription → global default. Backend 25/25 PASS, frontend 100%."),
    ("v1.11.0-step4+5", "May 25, 2026", "Iter 17",
     "Featured-Partner Showcase + Founding-Partner gating. Self-serve featured slots at $99/30 days via Stripe (random shuffle on /featured, gold ribbon across directory, editable content while window active). Admin grant/revoke + comped slots. Founding-Partner program: opt-in checkbox on /partners/apply with public 'X/cap' counter and progress bar; auto-grant on application approval if cap has room (5-year locked rate); admin cap controls + grant/revoke endpoints. Founding badges visible across directory + profile pages (including samples). Backend 20/20 PASS, frontend 100% after Founding badge + nested-anchor fixes."),
    ("v1.11.0-step6+7", "May 25, 2026", "Iter 18",
     "Paid Research Promotion + Payouts scaffolding. New /research public page with Promoted top section + general listing; partner-side CRUD at /dashboard/partner/research with tiered Stripe checkout ($49 brief / $149 peer-reviewed paper / 30 days). Stripe webhook fulfillment for `research_promotion` type; activate_research_promotion extends promoted_until on paid. Admin tier-override + free promotion grant/revoke. /partners directory got a Featured strip at top (auto-hidden in samples mode). Payouts UI: /dashboard/partner/payouts with 3 tabs (Ledger from referrals + off-site credits, W9 form persisted + signed, Payout method capture — Stripe Connect account OR encrypted ACH using Fernet PAYOUT_ENCRYPTION_KEY). Admin endpoints: list credits, mark-paid (one-way), view W9 (audit-logged). 2 sample research artifacts seeded. Header nav tightened to fit 11 items with no overlap on 1280px+, mobile menu activates below xl breakpoint. Backend 32/32 PASS, frontend 100%."),
    ("v1.11.0-step8+8.5", "May 25, 2026", "Iter 19",
     "Disbursement orchestration + Universal Share & Save System. Step 8: admin disbursement-settings (next_disbursement_date, cadence, partner-visible notes) at /admin/payouts; ready-to-pay aggregation gated to W9 + payout method on file; CSV export of pending payouts; partner email notification on mark-paid (`disbursement_notification` template). Step 8.5: ShareButton component (Copy/QR/Email/SMS/Bookmark/ICS/Cite icons context-aware) with `?via=` referral attribution that sets the birthright_ref cookie when sharer is an active community partner. Backend: POST /api/shares/log (anon-friendly), GET/POST/DELETE /api/me/bookmarks (polymorphic), GET /api/research/{id}/cite?format=apa7|bibtex, GET /api/workshops/{id}/ics, GET /api/me/share-token. New pages: /dashboard/bookmarks. Share buttons placed on workshop detail, product detail, research artifacts, partner profiles, join-us roles. Privacy matrix respected: no share on workshop materials, ledger rows, W9, payout methods, admin dashboards. qrcode.react npm pkg installed for client-side QR rendering."),
    ("v1.11.0-step9 + share-coverage", "May 25, 2026", "Iter 20",
     "Subscription UI parity + universal Share/Print/Download coverage. Step 9: partner-initiated cancel (non-destructive — license stays until expires_at; status='cancelled'); mid-flight plan change with prorated credit (free upgrade when credit >= new price else Stripe checkout for the delta); admin /admin/subscriptions page with filter chips, status pills, revoke + optional Stripe refund modal. Webhook fulfillment now handles supersedes_subscription_id end-to-end. ShareButton placement completed everywhere user requested: partner directory cards, governance board member cards, join-us list cards, workshops list cards, shop product cards (non-material), facilitators list + profile, research artifact cards, plus detail pages. Universal Print (window.print() with @media print rules in App.css that hide nav/footer/share) and Download QR PNG (rasterizes the SVG to a 4× canvas PNG; hidden QR pre-rendered so first click works). Privacy matrix preserved. 16/16 backend tests PASS."),
]

# Reverse so newest appears first
SHIPPED_ROWS = list(reversed(SHIPPED))

IN_PROGRESS = [
    ("v1.11.0-step10", "Refund/clawback cascade + Partnership agreement v2",
     "Cascade refunds back through credits + payouts and require partners to re-sign agreement v2 on next login."),
]

BACKLOG = [
    ("v1.11.0-steps 4–10", "Featured-partner showcase, founding-partner gating, paid research promotion, /partners rebuild with 5-tab pattern, payouts infra (W9/1099 collection), subscription UI parity, refund/clawback cascade, partnership agreement v2 with re-sign."),
    ("Phase 6B.5", "Research submissions queue: data model, public listing, admin moderation, DOI minting. (Scope PDF already exists, paused pending v1.11.0.)"),
    ("Phase 6C", "Communications: user↔partner DMs, partner↔partner DMs, ombudsman dashboard, dispute/escalation workflow."),
    ("Phase 6B.6", "'More Info' / FAQ contextual modals site-wide. Depends on 6C for ombudsman endpoints."),
    ("Discovery & Search", "Advanced cross-site search (products + workshops + partners), comparison view, vendor filters."),
    ("/music", "Curated mood/activation playlist library (YouTube + CC embeds)."),
    ("Email live mode", "Flip EMAIL_DRY_RUN=false once Resend DNS verification clears on birthright.live."),
    ("Tech debt", "Rate-limit auth + chat WS; Redis pub/sub for ws_manager; admin self-demotion guard; Stripe webhook signature verification audit; sponsorship tier upgrade flow; Twilio SMS check-in reminders; multi-language (en/es)."),
]


def shipped_table() -> str:
    rows = "\n".join(
        f"<tr><td class='ver'>{v}</td><td class='date'>{d}</td><td><span class='pill p-shipped'>Shipped</span> <span class='b'>{label}</span></td><td>{summary}</td></tr>"
        for (v, d, label, summary) in SHIPPED_ROWS
    )
    return f"""<table>
<thead><tr><th>Version</th><th>Date</th><th>Phase / Iter</th><th>What shipped</th></tr></thead>
<tbody>{rows}</tbody></table>"""


def in_progress_block() -> str:
    rows = "\n".join(
        f"<tr><td class='ver'>{v}</td><td><span class='pill p-progress'>In progress</span> <span class='b'>{label}</span></td><td>{summary}</td></tr>"
        for (v, label, summary) in IN_PROGRESS
    )
    return f"""<table>
<thead><tr><th>Target version</th><th>Status / Item</th><th>Scope</th></tr></thead>
<tbody>{rows}</tbody></table>"""


def backlog_block() -> str:
    rows = "\n".join(
        f"<tr><td class='ver'>{label}</td><td><span class='pill p-backlog'>Backlog</span></td><td>{summary}</td></tr>"
        for (label, summary) in BACKLOG
    )
    return f"""<table>
<thead><tr><th>Item</th><th>Status</th><th>Scope</th></tr></thead>
<tbody>{rows}</tbody></table>"""


body = f"""
<h1>Birthright — Version Index</h1>
<div class="subtitle">Tight history of every shipped version · Refreshed {TS}</div>

<div class="callout-mission">
<span class="b">How to read this document.</span> Three sections — <span class="b">Shipped</span> (newest first),
<span class="b">In progress</span> (currently being built), and <span class="b">Backlog</span>
(prioritized but not yet scheduled). Cross-references to scope PDFs are <code>monospaced</code>.
</div>

<h2>1 · Shipped</h2>
{shipped_table()}

<h2>2 · In progress</h2>
{in_progress_block()}

<div class="callout">
Current sequence: <code>v1.11.0-step6+7</code> shipped together on May 25, 2026 (Iter 18). Next up:
<code>v1.11.0-step8</code> (disbursement orchestration + CSV export) and <code>v1.11.0-step9</code>
(subscription UI parity). After that: <code>v1.11.0-step10</code> (refund/clawback cascade +
partnership agreement v2 with re-sign). Phase 6B.5 (Research submissions queue) remains paused
until v1.11.0 is fully shipped — scope PDF already exists at
<code>birthright-phase-6b5-research-scope-v1.pdf</code>.
</div>

<h2>3 · Backlog</h2>
{backlog_block()}

<h2>4 · Related scope &amp; proposal documents</h2>
<ul>
<li><code>birthright-pricing-proposal-v1.pdf</code> — Original pricing market analysis (4 partner classes, BTI multiplier, founding-partner program)</li>
<li><code>birthright-pricing-proposal-v2.pdf</code> — Revised pricing with inverted commitment economics (longer commitment = lower fee + lower foundation take)</li>
<li><code>birthright-v1.11-partner-economy-scope-v1.pdf</code> — Full v1.11.0 scope + 10-step implementation plan with per-step tests</li>
<li><code>birthright-phase-6b5-research-scope-v1.pdf</code> — Research Submissions Queue (deferred)</li>
<li><code>birthright-join-us-scope-v1.pdf</code> — Phase 6B.4.5b/c scope (shipped this iteration)</li>
<li><code>birthright-final-plans-review-v1.pdf</code> — Founder pre-shipping review document</li>
</ul>

<footer>Birthright Foundation · <em>Secure Bonds &gt; Thrive</em> · Version index · Refreshed automatically as each iteration ships</footer>
"""

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<title>Birthright Version Index</title><style>{CSS}</style>
</head><body>{body}</body></html>"""

(TMP / "versions.html").write_text(html)
pdf = OUT / "birthright-versions.pdf"
subprocess.run(
    ["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
     "--no-pdf-header-footer", f"--print-to-pdf={pdf}", f"file://{TMP / 'versions.html'}"],
    check=True, capture_output=True,
)
print(f"Generated: {pdf.name} ({pdf.stat().st_size} bytes)")
