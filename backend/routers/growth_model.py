"""Growth-model simulator for the peer-led facilitator network.

Admin-only. Takes tunable parameters (workshop capacity, conversion,
attrition, subscription mix + prices, market ceiling, etc.) and returns a
month-by-month + year-by-year projection over N years.

Endpoint:
  POST /api/admin/growth-model/simulate

The simulation is pure Python, deterministic, and runs in <50ms even for a
20-year horizon, so it's safe to re-run on every slider change from the UI.
"""
from __future__ import annotations

from collections import defaultdict
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from auth_utils import require_roles

router = APIRouter(prefix="/admin/growth-model", tags=["growth-model"])


class GrowthParams(BaseModel):
    years: int = Field(20, ge=1, le=40)
    starting_facilitators: int = Field(1, ge=1, le=1000)

    couples_per_workshop: int = Field(8, ge=1, le=50)
    price_per_couple: float = Field(285.0, ge=0)
    workshops_per_facilitator_per_year: float = Field(
        12.0, ge=1, le=52,
        description="How many workshops each active facilitator hosts per year",
    )

    participant_to_applicant_pct: float = Field(3.0, ge=0, le=100)   # % of participants who apply
    applicant_to_active_pct: float = Field(50.0, ge=0, le=100)       # % of applicants who complete training
    training_lag_months: int = Field(3, ge=0, le=24)

    # Cohort-tiered attrition (annual %). Real peer-ed networks lose the
    # bulk of new facilitators in year 1; tenured hosts are far stickier.
    attrition_year1_pct: float = Field(35.0, ge=0, le=100)
    attrition_year2_pct: float = Field(15.0, ge=0, le=100)
    attrition_year3plus_pct: float = Field(8.0, ge=0, le=100)

    # New-facilitator ramp-up: fill rate scales linearly from
    # `fill_ramp_start_pct` at tenure 0 to 100% at tenure `fill_ramp_months`.
    fill_ramp_start_pct: float = Field(30.0, ge=0, le=100)
    fill_ramp_months: int = Field(9, ge=0, le=36)

    # Conversion decay: as the movement mainstreams, participant->applicant
    # rate drops. Applied as an annual multiplicative decay.
    conversion_annual_decay_pct: float = Field(10.0, ge=0, le=100)

    # Split of workshops by curriculum source
    pct_workshops_using_ip: float = Field(
        80.0, ge=0, le=100,
        description="% of workshops using Birthright IP (rest use facilitator's own materials)",
    )

    # Foundation take % by (subscription tier × workshop type). Facilitator
    # keeps the remainder. Matches the published pricing table at
    # birthright.live: longer commitment -> smaller foundation cut, and
    # own-material workshops carry a 10-point premium.
    foundation_take_monthly_ip_pct: float = Field(40.0, ge=0, le=100)
    foundation_take_monthly_own_pct: float = Field(50.0, ge=0, le=100)
    foundation_take_annual_ip_pct: float = Field(35.0, ge=0, le=100)
    foundation_take_annual_own_pct: float = Field(45.0, ge=0, le=100)
    foundation_take_two_year_ip_pct: float = Field(30.0, ge=0, le=100)
    foundation_take_two_year_own_pct: float = Field(40.0, ge=0, le=100)

    # Subscription prices (paid to foundation per facilitator) — published
    # pricing on birthright.live
    sub_monthly_price: float = Field(99.0, ge=0)      # $/mo
    sub_annual_price: float = Field(999.0, ge=0)      # $/yr
    sub_two_year_price: float = Field(1799.0, ge=0)   # $/24mo

    # New-facilitator subscription mix (tenure < 12mo)
    new_mix_monthly_pct: float = Field(85.0, ge=0, le=100)
    new_mix_annual_pct: float = Field(10.0, ge=0, le=100)
    new_mix_two_year_pct: float = Field(5.0, ge=0, le=100)

    # Tenured mix (tenure >= 12mo)
    tenured_mix_monthly_pct: float = Field(15.0, ge=0, le=100)
    tenured_mix_annual_pct: float = Field(60.0, ge=0, le=100)
    tenured_mix_two_year_pct: float = Field(25.0, ge=0, le=100)

    # -------- Geographic reach (replaces flat market ceiling) --------
    # Instead of one national ceiling, the network expands metro by metro.
    # Total addressable demand at year Y =
    #   (initial_metros + new_metros_per_year * (Y-1)) * couples_per_metro_per_year
    initial_serviced_metros: int = Field(3, ge=1, le=1000)
    new_metros_per_year: float = Field(5.0, ge=0, le=200)
    couples_per_metro_per_year: int = Field(
        5000, ge=100, le=100_000,
        description="Annual workshop-attending couples a fully-covered metro can supply",
    )

    # -------- Costs & leakage --------
    foundation_marketing_cost_per_participant: float = Field(
        15.0, ge=0, le=500,
        description="Foundation-borne brand marketing per acquired participant",
    )
    pct_participants_from_referral: float = Field(
        30.0, ge=0, le=100,
        description="Referrals from existing facilitators skip paid acquisition",
    )
    refund_chargeback_pct: float = Field(5.0, ge=0, le=100)

    # -------- Demand mix --------
    avg_workshops_per_participant: float = Field(
        1.0, ge=1.0, le=5.0,
        description="Average workshop attendances per unique participant",
    )

    # -------- Cross-role revenue --------
    cross_role_revenue_per_tenured_fac_per_year: float = Field(
        500.0, ge=0,
        description="Additional foundation revenue from tenured facilitators serving as trainers, curriculum authors, retreat leaders",
    )
    cross_role_tenure_months: int = Field(
        24, ge=0, le=120,
        description="Minimum tenure before a facilitator generates cross-role revenue",
    )


class YearRow(BaseModel):
    year: int
    active_eoy: float
    workshops: float
    participants: float
    workshop_gross: float
    refunds: float
    workshop_net: float
    facilitator_earnings: float
    foundation_workshop_share: float
    subscription_revenue: float
    cross_role_revenue: float
    foundation_marketing_cost: float
    foundation_gross: float           # workshop share + subs + cross-role
    foundation_net: float             # foundation_gross - marketing cost
    fill_rate: float                  # 0-1, avg over the year
    market_ceiling: float             # couples/yr addressable this year


class GrowthResponse(BaseModel):
    params: GrowthParams
    years: List[YearRow]
    cumulative: dict


def _simulate(p: GrowthParams) -> GrowthResponse:
    months = p.years * 12

    p_to_applicant = p.participant_to_applicant_pct / 100.0
    applicant_to_active = p.applicant_to_active_pct / 100.0
    base_net_conversion = p_to_applicant * applicant_to_active

    # Cohort-tiered monthly attrition
    def _monthly(annual_pct):
        return 1 - (1 - annual_pct / 100.0) ** (1 / 12)
    m_attr_y1 = _monthly(p.attrition_year1_pct)
    m_attr_y2 = _monthly(p.attrition_year2_pct)
    m_attr_y3 = _monthly(p.attrition_year3plus_pct)

    def cohort_monthly_attrition(tenure_months: int) -> float:
        if tenure_months < 12:
            return m_attr_y1
        if tenure_months < 24:
            return m_attr_y2
        return m_attr_y3

    # Ramp-up fill fraction per cohort tenure
    def cohort_ramp(tenure_months: int) -> float:
        if p.fill_ramp_months <= 0:
            return 1.0
        start = p.fill_ramp_start_pct / 100.0
        pct_done = min(tenure_months / p.fill_ramp_months, 1.0)
        return start + (1.0 - start) * pct_done

    conv_decay = p.conversion_annual_decay_pct / 100.0
    ip_share = p.pct_workshops_using_ip / 100.0
    own_share = 1 - ip_share

    fnd_take = {
        "monthly":  (ip_share * p.foundation_take_monthly_ip_pct
                     + own_share * p.foundation_take_monthly_own_pct) / 100.0,
        "annual":   (ip_share * p.foundation_take_annual_ip_pct
                     + own_share * p.foundation_take_annual_own_pct) / 100.0,
        "two_year": (ip_share * p.foundation_take_two_year_ip_pct
                     + own_share * p.foundation_take_two_year_own_pct) / 100.0,
    }

    sub_mo = {
        "monthly": p.sub_monthly_price,
        "annual": p.sub_annual_price / 12.0,
        "two_year": p.sub_two_year_price / 24.0,
    }

    def _normalize(a, b, c):
        s = a + b + c
        return (a / s, b / s, c / s) if s > 0 else (0, 0, 0)

    new_mix = dict(zip(
        ["monthly", "annual", "two_year"],
        _normalize(p.new_mix_monthly_pct, p.new_mix_annual_pct, p.new_mix_two_year_pct),
    ))
    tenured_mix = dict(zip(
        ["monthly", "annual", "two_year"],
        _normalize(p.tenured_mix_monthly_pct, p.tenured_mix_annual_pct, p.tenured_mix_two_year_pct),
    ))

    refund_frac = p.refund_chargeback_pct / 100.0
    cac_per_participant = p.foundation_marketing_cost_per_participant
    cold_fraction = 1 - (p.pct_participants_from_referral / 100.0)
    attend_per_person = max(p.avg_workshops_per_participant, 1.0)
    cross_role_mo = p.cross_role_revenue_per_tenured_fac_per_year / 12.0

    tenure_hist = defaultdict(float)
    tenure_hist[0] = float(p.starting_facilitators)
    pending = [0.0] * p.training_lag_months if p.training_lag_months > 0 else []

    rows_month = []
    for month in range(1, months + 1):
        year_idx = (month - 1) // 12                     # 0-based
        year_1based = year_idx + 1

        # 1. Age all cohorts + apply cohort-tiered attrition
        aged = defaultdict(float)
        for t, c in tenure_hist.items():
            aged[t + 1] += c * (1 - cohort_monthly_attrition(t))
        tenure_hist = aged

        # 2. Activate lag-queued applicants
        if pending:
            activating = pending.pop(0)
        else:
            activating = 0.0
        tenure_hist[0] += activating

        # 3. Compute cohort-weighted ramp fill, then network-level saturation
        active = sum(tenure_hist.values())
        if active > 0:
            ramp_weighted = sum(c * cohort_ramp(t) for t, c in tenure_hist.items()) / active
        else:
            ramp_weighted = 1.0

        # Geographic market ceiling grows year over year with new metros
        market_ceiling = (
            (p.initial_serviced_metros + p.new_metros_per_year * year_idx)
            * p.couples_per_metro_per_year
        )

        workshops_per_fac_this_month = p.workshops_per_facilitator_per_year / 12.0
        workshops = active * workshops_per_fac_this_month

        # Pre-saturation annualized demand assuming ramp-adjusted fill
        annualized_demand = (
            active * p.workshops_per_facilitator_per_year
            * p.couples_per_workshop * ramp_weighted
        )
        if market_ceiling > 0 and annualized_demand > market_ceiling:
            over = (annualized_demand - market_ceiling) / (4 * market_ceiling)
            saturation_factor = max(0.15, 1.0 - 0.85 * min(over, 1.0))
        else:
            saturation_factor = 1.0

        fill_rate = ramp_weighted * saturation_factor
        effective_couples = p.couples_per_workshop * fill_rate
        participants = workshops * effective_couples * 2
        gross_per_workshop = effective_couples * p.price_per_couple

        # 4. Workshop revenue split by cohort × tier
        foundation_workshop = 0.0
        facilitator_earnings = 0.0
        sub_rev = 0.0
        cross_role_rev = 0.0
        for t, c in tenure_hist.items():
            mix = new_mix if t < 12 else tenured_mix
            per_fac_gross = gross_per_workshop * workshops_per_fac_this_month
            for tier, share in mix.items():
                pop = c * share
                foundation_workshop += pop * per_fac_gross * fnd_take[tier]
                facilitator_earnings += pop * per_fac_gross * (1 - fnd_take[tier])
                sub_rev += pop * sub_mo[tier]
            # Cross-role revenue applies to sufficiently-tenured facilitators
            if t >= p.cross_role_tenure_months:
                cross_role_rev += c * cross_role_mo

        workshop_gross = foundation_workshop + facilitator_earnings
        refunds = workshop_gross * refund_frac
        workshop_net = workshop_gross - refunds
        # Refunds hit both parties proportionally
        foundation_workshop *= (1 - refund_frac)
        facilitator_earnings *= (1 - refund_frac)

        # 5. Foundation marketing cost (unique cold participants only)
        unique_participants = participants / attend_per_person
        cold_participants = unique_participants * cold_fraction
        foundation_marketing_cost = cold_participants * cac_per_participant

        # 6. Applicant flow (with time-based conversion decay)
        decayed_conversion = base_net_conversion * ((1 - conv_decay) ** year_idx)
        applicants = unique_participants * decayed_conversion

        if p.training_lag_months > 0:
            pending.append(applicants)
        else:
            pending = [applicants]

        foundation_gross = foundation_workshop + sub_rev + cross_role_rev
        foundation_net = foundation_gross - foundation_marketing_cost

        rows_month.append({
            "month": month,
            "year": year_1based,
            "active": active,
            "workshops": workshops,
            "participants": participants,
            "workshop_gross": workshop_gross,
            "refunds": refunds,
            "workshop_net": workshop_net,
            "facilitator_earnings": facilitator_earnings,
            "foundation_workshop": foundation_workshop,
            "subscription_revenue": sub_rev,
            "cross_role_revenue": cross_role_rev,
            "foundation_marketing_cost": foundation_marketing_cost,
            "foundation_gross": foundation_gross,
            "foundation_net": foundation_net,
            "fill_rate": fill_rate,
            "market_ceiling": market_ceiling,
        })

    # yearly rollup
    yearly = {}
    fill_sum = defaultdict(float)
    fill_n = defaultdict(int)
    for r in rows_month:
        y = r["year"]
        if y not in yearly:
            yearly[y] = YearRow(
                year=y, active_eoy=0, workshops=0, participants=0,
                workshop_gross=0, refunds=0, workshop_net=0,
                facilitator_earnings=0,
                foundation_workshop_share=0, subscription_revenue=0,
                cross_role_revenue=0, foundation_marketing_cost=0,
                foundation_gross=0, foundation_net=0,
                fill_rate=0, market_ceiling=0,
            )
        yr = yearly[y]
        yr.workshops += r["workshops"]
        yr.participants += r["participants"]
        yr.workshop_gross += r["workshop_gross"]
        yr.refunds += r["refunds"]
        yr.workshop_net += r["workshop_net"]
        yr.facilitator_earnings += r["facilitator_earnings"]
        yr.foundation_workshop_share += r["foundation_workshop"]
        yr.subscription_revenue += r["subscription_revenue"]
        yr.cross_role_revenue += r["cross_role_revenue"]
        yr.foundation_marketing_cost += r["foundation_marketing_cost"]
        yr.foundation_gross += r["foundation_gross"]
        yr.foundation_net += r["foundation_net"]
        yr.active_eoy = r["active"]
        yr.market_ceiling = r["market_ceiling"]
        fill_sum[y] += r["fill_rate"]
        fill_n[y] += 1
    for y, yr in yearly.items():
        yr.fill_rate = round(fill_sum[y] / max(fill_n[y], 1), 3)

    years_list = [yearly[y] for y in sorted(yearly.keys())]

    cum = {
        "workshops": sum(y.workshops for y in years_list),
        "participants": sum(y.participants for y in years_list),
        "workshop_gross": sum(y.workshop_gross for y in years_list),
        "workshop_net": sum(y.workshop_net for y in years_list),
        "refunds": sum(y.refunds for y in years_list),
        "facilitator_earnings": sum(y.facilitator_earnings for y in years_list),
        "foundation_workshop_share": sum(y.foundation_workshop_share for y in years_list),
        "subscription_revenue": sum(y.subscription_revenue for y in years_list),
        "cross_role_revenue": sum(y.cross_role_revenue for y in years_list),
        "foundation_marketing_cost": sum(y.foundation_marketing_cost for y in years_list),
        "foundation_gross": sum(y.foundation_gross for y in years_list),
        "foundation_net": sum(y.foundation_net for y in years_list),
    }

    return GrowthResponse(params=p, years=years_list, cumulative=cum)


@router.post("/simulate", response_model=GrowthResponse)
async def simulate(params: GrowthParams, _user=Depends(require_roles("admin"))):
    return _simulate(params)
