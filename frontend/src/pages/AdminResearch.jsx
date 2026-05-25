import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Microscope, BookOpen, CheckCircle2, XCircle, MessageSquare, ExternalLink, X } from "lucide-react";
import api from "../lib/api";

const STATUS_TABS = [
  { v: "pending_review",     label: "Pending review" },
  { v: "changes_requested",  label: "Changes requested" },
  { v: "rejected",           label: "Rejected" },
  { v: "published",          label: "Published" },
  { v: "draft",              label: "Drafts" },
];

const STATUS_PILL = {
  pending_review:    "bg-[#FFF8E1] text-[#8B7128]",
  changes_requested: "bg-[#FDECE3] text-[#9E5C3C]",
  rejected:          "bg-[#F8DCDC] text-[#7E2C2C]",
  published:         "bg-[#E8F0EA] text-[#2E5C46]",
  draft:             "bg-[#F2EEE7] text-[#5C6B6B]",
  archived:          "bg-[#E5E1D8] text-[#5C6B6B]",
};

export default function AdminResearch() {
  const [tab, setTab] = useState("pending_review");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState({});

  const [modalArtifact, setModalArtifact] = useState(null);
  const [decision, setDecision] = useState(null); // "approve" | "changes" | "reject"
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const all = await api.get("/admin/research").then((r) => r.data);
      const byStatus = {};
      for (const a of all) byStatus[a.status] = (byStatus[a.status] || 0) + 1;
      setCounts(byStatus);
      setRows(all);
    } catch {
      toast.error("Could not load research artifacts");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => rows.filter((r) => r.status === tab), [rows, tab]);

  const openModal = (artifact, kind) => {
    setModalArtifact(artifact);
    setDecision(kind);
    setNote("");
  };
  const closeModal = () => { setModalArtifact(null); setDecision(null); setNote(""); };

  const submitDecision = async () => {
    if (!modalArtifact || !decision) return;
    if ((decision === "changes" || decision === "reject") && note.trim().length < 3) {
      toast.error("Please provide a note (≥ 3 chars)");
      return;
    }
    const endpoint = decision === "approve"
      ? `/admin/research/${modalArtifact.id}/approve`
      : decision === "changes"
        ? `/admin/research/${modalArtifact.id}/request-changes`
        : `/admin/research/${modalArtifact.id}/reject`;
    setBusy(true);
    try {
      await api.post(endpoint, { note: note.trim() || null });
      toast.success(
        decision === "approve" ? "Approved & published" :
        decision === "changes" ? "Sent back for changes" : "Rejected"
      );
      closeModal();
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Action failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-research-page">
      <span className="label">Admin · Research</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Microscope size={28} strokeWidth={1.2} /> Research moderation
      </h1>
      <div className="divider-flame" />

      <div className="flex flex-wrap gap-2 mb-6" data-testid="research-tabs">
        {STATUS_TABS.map((t) => (
          <button
            key={t.v}
            onClick={() => setTab(t.v)}
            className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              tab === t.v ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`research-tab-${t.v}`}
          >
            {t.label} ({counts[t.v] || 0})
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-[#5C6B6B]">Loading…</p>
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center text-sm text-[#5C6B6B]" data-testid="research-empty">
          No artifacts in this status.
        </div>
      ) : (
        <ul className="space-y-3" data-testid="research-list">
          {filtered.map((a) => {
            const TierIcon = a.tier === "paper" ? BookOpen : Microscope;
            return (
              <li key={a.id} className="card p-5" data-testid={`research-row-${a.id}`}>
                <div className="flex items-start gap-4">
                  <TierIcon size={18} strokeWidth={1.5} className="text-[#476B6B] mt-1" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-serif text-lg">{a.title}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-medium ${STATUS_PILL[a.status] || "bg-[#F2EEE7]"}`}>
                        {a.status.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-xs text-[#5C6B6B] mt-1">
                      {a.partner_display_name} · {a.tier} · {a.authors} · {a.publication_date}
                    </p>
                    <p className="text-sm text-[#1A2424] mt-2 line-clamp-3">{a.abstract}</p>
                    {a.moderation_note && (
                      <p className="text-xs mt-2 text-[#8B7128] italic" data-testid={`mod-note-${a.id}`}>
                        Prior note: {a.moderation_note}
                      </p>
                    )}
                    {a.full_text_url && (
                      <a href={a.full_text_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 mt-2 text-xs text-[#476B6B] hover:underline" data-testid={`open-link-${a.id}`}>
                        Open full text <ExternalLink size={11} strokeWidth={1.5} />
                      </a>
                    )}
                  </div>
                  {tab === "pending_review" && (
                    <div className="flex flex-col gap-2 shrink-0">
                      <button onClick={() => openModal(a, "approve")} className="btn-primary text-xs inline-flex items-center gap-1" data-testid={`approve-${a.id}`}>
                        <CheckCircle2 size={11} strokeWidth={2} /> Approve
                      </button>
                      <button onClick={() => openModal(a, "changes")} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`changes-${a.id}`}>
                        <MessageSquare size={11} strokeWidth={2} /> Request changes
                      </button>
                      <button onClick={() => openModal(a, "reject")} className="text-xs text-[#9E3C3C] hover:underline inline-flex items-center gap-1" data-testid={`reject-${a.id}`}>
                        <XCircle size={11} strokeWidth={2} /> Reject
                      </button>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {modalArtifact && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" data-testid="moderation-modal">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-serif text-xl">
                {decision === "approve" ? "Approve & publish" : decision === "changes" ? "Request changes" : "Reject artifact"}
              </h3>
              <button onClick={closeModal} aria-label="Close" className="text-[#5C6B6B] hover:text-[#1A2424]">
                <X size={16} strokeWidth={1.5} />
              </button>
            </div>
            <p className="text-sm text-[#5C6B6B] mb-3">"{modalArtifact.title}"</p>
            <label className="block text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">
              {decision === "approve" ? "Internal note (optional)" : "Note to partner (required)"}
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
              className="input-field text-sm w-full"
              placeholder={decision === "approve" ? "Anything to log internally?" : "Explain what needs to change…"}
              data-testid="moderation-note"
            />
            <div className="flex gap-2 mt-5">
              <button onClick={submitDecision} disabled={busy} className="btn-primary text-xs" data-testid="moderation-confirm">
                {busy ? "Saving…" : "Confirm"}
              </button>
              <button onClick={closeModal} className="btn-outline text-xs">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
