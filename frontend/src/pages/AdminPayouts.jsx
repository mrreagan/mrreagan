import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api, { API } from "../lib/api";
import { CheckCircle2, Wallet, Calendar, Download, ShieldCheck, ShieldAlert } from "lucide-react";

function fmtUSD(n) {
  return `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function AdminPayouts() {
  const [summary, setSummary] = useState([]);
  const [referrals, setReferrals] = useState([]);
  const [tab, setTab] = useState("earned");
  const [loading, setLoading] = useState(true);
  const [readyData, setReadyData] = useState(null);
  const [readyLoading, setReadyLoading] = useState(false);
  const [settings, setSettings] = useState({ next_disbursement_date: "", cadence: "monthly", notes: "" });
  const [savingSettings, setSavingSettings] = useState(false);

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

  const loadDisbursement = () => {
    setReadyLoading(true);
    Promise.all([
      api.get("/admin/payouts/ready-to-pay"),
      api.get("/admin/payouts/disbursement-settings"),
    ])
      .then(([rdy, sett]) => {
        setReadyData(rdy.data);
        setSettings({
          next_disbursement_date: sett.data.next_disbursement_date || "",
          cadence: sett.data.cadence || "monthly",
          notes: sett.data.notes || "",
        });
      })
      .finally(() => setReadyLoading(false));
  };
  useEffect(() => { loadDisbursement(); }, []);

  const saveSettings = async () => {
    setSavingSettings(true);
    try {
      await api.put("/admin/payouts/disbursement-settings", settings);
      toast.success("Disbursement settings saved");
    } catch (e) {
      toast.error("Could not save");
    } finally {
      setSavingSettings(false);
    }
  };

  const downloadCsv = () => {
    // GET ready-to-pay with format=csv requires auth cookie; open in new tab
    const url = `${API}/admin/payouts/ready-to-pay?format=csv`;
    window.open(url, "_blank");
  };

  return (
    <div className="container-page py-12" data-testid="admin-payouts-page">
      <span className="label">Admin · Partner payouts</span>
      <h1 className="editorial-h1 mt-2">Referral payouts & disbursements</h1>
      <div className="divider-flame" />

      {/* Disbursement orchestration */}
      <section className="card p-6" data-testid="disbursement-settings-section">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><Calendar size={16} strokeWidth={1.5} /> Next disbursement</h2>
        <div className="grid md:grid-cols-3 gap-3 mt-4">
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Next disbursement date</label>
            <input
              type="date"
              value={settings.next_disbursement_date || ""}
              onChange={(e) => setSettings({ ...settings, next_disbursement_date: e.target.value })}
              className="input-field text-sm w-full"
              data-testid="disbursement-date-input"
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Cadence</label>
            <select
              value={settings.cadence || "monthly"}
              onChange={(e) => setSettings({ ...settings, cadence: e.target.value })}
              className="input-field text-sm w-full"
              data-testid="disbursement-cadence-select"
            >
              <option value="weekly">Weekly</option>
              <option value="biweekly">Bi-weekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="adhoc">Ad hoc</option>
            </select>
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Notes (partner visible)</label>
            <input
              value={settings.notes || ""}
              onChange={(e) => setSettings({ ...settings, notes: e.target.value })}
              className="input-field text-sm w-full"
              placeholder="e.g. ACH transfers take 3 business days"
              data-testid="disbursement-notes-input"
            />
          </div>
        </div>
        <button
          onClick={saveSettings}
          disabled={savingSettings}
          className="btn-primary text-xs mt-4"
          data-testid="save-disbursement-settings"
        >
          {savingSettings ? "Saving…" : "Save settings"}
        </button>
      </section>

      {/* Ready to pay */}
      <section className="mt-8" data-testid="ready-to-pay-section">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="font-serif text-xl inline-flex items-center gap-2">
            <Wallet size={16} strokeWidth={1.5} /> Ready to pay
          </h2>
          <button
            onClick={downloadCsv}
            className="btn-outline text-xs inline-flex items-center gap-1"
            data-testid="export-disbursement-csv"
          >
            <Download size={12} strokeWidth={1.5} /> Export CSV
          </button>
        </div>
        {readyLoading || !readyData ? (
          <p className="text-sm text-[#5C6B6B] mt-3">Loading…</p>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
              <Stat label="Ready partners" value={readyData.ready_count} testid="stat-ready-count" />
              <Stat label="Ready total" value={fmtUSD(readyData.ready_total_usd)} testid="stat-ready-total" emphasis="positive" />
              <Stat label="Blocked credits" value={readyData.blocked_count} testid="stat-blocked-count" />
              <Stat label="Blocked total" value={fmtUSD(readyData.blocked_total_usd)} testid="stat-blocked-total" />
            </div>

            {readyData.ready.length > 0 && (
              <div className="mt-5">
                <p className="text-[10px] uppercase tracking-wider text-[#2E5C46] mb-2 inline-flex items-center gap-1">
                  <ShieldCheck size={11} strokeWidth={1.5} /> Ready ({readyData.ready.length})
                </p>
                <ReadyTable rows={readyData.ready} testid="ready-table" tone="ready" />
              </div>
            )}
            {readyData.blocked.length > 0 && (
              <div className="mt-6">
                <p className="text-[10px] uppercase tracking-wider text-[#C9A961] mb-2 inline-flex items-center gap-1">
                  <ShieldAlert size={11} strokeWidth={1.5} /> Blocked — partner missing W9 or payout method ({readyData.blocked.length})
                </p>
                <ReadyTable rows={readyData.blocked} testid="blocked-table" tone="blocked" />
              </div>
            )}
            {readyData.ready.length === 0 && readyData.blocked.length === 0 && (
              <p className="text-sm text-[#5C6B6B] mt-3">No earned credits awaiting disbursement.</p>
            )}
          </>
        )}
      </section>

      <section className="mt-10" data-testid="payout-by-partner">
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

function Stat({ label, value, testid, emphasis }) {
  const color = emphasis === "positive" ? "text-[#2E5C46]" : "text-[#1A2424]";
  return (
    <div className="card p-4" data-testid={testid}>
      <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{label}</p>
      <p className={`font-serif text-xl mt-1 ${color}`}>{value}</p>
    </div>
  );
}

function ReadyTable({ rows, testid, tone }) {
  return (
    <table className="w-full text-sm card" data-testid={testid}>
      <thead>
        <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
          <th className="text-left px-4 py-2">Partner</th>
          <th className="text-left px-4 py-2">Source</th>
          <th className="text-right px-4 py-2">Amount</th>
          <th className="text-left px-4 py-2">Method</th>
          {tone === "blocked" && <th className="text-left px-4 py-2">Missing</th>}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.credit_id} className="border-t border-[#E5E1D8]" data-testid={`${tone}-row-${r.credit_id}`}>
            <td className="px-4 py-3">
              <p className="font-medium">{r.partner_name || "(unnamed)"}</p>
              <p className="text-[10px] text-[#5C6B6B]">{r.partner_email}</p>
            </td>
            <td className="px-4 py-3 text-xs">{r.source}</td>
            <td className="px-4 py-3 text-right font-medium">${(r.amount_usd || 0).toFixed(2)}</td>
            <td className="px-4 py-3 text-xs">{r.method_type || "—"}</td>
            {tone === "blocked" && (
              <td className="px-4 py-3 text-[10px] text-[#C9A961]">
                {!r.w9_on_file && <span>W9</span>}
                {!r.w9_on_file && !r.method_on_file && <span> · </span>}
                {!r.method_on_file && <span>Payout method</span>}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
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
