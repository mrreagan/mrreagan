/* Featured Artist Invitation — Explore-before-Embrace preview.
 *
 * Public page (no auth) reached from the invitation email link
 *   /gallery/invite/:token
 *
 * The artist can browse a fully pre-curated mock of their featured page with
 * default selections + the full menu of options. They only commit (enroll as
 * a birthright Artist partner) by clicking "Accept & enroll" at the bottom.
 * Decline is one click, no questions asked (optional note).
 */
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Sparkles, Check, X, Eye, ChevronRight, HeartHandshake, Info } from "lucide-react";
import { setStoredToken } from "../lib/api";

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Position cycle matches the backend STATEMENT_POSITIONS.
const POSITION_CLASS = {
  tl: "top-4 left-4 right-auto bottom-auto text-left",
  tr: "top-4 right-4 left-auto bottom-auto text-right",
  bl: "bottom-4 left-4 right-auto top-auto text-left",
  br: "bottom-4 right-4 left-auto top-auto text-right",
  cb: "bottom-0 left-0 right-0 top-auto text-center px-6 pb-6 pt-12 bg-gradient-to-t from-black/55 to-transparent",
};

export default function FeaturedInvite() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statement, setStatement] = useState("");
  const [statementSource, setStatementSource] = useState("freeform");
  const [layout, setLayout] = useState("single-wall");
  const [accentColor, setAccentColor] = useState("flame");
  const [position, setPosition] = useState("br");  // preview-only — server locks on month start
  const [step, setStep] = useState("explore");     // explore | accept | declined
  const [password, setPassword] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [declineReason, setDeclineReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    axios.get(`${API_URL}/gallery/invite/${token}`).then((r) => {
      setData(r.data);
      const inv = r.data.invite || {};
      setStatement(inv.default_statement || "");
      setLayout(inv.default_layout || "single-wall");
      setAccentColor(inv.default_accent_color || "flame");
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
  const opts = data.options || {};
  const acceptanceInfo = data.what_acceptance_means || {};
  const accentHex = (opts.accent_colors || []).find((c) => c.key === accentColor)?.hex || "#9E3C3C";

  if (inv.status === "accepted") {
    return (
      <div className="container-page py-16">
        <div className="card p-8 max-w-xl mx-auto text-center" data-testid="invite-already-accepted">
          <Check className="mx-auto text-[#476B6B]" size={36} />
          <p className="font-serif text-2xl mt-4">You're enrolled.</p>
          <p className="text-sm text-[#5C6B6B] mt-2">
            This invitation has been accepted. Visit your gallery space to keep curating.
          </p>
        </div>
      </div>
    );
  }

  if (inv.status === "declined" || step === "declined") {
    return (
      <div className="container-page py-16">
        <div className="card p-8 max-w-xl mx-auto text-center" data-testid="invite-declined">
          <p className="font-serif text-2xl">Noted, with gratitude.</p>
          <p className="text-sm text-[#5C6B6B] mt-3 leading-relaxed">
            Thank you for considering. The door stays open — feel free to write us any time.
          </p>
        </div>
      </div>
    );
  }

  const submitAccept = async () => {
    if (!agreed) {
      toast.error("Please agree to the Artist Partnership terms to enroll.");
      return;
    }
    if (password.length < 8) {
      toast.error("Please set a password (at least 8 characters).");
      return;
    }
    setSubmitting(true);
    try {
      const r = await axios.post(`${API_URL}/gallery/invite/${token}/accept`, {
        password,
        agreed_to_partnership_terms: true,
        signature_statement: statement || null,
        signature_statement_source: statementSource,
        layout, accent_color: accentColor,
      });
      if (r.data.session_token) setStoredToken(r.data.session_token);
      toast.success("Welcome — you're enrolled as a birthright Featured Artist.");
      navigate(r.data.next || "/gallery/me/space");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't accept the invitation.");
    } finally {
      setSubmitting(false);
    }
  };

  const submitDecline = async () => {
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/gallery/invite/${token}/decline`, {
        reason: declineReason.trim() || null,
      });
      setStep("declined");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't decline.");
    } finally {
      setSubmitting(false);
    }
  };

  const charsLeft = (opts.statement?.max_length || 180) - (statement || "").length;
  const charsClass = charsLeft < 0 ? "text-[#9E3C3C]" : charsLeft < 30 ? "text-[#C9A961]" : "text-[#5C6B6B]";

  return (
    <div className="container-page py-10" data-testid="featured-invite-page">
      <span className="label text-[#C9A961]" data-testid="invite-label">Featured Artist Invitation</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Sparkles size={26} strokeWidth={1.2} className="text-[#C9A961]" /> Hi, {inv.display_name}
      </h1>
      <div className="divider-flame" />

      {inv.editorial_reason && (
        <blockquote className="my-6 border-l-[3px] border-[#C9A961] pl-4 py-1 italic text-[#1A2424] text-base bg-[#FAF8F5] py-2 pr-3 max-w-2xl" data-testid="invite-reason">
          "{inv.editorial_reason}"
        </blockquote>
      )}
      {inv.intended_period_label && (
        <p className="text-sm text-[#5C6B6B] max-w-2xl">
          Intended month: <strong className="text-[#1A2424]">{inv.intended_period_label}</strong>.
        </p>
      )}

      <div className="bg-[#FAF8F5] border border-[#E5DDD0] rounded-md p-4 my-6 max-w-2xl flex items-start gap-3" data-testid="invite-no-commitment-banner">
        <Eye size={18} className="text-[#476B6B] mt-0.5 flex-shrink-0" />
        <div className="text-sm text-[#1A2424] leading-relaxed">
          <strong>Explore freely, no commitment.</strong> Try every option below — change the statement,
          swap colors, see how the page would feel. You only enroll as a birthright Artist when
          you click <em>Accept & enroll</em> at the bottom.
        </div>
      </div>

      {/* Live preview */}
      <section className="mt-2">
        <p className="label">Preview — your featured page</p>
        <div className="card overflow-hidden mt-2 max-w-3xl" data-testid="invite-preview">
          <div className="relative aspect-[5/3] sm:aspect-[16/9] w-full bg-gradient-to-br from-[#C9A961] to-[#9E3C3C] flex items-center justify-center text-white" style={{ background: `linear-gradient(135deg, ${accentHex} 0%, #1A2424 100%)` }}>
            <div className="text-center px-6 opacity-90">
              <p className="text-xs uppercase tracking-[0.2em] opacity-80">Featured Hero — your signature image goes here</p>
            </div>
            {statement && statementSource !== "blank" && (
              <div className={`absolute pointer-events-none max-w-[78%] ${POSITION_CLASS[position]}`} data-testid={`preview-statement-${position}`}>
                <span className="inline-block px-3 py-1.5 font-serif text-white text-base sm:text-lg leading-snug" style={{
                  background: position === "cb" ? "transparent" : "rgba(0,0,0,0.35)",
                  borderLeft: position === "cb" ? "none" : `2px solid ${accentHex}`,
                  textShadow: "0 1px 8px rgba(0,0,0,0.45)",
                  backdropFilter: position === "cb" ? "none" : "blur(2px)",
                }}>
                  {statement}
                </span>
              </div>
            )}
            <div className="absolute top-3 left-3 bg-[#C9A961] text-white text-[10px] uppercase tracking-[0.18em] px-2 py-1 rounded">
              Foundation pick
            </div>
            <div className="absolute bottom-0 left-0 right-0 px-4 py-2 bg-gradient-to-t from-black/55 to-transparent">
              <p className="font-serif text-white text-base sm:text-lg">{inv.display_name}</p>
            </div>
          </div>
          <div className="p-4 text-xs text-[#5C6B6B]">
            Layout: <strong className="text-[#1A2424]">{layout}</strong> · Accent: <strong className="text-[#1A2424]">{accentColor}</strong>
            {' · '}Statement position is <strong>locked once your month begins</strong> and rotates with the lineup.
          </div>
        </div>
      </section>

      {/* Statement composer */}
      <section className="mt-8 max-w-2xl">
        <p className="label">Your featured statement <span className="text-[#5C6B6B]">· up to {opts.statement?.max_length || 180} characters</span></p>
        <p className="text-xs text-[#5C6B6B] mt-1 mb-3 italic">"Brevity is the soul of wit." — Birthright recommends 90–150 characters.</p>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-3">
          {(opts.statement?.choices || []).map((c) => (
            <button
              key={c.key}
              onClick={() => {
                setStatementSource(c.key);
                if (c.key === "blank") setStatement("");
                if (c.key === "ai_summary" && inv.default_statement) setStatement(inv.default_statement);
              }}
              className={`text-left px-3 py-2 border rounded text-xs leading-tight transition ${
                statementSource === c.key
                  ? "border-[#9E3C3C] bg-[#FAF8F5] text-[#1A2424]"
                  : "border-[#E5DDD0] text-[#5C6B6B] hover:border-[#C9A961]"
              }`}
              data-testid={`statement-option-${c.key}`}
            >
              <div className="font-serif text-sm text-[#1A2424]">{c.label}</div>
              <div className="text-[10px] mt-1 leading-relaxed">{c.blurb}</div>
            </button>
          ))}
        </div>
        <textarea
          value={statement}
          maxLength={opts.statement?.max_length || 180}
          onChange={(e) => setStatement(e.target.value)}
          disabled={statementSource === "blank"}
          rows={2}
          className="input-field font-serif text-base"
          placeholder={statementSource === "blank" ? "Image speaks for itself — no overlay text will render." : "Write something brief and true…"}
          data-testid="statement-textarea"
        />
        <p className={`text-xs mt-1 ${charsClass}`}>{(statement || "").length} / {opts.statement?.max_length || 180}</p>
      </section>

      {/* Layout */}
      <section className="mt-8 max-w-2xl">
        <p className="label">Layout</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
          {(opts.layouts || []).map((L) => (
            <button
              key={L.key}
              onClick={() => setLayout(L.key)}
              className={`text-left p-3 border rounded text-xs transition ${
                layout === L.key ? "border-[#9E3C3C] bg-[#FAF8F5]" : "border-[#E5DDD0] hover:border-[#C9A961]"
              }`}
              data-testid={`layout-option-${L.key}`}
            >
              <div className="font-serif text-sm text-[#1A2424]">{L.label}</div>
              <div className="text-[10px] text-[#5C6B6B] mt-1 leading-relaxed">{L.blurb}</div>
            </button>
          ))}
        </div>
      </section>

      {/* Accent color */}
      <section className="mt-8 max-w-2xl">
        <p className="label">Accent color</p>
        <div className="flex flex-wrap gap-2 mt-2">
          {(opts.accent_colors || []).map((c) => (
            <button
              key={c.key}
              onClick={() => setAccentColor(c.key)}
              className={`px-3 py-2 border rounded text-xs flex items-center gap-2 transition ${
                accentColor === c.key ? "border-[#9E3C3C]" : "border-[#E5DDD0] hover:border-[#C9A961]"
              }`}
              data-testid={`accent-option-${c.key}`}
            >
              <span className="w-3 h-3 rounded-full inline-block" style={{ background: c.hex }} />
              {c.label}
            </button>
          ))}
        </div>
      </section>

      {/* Position preview (educational only — server locks on month start) */}
      <section className="mt-8 max-w-2xl">
        <p className="label">Where the statement sits on your hero image</p>
        <p className="text-xs text-[#5C6B6B] mt-1 mb-2 italic flex items-start gap-1.5">
          <Info size={12} className="mt-0.5 text-[#C9A961]" />
          Each featured artist gets a position. The placement is set when your month begins so adjacent
          artists' overlays vary — you can preview each here, but the final position is chosen by the
          system and stays locked for the duration of your month.
        </p>
        <div className="flex flex-wrap gap-2 mt-2">
          {(opts.statement_positions || []).map((p) => (
            <button
              key={p.key}
              onClick={() => setPosition(p.key)}
              className={`px-3 py-1.5 border rounded text-xs transition ${
                position === p.key ? "border-[#9E3C3C] bg-[#FAF8F5]" : "border-[#E5DDD0] hover:border-[#C9A961]"
              }`}
              data-testid={`position-preview-${p.key}`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </section>

      {/* All other options — list-only for browse */}
      <section className="mt-8 max-w-2xl">
        <p className="label">All curation options available after you accept</p>
        <ul className="mt-2 text-sm text-[#5C6B6B] leading-relaxed grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
          {(opts.media || []).map((m, i) => (
            <li key={i} className="flex items-start gap-2"><Check size={12} className="mt-1 text-[#476B6B] flex-shrink-0" /> {m}</li>
          ))}
        </ul>
      </section>

      {/* What acceptance means + partnership terms */}
      <section className="mt-10 max-w-2xl card p-5 bg-[#FAF8F5]" data-testid="what-acceptance-means">
        <p className="font-serif text-lg text-[#1A2424] flex items-center gap-2">
          <HeartHandshake size={18} className="text-[#9E3C3C]" /> What enrolling means
        </p>
        <p className="text-sm text-[#1A2424] mt-2 leading-relaxed">{acceptanceInfo.summary}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-[#476B6B]">You agree to</p>
            <ul className="mt-1 text-sm text-[#1A2424] leading-relaxed space-y-1">
              {(acceptanceInfo.obligations || []).map((o, i) => (
                <li key={i} className="flex items-start gap-2"><ChevronRight size={12} className="mt-1 text-[#C9A961]" />{o}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-[#476B6B]">You keep</p>
            <ul className="mt-1 text-sm text-[#1A2424] leading-relaxed space-y-1">
              {(acceptanceInfo.you_keep || []).map((o, i) => (
                <li key={i} className="flex items-start gap-2"><ChevronRight size={12} className="mt-1 text-[#476B6B]" />{o}</li>
              ))}
            </ul>
          </div>
        </div>
        {acceptanceInfo.foundation_share && (
          <p className="text-xs text-[#5C6B6B] italic mt-4 border-t border-[#E5DDD0] pt-3">
            <strong className="text-[#1A2424] not-italic">Foundation share:</strong> {acceptanceInfo.foundation_share}
          </p>
        )}
      </section>

      {/* Commit */}
      {step !== "accept" ? (
        <section className="mt-8 max-w-2xl flex flex-col sm:flex-row gap-3" data-testid="invite-actions">
          <button
            className="btn-primary flex items-center justify-center gap-2"
            onClick={() => setStep("accept")}
            data-testid="invite-accept-btn"
          >
            <Check size={16} /> Accept &amp; enroll
          </button>
          <button
            className="btn-secondary"
            onClick={() => {
              const r = window.prompt("Optionally, let us know why? (or leave blank)");
              setDeclineReason(r || "");
              submitDecline();
            }}
            data-testid="invite-decline-btn"
            disabled={submitting}
          >
            <X size={14} className="inline -mt-0.5" /> No, thank you
          </button>
        </section>
      ) : (
        <section className="mt-8 max-w-2xl card p-5" data-testid="accept-form">
          <p className="font-serif text-lg text-[#1A2424]">One last step — set your password</p>
          <p className="text-xs text-[#5C6B6B] mt-1">We'll create your birthright Artist account using <strong className="text-[#1A2424]">{inv.contact_email || "your email"}</strong>.</p>
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
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="mt-1"
              data-testid="accept-terms-checkbox"
            />
            <span className="leading-relaxed">
              I've read the above and agree to the birthright <em>Artist Partnership Agreement</em>.
              I understand that enrolling creates my partner profile and locks in this month's featured slot.
            </span>
          </label>
          <div className="mt-4 flex gap-3">
            <button
              className="btn-primary"
              onClick={submitAccept}
              disabled={submitting}
              data-testid="accept-confirm-btn"
            >
              {submitting ? "Enrolling…" : "Confirm enrollment"}
            </button>
            <button
              className="btn-secondary"
              onClick={() => setStep("explore")}
              data-testid="accept-cancel-btn"
              disabled={submitting}
            >
              Back to preview
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
