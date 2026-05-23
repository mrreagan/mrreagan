import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { CheckCircle2, Clock, AlertCircle, TrendingUp } from "lucide-react";

const TYPE_LABEL = {
  facilitator: "Facilitator",
  community:   "Community",
  research:    "Research",
  vendor:      "Vendor",
};

export default function PartnerSubscribe() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [partnerType, setPartnerType] = useState(searchParams.get("type") || "facilitator");
  const [plans, setPlans] = useState([]);
  const [myProfiles, setMyProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get(`/subscriptions/plans?partner_type=${partnerType}`),
      user ? api.get("/partners/my-profiles") : Promise.resolve({ data: [] }),
    ])
      .then(([p, mp]) => { setPlans(p.data); setMyProfiles(mp.data); })
      .finally(() => setLoading(false));
  }, [partnerType, user]);

  const eligibleProfile = useMemo(() => myProfiles.find(
    (p) => p.partner_type === partnerType && p.status === "active"
  ), [myProfiles, partnerType]);

  const startCheckout = async (plan) => {
    if (!user) { toast.error("Please sign in first."); return; }
    if (!eligibleProfile) { toast.error(`You need an approved ${partnerType} partner profile first.`); return; }
    setBusy(plan.id);
    try {
      const { data } = await api.post("/subscriptions/checkout", {
        plan_id: plan.id,
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not start checkout");
      setBusy(null);
    }
  };

  return (
    <div className="container-page py-12" data-testid="partner-subscribe-page">
      <span className="label">Partner subscriptions</span>
      <h1 className="editorial-h1 mt-2">Choose your plan</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Subscription = license. The duration you choose is your license window — and shorter terms carry a higher revenue share for your work. Renew before expiry to stay licensed.
      </p>

      <div className="flex flex-wrap gap-2 mt-6" data-testid="subscribe-type-tabs">
        {Object.keys(TYPE_LABEL).map((t) => (
          <button
            key={t}
            onClick={() => setPartnerType(t)}
            className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              partnerType === t ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`subscribe-tab-${t}`}
          >
            {TYPE_LABEL[t]}
          </button>
        ))}
      </div>

      {user && !eligibleProfile && (
        <div className="card p-4 mt-6 bg-[#FAF8F5] border-[#C9A961]/40 flex items-start gap-3" data-testid="needs-approval-banner">
          <AlertCircle size={16} strokeWidth={1.5} className="text-[#C9A961] mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-sm">You need an approved {TYPE_LABEL[partnerType]} partner profile before you can subscribe.</p>
            <Link to="/partners/apply" className="text-sm text-[#476B6B] underline mt-1 inline-block">Apply now</Link>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-6">Loading plans...</p>
      ) : (
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="plan-cards">
          {plans.map((p) => <PlanCard key={p.id} plan={p} disabled={!eligibleProfile} busy={busy === p.id} onSubscribe={() => startCheckout(p)} />)}
        </div>
      )}
    </div>
  );
}

function PlanCard({ plan, disabled, busy, onSubscribe }) {
  const isAnnual = plan.duration_months === 12;
  return (
    <div className={`card p-6 relative ${isAnnual ? "border-[#476B6B] ring-1 ring-[#476B6B]" : ""}`} data-testid={`plan-${plan.id}`}>
      {isAnnual && <span className="absolute -top-2 left-6 px-2 py-0.5 bg-[#476B6B] text-white text-[10px] uppercase tracking-wider rounded-full">Most chosen</span>}
      <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">{plan.partner_type}</p>
      <h3 className="font-serif text-xl mt-1">{plan.name}</h3>
      <p className="text-xs text-[#5C6B6B] mt-1">{plan.tagline}</p>
      <p className="font-serif text-4xl mt-4">${plan.price_usd.toFixed(0)}</p>
      <p className="text-xs text-[#5C6B6B]">for {plan.duration_months} month{plan.duration_months === 1 ? "" : "s"} of access</p>
      <RevShareInfo plan={plan} />
      <button onClick={onSubscribe} disabled={disabled || busy} className="btn-primary w-full mt-5 inline-flex items-center justify-center gap-1" data-testid={`subscribe-${plan.id}`}>
        {busy ? "Opening Stripe..." : (disabled ? "Profile required" : "Subscribe")}
      </button>
    </div>
  );
}

function RevShareInfo({ plan }) {
  if (plan.partner_type === "facilitator") {
    return (
      <div className="mt-4 pt-4 border-t border-[#E5E1D8] space-y-2" data-testid={`plan-revshare-${plan.id}`}>
        <p className="label inline-flex items-center gap-1"><TrendingUp size={11} strokeWidth={1.5} /> Revenue share</p>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[#5C6B6B]">Birthright IP materials</span>
          <span className="font-medium text-[#2E5C46]">{plan.birthright_ip_pct}%</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[#5C6B6B]">Own / other materials</span>
          <span className="font-medium">{plan.other_content_pct}%</span>
        </div>
      </div>
    );
  }
  return (
    <div className="mt-4 pt-4 border-t border-[#E5E1D8] flex items-center justify-between text-sm" data-testid={`plan-revshare-${plan.id}`}>
      <span className="text-[#5C6B6B]">Revenue share</span>
      <span className="font-medium text-[#2E5C46]">{plan.default_pct}%</span>
    </div>
  );
}

// Compact card to embed in the partner workspace dashboard
export function SubscriptionStatusCard({ profile, subscription }) {
  if (!subscription || !subscription.is_active) {
    return (
      <div className="card p-4 bg-[#FAF8F5] border-[#C9A961]/40" data-testid={`sub-status-${profile.partner_type}-inactive`}>
        <p className="label inline-flex items-center gap-1"><Clock size={11} strokeWidth={1.5} /> No active subscription</p>
        <p className="text-sm mt-1">Your {profile.partner_type} profile is approved but unlicensed. Subscribe to activate revenue share and partner perks.</p>
        <Link to={`/partners/subscribe?type=${profile.partner_type}`} className="btn-primary inline-block mt-3 text-xs">View plans</Link>
      </div>
    );
  }
  const expires = new Date(subscription.expires_at);
  const daysLeft = Math.ceil((expires - new Date()) / (1000 * 60 * 60 * 24));
  const expiringSoon = daysLeft <= 30;
  return (
    <div className="card p-4" data-testid={`sub-status-${profile.partner_type}-active`}>
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#2E5C46]">
          <CheckCircle2 size={11} strokeWidth={2} /> Licensed
        </span>
        <span className={`text-[10px] uppercase tracking-wider ${expiringSoon ? "text-[#B86A5C]" : "text-[#5C6B6B]"}`}>
          {daysLeft} day{daysLeft === 1 ? "" : "s"} left
        </span>
      </div>
      <p className="font-medium text-sm mt-2">{subscription.plan?.name || "Active subscription"}</p>
      <p className="text-xs text-[#5C6B6B]">Expires {expires.toLocaleDateString()}</p>
      {expiringSoon && (
        <Link to={`/partners/subscribe?type=${profile.partner_type}`} className="btn-outline text-xs mt-3 inline-block" data-testid={`renew-${profile.partner_type}`}>
          Renew now
        </Link>
      )}
    </div>
  );
}
