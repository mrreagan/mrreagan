/**
 * ShareButton — Universal share & save affordance.
 *
 * Surfaces supported (see backend ShareSurface literal): workshop, product,
 * research, partner, facilitator, foundation_role, proposal, impact_statement.
 *
 * Channels exposed per surface (auto-narrowed):
 *  - Copy link        (always)
 *  - Native share     (mobile / supported browsers)
 *  - Email mailto:
 *  - SMS sms:
 *  - QR code preview  (always)
 *  - Bookmark/Save    (logged-in only)
 *  - Add to calendar  (.ics)  → workshop only
 *  - Cite             (APA 7 / BibTeX)  → research only
 *
 * Privacy gating: callers control whether to render this at all (e.g. NEVER
 * render on workshop materials, ledger rows, W9, payout method, admin panels).
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import {
  Share2, Copy, QrCode, Mail, MessageSquare, Bookmark, BookmarkCheck,
  CalendarPlus, Quote, Check, X,
} from "lucide-react";
import { toast } from "sonner";

import api, { API } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { buildShareUrl, getViaToken, logShare } from "../lib/shareUtils";

// Map surface → bookmark subject_type (a subset of surfaces is bookmarkable)
const BOOKMARK_TYPE_BY_SURFACE = {
  workshop: "workshop",
  product: "product",
  research: "research",
  partner: "partner",
  facilitator: "facilitator",
  foundation_role: "foundation_role",
  proposal: "proposal",
  impact_statement: "impact_statement",
};

const LABEL_BY_SURFACE = {
  workshop: "this workshop",
  product: "this product",
  research: "this research",
  partner: "this partner",
  facilitator: "this facilitator",
  foundation_role: "this open role",
  proposal: "this proposal",
  impact_statement: "this story",
  page: "this page",
};

export default function ShareButton({
  surface,
  surfaceId,
  path,
  title,
  emailSubject,
  showLabel = false,
  allowBookmark = true,
  allowCalendar,           // auto-true for workshop unless explicitly false
  allowCite,               // auto-true for research unless explicitly false
  bookmarkLabel,
  align = "right",
  size = "default",        // 'sm' | 'default'
  className = "",
}) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [showQr, setShowQr] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const [bookmarked, setBookmarked] = useState(false);
  const [bookmarkRow, setBookmarkRow] = useState(null);
  const [citeFormat, setCiteFormat] = useState(null);
  const [citeText, setCiteText] = useState("");
  const rootRef = useRef(null);

  const isWorkshop = surface === "workshop";
  const isResearch = surface === "research";
  const enableIcs = allowCalendar !== false && isWorkshop;
  const enableCite = allowCite !== false && isResearch;
  const label = LABEL_BY_SURFACE[surface] || "this";
  const bookmarkable = !!user && allowBookmark && BOOKMARK_TYPE_BY_SURFACE[surface];

  // Build share URL lazily when menu opens
  useEffect(() => {
    if (!open || shareUrl) return;
    let cancelled = false;
    (async () => {
      const via = await getViaToken({ user });
      const url = buildShareUrl(path || (typeof window !== "undefined" ? window.location.pathname : "/"), via);
      if (!cancelled) setShareUrl(url);
    })();
    return () => { cancelled = true; };
  }, [open, path, user, shareUrl]);

  // Detect existing bookmark state when menu opens
  useEffect(() => {
    if (!open || !bookmarkable || !surfaceId) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/me/bookmarks?subject_type=${BOOKMARK_TYPE_BY_SURFACE[surface]}`);
        if (cancelled) return;
        const existing = (data || []).find((b) => b.subject_id === surfaceId);
        if (existing) { setBookmarked(true); setBookmarkRow(existing); }
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, [open, bookmarkable, surface, surfaceId]);

  // Outside click closer
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false); setShowQr(false); setCiteFormat(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const fireLog = (channel) =>
    logShare({ surface, surface_id: surfaceId, channel, path });

  const handleCopy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success("Link copied");
    } catch {
      toast.error("Could not copy");
    }
    fireLog("copy_link");
  };

  const handleNativeShare = async () => {
    if (!shareUrl) return;
    if (navigator.share) {
      try {
        await navigator.share({ title: title || "Birthright", url: shareUrl });
        fireLog("native_share");
      } catch { /* user cancelled */ }
    } else {
      handleCopy();
    }
  };

  const handleEmail = () => {
    const subj = encodeURIComponent(emailSubject || title || "From the Birthright Foundation");
    const body = encodeURIComponent(`${title ? title + "\n\n" : ""}${shareUrl}`);
    window.open(`mailto:?subject=${subj}&body=${body}`, "_blank");
    fireLog("email");
  };

  const handleSms = () => {
    const body = encodeURIComponent(`${title ? title + " — " : ""}${shareUrl}`);
    window.open(`sms:?body=${body}`, "_blank");
    fireLog("sms");
  };

  const handleIcs = () => {
    if (!surfaceId) return;
    window.open(`${API}/workshops/${surfaceId}/ics`, "_blank");
    fireLog("ics");
  };

  const handleCite = async (format) => {
    if (!surfaceId) return;
    try {
      const { data } = await api.get(`/research/${surfaceId}/cite?format=${format}`);
      setCiteFormat(format);
      setCiteText(data.citation || "");
      try { await navigator.clipboard.writeText(data.citation || ""); toast.success("Citation copied"); }
      catch { /* leave on screen */ }
      fireLog("cite");
    } catch (e) {
      toast.error("Could not generate citation");
    }
  };

  const handleBookmarkToggle = async () => {
    if (!user) { toast.message("Sign in to save", { description: "Bookmarks live in your account." }); return; }
    if (!surfaceId) return;
    if (bookmarked && bookmarkRow) {
      try {
        await api.delete(`/me/bookmarks/${bookmarkRow.id}`);
        setBookmarked(false); setBookmarkRow(null);
        toast.success("Removed bookmark");
      } catch { toast.error("Could not remove bookmark"); }
    } else {
      try {
        const { data } = await api.post("/me/bookmarks", {
          subject_type: BOOKMARK_TYPE_BY_SURFACE[surface],
          subject_id: surfaceId,
          label: bookmarkLabel || title || null,
        });
        setBookmarked(true); setBookmarkRow(data);
        toast.success("Saved to bookmarks");
        fireLog("bookmark");
      } catch { toast.error("Could not bookmark"); }
    }
  };

  const sizeCls =
    size === "sm"
      ? "px-2 py-1 text-[11px]"
      : "px-3 py-1.5 text-xs";

  return (
    <div ref={rootRef} className={`relative inline-block ${className}`} data-testid={`share-button-${surface}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1.5 rounded-full border border-[#E5E1D8] bg-white hover:border-[#476B6B] hover:bg-[#FAF8F5] transition ${sizeCls}`}
        aria-haspopup="menu"
        aria-expanded={open}
        data-testid={`share-button-${surface}-trigger`}
      >
        <Share2 size={14} strokeWidth={1.5} />
        {showLabel && <span className="uppercase tracking-wider">Share</span>}
      </button>

      {open && (
        <div
          className={`absolute z-30 mt-2 w-72 rounded-md border border-[#E5E1D8] bg-white shadow-lg p-3 ${align === "left" ? "left-0" : "right-0"}`}
          role="menu"
          data-testid={`share-menu-${surface}`}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">Share {label}</p>
            <button onClick={() => setOpen(false)} className="text-[#5C6B6B] hover:text-[#1A2424]" aria-label="Close">
              <X size={14} strokeWidth={1.5} />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <Action onClick={handleCopy} icon={Copy} label="Copy link" testid={`share-copy-${surface}`} />
            <Action onClick={handleNativeShare} icon={Share2} label="More…" testid={`share-native-${surface}`} />
            <Action onClick={handleEmail} icon={Mail} label="Email" testid={`share-email-${surface}`} />
            <Action onClick={handleSms} icon={MessageSquare} label="Text" testid={`share-sms-${surface}`} />
            <Action onClick={() => setShowQr((v) => !v)} icon={QrCode} label="QR code" testid={`share-qr-${surface}`} />
            {bookmarkable && (
              <Action
                onClick={handleBookmarkToggle}
                icon={bookmarked ? BookmarkCheck : Bookmark}
                label={bookmarked ? "Saved" : "Save"}
                testid={`share-bookmark-${surface}`}
                active={bookmarked}
              />
            )}
            {enableIcs && (
              <Action onClick={handleIcs} icon={CalendarPlus} label="Calendar (.ics)" testid={`share-ics-${surface}`} />
            )}
            {enableCite && (
              <>
                <Action onClick={() => handleCite("apa7")} icon={Quote} label="Cite APA 7" testid={`share-cite-apa-${surface}`} />
                <Action onClick={() => handleCite("bibtex")} icon={Quote} label="Cite BibTeX" testid={`share-cite-bibtex-${surface}`} />
              </>
            )}
          </div>

          {showQr && shareUrl && (
            <div className="mt-3 p-3 bg-[#FAF8F5] border border-[#E5E1D8] rounded text-center" data-testid={`share-qr-preview-${surface}`}>
              <div className="bg-white inline-block p-2 border border-[#E5E1D8]">
                <QRCodeSVG value={shareUrl} size={132} bgColor="#FAF8F5" fgColor="#1A2424" level="M" />
              </div>
              <p className="mt-2 text-[10px] uppercase tracking-wider text-[#5C6B6B]">Scan to open</p>
            </div>
          )}

          {citeFormat && (
            <div className="mt-3 p-3 bg-[#FAF8F5] border border-[#E5E1D8] rounded" data-testid={`share-cite-preview-${surface}`}>
              <p className="text-[10px] uppercase tracking-wider text-[#C9A961] mb-1">{citeFormat.toUpperCase()} citation (copied)</p>
              <pre className="text-[11px] whitespace-pre-wrap break-words font-mono text-[#1A2424]">{citeText}</pre>
            </div>
          )}

          {shareUrl && (
            <div className="mt-3 text-[10px] text-[#5C6B6B] break-all" data-testid={`share-url-${surface}`}>
              {shareUrl}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Action({ onClick, icon: Icon, label, testid, active }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2 px-2.5 py-2 rounded text-xs border transition ${
        active
          ? "bg-[#476B6B] text-white border-[#476B6B]"
          : "border-[#E5E1D8] bg-white hover:border-[#476B6B] hover:bg-[#FAF8F5]"
      }`}
      data-testid={testid}
    >
      <Icon size={14} strokeWidth={1.5} />
      <span>{label}</span>
      {active && <Check size={12} className="ml-auto" strokeWidth={1.5} />}
    </button>
  );
}
