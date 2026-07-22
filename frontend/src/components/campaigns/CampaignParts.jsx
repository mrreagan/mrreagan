import React from "react";
import { Link } from "react-router-dom";
import { Heart, ArrowRight, Info } from "lucide-react";

/**
 * Compact "sponsor pill" badge. Renders on cards, campaign detail hero,
 * and homepage teaser. Links to the campaign page (or a custom `to`).
 * Always accompanied by the non-deductible notice tooltip via title attr.
 */
export function SponsorPill({ label = "Sponsor this campaign", to = "/campaigns", className = "", testId = "sponsor-pill" }) {
  return (
    <Link
      to={to}
      title="Sponsorships are not currently tax-deductible — 501(c)(3) status not yet granted."
      className={
        "inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold " +
        "bg-[#C9A961] text-[#0F2424] hover:bg-[#D4B677] transition " +
        className
      }
      data-testid={testId}
    >
      <Heart size={12} strokeWidth={2} />
      {label}
      <ArrowRight size={12} strokeWidth={2} />
    </Link>
  );
}

/**
 * Small inline status pill for quick disclosure.
 * Use next to headings ("Sponsor Campaign · [pill]") to signal legal status
 * without a full paragraph. Pair with `<NonDeductibleNotice />` on the same page.
 */
export function TaxStatusPill({ className = "" }) {
  return (
    <span
      title="Birthright is not yet a 501(c)(3). Sponsorships are not currently tax-deductible."
      className={
        "inline-flex items-center text-[10px] uppercase tracking-widest " +
        "text-[#8B4513] bg-[#E5D7B3] px-2 py-0.5 rounded-full font-semibold " +
        className
      }
      data-testid="tax-status-pill"
    >
      Not Currently Tax-Deductible
    </span>
  );
}

/**
 * Prominent disclosure block that must appear on every campaign card,
 * campaign detail page, and pledge confirmation.
 */
export function NonDeductibleNotice({ notice, className = "" }) {
  return (
    <div
      className={
        "text-[11px] leading-relaxed uppercase tracking-wide text-[#8B4513] " +
        "bg-[#FBF3E4] border border-[#E5D7B3] rounded-md px-3 py-2 " +
        className
      }
      data-testid="non-deductible-notice"
    >
      <strong className="font-bold">Not currently tax-deductible.</strong>{" "}
      <span className="normal-case tracking-normal text-[#5C6B6B]">
        {notice ||
          "Birthright Foundation has not yet submitted or received IRS 501(c)(3) determination. Sponsorships are not currently tax-deductible as charitable donations. Sponsors receive a business receipt only. No representation is made about future tax status."}
      </span>
    </div>
  );
}

/**
 * Progress bar for a campaign goal — pledged / goal.
 */
export function CampaignProgress({ pledged = 0, goal = 0, progressPct = 0, sponsors = 0 }) {
  return (
    <div className="mt-4" data-testid="campaign-progress">
      <div className="flex items-baseline justify-between">
        <div className="font-serif text-2xl text-[#0F2424]">
          ${Number(pledged).toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </div>
        <div className="text-xs text-[#5C6B6B]">
          of ${Number(goal).toLocaleString(undefined, { maximumFractionDigits: 0 })} goal
        </div>
      </div>
      <div className="mt-2 h-1.5 rounded-full bg-[#E5D7B3] overflow-hidden">
        <div
          className="h-full bg-[#C9A961] transition-all"
          style={{ width: `${Math.min(Math.max(progressPct || 0, 0), 100)}%` }}
        />
      </div>
      <div className="mt-1.5 text-[11px] text-[#5C6B6B]">
        {sponsors} sponsor{sponsors === 1 ? "" : "s"} · {progressPct}% pledged
      </div>
    </div>
  );
}


/**
 * Featured campaign card — the large gold-tinted hero used on the homepage
 * and on the /sponsor page above the tier grid. Displays title, tagline,
 * progress, CTA button, and contingency note.
 */
export function FeaturedCampaignCard({ campaign, testId = "featured-campaign-card" }) {
  if (!campaign) return null;
  return (
    <div
      className="card p-8 lg:p-10 bg-gradient-to-br from-[#FBF3E4] to-[#F4F1EA] border-[#E5D7B3]"
      data-testid={testId}
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        <div className="lg:col-span-8">
          <div className="inline-flex items-center gap-2">
            <span className="label text-[#8B4513]">Sponsor campaign</span>
            <TaxStatusPill />
          </div>
          <h2 className="editorial-h2 mt-3 text-[#0F2424]">{campaign.title}</h2>
          <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed max-w-xl">
            {campaign.tagline}
          </p>
          <div className="mt-5 flex items-baseline gap-3">
            <span className="font-serif text-2xl text-[#0F2424]">
              ${Number(campaign.total_pledged || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
            <span className="text-xs text-[#5C6B6B]">
              of ${Number(campaign.goal_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} · {campaign.sponsor_count || 0} sponsors
            </span>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              to={`/campaigns/${campaign.slug}`}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#C9A961] text-[#0F2424] font-semibold text-sm hover:bg-[#D4B677] transition"
              data-testid={`${testId}-cta`}
            >
              <Heart size={14} strokeWidth={1.8} /> {campaign.pill_label || "Sponsor this campaign"}
            </Link>
          </div>
        </div>
        <div className="lg:col-span-4">
          <div className="h-2 rounded-full bg-[#E5D7B3] overflow-hidden">
            <div className="h-full bg-[#C9A961]" style={{ width: `${Math.min(campaign.progress_pct || 0, 100)}%` }} />
          </div>
          <p className="text-[11px] text-[#5C6B6B] mt-2 text-right">
            {campaign.progress_pct}% pledged
          </p>
          {campaign.contingency_note && (
            <p className="text-[11px] text-[#8B4513] mt-4 italic leading-relaxed flex items-start gap-1.5">
              <Info size={12} strokeWidth={1.5} className="mt-0.5 shrink-0" />
              <span><strong>Contingent:</strong> {campaign.contingency_note}</span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
