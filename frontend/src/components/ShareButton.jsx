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
  CalendarPlus, Quote, Check, X, Printer, Download, Send,
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
  allowPrint = true,       // universal — opens browser print
  bookmarkLabel,
  align = "right",
  size = "default",        // 'sm' | 'default'
  className = "",
  stopPropagation = false, // when nested inside clickable cards
}) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [showQr, setShowQr] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const [bookmarked, setBookmarked] = useState(false);
  const [bookmarkRow, setBookmarkRow] = useState(null);
  const [citeFormat, setCiteFormat] = useState(null);
  const [citeText, setCiteText] = useState("");
  const [showSendToPartner, setShowSendToPartner] = useState(false);
  const [partnerThreads, setPartnerThreads] = useState([]);
  const rootRef = useRef(null);
  const qrRef = useRef(null);

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

  // Outside click closer (desktop only — mobile uses the backdrop button)
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      // The mobile menu lives outside rootRef (fixed-positioned), so on
      // mobile we rely on the explicit backdrop tap. On desktop the menu
      // is inside rootRef and this handler closes it on outside click.
      if (window.matchMedia("(max-width: 639px)").matches) return;
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
        await navigator.share({ title: title || "birthright", url: shareUrl });
        fireLog("native_share");
      } catch { /* user cancelled */ }
    } else {
      handleCopy();
    }
  };

  const handleEmail = () => {
    const subj = encodeURIComponent(emailSubject || title || "From the birthright Foundation");
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

  const handlePrint = () => {
    fireLog("download");  // log as download-channel event
    setOpen(false);
    // give the menu a tick to close before printing
    setTimeout(() => { try { window.print(); } catch { /* ignore */ } }, 80);
  };

  const handleDownloadQr = () => {
    if (!shareUrl) return;
    const svgEl = qrRef.current?.querySelector("svg");
    if (!svgEl) {
      toast.error("Open the QR preview first");
      setShowQr(true);
      return;
    }
    try {
      const xml = new XMLSerializer().serializeToString(svgEl);
      const svg64 = btoa(unescape(encodeURIComponent(xml)));
      const img = new Image();
      img.onload = () => {
        const scale = 4;
        const canvas = document.createElement("canvas");
        canvas.width = (svgEl.viewBox?.baseVal?.width || svgEl.clientWidth || 200) * scale;
        canvas.height = (svgEl.viewBox?.baseVal?.height || svgEl.clientHeight || 200) * scale;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#FAF8F5";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const a = document.createElement("a");
        const safeName = (title || surface).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
        a.download = `birthright-qr-${safeName || "share"}.png`;
        a.href = canvas.toDataURL("image/png");
        a.click();
        toast.success("QR PNG downloaded");
        fireLog("download");
      };
      img.onerror = () => toast.error("Could not export QR");
      img.src = `data:image/svg+xml;base64,${svg64}`;
    } catch (e) {
      toast.error("Could not export QR");
    }
  };

  const openSendToPartner = async () => {
    if (!user) {
      toast.message("Sign in to send to a partner", { description: "Open a thread with any birthright partner." });
      return;
    }
    setShowSendToPartner(true);
    if (partnerThreads.length === 0) {
      try {
        const { data } = await api.get("/dm/threads");
        // Only show active threads where the other participant is a partner
        const filtered = (data || []).filter((t) =>
          (t.status === "active" || t.status === "pending") && t.other_participant?.partner_type
        );
        setPartnerThreads(filtered);
      } catch { /* silent */ }
    }
  };
  const sendToThread = async (threadId, otherName) => {
    if (!shareUrl) return;
    const message = `${title ? title + "\n" : ""}${shareUrl}`;
    try {
      await api.post(`/dm/threads/${threadId}/messages`, { content: message });
      toast.success(`Sent to ${otherName}`);
      fireLog("native_share");
      setShowSendToPartner(false);
      setOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send");
    }
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
    <div
      ref={rootRef}
      className={`relative inline-block ${className}`}
      data-testid={`share-button-${surface}`}
      onClick={stopPropagation ? (e) => e.stopPropagation() : undefined}
      onKeyDown={stopPropagation ? (e) => e.stopPropagation() : undefined}
    >
      <button
        type="button"
        onClick={(e) => { if (stopPropagation) e.stopPropagation(); setOpen((v) => !v); }}
        className={`inline-flex items-center gap-1.5 rounded-full border border-[#E5E1D8] bg-white hover:border-[#476B6B] hover:bg-[#FAF8F5] transition ${sizeCls}`}
        aria-haspopup="menu"
        aria-expanded={open}
        data-testid={`share-button-${surface}-trigger`}
      >
        <Share2 size={14} strokeWidth={1.5} />
        {showLabel && <span className="uppercase tracking-wider">Share</span>}
      </button>

      {open && (
        <>
          {/* Mobile backdrop — closes on outside tap and keeps the menu from
              falling off-screen. The menu itself becomes a centered modal on
              small screens via the wrapper class below. */}
          <div
            className="fixed inset-0 bg-black/40 sm:hidden z-40"
            onClick={() => setOpen(false)}
            data-testid={`share-backdrop-${surface}`}
          />
          <div
            className={`
              z-50 rounded-2xl border border-[#E5E1D8] bg-white shadow-xl p-3
              fixed inset-x-4 bottom-4 max-h-[80vh] overflow-y-auto
              sm:absolute sm:inset-auto sm:bottom-auto sm:mt-2 sm:w-72 sm:max-h-none sm:overflow-visible
              ${align === "left" ? "sm:left-0" : "sm:right-0"}
            `}
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
            <Action onClick={handleDownloadQr} icon={Download} label="Download QR" testid={`share-download-qr-${surface}`} />
            {allowPrint && (
              <Action onClick={handlePrint} icon={Printer} label="Print" testid={`share-print-${surface}`} />
            )}
            {user && (
              <Action onClick={openSendToPartner} icon={Send} label="To a partner" testid={`share-send-partner-${surface}`} />
            )}
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

          {showSendToPartner && (
            <div className="mt-3 p-3 bg-[#FAF8F5] border border-[#E5E1D8] rounded" data-testid={`send-to-partner-${surface}`}>
              <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-2">Send link to:</p>
              {partnerThreads.length === 0 ? (
                <p className="text-[11px] text-[#5C6B6B]">
                  No open partner threads. Visit a partner profile and click <strong>Message</strong> first.
                </p>
              ) : (
                <ul className="space-y-1 max-h-40 overflow-y-auto">
                  {partnerThreads.map((t) => (
                    <li key={t.id}>
                      <button
                        onClick={() => sendToThread(t.id, t.other_participant.name)}
                        className="w-full text-left px-2 py-1.5 text-xs rounded hover:bg-white border border-transparent hover:border-[#E5E1D8] flex items-center justify-between gap-2"
                        data-testid={`send-target-${t.id}`}
                      >
                        <span className="truncate">{t.other_participant.name}</span>
                        <span className="text-[9px] uppercase text-[#C9A961]">{t.other_participant.partner_type}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {showQr && shareUrl && (
            <div ref={qrRef} className="mt-3 p-3 bg-[#FAF8F5] border border-[#E5E1D8] rounded text-center" data-testid={`share-qr-preview-${surface}`}>
              <div className="bg-white inline-block p-2 border border-[#E5E1D8]">
                <QRCodeSVG value={shareUrl} size={132} bgColor="#FAF8F5" fgColor="#1A2424" level="M" />
              </div>
              <p className="mt-2 text-[10px] uppercase tracking-wider text-[#5C6B6B]">Scan to open</p>
            </div>
          )}
          {/* Hidden QR for instant Download QR — always rendered when URL ready */}
          {!showQr && shareUrl && (
            <div ref={qrRef} style={{ position: "absolute", left: "-9999px", top: "-9999px" }} aria-hidden="true">
              <QRCodeSVG value={shareUrl} size={132} bgColor="#FAF8F5" fgColor="#1A2424" level="M" />
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
        </>
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
