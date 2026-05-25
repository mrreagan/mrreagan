import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Scale, Shield, ExternalLink, Send } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

const STATUS_PILL = {
  open:         { label: "Open",         cls: "bg-[#FFF8E1] text-[#8B7128]" },
  under_review: { label: "Under review", cls: "bg-[#E8F0FE] text-[#3458B5]" },
  resolved:     { label: "Resolved",     cls: "bg-[#E8F0EA] text-[#2E5C46]" },
  dismissed:    { label: "Dismissed",    cls: "bg-[#F2EEE7] text-[#5C6B6B]" },
};

export default function DisputeDetail({ adminMode = false }) {
  const { dispute_id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [ombudsmen, setOmbudsmen] = useState([]);
  const [assigning, setAssigning] = useState("");
  const [statusNote, setStatusNote] = useState("");
  const [newStatus, setNewStatus] = useState("under_review");
  const [resolutionNote, setResolutionNote] = useState("");
  const [outcome, setOutcome] = useState("dismissed");
  const [credit, setCredit] = useState("");
  const [busy, setBusy] = useState(false);

  const base = adminMode ? "/admin/disputes" : "/me/disputes";

  const load = () => {
    api.get(`${base}/${dispute_id}`)
      .then((r) => setD(r.data))
      .catch((e) => {
        toast.error(e.response?.data?.detail || "Could not load");
        navigate(adminMode ? "/admin/ombudsman" : "/dashboard/disputes");
      });
    if (adminMode) {
      api.get("/admin/ombudsman/users").then((r) => setOmbudsmen(r.data)).catch(() => {});
    }
  };
  useEffect(load, [dispute_id]);

  const assign = async () => {
    if (!assigning) { toast.error("Pick an ombudsman"); return; }
    setBusy(true);
    try {
      await api.post(`/admin/disputes/${dispute_id}/assign`, { ombudsman_user_id: assigning });
      toast.success("Assigned");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  const updateStatus = async () => {
    if (statusNote.trim().length < 3) { toast.error("Note required (≥ 3 chars)"); return; }
    setBusy(true);
    try {
      await api.post(`/admin/disputes/${dispute_id}/status`, { status: newStatus, note: statusNote.trim() });
      toast.success("Status updated");
      setStatusNote("");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  const resolve = async () => {
    if (resolutionNote.trim().length < 10) { toast.error("Resolution note (≥ 10 chars) required"); return; }
    setBusy(true);
    try {
      const payload = { outcome, resolution_note: resolutionNote.trim() };
      if (credit) payload.financial_credit_usd = parseFloat(credit) || 0;
      await api.post(`/admin/disputes/${dispute_id}/resolve`, payload);
      toast.success(outcome === "dismissed" ? "Dismissed" : "Resolved");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  if (!d) return <p className="container-page py-12 text-sm text-[#5C6B6B]">Loading…</p>;
  const pill = STATUS_PILL[d.status];
  const terminal = ["resolved", "dismissed"].includes(d.status);
  const showAdminActions = adminMode && !terminal;

  return (
    <div className="container-page py-8" data-testid="dispute-detail">
      <button onClick={() => navigate(adminMode ? "/admin/ombudsman" : "/dashboard/disputes")} className="text-xs uppercase tracking-wider text-[#5C6B6B] hover:underline inline-flex items-center gap-1 mb-4" data-testid="back-link">
        <ArrowLeft size={12} strokeWidth={1.5} /> {adminMode ? "Ombudsman queue" : "My disputes"}
      </button>

      <div className="card p-6">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <span className="label inline-flex items-center gap-2">
              <Scale size={11} strokeWidth={1.5} /> Dispute · {d.category}
            </span>
            <h1 className="font-serif text-2xl mt-1">{d.title}</h1>
          </div>
          <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded ${pill?.cls}`}>{pill?.label}</span>
        </div>
        <div className="grid sm:grid-cols-3 gap-3 mt-4 text-xs">
          <Box label="Filed by" value={d.filed_by_user?.name} sub={d.filed_by_user?.email} />
          <Box label="About" value={d.against_user?.name} sub={d.against_user?.email} />
          <Box label="Assigned to" value={d.assigned_ombudsman_user?.name || "Unassigned"} sub={d.assigned_ombudsman_user?.email} />
        </div>

        <h3 className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mt-6 mb-2">Description</h3>
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{d.description}</p>

        {(d.thread_id || d.transaction_id) && (
          <div className="mt-4 flex flex-wrap gap-3 text-xs">
            {d.thread_id && (
              <Link to={`/dashboard/messages/${d.thread_id}`} className="text-[#476B6B] hover:underline inline-flex items-center gap-1">
                Linked thread <ExternalLink size={11} strokeWidth={1.5} />
              </Link>
            )}
            {d.transaction_id && (
              <span className="text-[#5C6B6B]">Linked transaction: <code className="text-[10px]">{d.transaction_id}</code></span>
            )}
          </div>
        )}

        {d.resolution && (
          <div className="mt-6 card p-4 bg-[#FAF8F5] border-[#E5E1D8]" data-testid="dispute-resolution">
            <p className="text-[10px] uppercase tracking-wider text-[#C9A961] mb-1">
              Outcome: {d.resolution.outcome} {d.resolution.financial_credit_usd ? `· Credit: $${d.resolution.financial_credit_usd.toFixed(2)}` : ""}
            </p>
            <p className="text-sm whitespace-pre-wrap">{d.resolution.note}</p>
            <p className="text-[10px] text-[#5C6B6B] mt-2">Resolved {new Date(d.resolution.resolved_at).toLocaleString()}</p>
          </div>
        )}
      </div>

      {showAdminActions && (
        <div className="card p-6 mt-6" data-testid="admin-actions">
          <h3 className="font-serif text-lg inline-flex items-center gap-2"><Shield size={16} strokeWidth={1.5} /> Ombudsman actions</h3>

          <div className="mt-4">
            <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Assign to ombudsman</p>
            <div className="flex gap-2">
              <select value={assigning} onChange={(e) => setAssigning(e.target.value)} className="input-field text-sm flex-1" data-testid="assign-ombudsman">
                <option value="">— select —</option>
                {ombudsmen.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
              <button onClick={assign} disabled={busy} className="btn-outline text-xs" data-testid="assign-button">
                {busy ? "…" : "Assign"}
              </button>
            </div>
          </div>

          <div className="mt-4">
            <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Move status</p>
            <div className="flex gap-2">
              <select value={newStatus} onChange={(e) => setNewStatus(e.target.value)} className="input-field text-sm" data-testid="new-status">
                <option value="open">Open</option>
                <option value="under_review">Under review</option>
              </select>
              <input value={statusNote} onChange={(e) => setStatusNote(e.target.value)} placeholder="Note for audit log" className="input-field text-sm flex-1" data-testid="status-note" />
              <button onClick={updateStatus} disabled={busy} className="btn-outline text-xs" data-testid="status-update">
                {busy ? "…" : "Update"}
              </button>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-[#E5E1D8]">
            <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mb-1">Resolve / dismiss</p>
            <div className="flex gap-2 flex-wrap items-end">
              <div>
                <label className="block text-[10px] text-[#5C6B6B]">Outcome</label>
                <select value={outcome} onChange={(e) => setOutcome(e.target.value)} className="input-field text-sm" data-testid="outcome-select">
                  <option value="dismissed">Dismissed (no fault)</option>
                  <option value="upheld">Upheld</option>
                  <option value="partial">Partial</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-[#5C6B6B]">Financial credit $ (optional)</label>
                <input value={credit} onChange={(e) => setCredit(e.target.value)} placeholder="0.00" type="number" min="0" step="0.01" className="input-field text-sm w-32" data-testid="credit-input" />
              </div>
            </div>
            <textarea value={resolutionNote} onChange={(e) => setResolutionNote(e.target.value)} className="input-field text-sm w-full mt-2" rows={3} placeholder="Resolution rationale (≥ 10 chars; visible to filer + respondent)" data-testid="resolution-note" />
            <button onClick={resolve} disabled={busy} className="btn-primary text-xs mt-2 inline-flex items-center gap-1" data-testid="resolve-button">
              <Send size={12} strokeWidth={1.5} /> {busy ? "…" : "Finalize"}
            </button>
          </div>
        </div>
      )}

      {d.events?.length > 0 && (
        <div className="card p-6 mt-6" data-testid="dispute-timeline">
          <h3 className="font-serif text-lg">Timeline</h3>
          <ul className="mt-3 space-y-3 text-xs">
            {d.events.map((e, i) => (
              <li key={i} className="border-l-2 border-[#C9A961] pl-3" data-testid={`timeline-event-${i}`}>
                <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{e.type} · {new Date(e.at).toLocaleString()}</p>
                {e.note && <p className="text-xs text-[#1A2424] mt-0.5">{e.note}</p>}
                {e.from && e.to && <p className="text-[10px] text-[#5C6B6B]">{e.from} → {e.to}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Box({ label, value, sub }) {
  return (
    <div className="card p-3 bg-[#FAF8F5]">
      <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{label}</p>
      <p className="font-medium text-sm">{value || "—"}</p>
      {sub && <p className="text-[10px] text-[#5C6B6B] truncate">{sub}</p>}
    </div>
  );
}
