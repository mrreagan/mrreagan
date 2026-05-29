import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, Coins, FlaskConical, Heart, ShoppingBag, Trash2, ArrowRight, AlertTriangle } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const CATEGORIES = [
  { v: "cap", label: "Cap / Beanie" },
  { v: "tee", label: "T-shirt" },
  { v: "hoodie", label: "Hoodie" },
  { v: "sweatshirt", label: "Sweatshirt" },
  { v: "mug", label: "Mug" },
  { v: "water_bottle", label: "Water bottle" },
  { v: "tote", label: "Tote" },
  { v: "poster", label: "Poster / Print" },
  { v: "notebook", label: "Notebook" },
  { v: "journal", label: "Journal" },
];

const AUDIENCES = [
  { v: "founder_collection", label: "Founder Collection", hint: "Identity-wear with quiet, personal copy" },
  { v: "general_equip", label: "General Equip", hint: "Useful daily objects with calm, confident copy" },
];

export default function AdminStudio() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [brief, setBrief] = useState("");
  const [category, setCategory] = useState("cap");
  const [audiences, setAudiences] = useState(["founder_collection", "general_equip"]);
  const [imageCount, setImageCount] = useState(2);
  const [estimate, setEstimate] = useState(null);
  const [estimating, setEstimating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [drafts, setDrafts] = useState([]);

  useEffect(() => {
    if (!user || user.role !== "admin") {
      navigate("/dashboard", { replace: true });
      return;
    }
    refreshDrafts();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const refreshDrafts = async () => {
    try {
      const r = await api.get("/studio/drafts");
      setDrafts(r.data);
    } catch {
      // silent
    }
  };

  const canEstimate = brief.trim().length >= 10 && audiences.length > 0;

  const toggleAudience = (v) => {
    setAudiences((a) =>
      a.includes(v) ? (a.length > 1 ? a.filter((x) => x !== v) : a) : [...a, v]
    );
    setEstimate(null);
  };

  const runEstimate = async () => {
    if (!canEstimate) return;
    setEstimating(true);
    setEstimate(null);
    try {
      const r = await api.post("/studio/estimate", {
        brief: brief.trim(),
        category,
        audiences,
        image_count: imageCount,
      });
      setEstimate(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't estimate cost");
    } finally {
      setEstimating(false);
    }
  };

  const runGenerate = async () => {
    if (!estimate) {
      toast.message("Get a cost estimate first");
      return;
    }
    if (estimate.insufficient_funds) {
      toast.error("Top up your AI Wallet first");
      return;
    }
    setGenerating(true);
    try {
      const r = await api.post("/studio/generate", {
        brief: brief.trim(),
        category,
        audiences,
        image_count: imageCount,
      });
      toast.success("Draft created");
      setEstimate(null);
      setBrief("");
      refreshDrafts();
      // Scroll to drafts section
      setTimeout(() => {
        document.getElementById("studio-drafts")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 200);
      return r.data;
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const significantSpend = estimate?.significant_portion_of_balance;
  const insufficient = estimate?.insufficient_funds;

  return (
    <div className="container-page py-12" data-testid="admin-studio-page">
      <span className="label">Admin · AI Studio</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <FlaskConical size={26} strokeWidth={1.2} /> AI Studio
      </h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Dream a product. Studio gives you a real-dollar cost estimate up front,
        generates hero images and copy variants on confirmation, and saves the
        result as a draft you can review before publishing.
      </p>

      <div className="rounded-2xl border-2 border-[#C9A961] bg-[#FFF8E1] p-5 mt-6 max-w-3xl" data-testid="studio-honesty">
        <p className="text-[10px] uppercase tracking-wider text-[#8B7128] font-semibold">
          Pricing honesty — {PRICE_MULTIPLIER_HINT}× passthrough
        </p>
        <p className="font-serif text-lg mt-1 leading-snug">
          You see the dollar cost — and what supports the foundation — before you spend it.
        </p>
        <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">
          We're the only non-developer creative AI studio that shows you the exact dollar cost
          {" "}before generation. The +50% built into every call directly funds the foundation.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        {/* ====== Composer ====== */}
        <section className="lg:col-span-2 space-y-5" data-testid="studio-composer">
          <div className="card p-6">
            <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
              Brief
              <textarea
                value={brief}
                onChange={(e) => { setBrief(e.target.value); setEstimate(null); }}
                placeholder="e.g. a navy beanie with the softened-shield icon and the phrase 'Built to stay,' restrained and unfussy"
                className="input-field mt-2 min-h-[120px] !font-serif !text-base"
                data-testid="studio-brief"
              />
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
                Category
                <select
                  value={category}
                  onChange={(e) => { setCategory(e.target.value); setEstimate(null); }}
                  className="input-field mt-2"
                  data-testid="studio-category"
                >
                  {CATEGORIES.map((c) => <option key={c.v} value={c.v}>{c.label}</option>)}
                </select>
              </label>
              <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
                Images to generate
                <select
                  value={imageCount}
                  onChange={(e) => { setImageCount(parseInt(e.target.value, 10)); setEstimate(null); }}
                  className="input-field mt-2"
                  data-testid="studio-image-count"
                >
                  <option value={1}>1 image</option>
                  <option value={2}>2 images</option>
                  <option value={3}>3 images</option>
                </select>
              </label>
            </div>

            <div className="mt-5">
              <p className="text-xs uppercase tracking-wider text-[#5C6B6B] mb-2">Copy variants for</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {AUDIENCES.map((a) => (
                  <button
                    key={a.v}
                    type="button"
                    onClick={() => toggleAudience(a.v)}
                    className={`text-left rounded-lg border p-3 transition ${
                      audiences.includes(a.v)
                        ? "border-[#476B6B] bg-[#F4F1EA]"
                        : "border-[#E5E1D8] bg-white hover:border-[#5C6B6B]"
                    }`}
                    data-testid={`studio-audience-${a.v}`}
                  >
                    <span className="font-serif text-base inline-flex items-center gap-2">
                      {a.v === "founder_collection" ? <Heart size={14} strokeWidth={1.5} className="text-[#C9A961]" /> : <ShoppingBag size={14} strokeWidth={1.5} className="text-[#476B6B]" />}
                      {a.label}
                      {audiences.includes(a.v) && <span className="text-[10px] uppercase tracking-wider text-[#476B6B] ml-1">✓ selected</span>}
                    </span>
                    <p className="text-xs text-[#5C6B6B] mt-1">{a.hint}</p>
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-[#5C6B6B] mt-2">
                Choose one for focused copy, or both to see side-by-side variants.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <button
              type="button"
              onClick={runEstimate}
              disabled={!canEstimate || estimating}
              className="btn-outline text-sm inline-flex items-center gap-2"
              data-testid="studio-estimate-btn"
            >
              <Coins size={14} strokeWidth={1.6} /> {estimating ? "Estimating…" : "Estimate cost"}
            </button>
            {estimate && (
              <CostPill estimate={estimate} />
            )}
          </div>

          {/* Cost-aware confirm UI */}
          {estimate && (
            <div
              className={`rounded-xl border-2 p-4 ${
                insufficient
                  ? "border-[#9E3C3C] bg-[#FBEAEA]"
                  : significantSpend
                  ? "border-[#C9A961] bg-[#FFF8E1]"
                  : "border-[#E5E1D8] bg-white"
              }`}
              data-testid="studio-confirm-card"
            >
              {insufficient ? (
                <>
                  <p className="font-serif text-lg inline-flex items-center gap-2">
                    <AlertTriangle size={16} className="text-[#9E3C3C]" strokeWidth={1.5} /> Not enough in your wallet
                  </p>
                  <p className="text-sm text-[#5C6B6B] mt-1">
                    This prompt costs <strong>${estimate.estimated_cost_usd.toFixed(4)}</strong>, your balance is
                    {" "}<strong>${estimate.your_balance_usd.toFixed(2)}</strong>. Top up to continue.
                  </p>
                  <Link to="/dashboard/ai-wallet" className="btn-primary text-xs mt-3 inline-flex" data-testid="studio-topup">
                    Top up the AI Wallet →
                  </Link>
                </>
              ) : significantSpend ? (
                <>
                  <p className="font-serif text-lg">Confirm — this is a meaningful slice of your balance.</p>
                  <p className="text-sm text-[#5C6B6B] mt-1">
                    Spending <strong>${estimate.estimated_cost_usd.toFixed(4)}</strong> would leave
                    {" "}<strong>${estimate.after_this_prompt_usd.toFixed(2)}</strong>. Juice worth the squeeze?
                  </p>
                  <div className="flex gap-2 mt-3">
                    <button onClick={runGenerate} disabled={generating} className="btn-primary text-xs" data-testid="studio-confirm-generate">
                      {generating ? "Generating…" : `Yes — generate for $${estimate.estimated_cost_usd.toFixed(4)}`}
                    </button>
                    <Link to="/dashboard/ai-wallet" className="btn-outline text-xs">Top up first</Link>
                  </div>
                </>
              ) : (
                <>
                  <p className="font-serif text-lg">Ready to generate.</p>
                  <p className="text-sm text-[#5C6B6B] mt-1">
                    Spending <strong>${estimate.estimated_cost_usd.toFixed(4)}</strong> — of which
                    {" "}<strong>${estimate.foundation_portion_usd.toFixed(4)}</strong> supports the foundation.
                    {" "}You'll have <strong>${estimate.after_this_prompt_usd.toFixed(2)}</strong> after.
                  </p>
                  <button onClick={runGenerate} disabled={generating} className="btn-primary text-sm mt-3" data-testid="studio-confirm-generate">
                    {generating ? "Generating… (takes ~30s)" : "Generate"}
                  </button>
                </>
              )}
            </div>
          )}
        </section>

        {/* ====== Sidebar ====== */}
        <aside className="space-y-4">
          <div className="card p-5">
            <p className="label !mt-0">House style</p>
            <ul className="text-xs text-[#5C6B6B] space-y-2 mt-3 leading-relaxed">
              <li>· Quiet, grounded, editorial — never loud.</li>
              <li>· Cream / navy / gold palette dominates.</li>
              <li>· No exclamation points. No "AMAZING."</li>
              <li>· Reaches for daily life, not the spotlight.</li>
            </ul>
          </div>
          <div className="card p-5 bg-[#0F2424] text-[#FAF8F5]" data-testid="studio-vendor-cta">
            <p className="label !mt-0 !text-[#C9A961]">For partners</p>
            <p className="font-serif text-lg mt-2 leading-snug !text-[#FAF8F5]">
              When vendor mode opens, you'll get the same Studio for your own products.
            </p>
            <p className="text-xs text-[#FAF8F5]/70 mt-2 leading-relaxed">
              Dream concepts, see live dollar costs before generating, list on Birthright with our reach — or refer customers to your own store and earn referral credit.
            </p>
          </div>
        </aside>
      </div>

      {/* ====== Drafts list ====== */}
      <section id="studio-drafts" className="mt-12" data-testid="studio-drafts">
        <h2 className="font-serif text-2xl mb-3">Drafts awaiting review</h2>
        {drafts.length === 0 ? (
          <p className="text-sm text-[#5C6B6B]">No drafts yet. Make one above.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {drafts.map((d) => <DraftCard key={d.id} draft={d} onChange={refreshDrafts} />)}
          </div>
        )}
      </section>
    </div>
  );
}

function CostPill({ estimate }) {
  return (
    <span
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F4F1EA] border border-[#E5E1D8] text-xs"
      data-testid="studio-cost-pill"
      title={`${estimate.multiplier}× passthrough — ${estimate.foundation_markup_pct}% supports the foundation`}
    >
      <Sparkles size={11} strokeWidth={1.8} className="text-[#C9A961]" />
      <span><strong>${estimate.estimated_cost_usd.toFixed(4)}</strong> to generate</span>
      <span className="text-[#5C6B6B]">·</span>
      <span className="text-[#5C6B6B]">${estimate.foundation_portion_usd.toFixed(4)} supports the foundation</span>
    </span>
  );
}

function DraftCard({ draft, onChange }) {
  const [price, setPrice] = useState(0);
  const [publishing, setPublishing] = useState(false);
  const [discarding, setDiscarding] = useState(false);

  const setProductPrice = async (newPrice) => {
    try {
      await api.put(`/products/${draft.id}`, { price: newPrice });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't set price");
      throw err;
    }
  };

  const publish = async () => {
    if (!price || price <= 0) {
      toast.error("Set a price before publishing");
      return;
    }
    setPublishing(true);
    try {
      await setProductPrice(price);
      await api.post(`/studio/drafts/${draft.id}/publish`);
      toast.success(`Published: ${draft.name}`);
      onChange?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Publish failed");
    } finally {
      setPublishing(false);
    }
  };

  const discard = async () => {
    if (!window.confirm("Discard this draft? Images will be deleted.")) return;
    setDiscarding(true);
    try {
      await api.delete(`/studio/drafts/${draft.id}`);
      toast.success("Draft discarded");
      onChange?.();
    } catch (err) {
      toast.error("Discard failed");
    } finally {
      setDiscarding(false);
    }
  };

  return (
    <div className="card overflow-hidden flex flex-col" data-testid={`draft-card-${draft.id}`}>
      <div className="aspect-square bg-[#F4F1EA] flex items-center justify-center overflow-hidden">
        <img src={draft.image_url} alt={draft.name} className="w-full h-full object-contain p-2" />
      </div>
      <div className="p-4 flex flex-col gap-2 flex-1">
        <span className="label !mt-0 !text-[#C9A961]">{draft.category}</span>
        <p className="font-serif text-lg leading-tight">{draft.name}</p>
        <p className="text-xs text-[#5C6B6B] line-clamp-4 leading-relaxed">{draft.description}</p>
        {draft.studio_copy_variants && Object.keys(draft.studio_copy_variants).length > 1 && (
          <details className="mt-1">
            <summary className="text-[10px] uppercase tracking-wider text-[#476B6B] cursor-pointer">
              See {Object.keys(draft.studio_copy_variants).length} copy variants
            </summary>
            <div className="mt-2 space-y-2 text-xs">
              {Object.entries(draft.studio_copy_variants).map(([aud, v]) => (
                <div key={aud} className="rounded border border-[#E5E1D8] p-2">
                  <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">{aud}</p>
                  <p className="font-medium mt-1">{v.name}</p>
                  <p className="text-[#5C6B6B] mt-1 leading-relaxed">{v.description}</p>
                </div>
              ))}
            </div>
          </details>
        )}
        <div className="mt-3 flex items-center gap-2">
          <label className="text-[10px] uppercase tracking-wider text-[#5C6B6B] inline-flex items-center gap-1">
            $
            <input
              type="number" min="1" step="0.01"
              value={price || ""}
              onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
              placeholder="price"
              className="input-field !py-1 !px-2 text-xs w-20"
              data-testid={`draft-price-${draft.id}`}
            />
          </label>
          <button onClick={publish} disabled={publishing || !price} className="btn-primary text-xs flex-1 inline-flex items-center justify-center gap-1" data-testid={`draft-publish-${draft.id}`}>
            {publishing ? "Publishing…" : <>Publish <ArrowRight size={11} strokeWidth={1.8} /></>}
          </button>
          <button onClick={discard} disabled={discarding} className="btn-outline !text-[#9E3C3C] !border-[#9E3C3C] text-xs px-2 py-1.5" aria-label="Discard" data-testid={`draft-discard-${draft.id}`}>
            <Trash2 size={12} strokeWidth={1.5} />
          </button>
        </div>
      </div>
    </div>
  );
}

const PRICE_MULTIPLIER_HINT = "1.50";
