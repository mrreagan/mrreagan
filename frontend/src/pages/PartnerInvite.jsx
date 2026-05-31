/* Generic Partner Invitation — Explore-before-Embrace preview.
 *
 * Public page reached from invitation emails for ANY partner type:
 *   /partner/invite/:token
 *
 * Renders the partner-type-specific spec (defaults, options, obligations,
 * what you keep, foundation share) and lets the prospect explore freely.
 * They only enroll by clicking "Accept & enroll" at the bottom.
 */
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import {
  Sparkles, Check, X, ChevronRight, HeartHandshake,
  Briefcase,
} from "lucide-react";
import PreviewModeBanner from "../components/PreviewModeBanner";
import { setStoredToken } from "../lib/api";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PartnerInvite() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tier, setTier] = useState(null);
  const [step, setStep] = useState("explore");
  const [password, setPassword] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedOptions, setSelectedOptions] = useState({});

  useEffect(() => {
    axios.get(`${API_URL}/partners/invite/${token}`).then((r) => {
      setData(r.data);
      setTier(r.data.invite?.suggested_subscription_tier || null);
    }).catch((e) => {
      toast.error(e.response?.data?.detail || "Invitation not found or expired.");
    }).finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="container-page py-20 text-center text-[#5C6B6B]">Loading…</div>;
  if (!data) return (
    <div className="container-page py-20 text-center">
      <p className="font-serif text-2xl text-[#1A2424]">This invitation isn't available.</p>
      <p className="text-sm text-[#5C6B6B] mt-2">It may have expired or already been used.</p>
    </div>
  );

  const inv = data.invite || {};
  const spec = data.spec || {};
  const wam = spec.what_acceptance_means || {};
  const tiers = spec.options?.subscription_tiers || [];

  if (inv.status === "accepted") {
    return (
      <div className="container-page py-16">
        <div className="card p-8 max-w-xl mx-auto text-center" data-testid="invite-already-accepted">
          <Check className="mx-auto text-[#476B6B]" size={36} />
          <p className="font-serif text-2xl mt-4">You're enrolled.</p>
          <p className="text-sm text-[#5C6B6B] mt-2">This invitation has been accepted.</p>
        </div>
      </div>
    );
  }

  if (inv.status === "declined") {
    return (
      <div className="container-page py-16">
        <div className="card p-8 max-w-xl mx-auto text-center" data-testid="invite-declined">
          <p className="font-serif text-2xl">Noted, with gratitude.</p>
          <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">Thank you for considering. The door stays open.</p>
        </div>
      </div>
    );
  }

  const submitAccept = async () => {
    if (!agreed) return toast.error("Please agree to the Partnership terms to enroll.");
    if (password.length < 8) return toast.error("Please set a password (at least 8 characters).");
    setSubmitting(true);
    try {
      const r = await axios.post(`${API_URL}/partners/invite/${token}/accept`, {
        password,
        agreed_to_partnership_terms: true,
        selected_subscription_tier: tier || undefined,
        selected_options: Object.keys(selectedOptions).length ? selectedOptions : undefined,
      });
      if (r.data.session_token) setStoredToken(r.data.session_token);
      toast.success(`Welcome — you're enrolled as a Birthright ${spec.title}.`);
      navigate(r.data.next || "/dashboard/partner");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't accept the invitation.");
    } finally {
      setSubmitting(false);
    }
  };

  const submitDecline = async (reason) => {
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/partners/invite/${token}/decline`, { reason });
      window.location.reload();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't decline.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container-page py-10" data-testid="partner-invite-page">
      {/* Quiet brand mark */}
      <div className="flex items-center gap-2 mb-1">
        <Sparkles size={18} strokeWidth={1.2} className="text-[#C9A961]" />
        <span className="label text-[#C9A961]" data-testid="invite-label">{spec.title} invitation</span>
      </div>
      <h1 className="editorial-h1 mt-1 text-left" data-testid="invite-greeting">
        Hi, {inv.display_name}
      </h1>
      <div className="divider-flame" />

      {inv.note_to_prospect && (
        <blockquote className="my-6 border-l-[3px] border-[#C9A961] pl-4 italic text-[#1A2424] text-base bg-[#FAF8F5] py-2 pr-3 max-w-2xl" data-testid="invite-note">
          "{inv.note_to_prospect}"
        </blockquote>
      )}

      {/* MISSION ALIGNMENT BLUF — leads the entire invitation */}
      {inv.mission_alignment && (
        <div
          className="mt-6 max-w-2xl p-6 rounded-lg border-2 border-[#9E3C3C] bg-gradient-to-br from-[#FAF8F5] to-[#F4F1EA]"
          data-testid="mission-alignment-card"
        >
          <p className="text-[10px] uppercase tracking-[2px] text-[#9E3C3C] mb-3">
            Why we're reaching out
          </p>
          <p className="font-serif text-lg sm:text-xl text-[#1A2424] leading-relaxed">
            {inv.mission_alignment}
          </p>
        </div>
      )}

      {/* Highlight — what specifically caught the foundation's eye */}
      {inv.highlight_url && (
        <a
          href={inv.highlight_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 max-w-2xl block rounded border border-[#C9A961] bg-white hover:bg-[#FAF8F5] transition overflow-hidden"
          data-testid="highlight-card"
        >
          {inv.highlight_image_url && (
            <div className="w-full bg-[#F4F1EA] flex items-center justify-center" data-testid="highlight-image">
              <img
                src={inv.highlight_image_url}
                alt={inv.highlight_label || "highlight"}
                className="w-full max-h-[360px] object-cover"
              />
            </div>
          )}
          <div className="p-4">
            <p className="text-[10px] uppercase tracking-[1.5px] text-[#476B6B] mb-2">
              What we saw — your {(inv.highlight_label || "site").replace("_", " ")}
            </p>
            {inv.highlight_excerpt && (
              <blockquote className="text-[15px] italic text-[#1A2424] border-l-2 border-[#C9A961] pl-3 mb-2">
                "{inv.highlight_excerpt}"
              </blockquote>
            )}
            <p className="text-xs text-[#9E3C3C] font-serif break-all">{inv.highlight_url}</p>
            {inv.highlight_reason && (
              <p className="text-xs text-[#5C6B6B] mt-2 leading-relaxed">{inv.highlight_reason}</p>
            )}
          </div>
        </a>
      )}

      <p className="text-base text-[#5C6B6B] max-w-2xl mt-6">
        For these reasons, we'd like to invite you to partner with us as a <strong className="text-[#1A2424]">{spec.title}</strong>.
      </p>
      <p className="text-sm text-[#5C6B6B] max-w-2xl mt-2">{spec.blurb}</p>

      <div className="mt-6 max-w-2xl" data-testid="invite-no-commitment-banner">
        <PreviewModeBanner
          variant="invitation"
          label="Explore freely, no commitment"
          message="Browse every option below — change the tier, try the configuration, see how the role would feel. You only enroll when you click Accept & enroll at the bottom."
        />
      </div>

      {/* Subscription tiers — clear breakdown of WHAT you pay and WHAT YOU KEEP on each order channel */}
      {tiers.length > 0 && (
        <section className="mt-8 max-w-3xl" data-testid="tiers-section">
          <p className="label">Subscription tier</p>
          <p className="text-xs text-[#5C6B6B] mt-1 mb-3">
            Pick your own — longer commitments give you a better split on Birthright-fulfilled orders.
            <strong className="text-[#1A2424]"> Off-site referrals are always 100% yours</strong> — the foundation
            is paid only by your subscription on those.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {tiers.map((t) => {
              const ribbon = t.ribbon || (inv.suggested_subscription_tier === t.key ? "Suggested" : null);
              const isSelected = tier === t.key;
              const hasStructuredBreakdown = t.pod_vendor_pct != null;
              return (
                <button
                  key={t.key}
                  onClick={() => setTier(t.key)}
                  className={`relative text-left p-4 border rounded transition flex flex-col ${
                    isSelected ? "border-[#9E3C3C] border-2 bg-[#FAF8F5]" : "border-[#E5DDD0] hover:border-[#C9A961]"
                  }`}
                  data-testid={`tier-option-${t.key}`}
                >
                  {ribbon && (
                    <span className="absolute -top-2 right-2 bg-[#C9A961] text-white text-[9px] uppercase tracking-wider px-2 py-0.5 rounded">{ribbon}</span>
                  )}
                  <div className="font-serif text-base text-[#1A2424]">{t.label || t.key}</div>
                  {t.price_display && (
                    <div className="text-sm text-[#1A2424] font-semibold mt-1">{t.price_display}</div>
                  )}
                  {t.monthly_equivalent && t.monthly_equivalent !== t.price_display && (
                    <div className="text-[10px] text-[#5C6B6B]">{t.monthly_equivalent}</div>
                  )}
                  {hasStructuredBreakdown ? (
                    <>
                      <div className="mt-3 pt-3 border-t border-[#E5DDD0] space-y-2">
                        <div>
                          <p className="text-[9px] uppercase tracking-wider text-[#476B6B]">On birthright.org</p>
                          <p className="text-xs text-[#1A2424] mt-0.5">
                            You keep <strong>{t.pod_vendor_pct}%</strong><br />
                            <span className="text-[#5C6B6B]">Foundation {t.pod_foundation_pct}%</span>
                          </p>
                        </div>
                        <div>
                          <p className="text-[9px] uppercase tracking-wider text-[#476B6B]">Off-site (your store)</p>
                          <p className="text-xs text-[#1A2424] mt-0.5">
                            You keep <strong>{t.offsite_vendor_pct}%</strong>
                          </p>
                        </div>
                      </div>
                      {t.summary && (
                        <p className="text-[10px] text-[#5C6B6B] mt-2 leading-relaxed italic">{t.summary}</p>
                      )}
                    </>
                  ) : (
                    <>
                      {t.rev_share != null && (
                        <div className="text-[10px] text-[#476B6B] mt-2">Rev share: {t.rev_share}%</div>
                      )}
                      {t.rev_share_birthright_ip != null && (
                        <div className="text-[10px] text-[#476B6B] mt-2">
                          Birthright IP: {t.rev_share_birthright_ip}% · Own: {t.rev_share_other}%
                        </div>
                      )}
                      {t.blurb && <div className="text-[10px] text-[#5C6B6B] mt-1 leading-relaxed">{t.blurb}</div>}
                    </>
                  )}
                </button>
              );
            })}
          </div>
        </section>
      )}

      {/* Vendor fulfillment modes (vendor only) */}
      {spec.options?.fulfillment_modes && (
        <section className="mt-8 max-w-2xl">
          <p className="label">Fulfillment mode</p>
          <p className="text-xs text-[#5C6B6B] mt-1 mb-3">Pick how Birthright handles orders for your products. You can change this per-product after enrolling.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {spec.options.fulfillment_modes.map((m) => (
              <button
                key={m.key}
                onClick={() => setSelectedOptions({ ...selectedOptions, fulfillment_mode: m.key })}
                className={`text-left p-3 border rounded transition ${
                  selectedOptions.fulfillment_mode === m.key
                    ? "border-[#9E3C3C] bg-[#FAF8F5]"
                    : "border-[#E5DDD0] hover:border-[#C9A961]"
                }`}
                data-testid={`fulfillment-option-${m.key}`}
              >
                <div className="font-serif text-sm text-[#1A2424]">{m.label}</div>
                <div className="text-[10px] text-[#5C6B6B] mt-1 leading-relaxed">{m.blurb}</div>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Media + dashboard features list */}
      <section className="mt-8 max-w-2xl">
        <p className="label">What's in your dashboard after enrolling</p>
        <ul className="mt-2 text-sm text-[#1A2424] leading-relaxed grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
          {(spec.options?.media || []).map((m, i) => (
            <li key={i} className="flex items-start gap-2"><Check size={12} className="mt-1 text-[#476B6B] flex-shrink-0" /> {m}</li>
          ))}
        </ul>
        {spec.options?.policies && (
          <>
            <p className="text-xs text-[#5C6B6B] uppercase tracking-wider mt-4 mb-2">Policy controls</p>
            <ul className="text-sm text-[#1A2424] leading-relaxed space-y-1">
              {spec.options.policies.map((p, i) => (
                <li key={i} className="flex items-start gap-2"><Check size={12} className="mt-1 text-[#476B6B] flex-shrink-0" /> {p}</li>
              ))}
            </ul>
          </>
        )}
        {spec.options?.presents_birthright_ip_choice && (
          <p className="text-xs text-[#5C6B6B] italic mt-3 border-l-2 border-[#C9A961] pl-3">
            {spec.options.presents_birthright_ip_choice}
          </p>
        )}
      </section>

      {/* What enrolling means */}
      <section className="mt-10 max-w-2xl card p-5 bg-[#FAF8F5]" data-testid="what-acceptance-means">
        <p className="font-serif text-lg text-[#1A2424] flex items-center gap-2">
          <HeartHandshake size={18} className="text-[#9E3C3C]" /> What enrolling means
        </p>
        <p className="text-sm text-[#1A2424] mt-2 leading-relaxed">{wam.summary}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-[#476B6B]">You agree to</p>
            <ul className="mt-1 text-sm text-[#1A2424] leading-relaxed space-y-1">
              {(wam.obligations || []).map((o, i) => (
                <li key={i} className="flex items-start gap-2"><ChevronRight size={12} className="mt-1 text-[#C9A961]" />{o}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-[#476B6B]">You keep</p>
            <ul className="mt-1 text-sm text-[#1A2424] leading-relaxed space-y-1">
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

      {/* Commit */}
      {step !== "accept" ? (
        <section className="mt-8 max-w-2xl flex flex-col sm:flex-row gap-3" data-testid="invite-actions">
          <button className="btn-primary flex items-center justify-center gap-2" onClick={() => setStep("accept")} data-testid="invite-accept-btn">
            <Check size={16} /> Accept &amp; enroll
          </button>
          <button
            className="btn-secondary"
            onClick={() => {
              const r = window.prompt("Optionally, let us know why? (or leave blank)");
              submitDecline(r || null);
            }}
            data-testid="invite-decline-btn"
            disabled={submitting}
          >
            <X size={14} className="inline -mt-0.5" /> No, thank you
          </button>
        </section>
      ) : (
        <section className="mt-8 max-w-2xl card p-5" data-testid="accept-form">
          <p className="font-serif text-lg text-[#1A2424] flex items-center gap-2">
            <Briefcase size={16} /> One last step — set your password
          </p>
          <p className="text-xs text-[#5C6B6B] mt-1">
            We'll create your Birthright account using <strong className="text-[#1A2424]">{inv.contact_email || "your email"}</strong>.
          </p>
          <input
            type="password"
            placeholder="Choose a password (8+ characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-field mt-3"
            data-testid="accept-password-input"
            autoComplete="new-password"
          />
          <label className="mt-3 flex items-start gap-2 text-sm text-[#1A2424]">
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="mt-1" data-testid="accept-terms-checkbox" />
            <span className="leading-relaxed">
              I've read the above and agree to the Birthright <em>{spec.title} Partnership Agreement</em>.
              I understand enrolling creates my partner profile.
            </span>
          </label>
          <div className="mt-4 flex gap-3">
            <button className="btn-primary" onClick={submitAccept} disabled={submitting} data-testid="accept-confirm-btn">
              {submitting ? "Enrolling…" : "Confirm enrollment"}
            </button>
            <button className="btn-secondary" onClick={() => setStep("explore")} disabled={submitting} data-testid="accept-cancel-btn">
              Back to preview
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
