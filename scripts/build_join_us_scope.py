"""Generate the Join Us + Sample Profiles scope PDF and refresh versions PDF."""
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
h2 { font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:22px;
     color:#2E5C46; margin:26px 0 8px 0; border-left:4px solid #C9A961; padding-left:10px; }
h3 { font-family:"Cormorant Garamond",Georgia,serif; font-size:17px;
     margin:16px 0 4px 0; color:#1A2424; }
.role-title { font-family:"Cormorant Garamond",Georgia,serif; font-size:19px;
              color:#476B6B; margin:0; }
p,li { font-size:12.5px; }
ul,ol { margin:6px 0 10px 22px; }
table { width:100%; border-collapse:collapse; font-size:11px; margin:8px 0 12px 0;
        background:#fff; box-shadow:0 1px 2px rgba(0,0,0,.05); }
thead th { background:#476B6B; color:#FAF8F5; text-align:left; padding:7px 9px;
           font-size:10px; text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
td { padding:6px 9px; border-bottom:1px solid #E5E1D8; vertical-align:top; }
tr:nth-child(even) td { background:#F4F1EA; }
code { background:#F4F1EA; padding:1px 5px; border-radius:3px; font-size:10.5px; }
.b { font-weight:700; }
.muted { color:#5C6B6B; font-style:italic; }
.gold { color:#8B7128; font-weight:600; }
.green { color:#2E5C46; font-weight:600; }
.pill { display:inline-block; padding:2px 9px; border-radius:10px; font-size:10px;
        text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
.pill-sample { background:#C9A961; color:#1A2424; }
.pill-open { background:#476B6B; color:#FAF8F5; }
.pill-equity { background:#2E5C46; color:#FAF8F5; }
.role-card { background:#fff; border:1px solid #E5E1D8; border-radius:6px;
             padding:14px 18px; margin:10px 0; }
.persona-card { background:#fff; border:1px solid #E5E1D8; border-radius:6px;
                padding:12px 16px; margin:8px 0; font-size:12px; }
.persona-card .name { font-family:"Cormorant Garamond",Georgia,serif; font-size:16px;
                      color:#476B6B; font-weight:600; }
.persona-meta { font-size:10.5px; color:#5C6B6B; margin:2px 0 6px 0; }
.callout { background:#FFFBEF; border-left:4px solid #C9A961; padding:10px 14px;
           margin:10px 0; font-size:12px; }
.callout-mission { background:#ECF3EE; border-left:4px solid #2E5C46;
                   padding:10px 14px; margin:10px 0; font-size:12px; }
footer { margin-top:24px; font-size:9.5px; color:#5C6B6B; text-align:center;
         border-top:1px solid #E5E1D8; padding-top:9px; }
.pagebreak { page-break-before: always; }
"""

# ============================================================
# JOIN US + SAMPLE PROFILES SCOPE PDF
# ============================================================

join_us_body = f"""
<h1>Join Us — Foundation Roles &amp; Sample Profiles</h1>
<div class="subtitle">Birthright Foundation · Scope v1 · Exported {TS}</div>

<div class="callout-mission">
<span class="b">Two related additions, one UI pass.</span> Both ship alongside v1.11.0 Step 7
(the <code>/partners</code> directory + transparency-page rebuild). Same designer hour, two outcomes:
(1) advertise the 3 open foundation roles to fill leadership before founding-partner outreach;
(2) seed sample partner profiles so founding-partner prospects can see what "great" looks like
before they apply.
</div>

<h2>1 · Open Foundation Roles (the 3 currently placeholder seats)</h2>
<p class="muted">All roles are <span class="b">equity-in-mission</span> — Birthright is a not-for-profit and does not currently provide monetary compensation. These are leadership / stewardship roles for people who want to shape a foundation focused on secure bonds and human thriving. Stipends, honoraria, and grant-funded engagement may emerge as funding allows.</p>

<div class="role-card">
<h3 class="role-title">🪶 Board Chair &amp; Co-Founder</h3>
<div class="persona-meta"><span class="pill pill-open">Open Role</span> &nbsp; <span class="pill pill-equity">Equity in Mission</span> &nbsp; Time: ~6–8 hrs/month + quarterly board meetings</div>
<p><span class="b">Who you are:</span> A senior practitioner whose career bridges clinical work and community building. You hold (or have held) a clinical credential — psychiatry, psychology, family medicine, social work, or a comparable license — and you've moved from individual practice toward systems-level relational education. You're comfortable with governance: chairing meetings, mediating board disagreements, shepherding strategic direction.</p>
<p><span class="b">What you'll do:</span> Chair the governing board. Sign off on major strategic decisions, partnership agreements above material thresholds, and final approvals on the rev-share governance defaults. Be the public face of the foundation alongside the executive director. Recruit board successors.</p>
<p><span class="b">What you bring:</span> Doctorate in clinical psychology, psychiatry, family medicine, or related field. 15+ years of practice. Demonstrated nonprofit board experience. Capacity to commit 5+ years.</p>
</div>

<div class="role-card">
<h3 class="role-title">🪶 Research Advisor</h3>
<div class="persona-meta"><span class="pill pill-open">Open Role</span> &nbsp; <span class="pill pill-equity">Equity in Mission</span> &nbsp; Time: ~4–6 hrs/month + quarterly research-council meetings</div>
<p><span class="b">Who you are:</span> A scholar of attachment, developmental psychology, family systems, or trauma-informed practice. Active or recently active in academic or applied research — peer-reviewed publications, IRB-supervised studies, or methodologically serious practitioner work. You believe the foundation's curriculum and impact claims should be grounded in evidence, and you're willing to shepherd that translation.</p>
<p><span class="b">What you'll do:</span> Chair the foundation's research council. Vet incoming research-partner applications. Co-author the foundation's annual evidence brief. Advise on outcome-measurement instruments embedded in the workshop platform (pre/post surveys, longitudinal follow-up cadence). Guide the foundation's standards for what counts as a publishable "Birthright" research artifact and how DOIs are minted.</p>
<p><span class="b">What you bring:</span> Doctorate in psychology, social work, family medicine, or related field. Active peer-reviewed publication record in attachment, relational, or developmental research. Comfortable with both quantitative and qualitative methods. Capacity to commit 3+ years.</p>
</div>

<div class="role-card">
<h3 class="role-title">🪶 Director of Community Stewardship</h3>
<div class="persona-meta"><span class="pill pill-open">Open Role</span> &nbsp; <span class="pill pill-equity">Equity in Mission</span> &nbsp; Time: ~10 hrs/week</div>
<p><span class="b">Who you are:</span> A community elder — ordained, lay, or both — with a track record of holding space for groups doing hard relational work. You're comfortable training facilitators, mediating disputes between partners, and ensuring the foundation's work remains rooted in the lived experience of the people we serve rather than drifting into academic abstraction.</p>
<p><span class="b">What you'll do:</span> Oversee facilitator training and certification. Serve as the foundation's first-line ombudsman for participant and partner concerns. Curate the foundation's relationships with faith communities, recovery communities, and other partner organizations whose work overlaps with ours. Provide pastoral / elder presence at major foundation events.</p>
<p><span class="b">What you bring:</span> Ordained ministry, chaplaincy, or comparable community-elder credential preferred. Demonstrated experience training group facilitators. Capacity to model the relational presence the work itself requires.</p>
</div>

<div class="callout">
<span class="b">How applications flow.</span> Each role page (<code>/join-us/&lt;role-slug&gt;</code>) has an "Apply" button → simple form (name, email, current role, why you're drawn to this work, attach résumé/CV optional) → application lands in <code>/admin/foundation-applications</code> queue → admin reviews, schedules interviews, decides. No indemnification flow needed for applications themselves — that comes after offer acceptance via the standard partner agreement flow.
</div>

<div class="pagebreak"></div>

<h2>2 · Governance Page updates</h2>
<ul>
<li>Existing board member cards (Dr. Aurelia Mendez, James Reagan, Reverend Tomas Ifeanyi) get a prominent <span class="pill pill-sample">SAMPLE — ROLE WE'RE SEEKING TO FILL</span> ribbon</li>
<li>Bio text adjusted to lead with "We're looking for someone like this:" followed by the existing descriptive text reframed as a portrait of the ideal candidate</li>
<li>"Apply for this role →" link from each card jumps to the matching <code>/join-us/&lt;slug&gt;</code> listing</li>
<li>New "Join us" CTA bar on <code>/governance</code> above the board grid: <span class="muted">"These three seats are currently open. We're seeking founding leadership for the foundation."</span></li>
</ul>

<h2>3 · Sample Partner Personas (8 across 4 partner types)</h2>
<p class="muted">Each persona is a real <code>partner_profiles</code> row with <code>is_sample: true</code>. Hidden from the default <code>/partners</code> directory; visible at <code>/partners?samples=1</code> and at <code>/partners/sample-&lt;slug&gt;</code>. Every page shows a prominent <span class="pill pill-sample">SAMPLE</span> ribbon. Admin can edit them like real profiles.</p>

<h3 class="gold">🎓 Facilitators (2 personas)</h3>

<div class="persona-card">
<div class="name">Dr. Maya Chen, LCSW</div>
<div class="persona-meta">Trauma-informed facilitator · Portland, OR · <span class="pill pill-equity">Founding tier</span></div>
<p>Fifteen years clinical practice with adult children of relational trauma. Brings Foundation IP workshops to weekend retreats hosted at a partner studio in the Columbia Gorge. Maya represents the practitioner who already has a thriving private practice and wants Birthright's curriculum + community + virtual venue to extend her reach without rebuilding infrastructure herself.</p>
<p><span class="muted">Profile shows: 3 upcoming workshops, 47 completed registrations, 4.9★ aggregate rating, 12 published reflections, Eminence Sharing not applicable.</span></p>
</div>

<div class="persona-card">
<div class="name">Aaron Kalu</div>
<div class="persona-meta">Movement &amp; somatic facilitator · Brooklyn, NY · Annual tier</div>
<p>Background in dance and Authentic Movement. Hosts non-IP workshops blending somatic exploration with Birthright's relational frameworks. Represents the facilitator who mostly runs their own content but values Birthright as venue + checkout + cross-pollination with other facilitators' participants.</p>
<p><span class="muted">Profile shows: monthly studio gatherings, 24 completed participants, 4.8★, external Substack link with off-site attribution active.</span></p>
</div>

<h3 class="gold">🛍️ Vendors (2 personas)</h3>

<div class="persona-card">
<div class="name">Quiet Hours Studio (Sam Rivera)</div>
<div class="persona-meta">Linen-bound journals, prints, reflection cards · Asheville, NC · <span class="pill pill-equity">Founding tier</span></div>
<p>One-person bindery making journals and prompt decks aligned with relational practice. Sam represents the small-batch craft vendor: 12 products in the catalog, three of which are bundled into Foundation workshop checkouts as optional supplements. Customer experience integrated end-to-end so participants don't bounce off-platform for their workshop supplies.</p>
<p><span class="muted">Profile shows: 12 products, $4,200 lifetime gross, 4.9★ on 3 of the products, foundation events have purchased 2 bulk orders.</span></p>
</div>

<div class="persona-card">
<div class="name">Hearth Practice (digital studio)</div>
<div class="persona-meta">Guided audio meditations, downloadable workbooks · Remote · 2-Year tier</div>
<p>Digital-only vendor producing audio meditations and supplementary workbooks. Represents the lower-overhead vendor type — no physical inventory, instant fulfilment, sells through Birthright as primary distribution. Listed external site URL routes outbound clicks through Birthright's attribution tracker.</p>
<p><span class="muted">Profile shows: 8 products, all digital, $1,800 lifetime gross, average margin 88% (no shipping cost).</span></p>
</div>

<h3 class="gold">🤝 Community Partners (2 personas)</h3>

<div class="persona-card">
<div class="name">Reverend Pat Lindholm</div>
<div class="persona-meta">Lutheran congregation · Madison, WI · <span class="pill pill-equity">Founding tier · 2-Year Pro</span></div>
<p>Senior pastor whose congregation runs grief and trauma support groups. Refers congregants to Birthright workshops as a complementary resource. Represents the faith-leader community partner — high-trust, low-volume, mission-aligned referrals from a single congregation network of ~300 active families.</p>
<p><span class="muted">Profile shows: 6 referred conversions YTD, 14% locked share, monthly digest active.</span></p>
</div>

<div class="persona-card">
<div class="name">Liz Okonkwo</div>
<div class="persona-meta">Wellness influencer &amp; podcaster · Atlanta, GA · Plus tier</div>
<p>Independent podcaster on healing and relationship work, 28K Instagram followers. Mentions Birthright workshops on the podcast with a UTM-tagged referral link. Represents the digital-creator community partner: higher volume, paid Plus tier for custom UTM analytics, drives ~25–40 conversions per quarter when she actively promotes.</p>
<p><span class="muted">Profile shows: 31 referred conversions YTD, 10% share, +2% volume bonus active.</span></p>
</div>

<div class="pagebreak"></div>

<h3 class="gold">🔬 Research Partners (2 personas)</h3>

<div class="persona-card">
<div class="name">Dr. Imani Okafor</div>
<div class="persona-meta">Academic researcher · University of Michigan · <span class="pill pill-equity">Founding tier · Citation Pro 2-Year</span></div>
<p>Tenure-track in developmental psychology. Studies attachment outcomes in adoptive and foster families. Publishes peer-reviewed findings through Birthright as one of several distribution channels. Represents the academic research partner — eminence-driven, foundation gains credibility from her affiliation, she gains a public-facing channel and DOI minting through the foundation.</p>
<p><span class="muted">Profile shows: 4 approved publications, 2 with DOIs minted, citation analytics active, Eminence Sharing Agreement signed.</span></p>
</div>

<div class="persona-card">
<div class="name">Daniel Brookes, LMFT</div>
<div class="persona-meta">Practitioner-researcher · Independent · Standard (Free)</div>
<p>Family therapist who publishes case studies and practice briefs distilled from his clinical work. Not affiliated with any university; uses Birthright as his sole publishing platform. Represents the practitioner-researcher persona — publishes 2–4 briefs per year, no monetization, contributes to the foundation's library of practitioner wisdom in exchange for credibility and discoverability.</p>
<p><span class="muted">Profile shows: 6 approved case studies, no monetized items, free tier, ESA signed.</span></p>
</div>

<h2>4 · Implementation notes (within v1.11.0 Step 7's UI pass)</h2>
<table><thead><tr><th>Backend</th><th>Frontend</th></tr></thead><tbody>
<tr>
<td>
<ul>
<li>New collection <code>foundation_roles</code></li>
<li>New collection <code>foundation_role_applications</code></li>
<li>New endpoints: public <code>/api/foundation-roles[/{{slug}}]</code>; applicant <code>POST /api/foundation-role-applications</code>; admin CRUD + queue</li>
<li>Seed 3 role rows at runtime via <code>runtime_seed</code></li>
<li>New <code>is_sample</code> flag on <code>partner_profiles</code></li>
<li>Seed 8 sample profiles at runtime, idempotent by slug</li>
<li>Existing 3 board-member rows auto-marked <code>is_sample: true</code> + linked to role slugs</li>
</ul>
</td>
<td>
<ul>
<li>New page <code>/join-us</code> (browse roles)</li>
<li>New page <code>/join-us/&lt;role-slug&gt;</code> (role detail + apply)</li>
<li>New page <code>/admin/foundation-roles</code> (admin CRUD)</li>
<li>New page <code>/admin/foundation-applications</code> (review queue)</li>
<li>Governance page updated: SAMPLE ribbon + "Apply for this role →" link on each board card</li>
<li><code>/partners?samples=1</code> reveals sample personas inline; sample ribbon on each</li>
<li>"Join Us" tab added to <code>/partners</code> tabbed picker</li>
</ul>
</td>
</tr>
</tbody></table>

<h2>5 · Why this slot in the roadmap</h2>
<ul>
<li><span class="b">Step 7 of v1.11.0 already rebuilds <code>/partners</code></span> — adding a 5th tab + sample-toggle in the same UI pass is incremental work, not a separate iteration</li>
<li><span class="b">Founding-partner outreach starts in ~2 months</span> — sample profiles ARE the sales tool prospects need; shipping later means losing the window</li>
<li><span class="b">3 board seats need filling before founding partners arrive</span> — partners shouldn't be the foundation's first community without leadership in place</li>
<li><span class="b">Foundation roles share ~80% of partner-application data model</span> — building applications fresh would create code that needs reconciliation later</li>
</ul>

<footer>Birthright Foundation · <em>Secure Bonds &gt; Thrive</em> · Join Us + Sample Profiles scope · For review</footer>
"""

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<title>Birthright Join Us Scope</title><style>{CSS}</style>
</head><body>{join_us_body}</body></html>"""
(TMP / "join_us.html").write_text(html)

pdf = OUT / "birthright-join-us-scope-v1.pdf"
subprocess.run(
    ["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
     "--no-pdf-header-footer", f"--print-to-pdf={pdf}", f"file://{TMP / 'join_us.html'}"],
    check=True, capture_output=True,
)
print(f"Generated: {pdf.name} ({pdf.stat().st_size} bytes)")
