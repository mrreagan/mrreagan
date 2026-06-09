import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { Send, RefreshCw, Copy, Webhook, Clock, CheckCircle2, AlertCircle, FileText } from "lucide-react";

const PARTNER_TYPES = ["facilitator", "community", "research", "vendor"];

function firstDayOfMonth() {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
}
function lastDayOfMonth() {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().slice(0, 10);
}

const STATUS_PILL = {
  submitted: "bg-[#C9A961] text-[#1A2424]",
  approved: "bg-[#2E5C46] text-white",
  disputed: "bg-[#9E3C3C] text-white",
  revised: "bg-[#476B6B] text-white",
};

const STATUS_ICON = {
  submitted: Clock,
  approved: CheckCircle2,
  disputed: AlertCircle,
  revised: RefreshCw,
};

export default function PartnerSalesReports() {
  const [profiles, setProfiles] = useState([]);
  const [partnerType, setPartnerType] = useState(null);
  const [reports, setReports] = useState([]);
  const [webhookInfo, setWebhookInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const eligibleProfiles = profiles.filter((p) =>
    p.status === "active" && (p.partner_type === "vendor" || p.partner_type === "community"),
  );

  useEffect(() => {
    api.get("/partners/my-profiles")
      .then((r) => {
        setProfiles(r.data || []);
        const eligible = (r.data || []).filter(
          (p) => p.status === "active" && (p.partner_type === "vendor" || p.partner_type === "community"),
        );
        if (eligible.length > 0) setPartnerType(eligible[0].partner_type);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!partnerType) return;
    api.get(`/partner-sales-reports/my?partner_type=${partnerType}`)
      .then((r) => setReports(r.data));
    api.get(`/partner-sales-reports/my/webhook?partner_type=${partnerType}`)
      .then((r) => setWebhookInfo(r.data))
      .catch(() => setWebhookInfo(null));
  }, [partnerType]);

  if (loading) return <div className="container-page py-16">Loading...</div>;

  if (eligibleProfiles.length === 0) {
    return (
      <div className="container-page py-16" data-testid="sales-reports-empty">
        <h1 className="editorial-h1">Off-site sales reporting</h1>
        <div className="divider-flame" />
        <div className="card p-8 mt-4">
          <p className="font-serif text-xl">Available to vendor and community partners.</p>
          <p className="text-sm text-[#5C6B6B] mt-3">
            This feature is for partners whose birthright-attributed revenue happens off-platform (your Shopify store, podcast affiliate, etc.).
            You don't have an active vendor or community partner profile yet — <a href="/partner/apply" className="underline text-[#476B6B]">apply here</a>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container-page py-12" data-testid="partner-sales-reports-page">
      <span className="label">Partner</span>
      <h1 className="editorial-h1 mt-2">Off-site sales reporting</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl mt-2">
        Self-report attributable off-site revenue for a period. We'll credit you at your locked off-site rev-share rate once reconciled.
      </p>

      {eligibleProfiles.length > 1 && (
        <div className="flex gap-2 mt-4" data-testid="profile-type-tabs">
          {eligibleProfiles.map((p) => (
            <button
              key={p.partner_type}
              onClick={() => setPartnerType(p.partner_type)}
              className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                partnerType === p.partner_type ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`profile-tab-${p.partner_type}`}
            >
              {PARTNER_TYPES.find((t) => t === p.partner_type)}
            </button>
          ))}
        </div>
      )}

      <div className="mt-6 grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-serif text-2xl">Your reports</h2>
            <button onClick={() => setShowForm(true)} className="btn-primary inline-flex items-center gap-2" data-testid="new-report-btn">
              <Send size={14} strokeWidth={1.5} /> Submit a report
            </button>
          </div>
          <ReportList reports={reports} />
        </div>
        <div>
          <WebhookCard info={webhookInfo} partnerType={partnerType} onRotate={() => {
            api.post(`/partner-sales-reports/my/webhook/regenerate?partner_type=${partnerType}`)
              .then(() => api.get(`/partner-sales-reports/my/webhook?partner_type=${partnerType}`))
              .then((r) => { setWebhookInfo(r.data); toast.success("Webhook secret rotated."); });
          }} />
        </div>
      </div>

      {showForm && (
        <ReportForm
          partnerType={partnerType}
          onClose={() => setShowForm(false)}
          onSaved={(doc) => {
            setReports([doc, ...reports]);
            setShowForm(false);
            toast.success("Report submitted. We'll reconcile within a few business days.");
          }}
        />
      )}
    </div>
  );
}

function ReportList({ reports }) {
  if (reports.length === 0) {
    return <div className="card p-8 text-center text-sm text-[#5C6B6B]" data-testid="reports-empty">No reports yet.</div>;
  }
  return (
    <div className="space-y-3" data-testid="reports-list">
      {reports.map((r) => {
        const Icon = STATUS_ICON[r.status] || Clock;
        return (
          <div key={r.id} className="card p-5" data-testid={`report-${r.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Icon size={14} strokeWidth={1.5} className="text-[#476B6B]" />
                  <p className="font-serif text-lg">
                    {r.period_start} → {r.period_end}
                  </p>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider ${STATUS_PILL[r.status] || ""}`}>{r.status}</span>
                </div>
                <p className="text-sm text-[#1A2424] mt-2">
                  Gross: <strong>${Number(r.gross_revenue_usd).toFixed(2)}</strong>
                  {r.attributed_orders > 0 && <> · {r.attributed_orders} orders</>}
                  {r.status === "approved" && (
                    <>
                      {" · "}
                      <span className="text-[#2E5C46]">Approved payout: <strong>${Number(r.approved_payout_usd || 0).toFixed(2)}</strong> ({r.approved_pct}%)</span>
                    </>
                  )}
                </p>
                {r.note && <p className="text-xs text-[#5C6B6B] mt-2 italic">"{r.note}"</p>}
                {r.admin_note && (
                  <p className="text-xs text-[#5C6B6B] mt-2 pt-2 border-t border-[#E5E1D8]">
                    <strong>Admin note:</strong> {r.admin_note}
                  </p>
                )}
              </div>
              <div className="text-right shrink-0">
                <p className="text-[10px] text-[#5C6B6B]">{new Date(r.created_at).toLocaleDateString()}</p>
                <p className="text-[10px] text-[#5C6B6B] uppercase tracking-wider">{r.source}</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ReportForm({ partnerType, onClose, onSaved }) {
  const [form, setForm] = useState({
    period_start: firstDayOfMonth(),
    period_end: lastDayOfMonth(),
    gross_revenue_usd: "",
    attributed_orders: "",
    note: "",
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.gross_revenue_usd || parseFloat(form.gross_revenue_usd) < 0) {
      toast.error("Enter the gross revenue for this period.");
      return;
    }
    setSaving(true);
    try {
      const r = await api.post(`/partner-sales-reports?partner_type=${partnerType}`, {
        period_start: form.period_start,
        period_end: form.period_end,
        gross_revenue_usd: parseFloat(form.gross_revenue_usd),
        attributed_orders: parseInt(form.attributed_orders) || 0,
        note: form.note,
      });
      onSaved(r.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Submission failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()} className="bg-white w-full max-w-lg rounded-xl p-6" data-testid="report-form">
        <h2 className="font-serif text-2xl">New sales report</h2>
        <p className="text-xs text-[#5C6B6B] mt-1">For your {partnerType} profile.</p>

        <div className="mt-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Period start</label>
              <input type="date" value={form.period_start} onChange={(e) => setForm({ ...form, period_start: e.target.value })} className="input-field w-full text-sm" data-testid="form-period-start" />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Period end</label>
              <input type="date" value={form.period_end} onChange={(e) => setForm({ ...form, period_end: e.target.value })} className="input-field w-full text-sm" data-testid="form-period-end" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Gross revenue (USD)</label>
              <input type="number" min="0" step="0.01" value={form.gross_revenue_usd} onChange={(e) => setForm({ ...form, gross_revenue_usd: e.target.value })} className="input-field w-full text-sm" required data-testid="form-gross" />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Attributed orders</label>
              <input type="number" min="0" value={form.attributed_orders} onChange={(e) => setForm({ ...form, attributed_orders: e.target.value })} className="input-field w-full text-sm" data-testid="form-orders" />
            </div>
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Note (optional)</label>
            <textarea value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} rows={3} className="input-field w-full text-sm" placeholder="What's the source? Shopify export, podcast affiliate link, etc." data-testid="form-note" />
          </div>
          <div className="flex gap-2 pt-2">
            <button type="submit" disabled={saving} className="btn-primary flex-1" data-testid="form-submit">{saving ? "Submitting..." : "Submit report"}</button>
            <button type="button" onClick={onClose} className="btn-outline">Cancel</button>
          </div>
        </div>
      </form>
    </div>
  );
}

function WebhookCard({ info, partnerType, onRotate }) {
  const [reveal, setReveal] = useState(false);
  if (!info) {
    return <div className="card p-5"><p className="text-xs text-[#5C6B6B]">Webhook unavailable.</p></div>;
  }
  const apiBase = process.env.REACT_APP_BACKEND_URL || "";
  const fullUrl = `${apiBase}${info.webhook_path}`;
  const copy = (text, label) => { navigator.clipboard.writeText(text); toast.success(`${label} copied`); };
  return (
    <div className="card p-5" data-testid="webhook-card">
      <div className="flex items-center gap-2">
        <Webhook size={16} strokeWidth={1.5} className="text-[#C9A961]" />
        <h3 className="font-serif text-lg">Auto-report via webhook</h3>
      </div>
      <p className="text-xs text-[#5C6B6B] mt-2">
        For partners on platforms that can POST automatically (Shopify, Zapier, custom). HMAC-signed.
      </p>

      <div className="mt-4 space-y-3">
        <div>
          <p className="label text-[10px]">Endpoint</p>
          <div className="flex gap-1 mt-1">
            <code className="flex-1 bg-[#F4F1EA] px-2 py-1 rounded text-[11px] truncate">{fullUrl}</code>
            <button onClick={() => copy(fullUrl, "Endpoint")} className="text-[#476B6B]" data-testid="copy-endpoint"><Copy size={13} /></button>
          </div>
        </div>
        <div>
          <p className="label text-[10px]">Secret (rotate anytime)</p>
          <div className="flex gap-1 mt-1">
            <code className="flex-1 bg-[#F4F1EA] px-2 py-1 rounded text-[11px] truncate" data-testid="webhook-secret">
              {reveal ? info.secret : "•".repeat(32)}
            </code>
            <button onClick={() => setReveal(!reveal)} className="text-[#476B6B] text-[10px] underline" data-testid="reveal-secret">
              {reveal ? "Hide" : "Show"}
            </button>
            <button onClick={() => copy(info.secret, "Secret")} className="text-[#476B6B]" data-testid="copy-secret"><Copy size={13} /></button>
          </div>
        </div>
        <div>
          <p className="label text-[10px]">Header</p>
          <code className="block bg-[#F4F1EA] px-2 py-1 rounded text-[11px] mt-1">{info.signature_header}: sha256=&lt;hex&gt;</code>
          <p className="text-[10px] text-[#5C6B6B] mt-1">{info.signature_scheme}</p>
        </div>
        <button onClick={onRotate} className="text-xs text-[#9E3C3C] hover:underline inline-flex items-center gap-1" data-testid="rotate-secret">
          <RefreshCw size={11} /> Rotate secret
        </button>
      </div>
    </div>
  );
}
