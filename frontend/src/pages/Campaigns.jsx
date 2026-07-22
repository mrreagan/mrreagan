import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { ArrowRight, Info } from "lucide-react";
import { SponsorPill, NonDeductibleNotice, CampaignProgress } from "../components/campaigns/CampaignParts";

function CampaignCard({ c }) {
  return (
    <Link
      to={`/campaigns/${c.slug}`}
      className="card p-6 hover:shadow-lg transition block"
      data-testid={`campaign-card-${c.slug}`}
    >
      {c.hero_image_url ? (
        <div className="rounded-xl overflow-hidden mb-5 bg-[#F4F1EA] aspect-[16/9]">
          <img
            src={c.hero_image_url}
            alt={c.title}
            className="w-full h-full object-cover"
          />
        </div>
      ) : null}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <span className="label">Sponsor campaign</span>
          <h3 className="font-serif text-xl lg:text-2xl mt-2 text-[#0F2424] leading-tight">
            {c.title}
          </h3>
        </div>
        <SponsorPill label={c.pill_label} to={`/campaigns/${c.slug}`} testId={`pill-${c.slug}`} />
      </div>
      <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed line-clamp-3">
        {c.tagline}
      </p>
      <CampaignProgress
        pledged={c.total_pledged}
        goal={c.goal_amount}
        progressPct={c.progress_pct}
        sponsors={c.sponsor_count}
      />
      {c.contingency_note ? (
        <div className="mt-4 flex items-start gap-2 text-[11px] text-[#5C6B6B] leading-relaxed">
          <Info size={12} strokeWidth={1.5} className="mt-0.5 shrink-0" />
          <span><strong>Contingent:</strong> {c.contingency_note}</span>
        </div>
      ) : null}
    </Link>
  );
}

export default function Campaigns() {
  const [items, setItems] = useState([]);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/campaigns").then((r) => {
      setItems(r.data.campaigns || []);
      setNotice(r.data.non_deductible_notice || "");
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="container-page py-16" data-testid="campaigns-page">
      <div className="max-w-2xl">
        <span className="label">Sponsor a campaign</span>
        <h1 className="editorial-h1 mt-3">Fund specific projects. Named recognition.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          Sponsor campaigns underwrite bounded projects — a media placement, a scholarship
          cohort, a specific piece of research. Sponsors are named on the campaign page and
          in downstream promotion (with your permission). Pledges are collected as intent;
          the team follows up personally to confirm details before any money moves.
        </p>
        <NonDeductibleNotice notice={notice} className="mt-6" />
      </div>

      {loading ? (
        <p className="mt-12 text-[#5C6B6B]">Loading campaigns…</p>
      ) : items.length === 0 ? (
        <p className="mt-12 text-[#5C6B6B]">No active campaigns right now. Check back soon.</p>
      ) : (
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6" data-testid="campaigns-grid">
          {items.map((c) => <CampaignCard key={c.id} c={c} />)}
        </div>
      )}

      <div className="mt-16 text-sm text-[#5C6B6B]">
        Prefer general support? Visit{" "}
        <Link to="/sponsor" className="underline hover:text-[#C9A961]">/sponsor</Link>{" "}
        for tier-based general sponsorship <ArrowRight size={12} strokeWidth={1.5} className="inline" />
      </div>
    </div>
  );
}
