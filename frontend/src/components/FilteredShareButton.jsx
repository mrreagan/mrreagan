/**
 * FilteredShareButton — page-level share affordance that captures the
 * current URL (including search params reflecting active filters) and
 * uses native Web Share when available, falling back to clipboard copy.
 *
 * Usage:
 *   <FilteredShareButton title="Birthright shop" label="Share this view" />
 *
 * The button has no internal state about filters — it just reads
 * window.location.href when clicked. The page is responsible for keeping
 * its filter state in sync with the URL (useSearchParams).
 */
import React from "react";
import { toast } from "sonner";
import { Share2 } from "lucide-react";

export default function FilteredShareButton({ title, label = "Share this view", testId = "filtered-share-btn" }) {
  const onClick = async () => {
    const url = window.location.href;
    const data = { title: title || document.title, url };
    if (navigator.share) {
      try { await navigator.share(data); return; } catch (_) { /* user cancelled */ }
    }
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Link copied — your filters are baked into it.");
    } catch {
      toast.error("Couldn't copy link");
    }
  };
  return (
    <button
      onClick={onClick}
      data-testid={testId}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[#E5E1D8] bg-white text-xs text-[#1A2424] hover:border-[#476B6B] hover:text-[#476B6B] transition"
      title="Copy a link that preserves the filters you've applied"
    >
      <Share2 size={12} strokeWidth={1.8} /> {label}
    </button>
  );
}
