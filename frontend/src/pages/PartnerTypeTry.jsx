/* "Explore the role" preview — public, no auth.
 *
 *   /partner/types/:type/try
 *
 * Renders the same spec the invitation preview uses, but without a token.
 * Lets anyone browsing the site model what a role looks like before
 * applying or accepting an invitation.
 */
import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { Sparkles, Check, ChevronRight, HeartHandshake, ArrowRight } from "lucide-react";
import PreviewModeBanner from "../components/PreviewModeBanner";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PartnerTypeTry() {
  const { type } = useParams();
  const [spec, setSpec] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get(`${API_URL}/partners/preview-specs/${type}`).then((r) => {
      setSpec(r.data);
    }).catch((e) => {
      setError(e.response?.data?.detail || "Unknown partner type.");
    }).finally(() => setLoading(false));
  }, [type]);

  if (loading) return <div className="container-page py-20 text-center text-[#5C6B6B]">Loading…</div>;
  if (error || !spec) return (
    <div className="container-page py-20 text-center">
      <p className="font-serif text-2xl text-[#1A2424]">{error || "Not found."}</p>
      <Link to="/partner/types" className="btn-secondary mt-4 inline-block">Back to partner types</Link>
    </div>
  );

  const wam = spec.what_acceptance_means || {};
  const tiers = spec.options?.subscription_tiers || [];

  return (
    <div className="container-page py-10" data-testid={`partner-try-${type}`}>
      <span className="label text-[#476B6B]">Explore the role</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Sparkles size={26} strokeWidth={1.2} className="text-[#C9A961]" /> {spec.title}
      </h1>
      <div className="divider-flame" />

      <p className="text-base text-[#5C6B6B] max-w-2xl mt-4">{spec.blurb}</p>

      <div className="mt-6 max-w-2xl">
        <PreviewModeBanner
          variant="sandbox"
          label="Explore mode"
          message="This is a public read-only walkthrough of the role. Nothing here applies until you apply or accept an invitation."
        />
      </div>

      {/* Subscription tiers — costs, revenue split, and what's included */}
      {tiers.length > 0 && (
        <section className="mt-10 max-w-3xl">
          <p className="label">Subscription tiers &amp; costs</p>
          <p className="text-xs text-[#5C6B6B] mt-1 max-w-2xl">
            What you pay, what you keep, what the foundation keeps. Every number below is the actual current rate — no hidden fees, no upsell tiers behind these.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
            {tiers.map((t) => (
              <div key={t.key} className="card p-4 relative flex flex-col" data-testid={`try-tier-${t.key}`}>
                {t.ribbon && (
                  <span className="absolute -top-2 right-2 bg-[#C9A961] text-white text-[9px] uppercase tracking-wider px-2 py-0.5 rounded">{t.ribbon}</span>
                )}
                <p className="font-serif text-base text-[#1A2424]">{t.label}</p>

                {/* Cost */}
                {t.price_display && (
                  <p className="font-serif text-lg text-[#0F2424] mt-1" data-testid={`try-tier-price-${t.key}`}>
                    {t.price_display}
                  </p>
                )}
                {t.monthly_equivalent && t.monthly_equivalent !== t.price_display && (
                  <p className="text-[11px] text-[#5C6B6B] mt-0.5 italic">{t.monthly_equivalent}</p>
                )}

                {/* Revenue share — three possible schemas across partner types */}
                {(t.rev_share != null || t.rev_share_birthright_ip != null) && (
                  <div className="mt-2 pt-2 border-t border-[#E5E1D8] text-xs text-[#476B6B] space-y-0.5">
                    {t.rev_share != null && (
                      <p><strong className="text-[#0F2424]">Your revenue share:</strong> {t.rev_share}%</p>
                    )}
                    {t.rev_share_birthright_ip != null && (
                      <>
                        <p><strong className="text-[#0F2424]">Birthright IP workshops:</strong> you keep {t.rev_share_birthright_ip}%</p>
                        <p><strong className="text-[#0F2424]">Your own materials:</strong> you keep {t.rev_share_other}%</p>
                      </>
                    )}
                  </div>
                )}

                {/* Plain-language summary of what this tier means */}
                {(t.summary || t.blurb) && (
                  <p className="text-xs text-[#5C6B6B] mt-2 leading-relaxed">{t.summary || t.blurb}</p>
                )}
              </div>
            ))}
          </div>

          {/* Rolled-up foundation-share callout so it's visible before the reader scrolls to "What enrolling means" */}
          {wam.foundation_share && (
            <div
              className="mt-4 card p-4 bg-[#F4F1EA] border border-[#C9A961]/40"
              data-testid="try-foundation-share-callout"
            >
              <p className="label text-[#8B7128]">Foundation share (how the money flows)</p>
              <p className="text-sm text-[#1A2424] mt-1 leading-relaxed">{wam.foundation_share}</p>
            </div>
          )}
        </section>
      )}

      {/* Fulfillment modes (vendor only) */}
      {spec.options?.fulfillment_modes && (
        <section className="mt-10 max-w-3xl">
          <p className="label">Fulfillment options</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
            {spec.options.fulfillment_modes.map((m) => (
              <div key={m.key} className="card p-3" data-testid={`try-fulfillment-${m.key}`}>
                <p className="font-serif text-sm text-[#1A2424]">{m.label}</p>
                <p className="text-xs text-[#5C6B6B] mt-1">{m.blurb}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Dashboard features */}
      <section className="mt-10 max-w-3xl">
        <p className="label">What's in the dashboard</p>
        <ul className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm text-[#1A2424]">
          {(spec.options?.media || []).map((m, i) => (
            <li key={i} className="flex items-start gap-2"><Check size={12} className="mt-1 text-[#476B6B] flex-shrink-0" /> {m}</li>
          ))}
        </ul>
        {spec.options?.policies && (
          <>
            <p className="label mt-6">Policy controls</p>
            <ul className="mt-2 text-sm text-[#1A2424] space-y-1">
              {spec.options.policies.map((p, i) => (
                <li key={i} className="flex items-start gap-2"><Check size={12} className="mt-1 text-[#476B6B] flex-shrink-0" /> {p}</li>
              ))}
            </ul>
          </>
        )}
      </section>

      {/* What enrolling means */}
      <section className="mt-10 max-w-3xl card p-5 bg-[#FAF8F5]">
        <p className="font-serif text-lg text-[#1A2424] flex items-center gap-2">
          <HeartHandshake size={18} className="text-[#9E3C3C]" /> What enrolling means
        </p>
        <p className="text-sm text-[#1A2424] mt-2 leading-relaxed">{wam.summary}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-[#476B6B]">You agree to</p>
            <ul className="mt-1 text-sm text-[#1A2424] space-y-1">
              {(wam.obligations || []).map((o, i) => (
                <li key={i} className="flex items-start gap-2"><ChevronRight size={12} className="mt-1 text-[#C9A961]" />{o}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-[#476B6B]">You keep</p>
            <ul className="mt-1 text-sm text-[#1A2424] space-y-1">
              {(wam.you_keep || []).map((o, i) => (
                <li key={i} className="flex items-start gap-2"><ChevronRight size={12} className="mt-1 text-[#476B6B]" />{o}</li>
              ))}
            </ul>
          </div>
        </div>
        {wam.foundation_share && (
          <p className="text-xs text-[#5C6B6B] italic mt-4 border-t border-[#E5DDD0] pt-3">
            <strong className="text-[#1A2424] not-italic">Foundation share:</strong> {wam.foundation_share}
          </p>
        )}
      </section>

      {/* CTAs */}
      <section className="mt-10 max-w-3xl flex flex-col sm:flex-row gap-3" data-testid="try-ctas">
        <Link to={`/partners/apply?type=${type}`} className="btn-primary inline-flex items-center gap-2" data-testid={`try-apply-btn-${type}`}>
          Apply now <ArrowRight size={14} />
        </Link>
        <Link to="/partner/types" className="btn-secondary" data-testid="try-back-btn">
          Compare all partner types
        </Link>
        <Link to="/connect" className="btn-secondary" data-testid="try-contact-btn">
          Ask a question first
        </Link>
      </section>
    </div>
  );
}
