/**
 * AdminLegalRatifications — versioned publish flow + inline counsel redlines.
 *
 * Route:   /admin/legal/ratifications
 *
 * Admin can:
 *   - See every public legal doc and its current ratification status
 *   - Mark a doc as counsel-ratified v{N}      → suppresses the draft banner
 *   - Revoke a ratification                    → banner returns
 *   - View + post + resolve inline redlines / comments per doc
 *
 * Counsel (readonly_admin) can:
 *   - Read every ratification
 *   - Post redline comments (allow-listed in ReadonlyEnforcementMiddleware)
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ShieldCheck,
  MessageSquare,
  Plus,
  Trash2,
  Check,
  BadgeCheck,
  Download,
} from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

export default function AdminLegalRatifications() {
  const { user } = useAuth();
  const isCounsel = user?.role === "readonly_admin";
  const isAdmin = user?.role === "admin";

  const [pages, setPages] = useState([]);
  const [ratifications, setRatifications] = useState([]);
  const [openSlug, setOpenSlug] = useState(null);
  const [comments, setComments] = useState({}); // { source_slug: [comment,...] }
  const [form, setForm] = useState({ version: "", ratified_by: "", notes: "" });
  const [newComment, setNewComment] = useState({
    section: "",
    kind: "redline",
    quoted_text: "",
    suggested_replacement: "",
    body: "",
  });

  const loadAll = async () => {
    try {
      const [p, r] = await Promise.all([
        api.get("/legal/pages"),
        api.get("/legal/ratifications"),
      ]);
      setPages(p.data || []);
      setRatifications(r.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load ratifications");
    }
  };

  useEffect(() => { loadAll(); }, []);

  const ratifyMap = useMemo(() => {
    const m = {};
    for (const r of ratifications) {
      if (!m[r.source_slug]) m[r.source_slug] = r;
    }
    return m;
  }, [ratifications]);

  const openDoc = async (slug) => {
    setOpenSlug(slug);
    try {
      const pub = await api.get(`/legal/pages/${slug}`);
      const src = pub.data.source_slug;
      const c = await api.get(`/legal/comments/${src}`);
      setComments((old) => ({ ...old, [src]: c.data || [] }));
    } catch (e) {
      toast.error("Could not load comments");
    }
  };

  const openPage = pages.find((p) => p.slug === openSlug);
  const openSourceSlug = openPage && ratifyMap[Object.keys(ratifyMap).find((k) => k.includes(openSlug))]?.source_slug;
  // Simpler: we can derive source_slug from the ratifyMap or fetch pages/{slug} again.
  // For UX, resolve source_slug via a small lookup by hitting /legal/pages/{slug} on open.
  const [openMeta, setOpenMeta] = useState(null);
  useEffect(() => {
    if (!openSlug) { setOpenMeta(null); return; }
    api.get(`/legal/pages/${openSlug}`).then((r) => setOpenMeta(r.data)).catch(() => setOpenMeta(null));
  }, [openSlug]);
  const sourceSlug = openMeta?.source_slug;

  const ratify = async () => {
    if (!sourceSlug) return;
    if (!form.version.trim()) { toast.error("Version required (e.g. 1.0)"); return; }
    try {
      await api.post(`/legal/ratifications/${sourceSlug}`, form);
      toast.success(`Marked as counsel-ratified v${form.version}`);
      setForm({ version: "", ratified_by: "", notes: "" });
      await loadAll();
      if (openMeta) api.get(`/legal/pages/${openSlug}`).then((r) => setOpenMeta(r.data));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Ratify failed");
    }
  };

  const revoke = async (slug, source) => {
    if (!window.confirm("Revoke ratification? The draft banner will return.")) return;
    try {
      await api.delete(`/legal/ratifications/${source}`);
      toast.success("Ratification revoked");
      await loadAll();
      if (openSlug === slug) api.get(`/legal/pages/${slug}`).then((r) => setOpenMeta(r.data));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Revoke failed");
    }
  };

  const postComment = async () => {
    if (!sourceSlug) return;
    if (!newComment.body.trim()) { toast.error("Comment body required"); return; }
    try {
      await api.post(`/legal/comments/${sourceSlug}`, newComment);
      toast.success("Comment posted");
      setNewComment({ section: "", kind: "redline", quoted_text: "", suggested_replacement: "", body: "" });
      const c = await api.get(`/legal/comments/${sourceSlug}`);
      setComments((old) => ({ ...old, [sourceSlug]: c.data || [] }));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Comment failed");
    }
  };

  const resolve = async (id) => {
    if (!sourceSlug) return;
    try {
      await api.post(`/legal/comments/${sourceSlug}/${id}/resolve`);
      const c = await api.get(`/legal/comments/${sourceSlug}`);
      setComments((old) => ({ ...old, [sourceSlug]: c.data || [] }));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Resolve failed");
    }
  };

  const exportRedlines = async () => {
    if (!sourceSlug) return;
    try {
      const r = await api.get(`/legal/comments/${sourceSlug}/export`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([r.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `redlines-${openSlug}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Export failed");
    }
  };

  const openComments = sourceSlug ? (comments[sourceSlug] || []) : [];

  return (
    <div className="container-page py-12" data-testid="admin-legal-ratifications-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>

      <span className="label">Legal · Ratification &amp; Redlines</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <ShieldCheck size={28} strokeWidth={1.2} /> Legal ratifications
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Each public doc shows its current ratification status. Click a
        doc to see counsel redlines, add your own, or mark it ratified.
      </p>

      <div className="grid lg:grid-cols-2 gap-6 mt-8">
        {/* Left — list of public docs */}
        <div className="space-y-2" data-testid="legal-ratify-list">
          {pages.map((p) => {
            const r = ratifyMap[Object.keys(ratifyMap).find((k) => k) || ""] || null;
            // We look up by iterating pages/{slug} lazily on click; on the list
            // page we use openMeta once selected, otherwise show a neutral row.
            const ratified = ratifications.find((x) => x.source_slug && p.slug && x.source_slug.endsWith(p.slug.replace("-notice", "-notice"))) ||
              ratifications.find((x) => x.source_slug && x.source_slug.includes(p.slug.replace("terms", "terms-of-service").replace("privacy", "privacy-policy").replace("refunds", "refund-returns-policy").replace("cookie-notice", "cookie-notice").replace("scholarships", "sliding-scale-scholarship-terms").replace("community-standards", "community-standards")));
            return (
              <button
                key={p.slug}
                onClick={() => openDoc(p.slug)}
                className={`w-full text-left card p-4 flex items-center justify-between gap-3 hover:border-[#476B6B] transition ${openSlug === p.slug ? "border-[#476B6B] bg-[#F1EFE7]" : ""}`}
                data-testid={`legal-ratify-row-${p.slug}`}
              >
                <div>
                  <p className="font-serif text-lg text-[#0F2424]">{p.title}</p>
                  <p className="text-xs text-[#5C6B6B] mt-0.5">/legal/{p.slug}</p>
                </div>
                {ratified ? (
                  <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#EAF3EA] text-[#1E4030] rounded-full px-2 py-0.5 font-semibold">
                    <BadgeCheck size={11} /> Ratified v{ratified.version}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#FFF6E3] text-[#7A5A1A] rounded-full px-2 py-0.5 font-semibold">
                    Draft
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Right — detail pane */}
        <div className="space-y-4" data-testid="legal-ratify-detail">
          {!openSlug && (
            <p className="text-sm text-[#5C6B6B]">Select a document on the left to view its status, add counsel comments, or mark it ratified.</p>
          )}
          {openSlug && openMeta && (
            <>
              <div className="card p-5">
                <p className="text-xs uppercase tracking-wider text-[#476B6B] font-semibold">Ratification status</p>
                {openMeta.ratified ? (
                  <div className="mt-2">
                    <p className="text-sm text-[#1E4030] font-semibold inline-flex items-center gap-1">
                      <BadgeCheck size={16} /> Counsel-ratified v{openMeta.ratified_version}
                    </p>
                    <p className="text-xs text-[#5C6B6B] mt-1">
                      {openMeta.ratified_by ? `${openMeta.ratified_by} · ` : ""}
                      {new Date(openMeta.ratified_at).toLocaleString()}
                    </p>
                    {isAdmin && (
                      <button
                        onClick={() => revoke(openSlug, openMeta.source_slug)}
                        className="btn-outline text-xs inline-flex items-center gap-1 mt-3"
                        data-testid="legal-ratify-revoke"
                      >
                        <Trash2 size={12} /> Revoke ratification
                      </button>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-[#7A5A1A] mt-2">Not yet ratified. The public draft banner is showing.</p>
                )}
              </div>

              {isAdmin && !openMeta.ratified && (
                <div className="card p-5" data-testid="legal-ratify-form">
                  <p className="text-xs uppercase tracking-wider text-[#476B6B] font-semibold mb-3">Mark as counsel-ratified</p>
                  <div className="space-y-3">
                    <input
                      value={form.version}
                      onChange={(e) => setForm({ ...form, version: e.target.value })}
                      placeholder="Version (e.g. 1.0)"
                      className="input input-bordered w-full text-sm"
                      data-testid="legal-ratify-version-input"
                    />
                    <input
                      value={form.ratified_by}
                      onChange={(e) => setForm({ ...form, ratified_by: e.target.value })}
                      placeholder="Ratified by (firm or attorney)"
                      className="input input-bordered w-full text-sm"
                      data-testid="legal-ratify-by-input"
                    />
                    <textarea
                      value={form.notes}
                      onChange={(e) => setForm({ ...form, notes: e.target.value })}
                      placeholder="Notes / changelog entry"
                      className="input input-bordered w-full text-sm h-20"
                      data-testid="legal-ratify-notes-input"
                    />
                    <button onClick={ratify} className="btn-primary text-sm inline-flex items-center gap-1" data-testid="legal-ratify-submit">
                      <ShieldCheck size={14} /> Mark ratified
                    </button>
                  </div>
                </div>
              )}

              {/* Redlines / comments */}
              <div className="card p-5">
                <div className="flex items-center justify-between gap-2 mb-3">
                  <p className="text-xs uppercase tracking-wider text-[#476B6B] font-semibold inline-flex items-center gap-1">
                    <MessageSquare size={12} /> Counsel redlines &amp; comments
                  </p>
                  {openComments.some((c) => !c.resolved && c.kind === "redline") && (
                    <button
                      onClick={exportRedlines}
                      className="btn-outline text-xs inline-flex items-center gap-1"
                      data-testid="legal-comment-export-redlines"
                      title="Download unresolved redlines as a Word file with track-changes markup for offline counsel review."
                    >
                      <Download size={12} /> Export unresolved redlines (.docx)
                    </button>
                  )}
                </div>

                <div className="space-y-3">
                  <input
                    value={newComment.section}
                    onChange={(e) => setNewComment({ ...newComment, section: e.target.value })}
                    placeholder="Section (e.g. '3. Eligibility')"
                    className="input input-bordered w-full text-sm"
                    data-testid="legal-comment-section-input"
                  />
                  <select
                    value={newComment.kind}
                    onChange={(e) => setNewComment({ ...newComment, kind: e.target.value })}
                    className="input input-bordered w-full text-sm"
                    data-testid="legal-comment-kind-input"
                  >
                    <option value="redline">Redline (proposed change)</option>
                    <option value="comment">Comment (note only)</option>
                  </select>
                  {newComment.kind === "redline" && (
                    <>
                      <textarea
                        value={newComment.quoted_text}
                        onChange={(e) => setNewComment({ ...newComment, quoted_text: e.target.value })}
                        placeholder="Quoted text (the exact snippet to replace)"
                        className="input input-bordered w-full text-sm h-16"
                        data-testid="legal-comment-quote-input"
                      />
                      <textarea
                        value={newComment.suggested_replacement}
                        onChange={(e) => setNewComment({ ...newComment, suggested_replacement: e.target.value })}
                        placeholder="Suggested replacement"
                        className="input input-bordered w-full text-sm h-16"
                        data-testid="legal-comment-replacement-input"
                      />
                    </>
                  )}
                  <textarea
                    value={newComment.body}
                    onChange={(e) => setNewComment({ ...newComment, body: e.target.value })}
                    placeholder="Comment / rationale"
                    className="input input-bordered w-full text-sm h-20"
                    data-testid="legal-comment-body-input"
                  />
                  <button onClick={postComment} className="btn-outline text-sm inline-flex items-center gap-1" data-testid="legal-comment-submit">
                    <Plus size={14} /> Post {newComment.kind}
                  </button>
                </div>

                <ul className="mt-5 space-y-3" data-testid="legal-comment-list">
                  {openComments.length === 0 && (
                    <li className="text-xs text-[#5C6B6B]">No comments yet.</li>
                  )}
                  {openComments.map((c) => (
                    <li key={c.id} className={`border-l-2 pl-3 ${c.resolved ? "border-[#2E5C46] opacity-60" : "border-[#C9A961]"}`} data-testid={`legal-comment-${c.id}`}>
                      <p className="text-[10px] uppercase tracking-wider text-[#476B6B] font-semibold">
                        {c.kind}
                        {c.section ? ` · ${c.section}` : ""}
                        {c.resolved ? " · resolved" : ""}
                      </p>
                      {c.quoted_text && (
                        <p className="text-xs italic text-[#5C6B6B] mt-1">&ldquo;{c.quoted_text}&rdquo;</p>
                      )}
                      {c.suggested_replacement && (
                        <p className="text-xs text-[#1E4030] mt-1">→ {c.suggested_replacement}</p>
                      )}
                      <p className="text-sm text-[#0F2424] mt-1">{c.body}</p>
                      <p className="text-[10px] text-[#5C6B6B] mt-1">
                        {c.author_email} · {new Date(c.created_at).toLocaleString()}
                      </p>
                      {isAdmin && !c.resolved && (
                        <button onClick={() => resolve(c.id)} className="text-[10px] text-[#2E5C46] hover:underline inline-flex items-center gap-1 mt-1" data-testid={`legal-comment-resolve-${c.id}`}>
                          <Check size={10} /> Mark resolved
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
