"""Generate birthright-v1.11-step6-7-scope-v1.pdf — iter 18 scope document.

Run: python /app/scripts/build_iter18_scope.py
Output: /app/backend/static/exports/birthright-v1.11-step6-7-scope-v1.pdf
"""
from __future__ import annotations

import subprocess
from pathlib import Path

OUT = Path("/app/backend/static/exports")
TMP = Path("/tmp")

CSS = """
@page { size: Letter; margin: 0.55in; }
body { font-family:-apple-system,"Helvetica Neue",Arial,sans-serif; color:#1A2424;
       background:#FAF8F5; padding:24px 32px; line-height:1.5;
       -webkit-print-color-adjust:exact; print-color-adjust:exact; }
h1 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:30px;
     border-bottom:2px solid #C9A961; padding-bottom:8px; margin:0 0 6px 0; }
.subtitle { font-size:11px; letter-spacing:.13em; text-transform:uppercase;
            color:#5C6B6B; margin-bottom:22px; }
h2 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:21px;
     color:#2E5C46; margin:24px 0 8px 0; border-left:4px solid #C9A961; padding-left:10px; }
h3 { font-family:"Cormorant Garamond",Georgia,serif; font-size:17px; color:#476B6B; margin:14px 0 4px 0; }
p,li,td,th { font-size:12px; }
code { background:#F4F1EA; padding:1px 5px; border-radius:3px; font-size:10.5px; }
ul { margin:4px 0 8px 18px; }
.callout { background:#FFFBEF; border-left:4px solid #C9A961; padding:10px 14px;
           margin:10px 0; font-size:12px; }
.callout-mission { background:#ECF3EE; border-left:4px solid #2E5C46;
                   padding:10px 14px; margin:10px 0; font-size:12px; }
table { width:100%; border-collapse:collapse; margin:8px 0; background:#fff;
        box-shadow:0 1px 2px rgba(0,0,0,.05); }
thead th { background:#476B6B; color:#FAF8F5; text-align:left; padding:7px 9px;
           font-size:10px; text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
td { padding:7px 9px; border-bottom:1px solid #E5E1D8; vertical-align:top; }
tr:nth-child(even) td { background:#F4F1EA; }
.pill { display:inline-block; padding:2px 8px; border-radius:10px; font-size:9px;
        text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
.pill-shipped { background:#2E5C46; color:#FAF8F5; }
.pill-tier { background:#C9A961; color:#1A2424; }
footer { margin-top:18px; font-size:9.5px; color:#5C6B6B; text-align:center;
         border-top:1px solid #E5E1D8; padding-top:9px; }
"""

body = """
<h1>Iter 18 — v1.11.0 Step 6 + Step 7</h1>
<div class="subtitle">Paid Research Promotion · /partners polish · Payouts/W9/Method scaffolding · Shipped May 25, 2026</div>

<div class="callout-mission">
<span style="font-weight:600">What shipped.</span> Two independent product surfaces bundled in one
iteration: (1) a research-artifact CRUD + paid-promotion flow with two pricing tiers, and
(2) the first piece of payouts infrastructure — earnings ledger, W9 form, and payout-method
capture (Stripe Connect OR encrypted ACH).
</div>

<h2>1 · Research artifacts &amp; paid promotion (Step 6)</h2>

<h3>Pricing — tiered, admin-overridable</h3>
<table>
<thead><tr><th>Tier</th><th>Price</th><th>Duration</th><th>Audience</th></tr></thead>
<tbody>
<tr><td><span class="pill pill-tier">Brief</span></td><td>$49</td><td>30 days</td><td>Practitioner briefs, blog-style writeups, podcast episodes</td></tr>
<tr><td><span class="pill pill-tier">Peer-reviewed paper</span></td><td>$149</td><td>30 days</td><td>Journal-grade research, longitudinal studies, formal academic output</td></tr>
</tbody>
</table>
<p>Tier is set by the research partner when they create the artifact. Admin can override
(<code>PUT /api/admin/research/{id}/tier</code>) — e.g. comp a high-effort brief up to paper-tier
visibility without charging the partner. Admin can also grant a free promotion
(<code>POST /api/admin/research/{id}/promote/grant?days=30</code>).</p>

<h3>Artifact data model</h3>
<p>Full metadata captured: title, abstract, authors, publication_date, full_text_url, optional
DOI, optional cover_image_url, categories[] (up to 8), tags[] (up to 12), estimated_read_minutes,
tier, status (draft / published / archived), promoted_until.</p>

<h3>Public surfaces</h3>
<ul>
<li><code>/research</code> — promoted artifacts in top section (sparkle ribbon), general feed below sorted by publication_date desc</li>
<li><code>GET /api/research?q=...&amp;category=...</code> — search + category filter</li>
<li><code>GET /api/research/promoted</code> — promoted-only feed</li>
<li><code>GET /api/research/{id}</code> — detail</li>
</ul>

<h3>Partner-side flow</h3>
<ul>
<li><code>/dashboard/partner/research</code> — CRUD modal with all artifact fields</li>
<li><code>POST /api/me/research/{id}/promote/checkout</code> — opens Stripe at the artifact's tier price</li>
<li>Stripe webhook fulfillment via <code>_PAID_HANDLERS["research_promotion"]</code> calling
<code>activate_research_promotion</code> — extends or sets <code>promoted_until = now + 30 days</code>
and writes a <code>research_promotion_purchases</code> audit row</li>
<li>Partners cannot delete a currently-promoted artifact (would orphan the slot)</li>
</ul>

<h3>Seed data</h3>
<p>Two illustrative artifacts seeded via <code>runtime_seed.py</code>, linked to existing sample research
partners — visible on /research immediately:</p>
<ul>
<li><strong>Brief</strong> · "Co-Regulation Practices for Adult Children of Relational Trauma" (Daniel Brookes)</li>
<li><strong>Paper</strong> · "Attachment Patterns in Adoptive Families" (Imani Okafor) — with DOI</li>
</ul>

<h2>2 · /partners polish + Featured strip (Step 7a)</h2>

<p>Minimal-touch refresh: a <strong>Featured strip</strong> now appears at the top of <code>/partners</code>,
showing up to 4 currently-featured partners as compact ring-1 cards. Hidden in samples mode
(<code>?samples=1</code>). "See all featured →" link routes to the existing <code>/featured</code> page.
Tab structure and toggle behavior unchanged — this is intentionally a polish pass, not a rebuild.</p>

<h2>3 · Payouts &amp; financial collection (Step 7b)</h2>

<p>Three tabs at <code>/dashboard/partner/payouts</code>:</p>

<h3>Ledger tab</h3>
<p>Combines both earnings sources into a single ranked list with totals header:</p>
<ul>
<li>On-site referral payouts from <code>referral_payouts</code> collection</li>
<li>Off-site sales credits from <code>partner_off_site_credits</code> (shipped iter 16)</li>
<li>Status pills: earned / paid; sorted by earned_at desc</li>
<li><code>GET /api/me/payouts</code> returns <code>{totals, entries}</code></li>
</ul>

<h3>W9 form tab</h3>
<p>Full IRS Form W9 fields captured and persisted to <code>partner_w9_forms</code>:</p>
<ul>
<li>Full legal name, business name (if different), federal tax classification (7 options), exempt payee code</li>
<li>Address (line 1, line 2, city, state, ZIP, country)</li>
<li>TIN (SSN or EIN) — masked on display (<code>***-**-1234</code>); full TIN only visible to admin via <code>GET /api/admin/payouts/w9/{user_id}</code> (audit-logged)</li>
<li>Signature attestation (typed legal name) + auto-stamped <code>signed_at</code></li>
<li>Re-submission replaces and re-stamps</li>
</ul>

<h3>Payout method tab</h3>
<p>Two methods, mutually exclusive:</p>
<ul>
<li><strong>Stripe Connect</strong> — capture <code>acct_...</code> account ID (full Connect onboarding is a follow-up; this is the storage shape)</li>
<li><strong>Manual ACH</strong> — bank_name, account_holder_name, routing_number, account_number.
<strong>Account number is encrypted at rest</strong> via Fernet
(<code>PAYOUT_ENCRYPTION_KEY</code> env var, auto-generated at first boot). Only last 4 digits
ever returned on GET</li>
</ul>

<h3>Admin disbursement</h3>
<ul>
<li><code>GET /api/admin/payouts/credits[?status=earned]</code> — combined view across both collections</li>
<li><code>POST /api/admin/payouts/credits/{id}/mark-paid?source=on_site_referral|off_site_credit</code> — one-way state transition, terminal</li>
<li>Body accepts <code>{method, reference, note}</code> — stamped on the credit + audit-logged</li>
</ul>

<h2>4 · Test results</h2>
<table>
<thead><tr><th>Surface</th><th>Status</th><th>Coverage</th></tr></thead>
<tbody>
<tr><td>Backend</td><td><span class="pill pill-shipped">100% 32/32</span></td><td>All endpoints — research, payouts, webhook fulfillment, encryption roundtrip, audit logging</td></tr>
<tr><td>Frontend</td><td><span class="pill pill-shipped">100%</span></td><td>/research listing + search · /partners Featured strip · /dashboard/partner/research · /dashboard/partner/payouts (all 3 tabs)</td></tr>
<tr><td>Header overlap</td><td><span class="pill pill-shipped">Fixed</span></td><td>Logo + 11 nav items at 1920px verified no overlap; mobile menu now activates below 1280px (xl breakpoint)</td></tr>
</tbody>
</table>

<div class="callout">
<strong>Iteration report:</strong> <code>/app/test_reports/iteration_18.json</code> · zero defects ·
2 small frontend polish items addressed during the iter (Founding badge on samples from iter 17;
nav header overlap from iter 17). Updated versions index: <code>birthright-versions.pdf</code>.
</div>

<h2>5 · What's next</h2>
<ul>
<li><strong>v1.11.0-step8</strong> — Disbursement orchestration: CSV export of pending payouts (gated to W9+method on file), partner notification on mark-paid, "next disbursement date" setting</li>
<li><strong>v1.11.0-step9</strong> — Subscription UI parity (revoke, prorate, mid-flight plan change)</li>
<li><strong>v1.11.0-step10</strong> — Refund/clawback cascade + partnership agreement v2 with re-sign requirement</li>
</ul>

<footer>Birthright Foundation · <em>Secure Bonds &gt; Thrive</em> · v1.11.0 Step 6 + 7 scope · Shipped May 25, 2026</footer>
"""

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<title>Birthright v1.11.0 Step 6+7 Scope</title><style>{CSS}</style>
</head><body>{body}</body></html>"""

(TMP / "iter18.html").write_text(html)
pdf = OUT / "birthright-v1.11-step6-7-scope-v1.pdf"
subprocess.run(
    ["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
     "--no-pdf-header-footer", f"--print-to-pdf={pdf}", f"file://{TMP / 'iter18.html'}"],
    check=True, capture_output=True,
)
print(f"Generated: {pdf.name} ({pdf.stat().st_size} bytes)")
