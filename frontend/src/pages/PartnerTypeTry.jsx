/* "Try the dashboard" sandbox preview — public, no auth.
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
      <span className="label text-[#476B6B]">Try the role</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Sparkles size={26} strokeWidth={1.2} className="text-[#C9A961]" /> {spec.title}
      </h1>
      <div className="divider-flame" />

      <p className="text-base text-[#5C6B6B] max-w-2xl mt-4">{spec.blurb}</p>

      <div className="mt-6 max-w-2xl">
        <PreviewModeBanner
          variant="sandbox"
          label="Sandbox preview"
          message="This is a public read-only walkthrough of the role. Nothing here applies until you apply or accept an invitation."
        />
      </div>

      {/* Subscription tiers */}
      {tiers.length > 0 && (
        <section className="mt-10 max-w-3xl">
          <p className="label">Subscription tiers</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
            {tiers.map((t) => (
              <div key={t.key} className="card p-4 relative" data-testid={`try-tier-${t.key}`}>
                {t.ribbon && (
                  <span className="absolute -top-2 right-2 bg-[#C9A961] text-white text-[9px] uppercase tracking-wider px-2 py-0.5 rounded">{t.ribbon}</span>
                )}
                <p className="font-serif text-base text-[#1A2424]">{t.label}</p>
                {t.rev_share != null && (
                  <p className="text-xs text-[#476B6B] mt-1">Rev share: {t.rev_share}%</p>
                )}
                {t.rev_share_birthright_ip != null && (
                  <p className="text-xs text-[#476B6B] mt-1">Birthright IP: {t.rev_share_birthright_ip}% · Own: {t.rev_share_other}%</p>
                )}
                {t.blurb && <p className="text-xs text-[#5C6B6B] mt-1 leading-relaxed">{t.blurb}</p>}
              </div>
            ))}
          </div>
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
