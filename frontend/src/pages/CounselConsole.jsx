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
  ArrowLeft, Upload, Download, ShieldCheck, CheckCircle2,
  Clock, MessageSquare, Send, Trash2, GitCompare, History,
  MessageCircle,
} from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { ReleaseModal } from "../components/counsel/ReleaseModal";
import { DiffModal } from "../components/counsel/DiffModal";
import { HistoryModal } from "../components/counsel/HistoryModal";

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

