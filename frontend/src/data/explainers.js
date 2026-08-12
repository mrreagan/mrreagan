/**
 * Central copy store for board-facing metric explainers across the admin
 * reports. Edit copy here — components render the popover automatically.
 *
 * Each entry has:
 *   title  — short label (usually matches the metric name)
 *   what   — plain-language description of what the metric shows
 *   math   — how it's calculated (skip if purely descriptive)
 *   why    — board-perspective: what decision it should influence
 */
const explainers = {
  // ═════════════════════════════════════════════════════════════════════
  //  Growth Model Simulator — page overview
  // ═════════════════════════════════════════════════════════════════════
  "growth.page": {
    title: "Facilitator network growth simulator",
    what: "An interactive 20-year projection of how the peer-led workshop network could scale. Every slider re-runs a 240-month simulation; the chart and table update live.",
    why: "The board needs one honest, tunable financial picture — not a static forecast. Reset the sliders when assumptions change, save 'Conservative / Moderate / Aggressive' snapshots for meeting minutes, and use the sensitivity tornado to focus attention on the two or three levers that actually move the needle.",
  },

  // -------- KPI tiles --------
  "growth.kpi.active": {
    title: "Active facilitators (end of year)",
    what: "The projected count of trained peer-led hosts still active at the end of the simulation horizon.",
    math: "Starts with seed facilitators, adds new hosts after a training lag, subtracts monthly attrition per cohort (Y1 = 35% by default, Y2 = 15%, Y3+ = 8% annually).",
    why: "This is the board's headline scale metric. Every dollar of workshop revenue and every $ of participant reach traces back to how many facilitators are actively hosting. If this number stalls, everything below stalls with it.",
  },
  "growth.kpi.participants": {
    title: "Participants (cumulative)",
    what: "Total workshop seats filled across the entire horizon, counting couples as 2 seats.",
    math: "Σ (active facilitators × workshops per year × couples per workshop × 2 × effective fill rate) across all years.",
    why: "Mission impact metric. When counsel or partners ask 'how many people has Birthright reached', this is the answer. Also the top of the growth funnel — participants → applicants → future facilitators.",
  },
  "growth.kpi.workshop_net": {
    title: "Workshop revenue (net of refunds)",
    what: "Cumulative gross workshop revenue across all facilitators minus refunds and chargebacks.",
    math: "Σ (workshops × couples-filled × $/couple) × (1 − refund rate). The 60/40 split into facilitator vs foundation happens on this net figure.",
    why: "The size of the total value flowing through the platform. Even the facilitator share is a foundation KPI — bigger facilitator earnings means more livelihood created and stronger retention.",
  },
  "growth.kpi.foundation_net": {
    title: "Foundation NET (cumulative)",
    what: "What the foundation actually keeps over the horizon, after refunds and after paying its own marketing costs.",
    math: "Foundation workshop share + subscription revenue + cross-role revenue − foundation marketing costs. Refunds are already removed from the workshop share.",
    why: "The one number board financial planning should hinge on. Everything else is a component. If you have to remember one figure from this dashboard, it's this.",
  },

  // -------- Chart --------
  "growth.chart": {
    title: "Facilitator network trajectory",
    what: "Line chart of active facilitators at the end of each simulated year.",
    why: "Shape matters more than absolute values here. A healthy peer-led network is an S-curve: slow ramp, sharp middle, plateau at market saturation. A hockey stick means the model is missing friction. A flat line means the loop isn't self-sustaining.",
  },

  // -------- Parameter groups (section headers) --------
  "growth.group.simulation": {
    title: "Simulation setup",
    what: "How far into the future the model projects and how many facilitators exist at time zero.",
    why: "Board reviews typically look at a 20-year horizon (matches most foundation strategic plans). Adjust seed count if you're modelling from a real cohort of existing hosts.",
  },
  "growth.group.workshop_econ": {
    title: "Workshop economics",
    what: "The unit economics of a single facilitator's activity: size, price, cadence, and curriculum mix.",
    why: "This is where you decide whether Birthright is a boutique high-price experience or a scaled affordable one. Small changes here compound heavily — see the Sensitivity view.",
  },
  "growth.group.take_matrix": {
    title: "Foundation take by tier × workshop type",
    what: "Six sliders defining how much of workshop revenue Birthright keeps, per subscription tier and per curriculum source. Facilitators keep the remainder.",
    math: "Effective foundation share = (workshops using IP % × IP-take rate) + (workshops using own material % × own-material take rate), computed per subscription tier and blended across the tenure mix.",
    why: "This matrix is the published pricing on birthright.live and legally binding on all counsel documents. Change with intent — every % point shift affects facilitator livelihoods and is a real business-model decision.",
  },
  "growth.group.growth_loop": {
    title: "Growth loop",
    what: "The recruitment funnel: participant → applicant → certified facilitator. Plus the decay of enthusiasm as the movement matures.",
    why: "The single most important set of levers. Tiny percentage-point moves here compound over 20 years into hundreds of millions. If the model shows disappointing numbers, this is where to look first.",
  },
  "growth.group.retention": {
    title: "Retention (cohort attrition)",
    what: "Annual dropout rate by tenure. New facilitators drop out fastest; tenured ones are much stickier.",
    math: "Applied monthly as 1 − (1 − annual)^(1/12). A 35% Y1 attrition means only ~65% of new hosts are still active at 12 months.",
    why: "Retention is a force multiplier. Cutting Y1 attrition from 35% to 25% often adds more to the 20-year total than any pricing change. Onboarding quality investments pay for themselves many times over.",
  },
  "growth.group.ramp": {
    title: "New-facilitator ramp-up",
    what: "How full a new facilitator's workshops are during their first months hosting. New hosts don't fill 100% right away.",
    math: "Fill rate scales linearly from the starting % (default 30%) at tenure 0 to 100% at the ramp-completion month (default 9 months).",
    why: "Explains why Year 1 revenue is always modest relative to the facilitator count. Mentorship and local-marketing support can compress the ramp — a real operational lever.",
  },
  "growth.group.geography": {
    title: "Geographic reach",
    what: "How the addressable market grows year by year. Instead of one national ceiling, we open metros over time, each with its own demand pool.",
    math: "Year Y market ceiling = (initial metros + new metros/year × (Y−1)) × couples per metro per year.",
    why: "Peer networks are inherently local. A national number that doubles every year is meaningless if we've only opened facilitators in 3 metros. This model forces the board to think about the operational reality of geographic expansion.",
  },
  "growth.group.demand_mix": {
    title: "Demand mix",
    what: "Where participants come from (referrals vs paid acquisition) and how many workshops each unique person attends.",
    why: "Referrals are the difference between a healthy movement and a marketing-dependent business. As referral share climbs, the CAC line drops and foundation NET climbs materially.",
  },
  "growth.group.costs": {
    title: "Costs & leakage",
    what: "Money that doesn't reach the foundation: refunds, chargebacks, and foundation-level participant acquisition marketing.",
    why: "Small numbers per participant become large aggregates. A single-point cut in refund rate typically saves 6–7 figures over 20 years.",
  },
  "growth.group.cross_role": {
    title: "Cross-role revenue",
    what: "Additional foundation revenue from tenured facilitators who take on roles as trainers, curriculum authors, or retreat leaders.",
    math: "Annual $/tenured facilitator, applied to facilitators past the tenure gate (default 24 months).",
    why: "A tenured-network revenue tail. It's small in early years, but becomes meaningful once you have thousands of veteran hosts. Signals the maturity of the ecosystem, not just its size.",
  },
  "growth.group.sub_tiers": {
    title: "Subscription tier prices",
    what: "What facilitators pay Birthright to be certified and included on the platform — monthly, annual, or 2-year commitments.",
    why: "The published pricing on birthright.live. Changes require a public price update and counsel review, so treat these as reference values — the sliders exist to explore what-ifs before touching public pricing.",
  },
  "growth.group.new_mix": {
    title: "New-facilitator subscription mix",
    what: "Distribution across monthly/annual/2-year plans among facilitators in their first year.",
    why: "New facilitators overwhelmingly pick monthly (default 85%) because they're uncertain about commitment. If this shifts toward annual, it's a strong signal of confidence in the platform.",
  },
  "growth.group.tenured_mix": {
    title: "Tenured subscription mix",
    what: "Same distribution but for facilitators past their first year, when they know the model works for them.",
    why: "Annual is labelled 'MOST CHOSEN' on the public pricing page — this default reflects that. As facilitators mature, they migrate to longer terms and Birthright's revenue becomes more predictable.",
  },

  // -------- Individual sliders (representative — grouped ones get one explainer) --------
  "growth.slider.years": {
    title: "Horizon",
    what: "How many years to simulate forward.",
    why: "20 is the standard foundation-planning horizon and lets the S-curve fully develop. Use 5 or 10 for near-term board discussions.",
  },
  "growth.slider.workshops_per_fac_yr": {
    title: "Workshops per facilitator / year",
    what: "How often each active facilitator hosts.",
    math: "12 = one workshop per month. 24 = biweekly. 52 = weekly.",
    why: "A facilitator who doubles their cadence roughly doubles their local impact and income. This is one of the top 4 sensitivity levers — small changes in cadence flow through to every downstream metric.",
  },
  "growth.slider.price_per_couple": {
    title: "Price per couple",
    what: "The published workshop ticket price for a couple to attend one workshop.",
    why: "Directly proportional to gross revenue, so raising 5% raises everything 5% — but affects access and could suppress conversion. Model both directions before proposing any change to counsel.",
  },
  "growth.slider.p_to_a": {
    title: "Participants → applicants %",
    what: "Percentage of workshop participants who apply to become a facilitator.",
    why: "The mouth of the funnel. Comparable peer networks (La Leche League, Landmark) see 1–4%. Movement branding, alumni programs, and testimonial content are the levers that move this up.",
  },
  "growth.slider.a_to_active": {
    title: "Applicants → active facilitators %",
    what: "Percentage of applicants who complete the interview process and become active hosts.",
    why: "Certification bar × onboarding quality. Setting this too high hurts scale; setting it too low hurts quality and downstream retention.",
  },
  "growth.slider.lag": {
    title: "Training lag (months)",
    what: "Time between attending a workshop as a participant and hosting one's first workshop.",
    why: "The 'time-to-first-value' for a new facilitator. Faster ramp → faster reinvestment of the loop.",
  },
  "growth.slider.conv_decay": {
    title: "Conversion decay / year %",
    what: "Annual reduction in the participant→applicant rate as the movement matures.",
    math: "Applied multiplicatively each year: rate(Y) = base × (1 − decay)^Y. At 10% decay, conversion halves in ~7 years.",
    why: "Early adopters are activists. Mainstream participants convert less. If your board is expecting steady-state performance identical to launch year, this lever tells them why that's unrealistic.",
  },
  "growth.slider.ip_mix": {
    title: "Workshops using Birthright IP",
    what: "Percentage of workshops taught using Birthright's curriculum vs the facilitator's own materials.",
    why: "Own-material workshops carry a 10-point higher foundation take (per published pricing). But too many facilitators drifting to own material dilutes brand consistency. This is a strategic tension the board should monitor.",
  },
  "growth.slider.ceiling_ceil": {
    title: "Couples per metro per year",
    what: "How many workshop-attending couples a fully-covered metro can supply annually.",
    why: "0.1% of metropolitan-area couples is a reasonable ceiling for niche relationship programs. Big metros (NYC, LA) can be higher; smaller markets much lower.",
  },
  "growth.slider.metros_init": {
    title: "Initial serviced metros",
    what: "How many metros are actively served by the seed facilitators at launch.",
    why: "Concentration matters early. Two facilitators in one city compete for the same demand. Spreading initial facilitators across metros lifts fill rate; clustering them lowers it.",
  },
  "growth.slider.metros_new": {
    title: "New metros / year",
    what: "How fast Birthright opens up newly-serviced metropolitan areas.",
    why: "The pacing lever for the whole model. Faster metro expansion needs corresponding facilitator training capacity and local marketing. Slower expansion means saturation and fill-rate collapse.",
  },
  "growth.slider.referral": {
    title: "Referral share %",
    what: "Percentage of new participants that come from existing-facilitator word-of-mouth (no paid CAC).",
    why: "The health of the movement. High referral share (>50%) means the network markets itself. Low means Birthright is essentially a facilitator-fronted marketing business.",
  },
  "growth.slider.multi_attend": {
    title: "Avg workshops per participant",
    what: "How many workshops the average unique couple attends over time.",
    why: "1.0 = every couple comes once. 1.5 = a substantial repeat-attendance economy. Grows gross revenue without needing to grow the facilitator network.",
  },
  "growth.slider.cac": {
    title: "Marketing / cold participant ($)",
    what: "Foundation-level marketing cost per cold participant acquired.",
    math: "Foundation marketing spend = unique cold participants × $ per acquisition. 'Cold' means not from a facilitator referral.",
    why: "The counterweight to Referral share. Every point higher here reduces Foundation NET one-for-one. Content marketing and community-building investments are what actually move this number down.",
  },
  "growth.slider.refund": {
    title: "Refund / chargeback rate %",
    what: "Percentage of workshop gross that gets refunded, disputed, or written off.",
    why: "3–8% is typical for consumer workshops. Trends here reveal delivery quality problems long before NPS surveys do.",
  },
  "growth.slider.cross_role_amt": {
    title: "Cross-role $/tenured facilitator / year",
    what: "Additional annual foundation revenue per veteran facilitator taking on trainer / author / retreat-leader roles.",
    why: "A revenue tail that matures with the network. When Birthright has 5,000+ veterans, this alone is meaningful.",
  },
  "growth.slider.take_matrix_cell": {
    title: "Foundation take (cell)",
    what: "For workshops in this tier × curriculum-type, the % of gross that Birthright retains.",
    why: "Published on birthright.live. Facilitators keep 100% − this value. Longer commitments (2-year) and Birthright IP both carry lower foundation take, rewarding both commitment and brand-loyalty.",
  },

  // -------- Yearly projection table columns --------
  "growth.col.year": {
    title: "Year",
    what: "Simulation year, 1-indexed. Y1 = the first 12 months after launch.",
    why: "Time frame reference for every other column in the row.",
  },
  "growth.col.active_eoy": {
    title: "Active EOY (end of year)",
    what: "Facilitators still active on the last day of that year, after all attrition and new activations.",
    why: "The snapshot you'd share with anyone asking 'how big is the network right now?' at that point.",
  },
  "growth.col.workshops": {
    title: "Workshops",
    what: "Total workshops delivered during that year.",
    math: "Σ (active facilitators × workshops per month) across the 12 months.",
    why: "The unit of value delivery. Every workshop is one live event, one facilitator paid, and one cohort of participants touched.",
  },
  "growth.col.participants": {
    title: "Participants",
    what: "Seats filled that year, counting couples as 2 seats.",
    math: "workshops × couples per workshop × fill rate × 2 (people per couple).",
    why: "The audience Birthright reaches in a year. Divide by 2 for unique couples served.",
  },
  "growth.col.wkshp_net": {
    title: "Workshop net $",
    what: "Total workshop revenue that year net of refunds — the pool split between facilitator and foundation.",
    math: "workshops × couples-filled × price/couple × (1 − refund rate).",
    why: "The value-flow through the platform. Facilitator earnings and foundation workshop share both come out of this pot.",
  },
  "growth.col.refunds": {
    title: "Refunds",
    what: "Cost of workshops refunded, disputed, or written off that year.",
    math: "workshop gross × refund rate. Distributed between facilitator and foundation in the same 60/40 split.",
    why: "Small per-workshop but adds up. Trends here signal delivery-quality issues faster than surveys.",
  },
  "growth.col.fac_earnings": {
    title: "Facilitator $ (earnings)",
    what: "Total earnings paid out to facilitators that year, after refunds.",
    math: "workshop net × (100% − foundation take). Foundation take varies by subscription tier and curriculum type.",
    why: "The livelihood generated for the peer-hosting community. Strong facilitator earnings drive retention, referrals, and the perception of Birthright as a real professional opportunity.",
  },
  "growth.col.fnd_wkshp": {
    title: "Foundation workshop $",
    what: "Birthright's share of workshop revenue that year, after refunds.",
    math: "workshop net × foundation take. Blended across active subscription tiers and IP/own-material mix.",
    why: "The largest of the three foundation revenue streams in most scenarios. Grows in lock-step with active facilitator count.",
  },
  "growth.col.subs": {
    title: "Subscription $",
    what: "Revenue from facilitators paying their monthly/annual/2-year platform subscription.",
    math: "Σ (facilitators in each tier × per-month price for that tier) across all months.",
    why: "The most predictable revenue line. Locked in when facilitators sign up, so it lags workshop revenue but is smoother.",
  },
  "growth.col.cross_role": {
    title: "Cross-role $",
    what: "Foundation revenue from tenured facilitators serving as trainers, authors, or retreat leaders that year.",
    math: "Active facilitators past the tenure gate × annual $/tenured × (months active in year / 12).",
    why: "The maturity revenue line. Near zero in early years; substantial once the veteran cohort is deep.",
  },
  "growth.col.mktg": {
    title: "Marketing − (cost)",
    what: "Foundation-level participant-acquisition marketing spent that year.",
    math: "Cold participants (non-referrals) × $/cold-participant.",
    why: "The one negative line in the foundation stack. Scales with unique participants served, so growing this proportionally is a warning sign that word-of-mouth isn't compounding.",
  },
  "growth.col.fnd_net": {
    title: "Foundation NET",
    what: "What Birthright actually keeps that year after all its costs.",
    math: "Fnd wkshp $ + Subs $ + Cross-role $ − Marketing $. Refunds are already removed from Fnd wkshp $.",
    why: "The bottom line. Everything else in this row is either a component of, or a check-figure for, this number.",
  },
  "growth.col.ceiling": {
    title: "Ceiling",
    what: "Total addressable couples/year across all serviced metros that year.",
    math: "(initial metros + new metros/year × (Y − 1)) × couples per metro per year.",
    why: "The demand-side reality check. When network demand exceeds ceiling, fill rate drops — the S-curve plateaus.",
  },
  "growth.col.fill": {
    title: "Fill (%)",
    what: "Average per-workshop capacity used across the year.",
    math: "New-facilitator ramp fraction × geographic-saturation fraction, averaged over 12 months.",
    why: "The health metric for demand. 100% early years = network under-supplying demand (opportunity for faster metro growth). Sub-30% = network over-supplying (over-recruited facilitators competing for the same couples).",
  },

  // -------- Scenarios panel --------
  "growth.scenarios": {
    title: "Saved scenarios",
    what: "Named snapshots of the current parameter set. Save Conservative / Moderate / Aggressive versions to compare them side-by-side on the growth chart.",
    why: "Board decisions are almost always relative: is Aggressive plausible? Is Conservative catastrophic? Overlaying the three curves on one axis makes the answer immediately visible without a spreadsheet.",
  },

  // -------- Sensitivity view --------
  "growth.sensitivity": {
    title: "Sensitivity analysis",
    what: "Runs 32 additional simulations (each of 16 key levers dialled ±20%) against your currently-loaded parameters. The tornado chart ranks levers by their impact on the 20-year Foundation NET.",
    math: "For each lever L: Δ+ = simulate(L × 1.20).net − base.net; Δ− = simulate(L × 0.80).net − base.net; range = |Δ+ − Δ−|. Sorted descending by range.",
    why: "Answers the question the board actually cares about: 'if we can only get 3 things right, which 3?' The top 3–4 bars typically account for >80% of the possible outcome variance. Focus meetings, hires, and investment there.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  Foundation reports (/admin/reports)
  // ═════════════════════════════════════════════════════════════════════
  "reports.page": {
    title: "Foundation reports",
    what: "Snapshot of foundation-wide engagement, revenue, and print-on-demand economics as of right now.",
    why: "The 'how are we doing today' page — meant as a companion to the growth-model projections. Numbers here are actuals; growth-model numbers are futures.",
  },
  "reports.engagement.users": {
    title: "Users",
    what: "Total registered accounts (all roles: members, artists, facilitators, admins, partners).",
    why: "The audience Birthright has built to date. Compare growth over time to see whether outreach efforts are landing.",
  },
  "reports.engagement.workshops": {
    title: "Workshops",
    what: "Total workshops that have ever been listed on the platform (past + upcoming).",
    why: "The catalogue depth. Doesn't distinguish between real and mock — cross-check with active facilitator count to sanity check.",
  },
  "reports.engagement.products": {
    title: "Products",
    what: "Total shop items listed (POD merch, books, artist prints).",
    why: "Retail catalogue depth. A healthy shop grows with the artist and partner network.",
  },
  "reports.engagement.reviews": {
    title: "Reviews",
    what: "Total workshop reviews submitted by attendees.",
    why: "Trust content. Reviews-to-registrations ratio is a decent proxy for facilitator quality and workshop resonance.",
  },
  "reports.engagement.partners_active": {
    title: "Active partners",
    what: "Partners with an active subscription (studio, retreat center, therapist, etc).",
    why: "The channel-partner ecosystem. Partner revenue is a big lever for long-term stability.",
  },
  "reports.engagement.subs": {
    title: "Active subscriptions",
    what: "Facilitator and partner subscriptions currently in good standing.",
    why: "The most predictable recurring revenue base. Sudden dips warrant a churn investigation.",
  },
  "reports.engagement.discussions": {
    title: "Discussions",
    what: "Community discussion threads created on the platform.",
    why: "Engagement depth. Communities with active discussions retain 3–5× better than passive ones.",
  },
  "reports.engagement.new_regs_30": {
    title: "New registrations (30d)",
    what: "Paid workshop registrations in the last 30 days.",
    why: "The most sensitive real-time demand indicator. Compare to same-month last quarter for trend.",
  },
  "reports.engagement.new_signups_30": {
    title: "New signups (30d)",
    what: "New account creations in the last 30 days (all types).",
    why: "Top-of-funnel. Divide by marketing spend for a CAC read.",
  },
  "reports.rev.workshops": {
    title: "Workshop revenue",
    what: "Total gross revenue from paid workshop registrations, all time.",
    math: "Σ registration.amount_paid across all registrations with status='paid'.",
    why: "The core value-flow number. Doesn't distinguish foundation take vs facilitator share.",
  },
  "reports.rev.shop": {
    title: "Shop revenue",
    what: "Total gross shop revenue, all time (POD, books, prints).",
    why: "Secondary revenue stream. Small relative to workshops today, meaningful once the artist ecosystem matures.",
  },
  "reports.rev.pod": {
    title: "POD margin",
    what: "Print-on-demand: what customers paid vs what we pay to fulfillment (Printful / Lulu). The delta is the foundation margin.",
    math: "Customer revenue − vendor cost (fulfilment + shipping to buyer). Positive means we're pricing above cost.",
    why: "POD is capital-light but low-margin. A single-digit % margin miss on hundreds of orders erases meaningful money quickly.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  Admin Dashboard (/admin)
  // ═════════════════════════════════════════════════════════════════════
  "dash.stats.users": {
    title: "Users",
    what: "All accounts on the platform, current.",
    why: "Board-level reach number.",
  },
  "dash.stats.workshops": {
    title: "Workshops",
    what: "All workshops in the system.",
    why: "Content depth indicator.",
  },
  "dash.stats.regs": {
    title: "Registrations",
    what: "Total workshop registrations (any status).",
    why: "Divide by workshops to get avg fill; divide by users to get avg-per-member engagement.",
  },
  "dash.stats.orders": {
    title: "Orders",
    what: "Shop orders placed, any status.",
    why: "Retail-side depth. Sudden drops indicate fulfilment or pricing issues.",
  },
  "dash.stats.products": {
    title: "Products",
    what: "Live shop SKUs.",
    why: "Catalogue depth.",
  },
  "dash.stats.newsletter": {
    title: "Newsletter",
    what: "Newsletter subscribers.",
    why: "Owned-audience metric. Independent of platform, portable if we ever need to migrate.",
  },
  "dash.stats.sponsors": {
    title: "Sponsors",
    what: "Sponsors publicly displayed on the platform.",
    why: "Trust asset — third-party validation of the mission.",
  },
  "dash.stats.revenue": {
    title: "Revenue",
    what: "All-time gross revenue across all products and services on the platform.",
    why: "The topline. Track month-over-month growth trend, not the absolute number.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  AI Usage (/admin/ai-usage)
  // ═════════════════════════════════════════════════════════════════════
  "aiuse.page": {
    title: "AI usage & cost",
    what: "Tracks every LLM call made from the platform — which user, which feature, tokens in/out, dollars spent.",
    why: "AI features are pay-per-call. This page prevents surprises: a runaway feature or a compromised account could ring up thousands of dollars quickly. Watch the weekly and monthly rollups.",
  },
  "aiuse.window.today": {
    title: "Today's spend",
    what: "LLM cost accrued since midnight UTC.",
    why: "Fast-moving line — a sudden spike here is often the first sign of a bug or misuse.",
  },
  "aiuse.window.week": {
    title: "Last 7 days spend",
    what: "Rolling 7-day LLM cost total.",
    why: "Smooths daily noise. Compare to prior 7-day period for a trend read.",
  },
  "aiuse.window.month": {
    title: "Last 30 days spend",
    what: "Rolling 30-day LLM cost total.",
    why: "Board-reporting cadence. Grows in step with paying-user growth if AI features are properly gated.",
  },
  "aiuse.total_events": {
    title: "Total events",
    what: "Number of individual LLM calls in the selected window.",
    why: "High events + low cost usually means good caching. Low events + high cost means very expensive individual calls (fix the model choice).",
  },
  "aiuse.total_cost": {
    title: "Total cost",
    what: "Sum of all LLM costs in the selected window.",
    why: "The line that goes on the foundation's expense report.",
  },
  "aiuse.wallets": {
    title: "Active wallets",
    what: "Users who have accrued at least one AI-usage event.",
    why: "Not every user hits AI features. Divide total cost / active wallets for a rough per-user AI cost.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  Artist Payouts (/admin/artist-payouts)
  // ═════════════════════════════════════════════════════════════════════
  "payouts.page": {
    title: "Artist patronage payouts",
    what: "Disbursement console for royalties owed to contributing artists.",
    why: "Real money owed to real artists. Delays hurt trust. This dashboard exists so nothing falls through the cracks.",
  },
  "payouts.pending": {
    title: "Pending payouts",
    what: "Total dollars accrued to artists but not yet disbursed.",
    why: "The liability on Birthright's books today. Should trend to zero after each payout run.",
  },
  "payouts.paid": {
    title: "Paid lifetime",
    what: "Cumulative dollars actually disbursed to artists.",
    why: "The impact number. Shows how much livelihood Birthright has redistributed to the artist community since inception.",
  },
  "payouts.count": {
    title: "Rows in view",
    what: "Line-item count in the currently filtered view.",
    why: "Sanity check that filters aren't hiding important payouts.",
  },
  "payouts.bulk.attempted": {
    title: "Attempted",
    what: "Payout attempts in the most recent bulk run.",
    why: "Baseline for the success/skip/fail counters below.",
  },
  "payouts.bulk.paid": {
    title: "Paid (bulk)",
    what: "Successful payouts in the latest bulk run.",
    why: "The clean number. Would-love to see this = attempted.",
  },
  "payouts.bulk.skipped": {
    title: "Skipped",
    what: "Payouts intentionally not processed (e.g., insufficient balance, artist not yet KYC'd).",
    why: "Not errors — but each skip should have a documented reason.",
  },
  "payouts.bulk.failed": {
    title: "Failed",
    what: "Payouts that errored on the Stripe side.",
    why: "Requires human investigation. Common causes: expired connect accounts, insufficient Stripe balance, dispute holds.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  Subscriptions (/admin/subscriptions)
  // ═════════════════════════════════════════════════════════════════════
  "subs.page": {
    title: "Partner subscriptions",
    what: "All facilitator and partner subscriptions on the platform, filterable by status and partner type.",
    why: "The most predictable revenue base. This is where you monitor churn signals: cancellations, revocations, and expirations before they hit the topline.",
  },
  "subs.status.active": {
    title: "Active subscription",
    what: "Paid, current, not scheduled to cancel.",
    why: "The green line. What we want most rows to be.",
  },
  "subs.status.cancelling": {
    title: "Cancelling",
    what: "Subscription still active but scheduled to end at period-end. User has opted out of renewal.",
    why: "The at-risk pool. A retention outreach here often saves the subscription.",
  },
  "subs.status.superseded": {
    title: "Superseded",
    what: "Replaced by a newer subscription (e.g., upgrade from monthly to annual).",
    why: "Not a churn signal — it's a tier upgrade, which is usually good news.",
  },
  "subs.status.expired": {
    title: "Expired",
    what: "Reached end of paid period without renewal.",
    why: "Passive churn. Distinct from active cancellation — often means expired card, not deliberate quit.",
  },
  "subs.status.revoked": {
    title: "Revoked",
    what: "Terminated by Birthright administratively (policy violation, refund request, etc).",
    why: "Rare. Each one should have a documented reason on file.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  User Activity (/admin/user-activity)
  // ═════════════════════════════════════════════════════════════════════
  "activity.page": {
    title: "User activity & admin trace",
    what: "Time-series audit log of everything users and admins do on the platform.",
    why: "Regulatory compliance (data protection, financial audit trails) and abuse detection both need this. Also the first place to look when investigating any 'what happened' question.",
  },
  "activity.total_events_30d": {
    title: "Events (30 days)",
    what: "Total logged activity events in the last 30 days.",
    why: "Platform vitality read. Sudden drops often mean a feature is broken and not logging.",
  },
  "activity.users_active_30d": {
    title: "Users active (30 days)",
    what: "Distinct users who did at least one logged action in the last 30 days.",
    why: "The true 'active users' KPI — much more meaningful than registrations. Grows with content and feature engagement.",
  },
  "activity.top_event_type": {
    title: "Top event type (30 days)",
    what: "The most common event category logged in the window.",
    why: "Reveals what users actually do. Often surprising — if the top event is 'search' rather than 'view workshop', navigation needs work.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  Partner Sales Reports (/admin/partner-sales-reports)
  // ═════════════════════════════════════════════════════════════════════
  "psales.page": {
    title: "Partner off-site sales reports",
    what: "Submitted sales reports from partners selling Birthright-attributed products or services in their own channels.",
    why: "Off-site sales are how partners share revenue with the foundation for referral traffic. This dashboard exists so nothing is under-reported or over-credited.",
  },
  "psales.period": {
    title: "Period",
    what: "Date range this report covers.",
    why: "Cross-check against expected reporting cadence (typically monthly or quarterly per partner agreement).",
  },
  "psales.source": {
    title: "Source",
    what: "Where the sale originated (partner website, Instagram, event, etc).",
    why: "Attribution audit. Multiple sources per report is normal — but should reconcile with expected channels.",
  },
  "psales.gross": {
    title: "Gross revenue",
    what: "Total sales the partner is claiming as attributable to Birthright.",
    why: "The number counsel needs to see. Adjustments happen via the override fields if the claim needs adjustment.",
  },
  "psales.attributed": {
    title: "Attributed orders",
    what: "Count of orders included in the gross figure.",
    why: "Divide gross by this for an average order value — useful sanity check.",
  },
  "psales.override_gross": {
    title: "Override gross (optional)",
    what: "Adjusted gross figure entered by admin. Overrides the partner's submitted number.",
    why: "Used when counsel or audit finds discrepancies. Leave blank to accept the partner's figure.",
  },
  "psales.override_pct": {
    title: "Override %  (optional)",
    what: "Adjusted attribution percentage. Overrides the default partner-agreement rate.",
    why: "Same use-case — dispute resolution or one-off exceptions.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  Refunds & Clawbacks (/admin/refunds)
  // ═════════════════════════════════════════════════════════════════════
  "refunds.page": {
    title: "Refunds & clawbacks",
    what: "Every refund issued and every clawback (chargeback we're recovering from a facilitator/artist for a refunded purchase). Two tabs: cascades (auto-processed) and pending clawbacks (needing manual recovery).",
    why: "Refunds cost money. Clawbacks are how Birthright recovers the payout already made to a facilitator when the underlying order gets refunded. Failing to clawback = double-paying. Watch the pending clawback queue.",
  },
  "refunds.cascades": {
    title: "Cascades",
    what: "Refunds that were auto-processed through Stripe, with all downstream credit reversals handled automatically.",
    why: "The healthy path. High cascade count is a good sign that our refund plumbing works.",
  },
  "refunds.clawbacks_pending": {
    title: "Pending clawbacks",
    what: "Refunds where the recipient (facilitator, artist, partner) has an outstanding payment owed back to Birthright.",
    why: "Aging pending clawbacks are lost money. Should be resolved within one payout cycle. Anything over 90 days needs attention.",
  },

  // ═════════════════════════════════════════════════════════════════════
  //  Email Operations (/admin/email-ops)
  // ═════════════════════════════════════════════════════════════════════
  "emailops.page": {
    title: "Email operations",
    what: "Health check for outbound transactional email: from-address configuration, Resend API readiness, and recent delivery log.",
    why: "Every payment, invite, and password reset depends on email. This dashboard exists so we spot config drift before users hit the 'reset didn't arrive' pain point.",
  },
  "emailops.readiness": {
    title: "Readiness checklist",
    what: "Automated preflight: sending domain verified, Resend API key present, from-address set, DKIM/SPF configured.",
    why: "Any red item here means at least one type of email is silently failing. Fix immediately.",
  },
  "emailops.recent": {
    title: "Most recent emails",
    what: "The last N transactional emails sent, with delivery status.",
    why: "First-line debugging for 'my invite didn't arrive' tickets.",
  },
  "emailops.cutover": {
    title: "Cutover checklist",
    what: "Items to verify when moving email sending to a new provider or domain.",
    why: "Migrations here are high-risk. Follow the checklist to avoid a 24-hour bounce storm.",
  },
};

export default explainers;
