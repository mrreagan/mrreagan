import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cookie, X } from "lucide-react";

/**
 * CookieConsentBanner — GDPR/CCPA-friendly consent banner.
 *
 * Renders at the bottom of every page until the user makes a choice.
 * Choice is persisted in localStorage. "Reject all" is as prominent as
 * "Accept all" (EU regulatory expectation). Strictly-necessary cookies
 * (session, CSRF) are always on and not toggled here.
 *
 * Consent record is a simple string in localStorage — future work: send
 * the choice to the backend once we have a `consent_log` collection so we
 * can prove consent for a specific user + timestamp + version.
 */
const STORAGE_KEY = "br_cookie_consent_v1";
const CURRENT_VERSION = "2026-02-a";

export default function CookieConsentBanner() {
  const [choice, setChoice] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });

  // Older consent version → prompt again.
  const needsPrompt = !choice || !choice.startsWith(`${CURRENT_VERSION}:`);

  const persist = (decision) => {
    try {
      localStorage.setItem(STORAGE_KEY, `${CURRENT_VERSION}:${decision}:${new Date().toISOString()}`);
    } catch { /* private mode */ }
    setChoice(`${CURRENT_VERSION}:${decision}`);
  };

  if (!needsPrompt) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="cookie-consent-title"
      className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-md z-50 bg-[#0F2424] text-[#FBF3E4] shadow-2xl rounded-lg overflow-hidden"
      data-testid="cookie-consent-banner"
    >
      <div className="p-5">
        <div className="flex items-start gap-3">
          <Cookie size={18} strokeWidth={1.8} className="text-[#C9A961] shrink-0 mt-0.5" />
          <div className="flex-1">
            <h2 id="cookie-consent-title" className="font-serif text-lg leading-tight">
              We use cookies
            </h2>
            <p className="text-xs mt-2 leading-relaxed text-[#E5D7B3]">
              We use strictly-necessary cookies to keep you signed in and to keep the site secure.
              With your consent, we also use analytics cookies to understand how the site is used
              so we can improve it. See our{" "}
              <Link to="/legal/cookie-notice" className="underline hover:text-white" target="_blank">
                Cookie Notice
              </Link>{" "}
              and{" "}
              <Link to="/legal/privacy" className="underline hover:text-white" target="_blank">
                Privacy Policy
              </Link>.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 mt-4">
          <button
            onClick={() => persist("reject_all")}
            className="w-full text-xs font-semibold py-2 px-3 rounded border border-[#E5D7B3] text-[#FBF3E4] hover:bg-[#1a3535] transition"
            data-testid="cookie-reject-all"
          >
            Reject all (except necessary)
          </button>
          <button
            onClick={() => persist("accept_all")}
            className="w-full text-xs font-semibold py-2 px-3 rounded bg-[#C9A961] text-[#0F2424] hover:bg-[#D4B677] transition"
            data-testid="cookie-accept-all"
          >
            Accept all
          </button>
        </div>
      </div>
      <button
        onClick={() => persist("dismissed")}
        aria-label="Close cookie banner"
        className="absolute top-2 right-2 text-[#E5D7B3] hover:text-white p-1"
        data-testid="cookie-close"
      >
        <X size={14} strokeWidth={1.8} />
      </button>
    </div>
  );
}
