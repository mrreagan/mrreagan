import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, X, AlertTriangle, Filter } from "lucide-react";
import api from "../lib/api";

const STATUS_PILLS = {
  active:     { label: "Active",     cls: "bg-[#E8F0EA] text-[#2E5C46]" },
  cancelled:  { label: "Cancelling", cls: "bg-[#FDF1E8] text-[#B86A5C]" },
  superseded: { label: "Superseded", cls: "bg-[#F2EEE7] text-[#5C6B6B]" },
  expired:    { label: "Expired",    cls: "bg-[#F2EEE7] text-[#5C6B6B]" },
  revoked:    { label: "Revoked",    cls: "bg-[#F5DDDD] text-[#9E3C3C]" },
};

export default function AdminSubscriptions() {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [loading, setLoading] = useState(true);
  const [revokingId, setRevokingId] = useState(null);
  const [revokeReason, setRevokeReason] = useState("");
  const [refund, setRefund] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (type) params.set("partner_type", type);
    api.get(`/admin/subscriptions?${params.toString()}`)
      .then((r) => setRows(r.data))
      .catch(() => toast.error("Could not load subscriptions"))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [status, type]);

  const confirmRevoke = async () => {
    if (!revokingId || revokeReason.trim().length < 3) {
      toast.error("Reason required (≥ 3 chars)");
      return;
    }
    setBusy(true);
    try {
      await api.post(`/admin/subscriptions/${revokingId}/revoke`, {
        reason: revokeReason.trim(),
        refund,
      });
      toast.success(refund ? "Subscription revoked + refund issued" : "Subscription revoked");
      setRevokingId(null); setRevokeReason(""); setRefund(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Revoke failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-subscriptions-page">
      <span className="label">Admin · Subscriptions</span>
      <h1 className="editorial-h1 mt-2">Partner subscriptions</h1>
      <div className="divider-flame" />

      <div className="flex flex-wrap gap-3 items-end mt-2" data-testid="admin-sub-filters">
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Status</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="input-field text-sm" data-testid="filter-status">
            <option value="">All</option>
            {Object.keys(STATUS_PILLS).map((s) => <option key={s} value={s}>{STATUS_PILLS[s].label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Partner type</label>
          <select value={type} onChange={(e) => setType(e.target.value)} className="input-field text-sm" data-testid="filter-type">
            <option value="">All</option>
            <option value="facilitator">Facilitator</option>
            <option value="community">Community</option>
            <option value="research">Research</option>
            <option value="vendor">Vendor</option>
          </select>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-6">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-[#5C6B6B] mt-6">No subscriptions match these filters.</p>
      ) : (
        <table className="w-full text-sm card mt-6" data-testid="admin-sub-table">
          <thead className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
            <tr>
              <th className="text-left px-4 py-2">Partner</th>
              <th className="text-left px-4 py-2">Plan</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Started</th>
              <th className="text-left px-4 py-2">Expires</th>
              <th className="text-right px-4 py-2">Paid</th>
              <th className="text-right px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const pill = STATUS_PILLS[r.status] || STATUS_PILLS.expired;
              return (
                <tr key={r.id} className="border-t border-[#E5E1D8]" data-testid={`admin-sub-row-${r.id}`}>
                  <td className="px-4 py-3">
                    <p className="font-medium">{r.partner_name || "(unnamed)"}</p>
                    <p className="text-[10px] text-[#5C6B6B]">{r.partner_email} · {r.partner_type}</p>
                  </td>
                  <td className="px-4 py-3 text-xs">{r.plan?.name || r.plan_id}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${pill.cls}`}>
                      {pill.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs">{r.started_at ? new Date(r.started_at).toLocaleDateString() : "—"}</td>
                  <td className="px-4 py-3 text-xs">{r.expires_at ? new Date(r.expires_at).toLocaleDateString() : "—"}</td>
                  <td className="px-4 py-3 text-right">${(r.amount_paid || 0).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    {!["revoked", "superseded"].includes(r.status) && (
                      <button
                        onClick={() => setRevokingId(r.id)}
                        className="text-[10px] uppercase tracking-wider text-[#9E3C3C] hover:underline"
                        data-testid={`revoke-${r.id}`}
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {revokingId && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="revoke-modal">
          <div className="bg-white rounded shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif text-xl inline-flex items-center gap-2">
                <AlertTriangle size={18} strokeWidth={1.5} className="text-[#9E3C3C]" /> Revoke subscription
              </h3>
              <button onClick={() => setRevokingId(null)} className="text-[#5C6B6B] hover:text-[#1A2424]" aria-label="Close">
                <X size={16} strokeWidth={1.5} />
              </button>
            </div>
            <p className="text-sm text-[#5C6B6B]">
              This immediately ends the partner's license. Their profile remains, but rev-share + dashboards lock.
            </p>
            <label className="block mt-4 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Reason (required, audit-logged)</label>
            <textarea
              value={revokeReason}
              onChange={(e) => setRevokeReason(e.target.value)}
              className="input-field text-sm w-full"
              rows={3}
              placeholder="e.g. Agreement v2 not signed; partner unresponsive after 60 days"
              data-testid="revoke-reason"
            />
            <label className="flex items-center gap-2 mt-3 text-sm">
              <input
                type="checkbox"
                checked={refund}
                onChange={(e) => setRefund(e.target.checked)}
                data-testid="revoke-refund-checkbox"
              />
              Also issue full Stripe refund of the original payment
            </label>
            <div className="flex gap-2 mt-5">
              <button onClick={confirmRevoke} disabled={busy} className="btn-primary text-xs bg-[#9E3C3C] hover:bg-[#7E2C2C]" data-testid="confirm-revoke">
                {busy ? "Revoking…" : refund ? "Revoke + refund" : "Revoke"}
              </button>
              <button onClick={() => setRevokingId(null)} className="btn-outline text-xs">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
