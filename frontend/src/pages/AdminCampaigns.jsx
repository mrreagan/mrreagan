/**
 * AdminCampaigns — manage sponsor campaigns and pledges.
 *
 * Endpoints:
 *   GET    /api/admin/campaigns           — list all campaigns
 *   POST   /api/admin/campaigns           — create
 *   PUT    /api/admin/campaigns/{id}      — update
 *   DELETE /api/admin/campaigns/{id}      — delete
 *   GET    /api/admin/campaigns/pledges/all?campaign_id=&status=  — list pledges
 *   PUT    /api/admin/campaigns/pledges/{id}/status               — update pledge status
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Plus, Trash2, RefreshCcw, ExternalLink } from "lucide-react";
import api from "../lib/api";
import { toast } from "sonner";

const STATUS_ORDER = ["pending", "approved", "invoiced", "paid", "declined", "withdrawn"];

function PledgeRow({ p, onUpdated }) {
  const [status, setStatus] = useState(p.status);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/admin/campaigns/pledges/${p.id}/status`, { status });
      toast.success("Pledge updated");
      onUpdated();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Update failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className="border-b border-[#E8E4DC]" data-testid={`pledge-row-${p.id}`}>
      <td className="p-3 text-sm">
        <div className="font-semibold text-[#0F2424]">{p.sponsor_name}</div>
        <div className="text-xs text-[#5C6B6B]">{p.sponsor_email}</div>
        {p.organization && <div className="text-xs text-[#5C6B6B]">{p.organization}</div>}
      </td>
      <td className="p-3 text-sm">
        <div className="font-serif text-lg">${Number(p.amount).toLocaleString()}</div>
        {p.tier_id && <div className="text-xs text-[#C9A961]">{p.tier_id}</div>}
      </td>
      <td className="p-3 text-sm text-[#5C6B6B] max-w-xs">
        <div className="text-xs">{p.campaign_slug}</div>
        {p.message && <div className="text-xs italic mt-1 line-clamp-2">&ldquo;{p.message}&rdquo;</div>}
        <div className="text-[10px] mt-1">{p.display_publicly ? "Public listing OK" : "Anonymous"}</div>
      </td>
      <td className="p-3">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="input-field text-sm py-1"
          data-testid={`pledge-status-${p.id}`}
        >
          {STATUS_ORDER.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </td>
      <td className="p-3">
        <button
          onClick={save}
          disabled={saving || status === p.status}
          className="btn-outline text-xs py-1 px-3"
          data-testid={`pledge-save-${p.id}`}
        >
          {saving ? "…" : "Save"}
        </button>
      </td>
    </tr>
  );
}

function CampaignEditor({ initial, onSaved, onDeleted }) {
  const [form, setForm] = useState(initial || {
    title: "",
    slug: "",
    tagline: "",
    story: "",
    goal_amount: 1000,
    hero_image_url: "",
    pill_label: "Sponsor this campaign",
    status: "active",
    contingency_note: "",
    tiers: [],
  });
  const [saving, setSaving] = useState(false);
  const isEditing = Boolean(initial?.id);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, goal_amount: parseFloat(form.goal_amount) };
      if (isEditing) {
        await api.put(`/admin/campaigns/${initial.id}`, payload);
        toast.success("Campaign updated");
      } else {
        await api.post("/admin/campaigns", payload);
        toast.success("Campaign created");
      }
      onSaved();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const del = async () => {
    if (!window.confirm(`Delete campaign "${initial.title}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/admin/campaigns/${initial.id}`);
      toast.success("Deleted");
      onDeleted();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Delete failed");
    }
  };

  return (
    <form onSubmit={save} className="card p-5 space-y-3" data-testid={`campaign-editor-${initial?.id || "new"}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs font-semibold">Title</span>
          <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="input-field mt-1 w-full" />
        </label>
        <label className="block">
          <span className="text-xs font-semibold">Slug</span>
          <input required value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} className="input-field mt-1 w-full" disabled={isEditing} />
        </label>
        <label className="block md:col-span-2">
          <span className="text-xs font-semibold">Tagline</span>
          <input value={form.tagline} onChange={(e) => setForm({ ...form, tagline: e.target.value })} className="input-field mt-1 w-full" />
        </label>
        <label className="block md:col-span-2">
          <span className="text-xs font-semibold">Story (markdown)</span>
          <textarea rows={6} value={form.story} onChange={(e) => setForm({ ...form, story: e.target.value })} className="input-field mt-1 w-full font-mono text-xs" />
        </label>
        <label className="block">
          <span className="text-xs font-semibold">Goal amount ($)</span>
          <input type="number" min="1" step="1" required value={form.goal_amount} onChange={(e) => setForm({ ...form, goal_amount: e.target.value })} className="input-field mt-1 w-full" />
        </label>
        <label className="block">
          <span className="text-xs font-semibold">Status</span>
          <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className="input-field mt-1 w-full">
            <option value="active">active</option>
            <option value="paused">paused</option>
            <option value="funded">funded</option>
            <option value="archived">archived</option>
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-semibold">Hero image URL</span>
          <input value={form.hero_image_url || ""} onChange={(e) => setForm({ ...form, hero_image_url: e.target.value })} className="input-field mt-1 w-full" />
        </label>
        <label className="block">
          <span className="text-xs font-semibold">Sponsor pill label</span>
          <input value={form.pill_label} onChange={(e) => setForm({ ...form, pill_label: e.target.value })} className="input-field mt-1 w-full" />
        </label>
        <label className="block md:col-span-2">
          <span className="text-xs font-semibold">Contingency note</span>
          <input value={form.contingency_note || ""} onChange={(e) => setForm({ ...form, contingency_note: e.target.value })} className="input-field mt-1 w-full" />
        </label>
      </div>

      <div className="flex gap-2 items-center flex-wrap pt-2">
        <button type="submit" disabled={saving} className="btn-primary text-sm">
          {saving ? "…" : (isEditing ? "Update" : "Create")}
        </button>
        {isEditing && (
          <>
            <Link to={`/campaigns/${form.slug}`} target="_blank" className="btn-outline text-sm inline-flex items-center gap-1">
              <ExternalLink size={12} strokeWidth={1.5} /> View public
            </Link>
            <button type="button" onClick={del} className="text-sm text-red-600 hover:underline inline-flex items-center gap-1">
              <Trash2 size={12} strokeWidth={1.5} /> Delete
            </button>
            <span className="text-xs text-[#5C6B6B] ml-auto">
              {initial.tiers?.length || 0} tiers · {initial.sponsor_count || 0} pledges · ${(initial.total_pledged || 0).toLocaleString()} pledged
            </span>
          </>
        )}
      </div>
    </form>
  );
}

export default function AdminCampaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [pledges, setPledges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [cRes, pRes] = await Promise.all([
        api.get("/admin/campaigns"),
        api.get("/admin/campaigns/pledges/all"),
      ]);
      setCampaigns(cRes.data || []);
      setPledges(pRes.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Load failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="container-page py-12" data-testid="admin-campaigns-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-4">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="editorial-h1">Sponsor Campaigns</h1>
          <p className="text-sm text-[#5C6B6B] mt-1">
            Target-specific sponsorship drives. Pledge-only until 501(c)(3) status is granted.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="btn-outline text-sm inline-flex items-center gap-1">
            <RefreshCcw size={12} strokeWidth={1.5} /> Refresh
          </button>
          <button onClick={() => setShowNew(!showNew)} className="btn-primary text-sm inline-flex items-center gap-1" data-testid="new-campaign-btn">
            <Plus size={12} strokeWidth={1.5} /> New campaign
          </button>
        </div>
      </div>

      {showNew && (
        <div className="mb-8">
          <CampaignEditor onSaved={() => { setShowNew(false); load(); }} onDeleted={load} />
        </div>
      )}

      {loading ? (
        <p className="text-[#5C6B6B]">Loading…</p>
      ) : (
        <>
          <div className="space-y-4">
            {campaigns.map((c) => (
              <CampaignEditor key={c.id} initial={c} onSaved={load} onDeleted={load} />
            ))}
            {campaigns.length === 0 && (
              <p className="text-[#5C6B6B] text-sm">No campaigns yet. Create one above.</p>
            )}
          </div>

          <div className="mt-12">
            <h2 className="font-serif text-2xl text-[#0F2424] mb-3">All pledges</h2>
            <div className="card overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-[#F4F1EA] text-xs uppercase tracking-wide text-[#5C6B6B]">
                  <tr>
                    <th className="p-3">Sponsor</th>
                    <th className="p-3">Amount</th>
                    <th className="p-3">Campaign / Message</th>
                    <th className="p-3">Status</th>
                    <th className="p-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {pledges.map((p) => <PledgeRow key={p.id} p={p} onUpdated={load} />)}
                  {pledges.length === 0 && (
                    <tr><td colSpan={5} className="p-6 text-sm text-[#5C6B6B] text-center">No pledges yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
