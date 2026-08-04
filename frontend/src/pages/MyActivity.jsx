/**
 * MyActivity — user-visible security event log.
 * URL: /account/activity
 *
 * Shows the current user their own logins, password changes, sensitive
 * signings, checkout confirmations, and account events. Admin URL traces
 * are hidden from this view (backend enforces).
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Shield, RefreshCw, Check, AlertTriangle, LogIn, LogOut, FileSignature, CreditCard, User } from "lucide-react";
import api from "../lib/api";
import { toast } from "sonner";

const CATEGORY_META = {
  auth: { label: "Sign-in", icon: LogIn, color: "text-[#476B6B]" },
  security: { label: "Security", icon: Shield, color: "text-[#8B4513]" },
  signing: { label: "Document signed", icon: FileSignature, color: "text-[#01784E]" },
  payment: { label: "Payment", icon: CreditCard, color: "text-[#C9A961]" },
  account: { label: "Account", icon: User, color: "text-[#5C6B6B]" },
};

const EVENT_LABELS = {
  "auth.login_success": "Signed in successfully",
  "auth.login_failed": "Sign-in attempt failed",
  "auth.logout": "Signed out",
  "auth.password_changed": "Password changed",
  "auth.password_reset_requested": "Password reset requested",
  "auth.password_reset_completed": "Password reset completed",
  "signing.terms_accepted": "Terms of Service accepted",
  "signing.privacy_accepted": "Privacy Policy accepted",
  "signing.indemnification_signed": "Indemnification agreement signed",
  "signing.partner_agreement_signed": "Partner agreement signed",
  "payment.checkout_completed": "Payment completed",
  "payment.subscription_started": "Subscription started",
  "payment.subscription_canceled": "Subscription canceled",
  "account.created": "Account created",
  "account.deleted": "Account deletion requested",
};

export default function MyActivity() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/account/activity?limit=200");
      setEvents(r.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load activity");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  return (
    <div className="container-page py-12" data-testid="my-activity-page">
      <Link to="/profile" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-4">
        <ArrowLeft size={14} strokeWidth={1.5} /> Profile
      </Link>

      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <span className="label">Security</span>
          <h1 className="editorial-h1 mt-1">Your recent activity</h1>
        </div>
        <button onClick={load} className="btn-outline text-xs inline-flex items-center gap-1" data-testid="refresh-btn">
          <RefreshCw size={12} strokeWidth={1.5} /> Refresh
        </button>
      </div>

      <div className="divider-flame" />

      <p className="text-sm text-[#5C6B6B] max-w-2xl leading-relaxed mt-4">
        A record of the security-relevant things that happened on your account — sign-ins,
        password changes, documents you signed, and payments. If anything here looks
        unfamiliar, change your password immediately and contact us.
      </p>

      <div className="mt-8">
        {loading ? (
          <p className="text-[#5C6B6B]">Loading…</p>
        ) : events.length === 0 ? (
          <div className="card p-6 text-sm text-[#5C6B6B]" data-testid="no-events">
            No activity recorded yet.
          </div>
        ) : (
          <div className="card divide-y divide-[#E8E4DC]" data-testid="events-list">
            {events.map((e) => {
              const cat = CATEGORY_META[e.category] || CATEGORY_META.account;
              const Icon = cat.icon;
              const isFailure = e.status_code && e.status_code >= 400;
              return (
                <div key={e.id} className="p-4 flex items-start gap-3" data-testid={`event-${e.id}`}>
                  <div className={`shrink-0 w-8 h-8 rounded-full bg-[#F4F1EA] flex items-center justify-center ${cat.color}`}>
                    {isFailure ? (
                      <AlertTriangle size={14} strokeWidth={1.8} />
                    ) : (
                      <Icon size={14} strokeWidth={1.8} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm text-[#0F2424]">
                      {EVENT_LABELS[e.event_type] || e.event_type}
                    </div>
                    <div className="text-xs text-[#5C6B6B] mt-0.5">
                      {new Date(e.timestamp).toLocaleString()} · {cat.label}
                    </div>
                    {isFailure && (
                      <div className="mt-2 text-xs text-[#8B0000] bg-[#F9E5E1] border border-[#F0C0B8] rounded px-2 py-1 inline-block">
                        This attempt was not successful.
                      </div>
                    )}
                  </div>
                  {!isFailure && (
                    <Check size={16} strokeWidth={2} className="text-[#01784E] shrink-0 mt-1" />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
