/* eslint-disable */
import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { Palette, Plus, Trash2, Save, Sparkles, ArrowUpRight, Download, Share2, X, History } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const LAYOUTS = ["single-wall", "two-column", "salon-hang", "audio-forward"];
const ACCENTS = ["flame", "moss", "river", "ochre", "indigo", "graphite"];


// Tier card — fetches the current artist's tier + basis + runway, lifetime
// patronage total, 12-month revenue sparkline, AND tier-history timeline +
// celebration banner for unacknowledged UP transitions.
function ArtistTierCard() {
  const [tier, setTier] = useState(null);
  const [payouts, setPayouts] = useState(null);
  const [series, setSeries] = useState(null);
  const [history, setHistory] = useState(null);
  const [pendingShare, setPendingShare] = useState(null);
  const refresh = async () => {
    try {
      const [tierR, payR, seriesR, histR] = await Promise.all([
        api.get("/partner/me/artist-tier"),
        api.get("/partner/me/artist-payouts"),
        api.get("/partner/me/monthly-revenue?months=12"),
        api.get("/partner/me/tier-history"),
      ]);
      setTier(tierR.data);
      setPayouts(payR.data);
      setSeries(seriesR.data);
      setHistory(histR.data?.rows || []);
      setPendingShare(histR.data?.pending_share || null);
    } catch (_) { /* artist may not have a profile yet */ }
  };
  useEffect(() => { refresh(); }, []);
  if (!tier) return null;
  const fmt = (n) => `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

  const dismissShare = async () => {
    if (!pendingShare) return;
    try {
      await api.post(`/partner/me/tier-history/${pendingShare.id}/dismiss-share`);
      setPendingShare(null);
    } catch (e) {
      toast.error("Couldn't dismiss");
    }
  };
  return (
    <section className="card p-6 mt-6 max-w-3xl" data-testid="artist-tier-card">
      {pendingShare && tier.slug && (
        <TierUpCelebrationBanner
          slug={tier.slug}
          tier={tier}
          history={pendingShare}
          onDismiss={dismissShare}
        />
      )}
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <p className="label text-[#C9A961]">Your partnership tier</p>
          <h2 className="font-serif italic text-2xl mt-1">
            {tier.tier_icon} {tier.tier_label}
          </h2>
        </div>
        <Link
          to="/partner/artist"
          data-testid="artist-tier-card-terms-link"
          className="text-xs uppercase tracking-[0.18em] text-[#476B6B] hover:text-[#1A2424] inline-flex items-center gap-1"
        >
          Full terms <ArrowUpRight size={14} strokeWidth={1.6} />
        </Link>
      </div>

      <dl className="grid sm:grid-cols-3 gap-4 mt-5 text-sm">
        <div>
          <dt className="label">12-mo Birthright revenue</dt>
          <dd className="font-serif text-lg mt-1">{fmt(tier.basis_12mo)}</dd>
        </div>
        <div>
          <dt className="label">Inbound % (you earn)</dt>
          <dd className="font-serif text-lg mt-1">{tier.inbound_pct}%</dd>
        </div>
        <div>
          <dt className="label">Outbound % (you contribute)</dt>
          <dd className="font-serif text-lg mt-1">
            {tier.outbound_pct}%
            {tier.effective_outbound_pct > 0 && tier.effective_outbound_pct !== tier.outbound_pct && (
              <span className="text-xs text-[#5C6B6B] italic ml-2">eff. {tier.effective_outbound_pct}%</span>
            )}
          </dd>
        </div>
      </dl>

      {/* Lifetime patronage — total list_price across all artist_sale_payouts */}
      {payouts && payouts.summary?.count > 0 && (
        <div
          className="mt-5 pt-5 border-t border-[#E5E1D8] flex items-baseline justify-between gap-4 flex-wrap"
          data-testid="artist-patronage-total"
        >
          <div>
            <p className="label text-[#A87A4A]">Foundation patronage to date</p>
            <p className="font-serif text-2xl text-[#2C4E5A] italic mt-1">
              {fmt(payouts.summary.lifetime_total)}
            </p>
            <p className="text-xs text-[#5C6B6B] mt-1">
              across {payouts.summary.count} {payouts.summary.count === 1 ? "sale" : "sales"} through Birthright
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-[#5C6B6B]">
              <span className="inline-block w-2 h-2 rounded-full bg-[#2E5C46] mr-1.5" />
              Paid: <strong>{fmt(payouts.summary.paid_to_date)}</strong>
            </p>
            <p className="text-xs text-[#5C6B6B] mt-1">
              <span className="inline-block w-2 h-2 rounded-full bg-[#C9A961] mr-1.5" />
              Pending: <strong>{fmt(payouts.summary.pending_payout)}</strong>
            </p>
          </div>
        </div>
      )}

      {/* Tier-history sparkline */}
      {series && series.length > 0 && (
        <div className="mt-5" data-testid="artist-revenue-sparkline">
          <p className="label text-[#476B6B]">Monthly Birthright revenue · last 12 months</p>
          <RevenueSparkline series={series} />
        </div>
      )}

      {tier.next_tier_label && (
        <p className="text-xs text-[#5C6B6B] italic mt-4">
          <strong>{fmt(tier.distance_usd)}</strong> until {tier.next_tier_label}.
          Tier transitions take effect on the 1st of the following month.
        </p>
      )}
      {tier.source === "admin_override" && (
        <p className="text-xs text-[#C9A961] italic mt-2">
          Tier set manually by Foundation operator: {tier.override_reason}
        </p>
      )}

      {/* Tier history audit timeline (only if there's >=1 real transition) */}
      {history && history.some(h => h.direction !== "initial") && (
        <TierHistoryTimeline history={history} />
      )}
    </section>
  );
}


// Small celebration card shown above the tier card when the artist has
// transitioned UP a tier and hasn't dismissed it. Provides Copy-link,
// Download (PNG + SVG), and Web-Share buttons + a quiet ✕ to dismiss.
function TierUpCelebrationBanner({ slug, tier, history, onDismiss }) {
  const backendBase = process.env.REACT_APP_BACKEND_URL || "";
  const pngUrl = `${backendBase}/api/share/artist/${slug}/tier-card.png`;
  const svgUrl = `${backendBase}/api/share/artist/${slug}/tier-card.svg`;
  const galleryUrl = `https://birthright.live/partners/${slug}`;
  const shareText = `${tier.tier_icon} I just reached ${tier.tier_label} on birthright.live — patronage with character.`;

  const copyShare = async () => {
    try {
      await navigator.clipboard.writeText(`${shareText}\n${galleryUrl}`);
      toast.success("Share text copied");
    } catch (_) { toast.error("Couldn't copy"); }
  };
  const tryNativeShare = async () => {
    const data = { title: "Birthright Artist Tier", text: shareText, url: galleryUrl };
    if (navigator.share) {
      try { await navigator.share(data); } catch (_) { /* user cancelled */ }
    } else {
      copyShare();
    }
  };
  return (
    <div
      className="relative mb-5 rounded-md border border-[#C9A961]/40 bg-gradient-to-r from-[#F8F4EC] to-[#FBF7EC] p-4 sm:p-5"
      data-testid="artist-tier-up-banner"
    >
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        data-testid="tier-up-dismiss"
        className="absolute top-2 right-2 text-[#5C6B6B] hover:text-[#1A2424]"
      >
        <X size={14} strokeWidth={1.8} />
      </button>
      <div className="flex items-start gap-4 flex-wrap">
        <div className="flex-1 min-w-[220px]">
          <p className="label text-[#A87A4A]">Tier achievement</p>
          <h3 className="font-serif italic text-xl mt-1">
            {tier.tier_icon} You just reached {tier.tier_label}.
          </h3>
          <p className="text-sm text-[#5C6B6B] mt-1.5">
            Quietly proud of you. Your Foundation-attributed work crossed the
            {" "}<strong>{tier.tier_label}</strong> threshold. Share the moment —
            every visit your share drives is referral-attributed back to you.
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            <button
              onClick={tryNativeShare}
              className="btn-primary text-xs inline-flex items-center gap-1.5"
              data-testid="tier-up-share-btn"
            >
              <Share2 size={13} strokeWidth={1.8} /> Share
            </button>
            <a
              href={pngUrl}
              download={`birthright-${slug}-${tier.tier_key}.png`}
              className="btn-outline text-xs inline-flex items-center gap-1.5"
              data-testid="tier-up-download-png"
            >
              <Download size={13} strokeWidth={1.8} /> Download PNG
            </a>
            <a
              href={svgUrl}
              download={`birthright-${slug}-${tier.tier_key}.svg`}
              className="btn-outline text-xs inline-flex items-center gap-1.5"
              data-testid="tier-up-download-svg"
            >
              <Download size={13} strokeWidth={1.8} /> SVG
            </a>
            <button
              onClick={copyShare}
              className="btn-outline text-xs inline-flex items-center gap-1.5"
              data-testid="tier-up-copy"
            >
              Copy share text
            </button>
          </div>
        </div>
        <a
          href={pngUrl}
          target="_blank"
          rel="noreferrer"
          className="block flex-shrink-0 w-[180px] sm:w-[220px]"
          data-testid="tier-up-card-preview"
        >
          <img
            src={pngUrl}
            alt={`${tier.tier_label} share card`}
            className="w-full h-auto rounded border border-[#E5E1D8] shadow-sm"
          />
        </a>
      </div>
    </div>
  );
}


// Vertical timeline of past tier changes — initial baseline rows are
// skipped because the user explicitly chose to start tracking forward
// from the deployment. Each row shows: when, direction, from → to, basis.
function TierHistoryTimeline({ history }) {
  const fmt = (n) => `$${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  const rows = history.filter(h => h.direction !== "initial");
  if (rows.length === 0) return null;
  return (
    <div className="mt-6 pt-5 border-t border-[#E5E1D8]" data-testid="artist-tier-history-timeline">
      <p className="label text-[#476B6B] inline-flex items-center gap-1.5">
        <History size={11} strokeWidth={1.8} /> Tier history
      </p>
      <ol className="mt-3 space-y-3">
        {rows.map(r => {
          const up = r.direction === "up";
          return (
            <li
              key={r.id}
              className="flex items-baseline gap-3 text-sm"
              data-testid={`tier-history-row-${r.id}`}
            >
              <span
                className={`inline-block w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${up ? "bg-[#2E5C46]" : "bg-[#A87A4A]"}`}
                aria-hidden
              />
              <div className="flex-1">
                <p className="font-serif">
                  {up ? "Rose to" : "Settled to"}{" "}
                  <strong className="capitalize">{r.to_tier_key}</strong>
                  {r.from_tier_key && (
                    <span className="text-[#5C6B6B] text-xs italic ml-1">
                      from <span className="capitalize">{r.from_tier_key}</span>
                    </span>
                  )}
                </p>
                <p className="text-xs text-[#5C6B6B]">
                  {new Date(r.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                  {" · "}basis {fmt(r.basis_at_change)}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}



// Inline SVG sparkline — patronage (teal) and off-site (gold) stacked
// bars per month, with a baseline rule. No external chart lib.
function RevenueSparkline({ series }) {
  const W = 600, H = 80, pad = 6;
  const max = Math.max(1, ...series.map((d) => d.revenue));
  const barW = (W - pad * 2) / series.length - 4;
  const fmt = (n) => `$${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  return (
    <div className="mt-2 overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H + 22}`}
        preserveAspectRatio="none"
        style={{ width: "100%", height: 110 }}
        role="img"
        aria-label="Monthly Birthright revenue sparkline"
      >
        {/* Baseline */}
        <line x1={pad} x2={W - pad} y1={H} y2={H} stroke="#E5E1D8" strokeWidth="1" />
        {series.map((d, i) => {
          const x = pad + i * (barW + 4);
          const totalH = (d.revenue / max) * (H - 4);
          const patronageH = (d.patronage / max) * (H - 4);
          const offsiteH = (d.off_site / max) * (H - 4);
          const labelEvery = Math.ceil(series.length / 6);
          const showLabel = i % labelEvery === 0 || i === series.length - 1;
          return (
            <g key={d.month}>
              <title>{`${d.month}: ${fmt(d.revenue)} (patronage ${fmt(d.patronage)} · off-site ${fmt(d.off_site)})`}</title>
              {/* Off-site (gold) on top */}
              {offsiteH > 0 && (
                <rect
                  x={x} y={H - totalH}
                  width={barW} height={offsiteH}
                  fill="#A87A4A"
                />
              )}
              {/* Patronage (teal) at base */}
              {patronageH > 0 && (
                <rect
                  x={x} y={H - patronageH}
                  width={barW} height={patronageH}
                  fill="#2C4E5A"
                />
              )}
              {totalH === 0 && (
                <rect
                  x={x} y={H - 2}
                  width={barW} height={2}
                  fill="#E5E1D8"
                />
              )}
              {showLabel && (
                <text
                  x={x + barW / 2}
                  y={H + 14}
                  textAnchor="middle"
                  fontSize="9"
                  fill="#5C6B6B"
                  fontFamily="ui-monospace, monospace"
                >
                  {d.month.slice(5)}/{d.month.slice(2, 4)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <div className="flex items-center gap-4 text-[10px] text-[#5C6B6B] mt-1">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block w-2 h-2" style={{ background: "#2C4E5A" }} />
          On-site patronage
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block w-2 h-2" style={{ background: "#A87A4A" }} />
          Off-site (self-reported)
        </span>
      </div>
    </div>
  );
}

export default function ArtistStudio() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [space, setSpace] = useState(null);
  const [works, setWorks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingSpace, setSavingSpace] = useState(false);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    if (!user) { navigate("/sign-in"); return; }
    refresh();
  }, []);

  const refresh = async () => {
    setLoading(true);
    try {
      const [s, w] = await Promise.all([
        api.get("/gallery/me/space"),
        api.get("/gallery/me/works"),
      ]);
      setSpace(s.data);
      setWorks(w.data || []);
    } catch (err) {
      if (err?.response?.status === 403) {
        toast.error("You need an approved Artist partner profile first.");
        navigate("/partner/apply");
      } else { toast.error("Couldn't load gallery"); }
    } finally { setLoading(false); }
  };

  const saveSpace = async () => {
    setSavingSpace(true);
    try {
      const { id, user_id, created_at, updated_at, ...patch } = space || {};
      const r = await api.put("/gallery/me/space", patch);
      setSpace(r.data);
      toast.success("Gallery space saved");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSavingSpace(false);
    }
  };

  const deleteWork = async (id) => {
    if (!window.confirm("Remove this work?")) return;
    try { await api.delete(`/gallery/me/works/${id}`); refresh(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Delete failed"); }
  };

  if (loading || !space) return <div className="container-page py-12">Loading…</div>;

  return (
    <div className="container-page py-12" data-testid="artist-studio-page">
      <span className="label">Artist · Your gallery</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Palette size={26} strokeWidth={1.2} /> Manage your gallery space
      </h1>
      <div className="divider-flame" />

      {/* Tier card — your current partnership tier, basis, runway */}
      <ArtistTierCard />

      {/* Gallery space settings */}
      <section className="card p-6 mt-6 max-w-3xl" data-testid="artist-space-form">
        <h2 className="font-serif text-xl">Gallery space</h2>
        <p className="text-xs text-[#5C6B6B] mt-1">How your room feels. Optional fields are exactly that — leave anything blank.</p>
        <div className="space-y-3 mt-4 text-sm">
          <label className="block">
            <span className="block label !mt-0 !mb-1">Artist statement</span>
            <textarea value={space.statement || ""} onChange={(e) => setSpace({ ...space, statement: e.target.value })} className="input-field w-full" rows={4} data-testid="artist-statement-input" />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="block label !mt-0 !mb-1">Layout</span>
              <select value={space.layout || "single-wall"} onChange={(e) => setSpace({ ...space, layout: e.target.value })} className="input-field w-full" data-testid="artist-layout-select">
                {LAYOUTS.map((l) => <option key={l} value={l}>{l.replace("-", " ")}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="block label !mt-0 !mb-1">Accent color</span>
              <select value={space.accent_color || "flame"} onChange={(e) => setSpace({ ...space, accent_color: e.target.value })} className="input-field w-full" data-testid="artist-accent-select">
                {ACCENTS.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </label>
          </div>
          {[
            ["hero_image_url", "Hero image URL"],
            ["studio_photo_url", "Photo of you in studio"],
            ["audio_intro_url", "Audio intro URL (~30s mp3)"],
            ["video_reel_url", "Performance reel URL"],
            ["newsletter_signup_url", "Newsletter signup URL"],
            ["own_gallery_url", "Your own gallery URL"],
          ].map(([k, label]) => (
            <label key={k} className="block">
              <span className="block label !mt-0 !mb-1">{label}</span>
              <input value={space[k] || ""} onChange={(e) => setSpace({ ...space, [k]: e.target.value })} className="input-field w-full" data-testid={`artist-${k}-input`} />
            </label>
          ))}
          <label className="block">
            <span className="block label !mt-0 !mb-1">Open studio (dates, address, RSVP)</span>
            <textarea value={space.open_studio_text || ""} onChange={(e) => setSpace({ ...space, open_studio_text: e.target.value })} className="input-field w-full" rows={3} data-testid="artist-open-studio-input" />
          </label>
          <label className="block">
            <span className="block label !mt-0 !mb-1">Performance schedule (one per line)</span>
            <textarea value={space.performance_schedule || ""} onChange={(e) => setSpace({ ...space, performance_schedule: e.target.value })} className="input-field w-full" rows={3} data-testid="artist-perf-input" />
          </label>
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={!!space.commissions_open} onChange={(e) => setSpace({ ...space, commissions_open: e.target.checked })} data-testid="artist-commissions-toggle" />
            Accept commission inquiries
          </label>
          {space.commissions_open && (
            <label className="block">
              <span className="block label !mt-0 !mb-1">Commission inquiry intro (optional)</span>
              <textarea value={space.commission_inquiry_text || ""} onChange={(e) => setSpace({ ...space, commission_inquiry_text: e.target.value })} className="input-field w-full" rows={3} data-testid="artist-commission-text-input" />
            </label>
          )}
          <details className="text-xs text-[#5C6B6B]">
            <summary className="cursor-pointer">Advanced (rare)</summary>
            <label className="inline-flex items-center gap-2 mt-2">
              <input type="checkbox" checked={!!space.donate_proceeds_to_foundation} onChange={(e) => setSpace({ ...space, donate_proceeds_to_foundation: e.target.checked })} data-testid="artist-donate-toggle" />
              Donate all my proceeds back to the foundation
            </label>
          </details>
        </div>
        <button onClick={saveSpace} disabled={savingSpace} className="btn-primary text-sm mt-4 inline-flex items-center gap-2" data-testid="artist-save-space-btn">
          <Save size={14} /> {savingSpace ? "Saving…" : "Save"}
        </button>
      </section>

      {/* Works */}
      <section className="mt-8 max-w-3xl" data-testid="artist-works-section">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-xl">Your works ({works.length})</h2>
          <button onClick={() => setShowNew(true)} className="btn-primary text-sm inline-flex items-center gap-1" data-testid="artist-add-work-btn">
            <Plus size={14} /> Add a work
          </button>
        </div>
        {showNew && <NewWorkForm onClose={() => setShowNew(false)} onCreated={() => { setShowNew(false); refresh(); }} />}
        {works.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] italic mt-3">No works yet. Click &ldquo;Add a work&rdquo; to publish your first piece.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
            {works.map((w) => (
              <div key={w.id} className="card overflow-hidden" data-testid={`artist-work-row-${w.id}`}>
                <div className="aspect-square bg-[#F4F1EA]"><img src={w.image_url} alt={w.name} className="w-full h-full object-cover" /></div>
                <div className="p-3 text-sm">
                  <p className="font-serif">{w.name}</p>
                  <p className="text-xs text-[#5C6B6B]">${w.price.toFixed(2)} · {w.availability}</p>
                  <button onClick={() => deleteWork(w.id)} className="text-[#9E3C3C] text-xs hover:underline mt-1" data-testid={`artist-delete-work-${w.id}`}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function NewWorkForm({ onClose, onCreated }) {
  const [f, setF] = useState({
    name: "", description: "", list_price: 0,
    image_url: "", medium: "", dimensions: "", year: 2026, edition: "1/1",
    availability: "available", list_price_matches_own_gallery: false,
  });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!f.list_price_matches_own_gallery) {
      toast.error("Please confirm your list price matches your own gallery.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/gallery/me/works", { ...f, list_price: parseFloat(f.list_price) });
      toast.success("Work published");
      onCreated();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Publish failed");
    } finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit} className="card p-4 mt-3 space-y-2 text-sm" data-testid="artist-new-work-form">
      <input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Title" required className="input-field" data-testid="new-work-name" />
      <textarea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="Short description (≥10 chars)" required minLength={10} className="input-field" rows={3} data-testid="new-work-desc" />
      <div className="grid grid-cols-2 gap-2">
        <input value={f.list_price} onChange={(e) => setF({ ...f, list_price: e.target.value })} type="number" step="0.01" placeholder="List price ($)" className="input-field" required data-testid="new-work-price" />
        <input value={f.year} onChange={(e) => setF({ ...f, year: parseInt(e.target.value, 10) || 0 })} type="number" placeholder="Year" className="input-field" data-testid="new-work-year" />
        <input value={f.medium} onChange={(e) => setF({ ...f, medium: e.target.value })} placeholder="Medium" className="input-field" data-testid="new-work-medium" />
        <input value={f.dimensions} onChange={(e) => setF({ ...f, dimensions: e.target.value })} placeholder="Dimensions" className="input-field" data-testid="new-work-dim" />
        <input value={f.edition} onChange={(e) => setF({ ...f, edition: e.target.value })} placeholder="Edition (1/1, 12/100)" className="input-field" data-testid="new-work-edition" />
        <select value={f.availability} onChange={(e) => setF({ ...f, availability: e.target.value })} className="input-field" data-testid="new-work-avail">
          <option value="available">Available</option>
          <option value="not_for_sale">Not for sale</option>
          <option value="sold">Sold</option>
        </select>
      </div>
      <input value={f.image_url} onChange={(e) => setF({ ...f, image_url: e.target.value })} placeholder="Image URL" required className="input-field" data-testid="new-work-image" />
      <label className="flex items-start gap-2 text-xs">
        <input type="checkbox" checked={f.list_price_matches_own_gallery} onChange={(e) => setF({ ...f, list_price_matches_own_gallery: e.target.checked })} data-testid="new-work-attest" />
        <span>I attest this list price matches the price on my own gallery / website. (Birthright adds a 20% foundation markup on top at checkout.)</span>
      </label>
      <div className="flex gap-2">
        <button disabled={busy} className="btn-primary text-sm" data-testid="new-work-submit">{busy ? "Publishing…" : "Publish"}</button>
        <button type="button" onClick={onClose} className="btn-outline text-sm">Cancel</button>
      </div>
    </form>
  );
}
