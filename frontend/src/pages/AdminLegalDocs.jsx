/**
 * AdminLegalDocs — download static legal documents (counsel briefing, etc.)
 *
 * Endpoints:
 *   GET  /api/legal/docs                — list available docs (admin only)
 *   GET  /api/legal/docs/{key}          — stream the file as a download
 *
 * The endpoint requires an Authorization: Bearer token, so we can't just link
 * to it directly — we fetch it through the authenticated api client and
 * trigger a client-side blob download.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, FileText, RefreshCcw } from "lucide-react";
import api from "../lib/api";
import { toast } from "sonner";

export default function AdminLegalDocs() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/legal/docs");
      setDocs(r.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not load legal docs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const download = async (doc) => {
    setBusyKey(doc.key);
    try {
      const r = await api.get(`/legal/docs/${doc.key}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([r.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", doc.display_name || `${doc.key}.md`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Download failed");
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-legal-docs-page">
      <Link to="/admin" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Admin Hub
      </Link>
      <div className="flex items-start justify-between gap-6 flex-wrap mb-8">
        <div>
          <span className="label">Legal</span>
          <h1 className="editorial-h1 mt-3">Legal document downloads</h1>
          <p className="text-sm text-[#5C6B6B] mt-3 max-w-xl">
            Private static documents shipped with the backend — currently the
            counsel briefing that inventories every legal instrument the platform
            needs. Admin-only. Nothing here is served publicly.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="btn-outline text-sm inline-flex items-center gap-2"
          data-testid="legal-docs-refresh"
        >
          <RefreshCcw size={14} strokeWidth={1.5} /> Refresh
        </button>
      </div>

      {loading && <p className="text-sm text-[#5C6B6B]">Loading...</p>}
      {!loading && docs.length === 0 && (
        <div className="card p-8 text-center" data-testid="legal-docs-empty">
          <FileText size={32} strokeWidth={1.2} className="mx-auto text-[#5C6B6B]" />
          <p className="font-serif text-xl mt-4">No documents available.</p>
        </div>
      )}
      {!loading && docs.length > 0 && (() => {
        // Group by category so the 21 drafts + briefing are readable.
        const groups = docs.reduce((acc, d) => {
          const c = d.category || "Draft";
          (acc[c] = acc[c] || []).push(d);
          return acc;
        }, {});
        const order = ["Briefing", "Public-facing", "Partner agreements", "Governance", "Internal / Compliance", "Internal / IP", "Draft"];
        const sortedKeys = Object.keys(groups).sort((a, b) => order.indexOf(a) - order.indexOf(b));
        return (
          <div className="space-y-8" data-testid="legal-docs-list">
            {sortedKeys.map((cat) => (
              <section key={cat}>
                <h2 className="editorial-h3 mb-3">{cat}</h2>
                <div className="space-y-3">
                  {groups[cat].map((d) => (
                    <article
                      key={d.key}
                      className="card p-5 flex items-center justify-between gap-4"
                      data-testid={`legal-doc-${d.key}`}
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <FileText size={20} strokeWidth={1.5} className="text-[#C9A961] shrink-0 mt-0.5" />
                        <div className="min-w-0">
                          <p className="font-serif text-lg">{d.display_name}</p>
                          <p className="text-xs text-[#5C6B6B] mt-0.5">
                            {(d.size_bytes / 1024).toFixed(1)} KB · {d.display_name?.toLowerCase().endsWith(".docx") ? "Word document" : "Markdown"}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => download(d)}
                        disabled={busyKey === d.key}
                        className="btn-primary text-sm inline-flex items-center gap-2 shrink-0"
                        data-testid={`legal-doc-download-${d.key}`}
                      >
                        <Download size={14} strokeWidth={1.5} />
                        {busyKey === d.key ? "Downloading..." : "Download"}
                      </button>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        );
      })()}
    </div>
  );
}
