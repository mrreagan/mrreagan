/* AgreementResignBanner — header-mounted banner that surfaces when the
 * signed-in user hasn't accepted the currently-active legal indemnification
 * agreement.
 *
 * v2 enhancement (P2): now shows the per-partner list of write-side
 * actions that will be blocked until the user re-signs. This list is
 * computed server-side from the user's active partner_profiles.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, X, ArrowRight, Lock } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import api from "../lib/api";

export default function AgreementResignBanner() {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [dismissed, setDismissed] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (!user) { setStatus(null); return; }
    api.get("/legal/indemnification/my-status")
      .then((r) => setStatus(r.data))
      .catch(() => setStatus(null));
  }, [user]);

  if (!user || !status || dismissed) return null;
  if (!status.active_version) return null;
  if (status.signed) return null;

  const blocked = status.blocked_actions || [];

  return (
    <div className="bg-[#FFF6E5] border-b border-[#C9A961]" data-testid="agreement-resign-banner">
      <div className="container-page py-2.5 text-xs flex items-center gap-3 flex-wrap">
        <AlertTriangle size={14} strokeWidth={1.7} className="text-[#9E3C3C] shrink-0" />
        <p className="text-[#1A2424] leading-tight">
          <strong>Agreement v{status.active_version.version}</strong> is now active. Please review and re-sign to keep using partner write-features.
        </p>
        {blocked.length > 0 && (
          <button
            onClick={() => setShowDetails((s) => !s)}
            className="inline-flex items-center gap-1 text-[#9E3C3C] hover:underline"
            data-testid="agreement-banner-details-toggle"
          >
            <Lock size={11} strokeWidth={1.7} />
            {showDetails ? "Hide list" : `What's blocked? (${blocked.length})`}
          </button>
        )}
        <Link
          to="/legal/agreement"
          className="ml-auto inline-flex items-center gap-1 bg-[#476B6B] text-white px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-medium hover:bg-[#385454] transition"
          data-testid="agreement-banner-review"
        >
          Review &amp; sign <ArrowRight size={11} strokeWidth={1.7} />
        </Link>
        <button
          onClick={() => setDismissed(true)}
          className="text-[#5C6B6B] hover:text-[#1A2424]"
          aria-label="Dismiss"
          data-testid="agreement-banner-dismiss"
        >
          <X size={13} strokeWidth={1.7} />
        </button>
      </div>
      {showDetails && blocked.length > 0 && (
        <div className="container-page pb-3 -mt-1" data-testid="agreement-banner-blocked-list">
          <ul className="text-[11px] text-[#5C6B6B] grid sm:grid-cols-2 gap-x-6 gap-y-0.5 pl-6">
            {blocked.map((b) => (
              <li key={b} className="flex items-baseline gap-1.5">
                <span className="text-[#9E3C3C]">·</span> {b}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
