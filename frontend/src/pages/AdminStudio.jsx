import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, Coins, FlaskConical, Heart, ShoppingBag, Trash2, ArrowRight, AlertTriangle, Package, RefreshCw, Check } from "lucide-react";
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
              Dream concepts, see live dollar costs before generating, list on Birthright with our reach — or refer customers to your own store and send a referral commission back to the foundation.
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
  const [fulfilling, setFulfilling] = useState(false);
  const [showLulu, setShowLulu] = useState(false);
  const [rerolling, setRerolling] = useState(false);
  const [showGallery, setShowGallery] = useState(false);
  const [settingPrimary, setSettingPrimary] = useState(null); // url being promoted

  const printfulSupported = ["cap", "tee", "hoodie", "mug"].includes(draft.category);
  const luluSupported = ["journal", "notebook"].includes(draft.category);
  const onPrintful = !!draft.printful_sync_product_id;
  const onLulu = draft.fulfillable_via === "lulu";
  const gallery = draft.image_gallery || [];
  const hasGallery = gallery.length > 1;

  const reroll = async () => {
    if (!window.confirm("Generate 2 new cover variations? This spends AI credits (~$0.12).")) return;
    setRerolling(true);
    try {
      const r = await api.post(`/studio/drafts/${draft.id}/reroll-cover?count=2`);
      toast.success(`${r.data.new_image_urls.length} new covers generated — pick one to promote.`);
      setShowGallery(true);
      onChange?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Re-roll failed");
    } finally {
      setRerolling(false);
    }
  };

  const setPrimary = async (imageUrl) => {
    setSettingPrimary(imageUrl);
    try {
      await api.post(
        `/studio/drafts/${draft.id}/set-primary-image`,
        null,
        { params: { image_url: imageUrl } },
      );
      toast.success("Cover updated");
      if (onLulu && luluSupported) {
        toast.info("Heads-up: this draft is linked to Lulu — regenerate the cover PDF in the Lulu form below to push the new image to fulfillment.");
      }
      onChange?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't promote that image");
    } finally {
      setSettingPrimary(null);
    }
  };

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

  const makeFulfillable = async () => {
    if (!window.confirm(`Push this ${draft.category} to Printful as a Sync Product? Retail price will be set automatically (2× base cost, rounded to $.95).`)) return;
    setFulfilling(true);
    try {
      const r = await api.post("/printful/make-fulfillable", {
        product_id: draft.id,
        markup_multiplier: 2.0,
      });
      toast.success(`Fulfillable on Printful · base $${r.data.base_cost_usd?.toFixed(2)} → retail $${r.data.retail_price_usd?.toFixed(2)}`);
      setPrice(r.data.retail_price_usd);
      onChange?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Printful linking failed");
    } finally {
      setFulfilling(false);
    }
  };

  const detachFromPrintful = async () => {
    if (!window.confirm("Unlink this draft from Printful? The sync product there will be deleted.")) return;
    setFulfilling(true);
    try {
      await api.delete(`/printful/sync-products/${draft.id}`);
      toast.success("Unlinked from Printful");
      onChange?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Unlink failed");
    } finally {
      setFulfilling(false);
    }
  };

  const detachFromLulu = async () => {
    if (!window.confirm("Unlink this journal from Lulu?")) return;
    setFulfilling(true);
    try {
      await api.delete(`/lulu/fulfillment/${draft.id}`);
      toast.success("Unlinked from Lulu");
      onChange?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Unlink failed");
    } finally {
      setFulfilling(false);
    }
  };

  return (
    <div className="card overflow-hidden flex flex-col" data-testid={`draft-card-${draft.id}`}>
      <div className="aspect-square bg-[#F4F1EA] flex items-center justify-center overflow-hidden relative">
        <img src={draft.image_url} alt={draft.name} className="w-full h-full object-contain p-2" />
        {hasGallery && (
          <button
            onClick={() => setShowGallery(!showGallery)}
            className="absolute bottom-2 right-2 inline-flex items-center gap-1 bg-white/95 backdrop-blur text-[10px] uppercase tracking-wider font-medium text-[#476B6B] border border-[#E5E1D8] rounded-full px-2 py-1 hover:border-[#476B6B] transition"
            data-testid={`draft-gallery-toggle-${draft.id}`}
          >
            {showGallery ? "Hide" : `${gallery.length} options`}
          </button>
        )}
      </div>
      {showGallery && hasGallery && (
        <div className="px-4 py-3 border-b border-[#E5E1D8] bg-[#FAF8F5]" data-testid={`draft-gallery-${draft.id}`}>
          <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-2">Pick the cover</p>
          <div className="grid grid-cols-4 gap-2">
            {gallery.map((url) => {
              const isActive = url === draft.image_url;
              const isBusy = settingPrimary === url;
              return (
                <button
                  key={url}
                  onClick={() => !isActive && setPrimary(url)}
                  disabled={isActive || isBusy}
                  className={`relative aspect-square rounded overflow-hidden border-2 transition ${
                    isActive ? "border-[#476B6B] ring-2 ring-[#476B6B]/30" : "border-[#E5E1D8] hover:border-[#C9A961]"
                  }`}
                  data-testid={`draft-gallery-pick-${draft.id}-${url.split("/").pop()}`}
                  title={isActive ? "Currently the cover" : "Set as cover"}
                >
                  <img src={url} alt="" className="w-full h-full object-cover" />
                  {isActive && (
                    <div className="absolute inset-0 bg-[#476B6B]/20 flex items-center justify-center">
                      <Check size={14} strokeWidth={2.2} className="text-white drop-shadow" />
                    </div>
                  )}
                  {isBusy && (
                    <div className="absolute inset-0 bg-white/70 flex items-center justify-center text-[10px] text-[#476B6B]">…</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
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
          <button
            onClick={reroll}
            disabled={rerolling}
            className="btn-outline text-xs px-2 py-1.5 inline-flex items-center gap-1 !border-[#C9A961] !text-[#8B7128] hover:!bg-[#FFF8E1]"
            title="Generate 2 new cover variations (~$0.12)"
            data-testid={`draft-reroll-${draft.id}`}
          >
            <RefreshCw size={12} strokeWidth={1.5} className={rerolling ? "animate-spin" : ""} />
            {rerolling ? "…" : "Re-roll"}
          </button>
          <button onClick={discard} disabled={discarding} className="btn-outline !text-[#9E3C3C] !border-[#9E3C3C] text-xs px-2 py-1.5" aria-label="Discard" data-testid={`draft-discard-${draft.id}`}>
            <Trash2 size={12} strokeWidth={1.5} />
          </button>
        </div>

        {/* Fulfillment block (Printful for apparel, Lulu for paper goods) */}
        <div className="mt-2 pt-2 border-t border-dashed border-[#E5E1D8]" data-testid={`draft-fulfillment-block-${draft.id}`}>
          {onPrintful ? (
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 text-[#01784E]" data-testid={`draft-printful-linked-${draft.id}`}>
                <Package size={12} strokeWidth={1.8} /> Fulfillable on Printful
              </span>
              <button onClick={detachFromPrintful} disabled={fulfilling} className="text-[10px] uppercase tracking-wider text-[#9E3C3C] hover:underline" data-testid={`draft-printful-detach-${draft.id}`}>
                {fulfilling ? "…" : "unlink"}
              </button>
            </div>
          ) : onLulu ? (
            <div className="flex items-center justify-between gap-2 text-xs" data-testid={`draft-lulu-linked-${draft.id}`}>
              <span className="inline-flex items-center gap-1.5 text-[#01784E]">
                <Package size={12} strokeWidth={1.8} /> Fulfillable on Lulu ({draft.lulu_env})
              </span>
              <button onClick={detachFromLulu} disabled={fulfilling} className="text-[10px] uppercase tracking-wider text-[#9E3C3C] hover:underline" data-testid={`draft-lulu-detach-${draft.id}`}>
                {fulfilling ? "…" : "unlink"}
              </button>
            </div>
          ) : printfulSupported ? (
            <button onClick={makeFulfillable} disabled={fulfilling} className="w-full inline-flex items-center justify-center gap-1.5 text-[11px] uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] border border-[#476B6B] rounded-md py-1.5 transition" data-testid={`draft-printful-link-${draft.id}`}>
              <Package size={12} strokeWidth={1.8} /> {fulfilling ? "Linking to Printful…" : "Make fulfillable on Printful"}
            </button>
          ) : luluSupported ? (
            <LuluFulfillmentForm draft={draft} show={showLulu} setShow={setShowLulu} onLinked={onChange} />
          ) : (
            <p className="text-[10px] text-[#5C6B6B] italic">
              POD not yet supported for category "{draft.category}".
            </p>
          )}
          {draft.printful_label && onPrintful && (
            <p className="text-[10px] text-[#5C6B6B] mt-1 leading-snug">
              {draft.printful_label} · base ${draft.printful_base_cost_usd?.toFixed(2)}
            </p>
          )}
          {onLulu && (
            <p className="text-[10px] text-[#5C6B6B] mt-1 leading-snug">
              Lulu · {draft.lulu_page_count} pages · base ${draft.lulu_base_cost_usd?.toFixed(2)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

const PRICE_MULTIPLIER_HINT = "1.50";

function LuluFulfillmentForm({ draft, show, setShow, onLinked }) {
  const [presets, setPresets] = useState([]);
  const [presetKey, setPresetKey] = useState("");
  const [podId, setPodId] = useState("");
  const [pageCount, setPageCount] = useState(draft.lulu_page_count_suggested || 144);
  const [pagesAutoInferred, setPagesAutoInferred] = useState(!!draft.lulu_page_count_suggested);
  const [interiorUrl, setInteriorUrl] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [autoGenerating, setAutoGenerating] = useState(false);
  const [interiorStyles, setInteriorStyles] = useState([]);
  const [interiorStyle, setInteriorStyle] = useState(draft.interior_style || "lined");
  const [styleAutoInferred, setStyleAutoInferred] = useState(!!draft.interior_style);

  useEffect(() => {
    if (show && presets.length === 0) {
      api.get("/lulu/presets").then((r) => {
        const filtered = r.data.filter((p) => p.applies_to.includes(draft.category));
        setPresets(filtered);
        if (filtered.length && !presetKey) {
          setPresetKey(filtered[0].key);
          setPodId(filtered[0].pod_package_id);
          // Use AI suggestion if present; otherwise fall back to preset default
          if (!draft.lulu_page_count_suggested) {
            setPageCount(filtered[0].default_page_count);
          }
        }
      }).catch(() => {});
      api.get("/lulu/interior-styles").then((r) => setInteriorStyles(r.data)).catch(() => {});
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [show]);

  const autoGenerate = async () => {
    setAutoGenerating(true);
    try {
      const r = await api.post("/lulu/auto-generate-pdfs", {
        product_id: draft.id,
        page_count: parseInt(pageCount, 10),
        interior_style: interiorStyle,
      });
      setInteriorUrl(r.data.interior_pdf_url);
      setCoverUrl(r.data.cover_pdf_url);
      setInteriorStyle(r.data.interior_style);
      setPageCount(r.data.page_count);
      setStyleAutoInferred(false); // user has now seen + confirmed the style
      setPagesAutoInferred(false);
      toast.success(`PDFs generated · ${r.data.page_count} pp · style "${r.data.interior_style}"`);
      setPreview(null);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Auto-PDF failed");
    } finally { setAutoGenerating(false); }
  };

  const choosePreset = (k) => {
    const p = presets.find((x) => x.key === k);
    if (!p) return;
    setPresetKey(k);
    setPodId(p.pod_package_id);
    // Only change page count if it wasn't AI-inferred (user explicitly picked a preset)
    if (!pagesAutoInferred) {
      setPageCount(p.default_page_count);
    }
    setPreview(null);
  };

  const runPreview = async () => {
    if (!podId || !pageCount) return;
    setBusy(true);
    setPreview(null);
    try {
      const r = await api.post("/lulu/cost-preview", { pod_package_id: podId, page_count: parseInt(pageCount, 10), quantity: 1 });
      setPreview(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Cost preview failed");
    } finally { setBusy(false); }
  };

  const link = async () => {
    if (!podId || !interiorUrl || !coverUrl) {
      toast.error("Provide a pod_package_id, interior PDF URL, and cover PDF URL");
      return;
    }
    setBusy(true);
    try {
      const r = await api.post("/lulu/make-fulfillable", {
        product_id: draft.id,
        pod_package_id: podId,
        page_count: parseInt(pageCount, 10),
        interior_pdf_url: interiorUrl.trim(),
        cover_pdf_url: coverUrl.trim(),
      });
      toast.success(`Linked to Lulu · base $${r.data.base_cost_usd.toFixed(2)} → retail $${r.data.retail_price_usd.toFixed(2)}`);
      onLinked?.();
      setShow(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Lulu linking failed");
    } finally { setBusy(false); }
  };

  if (!show) {
    return (
      <button onClick={() => setShow(true)} className="w-full inline-flex items-center justify-center gap-1.5 text-[11px] uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] border border-[#476B6B] rounded-md py-1.5 transition" data-testid={`draft-lulu-link-${draft.id}`}>
        <Package size={12} strokeWidth={1.8} /> Make fulfillable on Lulu
      </button>
    );
  }

  return (
    <div className="space-y-2 text-xs" data-testid={`draft-lulu-form-${draft.id}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-[#476B6B]">Lulu config</span>
        <button onClick={() => setShow(false)} className="text-[10px] text-[#5C6B6B] hover:underline">cancel</button>
      </div>
      <button onClick={autoGenerate} disabled={autoGenerating} className="w-full inline-flex items-center justify-center gap-1.5 text-[11px] uppercase tracking-wider text-white bg-[#C9A961] hover:bg-[#B89A5A] rounded-md py-2 transition disabled:opacity-50" data-testid={`lulu-auto-pdfs-${draft.id}`}>
        <Sparkles size={12} strokeWidth={1.8} /> {autoGenerating ? "Generating PDFs…" : "Auto-generate interior + cover PDFs"}
      </button>
      <label className="block">
        Interior style{styleAutoInferred && <span className="ml-1 text-[9px] text-[#C9A961] uppercase">· ai-inferred</span>}
        <select value={interiorStyle} onChange={(e) => { setInteriorStyle(e.target.value); setStyleAutoInferred(false); }} className="input-field !py-1 !px-2 text-xs w-full mt-1" data-testid={`lulu-interior-style-${draft.id}`}>
          {interiorStyles.length === 0 && <option value={interiorStyle}>{interiorStyle}</option>}
          {interiorStyles.map((s) => <option key={s.key} value={s.key}>{s.key} — {s.description.slice(0, 70)}</option>)}
        </select>
      </label>
      <label className="block">
        Preset
        <select value={presetKey} onChange={(e) => choosePreset(e.target.value)} className="input-field !py-1 !px-2 text-xs w-full mt-1" data-testid={`lulu-preset-${draft.id}`}>
          {presets.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
        </select>
      </label>
      <div className="grid grid-cols-2 gap-2">
        <label>
          pod_package_id
          <input value={podId} onChange={(e) => { setPodId(e.target.value); setPreview(null); }} className="input-field !py-1 !px-2 text-xs w-full mt-1 font-mono" data-testid={`lulu-pod-${draft.id}`} />
        </label>
        <label>
          page_count{pagesAutoInferred && <span className="ml-1 text-[9px] text-[#C9A961] uppercase" data-testid={`lulu-pages-ai-${draft.id}`}>· ai-suggested</span>}
          <input type="number" min="4" max="800" value={pageCount} onChange={(e) => { setPageCount(parseInt(e.target.value, 10) || 0); setPagesAutoInferred(false); setPreview(null); }} className="input-field !py-1 !px-2 text-xs w-full mt-1" data-testid={`lulu-pages-${draft.id}`} />
        </label>
      </div>
      <label className="block">
        interior PDF URL
        <input type="url" value={interiorUrl} onChange={(e) => setInteriorUrl(e.target.value)} placeholder="https://.../interior.pdf" className="input-field !py-1 !px-2 text-xs w-full mt-1 font-mono" data-testid={`lulu-interior-${draft.id}`} />
      </label>
      <label className="block">
        cover PDF URL
        <input type="url" value={coverUrl} onChange={(e) => setCoverUrl(e.target.value)} placeholder="https://.../cover.pdf" className="input-field !py-1 !px-2 text-xs w-full mt-1 font-mono" data-testid={`lulu-cover-${draft.id}`} />
      </label>
      <div className="flex flex-wrap gap-2">
        <button onClick={runPreview} disabled={busy || !podId} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`lulu-preview-${draft.id}`}>
          <Coins size={11} strokeWidth={1.8} /> {busy ? "…" : "Preview cost"}
        </button>
        <button onClick={link} disabled={busy || !podId || !interiorUrl || !coverUrl} className="btn-primary text-xs" data-testid={`lulu-link-confirm-${draft.id}`}>
          {busy ? "Linking…" : "Make fulfillable"}
        </button>
      </div>
      {preview && (
        <div className="rounded border border-[#E5E1D8] bg-[#FAF8F5] p-2 text-[11px] leading-relaxed" data-testid={`lulu-preview-result-${draft.id}`}>
          <p>print ${preview.line_cost_usd} · ship ${preview.shipping_cost_usd} · fulfillment ${preview.fulfillment_cost_usd} · tax ${preview.tax_usd}</p>
          <p className="mt-1">base <strong>${preview.base_cost_excl_tax_usd}</strong> → suggested retail <strong>${preview.suggested_retail_usd}</strong></p>
        </div>
      )}
    </div>
  );
}
