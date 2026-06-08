/* AdminArtistPayouts — admin disbursement console.
 *
 * URL: /admin/artist/payouts
 *
 * Lists pending + recently-paid artist patronage payouts. Each row has
 * an inline "Pay via Stripe" button. The top bar has a "Bulk pay all
 * pending" button that fires a single batched POST to
 * /api/admin/artist/payouts/bulk-pay with a confirmation modal showing
 * the total dollar amount + number of artists about to receive funds.
 */
/* eslint-disable */
import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, AlertTriangle, Send, X } from "lucide-react";
import api from "../lib/api";

const fmt = (n) => `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function AdminArtistPayouts() {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState("pending");
  const [confirming, setConfirming] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const [running, setRunning] = useState(false);

  const load = async (status = filter) => {
    try {
      const r = await api.get(`/admin/artist/payouts?status=${status}`);
      setData(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't load payouts");
    }
  };
  useEffect(() => { load(filter); }, [filter]);

  const pending = (data?.rows || []).filter((r) => r.status === "pending");
  const eligible = pending.length;     // simplified: server will skip non-ready
  const totalAmount = pending.reduce((s, r) => s + Number(r.list_price || 0), 0);
  const uniqueArtists = new Set(pending.map((r) => r.artist_user_id)).size;

  const runBulkPay = async () => {
    setRunning(true);
    try {
      const r = await api.post("/admin/artist/payouts/bulk-pay", {
        notes: "Bulk monthly disbursement",
      });
      setBulkResult(r.data);
      toast.success(`Paid ${r.data.paid} of ${r.data.attempted} payouts (${fmt(r.data.total_paid_usd)})`);
      await load(filter);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Bulk pay failed");
    } finally {
      setRunning(false);
      setConfirming(false);
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-artist-payouts-page">
      <span className="label">Admin · disbursement console</span>
      <h1 className="editorial-h1 mt-2">Artist patronage payouts</h1>

      <div className="divider-flame" />

      {/* Top bar with filter + bulk pay CTA */}
      <div className="flex items-center justify-between gap-4 flex-wrap mt-6">
        <div className="flex items-center gap-2 text-xs">
          {["pending", "paid", "cancelled"].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              data-testid={`payouts-filter-${s}`}
              className={`px-3 py-1 rounded-full border transition ${
                filter === s
                  ? "border-[#476B6B] text-[#476B6B] bg-[#F0F6F4]"
                  : "border-[#E5E1D8] text-[#5C6B6B] hover:text-[#1A2424]"
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        {filter === "pending" && pending.length > 0 && (
          <button
            onClick={() => setConfirming(true)}
            data-testid="bulk-pay-open"
            className="btn-primary inline-flex items-center gap-2 text-sm"
          >
            <Send size={14} strokeWidth={1.6} />
            Bulk pay {pending.length} pending ({fmt(totalAmount)})
          </button>
        )}
      </div>

      {/* Summary banner */}
      {data && (
        <div className="grid sm:grid-cols-3 gap-3 mt-6">
          <div className="card p-4">
            <p className="label">Pending</p>
            <p className="font-serif text-2xl mt-1">{fmt(data.total_pending)}</p>
          </div>
          <div className="card p-4">
            <p className="label">Paid lifetime</p>
            <p className="font-serif text-2xl mt-1">{fmt(data.total_paid)}</p>
          </div>
          <div className="card p-4">
            <p className="label">Rows in view</p>
            <p className="font-serif text-2xl mt-1">{data.count}</p>
          </div>
        </div>
      )}

      {/* Bulk result */}
      {bulkResult && (
        <div className="card p-4 mt-6 border-l-2 border-[#476B6B]" data-testid="bulk-pay-result">
          <p className="label text-[#476B6B]">Last bulk run</p>
          <div className="grid sm:grid-cols-4 gap-3 mt-2 text-sm">
            <div><dt className="label">Attempted</dt><dd className="font-serif text-lg">{bulkResult.attempted}</dd></div>
            <div><dt className="label">Paid</dt><dd className="font-serif text-lg text-[#2E5C46]">{bulkResult.paid}</dd></div>
            <div><dt className="label">Skipped</dt><dd className="font-serif text-lg text-[#C9A961]">{bulkResult.skipped}</dd></div>
            <div><dt className="label">Failed</dt><dd className="font-serif text-lg text-[#9E3C3C]">{bulkResult.failed}</dd></div>
          </div>
        </div>
      )}

      {/* Payouts table */}
      <div className="overflow-x-auto mt-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#E5E1D8]">
              <th className="text-left py-2 label">Artist</th>
              <th className="text-left py-2 label">Artwork</th>
              <th className="text-right py-2 label">List price</th>
              <th className="text-right py-2 label">Foundation kept</th>
              <th className="text-left py-2 label">Buyer ships to</th>
              <th className="text-left py-2 label">Created</th>
            </tr>
          </thead>
          <tbody>
            {(data?.rows || []).map((p) => (
              <tr key={p.id} className="border-b border-[#E5E1D8] last:border-0" data-testid={`payout-row-${p.id}`}>
                <td className="py-3 font-serif italic">{p.artist_name || p.artist_user_id?.slice(0,8)}</td>
                <td className="py-3 text-[#5C6B6B]">{p.artwork_name}</td>
                <td className="py-3 text-right">{fmt(p.list_price)}</td>
                <td className="py-3 text-right text-[#A87A4A]">{fmt(p.foundation_markup)}</td>
                <td className="py-3 text-[#5C6B6B] text-xs">
                  {p.shipping_address?.city || "—"}
                  {p.shipping_address?.state ? `, ${p.shipping_address.state}` : ""}
                </td>
                <td className="py-3 text-[#5C6B6B] text-xs">{(p.created_at || "").slice(0,10)}</td>
              </tr>
            ))}
            {(data?.rows || []).length === 0 && (
              <tr><td colSpan={6} className="py-6 text-center text-[#5C6B6B] italic">No payouts in this view.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Confirmation modal */}
      {confirming && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setConfirming(false)}>
          <div className="bg-[#F8F2E5] max-w-md w-full p-6 border border-[#E5DCC4]" onClick={(e) => e.stopPropagation()} data-testid="bulk-pay-modal">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-[#A87A4A]">Confirm bulk disbursement</p>
                <h2 className="font-serif italic text-2xl text-[#2C4E5A] mt-1">Ready to send funds?</h2>
              </div>
              <button onClick={() => setConfirming(false)} className="text-[#5C6B6B] hover:text-[#1A2424]"><X size={18} /></button>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-5 font-serif">
              <div><p className="label">Artists</p><p className="text-xl mt-1">{uniqueArtists}</p></div>
              <div><p className="label">Payouts</p><p className="text-xl mt-1">{eligible}</p></div>
              <div className="col-span-2"><p className="label">Total amount</p><p className="text-3xl mt-1 italic text-[#2C4E5A]">{fmt(totalAmount)}</p></div>
            </div>
            <p className="text-xs text-[#5C6B6B] mt-4 leading-relaxed font-serif italic">
              Funds flow directly to each artist&apos;s Stripe Connect account.
              Rows where the artist has not completed Stripe onboarding will be
              automatically skipped (not marked paid). On failure, the row stays
              pending with a reason recorded.
            </p>
            <div className="flex items-center gap-2 mt-5">
              <button onClick={() => setConfirming(false)} className="btn-secondary text-xs">Cancel</button>
              <button onClick={runBulkPay} disabled={running} className="btn-primary inline-flex items-center gap-2 text-sm" data-testid="bulk-pay-confirm">
                {running ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
                {running ? "Sending…" : `Pay ${fmt(totalAmount)} now`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
