/**
 * CounselActivityLog — admin-only audit trail for counsel (readonly_admin)
 * users. Shows a summary per-counsel plus the full request-by-request log.
 *
 * URL: /admin/counsel-activity
 * Counsel accounts are blocked by backend from viewing this page even though
 * they can reach admin routes — the endpoint returns 403 for readonly_admin.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, RefreshCw, Trash2, Shield } from "lucide-react";
import api from "../lib/api";
import { toast } from "sonner";

function StatusPill({ code }) {
  const cls =
    code >= 500 ? "bg-[#F9E5E1] text-[#8B0000]"
    : code >= 400 ? "bg-[#FBF3E4] text-[#8B4513]"
    : code >= 300 ? "bg-[#EDEDED] text-[#5C6B6B]"
    : "bg-[#E5F0E8] text-[#01784E]";
  return (
    <span className={`inline-flex text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full ${cls}`}>
      {code}
    </span>
  );
}

export default function CounselActivityLog() {
  const [entries, setEntries] = useState([]);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(200);

  const load = async () => {
    setLoading(true);
    try {
      const [aRes, sRes] = await Promise.all([
        api.get(`/admin/counsel/activity?limit=${limit}`),
        api.get("/admin/counsel/activity/summary"),
      ]);
      setEntries(aRes.data || []);
      setSummary(sRes.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load activity log");
    } finally {
      setLoading(false);
    }
  };

  const clearLog = async () => {
    if (!window.confirm("Purge the entire counsel activity log? This cannot be undone.")) return;
    try {
      const { data } = await api.delete("/admin/counsel/activity");
      toast.success(`Cleared ${data.deleted} log entries.`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Clear failed");
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [limit]);

  return (
    <div className="container-page py-12" data-testid="counsel-activity-log-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-4">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>

      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <span className="label">Admin · Audit</span>
          <h1 className="editorial-h1 mt-1">Counsel Activity Log</h1>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="refresh-btn">
            <RefreshCw size={12} strokeWidth={1.5} /> Refresh
          </button>
          <button onClick={clearLog} className="text-xs text-red-700 border border-red-200 rounded px-3 py-1 hover:bg-red-50 inline-flex items-center gap-1" data-testid="clear-log-btn">
            <Trash2 size={12} strokeWidth={1.5} /> Purge log
          </button>
        </div>
      </div>

      <div className="divider-flame" />

      <div className="mt-4 flex items-start gap-2 text-xs text-[#8B4513] bg-[#FBF3E4] border border-[#E5D7B3] rounded-md px-3 py-2 max-w-3xl">
        <Shield size={14} strokeWidth={1.5} className="mt-0.5 shrink-0" />
        <span>
          <strong>Admin-only.</strong> Counsel accounts (role <code className="font-mono">readonly_admin</code>) are blocked from viewing this page — the backend endpoint returns HTTP 403 for their token. This protects the audit trail from tampering by a compromised counsel session.
        </span>
      </div>

      {/* Per-counsel summary */}
      <section className="mt-8" data-testid="summary-section">
        <h2 className="font-serif text-2xl text-[#0F2424] mb-3">Per-counsel summary</h2>
        <div className="card overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-[#F4F1EA] text-xs uppercase tracking-wide text-[#5C6B6B]">
              <tr>
                <th className="p-3">Counsel email</th>
                <th className="p-3">Requests</th>
                <th className="p-3">GET reads</th>
                <th className="p-3">Blocked writes</th>
                <th className="p-3">Unique URLs</th>
                <th className="p-3">Last activity</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((s) => (
                <tr key={s.email} className="border-b border-[#E8E4DC]" data-testid={`summary-row-${s.email}`}>
                  <td className="p-3 text-sm font-semibold text-[#0F2424]">{s.email || "(unknown)"}</td>
                  <td className="p-3 text-sm">{s.total_requests}</td>
                  <td className="p-3 text-sm">{s.read_count}</td>
                  <td className="p-3 text-sm">
                    {s.blocked_writes > 0
                      ? <span className="text-[#8B0000] font-semibold">{s.blocked_writes}</span>
                      : <span className="text-[#5C6B6B]">0</span>}
                  </td>
                  <td className="p-3 text-sm">{s.unique_path_count}</td>
                  <td className="p-3 text-xs text-[#5C6B6B]">
                    {s.last_activity_at ? new Date(s.last_activity_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
              {summary.length === 0 && (
                <tr><td colSpan={6} className="p-6 text-sm text-[#5C6B6B] text-center">No counsel activity yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Full log */}
      <section className="mt-10" data-testid="full-log-section">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="font-serif text-2xl text-[#0F2424]">Full request log</h2>
          <div className="text-xs text-[#5C6B6B]">
            Showing latest{" "}
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="input-field text-xs py-0.5 px-1 inline-block w-auto"
              data-testid="limit-selector"
            >
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
              <option value={2000}>2000</option>
            </select>
          </div>
        </div>
        <div className="card overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-[#F4F1EA] text-xs uppercase tracking-wide text-[#5C6B6B]">
              <tr>
                <th className="p-3">Time (UTC)</th>
                <th className="p-3">Counsel</th>
                <th className="p-3">Method</th>
                <th className="p-3">Path</th>
                <th className="p-3">Status</th>
                <th className="p-3">Client</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="p-6 text-sm text-[#5C6B6B] text-center">Loading…</td></tr>
              ) : (
                <>
                  {entries.map((e) => (
                    <tr key={e.id} className="border-b border-[#E8E4DC]" data-testid={`log-row-${e.id}`}>
                      <td className="p-3 text-xs font-mono text-[#5C6B6B]">
                        {e.timestamp ? new Date(e.timestamp).toISOString().slice(0, 19).replace("T", " ") : ""}
                      </td>
                      <td className="p-3 text-xs">{e.email || "(unknown)"}</td>
                      <td className="p-3 text-xs font-mono">{e.method}</td>
                      <td className="p-3 text-xs font-mono text-[#0F2424]">{e.path}</td>
                      <td className="p-3"><StatusPill code={e.status_code} /></td>
                      <td className="p-3 text-[10px] text-[#5C6B6B] font-mono">
                        {e.ip || "?"}
                      </td>
                    </tr>
                  ))}
                  {entries.length === 0 && (
                    <tr><td colSpan={6} className="p-6 text-sm text-[#5C6B6B] text-center">No log entries.</td></tr>
                  )}
                </>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
