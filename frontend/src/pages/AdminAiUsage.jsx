import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { BarChart3 } from "lucide-react";
import api from "../lib/api";

export default function AdminAiUsage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const load = async () => {
    try {
      const r = await api.get(`/admin/ai-wallet/usage-report?days=${days}`);
      setData(r.data);
    } catch {
      toast.error("Could not load usage");
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [days]);

  if (!data) return <p className="container-page py-12 text-sm text-[#5C6B6B]">Loading…</p>;

  return (
    <div className="container-page py-12" data-testid="admin-ai-usage-page">
      <span className="label">Admin · AI Usage</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <BarChart3 size={26} strokeWidth={1.2} /> AI usage report
      </h1>
      <div className="divider-flame" />

      <div className="flex items-center gap-2 mb-4">
        {[7, 30, 90, 365].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              days === d ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8]"
            }`}
            data-testid={`days-${d}`}
          >
            Last {d} days
          </button>
        ))}
      </div>

      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <StatCard label="Total events" value={data.total_events} testid="total-events" />
        <StatCard label="Total cost" value={`$${data.total_cost_usd.toFixed(2)}`} testid="total-cost" />
        <StatCard label="Active wallets" value={(data.wallets || []).length} testid="wallets-count" />
      </div>

      <h2 className="font-serif text-xl mb-2 mt-4">Usage by user × feature</h2>
      {data.by_user_feature.length === 0 ? (
        <p className="text-sm text-[#5C6B6B]">No AI activity in this window.</p>
      ) : (
        <table className="w-full text-sm card" data-testid="usage-table">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
              <th className="text-left px-3 py-2">User</th>
              <th className="text-left px-3 py-2">Feature</th>
              <th className="text-right px-3 py-2">Events</th>
              <th className="text-right px-3 py-2">In tok</th>
              <th className="text-right px-3 py-2">Out tok</th>
              <th className="text-right px-3 py-2">Images</th>
              <th className="text-right px-3 py-2">Cost</th>
            </tr>
          </thead>
          <tbody>
            {data.by_user_feature.map((r, idx) => (
              <tr key={idx} className="border-t border-[#E5E1D8]">
                <td className="px-3 py-2 text-xs">{r.user_email}</td>
                <td className="px-3 py-2 text-xs">{r.feature}</td>
                <td className="px-3 py-2 text-right text-xs">{r.events}</td>
                <td className="px-3 py-2 text-right text-xs">{r.tokens_in}</td>
                <td className="px-3 py-2 text-right text-xs">{r.tokens_out}</td>
                <td className="px-3 py-2 text-right text-xs">{r.images}</td>
                <td className="px-3 py-2 text-right">${r.cost_usd.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 className="font-serif text-xl mb-2 mt-8">Wallets</h2>
      <table className="w-full text-sm card" data-testid="wallets-table">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
            <th className="text-left px-3 py-2">User</th>
            <th className="text-right px-3 py-2">Balance</th>
            <th className="text-right px-3 py-2">Lifetime topup</th>
            <th className="text-right px-3 py-2">Lifetime spend</th>
            <th className="text-left px-3 py-2">Auto</th>
          </tr>
        </thead>
        <tbody>
          {data.wallets.map((w) => (
            <tr key={w.id} className="border-t border-[#E5E1D8]">
              <td className="px-3 py-2 text-xs font-mono">{w.user_id}</td>
              <td className="px-3 py-2 text-right">${(w.balance_usd || 0).toFixed(4)}</td>
              <td className="px-3 py-2 text-right text-xs">${(w.lifetime_topup_usd || 0).toFixed(2)}</td>
              <td className="px-3 py-2 text-right text-xs">${(w.lifetime_spend_usd || 0).toFixed(4)}</td>
              <td className="px-3 py-2 text-xs">{w.auto_recharge_enabled ? `on (${w.auto_recharge_threshold_usd}/${w.auto_recharge_amount_usd})` : "off"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatCard({ label, value, testid }) {
  return (
    <div className="card p-5" data-testid={testid}>
      <p className="label">{label}</p>
      <p className="font-serif text-3xl mt-2">{value}</p>
    </div>
  );
}
