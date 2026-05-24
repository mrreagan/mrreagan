"""Append v2 pricing proposal generation to the existing build script.

Run: python /app/scripts/build_pricing_v2.py
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
body { font-family:-apple-system,"Helvetica Neue",Arial,sans-serif; color:#1A2424; background:#FAF8F5;
       padding:24px 32px; line-height:1.45; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
h1 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:30px;
     border-bottom:2px solid #C9A961; padding-bottom:8px; margin:0 0 6px 0; }
.subtitle { font-size:11px; letter-spacing:.13em; text-transform:uppercase; color:#5C6B6B; margin-bottom:22px; }
h2 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:22px; color:#2E5C46;
     margin:24px 0 8px 0; border-left:4px solid #C9A961; padding-left:10px; }
h3 { font-family:"Cormorant Garamond",Georgia,serif; font-size:17px; margin:16px 0 6px 0; }
p,li { font-size:12.5px; }
ul,ol { margin:6px 0 10px 22px; }
table { width:100%; border-collapse:collapse; font-size:11px; margin:8px 0 16px 0; background:#fff;
        box-shadow:0 1px 2px rgba(0,0,0,.05); }
thead th { background:#476B6B; color:#FAF8F5; text-align:left; padding:7px 9px; font-size:10px;
           text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
td { padding:6px 9px; border-bottom:1px solid #E5E1D8; vertical-align:top; }
tr:nth-child(even) td { background:#F4F1EA; }
td.num,th.num { text-align:right; font-variant-numeric:tabular-nums; }
code { background:#F4F1EA; padding:1px 5px; border-radius:3px; font-size:10.5px; }
.b { font-weight:700; }
.gold { color:#8B7128; font-weight:600; }
.green { color:#2E5C46; font-weight:600; }
.red { color:#B86A5C; font-weight:600; }
.muted { color:#5C6B6B; font-style:italic; }
.callout { background:#FFFBEF; border-left:4px solid #C9A961; padding:10px 14px; margin:10px 0; font-size:12px; }
.callout-mission { background:#ECF3EE; border-left:4px solid #2E5C46; padding:10px 14px; margin:10px 0; font-size:12px; }
.callout-warn { background:#FBEDE9; border-left:4px solid #B86A5C; padding:10px 14px; margin:10px 0; font-size:12px; }
.qbox { background:#fff; border:1px solid #E5E1D8; border-radius:4px; padding:12px 14px; margin:8px 0; font-size:12px; }
.pill { display:inline-block; padding:2px 9px; border-radius:10px; font-size:10px;
        text-transform:uppercase; letter-spacing:.07em; font-weight:600; background:#476B6B; color:#FAF8F5; }
.pill-locked { background:#2E5C46; color:#FAF8F5; }
.pill-new { background:#C9A961; color:#1A2424; }
footer { margin-top:20px; font-size:9.5px; color:#5C6B6B; text-align:center;
         border-top:1px solid #E5E1D8; padding-top:9px; }
.pagebreak { page-break-before: always; }
"""

body = f"""
<h1>Subscription Pricing &amp; Rev-Share Model — v2 LOCKED</h1>
<div class="subtitle">Birthright Foundation · Secure Bonds &gt; Thrive · Exported {TS}</div>

<div class="callout-mission">
<span class="b">v2 supersedes v1.</span> All principles confirmed in the May 24, 2026 planning session are baked in:
longer commitment = smaller fee AND smaller foundation share; Foundation IP rev-share floors at 35/65; facilitators
never bulk-buy participant materials; no facilitator commission on Foundation materials (conflict-of-interest avoidance);
participant referrals as store credit only; required materials bundle into ticket; tiered refund policy.
</div>

<h2>1 · Locked principles</h2>
<ol>
<li><span class="b">Longer commitment is always rewarded.</span> Effective $/mo decreases; foundation share of partner revenue decreases; partner keep increases.</li>
<li><span class="b">Foundation only controls Foundation IP.</span> Everything else must be earned with carrots, not sticks.</li>
<li><span class="b">Participant materials are participant-only.</span> Facilitators cannot bulk-purchase. Admins author but do not buy.</li>
<li><span class="b">No facilitator commission on Foundation materials.</span> Foundation-driven promotion only; prevents conflict-of-interest and protects facilitator professional ethics codes.</li>
<li><span class="b">Mission-first, value-capturing.</span> Foundation share scales with partner revenue — we eat only when they eat.</li>
</ol>

<h2>2 · Standard rate tables (at BTI = 1.0)</h2>
<p class="muted">Pre-traction $ = these × 0.5 (current default). Founding-partner $ = these × 0.75, locked 5 years.</p>

<h3 class="gold">🎓 Facilitator</h3>
<table><thead><tr><th>Plan</th><th class="num">Sub fee</th><th class="num">Effective $/mo</th><th class="num">Foundation IP<br/>(foundation share)</th><th class="num">Non-IP<br/>(foundation share)</th><th class="num">Off-site</th></tr></thead><tbody>
<tr><td>Monthly</td><td class="num">$99/mo</td><td class="num">$99</td><td class="num"><span class="b">50%</span></td><td class="num">20%</td><td class="num">7%</td></tr>
<tr><td>Annual</td><td class="num">$899/yr</td><td class="num">$75 <span class="green">(–24%)</span></td><td class="num"><span class="b">42%</span></td><td class="num">15%</td><td class="num">5%</td></tr>
<tr><td>2-Year</td><td class="num">$1,499</td><td class="num">$62 <span class="green">(–37%)</span></td><td class="num"><span class="b">35%</span></td><td class="num">10%</td><td class="num">3%</td></tr>
</tbody></table>
<p class="muted"><span class="b">Floor:</span> Foundation IP share cannot drop below 35% except by admin override with audit log + governance proposal (per v1.6.0).</p>

<h3 class="gold">🛍️ Vendor (all sales are non-IP)</h3>
<table><thead><tr><th>Plan</th><th class="num">Sub fee</th><th class="num">Effective $/mo</th><th class="num">On-site<br/>(foundation share)</th><th class="num">Off-site</th></tr></thead><tbody>
<tr><td>Monthly</td><td class="num">$49/mo</td><td class="num">$49</td><td class="num">22%</td><td class="num">7%</td></tr>
<tr><td>Annual</td><td class="num">$419/yr</td><td class="num">$35 <span class="green">(–29%)</span></td><td class="num">17%</td><td class="num">5%</td></tr>
<tr><td>2-Year</td><td class="num">$749</td><td class="num">$31 <span class="green">(–37%)</span></td><td class="num">12%</td><td class="num">3%</td></tr>
</tbody></table>

<h3 class="gold">🤝 Community / Affiliate — FREE entry (we pay them)</h3>
<table><thead><tr><th>Plan</th><th class="num">Sub fee</th><th class="num">Their referral share</th><th>Volume bonus</th></tr></thead><tbody>
<tr style="background:#ECF3EE;"><td class="b">Starter</td><td class="num"><span class="green b">FREE</span></td><td class="num">8%</td><td>—</td></tr>
<tr><td>Plus</td><td class="num">$19/mo</td><td class="num">10%</td><td>+2% after 25 conversions/yr</td></tr>
<tr><td>Pro</td><td class="num">$99/yr ($8/mo)</td><td class="num">12%</td><td>+2% after 50; +4% after 100</td></tr>
<tr><td>2-Year Pro</td><td class="num">$149 ($6/mo)</td><td class="num"><span class="b">14% locked</span></td><td>Volume bonuses still apply</td></tr>
</tbody></table>

<h3 class="gold">🔬 Research — FREE entry + Eminence Sharing Agreement</h3>
<table><thead><tr><th>Plan</th><th class="num">Sub fee</th><th>What's included</th></tr></thead><tbody>
<tr style="background:#ECF3EE;"><td class="b">Standard</td><td class="num"><span class="green b">FREE</span></td><td>Submit research; chronological listing; ESA signed; foundation 5% on-site / 3% off-site if monetized</td></tr>
<tr><td>Citation Pro</td><td class="num">$99/yr</td><td>DOI minting, citation analytics, press-release co-rights</td></tr>
<tr><td>2-Year Citation Pro</td><td class="num">$149 ($6/mo)</td><td>Locked rates; same benefits</td></tr>
</tbody></table>
<p class="muted">À-la-carte paid promotion: Featured Research $99/mo · Highlighted Research $29/wk (one-time Stripe charges).</p>

<div class="pagebreak"></div>

<h2>3 · Foundation materials &amp; supplemental product rules</h2>

<table><thead><tr><th>Product type</th><th>Who can buy</th><th>Examples</th><th>Rev-share</th></tr></thead><tbody>
<tr><td><code>merch</code></td><td>Anyone</td><td>Branded journal, mug, t-shirt</td><td>Foundation 100% or vendor split</td></tr>
<tr><td><code>workshop_material</code></td><td><span class="b">Only paid registrants of that workshop</span></td><td>Workshop workbook, guided audio</td><td><span class="b">100% to foundation</span> (less Community referral if applicable). NO facilitator commission.</td></tr>
<tr><td><span class="pill pill-new">NEW</span> <code>facilitator_material</code></td><td>Only active Facilitator partner profiles</td><td>(Currently undefined — no foundation-curated facilitator library exists)</td><td>Foundation 100%</td></tr>
<tr><td><code>vendor_product</code></td><td>Anyone</td><td>Third-party merch via vendor catalog</td><td>Vendor rev-share (per their tier)</td></tr>
</tbody></table>

<h3 class="gold">Required vs optional material handling</h3>
<ul>
<li><span class="b">Required materials</span> (<code>is_required: true</code>) → auto-added to workshop ticket at registration with disclosure ("includes workbook"). Single line item on Stripe; foundation keeps the workbook portion as 100%.</li>
<li><span class="b">Optional materials</span> → shown as supplementary at checkout + post-registration; foundation drives the gentle nudge in confirmation email, dashboard, mid-workshop reminders. Facilitator is NEVER the salesperson.</li>
</ul>

<h3 class="gold">Why facilitators do NOT earn referral commission on Foundation materials</h3>
<table><thead><tr><th>Reason</th><th>Detail</th></tr></thead><tbody>
<tr><td>Professional ethics codes</td><td>APA / ACA / NASW / ICF all prohibit dual-relationship financial benefits with clients</td></tr>
<tr><td>Already fully compensated</td><td>Subscription = right to teach IP; workshop rev-share = labor of delivery</td></tr>
<tr><td>Materials are not facilitator-curated</td><td>Foundation chooses bundling; no endorsement to compensate</td></tr>
<tr><td>Mission reinvestment</td><td>Every $1 in commission is $1 not funding better materials/research</td></tr>
<tr><td>FTC #ad disclosure avoided</td><td>Skipping commissions removes paid-endorsement legal complications</td></tr>
</tbody></table>

<h2>4 · Refund &amp; clawback policy (codified in v1.11.0 Step 8)</h2>
<table><thead><tr><th>Cancel timing</th><th>Ticket refund</th><th>Material refund</th></tr></thead><tbody>
<tr><td>&gt; 72 hours before workshop</td><td class="green">Full</td><td class="green">Full</td></tr>
<tr><td>24–72 hours before</td><td class="green">Full</td><td class="red">None</td></tr>
<tr><td>&lt; 24 hours before</td><td class="red">None</td><td class="red">None</td></tr>
<tr><td>Facilitator-initiated cancellation</td><td class="green">Full</td><td class="green">Full</td></tr>
</tbody></table>
<p class="muted">Stripe refunds trigger automatic referral-row clawback per v1.11.0 cascade.</p>

<h2>5 · Participant referrals — store credit, no cash</h2>
<div class="callout">
<span class="b">Inserted into v1.11.0</span> rather than v1.12.0 — reuses the v1.9.0 referral cookie/attribution flow and shares the checkout-credit-redemption code with v1.11.0 Step 8 refund cascade. Minimizes refactoring.
</div>
<ul>
<li>Participant refers a friend → friend completes a workshop → referrer receives <span class="b">15% store credit</span> toward their next purchase</li>
<li>Credit applies to workshops, materials, OR merch — participant's choice</li>
<li>No cash payout; no 1099 obligation; no W-9 collection; no payout-batch infrastructure</li>
<li>New <code>user_credits</code> collection tracks balance + redemption ledger</li>
<li>Credit auto-applies at checkout (toggleable by participant)</li>
</ul>

<h2>6 · Carrots — why partners stay in the ecosystem</h2>
<h3 class="gold">Universal (all partner types)</h3>
<ul>
<li>One dashboard · one payout · one 1099 (vs 3–4 platforms otherwise)</li>
<li><span class="b">Indemnification coverage</span> extends v1.6.0 to cover partner work — hard to replicate elsewhere</li>
<li>"Birthright Approved Partner" trust badge</li>
<li>BTI transparency + grandfathered rates on renewal</li>
<li>Cross-partner collaboration tools (Phase 6C)</li>
</ul>

<h3 class="gold">🎓 Facilitator-specific</h3>
<ul>
<li><span class="b">The subscription IS the carrot</span> — buys the right to teach Foundation IP workshops</li>
<li>Virtual workshop venue (Zoom/Whereby integration) — saves their own license cost</li>
<li>Co-branded marketing assets generated by foundation</li>
<li>Student cross-pollination — students from one facilitator can register with others at small discount</li>
<li><span class="muted">NOTE: no "free facilitator library" — none exists; materials are activating, not conceptual</span></li>
</ul>

<h3 class="gold">🛍️ Vendor-specific</h3>
<ul>
<li>Zero listing fees (vs Etsy $0.20/listing + transaction fees)</li>
<li>AI product mockup generation — first 5 listings free (Gemini Nano Banana)</li>
<li>Workshop-supply bundles offered to <span class="b">participants at registration</span> (NEVER bulk-bought by facilitators)</li>
<li>Foundation events buy inventory for foundation-run symposiums at vendor bulk margins</li>
</ul>

<h3 class="gold">🤝 Community-specific</h3>
<ul>
<li>Volume bonuses significantly outpace Amazon Associates (1–10%)</li>
<li>2-Year Pro locks 14% lifetime, immune to BTI changes</li>
<li>Pro tier: 1 free workshop per quarter, featured listing eligibility, custom UTM analytics</li>
<li>Co-marketing in foundation newsletter + social</li>
</ul>

<h3 class="gold">🔬 Research-specific</h3>
<ul>
<li>DOI minting through foundation (~$0 vs $275 via Crossref)</li>
<li>Annual Research Symposium — invited speaking slot, no fee</li>
<li>Press release co-rights via foundation PR</li>
<li>Funding-introduction commission — 2–3% of grants from foundation-initiated intros</li>
<li>Data co-ownership for anonymized workshop datasets</li>
</ul>

<div class="pagebreak"></div>

<h2>7 · BTI multiplier (traffic-adjusted pricing)</h2>
<table><thead><tr><th>BTI range</th><th class="num">Multiplier</th><th>Plain English</th></tr></thead><tbody>
<tr style="background:#ECF3EE;"><td class="b">0.0 – 0.2 (today)</td><td class="num"><span class="b">× 0.50</span></td><td>Pre-traction discount</td></tr>
<tr><td>0.2 – 0.5</td><td class="num"><span class="b">× 0.70</span></td><td>Early launch</td></tr>
<tr><td>0.5 – 1.0</td><td class="num"><span class="b">× 0.85</span></td><td>Approaching parity</td></tr>
<tr><td>1.0 – 1.5</td><td class="num"><span class="b">× 1.00</span></td><td>Standard rate</td></tr>
<tr><td>1.5 – 2.5</td><td class="num"><span class="b">× 1.15</span></td><td>Premium</td></tr>
<tr><td>2.5+</td><td class="num"><span class="b">× 1.30</span></td><td>Hard cap on surge</td></tr>
</tbody></table>
<p class="muted">Formula: <code>BTI = (90d_unique_visitors / 50,000) × (90d_conversion / 0.025)</code>. Recalculated quarterly. Existing subscribers grandfathered until renewal. Founding partners immune to increases.</p>

<h2>8 · Founding Partner program</h2>
<ul>
<li>First 25 partners per type (100 total) during the 2-month outreach window</li>
<li>Locked at Standard × 0.75 for 5 years</li>
<li>Immune to BTI surge increases; benefits from BTI decreases (wins both ways)</li>
<li>"Founding Partner" badge displayed publicly</li>
<li>One-time eligibility, non-renewable</li>
</ul>

<h2>9 · Music Video Library (P2 backlog, non-revenue)</h2>
<p>Foundation-curated playlist on YouTube/YouTube Music. Embeds available in workshop chat / breakout rooms. Lyric videos created by participants/facilitators under Creative Commons for educational use. Available to facilitators AND participants. <span class="b">Explicitly not monetized.</span></p>

<h2>10 · Revenue stream audit</h2>
<table><thead><tr><th>Stream</th><th>Status</th></tr></thead><tbody>
<tr><td>Foundation IP workshop tickets · subscriptions · vendor on-site · workshop materials · community referrals</td><td class="green">Live</td></tr>
<tr><td>Off-site (outbound) referrals · sponsored / featured placement · research paid promotion · funding-introduction commission</td><td class="gold">New in v1.11.0</td></tr>
<tr><td>Participant referral store credit</td><td class="gold">Added to v1.11.0 (this revision)</td></tr>
<tr><td>Facilitator certification fee (~$500 one-time) · workshop-supply bundle margin (5-10%) · Annual Symposium tickets · Foundation-recommended tool affiliate</td><td>Queued for v1.12.0</td></tr>
</tbody></table>

<h2>11 · Remaining defaults (will apply unless you object)</h2>
<div class="qbox"><span class="pill pill-locked">Default</span> <span class="b">BTI baselines:</span> 50K visitors / 90 days · 2.5% conversion (parity threshold)</div>
<div class="qbox"><span class="pill pill-locked">Default</span> <span class="b">Pre-traction multiplier:</span> Start at × 0.50 immediately (rather than wait for live BTI measurement)</div>
<div class="qbox"><span class="pill pill-locked">Default</span> <span class="b">Founding partner cap:</span> 25 per type / 100 total</div>
<div class="qbox"><span class="pill pill-locked">Default</span> <span class="b">Transparency page:</span> <code>/governance/revenue-sharing</code> publishes BTI value publicly</div>
<div class="qbox"><span class="pill pill-locked">Default</span> <span class="b">Eminence Sharing Agreement:</span> I draft v1 inline with v1.6.0 indemnification (you/legal can refine before launch)</div>
<div class="qbox"><span class="pill pill-locked">Default</span> <span class="b">Indemnification extension:</span> v1.6.0 expands to cover partner work</div>
<div class="qbox"><span class="pill pill-locked">Default</span> <span class="b">Volume bonus thresholds:</span> 25 / 50 / 100 conversions/yr → +2% / +2% / +4%</div>
<div class="qbox"><span class="pill pill-locked">Default</span> <span class="b">3 proposed v1.12.0 streams:</span> certification fees, supply-bundle margin, symposium tickets, tool-affiliate → queued for v1.12.0 (avoids v1.11.0 bloat)</div>
<p class="muted">If silent, all defaults apply when v1.11.0 implementation begins.</p>

<footer>Birthright Foundation · <em>Secure Bonds &gt; Thrive</em> · v2 LOCKED — May 24, 2026 · supersedes v1</footer>
"""

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><title>Birthright Pricing v2</title><style>{CSS}</style></head><body>{body}</body></html>"""

html_path = TMP / "v2.html"
html_path.write_text(html)

pdf_out = OUT / "birthright-pricing-proposal-v2.pdf"
subprocess.run(
    ["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
     "--no-pdf-header-footer", f"--print-to-pdf={pdf_out}", f"file://{html_path}"],
    check=True, capture_output=True,
)
print(f"Generated: {pdf_out.name} ({pdf_out.stat().st_size} bytes)")
