import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { RotateCcw, AlertTriangle, X, Search } from "lucide-react";
import api from "../lib/api";
import Explainer from "../components/Explainer";

export default function AdminRefunds() {
  const [cascades, setCascades] = useState([]);
  const [clawbacks, setClawbacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("cascades");

  const [refundOpen, setRefundOpen] = useState(false);
  const [txnId, setTxnId] = useState("");
  const [selectedTxn, setSelectedTxn] = useState(null);
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
      toast.error("Pick a transaction and write a reason (≥ 5 chars)");
      return;
    }
    setBusy(true);
    try {
      await api.post("/admin/refunds", { txn_id: txnId.trim(), reason: reason.trim(), skip_stripe: skipStripe });
      toast.success("Refund cascade fired");
      closeRefundModal();
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Cascade failed");
    } finally {
      setBusy(false);
    }
  };

  const closeRefundModal = () => {
    setRefundOpen(false);
    setTxnId(""); setReason(""); setSkipStripe(false); setSelectedTxn(null);
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
        <RotateCcw size={28} strokeWidth={1.2} /> Refund cascades <Explainer id="refunds.page" size={16} />
      </h1>
      <div className="divider-flame" />

      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div className="flex gap-2" data-testid="refund-tabs">
          {[
            { v: "cascades",  label: `Cascades (${cascades.length})`, hint: "refunds.cascades" },
            { v: "clawbacks", label: `Pending clawbacks (${clawbacks.filter((c) => c.status === "pending_recovery").length})`, hint: "refunds.clawbacks_pending" },
          ].map((t) => (
            <div key={t.v} className="inline-flex items-center gap-1">
              <button
                onClick={() => setTab(t.v)}
                className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                  tab === t.v ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8] hover:border-[#476B6B]"
                }`}
                data-testid={`refund-tab-${t.v}`}
              >
                {t.label}
              </button>
              <Explainer id={t.hint} size={11} />
            </div>
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
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 overflow-y-auto" data-testid="refund-modal">
          <div className="bg-white rounded shadow-xl max-w-3xl w-full p-6 my-8">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif text-xl inline-flex items-center gap-2">
                <AlertTriangle size={18} strokeWidth={1.5} className="text-[#9E3C3C]" /> Fire refund cascade
              </h3>
              <button onClick={closeRefundModal} className="text-[#5C6B6B] hover:text-[#1A2424]" aria-label="Close">
                <X size={16} strokeWidth={1.5} />
              </button>
            </div>
            <p className="text-sm text-[#5C6B6B]">
              This refunds the Stripe charge AND undoes its side-effects (registrations, subs, featured slots, promotions)
              AND reverses derived partner credits. Already-paid credits will go to the pending-clawback queue.
            </p>

            <TransactionPicker
              onSelect={(t) => { setTxnId(t.id); setSelectedTxn(t); }}
              selectedId={txnId}
            />

            <label className="block mt-4 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Selected transaction</label>
            {selectedTxn ? (
              <div className="border border-[#476B6B] rounded p-3 bg-[#FAF8F5] text-sm" data-testid="selected-txn">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium capitalize">{selectedTxn.type?.replace(/_/g, " ")} · ${selectedTxn.amount.toFixed(2)}</p>
                    <p className="text-xs text-[#5C6B6B]">{selectedTxn.user_email || "(no email)"} · {new Date(selectedTxn.created_at).toLocaleDateString()}</p>
                    <p className="text-[10px] font-mono text-[#5C6B6B] truncate">{selectedTxn.id}</p>
                  </div>
                  <button onClick={() => { setSelectedTxn(null); setTxnId(""); }} className="text-xs text-[#9E3C3C] hover:underline shrink-0" data-testid="clear-selected-txn">
                    Clear
                  </button>
                </div>
              </div>
            ) : (
              <details className="text-xs text-[#5C6B6B] mt-1" data-testid="paste-id-details">
                <summary className="cursor-pointer hover:text-[#1A2424]">Or paste a transaction ID directly</summary>
                <input
                  value={txnId}
                  onChange={(e) => { setTxnId(e.target.value); setSelectedTxn(null); }}
                  className="input-field text-sm w-full font-mono mt-2"
                  placeholder="payment_transactions.id"
                  data-testid="refund-txn-id"
                />
              </details>
            )}

            <label className="block mt-4 text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Reason</label>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} className="input-field text-sm w-full" rows={3} placeholder="Audit-logged" data-testid="refund-reason" />
            <label className="flex items-center gap-2 mt-3 text-sm">
              <input type="checkbox" checked={skipStripe} onChange={(e) => setSkipStripe(e.target.checked)} data-testid="refund-skip-stripe" />
              Skip Stripe call (use for comp'd or already-out-of-band-refunded charges)
            </label>
            <div className="flex gap-2 mt-5">
              <button onClick={fireCascade} disabled={busy || !txnId} className="btn-primary text-xs bg-[#9E3C3C] hover:bg-[#7E2C2C] disabled:opacity-50" data-testid="refund-confirm">
                {busy ? "Firing…" : "Confirm cascade"}
              </button>
              <button onClick={closeRefundModal} className="btn-outline text-xs">Cancel</button>
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


function TransactionPicker({ onSelect, selectedId }) {
  const [data, setData] = useState(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const params = { limit: 50 };
      if (typeFilter !== "all") params.txn_type = typeFilter;
      if (q.trim().length >= 2) params.q = q.trim();
      const r = await api.get("/admin/refunds/refundable-transactions", { params });
      setData(r.data);
    } catch {
      toast.error("Couldn't load transactions");
    } finally {
      setLoading(false);
    }
  };

  // Reload on type-filter changes; debounce search input.
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [typeFilter]);
  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line
  }, [q]);

  const counts = data?.type_counts || {};
  const typeOptions = [
    { v: "all",                 label: "All" },
    { v: "workshop",            label: "Workshop" },
    { v: "order",               label: "Merch order" },
    { v: "subscription",        label: "Subscription" },
    { v: "featured_slot",       label: "Featured slot" },
    { v: "research_promotion",  label: "Research promo" },
    { v: "sponsorship",         label: "Sponsorship" },
    { v: "donation",            label: "Donation" },
    { v: "ai_wallet_topup",     label: "AI top-up" },
  ];

  return (
    <div className="mt-5 border border-[#E5E1D8] rounded p-3 bg-[#FAF8F5]" data-testid="txn-picker">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
        <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">Pick a transaction to refund</p>
        <p className="text-[10px] text-[#5C6B6B]">{data?.total ?? "—"} refundable in total</p>
      </div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {typeOptions.map((t) => (
          <button
            key={t.v}
            onClick={() => setTypeFilter(t.v)}
            className={`px-2.5 py-1 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              typeFilter === t.v ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8] hover:border-[#476B6B] text-[#5C6B6B]"
            }`}
            data-testid={`txn-type-${t.v}`}
          >
            {t.label}{counts[t.v] != null && t.v !== "all" ? ` (${counts[t.v]})` : ""}
          </button>
        ))}
      </div>
      <div className="relative">
        <Search size={12} strokeWidth={1.6} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by email, name, or ID…"
          className="input-field text-xs w-full pl-7"
          data-testid="txn-picker-search"
        />
      </div>
      <div className="mt-2 max-h-64 overflow-y-auto border border-[#E5E1D8] rounded bg-white">
        {loading ? (
          <p className="text-xs text-[#5C6B6B] p-3">Loading…</p>
        ) : (data?.transactions || []).length === 0 ? (
          <p className="text-xs text-[#5C6B6B] italic p-3" data-testid="txn-picker-empty">No refundable transactions match.</p>
        ) : (
          <ul className="divide-y divide-[#E5E1D8]">
            {data.transactions.map((t) => {
              const active = t.id === selectedId;
              return (
                <li key={t.id}>
                  <button
                    onClick={() => onSelect(t)}
                    className={`w-full text-left px-3 py-2 hover:bg-[#FAF8F5] transition flex items-center gap-3 ${active ? "bg-[#E5F0EA]" : ""}`}
                    data-testid={`txn-picker-row-${t.id}`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2 flex-wrap">
                        <span className="text-xs font-medium capitalize text-[#1A2424]">{(t.type || "").replace(/_/g, " ")}</span>
                        <span className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{t.payment_status}</span>
                        <span className="text-[10px] text-[#5C6B6B]">{new Date(t.created_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-[11px] text-[#5C6B6B] truncate">{t.user_email || "(no user)"}{t.user_name ? ` — ${t.user_name}` : ""}</p>
                    </div>
                    <span className="text-sm font-medium text-[#1A2424] shrink-0">${t.amount.toFixed(2)}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
