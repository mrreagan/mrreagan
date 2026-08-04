/**
 * CounselConsole — filtered admin console for counsel (and admin).
 *
 * Route: /counsel
 *
 * The public site keeps rendering the RELEASED .md until an admin
 * explicitly promotes the working draft via "Release as v{N}".
 *
 * Counsel can:
 *   - Download the released .docx
 *   - Upload a full replacement (.md or .docx) → creates/updates a working draft
 *   - Download the current working draft as .docx (for offline editing)
 *   - Mark the working draft "Ready for admin review"
 *   - Jump into the deep redline editor at /admin/legal/ratifications
 *
 * Admin can do everything counsel can, plus:
 *   - Release the working draft (auto-bumps minor version; override in modal)
 *   - Discard the working draft
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, Upload, Download, ShieldCheck, CheckCircle2, X as XIcon,
  Clock, FileText, MessageSquare, Send, Trash2, GitCompare, History, Undo2,
  CornerDownRight, MessageCircle,
} from "lucide-react";
import { toast } from "sonner";
import { diffLines } from "diff";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

export default function CounselConsole() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const isCounsel = user?.role === "readonly_admin";

  const [pages, setPages] = useState([]);
  const [ratifications, setRatifications] = useState([]);
  const [workingDrafts, setWorkingDrafts] = useState([]);
  const [busy, setBusy] = useState({});
  const [releaseModal, setReleaseModal] = useState(null); // { slug, defaultVersion }
  const [diffModal, setDiffModal] = useState(null); // { slug, title, released, working, wd }
  const [historyModal, setHistoryModal] = useState(null); // { slug, title }

  const loadAll = async () => {
    try {
      const [p, r, w] = await Promise.all([
        api.get("/legal/pages"),
        api.get("/legal/ratifications"),
        api.get("/legal/working-drafts"),
      ]);
      setPages(p.data || []);
      setRatifications(r.data || []);
      setWorkingDrafts(w.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load counsel console");
    }
  };

  useEffect(() => { loadAll(); }, []);

  // Public slug → source_slug map (mirrors PUBLIC_LEGAL_PAGES in the backend)
  const SOURCE_SLUG = {
    "terms": "01-terms-of-service",
    "privacy": "02-privacy-policy",
    "cookie-notice": "03-cookie-notice",
    "refunds": "15-refund-returns-policy",
    "scholarships": "10-sliding-scale-scholarship-terms",
    "community-standards": "14-community-standards",
  };

  // Index working drafts by source_slug for quick lookup
  const wdBySlug = useMemo(() => {
    const m = {};
    (workingDrafts || []).forEach((w) => { m[w.source_slug] = w; });
    return m;
  }, [workingDrafts]);

  // Latest ratification per source_slug
  const ratifiedBySlug = useMemo(() => {
    const m = {};
    (ratifications || []).forEach((r) => {
      if (!m[r.source_slug] || r.ratified_at > m[r.source_slug].ratified_at) {
        m[r.source_slug] = r;
      }
    });
    return m;
  }, [ratifications]);

  const setRowBusy = (slug, k, v) => setBusy((b) => ({ ...b, [`${slug}:${k}`]: v }));

  // -------- actions --------
  const uploadFullReplacement = async (sourceSlug, file) => {
    if (!file) return;
    if (!window.confirm(`Upload ${file.name} as the working version for this notice? The public site will still show the released version until an admin releases the working draft.`)) return;
    setRowBusy(sourceSlug, "upload", true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post(`/legal/docs/${sourceSlug}/upload`, fd);
      toast.success(`Working draft updated · ${r.data.bytes_written} bytes · state ${r.data.state}`);
      await loadAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Upload failed");
    } finally {
      setRowBusy(sourceSlug, "upload", false);
    }
  };

  const downloadReleased = async (sourceSlug, title) => {
    setRowBusy(sourceSlug, "dl-released", true);
    try {
      const r = await api.get(`/legal/drafts/${sourceSlug}`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url; a.download = `${title || sourceSlug}.released.docx`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Download failed");
    } finally {
      setRowBusy(sourceSlug, "dl-released", false);
    }
  };

  const downloadWorking = async (sourceSlug, title) => {
    setRowBusy(sourceSlug, "dl-working", true);
    try {
      const r = await api.get(`/legal/working-drafts/${sourceSlug}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url; a.download = `${title || sourceSlug}.working-draft.docx`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Download failed");
    } finally {
      setRowBusy(sourceSlug, "dl-working", false);
    }
  };

  const markReady = async (sourceSlug) => {
    if (!window.confirm("Mark this working draft ready for admin review? Editing after this will move it back to Draft. Admins will be notified by email.")) return;
    setRowBusy(sourceSlug, "ready", true);
    try {
      const r = await api.post(`/legal/working-drafts/${sourceSlug}/mark-ready`);
      const emailNote = r.data.email_scheduled ? " · admins notified" : " (already ready — no email)";
      toast.success(`Marked ready for admin${emailNote}`);
      await loadAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Mark-ready failed");
    } finally {
      setRowBusy(sourceSlug, "ready", false);
    }
  };

  const releaseNow = async (sourceSlug, version, notes) => {
    setRowBusy(sourceSlug, "release", true);
    try {
      const r = await api.post(`/legal/working-drafts/${sourceSlug}/release`, {
        version,
        notes,
        ratified_by: user?.email,
      });
      toast.success(`Released as v${r.data.released_as_version}`);
      setReleaseModal(null);
      await loadAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Release failed");
    } finally {
      setRowBusy(sourceSlug, "release", false);
    }
  };

  const discard = async (sourceSlug) => {
    const reason = window.prompt("Reason for discarding this working draft?");
    if (reason === null) return;
    setRowBusy(sourceSlug, "discard", true);
    try {
      await api.post(`/legal/working-drafts/${sourceSlug}/discard`, { reason });
      toast.success("Working draft discarded");
      await loadAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Discard failed");
    } finally {
      setRowBusy(sourceSlug, "discard", false);
    }
  };

  const openDiff = async (sourceSlug, title) => {
    setRowBusy(sourceSlug, "diff", true);
    try {
      const r = await api.get(`/legal/working-drafts/${sourceSlug}`);
      setDiffModal({
        slug: sourceSlug,
        title,
        released: r.data.released_md || "",
        working: r.data.content_md || "",
        wd: r.data,
      });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load diff");
    } finally {
      setRowBusy(sourceSlug, "diff", false);
    }
  };

  return (
    <div className="container-page py-12" data-testid="counsel-console-page">
      <div className="mb-6">
        <Link to={isAdmin ? "/admin" : "/dashboard"} className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B]">
          <ArrowLeft size={14} strokeWidth={1.5} /> {isAdmin ? "Admin Hub" : "Dashboard"}
        </Link>
      </div>

      <span className="label">Legal · Counsel Console</span>
      <h1 className="editorial-h1 mt-2 flex items-center gap-3">
        <ShieldCheck size={28} strokeWidth={1.2} /> Counsel Console
      </h1>
      <div className="divider-flame" />

      <div className="card p-5 max-w-3xl bg-[#FAF7F0]">
        <p className="text-sm text-[#0F2424] leading-relaxed">
          <strong>The workflow.</strong> Download the released doc, edit offline, upload the full replacement (or upload a changes-only .docx via <Link to="/admin/legal/ratifications" className="underline text-[#476B6B]">the redline editor</Link>). Every upload becomes a <strong>working version</strong> — the public site keeps showing the released version untouched. When you&apos;re ready, click <em>Mark ready for admin</em>. An admin releases it as a new version — that&apos;s the only step that changes what the public sees.
        </p>
        <p className="text-xs text-[#5C6B6B] mt-3 leading-relaxed">
          Accepted formats: <code>.md</code>, <code>.markdown</code>, <code>.txt</code>, <code>.docx</code>. Files up to 2 MB.
          {isCounsel && " Counsel accounts can create, edit, mark-ready, upload, and download. Release is admin-only."}
        </p>
      </div>

      <div className="grid gap-4 mt-8" data-testid="counsel-console-list">
        {pages.length === 0 && (
          <p className="text-sm text-[#5C6B6B]">No public legal pages configured yet.</p>
        )}
        {pages.map((p) => {
          const sourceSlug = SOURCE_SLUG[p.slug] || p.slug;
          const wd = wdBySlug[sourceSlug];
          const rat = ratifiedBySlug[sourceSlug];
          return (
            <div
              key={p.slug}
              className="card p-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"
              data-testid={`counsel-row-${sourceSlug}`}
            >
              {/* Left — title + status */}
              <div className="flex-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <h3 className="font-serif text-xl text-[#0F2424]">{p.title}</h3>
                  {rat ? (
                    <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#EAF3EA] text-[#1E4030] rounded-full px-2 py-0.5 font-semibold" data-testid={`counsel-row-${sourceSlug}-released-badge`}>
                      <CheckCircle2 size={11} /> Released v{rat.version}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#FFF6E3] text-[#7A5A1A] rounded-full px-2 py-0.5 font-semibold">
                      Draft only
                    </span>
                  )}
                  {wd && (
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 font-semibold ${wd.state === "awaiting_admin" ? "bg-[#E3EEF9] text-[#264D6B]" : "bg-[#FFF6E3] text-[#7A5A1A]"}`}
                      data-testid={`counsel-row-${sourceSlug}-wd-badge`}
                    >
                      <Clock size={11} /> {wd.state === "awaiting_admin" ? "Awaiting admin" : "Working draft"}
                    </span>
                  )}
                  {wd?.comment_stats?.total > 0 && (
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 font-semibold ${wd.comment_stats.open > 0 ? "bg-[#F5E6D6] text-[#7A4A1A]" : "bg-[#EAF3EA] text-[#1E4030]"}`}
                      data-testid={`counsel-row-${sourceSlug}-comments-badge`}
                    >
                      <MessageCircle size={11} /> {wd.comment_stats.open} open · {wd.comment_stats.total} total
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#5C6B6B] mt-1">
                  <Link to={`/legal/${p.slug}`} className="hover:text-[#476B6B]">/legal/{p.slug}</Link>
                  {wd && (
                    <>
                      {" · "}
                      last edit by <strong className="text-[#0F2424]">{wd.last_edited_by_email || wd.created_by_email}</strong>
                      {" ("}{wd.last_edited_by_role}{") "}
                      {new Date(wd.last_edited_at || wd.created_at).toLocaleString()}
                    </>
                  )}
                </p>
                {wd?.change_log?.length > 0 && (
                  <details className="mt-3" data-testid={`counsel-row-${sourceSlug}-log`}>
                    <summary className="text-xs uppercase tracking-wider text-[#476B6B] cursor-pointer inline-flex items-center gap-1">
                      <MessageSquare size={11} /> Change log · {wd.change_log.length}
                    </summary>
                    <ul className="mt-2 space-y-1 text-xs text-[#5C6B6B] pl-4 border-l border-[#E5E1D8]">
                      {wd.change_log.slice(-6).reverse().map((e, i) => (
                        <li key={i}>
                          <span className="text-[#0F2424]">{e.action}</span>
                          {" · "}
                          {e.by_email} ({e.by_role})
                          {" · "}
                          {new Date(e.at).toLocaleString()}
                          {e.note && <div className="text-[#5C6B6B]">{e.note}</div>}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>

              {/* Right — actions */}
              <div className="flex flex-wrap gap-2 lg:justify-end lg:min-w-[380px]">
                <button
                  onClick={() => setHistoryModal({ slug: sourceSlug, title: p.title })}
                  className="btn-outline text-xs inline-flex items-center gap-1"
                  data-testid={`counsel-row-${sourceSlug}-history-btn`}
                >
                  <History size={12} /> History
                </button>

                <button
                  onClick={() => downloadReleased(sourceSlug, p.title)}
                  disabled={!!busy[`${sourceSlug}:dl-released`]}
                  className="btn-outline text-xs inline-flex items-center gap-1"
                  data-testid={`counsel-row-${sourceSlug}-download-released`}
                >
                  <Download size={12} /> Released (.docx)
                </button>

                {wd && (
                  <button
                    onClick={() => openDiff(sourceSlug, p.title)}
                    disabled={!!busy[`${sourceSlug}:diff`]}
                    className="btn-outline text-xs inline-flex items-center gap-1"
                    data-testid={`counsel-row-${sourceSlug}-view-diff`}
                  >
                    <GitCompare size={12} /> View diff
                  </button>
                )}

                {wd && (
                  <button
                    onClick={() => downloadWorking(sourceSlug, p.title)}
                    disabled={!!busy[`${sourceSlug}:dl-working`]}
                    className="btn-outline text-xs inline-flex items-center gap-1"
                    data-testid={`counsel-row-${sourceSlug}-download-working`}
                  >
                    <Download size={12} /> Working (.docx)
                  </button>
                )}

                <label
                  className={`btn-primary text-xs inline-flex items-center gap-1 cursor-pointer ${busy[`${sourceSlug}:upload`] ? "opacity-60 pointer-events-none" : ""}`}
                  data-testid={`counsel-row-${sourceSlug}-upload-btn`}
                >
                  <Upload size={12} />
                  {busy[`${sourceSlug}:upload`] ? "Uploading…" : "Upload replacement"}
                  <input
                    type="file"
                    accept=".md,.markdown,.txt,.docx"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      // Reset the input immediately so re-selecting the same
                      // file fires change again — otherwise browsers dedupe.
                      e.target.value = "";
                      if (f) uploadFullReplacement(sourceSlug, f);
                    }}
                    data-testid={`counsel-row-${sourceSlug}-upload-input`}
                    disabled={!!busy[`${sourceSlug}:upload`]}
                  />
                </label>

                {wd?.state === "draft" && (
                  <button
                    onClick={() => markReady(sourceSlug)}
                    disabled={!!busy[`${sourceSlug}:ready`]}
                    className="btn-outline text-xs inline-flex items-center gap-1 text-[#264D6B] border-[#264D6B]"
                    data-testid={`counsel-row-${sourceSlug}-mark-ready`}
                  >
                    <Send size={12} /> Mark ready for admin
                  </button>
                )}

                {isAdmin && wd && (
                  <>
                    <button
                      onClick={() => setReleaseModal({ slug: sourceSlug, title: p.title, wd })}
                      disabled={!!busy[`${sourceSlug}:release`]}
                      className="btn-primary text-xs inline-flex items-center gap-1 bg-[#1E4030]"
                      data-testid={`counsel-row-${sourceSlug}-release-btn`}
                    >
                      <ShieldCheck size={12} /> Release
                    </button>
                    <button
                      onClick={() => discard(sourceSlug)}
                      disabled={!!busy[`${sourceSlug}:discard`]}
                      className="btn-outline text-xs inline-flex items-center gap-1 text-[#9E3C3C] border-[#9E3C3C]"
                      data-testid={`counsel-row-${sourceSlug}-discard-btn`}
                    >
                      <Trash2 size={12} /> Discard
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-[#5C6B6B] mt-8 max-w-3xl">
        Need the fine-grained redline / comment workflow?
        <Link to="/admin/legal/ratifications" className="underline text-[#476B6B] ml-1" data-testid="counsel-console-redline-link">
          Open the redline editor →
        </Link>
      </p>

      {/* Release modal — admin only */}
      {releaseModal && isAdmin && (
        <ReleaseModal
          data={releaseModal}
          ratifications={ratifications}
          onCancel={() => setReleaseModal(null)}
          onRelease={(version, notes) => releaseNow(releaseModal.slug, version, notes)}
          busy={!!busy[`${releaseModal.slug}:release`]}
        />
      )}

      {/* Diff modal — anyone with counsel-console access */}
      {diffModal && (
        <DiffModal
          data={diffModal}
          currentUser={user}
          onClose={() => setDiffModal(null)}
          onRelease={isAdmin ? () => {
            setReleaseModal({ slug: diffModal.slug, title: diffModal.title, wd: diffModal.wd });
            setDiffModal(null);
          } : null}
        />
      )}

      {/* Release history modal — anyone with counsel-console access */}
      {historyModal && (
        <HistoryModal
          data={historyModal}
          isAdmin={isAdmin}
          onClose={() => setHistoryModal(null)}
          onRolledBack={async () => { setHistoryModal(null); await loadAll(); }}
        />
      )}
    </div>
  );
}

// ---------- Release modal ----------
function ReleaseModal({ data, ratifications, onCancel, onRelease, busy }) {
  const { slug, title, wd } = data;
  const latest = (ratifications || []).filter((r) => r.source_slug === slug).sort((a, b) => (b.ratified_at || "").localeCompare(a.ratified_at || ""))[0];
  const defaultVersion = bumpMinor(latest?.version || "");
  const [version, setVersion] = useState(defaultVersion);
  const [notes, setNotes] = useState(`Released working draft ${wd?.id?.slice(0, 8) || ""}`);
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[60] p-4" data-testid="release-modal">
      <div className="bg-[#FBF3E4] rounded-2xl max-w-md w-full p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="label">Release working draft</span>
            <h2 className="font-serif text-2xl mt-1">{title}</h2>
          </div>
          <button onClick={onCancel} className="text-[#5C6B6B] hover:text-[#0F2424]" data-testid="release-modal-close">
            <XIcon size={18} />
          </button>
        </div>
        <p className="text-xs text-[#5C6B6B] mt-3">
          Promoting the working draft overwrites the released .md, rebuilds the .docx bundle, and creates a new ratification record. The public site will start showing this version immediately.
        </p>
        <div className="mt-4 space-y-3">
          <div>
            <label className="label block mb-1">Version</label>
            <input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="e.g. 1.3"
              className="input input-bordered w-full text-sm"
              data-testid="release-modal-version"
            />
            <p className="text-[10px] text-[#5C6B6B] mt-1">Prior released version: <strong>{latest?.version || "none"}</strong> · default is a minor bump.</p>
          </div>
          <div>
            <label className="label block mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input input-bordered w-full text-sm h-20"
              data-testid="release-modal-notes"
            />
          </div>
        </div>
        <div className="mt-5 flex gap-2 justify-end">
          <button onClick={onCancel} className="btn-outline text-sm" data-testid="release-modal-cancel">Cancel</button>
          <button
            onClick={() => onRelease(version.trim(), notes.trim())}
            disabled={busy || !version.trim()}
            className="btn-primary text-sm inline-flex items-center gap-1 bg-[#1E4030]"
            data-testid="release-modal-confirm"
          >
            <ShieldCheck size={14} /> {busy ? "Releasing…" : `Release v${version || "?"}`}
          </button>
        </div>
      </div>
    </div>
  );
}

function bumpMinor(v) {
  if (!v) return "1.0";
  const parts = String(v).split(".");
  const last = parts.pop();
  const n = parseInt(last, 10);
  if (Number.isNaN(n)) return `${v}.1`;
  parts.push(String(n + 1));
  return parts.join(".");
}

// ---------- Diff modal — side-by-side redline ----------
function DiffModal({ data, onClose, onRelease, currentUser }) {
  const { slug, title, released, working, wd } = data;
  const [mode, setMode] = useState("side"); // "side" | "unified"
  const [comments, setComments] = useState([]);
  const [composeLine, setComposeLine] = useState(null); // number or null (general)
  const [composeBody, setComposeBody] = useState("");
  const [composing, setComposing] = useState(false);

  // Line-level diff. Each part has {value, added?, removed?, count}.
  const parts = useMemo(() => diffLines(released || "", working || ""), [released, working]);

  // Build aligned left/right rows for side-by-side view.
  const rows = useMemo(() => buildRows(parts), [parts]);

  const stats = useMemo(() => {
    let added = 0, removed = 0;
    for (const p of parts) {
      const lc = (p.value.match(/\n/g) || []).length || (p.value ? 1 : 0);
      if (p.added) added += lc;
      else if (p.removed) removed += lc;
    }
    return { added, removed };
  }, [parts]);

  const loadComments = React.useCallback(async () => {
    if (!slug) return;
    try {
      const r = await api.get(`/legal/working-drafts/${slug}/comments`);
      setComments(r.data || []);
    } catch (e) {
      // silent — comments panel just stays empty
      console.warn("comments load failed", e);
    }
  }, [slug]);

  useEffect(() => { loadComments(); }, [loadComments]);

  const postComment = async (body, lineNumber, parentId) => {
    setComposing(true);
    try {
      await api.post(`/legal/working-drafts/${slug}/comments`, {
        body,
        line_number: lineNumber ?? null,
        side: lineNumber != null ? "working" : "general",
        parent_id: parentId || null,
      });
      setComposeBody("");
      await loadComments();
      toast.success("Comment posted");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Post failed");
    } finally {
      setComposing(false);
    }
  };

  const resolveComment = async (c, resolved) => {
    try {
      await api.post(`/legal/working-drafts/${slug}/comments/${c.id}/resolve`, { resolved });
      await loadComments();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Resolve failed");
    }
  };

  const deleteComment = async (c) => {
    if (!window.confirm("Delete this comment (and any replies)?")) return;
    try {
      await api.delete(`/legal/working-drafts/${slug}/comments/${c.id}`);
      await loadComments();
      toast.success("Comment deleted");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Delete failed");
    }
  };

  const openCount = comments.filter((c) => !c.resolved).length;
  const totalCount = comments.length;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-stretch justify-center z-[60] p-4" data-testid="diff-modal">
      <div className="bg-[#FBF3E4] rounded-2xl max-w-6xl w-full flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 p-5 border-b border-[#E5E1D8]">
          <div className="min-w-0">
            <span className="label">Working draft vs. released</span>
            <h2 className="font-serif text-2xl mt-1 truncate">{title}</h2>
            <p className="text-xs text-[#5C6B6B] mt-1">
              <span className="text-[#2E5C46] font-semibold" data-testid="diff-stat-added">+{stats.added} added</span>
              {" · "}
              <span className="text-[#9E3C3C] font-semibold" data-testid="diff-stat-removed">-{stats.removed} removed</span>
              {" · "}
              <span>state <strong>{wd?.state}</strong></span>
              {totalCount > 0 && (
                <>
                  {" · "}
                  <span className="text-[#7A4A1A] font-semibold" data-testid="diff-comment-count">
                    {openCount} open / {totalCount} comment{totalCount === 1 ? "" : "s"}
                  </span>
                </>
              )}
              {" · "}
              <span>last edit by {wd?.last_edited_by_email || wd?.created_by_email}</span>
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="rounded-full bg-white/70 p-0.5 flex text-xs">
              <button
                onClick={() => setMode("side")}
                className={`px-3 py-1 rounded-full ${mode === "side" ? "bg-[#0F2424] text-[#FBF3E4]" : "text-[#0F2424]"}`}
                data-testid="diff-mode-side"
              >Side-by-side</button>
              <button
                onClick={() => setMode("unified")}
                className={`px-3 py-1 rounded-full ${mode === "unified" ? "bg-[#0F2424] text-[#FBF3E4]" : "text-[#0F2424]"}`}
                data-testid="diff-mode-unified"
              >Unified</button>
            </div>
            <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#0F2424]" data-testid="diff-modal-close">
              <XIcon size={20} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto bg-white" data-testid="diff-modal-body">
          {mode === "side" ? (
            <table className="w-full font-mono text-xs" style={{ tableLayout: "fixed" }}>
              <thead className="sticky top-0 bg-[#FAF7F0] text-[#5C6B6B] uppercase tracking-wider text-[10px] z-10">
                <tr>
                  <th className="w-10 px-1 py-2 text-right"></th>
                  <th className="px-3 py-2 text-left border-r border-[#E5E1D8]">Released</th>
                  <th className="w-10 px-1 py-2 text-right"></th>
                  <th className="px-3 py-2 text-left">Working draft</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => {
                  const lineComments = row.rightNum != null
                    ? comments.filter((c) => c.line_number === row.rightNum)
                    : [];
                  return (
                    <React.Fragment key={i}>
                      <tr className="align-top group">
                        <td className={`w-10 px-1 py-0.5 text-right text-[#B7B0A0] select-none ${row.leftClass}`}>{row.leftNum ?? ""}</td>
                        <td className={`px-3 py-0.5 whitespace-pre-wrap break-words border-r border-[#F0EDE3] ${row.leftClass}`}>
                          {row.left ?? ""}
                        </td>
                        <td className={`w-10 px-1 py-0.5 text-right text-[#B7B0A0] select-none ${row.rightClass} relative`}>
                          {row.rightNum ?? ""}
                          {row.rightNum != null && (
                            <button
                              onClick={() => setComposeLine(row.rightNum)}
                              className="absolute -left-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 bg-[#0F2424] text-[#FBF3E4] rounded-full w-4 h-4 flex items-center justify-center text-[10px] leading-none hover:bg-[#476B6B] transition-opacity"
                              aria-label={`Add comment on line ${row.rightNum}`}
                              data-testid={`diff-add-comment-line-${row.rightNum}`}
                            >+</button>
                          )}
                        </td>
                        <td className={`px-3 py-0.5 whitespace-pre-wrap break-words ${row.rightClass}`}>
                          {row.right ?? ""}
                        </td>
                      </tr>
                      {lineComments.length > 0 && (
                        <tr>
                          <td colSpan={4} className="bg-[#FAF7F0] px-3 py-2 border-y border-[#E5E1D8]">
                            <InlineCommentThread
                              comments={lineComments}
                              allComments={comments}
                              lineNumber={row.rightNum}
                              currentUser={currentUser}
                              onReply={(body, parentId) => postComment(body, row.rightNum, parentId)}
                              onResolve={resolveComment}
                              onDelete={deleteComment}
                            />
                          </td>
                        </tr>
                      )}
                      {composeLine != null && composeLine === row.rightNum && (
                        <tr>
                          <td colSpan={4} className="bg-[#FFF6E3] px-3 py-2 border-y border-[#E5E1D8]">
                            <ComposeForm
                              placeholder={`Ask a question about line ${row.rightNum}…`}
                              value={composeBody}
                              onChange={setComposeBody}
                              onCancel={() => { setComposeLine(null); setComposeBody(""); }}
                              onSubmit={async () => {
                                if (!composeBody.trim()) return;
                                await postComment(composeBody.trim(), row.rightNum, null);
                                setComposeLine(null);
                              }}
                              busy={composing}
                              testidPrefix={`diff-compose-line-${row.rightNum}`}
                            />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="font-mono text-xs">
              {stats.added === 0 && stats.removed === 0 ? (
                <div className="p-8 text-center text-[#5C6B6B]" data-testid="diff-empty-state">
                  Working draft is identical to the released version.
                </div>
              ) : parts.map((p, i) => {
                const bg = p.added ? "bg-[#EAF3EA] text-[#1E4030]"
                  : p.removed ? "bg-[#FBEBEB] text-[#7A2E2E]"
                  : "text-[#0F2424]";
                const prefix = p.added ? "+ " : p.removed ? "- " : "  ";
                return (
                  <div key={i} className={`px-3 py-0.5 whitespace-pre-wrap break-words ${bg}`}>
                    {p.value.replace(/\n$/, "").split("\n").map((l, j) => (
                      <div key={j}>{prefix}{l}</div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}

          {/* General comments (not anchored to a line) */}
          <GeneralCommentsPanel
            comments={comments.filter((c) => c.line_number == null)}
            allComments={comments}
            currentUser={currentUser}
            composing={composing}
            composeBody={composeBody}
            setComposeBody={setComposeBody}
            onPost={(body, parentId) => postComment(body, null, parentId)}
            onResolve={resolveComment}
            onDelete={deleteComment}
          />
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#E5E1D8] flex items-center justify-between bg-[#FAF7F0]">
          <p className="text-xs text-[#5C6B6B]">
            Released body is untouched until admin releases the working draft.
          </p>
          <div className="flex gap-2">
            <button onClick={onClose} className="btn-outline text-sm" data-testid="diff-modal-cancel">
              Close
            </button>
            {onRelease && (
              <button
                onClick={onRelease}
                className="btn-primary text-sm inline-flex items-center gap-1 bg-[#1E4030]"
                data-testid="diff-modal-release"
              >
                <ShieldCheck size={14} /> Release from here
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- Inline comment thread (anchored to a line) ----------
function InlineCommentThread({ comments, allComments, lineNumber, currentUser, onReply, onResolve, onDelete }) {
  const [replyTo, setReplyTo] = useState(null);
  const [replyBody, setReplyBody] = useState("");
  const [busy, setBusy] = useState(false);
  const roots = comments.filter((c) => !c.parent_id);
  return (
    <div className="space-y-3 font-sans" data-testid={`inline-thread-line-${lineNumber ?? "general"}`}>
      {roots.map((c) => (
        <CommentCard
          key={c.id}
          comment={c}
          replies={allComments.filter((r) => r.parent_id === c.id)}
          currentUser={currentUser}
          onReplyClick={() => { setReplyTo(c.id); setReplyBody(""); }}
          onResolve={onResolve}
          onDelete={onDelete}
        />
      ))}
      {replyTo && (
        <ComposeForm
          placeholder="Write a reply…"
          value={replyBody}
          onChange={setReplyBody}
          onCancel={() => { setReplyTo(null); setReplyBody(""); }}
          onSubmit={async () => {
            if (!replyBody.trim()) return;
            setBusy(true);
            try {
              await onReply(replyBody.trim(), replyTo);
              setReplyTo(null);
              setReplyBody("");
            } finally { setBusy(false); }
          }}
          busy={busy}
          testidPrefix={`reply-line-${lineNumber ?? "general"}`}
        />
      )}
    </div>
  );
}

function CommentCard({ comment, replies, currentUser, onReplyClick, onResolve, onDelete }) {
  // NOTE(testing-agent): indirect self-reference. Direct JSX self-recursion
  // (<CommentCard/> inside CommentCard) crashes the @emergentbase/visual-edits
  // babel plugin with "Maximum call stack size exceeded", which breaks the
  // whole webpack build. Aliasing the component avoids the plugin cycle.
  const NestedCard = CommentCard;
  const canDelete = currentUser?.role === "admin" || currentUser?.id === comment.author_id;
  return (
    <div
      className={`rounded border p-3 text-xs bg-white ${comment.resolved ? "border-[#CEE0CE] opacity-70" : "border-[#E5E1D8]"}`}
      data-testid={`comment-${comment.id}`}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <strong className="text-[#0F2424] text-[13px]">{comment.author_email}</strong>
        <span className="text-[10px] uppercase tracking-wider rounded-full bg-[#F0EDE3] px-1.5 py-0.5 text-[#5C6B6B]">{comment.author_role}</span>
        <span className="text-[#5C6B6B]">· {new Date(comment.created_at).toLocaleString()}</span>
        {comment.line_number != null && (
          <span className="text-[10px] uppercase tracking-wider text-[#7A4A1A] font-semibold">Line {comment.line_number}</span>
        )}
        {comment.resolved && (
          <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#EAF3EA] text-[#1E4030] rounded-full px-2 py-0.5 font-semibold">
            <CheckCircle2 size={10} /> Resolved
          </span>
        )}
      </div>
      <p className="mt-2 text-[#0F2424] whitespace-pre-wrap leading-relaxed" data-testid={`comment-${comment.id}-body`}>
        {renderCommentBody(comment.body)}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          onClick={onReplyClick}
          className="text-[11px] uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] font-semibold inline-flex items-center gap-1"
          data-testid={`comment-${comment.id}-reply`}
        >
          <CornerDownRight size={12} /> Reply
        </button>
        <button
          onClick={() => onResolve(comment, !comment.resolved)}
          className="text-[11px] uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] font-semibold"
          data-testid={`comment-${comment.id}-resolve`}
        >
          {comment.resolved ? "Reopen" : "Resolve"}
        </button>
        {canDelete && (
          <button
            onClick={() => onDelete(comment)}
            className="text-[11px] uppercase tracking-wider text-[#9E3C3C] hover:text-[#0F2424] font-semibold inline-flex items-center gap-1"
            data-testid={`comment-${comment.id}-delete`}
          >
            <Trash2 size={12} /> Delete
          </button>
        )}
      </div>
      {replies.length > 0 && (
        <div className="mt-3 pl-4 border-l-2 border-[#E5E1D8] space-y-2">
          {replies.map((r) => (
            <NestedCard
              key={r.id}
              comment={r}
              replies={[]}
              currentUser={currentUser}
              onReplyClick={onReplyClick}
              onResolve={onResolve}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ComposeForm({ placeholder, value, onChange, onCancel, onSubmit, busy, testidPrefix }) {
  const hasMentions = /@(admin|counsel)\b/i.test(value || "");
  return (
    <div className="font-sans">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="input input-bordered w-full text-sm min-h-[70px]"
        data-testid={`${testidPrefix}-textarea`}
      />
      <div className="mt-2 flex items-center justify-between gap-2 flex-wrap">
        <p className="text-[10px] text-[#5C6B6B]">
          Tip: type <code className="text-[#7A4A1A]">@admin</code> or <code className="text-[#7A4A1A]">@counsel</code> to notify by email.
          {hasMentions && (
            <span className="ml-2 inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#F5E6D6] text-[#7A4A1A] rounded-full px-2 py-0.5 font-semibold" data-testid={`${testidPrefix}-mention-hint`}>
              Will notify by email
            </span>
          )}
        </p>
        <div className="flex gap-2">
          <button onClick={onCancel} className="btn-outline text-xs" data-testid={`${testidPrefix}-cancel`}>Cancel</button>
          <button
            onClick={onSubmit}
            disabled={busy || !value.trim()}
            className="btn-primary text-xs inline-flex items-center gap-1"
            data-testid={`${testidPrefix}-submit`}
          >
            <Send size={12} /> {busy ? "Posting…" : "Post"}
          </button>
        </div>
      </div>
    </div>
  );
}

// Render a comment body with @admin / @counsel highlighted as pills.
function renderCommentBody(body) {
  if (!body) return null;
  const parts = [];
  const rx = /@(admin|counsel)\b/gi;
  let last = 0;
  let m;
  while ((m = rx.exec(body)) !== null) {
    if (m.index > last) parts.push(body.slice(last, m.index));
    parts.push(
      <span
        key={`m-${m.index}`}
        className="inline-block text-[11px] uppercase tracking-wider bg-[#F5E6D6] text-[#7A4A1A] rounded-full px-2 py-0.5 font-semibold mx-0.5"
      >
        @{m[1].toLowerCase()}
      </span>,
    );
    last = m.index + m[0].length;
  }
  if (last < body.length) parts.push(body.slice(last));
  return parts;
}

function GeneralCommentsPanel({ comments, allComments, currentUser, composing, composeBody, setComposeBody, onPost, onResolve, onDelete }) {
  const [showCompose, setShowCompose] = useState(false);
  const roots = comments.filter((c) => !c.parent_id);
  return (
    <div className="border-t border-[#E5E1D8] px-5 py-4 bg-[#FAF7F0]" data-testid="diff-general-comments-panel">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs uppercase tracking-wider text-[#476B6B] font-semibold inline-flex items-center gap-1">
          <MessageCircle size={12} /> General comments · {roots.length}
        </h3>
        {!showCompose && (
          <button
            onClick={() => setShowCompose(true)}
            className="text-xs uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] font-semibold"
            data-testid="diff-general-add-btn"
          >
            + New comment
          </button>
        )}
      </div>
      {showCompose && (
        <div className="mb-4">
          <ComposeForm
            placeholder="Leave a general note about this working draft…"
            value={composeBody}
            onChange={setComposeBody}
            onCancel={() => { setShowCompose(false); setComposeBody(""); }}
            onSubmit={async () => {
              if (!composeBody.trim()) return;
              await onPost(composeBody.trim(), null);
              setShowCompose(false);
            }}
            busy={composing}
            testidPrefix="diff-general-compose"
          />
        </div>
      )}
      {roots.length === 0 && !showCompose && (
        <p className="text-xs text-[#5C6B6B]">No general comments yet. Use the <strong>+</strong> button on any line in the diff to ask about a specific spot, or add a general note here.</p>
      )}
      {roots.length > 0 && (
        <InlineCommentThread
          comments={roots}
          allComments={allComments}
          lineNumber={null}
          currentUser={currentUser}
          onReply={(body, parentId) => onPost(body, parentId)}
          onResolve={onResolve}
          onDelete={onDelete}
        />
      )}
    </div>
  );
}

// Turn jsdiff parts into aligned side-by-side rows. Removed lines occupy
// the left column, added lines occupy the right column; common lines
// occupy both. Blank cells align surrounding context.
function buildRows(parts) {
  const rows = [];
  let leftNum = 0;
  let rightNum = 0;
  for (const p of parts) {
    const lines = p.value.split("\n");
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    if (p.added) {
      for (const line of lines) {
        rightNum++;
        rows.push({
          left: null, leftNum: null, leftClass: "bg-white",
          right: line, rightNum, rightClass: "bg-[#EAF3EA] text-[#1E4030]",
        });
      }
    } else if (p.removed) {
      for (const line of lines) {
        leftNum++;
        rows.push({
          left: line, leftNum, leftClass: "bg-[#FBEBEB] text-[#7A2E2E]",
          right: null, rightNum: null, rightClass: "bg-white",
        });
      }
    } else {
      for (const line of lines) {
        leftNum++; rightNum++;
        rows.push({
          left: line, leftNum, leftClass: "bg-white",
          right: line, rightNum, rightClass: "bg-white",
        });
      }
    }
  }
  return rows;
}

// ---------- History modal — release timeline + rollback ----------
function HistoryModal({ data, isAdmin, onClose, onRolledBack }) {
  const { slug, title } = data;
  const [state, setState] = useState({ loading: true, data: null });
  const [limit, setLimit] = useState(5);
  const [busy, setBusy] = useState(null);
  const [previewTarget, setPreviewTarget] = useState(null); // { rat, preview, reason }

  const load = React.useCallback(async (n) => {
    setState((s) => ({ ...s, loading: true }));
    try {
      const r = await api.get(`/legal/history-timeline/${slug}`, { params: { limit: n } });
      setState({ loading: false, data: r.data });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load history");
      setState({ loading: false, data: null });
    }
  }, [slug]);

  useEffect(() => { load(limit); }, [load, limit]);

  const openPreview = async (rat) => {
    if (!isAdmin) return;
    setBusy(rat.id);
    try {
      const r = await api.get(`/legal/history/${slug}/rollback-preview/${rat.id}`);
      setPreviewTarget({ rat, preview: r.data, reason: "" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load rollback preview");
    } finally {
      setBusy(null);
    }
  };

  const confirmRollback = async () => {
    if (!previewTarget) return;
    const { rat, reason } = previewTarget;
    setBusy(rat.id);
    try {
      const r = await api.post(`/legal/history/${slug}/rollback/${rat.id}`, { reason });
      toast.success(`Rolled back to v${rat.version} · new version v${r.data.version}`);
      setPreviewTarget(null);
      await onRolledBack();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Rollback failed");
    } finally {
      setBusy(null);
    }
  };

  const d = state.data;
  const total = d?.total_versions || 0;
  const showingAll = limit >= total;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-[60] p-4" data-testid="history-modal">
      <div className="bg-[#FBF3E4] rounded-2xl max-w-2xl w-full flex flex-col overflow-hidden max-h-[85vh]">
        <div className="p-5 border-b border-[#E5E1D8] flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="label">Release history</span>
            <h2 className="font-serif text-2xl mt-1 truncate">{title}</h2>
            <p className="text-xs text-[#5C6B6B] mt-1" data-testid="history-total">
              {state.loading ? "Loading…" : (
                total === 0 ? "No versions released yet."
                : <>Showing <strong>{Math.min(limit, total)}</strong> of <strong>{total}</strong> total release{total === 1 ? "" : "s"} · current v<strong>{d?.current_version}</strong></>
              )}
            </p>
          </div>
          <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#0F2424]" data-testid="history-modal-close">
            <XIcon size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-5 space-y-3" data-testid="history-modal-body">
          {state.loading && <p className="text-sm text-[#5C6B6B]">Loading…</p>}
          {!state.loading && total === 0 && (
            <div className="text-sm text-[#5C6B6B] p-6 text-center" data-testid="history-empty">
              This doc hasn&apos;t been released yet. Once an admin releases a working draft, the version will appear here.
            </div>
          )}
          {(d?.versions || []).map((v, idx) => {
            const cs = v.change_summary || {};
            const isCurrent = idx === 0;
            return (
              <div
                key={v.id}
                className={`rounded-lg border p-4 ${isCurrent ? "border-[#1E4030] bg-white" : "border-[#E5E1D8] bg-white/60"}`}
                data-testid={`history-row-${v.version}`}
                data-ratification-id={v.id}
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <strong className="font-serif text-lg text-[#0F2424]">v{v.version}</strong>
                      {isCurrent && (
                        <span className="text-[10px] uppercase tracking-wider bg-[#1E4030] text-[#FBF3E4] rounded-full px-2 py-0.5 font-semibold">
                          Current
                        </span>
                      )}
                      {v.rolled_back_from_ratification_id && (
                        <span className="text-[10px] uppercase tracking-wider bg-[#F5E6D6] text-[#7A5A1A] rounded-full px-2 py-0.5 font-semibold inline-flex items-center gap-1">
                          <Undo2 size={10} /> Rollback from v{cs.rolled_back_from_version || "?"}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#5C6B6B] mt-1">
                      {new Date(v.ratified_at).toLocaleString()} · by <strong className="text-[#0F2424]">{v.ratified_by}</strong>
                    </p>
                    {v.notes && (
                      <p className="text-sm text-[#0F2424] mt-2 leading-relaxed" data-testid={`history-row-${v.version}-notes`}>
                        {v.notes}
                      </p>
                    )}
                    {cs.edits > 0 && (
                      <p className="text-xs text-[#5C6B6B] mt-2">
                        <strong>{cs.edits}</strong> edit{cs.edits === 1 ? "" : "s"} by {(cs.authors || []).join(", ") || "counsel"}
                        {cs.actions && Object.keys(cs.actions).length > 0 && (
                          <>
                            {" · "}
                            {Object.entries(cs.actions).map(([a, n], i) => (
                              <span key={a}>{i > 0 && ", "}{n} {a.replace(/_/g, " ")}</span>
                            ))}
                          </>
                        )}
                      </p>
                    )}
                  </div>
                  {isAdmin && !isCurrent && v.can_rollback && (
                    <button
                      onClick={() => openPreview(v)}
                      disabled={busy === v.id}
                      className="btn-outline text-xs inline-flex items-center gap-1 text-[#7A5A1A] border-[#7A5A1A] shrink-0"
                      data-testid={`history-row-${v.version}-rollback`}
                    >
                      <Undo2 size={12} /> {busy === v.id ? "Loading…" : "Rollback"}
                    </button>
                  )}
                  {isAdmin && !isCurrent && !v.can_rollback && (
                    <span className="text-[10px] uppercase tracking-wider text-[#5C6B6B] shrink-0" title="No content snapshot on record">
                      No snapshot
                    </span>
                  )}
                </div>
              </div>
            );
          })}
          {!state.loading && !showingAll && total > 0 && (
            <button
              onClick={() => setLimit((n) => Math.min(n + 5, total))}
              className="text-xs uppercase tracking-wider text-[#476B6B] hover:text-[#0F2424] font-semibold mt-2"
              data-testid="history-show-more"
            >
              Show {Math.min(5, total - limit)} more →
            </button>
          )}
        </div>

        <div className="p-4 border-t border-[#E5E1D8] flex items-center justify-between bg-[#FAF7F0]">
          <p className="text-xs text-[#5C6B6B]">
            Rollback creates a new release with the older content. Full history is preserved.
          </p>
          <button onClick={onClose} className="btn-outline text-sm" data-testid="history-modal-cancel">
            Close
          </button>
        </div>
      </div>
      {previewTarget && (
        <RollbackPreviewModal
          data={previewTarget}
          slugTitle={title}
          onCancel={() => setPreviewTarget(null)}
          onChangeReason={(reason) => setPreviewTarget((p) => ({ ...p, reason }))}
          onConfirm={confirmRollback}
          busy={busy === previewTarget.rat.id}
        />
      )}
    </div>
  );
}

// ---------- Rollback preview modal — nested inside history ----------
function RollbackPreviewModal({ data, slugTitle, onCancel, onChangeReason, onConfirm, busy }) {
  const { rat, preview, reason } = data;
  const parts = useMemo(
    () => diffLines(preview?.current_md || "", preview?.target_md || ""),
    [preview],
  );
  const rows = useMemo(() => buildRows(parts), [parts]);
  const stats = useMemo(() => {
    let added = 0, removed = 0;
    for (const p of parts) {
      const lc = (p.value.match(/\n/g) || []).length || (p.value ? 1 : 0);
      if (p.added) added += lc;
      else if (p.removed) removed += lc;
    }
    return { added, removed };
  }, [parts]);
  return (
    <div className="fixed inset-0 bg-black/60 flex items-stretch justify-center z-[70] p-4" data-testid="rollback-preview-modal">
      <div className="bg-[#FBF3E4] rounded-2xl max-w-5xl w-full flex flex-col overflow-hidden max-h-[90vh]">
        <div className="p-5 border-b border-[#E5E1D8] flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span className="label">Rollback preview · {slugTitle}</span>
            <h2 className="font-serif text-2xl mt-1">
              Restore v{preview.target_version}
              <span className="text-[#5C6B6B] text-base ml-2">(currently v{preview.current_version})</span>
            </h2>
            <p className="text-xs text-[#5C6B6B] mt-1">
              Target ratified <strong>{new Date(preview.target_ratified_at).toLocaleString()}</strong> by <strong>{preview.target_ratified_by}</strong>.
              {" "}<span className="text-[#2E5C46] font-semibold">+{stats.added} to add</span>
              {" · "}<span className="text-[#9E3C3C] font-semibold">-{stats.removed} to remove</span>
            </p>
          </div>
          <button onClick={onCancel} className="text-[#5C6B6B] hover:text-[#0F2424]" data-testid="rollback-preview-close">
            <XIcon size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-auto bg-white" data-testid="rollback-preview-body">
          {stats.added === 0 && stats.removed === 0 ? (
            <div className="p-8 text-center text-[#5C6B6B]" data-testid="rollback-preview-empty">
              This rollback would produce no textual change — target and current are already identical.
            </div>
          ) : (
            <table className="w-full font-mono text-xs" style={{ tableLayout: "fixed" }}>
              <thead className="sticky top-0 bg-[#FAF7F0] text-[#5C6B6B] uppercase tracking-wider text-[10px] z-10">
                <tr>
                  <th className="w-10 px-1 py-2 text-right"></th>
                  <th className="px-3 py-2 text-left border-r border-[#E5E1D8]">Current v{preview.current_version}</th>
                  <th className="w-10 px-1 py-2 text-right"></th>
                  <th className="px-3 py-2 text-left">Target v{preview.target_version} (will be restored)</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className="align-top">
                    <td className={`w-10 px-1 py-0.5 text-right text-[#B7B0A0] select-none ${row.leftClass}`}>{row.leftNum ?? ""}</td>
                    <td className={`px-3 py-0.5 whitespace-pre-wrap break-words border-r border-[#F0EDE3] ${row.leftClass}`}>
                      {row.left ?? ""}
                    </td>
                    <td className={`w-10 px-1 py-0.5 text-right text-[#B7B0A0] select-none ${row.rightClass}`}>{row.rightNum ?? ""}</td>
                    <td className={`px-3 py-0.5 whitespace-pre-wrap break-words ${row.rightClass}`}>
                      {row.right ?? ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="p-4 border-t border-[#E5E1D8] bg-[#FAF7F0] space-y-3">
          <div>
            <label className="label block mb-1">Reason (optional but recommended)</label>
            <textarea
              value={reason}
              onChange={(e) => onChangeReason(e.target.value)}
              placeholder="Why are you rolling back? This is stored in the new release's notes."
              className="input input-bordered w-full text-sm min-h-[60px]"
              data-testid="rollback-preview-reason"
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-[#5C6B6B]">
              Rolling back creates a new ratification with the older content. Any open working draft will be auto-discarded.
            </p>
            <div className="flex gap-2 shrink-0">
              <button onClick={onCancel} className="btn-outline text-sm" data-testid="rollback-preview-cancel">
                Cancel
              </button>
              <button
                onClick={onConfirm}
                disabled={busy}
                className="btn-primary text-sm inline-flex items-center gap-1 bg-[#7A5A1A]"
                data-testid="rollback-preview-confirm"
              >
                <Undo2 size={14} /> {busy ? "Rolling back…" : `Confirm rollback to v${rat.version}`}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
