import React from "react";
import { Link } from "react-router-dom";
import { Sparkles, ArrowRight, FlaskConical } from "lucide-react";

/**
 * StudioVendorNudge — a small editorial card that surfaces the AI Studio
 * differentiator on partner-relevant pages without overshadowing the
 * primary mission/tone.
 *
 * Variants:
 *   - "compact"   small inline pill, link-only
 *   - "card"      full card with headline + CTA (default)
 *   - "footer"    dark teal full-width footer band for end-of-page placement
 */
const COPY = {
  headline: "See the cost before you spend it.",
  sub:
    "birthright is the only non-developer creative AI studio that shows you the exact dollar cost — and what supports the foundation — before you generate. Use it to dream concepts in minutes; the +50% on every call funds the work.",
  vendor_hook:
    "Two ways to use it as a partner: list products for birthright checkout and earn revenue share per your tier — or list them as referrals to your own store, keep the retail, and send a small referral commission back to the foundation.",
  cta: "Become a partner",
  href: "/partner/apply",
};

export default function StudioVendorNudge({ variant = "card", showVendorHook = true, className = "" }) {
  if (variant === "compact") {
    return (
      <Link
        to={COPY.href}
        className={`inline-flex items-center gap-2 text-xs text-[#476B6B] hover:text-[#C9A961] transition ${className}`}
        data-testid="studio-vendor-nudge-compact"
      >
        <Sparkles size={11} strokeWidth={1.8} className="text-[#C9A961]" />
        <span><strong>Live dollar cost</strong> on every AI call · vendors get the same Studio</span>
        <ArrowRight size={11} strokeWidth={1.6} />
      </Link>
    );
  }

  if (variant === "footer") {
    return (
      <section
        className={`border-y border-[#1F3A3A] bg-[#0F2424] text-[#FAF8F5] ${className}`}
        data-testid="studio-vendor-nudge-footer"
      >
        <div className="container-page py-12 lg:py-16 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 text-[#C9A961]">
              <FlaskConical size={14} strokeWidth={1.5} />
              <span className="label !mt-0 text-[#C9A961]">AI Studio · for partners</span>
            </div>
            <h2 className="font-serif text-2xl lg:text-3xl mt-3 leading-tight !text-[#FAF8F5]">
              {COPY.headline}
            </h2>
            <p className="text-sm text-[#FAF8F5]/70 mt-3 max-w-xl leading-relaxed">
              {COPY.sub}
            </p>
            {showVendorHook && (
              <p className="text-sm text-[#FAF8F5]/70 mt-2 max-w-xl leading-relaxed">
                {COPY.vendor_hook}
              </p>
            )}
          </div>
          <div className="lg:col-span-5 lg:text-right">
            <Link
              to={COPY.href}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#C9A961] text-[#0F2424] font-semibold text-sm hover:bg-[#D4B677] transition"
              data-testid="studio-vendor-nudge-cta"
            >
              {COPY.cta} <ArrowRight size={14} strokeWidth={1.8} />
            </Link>
          </div>
        </div>
      </section>
    );
  }

  // default — "card"
  return (
    <div
      className={`rounded-2xl border-2 border-[#C9A961] bg-[#FFF8E1] p-5 ${className}`}
      data-testid="studio-vendor-nudge-card"
    >
      <div className="inline-flex items-center gap-2 text-[#8B7128]">
        <Sparkles size={12} strokeWidth={1.8} />
        <span className="label !mt-0 text-[#8B7128]">AI Studio</span>
      </div>
      <p className="font-serif text-lg mt-2 leading-snug">{COPY.headline}</p>
      <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">{COPY.sub}</p>
      {showVendorHook && (
        <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">{COPY.vendor_hook}</p>
      )}
    </div>
  );
}
