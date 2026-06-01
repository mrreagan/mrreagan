import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { BarChart3, Calendar, Sparkles } from "lucide-react";
import api from "../lib/api";

function fmtUSD(n, { precision = 2 } = {}) {
  const v = Number(n || 0);
  return `$${v.toLocaleString(undefined, {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })}`;
}

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

      {/* Time-window rollups (always today/week/month, independent of the filter below) */}
      {data.windows && (
        <div className="card p-5 mb-6" data-testid="window-rollups-card">
          <div className="flex items-center gap-2 mb-3">
            <Calendar size={14} strokeWidth={1.6} className="text-[#476B6B]" />
            <p className="label">Foundation-wide spend</p>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <WindowStat label="Today"        data={data.windows.today} testid="window-today" />
            <WindowStat label="Last 7 days"  data={data.windows.week}  testid="window-week" />
            <WindowStat label="Last 30 days" data={data.windows.month} testid="window-month" />
          </div>
          <p className="text-[10px] text-[#5C6B6B] italic mt-3">
            Includes the Foundation markup. The Foundation keeps {((1 - 1/1.5) * 100).toFixed(0)}% of each $ shown above.
          </p>
        </div>
      )}

      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs text-[#5C6B6B] mr-2">Filter table window:</span>
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
        <StatCard label={`Total events · ${days}d`} value={data.total_events} testid="total-events" />
        <StatCard label={`Total cost · ${days}d`} value={fmtUSD(data.total_cost_usd)} testid="total-cost" />
        <StatCard label="Active wallets" value={(data.wallets || []).length} testid="wallets-count" />
      </div>

      <h2 className="font-serif text-xl mb-2 mt-4 inline-flex items-center gap-2">
        <Sparkles size={16} strokeWidth={1.5} className="text-[#C9A961]" /> Usage by user × feature
      </h2>
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

      <h2 className="font-serif text-xl mb-2 mt-8">Wallets — sorted by lifetime spend</h2>
      <table className="w-full text-sm card" data-testid="wallets-table">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
            <th className="text-left px-3 py-2">User</th>
            <th className="text-left px-3 py-2">Role</th>
            <th className="text-right px-3 py-2">Balance</th>
            <th className="text-right px-3 py-2">Lifetime topup</th>
            <th className="text-right px-3 py-2">Lifetime spend</th>
            <th className="text-left px-3 py-2">Auto-recharge</th>
          </tr>
        </thead>
        <tbody>
          {data.wallets.map((w) => (
            <tr key={w.id} className="border-t border-[#E5E1D8]" data-testid={`wallet-row-${w.user_id}`}>
              <td className="px-3 py-2 text-xs">
                <p className="text-[#1A2424]">{w.user_email || <span className="text-[#9E3C3C] italic">unknown user</span>}</p>
                {w.user_name && <p className="text-[10px] text-[#5C6B6B]">{w.user_name}</p>}
              </td>
              <td className="px-3 py-2 text-xs capitalize text-[#476B6B]">{w.user_role || "—"}</td>
              <td className="px-3 py-2 text-right">${(w.balance_usd || 0).toFixed(4)}</td>
              <td className="px-3 py-2 text-right text-xs">${(w.lifetime_topup_usd || 0).toFixed(2)}</td>
              <td className="px-3 py-2 text-right text-xs">${(w.lifetime_spend_usd || 0).toFixed(4)}</td>
              <td className="px-3 py-2 text-xs">{w.auto_recharge_enabled ? `on (≤$${w.auto_recharge_threshold_usd} → +$${w.auto_recharge_amount_usd})` : "off"}</td>
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

function WindowStat({ label, data, testid }) {
  const cost = Number(data?.cost_usd || 0);
  const events = Number(data?.events || 0);
  const precision = cost < 1 ? 4 : 2;
  return (
    <div data-testid={testid}>
      <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{label}</p>
      <p className="font-serif text-3xl mt-1">${cost.toFixed(precision)}</p>
      <p className="text-[11px] text-[#5C6B6B] mt-0.5">{events} {events === 1 ? "AI call" : "AI calls"}</p>
    </div>
  );
}
