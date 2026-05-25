import React, { useState } from "react";
import { toast } from "sonner";
import { Sparkles, X, ClipboardCheck, Image as ImageIcon } from "lucide-react";
import api from "../lib/api";

/**
 * VendorPDMPanel — drawer for vendor partners.
 * 4 tabs: Write description · Suggest price · Marketing blurb · Generate image.
 */
export default function VendorPDMPanel({ open, onClose, onPickResult }) {
  const [tab, setTab] = useState("desc");
  return open ? (
    <div className="fixed inset-0 z-50 flex" data-testid="vendor-pdm-panel">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="ml-auto relative bg-[#FAF8F5] w-full sm:w-[540px] h-full shadow-2xl flex flex-col">
        <header className="flex items-center justify-between px-5 py-4 border-b border-[#E5E1D8] bg-white">
          <div className="flex items-center gap-2">
            <Sparkles size={16} strokeWidth={1.5} className="text-[#C9A961]" />
            <h2 className="font-serif text-lg">Product Development AI</h2>
          </div>
          <button onClick={onClose} aria-label="Close" data-testid="vendor-pdm-close"><X size={18} strokeWidth={1.5} /></button>
        </header>
        <div className="px-5 pt-3 flex flex-wrap gap-2" data-testid="vendor-pdm-tabs">
          {[
            { v: "desc",    l: "Description" },
            { v: "price",   l: "Price tier" },
            { v: "blurb",   l: "Marketing blurb" },
            { v: "image",   l: "Image" },
          ].map((t) => (
            <button
              key={t.v}
              onClick={() => setTab(t.v)}
              className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                tab === t.v ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8]"
              }`}
              data-testid={`vendor-pdm-tab-${t.v}`}
            >
              {t.l}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          {tab === "desc" && <DescPane onPickResult={onPickResult} />}
          {tab === "price" && <PricePane />}
          {tab === "blurb" && <BlurbPane onPickResult={onPickResult} />}
          {tab === "image" && <ImagePane onPickResult={onPickResult} />}
        </div>
      </div>
    </div>
  ) : null;
}

function CostPill({ cost }) {
  if (cost == null) return null;
  return <span className="text-[10px] uppercase tracking-wider text-[#5C6B6B]" data-testid="cost-pill">billed ${cost.toFixed(4)}</span>;
}

function DescPane({ onPickResult }) {
  const [brief, setBrief] = useState("");
  const [category, setCategory] = useState("merch");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setOut(null);
    try {
      const r = await api.post("/vendor-ai/write-description", { brief, category, target_words: 120 });
      setOut(r.data.description); setCost(r.data.cost_usd);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Brief</label>
      <textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={6} className="input-field text-sm w-full" data-testid="desc-brief" placeholder="A linen-cotton blend journal for daily attachment reflections…" />
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1 mt-3">Category</label>
      <input value={category} onChange={(e) => setCategory(e.target.value)} className="input-field text-sm w-full" data-testid="desc-category" />
      <button onClick={run} disabled={busy || brief.length < 10} className="btn-primary text-sm mt-3" data-testid="desc-run">
        {busy ? "Writing…" : "Write description"}
      </button>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {out && (
        <div className="card p-3 mt-3 bg-white" data-testid="desc-result">
          <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans">{out}</pre>
          {onPickResult && (
            <button onClick={() => onPickResult(out)} className="btn-outline text-xs mt-3 inline-flex items-center gap-1" data-testid="desc-pick">
              <ClipboardCheck size={11} /> Use this
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function PricePane() {
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("merch");
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setData(null);
    try {
      const r = await api.post("/vendor-ai/suggest-price", { description, category });
      setData(r.data); setCost(r.data.cost_usd);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Product description</label>
      <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={6} className="input-field text-sm w-full" data-testid="price-description" />
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1 mt-3">Category</label>
      <input value={category} onChange={(e) => setCategory(e.target.value)} className="input-field text-sm w-full" data-testid="price-category" />
      <button onClick={run} disabled={busy || description.length < 10} className="btn-primary text-sm mt-3" data-testid="price-run">
        {busy ? "…" : "Suggest price"}
      </button>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {data && (
        <div className="card p-3 mt-3 bg-white" data-testid="price-result">
          {data.low_usd != null ? (
            <>
              <p className="text-sm">Suggested range: <b>${data.low_usd}</b> – <b>${data.high_usd}</b> (mid: ${data.mid_usd})</p>
              <p className="text-xs text-[#5C6B6B] mt-2">{data.rationale}</p>
            </>
          ) : (
            <pre className="whitespace-pre-wrap text-sm">{data.rationale || JSON.stringify(data, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}

function BlurbPane({ onPickResult }) {
  const [description, setDescription] = useState("");
  const [audience, setAudience] = useState("general");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setOut(null);
    try {
      const r = await api.post("/vendor-ai/marketing-blurb", { description, audience, max_chars: 240 });
      setOut(r.data.blurb); setCost(r.data.cost_usd);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Product description</label>
      <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={5} className="input-field text-sm w-full" data-testid="blurb-description" />
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1 mt-3">Audience</label>
      <input value={audience} onChange={(e) => setAudience(e.target.value)} className="input-field text-sm w-full" data-testid="blurb-audience" />
      <button onClick={run} disabled={busy || description.length < 10} className="btn-primary text-sm mt-3" data-testid="blurb-run">
        {busy ? "…" : "Write blurb"}
      </button>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {out && (
        <div className="card p-3 mt-3 bg-white" data-testid="blurb-result">
          <p className="text-sm">{out}</p>
          {onPickResult && (
            <button onClick={() => onPickResult(out)} className="btn-outline text-xs mt-3 inline-flex items-center gap-1" data-testid="blurb-pick">
              <ClipboardCheck size={11} /> Use this
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ImagePane({ onPickResult }) {
  const [prompt, setPrompt] = useState("");
  const [slug, setSlug] = useState("vendor");
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState(null);
  const [cost, setCost] = useState(null);
  const run = async () => {
    setBusy(true); setUrl(null);
    try {
      const r = await api.post("/vendor-ai/generate-image", { prompt, slug });
      setUrl(r.data.image_url); setCost(r.data.cost_usd);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Image generation failed");
    } finally { setBusy(false); }
  };
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Image prompt</label>
      <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4} className="input-field text-sm w-full" data-testid="image-prompt" placeholder="A linen journal with embossed flame, warm natural light, cream background…" />
      <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1 mt-3">Slug (filename prefix)</label>
      <input value={slug} onChange={(e) => setSlug(e.target.value)} className="input-field text-sm w-full" data-testid="image-slug" />
      <button onClick={run} disabled={busy || prompt.length < 10} className="btn-primary text-sm mt-3 inline-flex items-center gap-1" data-testid="image-run">
        <ImageIcon size={13} /> {busy ? "Generating…" : "Generate image"}
      </button>
      <div className="mt-2"><CostPill cost={cost} /></div>
      {url && (
        <div className="card p-3 mt-3 bg-white" data-testid="image-result">
          <img src={url} alt="Generated" className="w-full rounded" />
          <p className="text-[10px] font-mono mt-2">{url}</p>
          {onPickResult && (
            <button onClick={() => onPickResult(url)} className="btn-outline text-xs mt-3 inline-flex items-center gap-1" data-testid="image-pick">
              <ClipboardCheck size={11} /> Use this image
            </button>
          )}
        </div>
      )}
    </div>
  );
}
