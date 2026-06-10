/**
 * birthright Universal Share & Save System — v1.11.0 Step 8.5
 *
 * Builds share URLs with `?via=<token>` referral attribution, calls
 * `/api/shares/log` for analytics + cookie-setting, and exposes a
 * polymorphic bookmark toggle for logged-in users.
 *
 * Token resolution:
 *  - Logged-in users: lazy-load /api/me/share-token; cached in sessionStorage
 *  - Anonymous: use/seed a `bright_anon` session id in localStorage
 */
import api from "./api";

const ANON_KEY = "bright_anon_session";
const TOKEN_CACHE_KEY = "bright_share_token";

function genAnonId() {
  const rand =
    (typeof crypto !== "undefined" && crypto.randomUUID)
      ? crypto.randomUUID().slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
  return `anon-${rand}`;
}

export function getAnonSessionId() {
  if (typeof window === "undefined") return null;
  try {
    let v = localStorage.getItem(ANON_KEY);
    if (!v) {
      v = genAnonId();
      localStorage.setItem(ANON_KEY, v);
    }
    return v;
  } catch {
    return genAnonId();
  }
}

/** Resolve the share token for the current viewer. Cached for the tab session. */
export async function getViaToken({ user } = {}) {
  if (typeof window === "undefined") return null;
  try {
    if (user) {
      const cached = sessionStorage.getItem(TOKEN_CACHE_KEY);
      if (cached) return cached;
      const { data } = await api.get("/me/share-token");
      if (data?.via) {
        sessionStorage.setItem(TOKEN_CACHE_KEY, data.via);
        return data.via;
      }
    }
  } catch {
    // fall through to anon
  }
  return getAnonSessionId();
}

/** Build a full share URL with `?via=` appended.
 *
 * Routes through /api/link-preview so that bot User-Agents (Facebook, Twitter,
 * iMessage, Slack, WhatsApp, LinkedIn, Discord, etc.) receive Open Graph
 * meta tags for the specific resource being shared (image, title, description).
 * Humans are 302-redirected to the canonical SPA URL with the via token intact.
 *
 * Anchor fragments (e.g. /shop#founder-collection) ride along as a query
 * string `hash` token because servers don't see #fragments — the rendered
 * OG stub then includes them in the final redirect URL.
 */
export function buildShareUrl(path, via) {
  if (typeof window === "undefined") return path;
  const origin = window.location.origin;
  // Normalise to a path string (strip origin if a full URL was passed)
  let pathOnly = path;
  if (path.startsWith("http")) {
    try {
      const parsed = new URL(path);
      pathOnly = `${parsed.pathname}${parsed.search}${parsed.hash}`;
    } catch { /* leave as-is */ }
  }
  if (!pathOnly.startsWith("/")) pathOnly = `/${pathOnly}`;

  const previewUrl = new URL(`${origin}/api/link-preview`);
  previewUrl.searchParams.set("path", pathOnly);
  if (via) previewUrl.searchParams.set("via", via);
  return previewUrl.toString();
}

/** Log a share event. Fire-and-forget; never throws. */
export async function logShare({ surface, surface_id, channel, via, path }) {
  try {
    await api.post("/shares/log", {
      surface,
      surface_id: surface_id || null,
      channel,
      via: via || null,
      path: path || (typeof window !== "undefined" ? window.location.pathname : null),
      session_id: getAnonSessionId(),
    });
  } catch {
    // analytics — silent
  }
}

/** Capture an inbound `?via=` from the URL and log it as a `landing` share event.
 *  Called once from App.js on mount. */
export async function captureInboundVia() {
  if (typeof window === "undefined") return;
  try {
    const params = new URLSearchParams(window.location.search);
    const via = params.get("via");
    if (!via) return;
    await logShare({
      surface: "page",
      surface_id: window.location.pathname,
      channel: "copy_link",
      via,
      path: window.location.pathname,
    });
    // Strip ?via= from the URL bar so it doesn't propagate further
    params.delete("via");
    const qs = params.toString();
    const newUrl = `${window.location.pathname}${qs ? `?${qs}` : ""}${window.location.hash || ""}`;
    window.history.replaceState({}, "", newUrl);
  } catch {
    // ignore
  }
}
