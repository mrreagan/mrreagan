import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { Clock, CheckCircle2, XCircle, MessageSquare, ShieldCheck, ArrowLeft, ExternalLink } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const TABS = [
  { v: "pending_review",    label: "Pending review",     icon: Clock },
  { v: "changes_requested", label: "Changes requested",  icon: MessageSquare },
  { v: "active",            label: "Approved",           icon: CheckCircle2 },
  { v: "rejected",          label: "Rejected",           icon: XCircle },
];

export default function AdminStudioQueue() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState("pending_review");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user || user.role !== "admin") {
      navigate("/dashboard", { replace: true });
      return;
    }
    refresh();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, tab]);

  const refresh = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/admin/studio/queue?status=${tab}`);
      setRows(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't load queue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-studio-queue-page">
      <Link to="/admin" className="text-xs text-[#5C6B6B] inline-flex items-center gap-1 hover:text-[#476B6B] mb-2">
        <ArrowLeft size={12} /> Admin
      </Link>
      <span className="label">Admin · AI Studio</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <ShieldCheck size={26} strokeWidth={1.2} /> Vendor moderation queue
      </h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Vendor AI Studio submissions awaiting review. Approve to publish to the
        public store, request changes to send feedback, or reject if the draft
        doesn't fit Birthright's brand.
      </p>

      <div className="flex flex-wrap gap-1 mt-6 border-b border-[#E5E1D8]" role="tablist">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.v}
              onClick={() => setTab(t.v)}
              className={`px-4 py-2 text-xs uppercase tracking-wider inline-flex items-center gap-2 border-b-2 -mb-px ${tab === t.v ? "border-[#476B6B] text-[#0F2424]" : "border-transparent text-[#5C6B6B] hover:text-[#476B6B]"}`}
              data-testid={`queue-tab-${t.v}`}
            >
              <Icon size={12} strokeWidth={1.8} /> {t.label}
            </button>
          );
        })}
      </div>

      <div className="mt-6">
        {loading ? (
          <p className="text-sm text-[#5C6B6B]">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-[#5C6B6B]" data-testid="queue-empty">Nothing here right now.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {rows.map((d) => <ModerationCard key={d.id} draft={d} onChange={refresh} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function ModerationCard({ draft, onChange }) {
  const [busy, setBusy] = useState(false);
  const [showApprove, setShowApprove] = useState(false);
  const [showFeedback, setShowFeedback] = useState(null); // "changes" | "reject" | null
  const [price, setPrice] = useState(0);
  const [adminNote, setAdminNote] = useState("");
  const status = draft.moderation_status || "pending_review";
  const isTerminal = status === "active" || status === "rejected";

  const doAction = async (path, body) => {
    setBusy(true);
    try {
      await api.post(`/admin/studio/queue/${draft.id}/${path}`, body || {});
      toast.success("Updated");
      onChange?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Action failed");
    } finally {
      setBusy(false);
      setShowApprove(false);
      setShowFeedback(null);
      setAdminNote("");
    }
  };

  return (
    <div className="card overflow-hidden flex flex-col" data-testid={`mod-card-${draft.id}`}>
      <div className="aspect-square bg-[#F4F1EA] flex items-center justify-center overflow-hidden">
        <img src={draft.image_url} alt={draft.name} className="w-full h-full object-contain p-2" />
      </div>
      <div className="p-4 flex flex-col gap-2 flex-1">
        <div className="flex items-center justify-between">
          <span className="label !mt-0 !text-[#C9A961]">{draft.category}</span>
          {draft.vendor_name && (
            <Link to={`/partner/${draft.vendor_slug}`} className="text-[10px] uppercase tracking-wider text-[#476B6B] hover:underline">
              by {draft.vendor_name}
            </Link>
          )}
        </div>
        <p className="font-serif text-lg leading-tight">{draft.name}</p>
        <p className="text-xs text-[#5C6B6B] line-clamp-3 leading-relaxed">{draft.description}</p>
        {draft.studio_brief && (
          <details className="mt-1">
            <summary className="text-[10px] uppercase tracking-wider text-[#476B6B] cursor-pointer">Vendor's original brief</summary>
            <p className="text-xs text-[#5C6B6B] mt-1 italic leading-relaxed">"{draft.studio_brief}"</p>
          </details>
        )}
        {draft.is_off_site && draft.external_url && (
          <div className="rounded border border-[#476B6B] bg-[#F4F1EA] p-2 mt-1" data-testid={`mod-off-site-block-${draft.id}`}>
            <p className="text-[10px] uppercase tracking-wider text-[#476B6B] inline-flex items-center gap-1">
              <ExternalLink size={10} strokeWidth={1.8} /> Off-site product (referral mode)
            </p>
            <a href={draft.external_url} target="_blank" rel="noreferrer noopener" className="text-xs text-[#0F2424] hover:underline break-all mt-1 inline-block">
              {draft.external_url} ↗
            </a>
            <p className="text-[10px] text-[#5C6B6B] mt-1">
              Approve to list as a referral. Customers buy on the vendor's site; vendor self-reports sales for revenue share.
            </p>
          </div>
        )}
        {draft.moderation_note && isTerminal && (
          <p className="text-[11px] text-[#5C6B6B] italic mt-1">Admin note: {draft.moderation_note}</p>
        )}

        {!isTerminal && (
          <div className="mt-3 space-y-2">
            {!showApprove && !showFeedback && (
              <div className="flex flex-wrap gap-2">
                <button onClick={() => setShowApprove(true)} disabled={busy} className="btn-primary text-xs inline-flex items-center gap-1" data-testid={`mod-approve-${draft.id}`}>
                  <CheckCircle2 size={11} strokeWidth={1.8} /> Approve
                </button>
                <button onClick={() => setShowFeedback("changes")} disabled={busy} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`mod-changes-${draft.id}`}>
                  <MessageSquare size={11} strokeWidth={1.8} /> Request changes
                </button>
                <button onClick={() => setShowFeedback("reject")} disabled={busy} className="btn-outline !text-[#9E3C3C] !border-[#9E3C3C] text-xs inline-flex items-center gap-1" data-testid={`mod-reject-${draft.id}`}>
                  <XCircle size={11} strokeWidth={1.8} /> Reject
                </button>
              </div>
            )}

            {showApprove && (
              <div className="rounded border border-[#01784E] bg-[#E8F4EC] p-3 space-y-2">
                <p className="text-[11px] uppercase tracking-wider text-[#01784E]">Approve & publish</p>
                <label className="text-xs text-[#5C6B6B] inline-flex items-center gap-2">
                  $ <input type="number" min="1" step="0.01" value={price || ""} onChange={(e) => setPrice(parseFloat(e.target.value) || 0)} placeholder="retail price" className="input-field !py-1 !px-2 text-xs w-28" data-testid={`mod-price-${draft.id}`} />
                </label>
                <textarea value={adminNote} onChange={(e) => setAdminNote(e.target.value)} placeholder="Optional note to vendor (200 chars)" maxLength={200} className="input-field text-xs w-full !py-1 !px-2" />
                <div className="flex gap-2">
                  <button disabled={busy || !price} onClick={() => doAction("approve", { price, admin_note: adminNote || null })} className="btn-primary text-xs" data-testid={`mod-approve-confirm-${draft.id}`}>
                    {busy ? "Publishing…" : "Approve & publish"}
                  </button>
                  <button onClick={() => { setShowApprove(false); setAdminNote(""); }} className="btn-outline text-xs">Cancel</button>
                </div>
              </div>
            )}

            {showFeedback && (
              <div className={`rounded border p-3 space-y-2 ${showFeedback === "reject" ? "border-[#9E3C3C] bg-[#FBEAEA]" : "border-[#C9A961] bg-[#FFF8E1]"}`}>
                <p className="text-[11px] uppercase tracking-wider">
                  {showFeedback === "reject" ? "Reject submission" : "Request changes"}
                </p>
                <textarea required value={adminNote} onChange={(e) => setAdminNote(e.target.value)} placeholder="Explain what you'd like changed (≥ 3 chars)" minLength={3} maxLength={500} className="input-field text-xs w-full !py-1 !px-2 min-h-[80px]" data-testid={`mod-note-${draft.id}`} />
                <div className="flex gap-2">
                  <button disabled={busy || adminNote.trim().length < 3} onClick={() => doAction(showFeedback === "reject" ? "reject" : "request-changes", { admin_note: adminNote })} className={`text-xs ${showFeedback === "reject" ? "btn-outline !text-[#9E3C3C] !border-[#9E3C3C]" : "btn-primary"}`} data-testid={`mod-${showFeedback}-confirm-${draft.id}`}>
                    {busy ? "Saving…" : showFeedback === "reject" ? "Reject" : "Send feedback"}
                  </button>
                  <button onClick={() => { setShowFeedback(null); setAdminNote(""); }} className="btn-outline text-xs">Cancel</button>
                </div>
              </div>
            )}
          </div>
        )}

        {status === "active" && draft.price > 0 && (
          <Link to={`/shop/${draft.slug}`} className="btn-outline text-xs mt-3 self-start" data-testid={`mod-view-live-${draft.id}`}>View live →</Link>
        )}
      </div>
    </div>
  );
}
