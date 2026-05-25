import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { RotateCcw, AlertTriangle, X } from "lucide-react";
import api from "../lib/api";

export default function AdminRefunds() {
  const [cascades, setCascades] = useState([]);
  const [clawbacks, setClawbacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("cascades");

  const [refundOpen, setRefundOpen] = useState(false);
  const [txnId, setTxnId] = useState("");
  const [reason, setReason] = useState("");
  const [skipStripe, setSkipStripe] = useState(false);
  const [busy, setBusy] = useState(false);

  const [resolvingId, setResolvingId] = useState(null);
  const [resolveStatus, setResolveStatus] = useState("recovered");
  const [resolveNote, setResolveNote] = useState("");

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/admin/refunds"),
      api.get("/admin/clawbacks"),
    ])
      .then(([c, cb]) => { setCascades(c.data); setClawbacks(cb.data); })
      .catch(() => toast.error("Could not load"))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const fireCascade = async () => {
    if (!txnId.trim() || reason.trim().length < 5) {
      toast.error("Transaction ID and reason (≥ 5 chars) required");
      return;
    }
    setBusy(true);
    try {
      await api.post("/admin/refunds", { txn_id: txnId.trim(), reason: reason.trim(), skip_stripe: skipStripe });
      toast.success("Refund cascade fired");
      setRefundOpen(false); setTxnId(""); setReason(""); setSkipStripe(false);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Cascade failed");
    } finally {
      setBusy(false);
    }
  };

  const resolveClawback = async () => {
    if (resolveNote.trim().length < 3) { toast.error("Note required"); return; }
    setBusy(true);
    try {
      await api.post(`/admin/clawbacks/${resolvingId}/resolve`, { status: resolveStatus, note: resolveNote.trim() });
      toast.success("Resolved");
      setResolvingId(null); setResolveNote(""); setResolveStatus("recovered");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-refunds-page">
      <span className="label">Admin · Refunds & Clawbacks</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <RotateCcw size={28} strokeWidth={1.2} /> Refund cascades
      </h1>
      <div className="divider-flame" />

      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div className="flex gap-2" data-testid="refund-tabs">
          {[
            { v: "cascades",  label: `Cascades (${cascades.length})` },
            { v: "clawbacks", label: `Pending clawbacks (${clawbacks.filter((c) => c.status === "pending_recovery").length})` },
          ].map((t) => (
            <button
              key={t.v}
              onClick={() => setTab(t.v)}
              className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                tab === t.v ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`refund-tab-${t.v}`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <button onClick={() => setRefundOpen(true)} className="btn-primary text-xs" data-testid="open-refund-modal">
          Fire refund cascade
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-[#5C6B6B]">Loading…</p>
      ) : tab === "cascades" ? (
        cascades.length === 0 ? (
          <p className="text-sm text-[#5C6B6B]">No refund cascades yet.</p>
        ) : (
          <table className="w-full text-sm card" data-testid="cascades-table">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
                <th className="text-left px-4 py-2">When</th>
                <th className="text-left px-4 py-2">Type</th>
                <th className="text-right px-4 py-2">Amount</th>
                <th className="text-left px-4 py-2">By</th>
                <th className="text-left px-4 py-2">Stripe</th>
                <th className="text-right px-4 py-2">Reversed credits</th>
                <th className="text-right px-4 py-2">Paid clawback $</th>
              </tr>
            </thead>
            <tbody>
              {cascades.map((c) => (
                <tr key={c.id} className="border-t border-[#E5E1D8]" data-testid={`cascade-row-${c.id}`}>
                  <td className="px-4 py-3 text-xs">{new Date(c.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-xs">{c.txn_type}</td>
                  <td className="px-4 py-3 text-right">${(c.txn_amount || 0).toFixed(2)}</td>
                  <td className="px-4 py-3 text-xs">{c.actor_name}</td>
                  <td className="px-4 py-3 text-[10px] uppercase tracking-wider text-[#5C6B6B]">{c.stripe_refund?.status}</td>
                  <td className="px-4 py-3 text-right">{c.credit_clawback?.reversed_count || 0}</td>
                  <td className="px-4 py-3 text-right text-[#9E3C3C]">${(c.credit_clawback?.paid_clawback_total_usd || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      ) : (
        clawbacks.length === 0 ? (
          <p className="text-sm text-[#5C6B6B]">No clawbacks.</p>
        ) : (
          <ul className="card divide-y divide-[#E5E1D8]" data-testid="clawbacks-list">
            {clawbacks.map((cb) => (
              <li key={cb.id} className="py-4 px-4 flex items-center gap-3" data-testid={`clawback-row-${cb.id}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium">{cb.partner_name || "(unnamed)"}</p>
                    <span className="text-[10px] uppercase tracking-wider text-[#C9A961]">{cb.source}</span>
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded ${
                      cb.status === "pending_recovery" ? "bg-[#FFF8E1] text-[#8B7128]" :
                      cb.status === "recovered" ? "bg-[#E8F0EA] text-[#2E5C46]" : "bg-[#F2EEE7] text-[#5C6B6B]"
                    }`}>
                      {cb.status.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-xs text-[#5C6B6B]">{cb.partner_email}</p>
                  <p className="text-[10px] text-[#5C6B6B]">Original txn {cb.original_payment_session_id}</p>
                </div>
                <p className="text-sm font-medium">${(cb.amount_usd || 0).toFixed(2)}</p>
                {cb.status === "pending_recovery" && (
                  <button onClick={() => setResolvingId(cb.id)} className="btn-outline text-xs" data-testid={`resolve-clawback-${cb.id}`}>
                    Resolve
                  </button>
                )}
              </li>
            ))}
          </ul>
        )
      )}

      {refundOpen && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="refund-modal">
          <div className="bg-white rounded shadow-xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif text-xl inline-flex items-center gap-2">
                <AlertTriangle size={18} strokeWidth={1.5} className="text-[#9E3C3C]" /> Fire refund cascade
              </h3>
              <button onClick={() => setRefundOpen(false)} className="text-[#5C6B6B] hover:text-[#1A2424]" aria-label="Close">
                <X size={16} strokeWidth={1.5} />
              </button>
            </div>
            <p className="text-sm text-[#5C6B6B]">
              This refunds the Stripe charge AND undoes its side-effects (registrations, subs, featured slots, promotions)
              AND reverses derived partner credits. Already-paid credits will go to the pending-clawback queue.
            </p>
            <label className="block mt-4 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Payment transaction ID</label>
            <input value={txnId} onChange={(e) => setTxnId(e.target.value)} className="input-field text-sm w-full font-mono" placeholder="payment_transactions.id" data-testid="refund-txn-id" />
            <label className="block mt-3 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Reason</label>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} className="input-field text-sm w-full" rows={3} placeholder="Audit-logged" data-testid="refund-reason" />
            <label className="flex items-center gap-2 mt-3 text-sm">
              <input type="checkbox" checked={skipStripe} onChange={(e) => setSkipStripe(e.target.checked)} data-testid="refund-skip-stripe" />
              Skip Stripe call (use for comp'd or already-out-of-band-refunded charges)
            </label>
            <div className="flex gap-2 mt-5">
              <button onClick={fireCascade} disabled={busy} className="btn-primary text-xs bg-[#9E3C3C] hover:bg-[#7E2C2C]" data-testid="refund-confirm">
                {busy ? "Firing…" : "Confirm cascade"}
              </button>
              <button onClick={() => setRefundOpen(false)} className="btn-outline text-xs">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {resolvingId && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="resolve-clawback-modal">
          <div className="bg-white rounded shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif text-xl">Resolve clawback</h3>
              <button onClick={() => setResolvingId(null)} className="text-[#5C6B6B] hover:text-[#1A2424]" aria-label="Close">
                <X size={16} strokeWidth={1.5} />
              </button>
            </div>
            <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Outcome</label>
            <select value={resolveStatus} onChange={(e) => setResolveStatus(e.target.value)} className="input-field text-sm w-full" data-testid="clawback-status-select">
              <option value="recovered">Recovered (partner returned funds)</option>
              <option value="written_off">Written off</option>
            </select>
            <label className="block mt-3 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Note</label>
            <textarea value={resolveNote} onChange={(e) => setResolveNote(e.target.value)} className="input-field text-sm w-full" rows={3} data-testid="clawback-resolve-note" />
            <div className="flex gap-2 mt-4">
              <button onClick={resolveClawback} disabled={busy} className="btn-primary text-xs" data-testid="clawback-resolve-confirm">
                {busy ? "…" : "Confirm"}
              </button>
              <button onClick={() => setResolvingId(null)} className="btn-outline text-xs">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
