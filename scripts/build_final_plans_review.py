"""Generate the final review PDF for subscription + rev-share + referral plans.
Reads live values from the DB so the document reflects the current seeded state."""
from __future__ import annotations

import asyncio
import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from database import db  # noqa: E402

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
     margin:16px 0 6px 0; color:#1A2424; }
p,li { font-size:12.5px; }
ul,ol { margin:6px 0 10px 22px; }
table { width:100%; border-collapse:collapse; font-size:11px; margin:8px 0 6px 0;
        background:#fff; box-shadow:0 1px 2px rgba(0,0,0,.05); }
thead th { background:#476B6B; color:#FAF8F5; text-align:left; padding:7px 9px;
           font-size:10px; text-transform:uppercase; letter-spacing:.07em; font-weight:600; }
td { padding:6px 9px; border-bottom:1px solid #E5E1D8; vertical-align:top; }
tr:nth-child(even) td { background:#F4F1EA; }
td.num,th.num { text-align:right; font-variant-numeric:tabular-nums; }
code { background:#F4F1EA; padding:1px 5px; border-radius:3px; font-size:10.5px; }
.b { font-weight:700; }
.gold { color:#8B7128; font-weight:600; }
.green { color:#2E5C46; font-weight:600; }
.muted { color:#5C6B6B; font-style:italic; }
.rationale { background:#FFFBEF; border-left:4px solid #C9A961; padding:10px 14px;
             margin:6px 0 18px 0; font-size:11.5px; }
.rationale .b { color:#8B7128; }
.lock { background:#ECF3EE; border-left:4px solid #2E5C46; padding:10px 14px;
        margin:10px 0; font-size:12px; }
.review-banner { background:#476B6B; color:#FAF8F5; padding:10px 14px;
                 border-radius:4px; font-size:12px; margin-bottom:14px; text-align:center; }
footer { margin-top:24px; font-size:9.5px; color:#5C6B6B; text-align:center;
         border-top:1px solid #E5E1D8; padding-top:9px; }
.pagebreak { page-break-before: always; }
sup { font-size:9px; color:#8B7128; font-weight:700; }
"""


async def gather_plans() -> dict[str, list[dict]]:
    by_type: dict[str, list[dict]] = {}
    async for p in db.subscription_plans.find({"active": True}, {"_id": 0}):
        by_type.setdefault(p["partner_type"], []).append(p)
    for t in by_type:
        by_type[t].sort(key=lambda x: x["duration_months"])
    return by_type


def fmt_price(p: float) -> str:
    return "FREE" if p == 0 else f"${p:,.2f}"


def fmt_pct(p) -> str:
    if p is None:
        return "—"
    return f"{p:g}%"


def plan_row_facilitator(p: dict) -> str:
    return (
        f"<tr><td class='b'>{p['name']}</td>"
        f"<td class='num'>{fmt_price(p['price_usd'])}</td>"
        f"<td class='num'>{fmt_pct(p.get('foundation_ip_pct'))}</td>"
        f"<td class='num'>{fmt_pct(p.get('non_ip_pct'))}</td>"
        f"<td class='num'>{fmt_pct(p.get('off_site_pct'))}</td></tr>"
    )


def plan_row_vendor(p: dict) -> str:
    return (
        f"<tr><td class='b'>{p['name']}</td>"
        f"<td class='num'>{fmt_price(p['price_usd'])}</td>"
        f"<td class='num'>{fmt_pct(p.get('default_pct'))}</td>"
        f"<td class='num'>{fmt_pct(p.get('off_site_pct'))}</td></tr>"
    )


def plan_row_community(p: dict) -> str:
    return (
        f"<tr><td class='b'>{p['name']}</td>"
        f"<td class='num'>{fmt_price(p['price_usd'])}</td>"
        f"<td class='num'>{fmt_pct(p.get('default_pct'))}</td></tr>"
    )


def plan_row_research(p: dict) -> str:
    return (
        f"<tr><td class='b'>{p['name']}</td>"
        f"<td class='num'>{fmt_price(p['price_usd'])}</td>"
        f"<td class='num'>{fmt_pct(p.get('default_pct'))}</td>"
        f"<td class='num'>{fmt_pct(p.get('off_site_pct'))}</td></tr>"
    )


async def main() -> None:
    plans = await gather_plans()

    fac_rows = "\n".join(plan_row_facilitator(p) for p in plans.get("facilitator", []))
    ven_rows = "\n".join(plan_row_vendor(p) for p in plans.get("vendor", []))
    com_rows = "\n".join(plan_row_community(p) for p in plans.get("community", []))
    res_rows = "\n".join(plan_row_research(p) for p in plans.get("research", []))

    body = f"""
<h1>Subscription, Rev-Share &amp; Referral Plans — Final Review</h1>
<div class="subtitle">Birthright Foundation · Secure Bonds &gt; Thrive · Exported {TS}</div>

<div class="review-banner">
<span class="b">REVIEW DOCUMENT.</span> These are the plans currently seeded in the database (pre-traction × 0.5 multiplier applied).
Approve to commit to git → next deploy goes live. Reject any line to revise before commit.
</div>

<h2>1 · Facilitator subscriptions</h2>
<table><thead><tr>
<th>Plan</th>
<th class="num">Fee</th>
<th class="num">Foundation IP<sup>1</sup><br/>(foundation share)</th>
<th class="num">Non-IP<sup>2</sup><br/>(foundation share)</th>
<th class="num">Off-site<sup>3</sup></th>
</tr></thead><tbody>{fac_rows}</tbody></table>

<div class="rationale">
<span class="b">Rationale.</span>
<sup>1</sup> <span class="b">Foundation IP rev-share</span> applies when the facilitator hosts a workshop using Birthright-curated curriculum, methodology, or branded materials. Foundation share decreases from 50% → 42% → 35% as commitment lengthens — rewarding longer subscriptions with better take-home for the facilitator. <span class="b">35% is a hard floor</span> that can only be reduced via admin override + governance audit log (per v1.6.0).
<br/><sup>2</sup> <span class="b">Non-IP rev-share</span> applies when a facilitator hosts their own workshops with their own content using Birthright as the venue + marketing + checkout layer. Foundation share is much lower (20% → 15% → 10%) because we don't own the IP — we're competing with Teachable/Thinkific and must stay attractive.
<br/><sup>3</sup> <span class="b">Off-site rev-share</span> applies when a participant clicks through from a facilitator's Birthright profile to the facilitator's external site and buys there. Foundation captures 7% → 5% → 3% — fair recognition of attribution + traffic without overstepping on revenue we don't process.
<br/><br/><span class="b">Why subscription fees exist at all.</span> The fee primarily buys the <span class="b">right to teach Foundation IP workshops</span>. There is no facilitator-only material library (materials are activating, not conceptual, and are participant-purchased). Facilitators who only run non-IP workshops can evaluate whether the subscription's other benefits (integrated payouts, indemnification, marketing assets, virtual venue, cross-pollination) are worth the cost — competitive vs Teachable/Thinkific/Kajabi.
</div>

<h2>2 · Vendor subscriptions</h2>
<table><thead><tr>
<th>Plan</th>
<th class="num">Fee</th>
<th class="num">On-site<sup>1</sup><br/>(foundation share)</th>
<th class="num">Off-site<sup>2</sup></th>
</tr></thead><tbody>{ven_rows}</tbody></table>

<div class="rationale">
<span class="b">Rationale.</span>
<sup>1</sup> <span class="b">On-site rev-share</span> on every vendor product sold through Birthright's store. Foundation share decreases from 22% → 17% → 12% with commitment. Competitive vs Faire (15–25%) and Amazon Handmade (15%), and far below the take rate of a high-traffic marketplace — appropriate given Birthright is curated + pre-traction.
<br/><sup>2</sup> <span class="b">Off-site rev-share</span>: when a vendor lists their external store URL on their Birthright profile and a Birthright visitor clicks through and buys, foundation captures 7% → 5% → 3%. Reflects attribution + traffic delivered, nothing more.
<br/><br/><span class="b">Why vendor fees are lower than facilitator fees.</span> Vendors don't access any Foundation IP — they're paying for distribution + checkout infrastructure + AI mockup generation + zero listing fees + workshop-bundle access for foundation events. The fee floors at $24.50/mo (pre-traction) so the barrier to entry is genuinely low for niche craftspeople aligned with the mission.
</div>

<div class="pagebreak"></div>

<h2>3 · Community / Affiliate plans</h2>
<table><thead><tr>
<th>Plan</th>
<th class="num">Fee</th>
<th class="num">Their referral share<sup>1</sup></th>
</tr></thead><tbody>{com_rows}</tbody></table>

<div class="rationale">
<span class="b">Rationale.</span>
<sup>1</sup> <span class="b">This is the COMMUNITY PARTNER's share</span>, not the foundation's. When a community partner sends an inbound referral that converts on Birthright, the partner keeps 8% → 10% → 12% → 14% of the purchase value. Foundation keeps the remainder. <span class="b">Higher commitment = higher partner share</span> — the inverse direction of facilitator/vendor because here we're paying THEM, and we want to keep good affiliates.
<br/><br/><span class="b">Volume bonuses</span> stack on top of the base share for paid tiers: +2% after 25 conversions/yr · +2% more after 50 · +4% more after 100. Significantly outpaces Amazon Associates (1-10%) and is competitive with Impact.com (10-30%).
<br/><br/><span class="b">Why FREE Starter.</span> Charging affiliates a subscription contradicts every industry norm (Amazon Associates, ShareASale, Impact.com, Substack — all free for affiliates). The Free tier removes the friction; paid tiers (Plus / Pro / 2-Year Pro) add specific benefits like custom UTM links, monthly digests, featured listing eligibility, locked rates.
</div>

<h2>4 · Research plans</h2>
<table><thead><tr>
<th>Plan</th>
<th class="num">Fee</th>
<th class="num">On-site share<sup>1</sup><br/>(foundation)</th>
<th class="num">Off-site share<sup>2</sup></th>
</tr></thead><tbody>{res_rows}</tbody></table>

<div class="rationale">
<span class="b">Rationale.</span>
<sup>1</sup> <span class="b">On-site rev-share</span> applies only when a research item is monetized (paid white paper, premium download). Foundation keeps 5% across all tiers — flat by design because most research is non-commercial.
<br/><sup>2</sup> <span class="b">Off-site rev-share</span> applies when Birthright traffic clicks through and buys a researcher's paid item elsewhere. Foundation captures 3% — low because the value researchers bring is primarily reputational (eminence), not monetary.
<br/><br/><span class="b">Why FREE Standard tier.</span> Academic platforms are mostly free (ResearchGate, SSRN); academics build careers on citation reach, not platform fees. Charging would suppress submissions and damage the foundation's credibility as a research host.
<br/><br/><span class="b">Eminence Sharing Agreement.</span> All approved research partners sign an addendum to v1.6.0 indemnification capturing non-monetary value: co-citation, press-release co-rights, speaking-engagement first-right, endorsement clause, funding-introduction commission (2-3% of foundation-introduced grants), data co-ownership of anonymized workshop datasets. This is how the foundation participates in the eminence the researcher builds.
<br/><br/><span class="b">À-la-carte paid promotion</span> exists separately as one-time Stripe charges: <span class="b">Featured Research $99/mo · Highlighted Research $29/wk</span>. Promoted research displays clear "Sponsored" microcopy for transparency.
</div>

<div class="pagebreak"></div>

<h2>5 · Product types &amp; material handling</h2>
<table><thead><tr><th>Type</th><th>Who can buy</th><th>Rev-share</th></tr></thead><tbody>
<tr><td class="b"><code>merch</code></td><td>Anyone</td><td>Foundation 100% or vendor split per their plan</td></tr>
<tr><td class="b"><code>workshop_material</code></td><td>ONLY paid registrants of that workshop</td><td><span class="b">Foundation 100%</span> (less Community referral if applicable)</td></tr>
<tr><td class="b"><code>facilitator_material</code> <span style="background:#C9A961;color:#1A2424;padding:1px 5px;border-radius:3px;font-size:9px">NEW</span></td><td>ONLY active Facilitator partner profiles</td><td>Foundation 100%</td></tr>
<tr><td class="b"><code>vendor_product</code></td><td>Anyone</td><td>Vendor's plan applies</td></tr>
</tbody></table>

<div class="rationale">
<span class="b">Rationale.</span>
Workshop materials are gated to <span class="b">paid registrants of that workshop only</span>. This protects Foundation IP from leakage (facilitators cannot bulk-buy and take materials out of the ecosystem) and increases participant agency, which is core to material efficacy.
<br/><br/><span class="b">No facilitator commission</span> on Foundation material purchases. Five reasons: (1) professional ethics codes (APA/ACA/NASW/ICF) prohibit dual-relationship financial benefits with clients; (2) facilitators are already fully compensated via subscription + workshop rev-share; (3) materials are bundled by the foundation, not curated by facilitators — nothing to compensate; (4) every $1 in commission is $1 not reinvested in better materials; (5) skipping commissions removes FTC #ad disclosure complications.
<br/><br/><span class="b">Required vs optional materials.</span> Required materials (<code>is_required: true</code>) auto-add to the workshop ticket at registration. Optional materials are nudged by the foundation directly (checkout, confirmation email, dashboard, mid-workshop reminders) — the facilitator is never the salesperson.
</div>

<h2>6 · Participant referrals — store credit, not cash</h2>
<table><thead><tr><th>Trigger</th><th class="num">Reward</th><th>Form</th></tr></thead><tbody>
<tr><td>Participant refers friend → friend completes a workshop</td><td class="num"><span class="b">15%</span> of friend's purchase</td><td>Store credit toward referrer's next purchase</td></tr>
</tbody></table>

<div class="rationale">
<span class="b">Rationale.</span> Store credit (not cash) avoids 1099 reporting, W-9 collection, payout-batch infrastructure, and FTC paid-endorsement complications. Credit applies to workshops, materials, OR merch — participant choice. Auto-applies at checkout (toggleable). Tracked via new <code>user_credits</code> ledger collection. Loops people back into the ecosystem rather than leaking cash out.
</div>

<h2>7 · Refund / clawback policy</h2>
<table><thead><tr><th>Cancel timing</th><th>Ticket refund</th><th>Material refund</th></tr></thead><tbody>
<tr><td>&gt; 72 hours before workshop</td><td class="green">Full</td><td class="green">Full</td></tr>
<tr><td>24–72 hours before</td><td class="green">Full</td><td>None</td></tr>
<tr><td>&lt; 24 hours before</td><td>None</td><td>None</td></tr>
<tr><td>Facilitator-initiated cancellation</td><td class="green">Full</td><td class="green">Full</td></tr>
</tbody></table>

<div class="rationale">
<span class="b">Rationale.</span> Mirrors industry standard for digital-product platforms. Stripe refunds trigger automatic referral-row clawback per the v1.11.0 Step 8 cascade — preserves data integrity in the payouts ledger.
</div>

<div class="pagebreak"></div>

<h2>8 · Cross-cutting principles (governance &amp; mechanics)</h2>

<h3 class="gold">A · BTI multiplier (traffic-adjusted pricing)</h3>
<table><thead><tr><th>BTI range</th><th class="num">Multiplier</th><th>Plain English</th></tr></thead><tbody>
<tr><td class='b'>0.0 – 0.2 (today)</td><td class='num'><span class='b'>× 0.50</span></td><td>Pre-traction discount — what is currently seeded</td></tr>
<tr><td>0.2 – 0.5</td><td class='num'>× 0.70</td><td>Early launch</td></tr>
<tr><td>0.5 – 1.0</td><td class='num'>× 0.85</td><td>Approaching parity</td></tr>
<tr><td>1.0 – 1.5</td><td class='num'>× 1.00</td><td>Standard market rate (the table values above × 2)</td></tr>
<tr><td>1.5 – 2.5</td><td class='num'>× 1.15</td><td>Premium — outperforming competitors</td></tr>
<tr><td>2.5+</td><td class='num'>× 1.30</td><td>Hard cap on surge</td></tr>
</tbody></table>
<div class="rationale">
<span class="b">BTI applies to subscription FEES only.</span> Rev-share percentages stay BTI-stable because partners' per-transaction income should be predictable. Quarterly recalculation. Existing subscribers grandfathered at signup rate until renewal. Founding partners immune to increases; still benefit from decreases.
<br/><br/>Formula: <code>BTI = (90d_unique_visitors / 50,000) × (90d_conversion / 0.025)</code>. Published transparently at <code>/governance/revenue-sharing</code> (to be built in v1.11.0 Step 7).
</div>

<h3 class="gold">B · Founding Partner program</h3>
<div class="rationale">
First 25 partners per type (100 total) get standard prices × 0.75 locked for 5 years from signup. Available only via admin invite during the 2-month outreach window. Immune to BTI surge increases (wins both ways: benefits from decreases too). Public "Founding Partner" badge.
<br/><br/><span class="b">What "standard" means here:</span> the BTI=1.0 rate (twice the currently-seeded pre-traction prices). So a Founding Facilitator Annual = $899 × 0.75 = $674/year, locked through 2031. As BTI rises and other partners see fees rise, founders stay at $674.
</div>

<h3 class="gold">C · Admin overrides &amp; rev-share exceptions</h3>
<div class="rationale">
The Foundation IP rev-share floor of 35% (foundation share) cannot drop below 35% via the normal commitment ladder. Admin overrides ARE allowed for special arrangements but must:
<ul>
<li>Include a written reason (≥10 chars) in the override request</li>
<li>Be recorded in the v1.6.0 audit log automatically</li>
<li>For high-value overrides, optionally trigger a governance proposal for review</li>
</ul>
This preserves the foundation's ability to make special-case arrangements (e.g., grant-funded research partners, signature facilitators, partnership pilots) while maintaining transparency.
</div>

<h2>9 · What's queued for v1.12.0 (not yet implemented)</h2>
<ul>
<li><span class="b">Facilitator certification fee</span> — one-time ~$500 to be vetted + listed (industry standard for therapy/coaching cert platforms)</li>
<li><span class="b">Workshop-supply bundle margin</span> — foundation curates vendor products into workshop kits; takes a 5–10% bundling margin</li>
<li><span class="b">Annual Research Symposium tickets</span> — public event; foundation sells tickets directly</li>
<li><span class="b">Foundation-recommended tool affiliate</span> — when foundation recommends Stripe / Resend / Notion etc., earn affiliate fees</li>
</ul>
<p class="muted">Queued for v1.12.0 to avoid v1.11.0 scope bloat. Each can be added without refactoring v1.11.0.</p>

<h2>10 · What's NOT being captured (intentional)</h2>
<ul>
<li><span class="b">Donations to partners through the site</span> — feels grabby; let donations flow directly</li>
<li><span class="b">Cross-partner collaboration fees</span> — adds complexity; revisit when partners ask</li>
<li><span class="b">Music video library</span> — Creative Commons curated playlists, explicitly non-monetized (P2 backlog)</li>
<li><span class="b">Data licensing beyond research</span> — privacy-sensitive; needs governance</li>
</ul>

<div class="lock">
<span class="b">Ready to commit.</span> All values shown reflect what's currently seeded in the database. Approve to commit to git and proceed with v1.11.0 Step 2 (outbound click tracker). Reject any specific line and I'll revise before commit.
</div>

<footer>Birthright Foundation · <em>Secure Bonds &gt; Thrive</em> · Final plans review · Generated from live DB seed</footer>
"""

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<title>Birthright Final Plans Review</title><style>{CSS}</style>
</head><body>{body}</body></html>"""
    html_path = TMP / "final_review.html"
    html_path.write_text(html)

    pdf_out = OUT / "birthright-final-plans-review-v1.pdf"
    subprocess.run(
        ["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
         "--no-pdf-header-footer", f"--print-to-pdf={pdf_out}", f"file://{html_path}"],
        check=True, capture_output=True,
    )
    print(f"Generated: {pdf_out.name} ({pdf_out.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
