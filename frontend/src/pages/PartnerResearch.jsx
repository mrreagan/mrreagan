import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { Plus, Pencil, Trash2, Sparkles, X, BookOpen, Microscope } from "lucide-react";

const EMPTY = {
  title: "",
  abstract: "",
  authors: "",
  publication_date: new Date().toISOString().slice(0, 10),
  full_text_url: "",
  doi: "",
  cover_image_url: "",
  categories: "",
  tags: "",
  estimated_read_minutes: "",
  tier: "brief",
  status: "draft",
};

const STATUS_PILL = {
  draft:             "bg-[#E5E1D8] text-[#5C6B6B]",
  pending_review:    "bg-[#FFF8E1] text-[#8B7128]",
  changes_requested: "bg-[#FDECE3] text-[#9E5C3C]",
  rejected:          "bg-[#F8DCDC] text-[#7E2C2C]",
  published:         "bg-[#2E5C46] text-white",
  archived:          "bg-[#E5E1D8] text-[#5C6B6B]",
};

export default function PartnerResearch() {
  const [artifacts, setArtifacts] = useState([]);
  const [pricing, setPricing] = useState(null);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [promoting, setPromoting] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/me/research").then((r) => setArtifacts(r.data)),
      api.get("/research/pricing").then((r) => setPricing(r.data)),
    ]).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const startNew = () => { setForm(EMPTY); setEditing("new"); };
  const startEdit = (a) => {
    setForm({
      title: a.title,
      abstract: a.abstract,
      authors: a.authors,
      publication_date: a.publication_date,
      full_text_url: a.full_text_url,
      doi: a.doi || "",
      cover_image_url: a.cover_image_url || "",
      categories: (a.categories || []).join(", "),
      tags: (a.tags || []).join(", "),
      estimated_read_minutes: a.estimated_read_minutes || "",
      tier: a.tier,
      status: a.status,
    });
    setEditing(a.id);
  };

  const save = async () => {
    const payload = {
      title: form.title,
      abstract: form.abstract,
      authors: form.authors,
      publication_date: form.publication_date,
      full_text_url: form.full_text_url,
      doi: form.doi || null,
      cover_image_url: form.cover_image_url || null,
      categories: form.categories.split(",").map((s) => s.trim()).filter(Boolean),
      tags: form.tags.split(",").map((s) => s.trim()).filter(Boolean),
      estimated_read_minutes: form.estimated_read_minutes ? parseInt(form.estimated_read_minutes, 10) : null,
      status: form.status,
    };
    try {
      if (editing === "new") {
        payload.tier = form.tier;  // partners can pick initial tier
        await api.post("/me/research", payload);
        toast.success("Artifact created.");
      } else {
        await api.put(`/me/research/${editing}`, payload);
        toast.success("Artifact updated.");
      }
      setEditing(null);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Save failed.");
    }
  };

  const del = async (a) => {
    if (!window.confirm(`Delete "${a.title}"?`)) return;
    try {
      await api.delete(`/me/research/${a.id}`);
      toast.success("Deleted.");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Delete failed.");
    }
  };

  const promote = async (a) => {
    setPromoting(a.id);
    try {
      const r = await api.post(`/me/research/${a.id}/promote/checkout`, {
        artifact_id: a.id,
        origin_url: window.location.origin,
      });
      window.location.href = r.data.url;
    } catch (e) {
      toast.error(e.response?.data?.detail || "Checkout failed.");
      setPromoting(null);
    }
  };

  if (loading) return <div className="container-page py-16">Loading...</div>;

  return (
    <div className="container-page py-12" data-testid="partner-research-page">
      <span className="label">Research partner</span>
      <h1 className="editorial-h1 mt-2">Your research artifacts</h1>
      <p className="text-sm text-[#5C6B6B] max-w-2xl mt-2">
        Publish briefs and peer-reviewed papers to <a href="/research" className="underline text-[#476B6B]">/research</a>.
        Promote any published artifact to the top of the page for 30 days.
        {pricing && <span className="block mt-2">Brief: <strong>${pricing.tiers.brief}</strong> · Paper: <strong>${pricing.tiers.paper}</strong> per 30 days. Tier is set on each artifact (your admin can override).</span>}
      </p>
      <div className="divider-flame" />

      <div className="flex justify-end mb-3">
        <button onClick={startNew} className="btn-primary inline-flex items-center gap-2" data-testid="new-artifact-btn">
          <Plus size={14} strokeWidth={1.5} /> New artifact
        </button>
      </div>

      <div className="space-y-3" data-testid="my-artifacts-list">
        {artifacts.length === 0 && (
          <div className="card p-10 text-center text-sm text-[#5C6B6B]">No artifacts yet. Create your first.</div>
        )}
        {artifacts.map((a) => {
          const TierIcon = a.tier === "paper" ? BookOpen : Microscope;
          const promoted = a.promoted_until && a.promoted_until > new Date().toISOString();
          return (
            <div key={a.id} className="card p-5 flex items-start gap-4" data-testid={`artifact-${a.id}`}>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <TierIcon size={14} strokeWidth={1.5} className="text-[#476B6B]" />
                  <h3 className="font-serif text-lg">{a.title}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium ${STATUS_PILL[a.status] || STATUS_PILL.draft}`}>
                    {a.status.replace("_", " ")}
                  </span>
                  {promoted && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold bg-[#C9A961] text-[#1A2424]">
                      <Sparkles size={10} strokeWidth={2} /> Promoted
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#5C6B6B] mt-1">{a.tier} · {a.authors} · {a.publication_date}</p>
                <p className="text-sm text-[#1A2424] mt-2 line-clamp-2">{a.abstract}</p>
                {a.moderation_note && (a.status === "changes_requested" || a.status === "rejected") && (
                  <div className="mt-2 p-2 rounded bg-[#FFF8E1] border border-[#C9A961]/40" data-testid={`mod-note-${a.id}`}>
                    <p className="text-[10px] uppercase tracking-wider text-[#8B7128] font-medium">Admin note</p>
                    <p className="text-xs text-[#1A2424] mt-1">{a.moderation_note}</p>
                  </div>
                )}
                {promoted && <p className="text-xs text-[#476B6B] mt-1">Promoted until {new Date(a.promoted_until).toLocaleDateString()}</p>}
              </div>
              <div className="flex flex-col gap-2 items-end shrink-0">
                <button onClick={() => startEdit(a)} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`edit-${a.id}`}>
                  <Pencil size={11} /> Edit
                </button>
                {(a.status === "draft" || a.status === "changes_requested" || a.status === "rejected") && (
                  <button
                    onClick={async () => {
                      try {
                        await api.post(`/me/research/${a.id}/submit-for-review`);
                        toast.success("Submitted for review");
                        load();
                      } catch (e) {
                        toast.error(e.response?.data?.detail || "Submit failed");
                      }
                    }}
                    className="btn-primary text-xs inline-flex items-center gap-1"
                    data-testid={`submit-review-${a.id}`}
                  >
                    Submit for review
                  </button>
                )}
                {a.status === "published" && (
                  <button onClick={() => promote(a)} disabled={promoting === a.id} className="btn-primary text-xs inline-flex items-center gap-1" data-testid={`promote-${a.id}`}>
                    <Sparkles size={11} /> {promoted ? "Extend" : `Promote $${pricing?.tiers?.[a.tier] || ""}`}
                  </button>
                )}
                {!promoted && (
                  <button onClick={() => del(a)} className="text-xs text-[#9E3C3C] hover:underline inline-flex items-center gap-1" data-testid={`del-${a.id}`}>
                    <Trash2 size={11} /> Delete
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {editing !== null && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={() => setEditing(null)}>
          <div className="bg-white max-w-2xl w-full rounded-xl p-6 max-h-[92vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="artifact-modal">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-serif text-2xl">{editing === "new" ? "New artifact" : "Edit artifact"}</h2>
              <button onClick={() => setEditing(null)}><X size={20} strokeWidth={1.5} /></button>
            </div>
            <div className="space-y-3">
              <Field label="Title" v={form.title} onChange={(v) => setForm({ ...form, title: v })} testid="form-title" />
              <Textarea label="Abstract" v={form.abstract} onChange={(v) => setForm({ ...form, abstract: v })} rows={5} testid="form-abstract" />
              <Field label="Authors" v={form.authors} onChange={(v) => setForm({ ...form, authors: v })} testid="form-authors" placeholder="Comma-separated" />
              <div className="grid grid-cols-2 gap-3">
                <Field label="Publication date" type="date" v={form.publication_date} onChange={(v) => setForm({ ...form, publication_date: v })} testid="form-date" />
                <Field label="Estimated read (min)" type="number" v={form.estimated_read_minutes} onChange={(v) => setForm({ ...form, estimated_read_minutes: v })} testid="form-readmins" />
              </div>
              <Field label="Full text URL" v={form.full_text_url} onChange={(v) => setForm({ ...form, full_text_url: v })} testid="form-url" />
              <div className="grid grid-cols-2 gap-3">
                <Field label="DOI (optional)" v={form.doi} onChange={(v) => setForm({ ...form, doi: v })} testid="form-doi" />
                <Field label="Cover image URL" v={form.cover_image_url} onChange={(v) => setForm({ ...form, cover_image_url: v })} testid="form-cover" />
              </div>
              <Field label="Categories" v={form.categories} onChange={(v) => setForm({ ...form, categories: v })} placeholder="attachment, adoption (comma-separated)" testid="form-categories" />
              <Field label="Tags" v={form.tags} onChange={(v) => setForm({ ...form, tags: v })} placeholder="peer-reviewed, longitudinal (comma-separated)" testid="form-tags" />
              <div className="grid grid-cols-2 gap-3">
                {editing === "new" && (
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Tier</label>
                    <select value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })} className="input-field w-full text-sm" data-testid="form-tier">
                      <option value="brief">Brief — ${pricing?.tiers?.brief || 49} / 30 days</option>
                      <option value="paper">Peer-reviewed paper — ${pricing?.tiers?.paper || 149} / 30 days</option>
                    </select>
                  </div>
                )}
                <div>
                  <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Status</label>
                  <select value={form.status === "draft" || form.status === "pending_review" ? form.status : "draft"} onChange={(e) => setForm({ ...form, status: e.target.value })} className="input-field w-full text-sm" data-testid="form-status">
                    <option value="draft">Save as draft</option>
                    <option value="pending_review">Submit for review</option>
                  </select>
                  <p className="text-[10px] text-[#5C6B6B] mt-1">Admin will review &amp; publish — you can't self-publish.</p>
                </div>
              </div>
              <div className="flex gap-2 pt-2">
                <button onClick={save} className="btn-primary flex-1" data-testid="form-save">Save</button>
                <button onClick={() => setEditing(null)} className="btn-outline">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, v, onChange, type = "text", placeholder, testid }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">{label}</label>
      <input type={type} value={v} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="input-field w-full text-sm" data-testid={testid} />
    </div>
  );
}
function Textarea({ label, v, onChange, rows = 4, testid }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">{label}</label>
      <textarea value={v} onChange={(e) => onChange(e.target.value)} rows={rows} className="input-field w-full text-sm" data-testid={testid} />
    </div>
  );
}
