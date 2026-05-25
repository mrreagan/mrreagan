import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { Sparkles, X, Trash2, Plus } from "lucide-react";

export default function AdminFeatured() {
  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState(null);
  const [cap, setCap] = useState("");
  const [showGrant, setShowGrant] = useState(false);
  const [includeExpired, setIncludeExpired] = useState(false);

  const load = () => {
    api.get(`/admin/featured?include_expired=${includeExpired}`).then((r) => setRows(r.data));
    api.get("/founding-partners/stats").then((r) => { setStats(r.data); setCap(String(r.data.cap)); });
  };
  useEffect(load, [includeExpired]);

  const revoke = async (row) => {
    const reason = window.prompt(`Revoke featured slot for ${row.display_name}? Reason (optional):`);
    if (reason === null) return;
    try {
      await api.post(`/admin/featured/${row.id}/revoke?reason=${encodeURIComponent(reason)}`);
      toast.success("Revoked.");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed."); }
  };

  const updateCap = async () => {
    const n = parseInt(cap, 10);
    if (!n || n < 1) return toast.error("Cap must be ≥ 1");
    try {
      await api.put("/admin/founding-partners/cap", { cap: n });
      toast.success(`Cap updated to ${n}.`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed."); }
  };

  return (
    <div className="container-page py-12" data-testid="admin-featured-page">
      <span className="label">Admin</span>
      <h1 className="editorial-h1 mt-2">Featured & Founding</h1>
      <p className="text-sm text-[#5C6B6B] mt-2 max-w-2xl">
        Featured slots are bought self-serve through Stripe ($99 / 30 days by default), but you can grant comped slots or revoke active ones.
        Founding-Partner status is a separate flag with a global cap.
      </p>
      <div className="divider-flame" />

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        {stats && (
          <div className="card p-5" data-testid="founding-stats-card">
            <p className="label">Founding Partners</p>
            <p className="font-serif text-3xl mt-1">{stats.taken} <span className="text-base text-[#5C6B6B]">/ {stats.cap}</span></p>
            <p className="text-xs text-[#5C6B6B] mt-1">{stats.available} seats remaining</p>
            <div className="h-2 bg-[#E5E1D8] rounded-full mt-3 overflow-hidden">
              <div className="h-full bg-[#2E5C46]" style={{ width: `${Math.min(100, Math.round((stats.taken / stats.cap) * 100))}%` }} />
            </div>
            <div className="flex gap-2 mt-3">
              <input value={cap} onChange={(e) => setCap(e.target.value)} className="input-field text-sm w-24" data-testid="cap-input" />
              <button onClick={updateCap} className="btn-outline text-sm" data-testid="update-cap">Update cap</button>
            </div>
          </div>
        )}
        <div className="card p-5">
          <p className="label">Active Featured slots</p>
          <p className="font-serif text-3xl mt-1">{rows.filter((r) => r.featured_until && new Date(r.featured_until) > new Date()).length}</p>
          <p className="text-xs text-[#5C6B6B] mt-1">Self-serve checkout at $99/30 days</p>
        </div>
      </div>

      <div className="flex items-center justify-between mb-3 flex-wrap gap-3">
        <h2 className="font-serif text-2xl">Featured slots</h2>
        <div className="flex items-center gap-3">
          <label className="text-xs text-[#5C6B6B] inline-flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={includeExpired} onChange={(e) => setIncludeExpired(e.target.checked)} data-testid="include-expired" />
            Include expired
          </label>
          <button onClick={() => setShowGrant(true)} className="btn-primary inline-flex items-center gap-2" data-testid="grant-featured-btn">
            <Plus size={14} strokeWidth={1.5} /> Grant comped slot
          </button>
        </div>
      </div>

      <div className="space-y-3" data-testid="featured-list">
        {rows.length === 0 && (
          <div className="card p-8 text-center text-sm text-[#5C6B6B]">No featured profiles.</div>
        )}
        {rows.map((r) => {
          const active = r.featured_until && new Date(r.featured_until) > new Date();
          return (
            <div key={r.id} className="card p-4 flex items-start gap-3" data-testid={`featured-row-${r.slug}`}>
              {r.photo_url && <img src={r.photo_url} alt="" className="w-12 h-12 rounded-full object-cover" />}
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-serif text-lg">{r.display_name}</p>
                  {active ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold bg-[#C9A961] text-[#1A2424]">
                      <Sparkles size={10} strokeWidth={2} /> Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold bg-[#E5E1D8] text-[#5C6B6B]">
                      Expired
                    </span>
                  )}
                  {r.is_founding_partner && <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold bg-[#2E5C46] text-white">★ Founding</span>}
                </div>
                <p className="text-xs text-[#5C6B6B]">{r.partner_type} · {r.slug}</p>
                <p className="text-xs text-[#476B6B] mt-1">Until: {new Date(r.featured_until).toLocaleDateString()}</p>
                {r.featured_mission_alignment && (
                  <p className="text-xs text-[#1A2424] mt-2 italic line-clamp-2">"{r.featured_mission_alignment}"</p>
                )}
              </div>
              {active && (
                <button onClick={() => revoke(r)} className="text-xs text-[#9E3C3C] hover:underline inline-flex items-center gap-1" data-testid={`revoke-${r.slug}`}>
                  <Trash2 size={11} /> Revoke
                </button>
              )}
            </div>
          );
        })}
      </div>

      {showGrant && <GrantModal onClose={() => setShowGrant(false)} onGranted={() => { setShowGrant(false); load(); }} />}
    </div>
  );
}

function GrantModal({ onClose, onGranted }) {
  const [profileId, setProfileId] = useState("");
  const [days, setDays] = useState("30");
  const [mission, setMission] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const until = new Date(Date.now() + parseInt(days, 10) * 86400000).toISOString();
      await api.post(`/admin/featured/${profileId}/grant`, { until, mission_alignment: mission });
      toast.success("Granted.");
      onGranted();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed."); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()} className="bg-white w-full max-w-md rounded-xl p-6" data-testid="grant-modal">
        <div className="flex justify-between items-center mb-4">
          <h2 className="font-serif text-2xl">Grant comped slot</h2>
          <button type="button" onClick={onClose}><X size={20} strokeWidth={1.5} /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="label">Partner profile ID</label>
            <input value={profileId} onChange={(e) => setProfileId(e.target.value)} required className="input-field text-sm w-full" data-testid="grant-profile-id" placeholder="UUID from /admin/partners" />
          </div>
          <div>
            <label className="label">Duration (days)</label>
            <input type="number" min="1" max="365" value={days} onChange={(e) => setDays(e.target.value)} required className="input-field text-sm w-full" data-testid="grant-days" />
          </div>
          <div>
            <label className="label">Mission alignment</label>
            <textarea value={mission} onChange={(e) => setMission(e.target.value)} rows={3} className="input-field text-sm w-full" data-testid="grant-mission" />
          </div>
          <button type="submit" disabled={busy} className="btn-primary w-full" data-testid="grant-submit">{busy ? "Granting..." : "Grant slot"}</button>
        </div>
      </form>
    </div>
  );
}
