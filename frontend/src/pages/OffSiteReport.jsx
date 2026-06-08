/* OffSiteReport — quarterly self-reporting for artists.
 *
 * URL: /partner/me/off-site-report
 *
 * Three sections:
 *   1. Tier + estimated rate banner (so the artist sees what % their
 *      report will be charged at, before submitting).
 *   2. Submission form (period_start, period_end, gross_revenue_usd,
 *      attributed_orders, note).
 *   3. History table — previous reports + their status (submitted,
 *      approved, disputed).
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { FileText, ArrowUpRight, Send, CheckCircle2, Clock, AlertTriangle } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const STATUS_PILL = {
  submitted: { label: "Awaiting review", icon: Clock, color: "text-[#C9A961] bg-[#FFF8E8] border-[#F0E2B2]" },
  approved:  { label: "Approved",        icon: CheckCircle2, color: "text-[#2E5C46] bg-[#E8F1EA] border-[#BAD5BF]" },
  disputed:  { label: "Disputed",        icon: AlertTriangle, color: "text-[#9E3C3C] bg-[#FBEAEA] border-[#E7C0C0]" },
  revised:   { label: "Needs revision",  icon: AlertTriangle, color: "text-[#C9A961] bg-[#FFF8E8] border-[#F0E2B2]" },
};

function todayISO() { return new Date().toISOString().slice(0, 10); }
function quarterAgoISO() {
  const d = new Date(); d.setMonth(d.getMonth() - 3);
  return d.toISOString().slice(0, 10);
}

export default function OffSiteReport() {
  const { user } = useAuth();
  const [tier, setTier] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    period_start: quarterAgoISO(),
    period_end: todayISO(),
    gross_revenue_usd: "",
    attributed_orders: 0,
    note: "",
  });

  const load = async () => {
    try {
      const [tierR, listR] = await Promise.all([
        api.get("/partner/me/artist-tier"),
        api.get("/partner-sales-reports/my?partner_type=artist"),
      ]);
      setTier(tierR.data);
      setReports(listR.data || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't load");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [tierR, listR] = await Promise.all([
          api.get("/partner/me/artist-tier"),
          api.get("/partner-sales-reports/my?partner_type=artist"),
        ]);
        if (cancelled) return;
        setTier(tierR.data);
        setReports(listR.data || []);
      } catch (err) {
        if (!cancelled) toast.error(err?.response?.data?.detail || "Couldn't load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const estimated = useMemo(() => {
    const grossNum = parseFloat(form.gross_revenue_usd) || 0;
    if (!tier || grossNum <= 0) return null;
    const owed = grossNum * (tier.outbound_pct / 100);
    return {
      pct: tier.outbound_pct,
      owed: owed.toFixed(2),
      kept: (grossNum - owed).toFixed(2),
    };
  }, [tier, form.gross_revenue_usd]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.gross_revenue_usd || parseFloat(form.gross_revenue_usd) <= 0) {
      toast.error("Enter a gross revenue greater than $0");
      return;
    }
    setSubmitting(true);
    try {
      await api.post(
        "/partner-sales-reports?partner_type=artist",
        {
          period_start: form.period_start,
          period_end: form.period_end,
          gross_revenue_usd: parseFloat(form.gross_revenue_usd),
          attributed_orders: parseInt(form.attributed_orders, 10) || 0,
          note: form.note,
        },
      );
      toast.success("Report submitted — Foundation will review it within 14 days");
      setForm({ ...form, gross_revenue_usd: "", attributed_orders: 0, note: "" });
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="container-page py-12">Loading…</div>;

  return (
    <div className="container-page py-12" data-testid="off-site-report-page">
      <span className="label">Artist · quarterly self-report</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <FileText size={24} strokeWidth={1.2} /> Off-site sales report
      </h1>
      <p className="text-sm text-[#5C6B6B] mt-2 max-w-2xl">
        Report sales you made on <em>your own website</em> from buyers we
        sent you (the <code className="text-[10px] bg-[#FAF8F5] px-1.5 py-0.5 rounded">?via=birthright</code> tag in
        your dashboard analytics). Submit quarterly. Trust-based — we
        don&apos;t audit. Foundation reviews within 14 days.
      </p>

      <div className="divider-flame" />

      {/* Tier banner */}
      {tier && (
        <section
          className="card p-5 mt-6 max-w-3xl bg-[#FAF8F5]"
          data-testid="off-site-tier-banner"
        >
          <div className="flex items-baseline justify-between flex-wrap gap-3">
            <div>
              <p className="label text-[#C9A961]">Your current tier</p>
              <p className="font-serif italic text-2xl mt-1">
                {tier.tier_icon} {tier.tier_label}
              </p>
            </div>
            <div className="text-right">
              <p className="label">Outbound rate</p>
              <p className="font-serif text-xl mt-1">
                <strong>{tier.outbound_pct}%</strong>
                <span className="text-xs text-[#5C6B6B] italic ml-2">on this report</span>
              </p>
            </div>
          </div>
          <p className="text-xs text-[#5C6B6B] mt-3">
            At {tier.tier_label}, your outbound contribution to Foundation
            on off-site sales we drove is{" "}
            <strong>{tier.outbound_pct}%</strong>. See{" "}
            <Link to="/partner/artist" className="underline text-[#476B6B]">full terms</Link>.
          </p>
        </section>
      )}

      {/* Submission form */}
      <section className="card p-6 mt-6 max-w-3xl" data-testid="off-site-form-section">
        <h2 className="font-serif text-xl">Submit a new report</h2>
        <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <div>
            <label className="label">Period start</label>
            <input
              type="date" required
              value={form.period_start}
              onChange={(e) => setForm({ ...form, period_start: e.target.value })}
              className="input-field w-full" data-testid="off-site-period-start"
            />
          </div>
          <div>
            <label className="label">Period end</label>
            <input
              type="date" required
              value={form.period_end}
              onChange={(e) => setForm({ ...form, period_end: e.target.value })}
              className="input-field w-full" data-testid="off-site-period-end"
            />
          </div>
          <div>
            <label className="label">Gross revenue from Birthright-referred buyers (USD)</label>
            <input
              type="number" step="0.01" min="0" required
              value={form.gross_revenue_usd}
              onChange={(e) => setForm({ ...form, gross_revenue_usd: e.target.value })}
              className="input-field w-full" data-testid="off-site-gross"
              placeholder="e.g. 1250.00"
            />
          </div>
          <div>
            <label className="label">Attributed orders (count)</label>
            <input
              type="number" min="0"
              value={form.attributed_orders}
              onChange={(e) => setForm({ ...form, attributed_orders: e.target.value })}
              className="input-field w-full" data-testid="off-site-orders"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Notes (optional)</label>
            <textarea
              rows={3} maxLength={2000}
              value={form.note}
              onChange={(e) => setForm({ ...form, note: e.target.value })}
              className="input-field w-full" data-testid="off-site-note"
              placeholder="Anything that would help us review (e.g. specific orders, breakdown by piece, etc.)"
            />
          </div>

          {estimated && (
            <div
              className="sm:col-span-2 bg-[#F0F6F4] border border-[#C8DDD7] rounded p-4 text-sm"
              data-testid="off-site-estimate"
            >
              <p className="text-xs uppercase tracking-[0.18em] text-[#476B6B] mb-2">
                Estimated breakdown
              </p>
              <div className="grid grid-cols-3 gap-3 font-serif">
                <div>
                  <p className="text-[10px] text-[#5C6B6B] uppercase tracking-wider">You keep</p>
                  <p className="text-lg text-[#2C4E5A] mt-1">${estimated.kept}</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#5C6B6B] uppercase tracking-wider">Foundation share ({estimated.pct}%)</p>
                  <p className="text-lg text-[#A87A4A] mt-1">${estimated.owed}</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#5C6B6B] uppercase tracking-wider">Report total</p>
                  <p className="text-lg text-[#2C4E5A] mt-1">${parseFloat(form.gross_revenue_usd || 0).toFixed(2)}</p>
                </div>
              </div>
            </div>
          )}

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={submitting}
              className="btn-primary inline-flex items-center gap-2"
              data-testid="off-site-submit"
            >
              <Send size={14} strokeWidth={1.6} />
              {submitting ? "Submitting…" : "Submit report"}
            </button>
          </div>
        </form>
      </section>

      {/* History */}
      <section className="mt-10 max-w-3xl" data-testid="off-site-history-section">
        <h2 className="font-serif text-xl">Your previous reports</h2>
        {reports.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] italic mt-3">
            No reports yet. Your first quarterly report will appear here.
          </p>
        ) : (
          <div className="overflow-x-auto mt-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E5E1D8]">
                  <th className="text-left py-2 label">Period</th>
                  <th className="text-right py-2 label">Gross</th>
                  <th className="text-right py-2 label">Orders</th>
                  <th className="text-right py-2 label">Foundation %</th>
                  <th className="text-right py-2 label">Foundation share</th>
                  <th className="text-left py-2 label">Status</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => {
                  const pill = STATUS_PILL[r.status] || STATUS_PILL.submitted;
                  const Icon = pill.icon;
                  return (
                    <tr
                      key={r.id}
                      className="border-b border-[#E5E1D8] last:border-0"
                      data-testid={`off-site-row-${r.id}`}
                    >
                      <td className="py-3">{r.period_start} → {r.period_end}</td>
                      <td className="py-3 text-right">${Number(r.gross_revenue_usd).toFixed(2)}</td>
                      <td className="py-3 text-right text-[#5C6B6B]">{r.attributed_orders ?? 0}</td>
                      <td className="py-3 text-right">{r.approved_pct ?? "—"}{r.approved_pct ? "%" : ""}</td>
                      <td className="py-3 text-right text-[#A87A4A]">
                        {r.approved_payout_usd != null ? `$${Number(r.approved_payout_usd).toFixed(2)}` : "—"}
                      </td>
                      <td className="py-3">
                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${pill.color}`}>
                          <Icon size={11} strokeWidth={1.8} />
                          {pill.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="mt-10 max-w-3xl">
        <Link
          to="/partner/me/payout-method"
          className="text-xs uppercase tracking-[0.18em] text-[#476B6B] hover:text-[#1A2424] inline-flex items-center gap-1"
          data-testid="off-site-payout-link"
        >
          Set up payout method <ArrowUpRight size={12} strokeWidth={1.6} />
        </Link>
      </div>
    </div>
  );
}
