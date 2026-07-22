import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { ArrowLeft, Check, Gem, Info } from "lucide-react";
import { NonDeductibleNotice, CampaignProgress, TaxStatusPill } from "../components/campaigns/CampaignParts";

const TIER_COLORS = {
  bronze: "from-[#8B4513] to-[#A66832]",
  silver: "from-[#8A8A8A] to-[#B0B0B0]",
  gold: "from-[#C9A961] to-[#D4B677]",
  presenting: "from-[#476B6B] to-[#5F8686]",
};

function StorySection({ story }) {
  // Minimal markdown: split by ## for h2, keep paragraphs.
  const blocks = useMemo(() => {
    if (!story) return [];
    const parts = story.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
    return parts.map((p) => {
      if (p.startsWith("## ")) return { type: "h2", text: p.slice(3).trim() };
      if (p.startsWith("- ")) {
        return { type: "ul", items: p.split(/\n- /).map((x) => x.replace(/^- /, "").trim()) };
      }
      return { type: "p", text: p };
    });
  }, [story]);

  return (
    <div className="prose prose-sm max-w-none text-[#3D4A4A]">
      {blocks.map((b, i) => {
        if (b.type === "h2") return <h2 key={i} className="font-serif text-2xl text-[#0F2424] mt-8 mb-3">{b.text}</h2>;
        if (b.type === "ul") return (
          <ul key={i} className="list-disc pl-5 space-y-1 my-3 text-sm leading-relaxed">
            {b.items.map((it, j) => <li key={j}>{it}</li>)}
          </ul>
        );
        return <p key={i} className="text-sm leading-relaxed my-3">{renderInline(b.text)}</p>;
      })}
    </div>
  );
}

function renderInline(text) {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return <strong key={i} className="font-semibold text-[#0F2424]">{p.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={i}>{p}</React.Fragment>;
  });
}

function TierCard({ tier, selected, onSelect }) {
  const color = TIER_COLORS[tier.id] || "from-[#5C6B6B] to-[#9CA9A9]";
  return (
    <button
      type="button"
      onClick={() => onSelect(tier.id)}
      className={`text-left card p-5 flex flex-col transition ${selected ? "ring-2 ring-[#C9A961] shadow-md" : "hover:shadow-md"}`}
      data-testid={`tier-${tier.id}`}
    >
      <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${color} flex items-center justify-center`}>
        <Gem size={16} strokeWidth={1.5} className="text-white" />
      </div>
      <p className="font-serif text-lg mt-3">{tier.name}</p>
      <p className="font-serif text-3xl text-[#0F2424] mt-1">${tier.amount?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
      <p className="text-xs text-[#5C6B6B] mt-3 flex-1 leading-relaxed">{tier.perks}</p>
      {selected ? (
        <div className="mt-3 inline-flex items-center gap-1 text-xs text-[#C9A961] font-semibold">
          <Check size={12} strokeWidth={2} /> Selected
        </div>
      ) : null}
    </button>
  );
}

function PledgeForm({ campaign, selectedTierId, onSubmitted }) {
  const [form, setForm] = useState({
    sponsor_name: "",
    sponsor_email: "",
    organization: "",
    amount: "",
    message: "",
    display_publicly: false,
  });
  const [submitting, setSubmitting] = useState(false);

  // When tier changes, pre-fill amount
  useEffect(() => {
    if (!selectedTierId) return;
    const t = (campaign.tiers || []).find((x) => x.id === selectedTierId);
    if (t) setForm((f) => ({ ...f, amount: String(t.amount) }));
  }, [selectedTierId, campaign.tiers]);

  const submit = async (e) => {
    e.preventDefault();
    const amt = parseFloat(form.amount);
    if (!form.sponsor_name.trim() || !form.sponsor_email.trim() || !amt || amt < 1) {
      toast.error("Please provide your name, email, and a valid amount.");
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post(`/campaigns/${campaign.slug}/pledge`, {
        ...form,
        amount: amt,
        tier_id: selectedTierId || null,
      });
      toast.success(data.message || "Pledge received. Thank you.");
      onSubmitted?.();
      setForm({
        sponsor_name: "",
        sponsor_email: "",
        organization: "",
        amount: "",
        message: "",
        display_publicly: false,
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not submit pledge.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="card p-6 lg:p-8" data-testid="pledge-form">
      <h2 className="font-serif text-2xl text-[#0F2424]">Pledge your support</h2>
      <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">
        Submit your pledge and we&apos;ll follow up personally to confirm details and next steps.
        No payment is collected on this form.
      </p>
      <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="block">
          <span className="text-xs font-semibold text-[#0F2424]">Your name *</span>
          <input
            type="text"
            required
            value={form.sponsor_name}
            onChange={(e) => setForm({ ...form, sponsor_name: e.target.value })}
            className="input-field mt-1 w-full"
            data-testid="pledge-name"
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-[#0F2424]">Email *</span>
          <input
            type="email"
            required
            value={form.sponsor_email}
            onChange={(e) => setForm({ ...form, sponsor_email: e.target.value })}
            className="input-field mt-1 w-full"
            data-testid="pledge-email"
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-[#0F2424]">Organization (optional)</span>
          <input
            type="text"
            value={form.organization}
            onChange={(e) => setForm({ ...form, organization: e.target.value })}
            className="input-field mt-1 w-full"
            data-testid="pledge-org"
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-[#0F2424]">Pledge amount ($) *</span>
          <input
            type="number"
            required
            min="1"
            step="1"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            className="input-field mt-1 w-full"
            data-testid="pledge-amount"
          />
        </label>
      </div>
      <label className="block mt-4">
        <span className="text-xs font-semibold text-[#0F2424]">Message (optional)</span>
        <textarea
          rows={3}
          value={form.message}
          onChange={(e) => setForm({ ...form, message: e.target.value })}
          className="input-field mt-1 w-full"
          data-testid="pledge-message"
          placeholder="Anything you want the founders to know about your sponsorship."
        />
      </label>
      <label className="flex items-start gap-3 mt-4 cursor-pointer">
        <input
          type="checkbox"
          checked={form.display_publicly}
          onChange={(e) => setForm({ ...form, display_publicly: e.target.checked })}
          className="mt-0.5"
          data-testid="pledge-public"
        />
        <span className="text-xs text-[#5C6B6B] leading-relaxed">
          List me publicly as a sponsor on this campaign page. My name (and organization, if provided)
          may be displayed. Uncheck to remain anonymous.
        </span>
      </label>
      <div className="mt-5">
        <NonDeductibleNotice />
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="btn-primary mt-6 w-full justify-center"
        data-testid="pledge-submit"
      >
        {submitting ? "Submitting…" : "Submit pledge"}
      </button>
    </form>
  );
}

export default function CampaignDetail() {
  const { slug } = useParams();
  const [c, setC] = useState(null);
  const [selectedTierId, setSelectedTierId] = useState(null);
  const [notFound, setNotFound] = useState(false);

  const load = () => {
    api.get(`/campaigns/${slug}`)
      .then((r) => setC(r.data))
      .catch(() => setNotFound(true));
  };
  useEffect(() => { load(); }, [slug]);

  if (notFound) {
    return (
      <div className="container-page py-24 text-center" data-testid="campaign-not-found">
        <h1 className="editorial-h2">Campaign not found</h1>
        <Link to="/campaigns" className="btn-outline mt-6">Back to campaigns</Link>
      </div>
    );
  }
  if (!c) {
    return <div className="container-page py-24 text-[#5C6B6B]" data-testid="campaign-loading">Loading…</div>;
  }

  return (
    <div className="container-page py-12" data-testid="campaign-detail-page">
      <Link to="/campaigns" className="inline-flex items-center gap-1 text-xs text-[#5C6B6B] hover:text-[#0F2424]">
        <ArrowLeft size={12} strokeWidth={1.5} /> All campaigns
      </Link>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-7">
          {c.hero_image_url ? (
            <div className="rounded-2xl overflow-hidden bg-[#F4F1EA] aspect-[16/9] mb-8">
              <img src={c.hero_image_url} alt={c.title} className="w-full h-full object-cover" />
            </div>
          ) : null}
          <span className="label">Sponsor campaign</span>
          <TaxStatusPill className="ml-2" />
          <h1 className="editorial-h1 mt-3" data-testid="campaign-title">{c.title}</h1>
          <p className="text-lg text-[#5C6B6B] mt-3 leading-relaxed">{c.tagline}</p>
          <NonDeductibleNotice notice={c.non_deductible_notice} className="mt-5" />
          {c.contingency_note ? (
            <div className="mt-4 flex items-start gap-2 text-xs text-[#8B4513] bg-[#FBF3E4] border border-[#E5D7B3] rounded-md px-3 py-2">
              <Info size={14} strokeWidth={1.5} className="mt-0.5 shrink-0" />
              <span><strong>Contingent:</strong> {c.contingency_note}</span>
            </div>
          ) : null}

          <div className="mt-8">
            <StorySection story={c.story} />
          </div>

          {c.public_sponsors && c.public_sponsors.length > 0 && (
            <div className="mt-10">
              <h3 className="font-serif text-xl text-[#0F2424]">Named sponsors</h3>
              <div className="mt-3 flex flex-wrap gap-2" data-testid="public-sponsors">
                {c.public_sponsors.map((s, i) => (
                  <span key={i} className="px-3 py-1.5 rounded-full text-xs bg-[#F4F1EA] text-[#0F2424]">
                    {s.name}{s.organization ? ` · ${s.organization}` : ""}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-5 space-y-8">
          <div className="card p-6 sticky top-6">
            <CampaignProgress
              pledged={c.total_pledged}
              goal={c.goal_amount}
              progressPct={c.progress_pct}
              sponsors={c.sponsor_count}
            />
          </div>

          {(c.tiers || []).length > 0 && (
            <div>
              <h3 className="font-serif text-lg text-[#0F2424] mb-3">Choose a tier</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {c.tiers.map((t) => (
                  <TierCard
                    key={t.id}
                    tier={t}
                    selected={selectedTierId === t.id}
                    onSelect={setSelectedTierId}
                  />
                ))}
              </div>
              <button
                type="button"
                onClick={() => setSelectedTierId(null)}
                className="mt-3 text-xs text-[#5C6B6B] underline hover:text-[#0F2424]"
                data-testid="clear-tier"
              >
                Or pledge a custom amount →
              </button>
            </div>
          )}

          <PledgeForm campaign={c} selectedTierId={selectedTierId} onSubmitted={load} />
        </div>
      </div>
    </div>
  );
}
