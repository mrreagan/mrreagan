/**
 * AdminUserActivity — full user + admin trace audit view.
 * URL: /admin/user-activity  (admin-only; counsel role blocked)
 *
 * Combines security events (Tier 1) with admin URL trace (Tier 2) and
 * exposes filters for user, category, event type, and date range.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, RefreshCw, Filter } from "lucide-react";
import api from "../lib/api";
import { toast } from "sonner";

const CATEGORIES = ["auth", "security", "signing", "payment", "admin_trace", "admin_action", "account"];

function StatusPill({ code }) {
  if (code == null) return <span className="text-xs text-[#5C6B6B]">—</span>;
  const cls =
    code >= 500 ? "bg-[#F9E5E1] text-[#8B0000]" :
    code >= 400 ? "bg-[#FBF3E4] text-[#8B4513]" :
    code >= 300 ? "bg-[#EDEDED] text-[#5C6B6B]" :
    "bg-[#E5F0E8] text-[#01784E]";
  return (
    <span className={`inline-flex text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full ${cls}`}>
      {code}
    </span>
  );
}

export default function AdminUserActivity() {
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ email: "", category: "", event_type: "", limit: 300 });

  const load = async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ limit: String(filters.limit) });
      if (filters.email) qs.set("email", filters.email);
      if (filters.category) qs.set("category", filters.category);
      if (filters.event_type) qs.set("event_type", filters.event_type);
      const [eRes, sRes] = await Promise.all([
        api.get(`/admin/user-activity?${qs.toString()}`),
        api.get("/admin/user-activity/summary"),
      ]);
      setEvents(eRes.data || []);
      setSummary(sRes.data || null);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load activity");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const eventTypes = useMemo(() => {
    if (!summary) return [];
    return summary.top_events.map((e) => e.event_type);
  }, [summary]);

  return (
    <div className="container-page py-12" data-testid="admin-user-activity-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-4">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>

      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <span className="label">Admin · Audit</span>
          <h1 className="editorial-h1 mt-1">User Activity & Admin Trace</h1>
        </div>
        <button onClick={load} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="refresh-btn">
          <RefreshCw size={12} strokeWidth={1.5} /> Refresh
        </button>
      </div>

      <div className="divider-flame" />

      <p className="text-sm text-[#5C6B6B] max-w-3xl leading-relaxed mt-4">
        Tier 1 security events (sign-ins, password resets, sensitive signings, payments) across all users,
        combined with Tier 2 URL traces from every admin session. Counsel accounts are blocked from this view.
        Entries are retained for 365 days on a rolling basis.
      </p>

      {/* Summary */}
      {summary && (
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <p className="label !mt-0">Last 30 days · events</p>
            <p className="font-serif text-3xl text-[#0F2424] mt-1">{summary.total_events.toLocaleString()}</p>
          </div>
          <div className="card p-4">
            <p className="label !mt-0">Users active (30d)</p>
            <p className="font-serif text-3xl text-[#0F2424] mt-1">{summary.per_user.length}</p>
          </div>
          <div className="card p-4">
            <p className="label !mt-0">Top event type (30d)</p>
            <p className="font-serif text-lg text-[#0F2424] mt-1 truncate">
              {summary.top_events[0]?.event_type || "—"}
            </p>
            <p className="text-xs text-[#5C6B6B]">{summary.top_events[0]?.count || 0} occurrences</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mt-8 card p-4 flex flex-wrap items-end gap-3" data-testid="filters">
        <div>
          <label className="text-xs font-semibold text-[#0F2424] block mb-1">Email</label>
          <input
            type="text"
            value={filters.email}
            onChange={(e) => setFilters({ ...filters, email: e.target.value })}
            placeholder="jane@example.com"
            className="input-field text-sm py-1"
            data-testid="filter-email"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-[#0F2424] block mb-1">Category</label>
          <select
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
            className="input-field text-sm py-1"
            data-testid="filter-category"
          >
            <option value="">All</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-[#0F2424] block mb-1">Event type</label>
          <select
            value={filters.event_type}
            onChange={(e) => setFilters({ ...filters, event_type: e.target.value })}
            className="input-field text-sm py-1"
            data-testid="filter-event-type"
          >
            <option value="">All</option>
            {eventTypes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-[#0F2424] block mb-1">Limit</label>
          <select
            value={filters.limit}
            onChange={(e) => setFilters({ ...filters, limit: Number(e.target.value) })}
            className="input-field text-sm py-1"
            data-testid="filter-limit"
          >
            {[100, 300, 500, 1000, 5000].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <button onClick={load} className="btn-primary text-sm inline-flex items-center gap-1" data-testid="apply-filters">
          <Filter size={12} strokeWidth={1.8} /> Apply
        </button>
      </div>

      {/* Per-user summary */}
      {summary && summary.per_user.length > 0 && (
        <div className="mt-8">
          <h2 className="font-serif text-2xl text-[#0F2424] mb-3">Per-user (last 30 days)</h2>
          <div className="card overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-[#F4F1EA] text-xs uppercase tracking-wide text-[#5C6B6B]">
                <tr>
                  <th className="p-3">User</th>
                  <th className="p-3">Role</th>
                  <th className="p-3">Events</th>
                  <th className="p-3">Categories</th>
                  <th className="p-3">Last activity</th>
                </tr>
              </thead>
              <tbody>
                {summary.per_user.slice(0, 30).map((u) => (
                  <tr key={u.email} className="border-b border-[#E8E4DC]" data-testid={`user-row-${u.email}`}>
                    <td className="p-3 text-sm font-semibold">{u.email}</td>
                    <td className="p-3 text-xs uppercase tracking-wider">{u.role || "—"}</td>
                    <td className="p-3 text-sm">{u.events}</td>
                    <td className="p-3 text-xs">
                      {Object.entries(u.categories).map(([k, v]) => (
                        <span key={k} className="inline-block mr-2">
                          <span className="font-mono text-[#476B6B]">{k}</span>: {v}
                        </span>
                      ))}
                    </td>
                    <td className="p-3 text-xs text-[#5C6B6B]">
                      {u.last_at ? new Date(u.last_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Full log */}
      <div className="mt-10">
        <h2 className="font-serif text-2xl text-[#0F2424] mb-3">Recent events</h2>
        <div className="card overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-[#F4F1EA] text-xs uppercase tracking-wide text-[#5C6B6B]">
              <tr>
                <th className="p-3">Time (UTC)</th>
                <th className="p-3">User</th>
                <th className="p-3">Event</th>
                <th className="p-3">Category</th>
                <th className="p-3">Path / status</th>
                <th className="p-3">IP</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="p-6 text-sm text-[#5C6B6B] text-center">Loading…</td></tr>
              ) : (
                <>
                  {events.map((e) => (
                    <tr key={e.id} className="border-b border-[#E8E4DC]" data-testid={`event-row-${e.id}`}>
                      <td className="p-3 text-xs font-mono text-[#5C6B6B] whitespace-nowrap">
                        {e.timestamp ? new Date(e.timestamp).toISOString().slice(0, 19).replace("T", " ") : ""}
                      </td>
                      <td className="p-3 text-xs">{e.email || "(anon)"}</td>
                      <td className="p-3 text-xs font-mono">{e.event_type}</td>
                      <td className="p-3 text-xs uppercase tracking-wider">{e.category}</td>
                      <td className="p-3 text-xs">
                        <div className="font-mono text-[#0F2424] truncate max-w-md">{e.path || "—"}</div>
                        <div className="mt-1"><StatusPill code={e.status_code} /></div>
                      </td>
                      <td className="p-3 text-[10px] font-mono text-[#5C6B6B]">{e.ip || "?"}</td>
                    </tr>
                  ))}
                  {events.length === 0 && (
                    <tr><td colSpan={6} className="p-6 text-sm text-[#5C6B6B] text-center">No events match filters.</td></tr>
                  )}
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
