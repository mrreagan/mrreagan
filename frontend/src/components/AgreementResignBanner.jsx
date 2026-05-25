/** Banner shown across logged-in pages when the user hasn't signed the latest
 * active indemnification agreement. Clicking opens the agreement & accept flow. */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldAlert, X } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const DISMISS_KEY = "bright_agreement_banner_dismissed_for";

export default function AgreementResignBanner() {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get("/legal/indemnification/my-status")
      .then((r) => {
        setStatus(r.data);
        try {
          const stored = localStorage.getItem(DISMISS_KEY);
          if (stored === r.data?.active_version?.id) setDismissed(true);
        } catch {/* ignore */}
      })
      .catch(() => {});
  }, [user]);

  if (!user || !status?.active_version || status.signed || dismissed) return null;

  const dismiss = () => {
    setDismissed(true);
    try { localStorage.setItem(DISMISS_KEY, status.active_version.id); } catch {/* ignore */}
  };

  return (
    <div className="bg-[#FFF8E1] border-b border-[#C9A961]/40 px-6 py-3 flex items-center gap-3 print:hidden" data-testid="agreement-resign-banner">
      <ShieldAlert size={16} strokeWidth={1.5} className="text-[#8B7128] flex-shrink-0" />
      <div className="flex-1 text-sm text-[#8B7128]">
        <strong>Updated agreement (v{status.active_version.version}) requires your acceptance</strong> before you can open new direct messages or start a subscription.
      </div>
      <Link to="/legal/agreement" className="btn-primary text-xs" data-testid="agreement-review-link">
        Review & accept
      </Link>
      <button
        onClick={dismiss}
        className="text-[#8B7128] hover:text-[#1A2424] p-1"
        aria-label="Dismiss"
        data-testid="agreement-banner-dismiss"
      >
        <X size={14} strokeWidth={1.5} />
      </button>
    </div>
  );
}
