/* At-a-glance AI spend tile for PartnerDashboard.
 *
 * Pulls the lightweight /ai-wallet/me/summary endpoint and renders a
 * single card that shows balance + this-month spend + low-balance warning
 * + a one-click link to the full wallet page. Designed to live next to
 * PartnerEarningsCard so partners see ALL their money flows in one
 * vertical scan.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Wallet, AlertTriangle, RefreshCw, ChevronRight } from "lucide-react";

function fmtUSD(n, { precision = 2 } = {}) {
  const v = Number(n || 0);
  return `$${v.toLocaleString(undefined, {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })}`;
}

export default function AiSpendCard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.get("/ai-wallet/me/summary")
      .then((r) => { if (!cancelled) setData(r.data); })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, []);

  // If endpoint isn't available (older backend) or user has zero history,
  // we still render the discovery card — the goal is visibility, even at
  // $0.00.
  if (error || !data) {
    if (error) return null; // silent fail; don't clutter the dashboard
    return <div className="card p-5 text-sm text-[#5C6B6B]" data-testid="ai-spend-loading">Loading AI spend…</div>;
  }

  const lowBalance = data.low_balance;
  const usedThisMonth = (data.this_month_events || 0) > 0;

  return (
    <Link
      to="/dashboard/ai-wallet"
      className="card p-5 block hover:border-[#476B6B] transition group"
      data-testid="ai-spend-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Wallet size={14} strokeWidth={1.6} className="text-[#476B6B]" />
          <span className="label">AI Wallet</span>
        </div>
        <ChevronRight size={14} strokeWidth={1.6} className="text-[#5C6B6B] group-hover:text-[#476B6B] mt-0.5" />
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3 text-center" data-testid="ai-spend-tiles">
        <div data-testid="ai-spend-balance">
          <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">Balance</p>
          <p className={`font-serif text-2xl mt-1 ${lowBalance ? "text-[#9E3C3C]" : "text-[#1A2424]"}`}>
            {fmtUSD(data.balance_usd, { precision: data.balance_usd < 1 ? 4 : 2 })}
          </p>
        </div>
        <div data-testid="ai-spend-month">
          <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">This month</p>
          <p className="font-serif text-2xl mt-1 text-[#1A2424]">
            {fmtUSD(data.this_month_spend_usd, { precision: data.this_month_spend_usd < 1 ? 4 : 2 })}
          </p>
          <p className="text-[10px] text-[#5C6B6B] mt-0.5">{data.this_month_events || 0} calls</p>
        </div>
        <div data-testid="ai-spend-lifetime">
          <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">Lifetime</p>
          <p className="font-serif text-2xl mt-1 text-[#1A2424]">
            {fmtUSD(data.lifetime_spend_usd, { precision: data.lifetime_spend_usd < 1 ? 4 : 2 })}
          </p>
        </div>
      </div>

      {lowBalance && (
        <div className="mt-3 flex items-start gap-2 text-xs text-[#9E3C3C]" data-testid="ai-spend-low-warn">
          <AlertTriangle size={12} strokeWidth={1.6} className="mt-0.5 shrink-0" />
          <p>Balance is low — top up to keep AI features running.</p>
        </div>
      )}
      {!lowBalance && data.auto_recharge_enabled && (
        <p className="mt-3 text-xs text-[#476B6B] inline-flex items-center gap-1" data-testid="ai-spend-auto-on">
          <RefreshCw size={11} strokeWidth={1.6} /> Auto-recharge on
        </p>
      )}
      {!usedThisMonth && !lowBalance && (
        <p className="mt-3 text-xs text-[#5C6B6B] italic" data-testid="ai-spend-empty">
          You haven't used AI features yet this month — open the wallet to explore Concierge, Vendor PDM, and Research tools.
        </p>
      )}
    </Link>
  );
}
