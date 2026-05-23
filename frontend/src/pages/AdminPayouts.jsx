import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { CheckCircle2, Wallet } from "lucide-react";

function fmtUSD(n) {
  return `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function AdminPayouts() {
  const [summary, setSummary] = useState([]);
  const [referrals, setReferrals] = useState([]);
  const [tab, setTab] = useState("earned");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/admin/referrals/payout-summary"),
      api.get(`/admin/referrals?status=${tab}&limit=500`),
    ])
      .then(([s, r]) => { setSummary(s.data); setReferrals(r.data); })
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [tab]);

  return (
    <div className="container-page py-12" data-testid="admin-payouts-page">
      <span className="label">Admin · Partner payouts</span>
      <h1 className="editorial-h1 mt-2">Referral payouts</h1>
      <div className="divider-flame" />

      <section data-testid="payout-by-partner">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><Wallet size={16} strokeWidth={1.5} /> Per-partner liability</h2>
        {summary.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] mt-3">No partner referral activity yet.</p>
        ) : (
          <ul className="mt-4 card divide-y divide-[#E5E1D8]" data-testid="payout-summary-list">
            {summary.map((s) => (
              <li key={s.partner_user_id} className="py-3 px-4 flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="font-medium">{s.partner_name}</p>
                  <p className="text-xs text-[#5C6B6B]">{s.partner_email} · {s.count} attribution{s.count === 1 ? "" : "s"}</p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">Pending {fmtUSD(s.earned)}</p>
                  <p className="text-[10px] uppercase tracking-wider text-[#2E5C46]">Paid {fmtUSD(s.paid)}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10" data-testid="referrals-detail">
        <h2 className="font-serif text-xl">Referral ledger</h2>
        <div className="flex flex-wrap gap-2 mt-4" data-testid="ledger-tabs">
          {["earned", "paid"].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                tab === t ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`ledger-tab-${t}`}
            >
              {t}
            </button>
          ))}
        </div>
        {loading ? (
          <p className="text-sm text-[#5C6B6B] mt-3">Loading…</p>
        ) : referrals.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] mt-3">No {tab} referrals.</p>
        ) : (
          <table className="mt-4 w-full text-sm card" data-testid="referrals-table">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
                <th className="text-left px-4 py-2">Date</th>
                <th className="text-left px-4 py-2">Subject</th>
                <th className="text-right px-4 py-2">Order</th>
                <th className="text-right px-4 py-2">Rate</th>
                <th className="text-right px-4 py-2">Payout</th>
                <th className="text-right px-4 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {referrals.map((r) => <ReferralRow key={r.id} r={r} onPaid={load} />)}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function ReferralRow({ r, onPaid }) {
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ method: "manual", reference: "", note: "" });

  const markPaid = async () => {
    setBusy(true);
    try {
      await api.post(`/admin/referrals/${r.id}/mark-paid`, form);
      toast.success("Marked paid");
      onPaid();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not mark paid");
    } finally { setBusy(false); }
  };

  return (
    <>
      <tr className="border-t border-[#E5E1D8]" data-testid={`referral-row-${r.id}`}>
        <td className="px-4 py-3 text-xs">{new Date(r.earned_at).toLocaleDateString()}</td>
        <td className="px-4 py-3">
          <p className="truncate max-w-xs">{r.subject_label || r.subject_id.slice(0, 8)}</p>
          <p className="text-[10px] text-[#5C6B6B]">{r.subject_type}</p>
        </td>
        <td className="px-4 py-3 text-right">${r.order_total.toFixed(2)}</td>
        <td className="px-4 py-3 text-right">{r.rev_share_pct}%</td>
        <td className="px-4 py-3 text-right font-medium">${r.payout_amount.toFixed(2)}</td>
        <td className="px-4 py-3 text-right">
          {r.status === "earned" ? (
            <button onClick={() => setShowForm((v) => !v)} className="btn-outline text-xs" data-testid={`mark-paid-${r.id}`}>
              Mark paid
            </button>
          ) : (
            <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#2E5C46]">
              <CheckCircle2 size={11} strokeWidth={1.5} /> {new Date(r.paid_at).toLocaleDateString()}
            </span>
          )}
        </td>
      </tr>
      {showForm && (
        <tr data-testid={`mark-paid-form-${r.id}`}>
          <td colSpan={6} className="px-4 py-3 bg-[#FAF8F5] border-t border-[#E5E1D8]">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 items-end">
              <select className="input-field text-xs" value={form.method} onChange={(e) => setForm((f) => ({ ...f, method: e.target.value }))} data-testid={`pay-method-${r.id}`}>
                <option value="manual">Manual</option>
                <option value="check">Check</option>
                <option value="wire">Wire</option>
                <option value="paypal">PayPal</option>
                <option value="stripe_payout">Stripe payout</option>
              </select>
              <input className="input-field text-xs" placeholder="Reference / txn id" value={form.reference} onChange={(e) => setForm((f) => ({ ...f, reference: e.target.value }))} data-testid={`pay-ref-${r.id}`} />
              <input className="input-field text-xs md:col-span-2" placeholder="Note (optional)" value={form.note} onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))} data-testid={`pay-note-${r.id}`} />
            </div>
            <div className="flex gap-2 mt-2">
              <button onClick={markPaid} disabled={busy} className="btn-primary text-xs" data-testid={`confirm-paid-${r.id}`}>{busy ? "Saving…" : "Confirm paid"}</button>
              <button onClick={() => setShowForm(false)} className="btn-outline text-xs">Cancel</button>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
