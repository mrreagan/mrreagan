import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { Sliders, Users, ShieldAlert, Scroll, ClipboardList, Plus, Trash2 } from "lucide-react";

const PARTNER_TYPES = ["facilitator", "community", "research", "vendor"];

function fmt(iso) {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

export default function AdminGovernance() {
  const [tab, setTab] = useState("defaults");
  return (
    <div className="container-page py-12" data-testid="admin-governance-page">
      <span className="label">Admin</span>
      <h1 className="editorial-h1 mt-2">Governance & legal</h1>
      <div className="divider-flame" />

      <div className="flex flex-wrap gap-2 mt-6" data-testid="admin-gov-tabs">
        {[
          { id: "defaults", label: "Defaults", icon: Sliders },
          { id: "members", label: "Members", icon: Users },
          { id: "indemnification", label: "Indemnification", icon: Scroll },
          { id: "audit", label: "Audit log", icon: ClipboardList },
        ].map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition inline-flex items-center gap-1 ${
                tab === t.id ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`admin-tab-${t.id}`}
            >
              <Icon size={11} strokeWidth={1.5} /> {t.label}
            </button>
          );
        })}
      </div>

      <div className="mt-6">
        {tab === "defaults" && <DefaultsPanel />}
        {tab === "members" && <MembersPanel />}
        {tab === "indemnification" && <IndemnificationPanel />}
        {tab === "audit" && <AuditPanel />}
      </div>
    </div>
  );
}

function DefaultsPanel() {
  const [defaults, setDefaults] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/governance/defaults").then((r) => setDefaults(r.data));
  useEffect(() => { load(); }, []);

  if (!defaults) return <p className="text-sm text-[#5C6B6B]">Loading…</p>;

  const updateTier = (type, i, key, value) => {
    setDefaults((d) => {
      const next = { ...d, rev_share: { ...d.rev_share, [type]: [...(d.rev_share[type] || [])] } };
      next.rev_share[type][i] = { ...next.rev_share[type][i], [key]: key === "pct" ? Number(value) : value };
      return next;
    });
  };
  const addTier = (type) => setDefaults((d) => ({
    ...d, rev_share: { ...d.rev_share, [type]: [...(d.rev_share[type] || []), { name: "new_tier", pct: 0, description: "" }] },
  }));
  const removeTier = (type, i) => setDefaults((d) => ({
    ...d, rev_share: { ...d.rev_share, [type]: d.rev_share[type].filter((_, idx) => idx !== i) },
  }));

  const save = async () => {
    setBusy(true);
    try {
      await api.put("/governance/defaults", { rev_share: defaults.rev_share, min_listing_rating: defaults.min_listing_rating });
      toast.success("Defaults updated");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not save");
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="defaults-panel">
      <div className="card p-5">
        <span className="label">Minimum listing rating</span>
        <p className="text-xs text-[#5C6B6B] mt-1">Vendor / partner offerings below this average rating are hidden from public listings.</p>
        <input
          type="number" step="0.1" min="0" max="5"
          className="input-field mt-2 max-w-xs"
          value={defaults.min_listing_rating ?? 0}
          onChange={(e) => setDefaults((d) => ({ ...d, min_listing_rating: Number(e.target.value) }))}
          data-testid="min-rating-input"
        />
      </div>

      {PARTNER_TYPES.map((type) => (
        <div key={type} className="card p-5" data-testid={`tiers-${type}`}>
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-lg capitalize">{type} revenue share tiers</h3>
            <button onClick={() => addTier(type)} className="text-xs text-[#476B6B] hover:underline inline-flex items-center gap-1" data-testid={`add-tier-${type}`}>
              <Plus size={11} strokeWidth={1.5} /> Add tier
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {(defaults.rev_share?.[type] || []).map((tier, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-start">
                <input
                  className="input-field col-span-3 text-sm" placeholder="name"
                  value={tier.name} onChange={(e) => updateTier(type, i, "name", e.target.value)}
                  data-testid={`tier-${type}-${i}-name`}
                />
                <div className="col-span-2 flex items-center gap-1">
                  <input
                    type="number" step="0.1" min="0" max="100"
                    className="input-field text-sm" value={tier.pct}
                    onChange={(e) => updateTier(type, i, "pct", e.target.value)}
                    data-testid={`tier-${type}-${i}-pct`}
                  />
                  <span className="text-sm text-[#5C6B6B]">%</span>
                </div>
                <input
                  className="input-field col-span-6 text-sm" placeholder="description"
                  value={tier.description || ""}
                  onChange={(e) => updateTier(type, i, "description", e.target.value)}
                  data-testid={`tier-${type}-${i}-desc`}
                />
                <button onClick={() => removeTier(type, i)} className="col-span-1 text-[#B86A5C] hover:text-[#1A2424]" data-testid={`remove-tier-${type}-${i}`}>
                  <Trash2 size={14} strokeWidth={1.5} />
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}

      <button onClick={save} disabled={busy} className="btn-primary" data-testid="save-defaults-btn">
        {busy ? "Saving…" : "Save defaults"}
      </button>
    </div>
  );
}

function MembersPanel() {
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState([]);

  const load = () => api.get("/governance/members").then((r) => setMembers(r.data));
  useEffect(() => { load(); }, []);

  // Lookup uses /admin/users (admin only) with client-side filter.
  useEffect(() => {
    if (search.trim().length < 2) { setSearchResults([]); return; }
    const q = search.trim().toLowerCase();
    api.get("/admin/users")
      .then((r) => {
        const all = r.data || [];
        setSearchResults(
          all.filter((u) =>
            (u.first_name || "").toLowerCase().includes(q) ||
            (u.last_name || "").toLowerCase().includes(q) ||
            (u.email || "").toLowerCase().includes(q)
          )
        );
      })
      .catch(() => setSearchResults([]));
  }, [search]);

  const setFlags = async (userId, flags) => {
    try {
      await api.put(`/governance/members/${userId}`, flags);
      toast.success("Updated");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not update");
    }
  };

  return (
    <div className="space-y-6" data-testid="members-panel">
      <div className="card p-5">
        <span className="label inline-flex items-center gap-1"><ShieldAlert size={11} strokeWidth={1.5} /> Current governance members</span>
        <ul className="mt-3 divide-y divide-[#E5E1D8]" data-testid="members-list">
          {members.map((m) => (
            <li key={m.id} className="py-3 flex items-center justify-between gap-3 flex-wrap" data-testid={`member-${m.id}`}>
              <div>
                <p className="font-medium">{m.name}</p>
                <p className="text-xs text-[#5C6B6B]">{m.role} · {m.credentials}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <label className="text-xs inline-flex items-center gap-1">
                  <input type="checkbox" checked={m.governance_member} onChange={(e) => setFlags(m.id, { governance_member: e.target.checked })} data-testid={`gov-${m.id}`} />
                  Member
                </label>
                <label className="text-xs inline-flex items-center gap-1">
                  <input type="checkbox" checked={m.is_ombudsman} onChange={(e) => setFlags(m.id, { is_ombudsman: e.target.checked })} data-testid={`omb-${m.id}`} />
                  Ombudsman
                </label>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="card p-5">
        <span className="label">Promote a user</span>
        <p className="text-xs text-[#5C6B6B] mt-1">Search by name or email; set governance / ombudsman flags directly.</p>
        <input
          className="input-field mt-2"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Type 2+ characters…"
          data-testid="user-search"
        />
        {searchResults.length > 0 && (
          <ul className="mt-3 divide-y divide-[#E5E1D8]" data-testid="user-search-results">
            {searchResults.slice(0, 20).map((u) => (
              <li key={u.id} className="py-2 flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium">{u.first_name} {u.last_name}</p>
                  <p className="text-[10px] text-[#5C6B6B]">{u.email} · {u.role}</p>
                </div>
                <div className="flex gap-2">
                  <button className="btn-outline text-xs" onClick={() => setFlags(u.id, { governance_member: true })}>
                    Make member
                  </button>
                  <button className="btn-outline text-xs" onClick={() => setFlags(u.id, { is_ombudsman: true })}>
                    Make ombudsman
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function IndemnificationPanel() {
  const [versions, setVersions] = useState([]);
  const [form, setForm] = useState({ version: "", body: "", summary_of_changes: "" });
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/legal/indemnification/versions").then((r) => setVersions(r.data));
  useEffect(() => { load(); }, []);

  const publish = async (e) => {
    e.preventDefault();
    if (!form.version.trim() || form.body.length < 50) {
      toast.error("Version and body (≥50 chars) are required.");
      return;
    }
    if (!window.confirm(`Publish version ${form.version} and deactivate the current one? Existing signatures remain valid against their own version.`)) return;
    setBusy(true);
    try {
      await api.post("/legal/indemnification/versions", form);
      toast.success(`Published v${form.version}`);
      setForm({ version: "", body: "", summary_of_changes: "" });
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not publish");
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="indemnification-panel">
      <div className="card p-5">
        <span className="label">Published versions</span>
        <ul className="mt-3 divide-y divide-[#E5E1D8]" data-testid="versions-list">
          {versions.map((v) => (
            <li key={v.id} className="py-2 flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">v{v.version} {v.active && <span className="ml-2 text-[10px] uppercase tracking-wider text-[#2E5C46]">Active</span>}</p>
                <p className="text-xs text-[#5C6B6B] mt-0.5">Published {fmt(v.activated_at || v.created_at)} · {v.summary_of_changes || "—"}</p>
              </div>
              <Link to="/legal/indemnification" className="text-xs text-[#476B6B] hover:underline">Preview</Link>
            </li>
          ))}
        </ul>
      </div>

      <form onSubmit={publish} className="card p-5 space-y-3" data-testid="new-version-form">
        <span className="label">Publish a new version</span>
        <input
          className="input-field" placeholder="e.g. 1.1" value={form.version}
          onChange={(e) => setForm((f) => ({ ...f, version: e.target.value }))}
          data-testid="new-version-number"
        />
        <input
          className="input-field" placeholder="Short summary of what changed" value={form.summary_of_changes}
          onChange={(e) => setForm((f) => ({ ...f, summary_of_changes: e.target.value }))}
          data-testid="new-version-summary"
        />
        <textarea
          className="input-field min-h-[260px]" placeholder="Full body (markdown allowed)" value={form.body}
          onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
          data-testid="new-version-body"
        />
        <button type="submit" className="btn-primary" disabled={busy} data-testid="publish-version-btn">
          {busy ? "Publishing…" : "Publish & activate"}
        </button>
      </form>
    </div>
  );
}

function AuditPanel() {
  const [entries, setEntries] = useState([]);
  const [prefix, setPrefix] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: "200" });
    if (prefix.trim()) params.set("action_prefix", prefix.trim());
    api.get(`/audit?${params}`)
      .then((r) => setEntries(r.data))
      .finally(() => setLoading(false));
  }, [prefix]);

  return (
    <div className="card p-5" data-testid="audit-panel">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="label">Recent activity</span>
        <input
          className="input-field text-xs max-w-xs"
          placeholder="Filter by action prefix (e.g. governance.)"
          value={prefix}
          onChange={(e) => setPrefix(e.target.value)}
          data-testid="audit-prefix-filter"
        />
      </div>
      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-3">Loading…</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-[#5C6B6B] mt-3">No entries match.</p>
      ) : (
        <ul className="mt-3 divide-y divide-[#E5E1D8] text-sm" data-testid="audit-entries">
          {entries.map((e) => (
            <li key={e.id} className="py-2 flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-mono text-[11px] text-[#476B6B]">{e.action}</p>
                <p className="text-xs text-[#5C6B6B] mt-0.5">
                  {e.actor_name || e.actor_id || "system"}
                  {e.target_id && <> → {e.target_type}/{e.target_id.slice(0, 8)}…</>}
                </p>
              </div>
              <span className="text-[10px] text-[#5C6B6B] shrink-0">{fmt(e.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
