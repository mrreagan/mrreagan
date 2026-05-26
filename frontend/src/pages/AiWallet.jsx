import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Sparkles, Wallet, Plus, RefreshCw, AlertTriangle, LogIn } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const STORE_KEY_AUTO = "ai_wallet_auto_recharge_v1";

export default function AiWallet() {
  const { user, loading: authLoading, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null); // { kind, message }
  const [busy, setBusy] = useState(false);
  const [pack, setPack] = useState(25);
  const [auto, setAuto] = useState({ enabled: false, threshold_usd: 5, amount_usd: 25 });

  const load = async () => {
    setLoadError(null);
    try {
      const r = await api.get("/ai-wallet/me");
      setData(r.data);
      const w = r.data.wallet;
      setAuto({
        enabled: !!w.auto_recharge_enabled,
        threshold_usd: w.auto_recharge_threshold_usd || 5,
        amount_usd: w.auto_recharge_amount_usd || 25,
      });
    } catch (e) {
      const status = e?.response?.status;
      if (status === 404) {
        setLoadError({
          kind: "unavailable",
          message:
            "AI Wallet isn’t available on this environment yet. If you’re viewing production, the latest backend may not be deployed — please redeploy or contact an admin.",
        });
      } else if (status === 401 || status === 403) {
        // IMPORTANT: do NOT call refreshUser() here. If the wallet endpoint
        // returns 401 while the rest of the app is signed in (cookie scoping
        // bug on prod, etc.), calling refreshUser would set user=null and
        // bounce us to /login — exactly the loop the user reported. Instead,
        // surface a clear error and let the user decide.
        setLoadError({
          kind: "auth_unclear",
          message:
            "We couldn’t load your AI Wallet. The rest of the site says you’re signed in, but this endpoint disagrees — that’s usually a production cookie/CORS issue, not your account. Try again, or sign out and sign back in if it persists.",
        });
      } else {
        setLoadError({
          kind: "generic",
          message:
            e?.response?.data?.detail ||
            "We couldn’t load your AI Wallet right now. Please try again in a moment.",
        });
      }
    }
  };
  useEffect(() => {
    // Wait for AuthContext to resolve before doing anything.
    if (authLoading) return;
    if (!user) {
      // Only here when AuthContext explicitly resolved with no user.
      // Render an inline "please sign in" state instead of doing a hard
      // navigate — a hard redirect from inside a useEffect causes a
      // loop on production if the cookie is being lost between pages.
      setLoadError({
        kind: "signed_out",
        message:
          "You need to be signed in to view your AI Wallet. If you’re seeing this even though you just signed in, your browser may be blocking the session cookie on this domain.",
      });
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user]);

  const handleHardSignOut = async () => {
    await logout();
    navigate("/login?next=/dashboard/ai-wallet", { replace: true });
  };

  const topup = async () => {
    setBusy(true);
    try {
      const res = await api.post("/ai-wallet/topup/checkout", {
        amount_usd: pack,
        origin_url: window.location.origin,
      });
      window.location.href = res.data.url;
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not start top-up");
    } finally {
      setBusy(false);
    }
  };

  const saveAuto = async () => {
    setBusy(true);
    try {
      await api.put("/ai-wallet/auto-recharge", {
        enabled: auto.enabled,
        threshold_usd: Number(auto.threshold_usd),
        amount_usd: Number(auto.amount_usd),
      });
      toast.success("Auto-recharge settings saved");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not save");
    } finally {
      setBusy(false);
    }
  };

  if (loadError) {
    const isAuthUnclear = loadError.kind === "auth_unclear";
    return (
      <div className="container-page py-12" data-testid="ai-wallet-error">
        <span className="label">Dashboard · AI Wallet</span>
        <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
          <Wallet size={26} strokeWidth={1.2} /> AI Wallet
        </h1>
        <div className="divider-flame" />
        <div className="card p-6 max-w-2xl" data-testid={`ai-wallet-error-${loadError.kind}`}>
          <div className="flex items-start gap-3">
            <AlertTriangle size={20} strokeWidth={1.4} className="text-[#9E3C3C] mt-0.5" />
            <div>
              <p className="font-serif text-lg">
                {loadError.kind === "unavailable" && "AI Wallet not yet available"}
                {loadError.kind === "auth_unclear" && "Couldn’t load AI Wallet"}
                {loadError.kind === "signed_out" && "Please sign in"}
                {loadError.kind === "generic" && "Something went wrong"}
              </p>
              <p className="text-sm text-[#5C6B6B] mt-1">{loadError.message}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {loadError.kind === "signed_out" ? (
                  <a href="/login?next=/dashboard/ai-wallet" className="btn-primary text-xs inline-flex items-center gap-1" data-testid="ai-wallet-signin-link">
                    <LogIn size={11} strokeWidth={1.6} /> Sign in
                  </a>
                ) : (
                  <button onClick={load} className="btn-primary text-xs" data-testid="ai-wallet-retry-btn">
                    Try again
                  </button>
                )}
                {isAuthUnclear && (
                  <button onClick={handleHardSignOut} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="ai-wallet-resignin-btn">
                    <LogIn size={11} strokeWidth={1.6} /> Sign out & sign back in
                  </button>
                )}
                <a href="/ai" className="btn-outline text-xs" data-testid="ai-wallet-learn-btn">
                  Learn about AI tools
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (authLoading || !data) return <p className="container-page py-12 text-sm text-[#5C6B6B]">Loading wallet…</p>;
  const w = data.wallet;
  const packs = data.topup_packs_usd || [10, 25, 50, 100];

  return (
    <div className="container-page py-12" data-testid="ai-wallet-page">
      <span className="label">Dashboard · AI Wallet</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Wallet size={26} strokeWidth={1.2} /> AI Wallet
      </h1>
      <div className="divider-flame" />

      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <div className="card p-5">
          <p className="label">Balance</p>
          <p className="font-serif text-3xl mt-2" data-testid="wallet-balance">${(w.balance_usd || 0).toFixed(4)}</p>
          {w.balance_usd <= 1 && (
            <p className="text-xs text-[#9E3C3C] mt-2">Balance is low — top up to keep using AI tools.</p>
          )}
        </div>
        <div className="card p-5">
          <p className="label">Lifetime top-up</p>
          <p className="font-serif text-3xl mt-2">${(w.lifetime_topup_usd || 0).toFixed(2)}</p>
        </div>
        <div className="card p-5">
          <p className="label">Lifetime spend</p>
          <p className="font-serif text-3xl mt-2">${(w.lifetime_spend_usd || 0).toFixed(4)}</p>
        </div>
      </div>

      {/* Foundation pricing disclosure — shown immediately under the hero */}
      {data.pricing && (
        <div className="rounded-2xl border-2 border-[#C9A961] bg-[#FFF8E1] p-5 mb-6" data-testid="ai-wallet-pricing-disclosure">
          <p className="text-[10px] uppercase tracking-wider text-[#8B7128] font-semibold">
            Pricing — {data.pricing.multiplier.toFixed(2)}× passthrough
          </p>
          <p className="font-serif text-xl mt-1 leading-snug">
            Thank you for supporting Birthright Foundation.
          </p>
          <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">
            {data.pricing.disclosure}
          </p>
        </div>
      )}

      <div className="card p-5 mb-6" data-testid="topup-card">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><Plus size={16} strokeWidth={1.5} /> Top up</h2>
        <p className="text-sm text-[#5C6B6B] mt-1">
          Top up is billed at face value — every dollar here funds your AI usage at
          {" "}<strong>{data.pricing?.multiplier.toFixed(2) || "1.50"}×</strong> the provider cost
          {" "}(the extra <strong>{data.pricing?.foundation_markup_pct || 50}%</strong> supports the foundation).
        </p>
        <div className="flex flex-wrap gap-2 mt-4">
          {packs.map((p) => (
            <button
              key={p}
              onClick={() => setPack(p)}
              className={`px-4 py-2 rounded-full text-sm border transition ${
                pack === p ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`topup-pack-${p}`}
            >
              ${p}
            </button>
          ))}
        </div>
        <button onClick={topup} disabled={busy} className="btn-primary mt-4" data-testid="topup-checkout-btn">
          {busy ? "…" : `Top up $${pack} via Stripe`}
        </button>
      </div>

      <div className="card p-5 mb-6" data-testid="auto-recharge-card">
        <h2 className="font-serif text-xl inline-flex items-center gap-2"><RefreshCw size={16} strokeWidth={1.5} /> Auto-recharge</h2>
        <label className="flex items-center gap-2 mt-3 text-sm">
          <input type="checkbox" checked={auto.enabled} onChange={(e) => setAuto({ ...auto, enabled: e.target.checked })} data-testid="auto-recharge-toggle" />
          Auto-top-up when balance drops below threshold
        </label>
        <div className="grid grid-cols-2 gap-3 mt-3 max-w-md">
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">When ≤ ($)</label>
            <input type="number" min="1" max="100" value={auto.threshold_usd}
                   onChange={(e) => setAuto({ ...auto, threshold_usd: e.target.value })}
                   className="input-field w-full text-sm" data-testid="auto-threshold" />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Add ($)</label>
            <input type="number" min="10" max="500" value={auto.amount_usd}
                   onChange={(e) => setAuto({ ...auto, amount_usd: e.target.value })}
                   className="input-field w-full text-sm" data-testid="auto-amount" />
          </div>
        </div>
        <button onClick={saveAuto} disabled={busy} className="btn-outline mt-4 text-xs" data-testid="auto-save-btn">
          Save auto-recharge settings
        </button>
      </div>

      <h2 className="font-serif text-xl mb-2 mt-8 inline-flex items-center gap-2">
        <Sparkles size={16} strokeWidth={1.5} className="text-[#C9A961]" /> Recent AI usage
      </h2>
      {data.recent_usage.length === 0 ? (
        <p className="text-sm text-[#5C6B6B]">No AI activity yet.</p>
      ) : (
        <table className="w-full text-sm card" data-testid="usage-table">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">
              <th className="text-left px-3 py-2">When</th>
              <th className="text-left px-3 py-2">Feature</th>
              <th className="text-left px-3 py-2">Model</th>
              <th className="text-right px-3 py-2">In tok</th>
              <th className="text-right px-3 py-2">Out tok</th>
              <th className="text-right px-3 py-2">Img</th>
              <th className="text-right px-3 py-2">Cost</th>
            </tr>
          </thead>
          <tbody>
            {data.recent_usage.map((e) => (
              <tr key={e.id} className="border-t border-[#E5E1D8]" data-testid={`usage-row-${e.id}`}>
                <td className="px-3 py-2 text-xs">{new Date(e.created_at).toLocaleString()}</td>
                <td className="px-3 py-2 text-xs">{e.feature}</td>
                <td className="px-3 py-2 text-xs font-mono">{e.model}</td>
                <td className="px-3 py-2 text-right text-xs">{e.tokens_in}</td>
                <td className="px-3 py-2 text-right text-xs">{e.tokens_out}</td>
                <td className="px-3 py-2 text-right text-xs">{e.images || 0}</td>
                <td className="px-3 py-2 text-right">${e.cost_usd.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
