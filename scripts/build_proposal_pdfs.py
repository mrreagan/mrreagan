"""Rebuild Birthright proposal PDFs from canonical content.

Run: python /app/scripts/build_proposal_pdfs.py
Output: /app/backend/static/exports/*.pdf
"""
from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

OUT = Path("/app/backend/static/exports")
TMP = Path("/tmp")
TS = dt.datetime.utcnow().strftime("%b %d, %Y %H:%M UTC")

SHARED_CSS = """
@page { size: Letter; margin: 0.55in; }
body { font-family:-apple-system,"Helvetica Neue",Arial,sans-serif; color:#1A2424; background:#FAF8F5;
       padding:24px 32px; line-height:1.45; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
h1 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:30px;
     border-bottom:2px solid #C9A961; padding-bottom:8px; margin:0 0 6px 0; }
.subtitle { font-size:11px; letter-spacing:.13em; text-transform:uppercase; color:#5C6B6B; margin-bottom:22px; }
h2 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:22px; color:#2E5C46;
     margin:26px 0 8px 0; border-left:4px solid #C9A961; padding-left:10px; }
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
pre { background:#F4F1EA; padding:10px 14px; border-left:3px solid #C9A961; font-size:10.5px;
      white-space:pre-wrap; }
.b { font-weight:700; }
.gold { color:#8B7128; font-weight:600; }
.green { color:#2E5C46; font-weight:600; }
.red { color:#B86A5C; font-weight:600; }
.muted { color:#5C6B6B; font-style:italic; }
.callout { background:#FFFBEF; border-left:4px solid #C9A961; padding:10px 14px; margin:10px 0; font-size:12px; }
.callout-mission { background:#ECF3EE; border-left:4px solid #2E5C46; padding:10px 14px; margin:10px 0; font-size:12px; }
.callout-warn { background:#FBEDE9; border-left:4px solid #B86A5C; padding:10px 14px; margin:10px 0; font-size:12px; }
.qbox { background:#fff; border:1px solid #E5E1D8; border-radius:4px; padding:12px 14px; margin:8px 0; font-size:12px; }
.step { background:#fff; border:1px solid #E5E1D8; border-radius:4px; padding:12px 14px; margin:8px 0; }
.step h4 { margin:0 0 5px 0; font-family:"Cormorant Garamond",Georgia,serif; color:#476B6B; font-size:15px; }
.step-num { background:#C9A961; color:#1A2424; font-weight:700; padding:2px 9px; border-radius:10px; font-size:10.5px; margin-right:8px; }
.test-line { color:#2E5C46; font-size:11px; font-style:italic; margin-top:4px; }
.pill { display:inline-block; padding:2px 9px; border-radius:10px; font-size:10px;
        text-transform:uppercase; letter-spacing:.07em; font-weight:600; background:#476B6B; color:#FAF8F5; }
footer { margin-top:24px; font-size:9.5px; color:#5C6B6B; text-align:center;
         border-top:1px solid #E5E1D8; padding-top:9px; }
.pagebreak { page-break-before: always; }
"""


def wrap(title: str, body: str) -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8" />
<title>{title}</title><style>{SHARED_CSS}</style></head><body>{body}</body></html>"""


def to_pdf(html_path: Path, pdf_name: str) -> None:
    out = OUT / pdf_name
    subprocess.run(
        [
            "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out}",
            f"file://{html_path}",
        ],
        check=True, capture_output=True,
    )
    print(f"  → {pdf_name}  ({out.stat().st_size} bytes)")


# ============================================================
# 1) PRICING PROPOSAL
# ============================================================

pricing_body = f"""
<h1>Subscription Pricing — Market Analysis &amp; Proposal</h1>
<div class="subtitle">Birthright Foundation · Secure Bonds &gt; Thrive · Exported {TS}</div>

<div class="callout-mission">
<span class="b">Mission alignment.</span> Birthright is a not-for-profit; subscription pricing must capture value
where partners benefit financially while remaining genuinely accessible — and never charge those who help us
(community referrers, researchers building eminence). This proposal threads that needle with a
<span class="b">traffic-adjusted multiplier</span> that grows with proof of value, free tiers for non-revenue partners,
and an explicit <span class="b">eminence-sharing</span> mechanism for academic contributors.
</div>

<h2>1 · Honest baseline assumption</h2>
<p>Birthright is <span class="b">pre-traction</span>: limited organic search visibility, no paid acquisition, public launch just completed.
Charging marketplace-grade rates today would be dishonest. Every recommendation below is anchored to a
<span class="b">Birthright Traffic Index (BTI)</span> that rises only when we prove value.</p>

<h2>2 · Market benchmarks per partner class</h2>

<h3 class="gold">🎓 Facilitator class (instructor / creator)</h3>
<table><thead><tr><th>Platform</th><th>Subscription</th><th>Take rate on courses</th><th>Notes</th></tr></thead><tbody>
<tr><td>Teachable</td><td>$39–$199/mo</td><td>5–10% transaction</td><td>Industry leader</td></tr>
<tr><td>Thinkific</td><td>$0–$199/mo</td><td>0% at higher tiers</td><td>Self-serve</td></tr>
<tr><td>Kajabi</td><td>$149–$399/mo</td><td>0%</td><td>High-end</td></tr>
<tr><td>Mighty Networks</td><td>$41–$179/mo</td><td>2–5%</td><td>Community-focused</td></tr>
<tr><td>Coursera Plus partners</td><td>Rev-share only</td><td>40–60% to platform</td><td>Marketplace</td></tr>
<tr style="background:#FFFBEF;"><td class="b">Birthright (current seed)</td><td>$99/mo – $1,799 (2 yr)</td><td>30–50% to platform</td><td><span class="red">High side</span></td></tr>
</tbody></table>
<p class="callout"><span class="b">Verdict:</span> Subscription price in range; on-site take rate priced like a marketplace without marketplace traffic. Keep subscription; lower facilitator take pre-traction; let BTI surge it as traffic proves out.</p>

<h3 class="gold">🛍️ Vendor class</h3>
<table><thead><tr><th>Platform</th><th>Subscription</th><th>Take rate</th><th>Notes</th></tr></thead><tbody>
<tr><td>Etsy</td><td>Free + $0.20/listing</td><td>6.5% + payment fees</td><td>Massive traffic</td></tr>
<tr><td>Shopify</td><td>$39–$399/mo</td><td>0%</td><td>Self-hosted</td></tr>
<tr><td>Amazon Handmade</td><td>$39.99/mo</td><td>15% referral</td><td>Curated marketplace</td></tr>
<tr><td>Faire (wholesale)</td><td>Free</td><td>15–25% commission</td><td>Curated, lower traffic</td></tr>
<tr style="background:#FFFBEF;"><td class="b">Birthright (current seed)</td><td>$49/mo – $899 (2 yr)</td><td>18–25% to platform</td><td><span class="green">Fair for curated, low traffic</span></td></tr>
</tbody></table>
<p class="callout"><span class="b">Verdict:</span> Vendor subscription is competitive vs Faire-style curated peers. Take rate at the high end of acceptable today — BTI will moderate as traffic grows.</p>

<h3 class="gold">🤝 Community / Affiliate class</h3>
<table><thead><tr><th>Platform</th><th>Subscription</th><th>Referral %</th><th>Notes</th></tr></thead><tbody>
<tr><td>Amazon Associates</td><td>Free</td><td>1–10%</td><td>Massive scale</td></tr>
<tr><td>ShareASale</td><td>Free (merchants pay)</td><td>5–20%</td><td>Affiliate network</td></tr>
<tr><td>Impact.com</td><td>Free</td><td>10–30%</td><td>Higher-touch</td></tr>
<tr><td>Substack referral</td><td>Free</td><td>30% (first year)</td><td>Lifetime tier exists</td></tr>
<tr style="background:#FBEDE9;"><td class="b">Birthright (current seed)</td><td>$29/mo – $549 (2 yr)</td><td>8–12% to community</td><td><span class="red">Subscription is uncommon</span></td></tr>
</tbody></table>
<p class="callout-warn"><span class="b">Verdict:</span> Charging affiliates a subscription contradicts industry norms. <span class="b">Recommendation: free entry tier</span> + paid upgrade tiers.</p>

<h3 class="gold">🔬 Research class</h3>
<table><thead><tr><th>Platform</th><th>Subscription</th><th>Model</th></tr></thead><tbody>
<tr><td>ResearchGate</td><td>Free</td><td>Ad / recruitment</td></tr>
<tr><td>Academia.edu</td><td>$99/yr Premium</td><td>Reader analytics, citation alerts</td></tr>
<tr><td>SSRN</td><td>Free</td><td>Endowment-funded</td></tr>
<tr><td>Substack (academic)</td><td>Free</td><td>10% on paid subscribers</td></tr>
<tr style="background:#FBEDE9;"><td class="b">Birthright (current seed)</td><td>$49/mo – $899 (2 yr)</td><td>0% rev share — <span class="red">too high for value delivered today</span></td></tr>
</tbody></table>
<p class="callout-warn"><span class="b">Verdict:</span> Academic platforms are mostly free. <span class="b">Recommendation: free baseline + paid à-la-carte promotion + Eminence-Sharing Agreement.</span></p>

<div class="pagebreak"></div>

<h2>3 · Eminence Sharing — formalizing non-monetary value</h2>
<table><thead><tr><th>Mechanism</th><th>Foundation gets</th><th>Researcher gets</th></tr></thead><tbody>
<tr><td>Co-citation requirement</td><td>Cited as platform / publisher</td><td>Discoverability in academic search</td></tr>
<tr><td>Press release co-rights</td><td>Right to press-release findings with attribution</td><td>Mainstream visibility beyond academia</td></tr>
<tr><td>Speaking-engagement first-right</td><td>Right of first invitation</td><td>Paid speaking gigs via foundation</td></tr>
<tr><td>Endorsement clause</td><td>Public endorsement on LinkedIn / ORCID</td><td>Credibility lift on profile</td></tr>
<tr><td>Funding-introduction commission</td><td>2–3% of grants from foundation-initiated intros</td><td>Warm intros to funders</td></tr>
<tr><td>Data co-ownership</td><td>Half-owns anonymized workshop datasets</td><td>Research access to joint dataset</td></tr>
</tbody></table>
<p class="callout"><span class="b">Proposal:</span> Approved research partners sign an <span class="b">Eminence Sharing Agreement</span> as an addendum to the v1.6.0 indemnification flow. <span class="b">No subscription required.</span></p>

<h2>4 · Traffic-Adjusted Pricing — the Birthright Traffic Index (BTI)</h2>
<div class="callout"><span class="b">Formula.</span> &nbsp;<code>BTI = (rolling_90d_unique_visitors / 50,000) × (rolling_90d_conversion / 0.025)</code>
<ul><li>50,000 visitors / 90 days = threshold where Etsy/Faire-equivalent rates become defensible</li>
<li>2.5% conversion = standard e-commerce baseline</li>
<li>BTI = 1.0 means "comparable to competitors"</li></ul></div>

<table><thead><tr><th>BTI range</th><th class="num">Multiplier</th><th>Plain English</th></tr></thead><tbody>
<tr><td>0.0 – 0.2</td><td class="num"><span class="b">× 0.50</span></td><td>Pre-traction discount — half price</td></tr>
<tr><td>0.2 – 0.5</td><td class="num"><span class="b">× 0.70</span></td><td>Early launch tier</td></tr>
<tr><td>0.5 – 1.0</td><td class="num"><span class="b">× 0.85</span></td><td>Approaching parity</td></tr>
<tr style="background:#ECF3EE;"><td class="b">1.0 – 1.5</td><td class="num"><span class="b">× 1.00</span></td><td><span class="green">Standard market rate</span></td></tr>
<tr><td>1.5 – 2.5</td><td class="num"><span class="b">× 1.15</span></td><td>Premium — outperforming competitors</td></tr>
<tr><td>2.5+</td><td class="num"><span class="b">× 1.30</span></td><td>Hard cap on surge</td></tr>
</tbody></table>

<ul>
<li>Recalculated on the first of each quarter</li>
<li>Existing subscribers grandfathered at signup rate until renewal</li>
<li>Founding partners immune to surge increases, still enjoy surge decreases</li>
<li>Published transparently at <code>/governance/revenue-sharing</code></li>
<li>Per-partner admin overrides allowed (governance audit-logged)</li>
</ul>

<div class="pagebreak"></div>

<h2>5 · Recommended subscription matrix — pre-traction (BTI × 0.5)</h2>
<p class="muted">Pre-traction $ = standard × 0.5. Standard applies at BTI = 1.0. Founding partners pay standard × 0.75, locked 5 years.</p>

<h3 class="gold">🎓 Facilitator</h3>
<table><thead><tr><th>Plan</th><th class="num">Pre-traction $</th><th class="num">Standard $</th><th>On-site take (IP / Non-IP)</th><th class="num">Off-site take</th></tr></thead><tbody>
<tr><td>Monthly</td><td class="num">$49</td><td class="num">$99</td><td>25% / 50% → 30% / 50%</td><td class="num">5% → 10%</td></tr>
<tr><td>Annual</td><td class="num">$499</td><td class="num">$999</td><td>22% / 45% → 35% / 55%</td><td class="num">7% → 12%</td></tr>
<tr><td>2-Year</td><td class="num">$899</td><td class="num">$1,799</td><td>20% / 40% → 40% / 60%</td><td class="num">10% → 15%</td></tr>
</tbody></table>

<h3 class="gold">🛍️ Vendor</h3>
<table><thead><tr><th>Plan</th><th class="num">Pre-traction $</th><th class="num">Standard $</th><th class="num">On-site take</th><th class="num">Off-site take</th></tr></thead><tbody>
<tr><td>Monthly</td><td class="num">$25</td><td class="num">$49</td><td class="num">15% → 18%</td><td class="num">3% → 5%</td></tr>
<tr><td>Annual</td><td class="num">$249</td><td class="num">$499</td><td class="num">18% → 22%</td><td class="num">5% → 7%</td></tr>
<tr><td>2-Year</td><td class="num">$449</td><td class="num">$899</td><td class="num">22% → 25%</td><td class="num">7% → 10%</td></tr>
</tbody></table>

<h3 class="gold">🤝 Community / Affiliate — Free entry</h3>
<table><thead><tr><th>Plan</th><th class="num">Pre-traction $</th><th class="num">Standard $</th><th class="num">Their referral share</th><th>What higher tiers add</th></tr></thead><tbody>
<tr style="background:#ECF3EE;"><td class="b">Starter</td><td class="num"><span class="green b">FREE</span></td><td class="num"><span class="green b">FREE</span></td><td class="num">8%</td><td>Basic referral link + analytics</td></tr>
<tr><td>Plus</td><td class="num">$9/mo</td><td class="num">$19/mo</td><td class="num">10%</td><td>Custom UTM links, monthly digest, public profile</td></tr>
<tr><td>Pro</td><td class="num">$49/yr</td><td class="num">$99/yr</td><td class="num">12%</td><td>Featured listing eligibility, top-of-directory rotation</td></tr>
<tr><td>2-Year Pro</td><td class="num">$79</td><td class="num">$159</td><td class="num">12% locked</td><td>Founding eligibility</td></tr>
</tbody></table>

<h3 class="gold">🔬 Research — Free entry + Eminence Sharing Agreement</h3>
<table><thead><tr><th>Plan</th><th class="num">Pre-traction $</th><th class="num">Standard $</th><th>What it includes</th></tr></thead><tbody>
<tr style="background:#ECF3EE;"><td class="b">Standard</td><td class="num"><span class="green b">FREE</span></td><td class="num"><span class="green b">FREE</span></td><td>Submit research, public profile, chronological listing, Eminence Sharing terms apply</td></tr>
<tr><td>Featured (à la carte)</td><td class="num">$29/wk or $99/mo</td><td class="num">$49/wk or $179/mo</td><td>Homepage rotation, top of category, expanded mission alignment, video embed</td></tr>
<tr><td>Citation Pro</td><td class="num">$49/yr</td><td class="num">$99/yr</td><td>Citation analytics, DOI minting assistance, press-release co-rights</td></tr>
</tbody></table>
<p class="muted">On-site rev share: foundation gets <span class="b">5%</span> on monetized research items. Off-site: <span class="b">3%</span>.</p>

<h3 class="gold">💎 Founding Partner overlay (all classes)</h3>
<ul>
<li>First <span class="b">25 partners per type</span> (100 total) during the 2-month outreach window</li>
<li>Locked at <span class="b">Standard × 0.75</span> for <span class="b">5 years</span></li>
<li>Immune to BTI surge increases; still benefits from BTI decreases</li>
<li>"Founding Partner" badge displayed publicly</li>
<li>One-time eligibility, non-renewable</li>
</ul>

<div class="pagebreak"></div>

<h2>6 · Mission alignment check</h2>
<table><thead><tr><th>Concern raised</th><th>How this addresses it</th></tr></thead><tbody>
<tr><td>"Don't charge people who help us"</td><td>Community + Research move to <span class="green b">FREE</span> entry</td></tr>
<tr><td>"Capture value where appropriate"</td><td>Vendors + Facilitators (revenue-generating) still subscribe; eminence captured from researchers</td></tr>
<tr><td>"Don't price-gouge on low traffic"</td><td>BTI multiplier × 0.5 today; transparently published</td></tr>
<tr><td>"Surge when we outperform"</td><td>BTI × 1.15–1.30 at scale</td></tr>
<tr><td>"Workers worthy of wages"</td><td>Founding partner discount recognizes early believers</td></tr>
<tr><td>"Not primarily a money-making org"</td><td>Foundation share scales with partner revenue — we eat only when they eat</td></tr>
</tbody></table>

<h2>7 · Final confirmations before implementation</h2>
<div class="qbox"><span class="pill">Q1</span> <span class="b">BTI formula.</span> Use 50K visitors / 2.5% conversion as parity baselines, or adjust?</div>
<div class="qbox"><span class="pill">Q2</span> <span class="b">Free Community + Free Research entry</span> — structural change from existing $29 / $49 subscriptions — confirmed?</div>
<div class="qbox"><span class="pill">Q3</span> <span class="b">Eminence Sharing Agreement</span> — draft v1 inline with v1.6.0 indemnification, or punt to outside counsel and just wire the toggle?</div>
<div class="qbox"><span class="pill">Q4</span> <span class="b">Pre-traction multiplier</span> — start at × 0.50 immediately, or × 1.00 until BTI measured live?</div>
<div class="qbox"><span class="pill">Q5</span> <span class="b">Founding partner cap</span> — 25 per type / 100 total confirmed?</div>
<div class="qbox"><span class="pill">Q6</span> <span class="b">Transparency page</span> at <code>/governance/revenue-sharing</code> — publish BTI value publicly, or admin-only?</div>

<footer>Birthright Foundation · <em>Secure Bonds &gt; Thrive</em> · Pricing proposal · For review &amp; approval</footer>
"""

# ============================================================
# 2) PHASE 6B.5 SCOPE
# ============================================================

phase_body = f"""
<h1>Phase 6B.5 — Research Submissions Queue</h1>
<div class="subtitle">Birthright Foundation · Scope v1 · Exported {TS}</div>

<div class="callout"><span class="b">Status:</span> P0 backlog — paused pending v1.11.0 (Partner Economy Completion) so that subscription tier,
featured-state, and rev-share defaults exist before research economics are wired in.</div>

<h2>1 · Purpose</h2>
<p>Give approved Research Partners a way to publish briefs, case studies, white papers, and findings through
Birthright — and give the foundation editorial control plus a public showcase that builds credibility.</p>

<h2>2 · Personas</h2>
<table><thead><tr><th>Who</th><th>What they do</th></tr></thead><tbody>
<tr><td class="b">Research Partner</td><td>Submits research items, tracks status, edits drafts, replies to admin feedback</td></tr>
<tr><td class="b">Admin / Ombudsman</td><td>Reviews queue, approves, requests revisions, unpublishes, attaches editorial notes</td></tr>
<tr><td class="b">Public visitor</td><td>Browses approved research at <code>/partners?tab=research</code>, opens detail pages, downloads PDF if attached</td></tr>
<tr><td class="b">Participant</td><td>Leaves a polymorphic review on a research item (reuses v1.5.0)</td></tr>
</tbody></table>

<h2>3 · Data model — new <code>research_submissions</code> collection</h2>
<pre>id, slug
partner_id, partner_user_id              (FK → partner_profiles)
title, abstract, body_markdown
research_type: brief | case-study | white-paper | findings | publication
topic_tags: ["secure-attachment","trauma-informed", ...]
methodology: qualitative | quantitative | mixed | meta-analysis | other
citation, doi, external_url
attachment_url                            (optional — PDF in /static/research/)
hero_image_url
status: draft | submitted | in_review | approved | revisions_requested | unpublished
admin_note, admin_reviewer_id, reviewed_at
submitted_at, approved_at, unpublished_at, created_at, updated_at
view_count, download_count</pre>

<h2>4 · Backend API — new <code>routers/research.py</code></h2>

<h3 class="gold">Researcher self-serve (active research partner profile required)</h3>
<ul>
<li><code>GET    /api/research/my-submissions</code></li>
<li><code>POST   /api/research/submissions</code> (starts as draft)</li>
<li><code>PUT    /api/research/submissions/{{id}}</code> (draft + revisions_requested only)</li>
<li><code>POST   /api/research/submissions/{{id}}/submit</code> (draft → submitted)</li>
<li><code>DELETE /api/research/submissions/{{id}}</code> (draft only)</li>
<li><code>POST   /api/research/submissions/{{id}}/upload-attachment</code> (PDF, ≤ 15 MB)</li>
</ul>

<h3 class="gold">Admin moderation</h3>
<ul>
<li><code>GET   /api/admin/research?status=…</code></li>
<li><code>POST  /api/admin/research/{{id}}/approve</code></li>
<li><code>POST  /api/admin/research/{{id}}/request-revisions</code> (body: admin_note)</li>
<li><code>POST  /api/admin/research/{{id}}/unpublish</code></li>
<li><code>POST  /api/admin/research/{{id}}/restore</code></li>
</ul>

<h3 class="gold">Public</h3>
<ul>
<li><code>GET /api/research</code> (approved only; filters: type, topic, methodology, partner)</li>
<li><code>GET /api/research/{{slug}}</code> (404 unless approved OR caller is owner/admin)</li>
</ul>

<div class="pagebreak"></div>

<h2>5 · Frontend pages</h2>
<table><thead><tr><th>Route</th><th>Who</th><th>What</th></tr></thead><tbody>
<tr><td><code>/dashboard/research</code></td><td>Researcher</td><td>Submissions table with status badges; inline editor drawer; "Submit for review" CTA</td></tr>
<tr><td><code>/admin/research</code></td><td>Admin</td><td>Cross-partner moderation queue with tabs; approve / request-revisions / unpublish / restore</td></tr>
<tr><td><code>/partners?tab=research</code></td><td>Public</td><td>Card grid of approved research with topic/type/methodology filters</td></tr>
<tr><td><code>/research/{{slug}}</code></td><td>Public</td><td>Article-style detail with hero, byline, abstract, body, citation, PDF download, related research, reviews (v1.5.0)</td></tr>
<tr><td>Partner profile</td><td>Public</td><td>Adds "Published research" section listing approved items by that partner</td></tr>
<tr><td><code>/dashboard/partner</code></td><td>Researcher</td><td>"Manage research" CTA on research partner profile cards</td></tr>
</tbody></table>

<h2>6 · Email touchpoints</h2>
<ul>
<li>Submitter: confirmation on submit; decision email on approve / request-revisions / unpublish</li>
<li>Admins: optional daily digest of new submissions awaiting review</li>
</ul>

<h2>7 · Acceptance criteria</h2>
<ul>
<li>Non-research-partner users see a clean access-denied state at <code>/dashboard/research</code></li>
<li>Submitted items become read-only to the submitter until status flips back to revisions_requested</li>
<li>Approved items appear at <code>/partners?tab=research</code> within seconds</li>
<li>Unpublished items return 404 to public; remain editable for admin + owner</li>
<li>All status transitions in audit log</li>
</ul>

<h2>8 · Open decisions</h2>
<div class="qbox"><span class="pill">Q1</span> <span class="b">PDF attachments</span> — required, or optional? (Recommended: optional)</div>
<div class="qbox"><span class="pill">Q2</span> <span class="b">Externally-published work</span> — allowed via DOI / external_url, or original-to-platform only?</div>
<div class="qbox"><span class="pill">Q3</span> <span class="b">Reviews on research items</span> — reuse v1.5.0 polymorphic reviews, or read-only?</div>
<div class="qbox"><span class="pill">Q4</span> <span class="b">Editorial workflow</span> — single-tier (admin approves) or two-step (ombudsman pre-screen → admin final)?</div>
<div class="qbox"><span class="pill">Q5</span> Anything else before kickoff?</div>

<footer>Birthright Foundation · <em>Secure Bonds &gt; Thrive</em> · Phase 6B.5 scope · For review</footer>
"""

# ============================================================
# 3) V1.11.0 SCOPE & PLAN
# ============================================================

v111_body = f"""
<h1>v1.11.0 — Partner Economy Completion</h1>
<div class="subtitle">Birthright Foundation · Scope &amp; Implementation Plan v1 · Exported {TS}</div>

<div class="callout-mission">
<span class="b">Why insert this before Phase 6B.5.</span> Research submissions, communications, and advanced search will
all gate behaviour on subscription tier, featured state, and rev-share defaults. Building those features first
would force a refactor of three routers to add economics later.
</div>

<h2>1 · Scope lock-in</h2>

<h3 class="gold">A · Off-site attribution — hybrid with adversarial reconciliation</h3>
<ul>
<li><code>outbound_clicks</code> collection captures every click-through to a partner's external site</li>
<li>Self-report panel on <code>/dashboard/partner</code> — partner enters monthly attributed revenue</li>
<li>Webhook ingestion: <code>POST /api/webhooks/partner/{{partner_id}}/sales</code></li>
<li>Reconciliation dashboard shows self-report ↔ webhook side-by-side with delta % + 🚩 if delta &gt; tolerance</li>
<li>Light estimation engine: <code>outbound_clicks × industry_avg_conv × estimated_AOV</code>; flag ±30% deviations</li>
<li>Partnership agreement clause: material misreporting forfeits partnership + clawback rights</li>
</ul>

<h3 class="gold">B · Founding Partner program</h3>
<ul>
<li>First 25 partners per type (100 total) lock standard × 0.75 for 5 years</li>
<li>Admin-only toggle; "Founding Partner" badge publicly</li>
<li>Available only via admin invite</li>
</ul>

<h3 class="gold">C · Hybrid featured sponsorship</h3>
<ul>
<li>Admin invite-only initially (governance-aligned)</li>
<li>Featured partners get top of <code>/partners</code> in their category, gold badge, extended profile (mission alignment, signature content, video embed, image slots, custom CTA), homepage rotation</li>
</ul>

<h3 class="gold">D · Rev-share defaults + governance overrides</h3>
<ul>
<li>Per-partner override fields respecting v1.6.0 governance audit log</li>
<li>Admin sets via <code>/admin/partners/{{id}}/rev-share-override</code> with reason → audit log entry</li>
</ul>

<h3 class="gold">E · Research economics</h3>
<ul>
<li>Research subscriptions move to <span class="green b">FREE entry</span> + paid à-la-carte promotion</li>
<li>Featured Research $99/mo · Highlighted Research $29/week (one-time Stripe charges)</li>
<li>Extended research profile: "Why this matters" + "Alignment with Birthright mission" sections</li>
<li>On-site rev share: 5% on monetized research; off-site: 3%</li>
</ul>

<h3 class="gold">F · Catch-all items (added proactively)</h3>
<table><thead><tr><th>What</th><th>Why now</th></tr></thead><tbody>
<tr><td>Payout thresholds + cadence (min $50, monthly on the 15th)</td><td>Industry standard</td></tr>
<tr><td>W-9 / W-8BEN collection flow</td><td>Required before first US payout</td></tr>
<tr><td>1099-NEC export for admins</td><td>Year-end tax compliance for ≥ $600 payouts</td></tr>
<tr><td>Clawback policy + workflow</td><td>Promised in §A; needs admin action + audit trail</td></tr>
<tr><td>Refund-handling cascade</td><td>Stripe refunds auto-reverse linked referral rows</td></tr>
<tr><td>Partner agreement versioning</td><td>Tier-change diff page for explicit acceptance</td></tr>
<tr><td>Currency-ready data model</td><td><code>currency</code> field included now; no future refactor</td></tr>
<tr><td>Public transparency page <code>/governance/revenue-sharing</code></td><td>Publishes BTI + rates aligned with foundation values</td></tr>
</tbody></table>

<div class="pagebreak"></div>

<h2>2 · Implementation plan (10 independently-testable steps)</h2>

<div class="step"><h4><span class="step-num">1</span> Data model + rev-share defaults migration</h4>
Extend <code>PartnerProfile</code>: <code>is_founding_partner</code>, <code>founding_rate_expires_at</code>, <code>featured_until</code>, <code>featured_*</code> fields, <code>external_site_url</code>, <code>rev_share_overrides</code>, <code>w9_status</code>, <code>payout_threshold_usd</code>, <code>payout_method</code>, <code>payout_address_snapshot</code>.
Update <code>seed_subscription_plans.py</code> with new defaults.
New collections: <code>outbound_clicks</code>, <code>partner_sales_reports</code>, <code>research_promotions</code>.
<div class="test-line">Test: ruff + 5 unit tests for new fields/collections.</div></div>

<div class="step"><h4><span class="step-num">2</span> Outbound click tracker + estimation engine</h4>
<code>GET /api/out/{{partner_slug}}?dest=…&amp;utm_*=*</code> inserts row, 302 redirects. Frontend routes all external buttons through this.
<code>compute_estimated_revenue(partner_id, period)</code>: clicks × 2.5% conv × $45 AOV.
<div class="test-line">Test: click 5 outbound links → rows inserted; estimation plausible.</div></div>

<div class="step"><h4><span class="step-num">3</span> Self-reporting + reconciliation</h4>
<code>POST /api/partner/sales-reports</code> + HMAC-verified webhook ingestion.
<code>GET /api/partner/sales-reconciliation</code> (self vs webhook vs estimated) + admin aggregate.
<div class="test-line">Test: seed conflicting values → reconciliation math + flags trigger.</div></div>

<div class="step"><h4><span class="step-num">4</span> Featured / Founding flags + admin tools</h4>
<code>POST /api/admin/partners/{{id}}/feature</code>, <code>unfeature</code>, <code>founding</code>, <code>rev-share-override</code>. Public sort: featured first.
<div class="test-line">Test: feature a partner → sorts to top + extended fields + badge.</div></div>

<div class="step"><h4><span class="step-num">5</span> Research paid promotion</h4>
<code>/promote/featured</code> ($99/mo) + <code>/promote/highlighted</code> ($29/wk) Stripe checkouts. Webhook fulfilment + daily expiry job.
<div class="test-line">Test: purchase → active → simulate expiry → deactivates.</div></div>

<div class="step"><h4><span class="step-num">6</span> Payout infrastructure</h4>
W-9/W-8BEN upload (admin-only access). Payout threshold check. Monthly job on the 15th bundles into <code>payout_batches</code>. 1099-NEC CSV export.
<div class="test-line">Test: seed referral → run job → batch created → CSV export.</div></div>

<div class="step"><h4><span class="step-num">7</span> Subscription UI parity + transparency</h4>
Redesign <code>/partners/subscribe</code> as 4-type tabbed picker. Public <code>/governance/revenue-sharing</code> page. Partner reconciliation dashboard at <code>/dashboard/partner/economics</code>.
<div class="test-line">Test: all 4 types view + purchase; public page loads without auth.</div></div>

<div class="step"><h4><span class="step-num">8</span> Refund + clawback cascade</h4>
Stripe <code>charge.refunded</code> handler auto-reverses linked referrals + audit entry. Admin "Claw back referral" action.
<div class="test-line">Test: Stripe test refund → referral flips to <code>clawed_back</code>.</div></div>

<div class="step"><h4><span class="step-num">9</span> Documentation + legal binding</h4>
Partnership-agreement-v2 auto-attached to v1.6.0 indemnification flow. Existing partners get re-sign requirement.
<div class="test-line">Test: new partner sees v2 + signature recorded.</div></div>

<div class="step"><h4><span class="step-num">10</span> Full regression + Phase 6B.5 prep</h4>
Full regression suite. PRD.md + CHANGELOG.md updates.
<div class="test-line">Test: 77+ pytest green; smoke test all 4 partner types end-to-end.</div></div>

<p class="callout"><span class="b">Estimated total:</span> 2 medium iterations. Testing agent called at end of Steps 1–3, 4–6, 7–9; full regression at Step 10.</p>

<h2>3 · Related documents</h2>
<ul>
<li>Pricing tables, BTI multiplier, founding economics — <code>birthright-pricing-proposal-v1.pdf</code></li>
<li>Platform version context — <code>birthright-versions.pdf</code></li>
<li>Downstream feature — <code>birthright-phase-6b5-research-scope-v1.pdf</code></li>
</ul>

<footer>Birthright Foundation · <em>Secure Bonds &gt; Thrive</em> · v1.11.0 scope + implementation plan</footer>
"""

# ============================================================
# Render + emit
# ============================================================

targets = [
    ("birthright-pricing-proposal-v1.pdf",
     wrap("Birthright — Pricing Proposal", pricing_body)),
    ("birthright-phase-6b5-research-scope-v1.pdf",
     wrap("Birthright — Phase 6B.5 Scope", phase_body)),
    ("birthright-v1.11-partner-economy-scope-v1.pdf",
     wrap("Birthright — v1.11.0 Scope", v111_body)),
]

print(f"Build at {TS}")
print("Generating PDFs:")
for fname, html in targets:
    html_path = TMP / fname.replace(".pdf", ".html")
    html_path.write_text(html)
    to_pdf(html_path, fname)

print("Done.")
