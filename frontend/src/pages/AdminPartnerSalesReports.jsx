import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { CheckCircle2, AlertCircle, RefreshCw, X, ExternalLink } from "lucide-react";

const STATUSES = ["submitted", "approved", "disputed", "revised"];
const STATUS_COLOR = {
  submitted: "bg-[#C9A961] text-[#1A2424]",
  approved: "bg-[#2E5C46] text-white",
  disputed: "bg-[#9E3C3C] text-white",
  revised: "bg-[#476B6B] text-white",
};

export default function AdminPartnerSalesReports() {
  const [tab, setTab] = useState("submitted");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(null);
  const [form, setForm] = useState({ admin_note: "", override_gross_usd: "", override_pct: "" });

  const load = () => {
    setLoading(true);
    api.get(`/admin/partner-sales-reports?status=${tab}`)
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(load, [tab]);

  const decide = async (decision) => {
    const body = { admin_note: form.admin_note };
    if (form.override_gross_usd !== "") body.override_gross_usd = parseFloat(form.override_gross_usd);
    if (form.override_pct !== "") body.override_pct = parseFloat(form.override_pct);
    try {
      await api.post(`/admin/partner-sales-reports/${open.id}/decision?status=${decision}`, body);
      toast.success(`Report ${decision}d.`);
      setOpen(null);
      setForm({ admin_note: "", override_gross_usd: "", override_pct: "" });
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Update failed.");
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-partner-sales-reports">
      <span className="label">Admin</span>
      <h1 className="editorial-h1 mt-2">Partner off-site sales reports</h1>
      <p className="text-sm text-[#5C6B6B] mt-2 max-w-2xl">
        Reconcile self-reported off-site revenue from vendor and community partners. Approving credits the partner at their locked off-site rev-share rate.
      </p>
      <div className="divider-flame" />

      <div className="flex flex-wrap gap-2" data-testid="report-status-tabs">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setTab(s)}
            className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              tab === s ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`report-status-${s}`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-3">
        {loading && <p className="text-sm text-[#5C6B6B]">Loading...</p>}
        {!loading && rows.length === 0 && (
          <div className="card p-10 text-center"><p className="font-serif text-lg">No reports with status "{tab}".</p></div>
        )}
        {rows.map((r) => (
          <button
            key={r.id}
            onClick={() => { setOpen(r); setForm({ admin_note: r.admin_note || "", override_gross_usd: "", override_pct: "" }); }}
            className="card p-5 w-full text-left hover:border-[#476B6B] transition"
            data-testid={`admin-report-${r.id}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-serif text-lg">{r.partner_slug}</p>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider ${STATUS_COLOR[r.status] || ""}`}>{r.status}</span>
                  <span className="text-[10px] text-[#5C6B6B] uppercase tracking-wider">{r.source}</span>
                </div>
                <p className="text-sm text-[#1A2424] mt-2">
                  {r.period_start} → {r.period_end} · <strong>${Number(r.gross_revenue_usd).toFixed(2)}</strong>
                  {r.attributed_orders > 0 && <> · {r.attributed_orders} orders</>}
                </p>
                {r.note && <p className="text-xs text-[#5C6B6B] mt-1 italic">"{r.note}"</p>}
                {r.status === "approved" && (
                  <p className="text-xs text-[#2E5C46] mt-1">Credited: ${Number(r.approved_payout_usd).toFixed(2)} ({r.approved_pct}% / {r.approved_pct_source})</p>
                )}
              </div>
              <p className="text-[10px] text-[#5C6B6B]">{new Date(r.created_at).toLocaleString()}</p>
            </div>
          </button>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={() => setOpen(null)}>
          <div className="bg-white max-w-2xl w-full rounded-xl p-6 max-h-[92vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="admin-report-modal">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="font-serif text-2xl">{open.partner_slug}</h2>
                <p className="text-xs text-[#5C6B6B] mt-1">
                  {open.partner_type} · <a href={`/partner/${open.partner_slug}`} target="_blank" rel="noreferrer" className="text-[#476B6B] hover:underline inline-flex items-center gap-1">profile <ExternalLink size={10} /></a>
                </p>
              </div>
              <button onClick={() => setOpen(null)}><X size={20} strokeWidth={1.5} /></button>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
              <Stat label="Period" value={`${open.period_start} → ${open.period_end}`} />
              <Stat label="Source" value={open.source} />
              <Stat label="Gross revenue" value={`$${Number(open.gross_revenue_usd).toFixed(2)}`} />
              <Stat label="Attributed orders" value={open.attributed_orders} />
            </div>

            {open.note && (
              <div className="mb-4 p-3 bg-[#FAF8F5] rounded text-sm">
                <p className="label">Partner note</p>
                <p className="text-sm text-[#1A2424] mt-1">{open.note}</p>
              </div>
            )}

            {open.status === "submitted" || open.status === "revised" ? (
              <>
                <div className="grid grid-cols-2 gap-3 mt-4">
                  <Field label="Override gross (optional)" value={form.override_gross_usd} type="number" step="0.01" onChange={(v) => setForm({ ...form, override_gross_usd: v })} testid="override-gross" />
                  <Field label="Override pct (optional)" value={form.override_pct} type="number" step="0.1" onChange={(v) => setForm({ ...form, override_pct: v })} testid="override-pct" />
                </div>
                <div className="mt-3">
                  <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Admin note</label>
                  <textarea value={form.admin_note} onChange={(e) => setForm({ ...form, admin_note: e.target.value })} rows={3} className="input-field w-full text-sm" data-testid="admin-note" />
                </div>
                <div className="flex gap-2 mt-5 pt-4 border-t border-[#E5E1D8]">
                  <button onClick={() => decide("approve")} className="btn-primary inline-flex items-center gap-2 flex-1 justify-center" data-testid="decide-approve">
                    <CheckCircle2 size={14} strokeWidth={1.5} /> Approve & credit
                  </button>
                  <button onClick={() => decide("revise")} className="btn-outline inline-flex items-center gap-2" data-testid="decide-revise">
                    <RefreshCw size={14} strokeWidth={1.5} /> Send back for revision
                  </button>
                  <button onClick={() => decide("dispute")} className="text-[#9E3C3C] border border-[#9E3C3C] px-4 py-2 rounded inline-flex items-center gap-2 text-sm" data-testid="decide-dispute">
                    <AlertCircle size={14} strokeWidth={1.5} /> Dispute
                  </button>
                </div>
              </>
            ) : (
              <p className="text-sm text-[#5C6B6B] italic mt-4">This report is in a terminal state ({open.status}) and can no longer be changed.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="label">{label}</p>
      <p className="text-sm text-[#1A2424] mt-1">{value}</p>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", step, testid }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">{label}</label>
      <input type={type} step={step} value={value} onChange={(e) => onChange(e.target.value)} className="input-field w-full text-sm" data-testid={testid} />
    </div>
  );
}
