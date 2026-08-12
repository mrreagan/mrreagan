import React, { useState, useEffect, useMemo, useCallback } from "react";
import api from "../lib/api";
import { TrendingUp, Users, DollarSign, RefreshCw } from "lucide-react";

const DEFAULTS = {
  years: 20,
  starting_facilitators: 1,
  couples_per_workshop: 8,
  price_per_couple: 285,
  workshops_per_facilitator_per_year: 12,
  participant_to_applicant_pct: 3,
  applicant_to_active_pct: 50,
  training_lag_months: 3,
  // Cohort-tiered attrition
  attrition_year1_pct: 35,
  attrition_year2_pct: 15,
  attrition_year3plus_pct: 8,
  // New-facilitator ramp
  fill_ramp_start_pct: 30,
  fill_ramp_months: 9,
  // Conversion decay
  conversion_annual_decay_pct: 10,
  // Workshop curriculum mix
  pct_workshops_using_ip: 80,
  // Foundation take % by (tier × workshop type)
  foundation_take_monthly_ip_pct: 40,
  foundation_take_monthly_own_pct: 50,
  foundation_take_annual_ip_pct: 35,
  foundation_take_annual_own_pct: 45,
  foundation_take_two_year_ip_pct: 30,
  foundation_take_two_year_own_pct: 40,
  // Subscription prices
  sub_monthly_price: 99,
  sub_annual_price: 999,
  sub_two_year_price: 1799,
  // Subscription mix
  new_mix_monthly_pct: 85,
  new_mix_annual_pct: 10,
  new_mix_two_year_pct: 5,
  tenured_mix_monthly_pct: 15,
  tenured_mix_annual_pct: 60,
  tenured_mix_two_year_pct: 25,
  // Geographic reach
  initial_serviced_metros: 3,
  new_metros_per_year: 5,
  couples_per_metro_per_year: 5000,
  // Costs & leakage
  foundation_marketing_cost_per_participant: 15,
  pct_participants_from_referral: 30,
  refund_chargeback_pct: 5,
  // Demand mix
  avg_workshops_per_participant: 1.0,
  // Cross-role revenue
  cross_role_revenue_per_tenured_fac_per_year: 500,
  cross_role_tenure_months: 24,
};

const fmtInt = (n) => Math.round(n).toLocaleString();
const fmtUSD = (n) => {
  const v = Number(n || 0);
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(1)}k`;
  return `$${v.toFixed(0)}`;
};

function Slider({ label, hint, unit, value, min, max, step, onChange, testid }) {
  return (
    <div className="mb-4" data-testid={testid}>
      <div className="flex items-baseline justify-between mb-1">
        <label className="text-xs font-medium text-[#1A2424]">{label}</label>
        <span className="text-xs tabular-nums text-[#476B6B] font-medium">
          {value}
          {unit || ""}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#476B6B]"
        data-testid={`${testid}-input`}
      />
      {hint && <p className="text-[10px] text-[#8B9494] mt-0.5 leading-tight">{hint}</p>}
    </div>
  );
}

function GrowthChart({ years }) {
  if (!years || years.length === 0) return null;
  const w = 640, h = 220, padL = 60, padR = 20, padT = 20, padB = 30;
  const innerW = w - padL - padR, innerH = h - padT - padB;
  const maxFac = Math.max(...years.map((y) => y.active_eoy), 1);
  const xs = (i) => padL + (innerW * i) / Math.max(years.length - 1, 1);
  const yf = (v) => padT + innerH - (innerH * v) / maxFac;
  const facPath = years.map((y, i) => `${i === 0 ? "M" : "L"}${xs(i)},${yf(y.active_eoy)}`).join(" ");
  const yTicks = 4;
  const tickVals = Array.from({ length: yTicks + 1 }, (_, i) => (maxFac * i) / yTicks);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-56" data-testid="growth-chart">
      <rect x="0" y="0" width={w} height={h} fill="#FAF8F5" />
      {tickVals.map((v, i) => (
        <g key={i}>
          <line x1={padL} x2={w - padR} y1={yf(v)} y2={yf(v)} stroke="#E5E1D8" strokeWidth="1" />
          <text x={padL - 6} y={yf(v) + 3} textAnchor="end" fontSize="9" fill="#8B9494">
            {v >= 1000 ? `${(v / 1000).toFixed(0)}k` : Math.round(v)}
          </text>
        </g>
      ))}
      {years.map((y, i) =>
        i % 2 === 0 ? (
          <text key={i} x={xs(i)} y={h - padB + 12} textAnchor="middle" fontSize="9" fill="#8B9494">
            Y{y.year}
          </text>
        ) : null
      )}
      <path d={facPath} fill="none" stroke="#476B6B" strokeWidth="2" />
      {years.map((y, i) => (
        <circle key={i} cx={xs(i)} cy={yf(y.active_eoy)} r="2.5" fill="#C9A961" />
      ))}
      <text x={padL} y={padT - 6} fontSize="10" fill="#5C6B6B">
        Active facilitators (end of year)
      </text>
    </svg>
  );
}

export default function AdminGrowthModel() {
  const [params, setParams] = useState(DEFAULTS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const run = useCallback(
    async (p) => {
      setLoading(true);
      setErr(null);
      try {
        const r = await api.post("/admin/growth-model/simulate", p);
        setData(r.data);
      } catch (e) {
        setErr(e?.response?.data?.detail || e.message);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Debounced re-run on slider change
  useEffect(() => {
    const t = setTimeout(() => run(params), 250);
    return () => clearTimeout(t);
  }, [params, run]);

  const update = (key) => (v) => setParams((p) => ({ ...p, [key]: v }));

  const reset = () => setParams(DEFAULTS);

  const keyYears = useMemo(() => {
    if (!data) return [];
    const marks = [1, 2, 3, 4, 5, 7, 10, 12, 15, 17, 20];
    return data.years.filter((y) => marks.includes(y.year));
  }, [data]);

  return (
    <div className="container-page py-10" data-testid="admin-growth-model">
      <header className="mb-8">
        <span className="label text-[#C9A961]">Admin</span>
        <h1 className="font-serif text-4xl mt-1 flex items-center gap-3">
          <TrendingUp size={28} strokeWidth={1.5} className="text-[#476B6B]" />
          Facilitator network growth model
        </h1>
        <p className="text-sm text-[#5C6B6B] mt-2 max-w-prose">
          Interactive projection of how the peer-led workshop network could scale.
          Every slider re-runs the 240-month simulation locally. Adjust the demand
          ceiling, conversion, and attrition to explore realistic vs aggressive
          scenarios.
        </p>
      </header>

      <div className="grid lg:grid-cols-[340px_1fr] gap-8">
        {/* -------- Sliders -------- */}
        <aside className="card p-5" data-testid="growth-model-controls">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-lg">Parameters</h2>
            <button
              type="button"
              onClick={reset}
              className="text-xs inline-flex items-center gap-1 text-[#476B6B] hover:underline"
              data-testid="growth-model-reset"
            >
              <RefreshCw size={12} strokeWidth={1.5} /> Reset
            </button>
          </div>

          <div className="space-y-1">
            <p className="label text-[#C9A961] text-[10px] mb-2">Simulation</p>
            <Slider label="Horizon" unit=" yrs" value={params.years} min={1} max={30}
              step={1} onChange={update("years")} testid="slider-years" />
            <Slider label="Seed facilitators" value={params.starting_facilitators}
              min={1} max={20} step={1} onChange={update("starting_facilitators")}
              testid="slider-seed" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">Workshop economics</p>
            <Slider label="Couples per workshop" value={params.couples_per_workshop}
              min={1} max={30} step={1} onChange={update("couples_per_workshop")}
              testid="slider-couples" />
            <Slider label="Workshops per facilitator / year"
              value={params.workshops_per_facilitator_per_year} min={1} max={52} step={1}
              onChange={update("workshops_per_facilitator_per_year")}
              hint="Default 12 = one per month. Bump higher for weekly or biweekly hosts."
              testid="slider-workshops-per-year" />
            <Slider label="Price per couple" unit=" $" value={params.price_per_couple}
              min={0} max={1000} step={5} onChange={update("price_per_couple")}
              testid="slider-price" />
            <Slider label="Workshops using Birthright IP" unit="%"
              value={params.pct_workshops_using_ip} min={0} max={100} step={5}
              onChange={update("pct_workshops_using_ip")}
              hint="Rest use facilitator's own materials (higher foundation take)."
              testid="slider-ip-mix" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">
              Foundation take by tier × type (%)
            </p>
            <div className="text-[10px] text-[#8B9494] mb-2 leading-tight">
              Facilitator keeps 100% − take. Published rates: monthly 40/50,
              annual 35/45, two-year 30/40 (IP / own).
            </div>
            <Slider label="Monthly · IP" unit="%"
              value={params.foundation_take_monthly_ip_pct} min={0} max={100} step={1}
              onChange={update("foundation_take_monthly_ip_pct")}
              testid="slider-take-mo-ip" />
            <Slider label="Monthly · own material" unit="%"
              value={params.foundation_take_monthly_own_pct} min={0} max={100} step={1}
              onChange={update("foundation_take_monthly_own_pct")}
              testid="slider-take-mo-own" />
            <Slider label="Annual · IP" unit="%"
              value={params.foundation_take_annual_ip_pct} min={0} max={100} step={1}
              onChange={update("foundation_take_annual_ip_pct")}
              testid="slider-take-yr-ip" />
            <Slider label="Annual · own material" unit="%"
              value={params.foundation_take_annual_own_pct} min={0} max={100} step={1}
              onChange={update("foundation_take_annual_own_pct")}
              testid="slider-take-yr-own" />
            <Slider label="2-year · IP" unit="%"
              value={params.foundation_take_two_year_ip_pct} min={0} max={100} step={1}
              onChange={update("foundation_take_two_year_ip_pct")}
              testid="slider-take-2yr-ip" />
            <Slider label="2-year · own material" unit="%"
              value={params.foundation_take_two_year_own_pct} min={0} max={100} step={1}
              onChange={update("foundation_take_two_year_own_pct")}
              testid="slider-take-2yr-own" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">Growth loop</p>
            <Slider label="Participants → applicants" unit="%"
              value={params.participant_to_applicant_pct} min={0} max={20} step={0.5}
              onChange={update("participant_to_applicant_pct")}
              hint="Of workshop participants who express interest in facilitating."
              testid="slider-p-to-a" />
            <Slider label="Applicants → active facilitators" unit="%"
              value={params.applicant_to_active_pct} min={0} max={100} step={5}
              onChange={update("applicant_to_active_pct")}
              hint="Complete training + host regularly."
              testid="slider-a-to-active" />
            <Slider label="Training lag" unit=" mo"
              value={params.training_lag_months} min={0} max={12} step={1}
              onChange={update("training_lag_months")}
              hint="Time from participation to first hosted workshop."
              testid="slider-lag" />
            <Slider label="Conversion decay / year" unit="%"
              value={params.conversion_annual_decay_pct} min={0} max={50} step={1}
              onChange={update("conversion_annual_decay_pct")}
              hint="Applicant rate declines as the movement matures past early adopters."
              testid="slider-conv-decay" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">
              Retention (annual attrition %)
            </p>
            <Slider label="Year 1" unit="%"
              value={params.attrition_year1_pct} min={0} max={80} step={1}
              onChange={update("attrition_year1_pct")}
              hint="New facilitators drop out fastest."
              testid="slider-attr-y1" />
            <Slider label="Year 2" unit="%"
              value={params.attrition_year2_pct} min={0} max={50} step={1}
              onChange={update("attrition_year2_pct")}
              testid="slider-attr-y2" />
            <Slider label="Year 3+" unit="%"
              value={params.attrition_year3plus_pct} min={0} max={30} step={1}
              onChange={update("attrition_year3plus_pct")}
              hint="Tenured hosts are much stickier."
              testid="slider-attr-y3" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">New-facilitator ramp</p>
            <Slider label="Starting fill rate" unit="%"
              value={params.fill_ramp_start_pct} min={0} max={100} step={5}
              onChange={update("fill_ramp_start_pct")}
              hint="How full a new facilitator's first workshops are."
              testid="slider-ramp-start" />
            <Slider label="Ramp to full over" unit=" mo"
              value={params.fill_ramp_months} min={0} max={36} step={1}
              onChange={update("fill_ramp_months")}
              testid="slider-ramp-months" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">Geographic reach</p>
            <Slider label="Initial serviced metros"
              value={params.initial_serviced_metros} min={1} max={50} step={1}
              onChange={update("initial_serviced_metros")}
              hint="Metros where seed facilitators operate at launch."
              testid="slider-metros-init" />
            <Slider label="New metros / year"
              value={params.new_metros_per_year} min={0} max={50} step={0.5}
              onChange={update("new_metros_per_year")}
              hint="Pace at which new metros come online."
              testid="slider-metros-new" />
            <Slider label="Couples / metro / year"
              value={params.couples_per_metro_per_year} min={100} max={30000} step={100}
              onChange={update("couples_per_metro_per_year")}
              hint="Annual demand a fully-covered metro can supply."
              testid="slider-metros-couples" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">Demand mix</p>
            <Slider label="Referral share" unit="%"
              value={params.pct_participants_from_referral} min={0} max={100} step={5}
              onChange={update("pct_participants_from_referral")}
              hint="Participants from word-of-mouth (skip paid CAC)."
              testid="slider-referral" />
            <Slider label="Avg workshops / participant"
              value={params.avg_workshops_per_participant} min={1} max={3} step={0.1}
              onChange={update("avg_workshops_per_participant")}
              hint="Multi-attendance uplift (returning couples)."
              testid="slider-multi-attend" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">Costs & leakage</p>
            <Slider label="Marketing / cold participant" unit=" $"
              value={params.foundation_marketing_cost_per_participant} min={0} max={200} step={5}
              onChange={update("foundation_marketing_cost_per_participant")}
              hint="Foundation-borne brand marketing CAC per unique cold participant."
              testid="slider-cac" />
            <Slider label="Refund / chargeback rate" unit="%"
              value={params.refund_chargeback_pct} min={0} max={30} step={0.5}
              onChange={update("refund_chargeback_pct")}
              testid="slider-refund" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">Cross-role revenue</p>
            <Slider label="$/tenured fac / year" unit=" $"
              value={params.cross_role_revenue_per_tenured_fac_per_year} min={0} max={5000} step={50}
              onChange={update("cross_role_revenue_per_tenured_fac_per_year")}
              hint="Trainer, curriculum author, retreat leader income to foundation."
              testid="slider-cross-role-rev" />
            <Slider label="Cross-role tenure gate" unit=" mo"
              value={params.cross_role_tenure_months} min={6} max={60} step={3}
              onChange={update("cross_role_tenure_months")}
              hint="Minimum tenure before a facilitator qualifies."
              testid="slider-cross-role-gate" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">Subscription tiers</p>
            <Slider label="Monthly plan" unit=" $/mo"
              value={params.sub_monthly_price} min={0} max={300} step={1}
              onChange={update("sub_monthly_price")} testid="slider-sub-monthly" />
            <Slider label="Annual plan" unit=" $/yr"
              value={params.sub_annual_price} min={0} max={3000} step={25}
              onChange={update("sub_annual_price")} testid="slider-sub-annual" />
            <Slider label="Two-year plan" unit=" $/2yr"
              value={params.sub_two_year_price} min={0} max={5000} step={50}
              onChange={update("sub_two_year_price")} testid="slider-sub-2yr" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">
              New facilitator mix (&lt;1yr tenure)
            </p>
            <Slider label="Monthly" unit="%"
              value={params.new_mix_monthly_pct} min={0} max={100} step={5}
              onChange={update("new_mix_monthly_pct")}
              testid="slider-new-mo" />
            <Slider label="Annual" unit="%"
              value={params.new_mix_annual_pct} min={0} max={100} step={5}
              onChange={update("new_mix_annual_pct")}
              testid="slider-new-yr" />
            <Slider label="Two-year" unit="%"
              value={params.new_mix_two_year_pct} min={0} max={100} step={5}
              onChange={update("new_mix_two_year_pct")}
              testid="slider-new-2yr" />

            <p className="label text-[#C9A961] text-[10px] mt-4 mb-2">
              Tenured mix (≥1yr)
            </p>
            <Slider label="Monthly" unit="%"
              value={params.tenured_mix_monthly_pct} min={0} max={100} step={5}
              onChange={update("tenured_mix_monthly_pct")}
              testid="slider-ten-mo" />
            <Slider label="Annual" unit="%"
              value={params.tenured_mix_annual_pct} min={0} max={100} step={5}
              onChange={update("tenured_mix_annual_pct")}
              testid="slider-ten-yr" />
            <Slider label="Two-year" unit="%"
              value={params.tenured_mix_two_year_pct} min={0} max={100} step={5}
              onChange={update("tenured_mix_two_year_pct")}
              testid="slider-ten-2yr" />
          </div>
        </aside>

        {/* -------- Results -------- */}
        <section className="space-y-6">
          {err && (
            <div className="card p-4 bg-red-50 border-red-200 text-sm text-red-800"
              data-testid="growth-model-error">
              {err}
            </div>
          )}

          {data && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="growth-model-kpis">
                <KPI icon={Users} label={`Active by Y${params.years}`}
                  value={fmtInt(data.years[data.years.length - 1].active_eoy)}
                  testid="kpi-active" />
                <KPI icon={Users} label={`Participants (cumulative)`}
                  value={fmtInt(data.cumulative.participants)}
                  testid="kpi-participants" />
                <KPI icon={DollarSign} label={`Workshop revenue net`}
                  value={fmtUSD(data.cumulative.workshop_net)}
                  testid="kpi-workshop-net" />
                <KPI icon={DollarSign} label={`Foundation NET (cum.)`}
                  value={fmtUSD(data.cumulative.foundation_net)}
                  accent
                  testid="kpi-foundation-net" />
              </div>

              <div className="card p-4">
                <h3 className="font-serif text-base mb-3">Facilitator network trajectory</h3>
                <GrowthChart years={data.years} />
              </div>

              <div className="card p-4 overflow-x-auto" data-testid="growth-model-table">
                <h3 className="font-serif text-base mb-3">Yearly projection</h3>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-[#5C6B6B] border-b border-[#E5E1D8]">
                      <th className="py-2 pr-3">Year</th>
                      <th className="py-2 px-2 text-right">Active EOY</th>
                      <th className="py-2 px-2 text-right">Workshops</th>
                      <th className="py-2 px-2 text-right">Participants</th>
                      <th className="py-2 px-2 text-right">Wkshp net $</th>
                      <th className="py-2 px-2 text-right text-[#8B9494]">Refunds</th>
                      <th className="py-2 px-2 text-right">Fac $</th>
                      <th className="py-2 px-2 text-right">Fnd wkshp $</th>
                      <th className="py-2 px-2 text-right">Subs $</th>
                      <th className="py-2 px-2 text-right">Cross-role $</th>
                      <th className="py-2 px-2 text-right text-red-700">Mktg −</th>
                      <th className="py-2 px-2 text-right font-medium text-[#1A2424]">
                        Fnd NET
                      </th>
                      <th className="py-2 px-2 text-right text-[#8B9494]">Ceiling</th>
                      <th className="py-2 px-2 text-right">Fill</th>
                    </tr>
                  </thead>
                  <tbody>
                    {keyYears.map((y) => (
                      <tr key={y.year} className="border-b border-[#E5E1D8]/60"
                        data-testid={`growth-row-y${y.year}`}>
                        <td className="py-1.5 pr-3 font-medium">Y{y.year}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums">{fmtInt(y.active_eoy)}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums">{fmtInt(y.workshops)}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums">{fmtInt(y.participants)}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums">{fmtUSD(y.workshop_net)}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-[#8B9494]">
                          {fmtUSD(y.refunds)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-[#5C6B6B]">
                          {fmtUSD(y.facilitator_earnings)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums">
                          {fmtUSD(y.foundation_workshop_share)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums">
                          {fmtUSD(y.subscription_revenue)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums">
                          {fmtUSD(y.cross_role_revenue)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-red-700">
                          −{fmtUSD(y.foundation_marketing_cost)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums font-medium text-[#1A2424]">
                          {fmtUSD(y.foundation_net)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-[#8B9494]">
                          {fmtInt(y.market_ceiling)}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-[#8B9494]">
                          {(y.fill_rate * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="text-[10px] text-[#8B9494] mt-3 leading-relaxed">
                  <b>Workshop net</b> = gross minus refunds. <b>Fill</b> = ramp-up × geographic
                  saturation (avg over the year). <b>Ceiling</b> = addressable couples/year
                  from serviced metros. <b>Fnd NET</b> = workshop share + subs + cross-role
                  − marketing. Cumulative KPIs use every simulated year.
                </p>
              </div>
            </>
          )}

          {loading && !data && (
            <div className="text-sm text-[#5C6B6B]" data-testid="growth-model-loading">
              Running simulation…
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function KPI({ icon: Icon, label, value, accent, testid }) {
  return (
    <div className={`card p-3 ${accent ? "!bg-[#476B6B] !border-[#476B6B]" : ""}`}
      data-testid={testid}>
      <div className="flex items-center gap-2 mb-1">
        <Icon size={14} strokeWidth={1.5}
          className={accent ? "text-[#C9A961]" : "text-[#476B6B]"} />
        <p className={`text-[10px] uppercase tracking-wider ${accent ? "text-white/70" : "text-[#8B9494]"}`}>
          {label}
        </p>
      </div>
      <p className={`font-serif text-lg tabular-nums ${accent ? "text-white" : "text-[#1A2424]"}`}>
        {value}
      </p>
    </div>
  );
}
