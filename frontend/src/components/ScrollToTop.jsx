import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * ScrollToTop — resets window scroll on route change.
 *
 * React Router preserves scroll position by default, which is the wrong
 * behaviour for top-level page navigation (a user clicking a Nav link from
 * the bottom of a long page expects the next page to start at the top).
 *
 * Respects in-page anchor links (e.g. /equip#founder-collection) so anchor
 * jumps still work normally.
 */
export default function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    // If the URL has a hash, let the browser handle the anchor jump.
    if (hash) return;
    // Reset both the window scroll and the documentElement (for browsers that
    // route scroll position to <html>).
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname, hash]);

  return null;
}
