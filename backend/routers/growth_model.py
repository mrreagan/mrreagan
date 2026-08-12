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

    participant_to_applicant_pct: float = Field(3.0, ge=0, le=100)   # % of participants who apply
    applicant_to_active_pct: float = Field(50.0, ge=0, le=100)       # % of applicants who complete training
    training_lag_months: int = Field(3, ge=0, le=24)
    annual_attrition_pct: float = Field(10.0, ge=0, le=100)

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

    # Tenured mix (tenure >= 12mo) — Annual is labelled "MOST CHOSEN" on
    # the public pricing page, so tenured facilitators skew toward Annual
    tenured_mix_monthly_pct: float = Field(15.0, ge=0, le=100)
    tenured_mix_annual_pct: float = Field(60.0, ge=0, le=100)
    tenured_mix_two_year_pct: float = Field(25.0, ge=0, le=100)

    # Optional demand ceiling: max addressable couples per year across the
    # network. Above this, per-workshop fill rate degrades linearly.
    market_ceiling_couples_per_year: Optional[int] = Field(
        500_000, ge=0, description="Set very high or null to remove ceiling"
    )


class YearRow(BaseModel):
    year: int
    active_eoy: float
    workshops: float
    participants: float
    workshop_gross: float
    facilitator_earnings: float
    foundation_workshop_share: float
    subscription_revenue: float
    foundation_total: float
    fill_rate: float  # 0-1, avg over the year


class GrowthResponse(BaseModel):
    params: GrowthParams
    years: List[YearRow]
    cumulative: dict


def _simulate(p: GrowthParams) -> GrowthResponse:
    months = p.years * 12

    p_to_applicant = p.participant_to_applicant_pct / 100.0
    applicant_to_active = p.applicant_to_active_pct / 100.0
    net_conversion = p_to_applicant * applicant_to_active

    monthly_attrition = 1 - (1 - p.annual_attrition_pct / 100.0) ** (1 / 12)

    ip_share = p.pct_workshops_using_ip / 100.0
    own_share = 1 - ip_share

    # Effective foundation take fraction, per subscription tier, blended by
    # IP vs own-material workshop mix.
    fnd_take = {
        "monthly":  (ip_share * p.foundation_take_monthly_ip_pct
                     + own_share * p.foundation_take_monthly_own_pct) / 100.0,
        "annual":   (ip_share * p.foundation_take_annual_ip_pct
                     + own_share * p.foundation_take_annual_own_pct) / 100.0,
        "two_year": (ip_share * p.foundation_take_two_year_ip_pct
                     + own_share * p.foundation_take_two_year_own_pct) / 100.0,
    }

    # Per-month economics of each subscription tier (paid to foundation)
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

    tenure_hist = defaultdict(float)
    tenure_hist[0] = float(p.starting_facilitators)
    pending = [0.0] * p.training_lag_months if p.training_lag_months > 0 else []

    rows_month = []
    for month in range(1, months + 1):
        # age everyone + attrition
        aged = defaultdict(float)
        for t, c in tenure_hist.items():
            aged[t + 1] += c * (1 - monthly_attrition)
        tenure_hist = aged

        # activate applicants whose lag just ended
        if pending:
            activating = pending.pop(0)
        else:
            activating = 0.0
        tenure_hist[0] += activating

        active = sum(tenure_hist.values())
        workshops = active

        # Demand-side saturation
        annualized_demand = active * 12 * p.couples_per_workshop
        if p.market_ceiling_couples_per_year and p.market_ceiling_couples_per_year > 0:
            ceiling = p.market_ceiling_couples_per_year
            if annualized_demand <= ceiling:
                fill_rate = 1.0
            else:
                over = (annualized_demand - ceiling) / (4 * ceiling)
                fill_rate = max(0.15, 1.0 - 0.85 * min(over, 1.0))
        else:
            fill_rate = 1.0

        effective_couples = p.couples_per_workshop * fill_rate
        participants = workshops * effective_couples * 2
        gross_per_facilitator = effective_couples * p.price_per_couple
        workshop_gross = workshops * gross_per_facilitator

        # Split workshop revenue: for each tenure bucket, blend by tier mix
        foundation_workshop = 0.0
        facilitator_earnings = 0.0
        sub_rev = 0.0
        for t, c in tenure_hist.items():
            mix = new_mix if t < 12 else tenured_mix
            for tier, share in mix.items():
                pop = c * share
                foundation_workshop += pop * gross_per_facilitator * fnd_take[tier]
                facilitator_earnings += pop * gross_per_facilitator * (1 - fnd_take[tier])
                sub_rev += pop * sub_mo[tier]

        applicants = participants * net_conversion
        if p.training_lag_months > 0:
            pending.append(applicants)
        else:
            pending = [applicants]

        rows_month.append({
            "month": month,
            "year": (month - 1) // 12 + 1,
            "active": active,
            "workshops": workshops,
            "participants": participants,
            "workshop_gross": workshop_gross,
            "facilitator_earnings": facilitator_earnings,
            "foundation_workshop": foundation_workshop,
            "subscription_revenue": sub_rev,
            "foundation_total": foundation_workshop + sub_rev,
            "fill_rate": fill_rate,
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
                workshop_gross=0, facilitator_earnings=0,
                foundation_workshop_share=0, subscription_revenue=0,
                foundation_total=0, fill_rate=0,
            )
        yr = yearly[y]
        yr.workshops += r["workshops"]
        yr.participants += r["participants"]
        yr.workshop_gross += r["workshop_gross"]
        yr.facilitator_earnings += r["facilitator_earnings"]
        yr.foundation_workshop_share += r["foundation_workshop"]
        yr.subscription_revenue += r["subscription_revenue"]
        yr.foundation_total += r["foundation_total"]
        yr.active_eoy = r["active"]
        fill_sum[y] += r["fill_rate"]
        fill_n[y] += 1
    for y, yr in yearly.items():
        yr.fill_rate = round(fill_sum[y] / max(fill_n[y], 1), 3)

    years_list = [yearly[y] for y in sorted(yearly.keys())]

    cum = {
        "workshops": sum(y.workshops for y in years_list),
        "participants": sum(y.participants for y in years_list),
        "workshop_gross": sum(y.workshop_gross for y in years_list),
        "facilitator_earnings": sum(y.facilitator_earnings for y in years_list),
        "foundation_workshop_share": sum(y.foundation_workshop_share for y in years_list),
        "subscription_revenue": sum(y.subscription_revenue for y in years_list),
        "foundation_total": sum(y.foundation_total for y in years_list),
    }

    return GrowthResponse(params=p, years=years_list, cumulative=cum)


@router.post("/simulate", response_model=GrowthResponse)
async def simulate(params: GrowthParams, _user=Depends(require_roles("admin"))):
    return _simulate(params)
