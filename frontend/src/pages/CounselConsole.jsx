/**
 * CounselConsole — the single legal-documents hub for the whole platform.
 *
 * Route: /counsel (public — no auth required for downloads)
 *
 * What it does:
 *   - Anyone can download every legal draft artefact (briefing, public-
 *     facing policies, partner agreements, governance, compliance, IP,
 *     advisory memos) organised by the same categories as the admin site.
 *   - Admin + counsel (`readonly_admin`) additionally see the full
 *     working-draft workflow per doc: upload replacements, download the
 *     working draft, view diff, add inline comments, mark ready, and
 *     admin can release / discard / roll back.
 *   - `/admin/legal-docs` now redirects here — one hub, no redundant page.
 *
 * Data flow:
 *   - `GET /api/legal/docs` → every draft artefact with {key, display_name,
 *     category, source_slug (nullable), size_bytes, download_url}.
 *   - `GET /api/legal/pages` → public-facing subset used to link to the
 *     rendered /legal/{slug} page.
 *   - `GET /api/legal/ratifications` + `GET /api/legal/working-drafts`
 *     drive the release badge and workflow badges.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, Upload, Download, ShieldCheck, CheckCircle2,
  Clock, Send, Trash2, GitCompare, History, MessageCircle,
  FileText, ChevronDown, ChevronUp, Archive,
} from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { ReleaseModal } from "../components/counsel/ReleaseModal";
import { DiffModal } from "../components/counsel/DiffModal";
import { HistoryModal } from "../components/counsel/HistoryModal";

// Preferred category ordering — mirrors the admin /admin/legal-docs view.
const CATEGORY_ORDER = [
  "Briefing",
  "Public-facing",
  "Partner agreements",
  "Governance",
  "Internal / Compliance",
  "Internal / IP",
  "Advisory memos",
];
const CATEGORY_BLURB = {
  "Briefing": "Orientation material — the Legal Briefing and the priority-scoped review plan.",
  "Public-facing": "Notices rendered on the public site under /legal/*. Full working-draft workflow available.",
  "Partner agreements": "Contracts for facilitators, artists, vendors, community partners, and sponsors.",
  "Governance": "Board, officer, volunteer, ombudsman, and nonprofit governance instruments.",
  "Internal / Compliance": "Tax, charitable solicitation, and other regulatory playbooks.",
  "Internal / IP": "Trademark and copyright strategy documents.",
  "Advisory memos": "Analytical memos and one-off legal opinions on specific business decisions.",
};

// Priority buckets mirror the Legal Briefing §5 (Priority One) and §6
// (Priority Two). Slugs here are the `source_slug` values used across
// working-draft and ratification endpoints. Docs without a source_slug
// (the briefing itself) are always shown.
const PRIORITY_ONE_SLUGS = new Set([
  "01-terms-of-service",
  "02-privacy-policy",
  "03-cookie-notice",
  "04-indemnification-hold-harmless",
  "10-sliding-scale-scholarship-terms",
  "14-community-standards",
  "15-refund-returns-policy",
  "11-board-officer-agreement",
  "12-volunteer-agreement",
  "13-ombudsman-charter",
  "16-sales-tax-registration-plan",
  "17-trademark-filings-plan",
  "18-copyright-registration-strategy",
  "19-data-processing-agreement-template",
  "20-nonprofit-governance-bundle",
  "21-charitable-solicitation-plan",
]);

export default function CounselConsole() {
  const { user, refreshUser } = useAuth();
  const isAdmin = user?.role === "admin";
  const isCounsel = user?.role === "readonly_admin";
  const canEdit = isAdmin || isCounsel;
  const mentionFrequency = user?.mention_email_frequency || "daily";
  const [freqBusy, setFreqBusy] = useState(false);
  const setMentionFrequency = async (next) => {
    if (next === mentionFrequency) return;
    setFreqBusy(true);
    try {
      await api.put("/auth/me", { mention_email_frequency: next });
      await refreshUser();
      toast.success(next === "realtime"
        ? "You'll now get each @mention as a live email."
        : "You'll now get one daily digest of @mentions.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not update preference");
    } finally { setFreqBusy(false); }
  };

  const [docs, setDocs] = useState([]);
  const [pages, setPages] = useState([]);
  const [ratifications, setRatifications] = useState([]);
  const [workingDrafts, setWorkingDrafts] = useState([]);
  const [busy, setBusy] = useState({});
  const [releaseModal, setReleaseModal] = useState(null);
  const [diffModal, setDiffModal] = useState(null);
  const [historyModal, setHistoryModal] = useState(null);

  const loadAll = async () => {
    try {
      // /docs and /pages are public; ratifications + working-drafts
      // are role-gated. Guard against 403 so the anonymous experience
      // still renders every download.
      const [d, p] = await Promise.all([
        api.get("/legal/docs"),
        api.get("/legal/pages"),
      ]);
      setDocs(d.data || []);
      setPages(p.data || []);
      if (canEdit) {
        const [r, w] = await Promise.all([
          api.get("/legal/ratifications"),
          api.get("/legal/working-drafts"),
        ]);
        setRatifications(r.data || []);
        setWorkingDrafts(w.data || []);
      } else {
        setRatifications([]);
        setWorkingDrafts([]);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load legal docs");
    }
  };
  useEffect(() => { loadAll(); }, [canEdit]);

  const wdBySlug = useMemo(() => {
    const m = {};
    workingDrafts.forEach((w) => { m[w.source_slug] = w; });
    return m;
  }, [workingDrafts]);

  const ratBySlug = useMemo(() => {
    const m = {};
    ratifications.forEach((r) => {
      if (!m[r.source_slug] || r.ratified_at > m[r.source_slug].ratified_at) {
        m[r.source_slug] = r;
      }
    });
    return m;
  }, [ratifications]);

  const publicSlugBySource = useMemo(() => {
    const m = {};
    // Reverse the backend's SOURCE → PUBLIC map. `/legal/pages` returns
    // {slug: <public>, title, ratified_source} where the public slug maps
    // 1:1 to a source slug we already know from the doc list.
    const KNOWN = {
      "01-terms-of-service": "terms",
      "02-privacy-policy": "privacy",
      "03-cookie-notice": "cookie-notice",
      "04-indemnification-hold-harmless": "indemnification",
      "10-sliding-scale-scholarship-terms": "scholarships",
      "14-community-standards": "community-standards",
      "15-refund-returns-policy": "refunds",
    };
    pages.forEach((p) => {
      const source = Object.entries(KNOWN).find(([, pub]) => pub === p.slug)?.[0];
      if (source) m[source] = p.slug;
    });
    return m;
  }, [pages]);

  // Priority filter — `all` (default), `p1`, or `p2`. Persisted in
  // localStorage so counsel's chosen focus survives a page reload.
  const [priorityFilter, setPriorityFilter] = useState(() => {
    try { return localStorage.getItem("counsel:priority-filter") || "all"; }
    catch { return "all"; }
  });
  useEffect(() => {
    try { localStorage.setItem("counsel:priority-filter", priorityFilter); }
    catch { /* localStorage denied — fine */ }
  }, [priorityFilter]);

  const matchesPriority = (doc) => {
    if (priorityFilter === "all") return true;
    // Briefing docs (no source_slug) are always shown — they orient the
    // review regardless of which priority is active.
    if (!doc.source_slug) return true;
    const isP1 = PRIORITY_ONE_SLUGS.has(doc.source_slug);
    return priorityFilter === "p1" ? isP1 : !isP1;
  };

  const grouped = useMemo(() => {
    const g = {};
    docs.filter(matchesPriority).forEach((d) => {
      const cat = d.category || "Other";
      (g[cat] = g[cat] || []).push(d);
    });
    // Sort inside each category by display_name for a predictable list.
    Object.values(g).forEach((arr) => arr.sort((a, b) => a.display_name.localeCompare(b.display_name)));
    return g;
  }, [docs, priorityFilter]);

  const setRowBusy = (key, k, v) => setBusy((b) => ({ ...b, [`${key}:${k}`]: v }));

  // ---------- actions ----------
  const downloadDoc = async (doc) => {
    setRowBusy(doc.key, "dl", true);
    try {
      const r = await api.get(`/legal/docs/${doc.key}`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url; a.download = doc.display_name;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Download failed");
    } finally {
      setRowBusy(doc.key, "dl", false);
    }
  };

  const [bundleBusy, setBundleBusy] = useState(false);
  const downloadBundle = async (category) => {
    if (!canEdit) return;
    setBundleBusy(true);
    const key = category || "__all__";
    setRowBusy(key, "bundle", true);
    try {
      const params = category ? { category } : {};
      const r = await api.get("/legal/docs-bundle.zip", { params, responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      const fname = category
        ? `birthright-legal-${category.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.zip`
        : "birthright-legal-all.zip";
      a.href = url; a.download = fname;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success(category ? `Downloaded ${category} bundle` : "Downloaded full archive");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Bundle download failed");
    } finally {
      setBundleBusy(false);
      setRowBusy(key, "bundle", false);
    }
  };

  const uploadReplacement = async (sourceSlug, file, title) => {
    if (!file) return;
    if (!window.confirm(`Upload ${file.name} as the working version for "${title}"? The public site will still show the released version until an admin releases the working draft.`)) return;
    setRowBusy(sourceSlug, "upload", true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post(`/legal/docs/${sourceSlug}/upload`, fd);
      toast.success(`Working draft updated · ${r.data.bytes_written} bytes`);
      await loadAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Upload failed");
    } finally {
      setRowBusy(sourceSlug, "upload", false);
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
    if (!window.confirm("Mark this working draft ready for admin review? Editing after this will move it back to Draft. Admins receive a daily digest of unresolved mentions.")) return;
    setRowBusy(sourceSlug, "ready", true);
    try {
      const r = await api.post(`/legal/working-drafts/${sourceSlug}/mark-ready`);
      const note = r.data.email_scheduled ? " · admins queued for next digest" : "";
      toast.success(`Marked ready for admin${note}`);
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
        version, notes, ratified_by: user?.email,
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
        slug: sourceSlug, title,
        released: r.data.released_md_diff || r.data.released_md || "",
        working: r.data.content_md_diff || r.data.content_md || "",
        wd: r.data,
      });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load diff");
    } finally {
      setRowBusy(sourceSlug, "diff", false);
    }
  };

  const totalCount = docs.length;

  return (
    <div className="container-page py-12" data-testid="counsel-console-page">
      <div className="mb-6">
        <Link to={isAdmin ? "/admin" : "/"} className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B]">
          <ArrowLeft size={14} strokeWidth={1.5} /> {isAdmin ? "Admin Hub" : "Home"}
        </Link>
      </div>

      <span className="label">Legal · Documents Hub</span>
      <h1 className="editorial-h1 mt-2 flex items-center gap-3">
        <ShieldCheck size={28} strokeWidth={1.2} /> Legal documents
      </h1>
      <div className="divider-flame" />

      <div className="card p-5 max-w-3xl bg-[#FAF7F0]">
        <p className="text-sm text-[#0F2424] leading-relaxed">
          <strong>{totalCount}</strong> draft artefact{totalCount === 1 ? "" : "s"} across <strong>{Object.keys(grouped).length}</strong> categor{Object.keys(grouped).length === 1 ? "y" : "ies"}. Anyone can download the drafts.
          {canEdit ? (
            <> As {isAdmin ? "admin" : "counsel"} you also get the full working-draft workflow: upload replacements, diff, add inline comments, and {isAdmin ? "release / roll back" : "mark ready for admin"}.</>
          ) : (
            <> Log in as admin or counsel for the full editing workflow.</>
          )}
        </p>
        <p className="text-xs text-[#5C6B6B] mt-3">
          Accepted upload formats: <code className="text-[#0F2424]">.md</code>, <code className="text-[#0F2424]">.markdown</code>, <code className="text-[#0F2424]">.txt</code>, <code className="text-[#0F2424]">.docx</code>. Files up to 2 MB.
        </p>
        {canEdit && (
          <button
            onClick={() => downloadBundle(null)}
            disabled={bundleBusy}
            className="btn-primary text-xs inline-flex items-center gap-1 mt-4"
            data-testid="counsel-bundle-all"
          >
            <Archive size={12} /> {bundleBusy ? "Zipping…" : `Download all ${totalCount} docs (.zip)`}
          </button>
        )}
        {canEdit && (
          <div className="mt-4 pt-4 border-t border-[#E5E1D8]" data-testid="counsel-mention-freq">
            <p className="text-[11px] uppercase tracking-wider text-[#5C6B6B] font-semibold mb-2">
              @mention emails
            </p>
            <div className="flex flex-wrap gap-2 text-xs">
              {["daily", "realtime"].map((f) => (
                <button
                  key={f}
                  onClick={() => setMentionFrequency(f)}
                  disabled={freqBusy}
                  className={`px-3 py-1.5 rounded-full border transition-colors ${
                    mentionFrequency === f
                      ? "bg-[#0F2424] border-[#0F2424] text-[#FAF7F0] font-semibold"
                      : "bg-white border-[#D6CFC2] text-[#0F2424] hover:border-[#476B6B]"
                  }`}
                  data-testid={`counsel-mention-freq-${f}`}
                >
                  {f === "daily" ? "Daily digest" : "Real-time"}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-[#5C6B6B] mt-2 leading-relaxed">
              {mentionFrequency === "realtime"
                ? "You'll get a live email each time someone @-mentions your role. Great for active review sprints."
                : "You'll get one summary email per day of unresolved @mentions. Good for keeping the inbox calm."}
            </p>
          </div>
        )}
        <div className="mt-4 pt-4 border-t border-[#E5E1D8]" data-testid="counsel-priority-filter">
          <p className="text-[11px] uppercase tracking-wider text-[#5C6B6B] font-semibold mb-2">
            Focus by priority
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            {[
              { key: "all", label: "All" },
              { key: "p1", label: "Priority One" },
              { key: "p2", label: "Priority Two" },
            ].map((f) => (
              <button
                key={f.key}
                onClick={() => setPriorityFilter(f.key)}
                className={`px-3 py-1.5 rounded-full border transition-colors ${
                  priorityFilter === f.key
                    ? "bg-[#0F2424] border-[#0F2424] text-[#FAF7F0] font-semibold"
                    : "bg-white border-[#D6CFC2] text-[#0F2424] hover:border-[#476B6B]"
                }`}
                data-testid={`counsel-priority-filter-${f.key}`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-[#5C6B6B] mt-2 leading-relaxed">
            {priorityFilter === "p1"
              ? "Showing the public docs plus compliance, incorporation, IP-protection, and governance foundations. Priority One in the Legal Briefing §5."
              : priorityFilter === "p2"
              ? "Showing partner instruments, charters, and advisory memos. Priority Two in the Legal Briefing §6."
              : "Showing every draft. Switch to Priority One or Priority Two to focus a single-session review."}
          </p>
        </div>
      </div>

      {/* Render categories in the preferred order */}
      <div className="mt-8 space-y-10" data-testid="counsel-console-categories">
        {CATEGORY_ORDER.filter((cat) => grouped[cat]?.length).map((cat) => (
          <CategorySection
            key={cat}
            category={cat}
            blurb={CATEGORY_BLURB[cat] || ""}
            docs={grouped[cat]}
            wdBySlug={wdBySlug}
            ratBySlug={ratBySlug}
            publicSlugBySource={publicSlugBySource}
            canEdit={canEdit}
            isAdmin={isAdmin}
            isCounsel={isCounsel}
            busy={busy}
            onDownload={downloadDoc}
            onUpload={uploadReplacement}
            onDownloadWorking={downloadWorking}
            onDiff={openDiff}
            onMarkReady={markReady}
            onHistory={(slug, title) => setHistoryModal({ slug, title })}
            onRelease={(slug, title, wd) => setReleaseModal({ slug, title, wd })}
            onDiscard={discard}
            onBundleDownload={downloadBundle}
          />
        ))}
        {/* Any categories not in the preferred order — append at the end. */}
        {Object.keys(grouped).filter((c) => !CATEGORY_ORDER.includes(c)).map((cat) => (
          <CategorySection
            key={cat}
            category={cat}
            blurb=""
            docs={grouped[cat]}
            wdBySlug={wdBySlug}
            ratBySlug={ratBySlug}
            publicSlugBySource={publicSlugBySource}
            canEdit={canEdit}
            isAdmin={isAdmin}
            isCounsel={isCounsel}
            busy={busy}
            onDownload={downloadDoc}
            onUpload={uploadReplacement}
            onDownloadWorking={downloadWorking}
            onDiff={openDiff}
            onMarkReady={markReady}
            onHistory={(slug, title) => setHistoryModal({ slug, title })}
            onRelease={(slug, title, wd) => setReleaseModal({ slug, title, wd })}
            onDiscard={discard}
            onBundleDownload={downloadBundle}
          />
        ))}
      </div>

      {canEdit && (
        <p className="text-xs text-[#5C6B6B] mt-8 max-w-3xl">
          Need the fine-grained redline / comment workflow?
          <Link to="/admin/legal/ratifications" className="underline text-[#476B6B] ml-1" data-testid="counsel-console-redline-link">
            Open the redline editor →
          </Link>
        </p>
      )}

      {releaseModal && isAdmin && (
        <ReleaseModal
          data={releaseModal}
          ratifications={ratifications}
          onCancel={() => setReleaseModal(null)}
          onRelease={(version, notes) => releaseNow(releaseModal.slug, version, notes)}
          busy={!!busy[`${releaseModal.slug}:release`]}
        />
      )}

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

// ---------- Category section ----------
function CategorySection({
  category, blurb, docs,
  wdBySlug, ratBySlug, publicSlugBySource,
  canEdit, isAdmin, isCounsel, busy,
  onDownload, onUpload, onDownloadWorking, onDiff,
  onMarkReady, onHistory, onRelease, onDiscard,
  onBundleDownload,
}) {
  const [open, setOpen] = useState(true);
  const bundleKey = `${category}:bundle`;
  return (
    <section data-testid={`counsel-category-${slugify(category)}`}>
      <div className="w-full flex items-center justify-between gap-3">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex-1 flex items-center justify-between text-left group"
          data-testid={`counsel-category-${slugify(category)}-toggle`}
        >
          <div>
            <h2 className="font-serif text-2xl text-[#0F2424] group-hover:text-[#476B6B] transition-colors">
              {category}
              <span className="ml-2 text-sm text-[#5C6B6B] font-sans">· {docs.length}</span>
            </h2>
            {blurb && <p className="text-xs text-[#5C6B6B] mt-1 max-w-3xl">{blurb}</p>}
          </div>
          {open ? <ChevronUp size={20} strokeWidth={1.4} /> : <ChevronDown size={20} strokeWidth={1.4} />}
        </button>
        {canEdit && (
          <button
            onClick={() => onBundleDownload(category)}
            disabled={!!busy[bundleKey]}
            className="btn-outline text-xs inline-flex items-center gap-1 shrink-0"
            data-testid={`counsel-category-${slugify(category)}-bundle`}
            title={`Download all ${docs.length} ${category} docs as a zip`}
          >
            <Archive size={12} /> {busy[bundleKey] ? "Zipping…" : ".zip"}
          </button>
        )}
      </div>
      <div className="divider-flame my-3" />
      {open && (
        <div className="grid gap-3">
          {docs.map((doc) => (
            <DocRow
              key={doc.key}
              doc={doc}
              wd={doc.source_slug ? wdBySlug[doc.source_slug] : null}
              rat={doc.source_slug ? ratBySlug[doc.source_slug] : null}
              publicSlug={doc.source_slug ? publicSlugBySource[doc.source_slug] : null}
              canEdit={canEdit}
              isAdmin={isAdmin}
              isCounsel={isCounsel}
              busy={busy}
              onDownload={onDownload}
              onUpload={onUpload}
              onDownloadWorking={onDownloadWorking}
              onDiff={onDiff}
              onMarkReady={onMarkReady}
              onHistory={onHistory}
              onRelease={onRelease}
              onDiscard={onDiscard}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function slugify(s) {
  return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

// ---------- Single doc row ----------
function DocRow({
  doc, wd, rat, publicSlug,
  canEdit, isAdmin, isCounsel, busy,
  onDownload, onUpload, onDownloadWorking, onDiff,
  onMarkReady, onHistory, onRelease, onDiscard,
}) {
  const source = doc.source_slug;
  const canWorkflow = !!source && canEdit;   // /counsel-briefing-docx and /counsel-briefing-md have no source_slug
  return (
    <div
      className="card p-4 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3"
      data-testid={`counsel-row-${source || doc.key}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <FileText size={14} strokeWidth={1.4} className="text-[#C9A961] shrink-0" />
          <h3 className="font-serif text-base text-[#0F2424] break-words">{doc.display_name}</h3>
          {rat && (
            <span
              className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-[#EAF3EA] text-[#1E4030] rounded-full px-2 py-0.5 font-semibold"
              data-testid={`counsel-row-${source}-released-badge`}
            >
              <CheckCircle2 size={11} /> v{rat.version}
            </span>
          )}
          {wd && (
            <span
              className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 font-semibold ${wd.state === "awaiting_admin" ? "bg-[#E3EEF9] text-[#264D6B]" : "bg-[#FFF6E3] text-[#7A5A1A]"}`}
              data-testid={`counsel-row-${source}-wd-badge`}
            >
              <Clock size={11} /> {wd.state === "awaiting_admin" ? "Awaiting admin" : "Working draft"}
            </span>
          )}
          {wd?.comment_stats?.total > 0 && (
            <span
              className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 font-semibold ${wd.comment_stats.open > 0 ? "bg-[#F5E6D6] text-[#7A4A1A]" : "bg-[#EAF3EA] text-[#1E4030]"}`}
              data-testid={`counsel-row-${source}-comments-badge`}
            >
              <MessageCircle size={11} /> {wd.comment_stats.open} open · {wd.comment_stats.total} total
            </span>
          )}
        </div>
        <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mt-1">
          {(doc.size_bytes / 1024).toFixed(1)} KB
          {publicSlug && (
            <> · <Link to={`/legal/${publicSlug}`} className="hover:text-[#476B6B]">/legal/{publicSlug}</Link></>
          )}
          {wd && (
            <> · last edit by <strong className="text-[#0F2424]">{wd.last_edited_by_email || wd.created_by_email}</strong> · {new Date(wd.last_edited_at || wd.created_at).toLocaleDateString()}</>
          )}
        </p>
        {rat && (rat.notes || rat.ratified_at) && (
          <div
            className="mt-2 rounded border border-[#DDEBDD] bg-[#F5FAF5] px-3 py-2 text-[11px] leading-relaxed"
            data-testid={`counsel-row-${source}-last-release`}
          >
            <p className="text-[10px] uppercase tracking-wider text-[#1E4030] font-semibold">
              Last release · v{rat.version}
              {rat.ratified_at && (
                <> · {new Date(rat.ratified_at).toLocaleDateString()}</>
              )}
              {rat.ratified_by && (
                <> · <span className="text-[#0F2424]">{rat.ratified_by}</span></>
              )}
            </p>
            {rat.notes && (
              <p className="mt-1 text-[#0F2424] whitespace-pre-wrap break-words line-clamp-3">{rat.notes}</p>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2 lg:justify-end lg:min-w-[380px]">
        <button
          onClick={() => onDownload(doc)}
          disabled={!!busy[`${doc.key}:dl`]}
          className="btn-outline text-xs inline-flex items-center gap-1"
          data-testid={`counsel-row-${source || doc.key}-download`}
        >
          <Download size={12} /> Download
        </button>

        {canWorkflow && wd && (
          <>
            <button
              onClick={() => onDiff(source, doc.display_name)}
              disabled={!!busy[`${source}:diff`]}
              className="btn-outline text-xs inline-flex items-center gap-1"
              data-testid={`counsel-row-${source}-view-diff`}
            >
              <GitCompare size={12} /> Diff
            </button>
            <button
              onClick={() => onDownloadWorking(source, doc.display_name)}
              disabled={!!busy[`${source}:dl-working`]}
              className="btn-outline text-xs inline-flex items-center gap-1"
              data-testid={`counsel-row-${source}-download-working`}
            >
              <Download size={12} /> Working
            </button>
          </>
        )}

        {canWorkflow && (
          <button
            onClick={() => onHistory(source, doc.display_name)}
            className="btn-outline text-xs inline-flex items-center gap-1"
            data-testid={`counsel-row-${source}-history-btn`}
          >
            <History size={12} /> History
          </button>
        )}

        {canWorkflow && (
          <label
            className={`btn-primary text-xs inline-flex items-center gap-1 cursor-pointer ${busy[`${source}:upload`] ? "opacity-60 pointer-events-none" : ""}`}
            data-testid={`counsel-row-${source}-upload-btn`}
          >
            <Upload size={12} />
            {busy[`${source}:upload`] ? "Uploading…" : "Upload"}
            <input
              type="file"
              accept=".md,.markdown,.txt,.docx"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (f) onUpload(source, f, doc.display_name);
              }}
              data-testid={`counsel-row-${source}-upload-input`}
              disabled={!!busy[`${source}:upload`]}
            />
          </label>
        )}

        {canWorkflow && wd?.state === "draft" && (
          <button
            onClick={() => onMarkReady(source)}
            disabled={!!busy[`${source}:ready`]}
            className="btn-outline text-xs inline-flex items-center gap-1 text-[#264D6B] border-[#264D6B]"
            data-testid={`counsel-row-${source}-mark-ready`}
          >
            <Send size={12} /> Mark ready
          </button>
        )}

        {isAdmin && wd && (
          <>
            <button
              onClick={() => onRelease(source, doc.display_name, wd)}
              disabled={!!busy[`${source}:release`]}
              className="btn-primary text-xs inline-flex items-center gap-1 bg-[#1E4030]"
              data-testid={`counsel-row-${source}-release-btn`}
            >
              <ShieldCheck size={12} /> Release
            </button>
            <button
              onClick={() => onDiscard(source)}
              disabled={!!busy[`${source}:discard`]}
              className="btn-outline text-xs inline-flex items-center gap-1 text-[#9E3C3C] border-[#9E3C3C]"
              data-testid={`counsel-row-${source}-discard-btn`}
            >
              <Trash2 size={12} /> Discard
            </button>
          </>
        )}
      </div>
    </div>
  );
}
