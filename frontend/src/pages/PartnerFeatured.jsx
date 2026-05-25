import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { Sparkles, Save, ExternalLink as LinkIcon, CreditCard } from "lucide-react";

const EMPTY = {
  mission_alignment: "",
  signature_content: "",
  video_url: "",
  image_urls: ["", "", ""],
  custom_cta: "",
  custom_cta_url: "",
};

export default function PartnerFeatured() {
  const [profiles, setProfiles] = useState([]);
  const [partnerType, setPartnerType] = useState(null);
  const [state, setState] = useState(null); // {profile, is_featured, pricing}
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/partners/my-profiles")
      .then((r) => {
        const active = (r.data || []).filter((p) => p.status === "active" && !p.is_sample);
        setProfiles(active);
        if (active.length > 0) setPartnerType(active[0].partner_type);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!partnerType) return;
    api.get(`/me/featured?partner_type=${partnerType}`).then((r) => {
      setState(r.data);
      const p = r.data.profile;
      setForm({
        mission_alignment: p.featured_mission_alignment || "",
        signature_content: p.featured_signature_content || "",
        video_url: p.featured_video_url || "",
        image_urls: [...(p.featured_image_urls || []), "", "", ""].slice(0, 3),
        custom_cta: p.featured_custom_cta || "",
        custom_cta_url: p.featured_custom_cta_url || "",
      });
    });
  }, [partnerType]);

  if (loading) return <div className="container-page py-16">Loading...</div>;
  if (profiles.length === 0) {
    return (
      <div className="container-page py-16" data-testid="featured-empty-partner">
        <h1 className="editorial-h1">Featured slot</h1>
        <div className="divider-flame" />
        <div className="card p-8">
          <p className="font-serif text-xl">No active partner profile.</p>
          <p className="text-sm text-[#5C6B6B] mt-3">Apply as a partner first — <a href="/partners/apply" className="underline text-[#476B6B]">/partners/apply</a>.</p>
        </div>
      </div>
    );
  }

  const purchase = async () => {
    setPurchasing(true);
    try {
      const r = await api.post("/me/featured/checkout", {
        partner_type: partnerType,
        origin_url: window.location.origin,
        mission_alignment: form.mission_alignment,
        signature_content: form.signature_content,
        video_url: form.video_url || null,
        image_urls: form.image_urls.filter(Boolean),
        custom_cta: form.custom_cta || null,
        custom_cta_url: form.custom_cta_url || null,
      });
      window.location.href = r.data.url;
    } catch (e) {
      toast.error(e.response?.data?.detail || "Checkout failed.");
    } finally {
      setPurchasing(false);
    }
  };

  const saveContent = async () => {
    setSaving(true);
    try {
      await api.put(`/me/featured?partner_type=${partnerType}`, {
        mission_alignment: form.mission_alignment,
        signature_content: form.signature_content || null,
        video_url: form.video_url || null,
        image_urls: form.image_urls.filter(Boolean),
        custom_cta: form.custom_cta || null,
        custom_cta_url: form.custom_cta_url || null,
      });
      toast.success("Featured content updated.");
      const r = await api.get(`/me/featured?partner_type=${partnerType}`);
      setState(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Update failed.");
    } finally {
      setSaving(false);
    }
  };

  const setImg = (i, v) => {
    const next = [...form.image_urls];
    next[i] = v;
    setForm({ ...form, image_urls: next });
  };

  return (
    <div className="container-page py-12" data-testid="partner-featured-page">
      <span className="label">Partner</span>
      <h1 className="editorial-h1 mt-2">Featured slot</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Promote your work in the spotlight section of Birthright. Featured partners appear on{" "}
        <a href="/featured" className="text-[#476B6B] underline">/featured</a> and carry a gold ribbon across the directory.
      </p>

      {profiles.length > 1 && (
        <div className="flex gap-2 mt-4">
          {profiles.map((p) => (
            <button
              key={p.partner_type}
              onClick={() => setPartnerType(p.partner_type)}
              className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                partnerType === p.partner_type ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`featured-tab-${p.partner_type}`}
            >
              {p.partner_type}
            </button>
          ))}
        </div>
      )}

      {state && (
        <div className="mt-6 grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 card p-6" data-testid="featured-content-form">
            <h2 className="font-serif text-2xl flex items-center gap-2">
              <Sparkles size={18} strokeWidth={1.5} className="text-[#C9A961]" />
              Your featured content
            </h2>
            <p className="text-xs text-[#5C6B6B] mt-1">Update freely while your slot is active.</p>

            <div className="mt-5 space-y-4">
              <Textarea
                label="Mission alignment"
                placeholder="In 2–4 sentences, why does your work belong in Birthright's spotlight?"
                value={form.mission_alignment}
                onChange={(v) => setForm({ ...form, mission_alignment: v })}
                rows={3}
                testid="form-mission"
              />
              <Textarea
                label="Signature content"
                placeholder="A short piece of writing, an offer, a story — what you most want our audience to read."
                value={form.signature_content}
                onChange={(v) => setForm({ ...form, signature_content: v })}
                rows={6}
                testid="form-signature"
              />
              <Field label="Video URL (optional, YouTube/Vimeo)" value={form.video_url} onChange={(v) => setForm({ ...form, video_url: v })} placeholder="https://..." testid="form-video" />
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Image URLs (up to 3)</label>
                <div className="space-y-2">
                  {[0, 1, 2].map((i) => (
                    <input
                      key={i}
                      value={form.image_urls[i] || ""}
                      onChange={(e) => setImg(i, e.target.value)}
                      placeholder={`Image ${i + 1} URL`}
                      className="input-field w-full text-sm"
                      data-testid={`form-image-${i}`}
                    />
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Custom CTA text" value={form.custom_cta} onChange={(v) => setForm({ ...form, custom_cta: v })} placeholder="Visit our store →" testid="form-cta" />
                <Field label="Custom CTA URL" value={form.custom_cta_url} onChange={(v) => setForm({ ...form, custom_cta_url: v })} placeholder="https://..." testid="form-cta-url" />
              </div>

              {state.is_featured ? (
                <button onClick={saveContent} disabled={saving} className="btn-primary inline-flex items-center gap-2" data-testid="save-content">
                  <Save size={14} strokeWidth={1.5} /> {saving ? "Saving..." : "Save content"}
                </button>
              ) : (
                <p className="text-xs text-[#5C6B6B] italic">Fields above will activate the moment you purchase a slot.</p>
              )}
            </div>
          </div>

          <div>
            <SlotCard state={state} onPurchase={purchase} purchasing={purchasing} />
          </div>
        </div>
      )}
    </div>
  );
}

function SlotCard({ state, onPurchase, purchasing }) {
  if (state.is_featured) {
    const until = new Date(state.profile.featured_until);
    const daysLeft = Math.max(Math.ceil((until - new Date()) / (1000 * 60 * 60 * 24)), 0);
    return (
      <div className="card p-6 bg-[#FFFBEF] border-[#C9A961]" data-testid="slot-active">
        <div className="flex items-center gap-2">
          <Sparkles size={16} strokeWidth={1.5} className="text-[#C9A961]" />
          <h3 className="font-serif text-lg">You're featured</h3>
        </div>
        <p className="text-xs text-[#5C6B6B] mt-2">Your slot runs until <strong>{until.toLocaleDateString()}</strong>.</p>
        <p className="text-2xl font-serif text-[#8B7128] mt-3">{daysLeft} days left</p>
        <a href="/featured" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-[#476B6B] hover:underline mt-3" data-testid="view-featured-page">
          <LinkIcon size={11} strokeWidth={1.5} /> See yourself on /featured
        </a>
        <button onClick={onPurchase} disabled={purchasing} className="btn-outline w-full mt-5 text-sm" data-testid="extend-slot">
          {purchasing ? "Loading..." : `Extend (+${state.pricing.duration_days} days for $${state.pricing.price_usd})`}
        </button>
      </div>
    );
  }
  return (
    <div className="card p-6" data-testid="slot-purchase">
      <h3 className="font-serif text-lg flex items-center gap-2">
        <CreditCard size={16} strokeWidth={1.5} className="text-[#C9A961]" />
        Buy a featured slot
      </h3>
      <p className="text-3xl font-serif text-[#1A2424] mt-3">${state.pricing.price_usd}</p>
      <p className="text-xs text-[#5C6B6B]">{state.pricing.duration_days} days · Stripe checkout</p>

      <ul className="text-xs text-[#5C6B6B] mt-4 space-y-2 list-disc list-inside">
        <li>Gold ribbon across the directory</li>
        <li>Featured card on /featured with your content + CTA</li>
        <li>Edit content freely while slot is active</li>
        <li>Random rotation order — no auction</li>
      </ul>

      <button onClick={onPurchase} disabled={purchasing} className="btn-primary w-full mt-5" data-testid="purchase-slot">
        {purchasing ? "Loading..." : "Purchase slot"}
      </button>
      <p className="text-[10px] text-[#5C6B6B] mt-2 text-center">You can preview and refine content before going live.</p>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, testid }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="input-field w-full text-sm" data-testid={testid} />
    </div>
  );
}
function Textarea({ label, value, onChange, placeholder, rows = 4, testid }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">{label}</label>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} rows={rows} className="input-field w-full text-sm" data-testid={testid} />
    </div>
  );
}
