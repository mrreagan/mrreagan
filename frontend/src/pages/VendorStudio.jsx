import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, Coins, FlaskConical, Heart, ShoppingBag, Trash2, AlertTriangle, Clock, CheckCircle2, XCircle, MessageSquare, ExternalLink, Package } from "lucide-react";
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

const STATUS_META = {
  pending_review:   { label: "Pending review",   color: "text-[#8B7128] bg-[#FFF8E1] border-[#C9A961]", icon: Clock },
  changes_requested:{ label: "Changes requested",color: "text-[#9E3C3C] bg-[#FBEAEA] border-[#9E3C3C]", icon: MessageSquare },
  rejected:         { label: "Rejected",         color: "text-[#5C6B6B] bg-[#F4F1EA] border-[#5C6B6B]", icon: XCircle },
  active:           { label: "Approved & live",  color: "text-[#01784E] bg-[#E8F4EC] border-[#01784E]", icon: CheckCircle2 },
};

export default function VendorStudio() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [brief, setBrief] = useState("");
  const [category, setCategory] = useState("cap");
  const [audiences, setAudiences] = useState(["general_equip"]);
  const [imageCount, setImageCount] = useState(2);
  const [isOffSite, setIsOffSite] = useState(false);
  const [externalUrl, setExternalUrl] = useState("");
  const [estimate, setEstimate] = useState(null);
  const [estimating, setEstimating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [drafts, setDrafts] = useState([]);
  const [accessChecked, setAccessChecked] = useState(false);
  const [hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    if (!user) {
      navigate("/login", { replace: true });
      return;
    }
    // Quick access pre-check via /partners/my-profiles
    api.get("/partners/my-profiles").then((r) => {
      const ok = (r.data || []).some((p) => p.partner_type === "vendor" && p.status === "active");
      setHasAccess(ok || user.role === "admin");
      setAccessChecked(true);
      if (ok || user.role === "admin") refreshDrafts();
    }).catch(() => {
      setHasAccess(user.role === "admin");
      setAccessChecked(true);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const refreshDrafts = async () => {
    try {
      const r = await api.get("/studio/my-drafts");
      setDrafts(r.data);
    } catch {
      // silent
    }
  };

  const canEstimate = brief.trim().length >= 10 && audiences.length > 0;
  const offSiteUrlValid = !isOffSite || /^https?:\/\/.+/i.test(externalUrl.trim());

  const toggleAudience = (v) => {
    setAudiences((a) => (a.includes(v) ? (a.length > 1 ? a.filter((x) => x !== v) : a) : [...a, v]));
    setEstimate(null);
  };

  const runEstimate = async () => {
    if (!canEstimate) return;
    setEstimating(true);
    setEstimate(null);
    try {
      const r = await api.post("/studio/estimate", { brief: brief.trim(), category, audiences, image_count: imageCount });
      setEstimate(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't estimate cost");
    } finally {
      setEstimating(false);
    }
  };

  const runGenerate = async () => {
    if (!estimate) { toast.message("Get a cost estimate first"); return; }
    if (estimate.insufficient_funds) { toast.error("Top up your AI Wallet first"); return; }
    if (isOffSite && !offSiteUrlValid) { toast.error("Enter a valid http(s) URL for your external site"); return; }
    setGenerating(true);
    try {
      const payload = {
        brief: brief.trim(),
        category,
        audiences,
        image_count: imageCount,
        is_off_site: isOffSite,
        external_url: isOffSite ? externalUrl.trim() : null,
      };
      await api.post("/studio/generate", payload);
      toast.success("Submitted for admin review");
      setEstimate(null);
      setBrief("");
      setExternalUrl("");
      refreshDrafts();
      setTimeout(() => {
        document.getElementById("vendor-studio-drafts")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 200);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  if (!accessChecked) return <div className="container-page py-20 text-center text-sm text-[#5C6B6B]">Loading…</div>;
  if (!hasAccess) {
    return (
      <div className="container-page py-12 max-w-2xl" data-testid="vendor-studio-access-denied">
        <h1 className="editorial-h1">AI Studio</h1>
        <div className="card p-6 mt-4">
          <p className="font-serif text-lg">You need an active vendor partner profile to use the Studio.</p>
          <p className="text-sm text-[#5C6B6B] mt-2">Apply to become a Birthright vendor partner — then come back to dream products into being.</p>
          <Link to="/partners/apply?type=vendor" className="btn-primary text-sm mt-4 inline-flex">Apply as a vendor →</Link>
        </div>
      </div>
    );
  }

  const significantSpend = estimate?.significant_portion_of_balance;
  const insufficient = estimate?.insufficient_funds;

  return (
    <div className="container-page py-12" data-testid="vendor-studio-page">
      <span className="label">Vendor · AI Studio</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <FlaskConical size={26} strokeWidth={1.2} /> Dream a product
      </h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Describe what you want. Studio shows you the dollar cost upfront, generates
        hero images and copy, and submits your draft to admin for moderation before
        it goes live. Once approved it lives on Birthright with your name as the vendor.
      </p>

      <div className="rounded-2xl border-2 border-[#C9A961] bg-[#FFF8E1] p-5 mt-6 max-w-3xl">
        <p className="text-[10px] uppercase tracking-wider text-[#8B7128] font-semibold">Pricing honesty — 1.50× passthrough</p>
        <p className="font-serif text-lg mt-1 leading-snug">You see the dollar cost — and what supports the foundation — before you spend it.</p>
        <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">
          The +50% built into every call directly funds the foundation. Your share of
          eventual product sales is set by your active subscription tier.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        <section className="lg:col-span-2 space-y-5" data-testid="vendor-studio-composer">
          <div className="card p-6">
            <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
              Brief
              <textarea
                value={brief}
                onChange={(e) => { setBrief(e.target.value); setEstimate(null); }}
                placeholder="e.g. a deep navy cotton tee with a small softened-shield icon over the heart, brand language quiet and restrained"
                className="input-field mt-2 min-h-[120px] !font-serif !text-base"
                data-testid="vendor-studio-brief"
              />
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
                Category
                <select value={category} onChange={(e) => { setCategory(e.target.value); setEstimate(null); }} className="input-field mt-2" data-testid="vendor-studio-category">
                  {CATEGORIES.map((c) => <option key={c.v} value={c.v}>{c.label}</option>)}
                </select>
              </label>
              <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
                Images to generate
                <select value={imageCount} onChange={(e) => { setImageCount(parseInt(e.target.value, 10)); setEstimate(null); }} className="input-field mt-2" data-testid="vendor-studio-image-count">
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
                    className={`text-left rounded-lg border p-3 transition ${audiences.includes(a.v) ? "border-[#476B6B] bg-[#F4F1EA]" : "border-[#E5E1D8] bg-white hover:border-[#5C6B6B]"}`}
                    data-testid={`vendor-studio-audience-${a.v}`}
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
            </div>

            {/* Phase 4 — Off-site referral mode */}
            <div className="mt-5 pt-4 border-t border-[#E5E1D8]" data-testid="vendor-studio-fulfillment">
              <p className="text-xs uppercase tracking-wider text-[#5C6B6B] mb-2">Where will customers buy this?</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => { setIsOffSite(false); setEstimate(null); }}
                  className={`text-left rounded-lg border p-3 transition ${!isOffSite ? "border-[#476B6B] bg-[#F4F1EA]" : "border-[#E5E1D8] bg-white hover:border-[#5C6B6B]"}`}
                  data-testid="vendor-studio-fulfill-birthright"
                >
                  <span className="font-serif text-base">Birthright store</span>
                  <p className="text-xs text-[#5C6B6B] mt-1">We handle checkout. You earn your revenue share per your subscription tier — Birthright keeps the rest.</p>
                </button>
                <button
                  type="button"
                  onClick={() => { setIsOffSite(true); setEstimate(null); }}
                  className={`text-left rounded-lg border p-3 transition ${isOffSite ? "border-[#476B6B] bg-[#F4F1EA]" : "border-[#E5E1D8] bg-white hover:border-[#5C6B6B]"}`}
                  data-testid="vendor-studio-fulfill-external"
                >
                  <span className="font-serif text-base">My external site</span>
                  <p className="text-xs text-[#5C6B6B] mt-1">We send customers your way. You keep the full retail and send a small referral commission back to Birthright.</p>
                </button>
              </div>
              {isOffSite && (
                <div className="mt-3" data-testid="vendor-studio-external-url-block">
                  <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
                    Product URL on your site
                    <input
                      type="url"
                      value={externalUrl}
                      onChange={(e) => { setExternalUrl(e.target.value); setEstimate(null); }}
                      placeholder="https://yourshop.com/products/your-thing"
                      className="input-field mt-2 text-sm"
                      data-testid="vendor-studio-external-url"
                    />
                  </label>
                  <p className="text-[11px] text-[#5C6B6B] mt-2 leading-relaxed">
                    We'll stamp <code className="text-[#476B6B]">?via=birthright_{user?.id?.slice(0, 6) || "you"}</code> on
                    the destination so you can identify Birthright-sourced traffic. Report those
                    confirmed sales in <Link to="/dashboard/partner/sales-reports" className="underline">Sales reports</Link> —
                    Birthright will invoice the agreed referral commission on the traffic we sent you.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <button type="button" onClick={runEstimate} disabled={!canEstimate || estimating} className="btn-outline text-sm inline-flex items-center gap-2" data-testid="vendor-studio-estimate-btn">
              <Coins size={14} strokeWidth={1.6} /> {estimating ? "Estimating…" : "Estimate cost"}
            </button>
            {estimate && (
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F4F1EA] border border-[#E5E1D8] text-xs" data-testid="vendor-studio-cost-pill">
                <Sparkles size={11} strokeWidth={1.8} className="text-[#C9A961]" />
                <span><strong>${estimate.estimated_cost_usd.toFixed(4)}</strong> to generate</span>
                <span className="text-[#5C6B6B]">·</span>
                <span className="text-[#5C6B6B]">${estimate.foundation_portion_usd.toFixed(4)} supports the foundation</span>
              </span>
            )}
          </div>

          {estimate && (
            <div className={`rounded-xl border-2 p-4 ${insufficient ? "border-[#9E3C3C] bg-[#FBEAEA]" : significantSpend ? "border-[#C9A961] bg-[#FFF8E1]" : "border-[#E5E1D8] bg-white"}`} data-testid="vendor-studio-confirm-card">
              {insufficient ? (
                <>
                  <p className="font-serif text-lg inline-flex items-center gap-2">
                    <AlertTriangle size={16} className="text-[#9E3C3C]" strokeWidth={1.5} /> Not enough in your wallet
                  </p>
                  <p className="text-sm text-[#5C6B6B] mt-1">This prompt costs <strong>${estimate.estimated_cost_usd.toFixed(4)}</strong>. Top up to continue.</p>
                  <Link to="/dashboard/ai-wallet" className="btn-primary text-xs mt-3 inline-flex">Top up the AI Wallet →</Link>
                </>
              ) : (
                <>
                  <p className="font-serif text-lg">Ready to submit.</p>
                  <p className="text-sm text-[#5C6B6B] mt-1">
                    Spending <strong>${estimate.estimated_cost_usd.toFixed(4)}</strong>. Your draft is sent
                    to admin for review before going live.
                  </p>
                  <button onClick={runGenerate} disabled={generating} className="btn-primary text-sm mt-3" data-testid="vendor-studio-confirm-generate">
                    {generating ? "Generating… (takes ~30s)" : "Generate & submit for review"}
                  </button>
                </>
              )}
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <div className="card p-5">
            <p className="label !mt-0">How review works</p>
            <ul className="text-xs text-[#5C6B6B] space-y-2 mt-3 leading-relaxed">
              <li>· Admin reviews your draft within 1–2 days.</li>
              <li>· They may request changes (a note will appear here).</li>
              <li>· On approval, admin sets the retail price and publishes.</li>
              <li>· <strong>Birthright store</strong>: you earn revenue share per your tier on every sale.</li>
              <li>· <strong>External site</strong>: you keep the retail; Birthright invoices a referral commission on the traffic we sent.</li>
            </ul>
          </div>
        </aside>
      </div>

      <section id="vendor-studio-drafts" className="mt-12" data-testid="vendor-studio-drafts">
        <h2 className="font-serif text-2xl mb-3">Your submissions</h2>
        {drafts.length === 0 ? (
          <p className="text-sm text-[#5C6B6B]">Nothing submitted yet — dream one up above.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {drafts.map((d) => <VendorDraftCard key={d.id} draft={d} onChange={refreshDrafts} />)}
          </div>
        )}
      </section>
    </div>
  );
}

function VendorDraftCard({ draft, onChange }) {
  const [discarding, setDiscarding] = useState(false);
  const status = draft.moderation_status || "pending_review";
  const meta = STATUS_META[status] || STATUS_META.pending_review;
  const Icon = meta.icon;
  const canDiscard = status !== "active";
  const canFulfill = ["pending_review", "changes_requested"].includes(status) && !draft.is_off_site;
  const printfulSupported = ["cap", "tee", "hoodie", "mug"].includes(draft.category);
  const luluSupported = ["journal", "notebook"].includes(draft.category);
  const onPrintful = !!draft.printful_sync_product_id;
  const onLulu = draft.fulfillable_via === "lulu";

  const discard = async () => {
    if (!window.confirm("Discard this draft? Images will be deleted.")) return;
    setDiscarding(true);
    try {
      await api.delete(`/studio/drafts/${draft.id}`);
      toast.success("Draft discarded");
      onChange?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Discard failed");
    } finally {
      setDiscarding(false);
    }
  };

  return (
    <div className="card overflow-hidden flex flex-col" data-testid={`vendor-draft-card-${draft.id}`}>
      <div className="aspect-square bg-[#F4F1EA] flex items-center justify-center overflow-hidden">
        <img src={draft.image_url} alt={draft.name} className="w-full h-full object-contain p-2" />
      </div>
      <div className="p-4 flex flex-col gap-2 flex-1">
        <div className="flex items-center justify-between">
          <span className="label !mt-0 !text-[#C9A961]">
            {draft.category}
            {draft.is_off_site && (
              <span className="ml-2 inline-flex items-center gap-1 text-[#476B6B]" data-testid={`vendor-draft-off-site-${draft.id}`}>
                <ExternalLink size={9} strokeWidth={1.8} /> off-site
              </span>
            )}
          </span>
          <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider border px-2 py-0.5 rounded-full ${meta.color}`} data-testid={`vendor-draft-status-${draft.id}`}>
            <Icon size={10} strokeWidth={1.8} /> {meta.label}
          </span>
        </div>
        <p className="font-serif text-lg leading-tight">{draft.name}</p>
        <p className="text-xs text-[#5C6B6B] line-clamp-3 leading-relaxed">{draft.description}</p>
        {draft.moderation_note && status !== "active" && (
          <div className="rounded border border-[#E5E1D8] bg-[#FFF8E1] p-2 mt-1">
            <p className="text-[10px] uppercase tracking-wider text-[#8B7128]">Admin note</p>
            <p className="text-xs text-[#5C6B6B] mt-1 leading-relaxed">{draft.moderation_note}</p>
          </div>
        )}
        {status === "active" && draft.price > 0 && (
          <p className="text-xs text-[#01784E] mt-1">Listed at ${draft.price.toFixed(2)}</p>
        )}

        {/* Vendor self-service fulfillment */}
        {canFulfill && (printfulSupported || luluSupported) && (
          <div className="mt-3 pt-3 border-t border-dashed border-[#E5E1D8]" data-testid={`vendor-draft-fulfill-${draft.id}`}>
            {onPrintful ? (
              <p className="text-[11px] inline-flex items-center gap-1.5 text-[#01784E]" data-testid={`vendor-draft-printful-linked-${draft.id}`}>
                <Package size={12} strokeWidth={1.8} /> Printful-ready · awaiting admin approval
              </p>
            ) : onLulu ? (
              <p className="text-[11px] inline-flex items-center gap-1.5 text-[#01784E]" data-testid={`vendor-draft-lulu-linked-${draft.id}`}>
                <Package size={12} strokeWidth={1.8} /> Lulu-ready ({draft.lulu_env}) · awaiting admin approval
              </p>
            ) : printfulSupported ? (
              <VendorPrintfulButton draft={draft} onLinked={onChange} />
            ) : luluSupported ? (
              <VendorLuluForm draft={draft} onLinked={onChange} />
            ) : null}
            <p className="text-[10px] text-[#5C6B6B] mt-1.5 leading-snug italic">
              Optional: set up fulfillment yourself. Admin still reviews + sets retail price before publish.
            </p>
          </div>
        )}

        {canDiscard && (
          <button onClick={discard} disabled={discarding} className="btn-outline !text-[#9E3C3C] !border-[#9E3C3C] text-xs px-2 py-1.5 mt-2 self-start inline-flex items-center gap-1" data-testid={`vendor-draft-discard-${draft.id}`}>
            <Trash2 size={12} strokeWidth={1.5} /> {discarding ? "…" : "Discard"}
          </button>
        )}
      </div>
    </div>
  );
}

function VendorPrintfulButton({ draft, onLinked }) {
  const [busy, setBusy] = useState(false);
  const run = async () => {
    if (!window.confirm(`Push this ${draft.category} to Printful? Admin will set the retail price on approval.`)) return;
    setBusy(true);
    try {
      const r = await api.post("/printful/make-fulfillable", { product_id: draft.id });
      toast.success(`Printful-ready · base $${r.data.base_cost_usd?.toFixed(2)}`);
      onLinked?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Printful linking failed");
    } finally { setBusy(false); }
  };
  return (
    <button onClick={run} disabled={busy} className="w-full inline-flex items-center justify-center gap-1.5 text-[11px] uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] border border-[#476B6B] rounded-md py-1.5 transition" data-testid={`vendor-printful-btn-${draft.id}`}>
      <Package size={12} strokeWidth={1.8} /> {busy ? "Linking…" : "Make fulfillable on Printful"}
    </button>
  );
}

function VendorLuluForm({ draft, onLinked }) {
  const [show, setShow] = useState(false);
  const [presets, setPresets] = useState([]);
  const [presetKey, setPresetKey] = useState("");
  const [podId, setPodId] = useState("");
  const [pageCount, setPageCount] = useState(draft.lulu_page_count_suggested || 144);
  const [interiorUrl, setInteriorUrl] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [interiorStyle, setInteriorStyle] = useState(draft.interior_style || "lined");
  const [styleAuto, setStyleAuto] = useState(!!draft.interior_style);
  const [pagesAuto, setPagesAuto] = useState(!!draft.lulu_page_count_suggested);
  const [busy, setBusy] = useState(false);
  const [autoGenerating, setAutoGenerating] = useState(false);

  useEffect(() => {
    if (show && presets.length === 0) {
      api.get("/lulu/presets").then((r) => {
        const filtered = (r.data || []).filter((p) => p.applies_to?.includes(draft.category));
        setPresets(filtered);
        if (filtered.length && !presetKey) {
          setPresetKey(filtered[0].key);
          setPodId(filtered[0].pod_package_id);
        }
      }).catch(() => {});
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [show]);

  const choosePreset = (k) => {
    const p = presets.find((x) => x.key === k);
    if (!p) return;
    setPresetKey(k);
    setPodId(p.pod_package_id);
  };

  const autoGen = async () => {
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
      setStyleAuto(false);
      setPagesAuto(false);
      toast.success(`PDFs generated · ${r.data.page_count} pp · style "${r.data.interior_style}"`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Auto-PDF failed");
    } finally { setAutoGenerating(false); }
  };

  const link = async () => {
    if (!podId || !interiorUrl || !coverUrl) {
      toast.error("Generate PDFs and pick a preset first");
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
      toast.success(`Lulu-ready · base $${r.data.base_cost_usd?.toFixed(2)}`);
      onLinked?.();
      setShow(false);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Lulu linking failed");
    } finally { setBusy(false); }
  };

  if (!show) {
    return (
      <button onClick={() => setShow(true)} className="w-full inline-flex items-center justify-center gap-1.5 text-[11px] uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] border border-[#476B6B] rounded-md py-1.5 transition" data-testid={`vendor-lulu-open-${draft.id}`}>
        <Package size={12} strokeWidth={1.8} /> Make fulfillable on Lulu
      </button>
    );
  }

  return (
    <div className="space-y-2 text-xs" data-testid={`vendor-lulu-form-${draft.id}`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-[#476B6B]">Lulu config</span>
        <button onClick={() => setShow(false)} className="text-[10px] text-[#5C6B6B] hover:underline">cancel</button>
      </div>
      <button onClick={autoGen} disabled={autoGenerating} className="w-full inline-flex items-center justify-center gap-1.5 text-[11px] uppercase tracking-wider text-white bg-[#C9A961] hover:bg-[#B89A5A] rounded-md py-2 transition disabled:opacity-50" data-testid={`vendor-lulu-auto-${draft.id}`}>
        <Sparkles size={12} strokeWidth={1.8} /> {autoGenerating ? "Generating…" : "Auto-generate PDFs"}
      </button>
      <label className="block">
        Preset
        <select value={presetKey} onChange={(e) => choosePreset(e.target.value)} className="input-field !py-1 !px-2 text-xs w-full mt-1" data-testid={`vendor-lulu-preset-${draft.id}`}>
          {presets.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
        </select>
      </label>
      <div className="grid grid-cols-2 gap-2">
        <label>
          Pages{pagesAuto && <span className="ml-1 text-[9px] text-[#C9A961] uppercase" data-testid={`vendor-lulu-pages-ai-${draft.id}`}>· ai-suggested</span>}
          <input type="number" min="4" max="800" value={pageCount}
            onChange={(e) => { setPageCount(parseInt(e.target.value, 10) || 0); setPagesAuto(false); }}
            className="input-field !py-1 !px-2 text-xs w-full mt-1" data-testid={`vendor-lulu-pages-${draft.id}`} />
        </label>
        <label>
          Style{styleAuto && <span className="ml-1 text-[9px] text-[#C9A961] uppercase" data-testid={`vendor-lulu-style-ai-${draft.id}`}>· ai-inferred</span>}
          <input value={interiorStyle} onChange={(e) => { setInteriorStyle(e.target.value); setStyleAuto(false); }} className="input-field !py-1 !px-2 text-xs w-full mt-1" data-testid={`vendor-lulu-style-${draft.id}`} />
        </label>
      </div>
      {interiorUrl && coverUrl && (
        <p className="text-[10px] text-[#01784E] leading-relaxed" data-testid={`vendor-lulu-pdfs-ready-${draft.id}`}>
          ✓ PDFs generated. Click below to link.
        </p>
      )}
      <button onClick={link} disabled={busy || !interiorUrl || !coverUrl} className="btn-primary text-xs w-full" data-testid={`vendor-lulu-link-${draft.id}`}>
        {busy ? "Linking…" : "Make fulfillable"}
      </button>
    </div>
  );
}
