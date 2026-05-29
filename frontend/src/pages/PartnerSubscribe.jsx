import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import StudioVendorNudge from "../components/StudioVendorNudge";
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

      <StudioVendorNudge className="mt-6 max-w-2xl" />

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
            <Link to="/partner/apply" className="text-sm text-[#476B6B] underline mt-1 inline-block">Apply now</Link>
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
export function SubscriptionStatusCard({ profile, subscription, onChanged }) {
  const [showActions, setShowActions] = React.useState(false);
  const [showChange, setShowChange] = React.useState(false);
  const [cancelOpen, setCancelOpen] = React.useState(false);
  const [reason, setReason] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [plans, setPlans] = React.useState([]);
  const [previewing, setPreviewing] = React.useState(null);
  const [preview, setPreview] = React.useState(null);

  const loadPlans = async () => {
    try {
      const { data } = await api.get(`/subscriptions/plans?partner_type=${profile.partner_type}`);
      setPlans(data);
    } catch { /* ignore */ }
  };

  const previewChange = async (planId) => {
    if (!subscription) return;
    setPreviewing(planId);
    setPreview(null);
    try {
      const { data } = await api.get(`/subscriptions/${subscription.id}/change-preview?new_plan_id=${planId}`);
      setPreview(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Preview failed");
    } finally {
      setPreviewing(null);
    }
  };

  const confirmChange = async () => {
    if (!preview || !subscription) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/subscriptions/${subscription.id}/change-plan`, {
        new_plan_id: preview.new_plan_id,
        origin_url: window.location.origin,
      });
      if (data.checkout_required) {
        window.location.href = data.url;
      } else {
        toast.success("Plan changed — credit covered the new plan");
        if (onChanged) onChanged();
        setShowChange(false); setShowActions(false); setPreview(null);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not change plan");
    } finally {
      setBusy(false);
    }
  };

  const submitCancel = async () => {
    setBusy(true);
    try {
      await api.post(`/subscriptions/${subscription.id}/cancel`, { reason });
      toast.success("Cancellation recorded — your license remains active until the current expiry.");
      if (onChanged) onChanged();
      setCancelOpen(false); setShowActions(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Cancel failed");
    } finally {
      setBusy(false);
    }
  };

  if (!subscription || !subscription.is_active) {
    return (
      <div className="card p-4 bg-[#FAF8F5] border-[#C9A961]/40" data-testid={`sub-status-${profile.partner_type}-inactive`}>
        <p className="label inline-flex items-center gap-1"><Clock size={11} strokeWidth={1.5} /> No active subscription</p>
        <p className="text-sm mt-1">Your {profile.partner_type} profile is approved but unlicensed. Subscribe to activate revenue share and partner perks.</p>
        <Link to={`/partner/subscribe?type=${profile.partner_type}`} className="btn-primary inline-block mt-3 text-xs">View plans</Link>
      </div>
    );
  }
  const expires = new Date(subscription.expires_at);
  const daysLeft = Math.ceil((expires - new Date()) / (1000 * 60 * 60 * 24));
  const expiringSoon = daysLeft <= 30;
  const isCancelled = subscription.status === "cancelled";
  return (
    <div className="card p-4" data-testid={`sub-status-${profile.partner_type}-active`}>
      <div className="flex items-center justify-between gap-2">
        <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider ${isCancelled ? "text-[#B86A5C]" : "text-[#2E5C46]"}`}>
          <CheckCircle2 size={11} strokeWidth={2} /> {isCancelled ? "Licensed (cancellation queued)" : "Licensed"}
        </span>
        <span className={`text-[10px] uppercase tracking-wider ${expiringSoon ? "text-[#B86A5C]" : "text-[#5C6B6B]"}`}>
          {daysLeft} day{daysLeft === 1 ? "" : "s"} left
        </span>
      </div>
      <p className="font-medium text-sm mt-2">{subscription.plan?.name || "Active subscription"}</p>
      <p className="text-xs text-[#5C6B6B]">Expires {expires.toLocaleDateString()}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {expiringSoon && (
          <Link to={`/partner/subscribe?type=${profile.partner_type}`} className="btn-outline text-xs" data-testid={`renew-${profile.partner_type}`}>
            Renew
          </Link>
        )}
        <button
          onClick={() => { setShowActions((v) => !v); if (!plans.length) loadPlans(); }}
          className="btn-outline text-xs"
          data-testid={`manage-sub-${profile.partner_type}`}
        >
          Manage
        </button>
      </div>

      {showActions && (
        <div className="mt-3 pt-3 border-t border-[#E5E1D8] space-y-2" data-testid={`manage-panel-${profile.partner_type}`}>
          {!showChange && !cancelOpen && (
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => setShowChange(true)} className="btn-outline text-xs" data-testid={`change-plan-${profile.partner_type}`}>
                Change plan
              </button>
              {!isCancelled && (
                <button onClick={() => setCancelOpen(true)} className="btn-outline text-xs text-[#9E3C3C] border-[#9E3C3C]/40" data-testid={`cancel-sub-${profile.partner_type}`}>
                  Cancel renewal
                </button>
              )}
            </div>
          )}
          {showChange && (
            <div className="space-y-2" data-testid={`change-panel-${profile.partner_type}`}>
              <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">Switch to:</p>
              {plans.filter((p) => p.id !== subscription.plan_id).map((p) => (
                <div key={p.id} className="flex items-center justify-between gap-2 border border-[#E5E1D8] rounded p-2">
                  <div className="min-w-0">
                    <p className="text-xs font-medium truncate">{p.name}</p>
                    <p className="text-[10px] text-[#5C6B6B]">${p.price_usd} · {p.duration_months}mo</p>
                  </div>
                  <button
                    onClick={() => previewChange(p.id)}
                    disabled={previewing === p.id}
                    className="text-[10px] uppercase tracking-wider text-[#476B6B] hover:underline"
                    data-testid={`preview-change-${p.id}`}
                  >
                    {previewing === p.id ? "…" : "Preview"}
                  </button>
                </div>
              ))}
              {preview && (
                <div className="card p-3 bg-[#FAF8F5]" data-testid={`change-preview-${profile.partner_type}`}>
                  <p className="text-xs font-medium">{preview.new_plan_name}</p>
                  <table className="text-xs w-full mt-2">
                    <tbody>
                      <tr><td className="text-[#5C6B6B]">New plan price</td><td className="text-right">${preview.new_plan_price_usd.toFixed(2)}</td></tr>
                      <tr><td className="text-[#5C6B6B]">Prorated credit</td><td className="text-right text-[#2E5C46]">− ${preview.prorated_credit_usd.toFixed(2)}</td></tr>
                      <tr className="font-medium border-t border-[#E5E1D8]"><td>Due today</td><td className="text-right">${preview.amount_due_usd.toFixed(2)}</td></tr>
                    </tbody>
                  </table>
                  <div className="flex gap-2 mt-3">
                    <button onClick={confirmChange} disabled={busy} className="btn-primary text-xs" data-testid={`confirm-change-${profile.partner_type}`}>
                      {busy ? "Saving…" : preview.amount_due_usd > 0 ? "Continue to checkout" : "Apply free upgrade"}
                    </button>
                    <button onClick={() => { setPreview(null); }} className="btn-outline text-xs">Back</button>
                  </div>
                </div>
              )}
              <button onClick={() => { setShowChange(false); setPreview(null); }} className="text-[10px] uppercase tracking-wider text-[#5C6B6B] hover:underline">Close</button>
            </div>
          )}
          {cancelOpen && (
            <div className="space-y-2" data-testid={`cancel-panel-${profile.partner_type}`}>
              <p className="text-xs text-[#1A2424]">
                Your license stays active until <strong>{expires.toLocaleDateString()}</strong>. No refunds — but you won't be prompted to renew.
              </p>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="What's prompting this? (optional, helps us improve)"
                className="input-field text-xs w-full"
                rows={3}
                data-testid={`cancel-reason-${profile.partner_type}`}
              />
              <div className="flex gap-2">
                <button onClick={submitCancel} disabled={busy} className="btn-primary text-xs bg-[#9E3C3C] hover:bg-[#7E2C2C]" data-testid={`confirm-cancel-${profile.partner_type}`}>
                  {busy ? "Saving…" : "Confirm cancel"}
                </button>
                <button onClick={() => setCancelOpen(false)} className="btn-outline text-xs">Back</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
