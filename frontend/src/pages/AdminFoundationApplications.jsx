import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { Mail, Phone, FileText, Linkedin, X } from "lucide-react";

const STATUSES = ["new", "reviewing", "interviewing", "accepted", "declined", "withdrawn"];
const STATUS_COLOR = {
  new: "bg-[#476B6B] text-white",
  reviewing: "bg-[#C9A961] text-[#1A2424]",
  interviewing: "bg-[#2E5C46] text-white",
  accepted: "bg-[#2E5C46] text-white",
  declined: "bg-[#9E3C3C] text-white",
  withdrawn: "bg-[#E5E1D8] text-[#5C6B6B]",
};

export default function AdminFoundationApplications() {
  const [tab, setTab] = useState("new");
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(null); // application object being viewed
  const [note, setNote] = useState("");

  const load = () => {
    setLoading(true);
    api.get(`/admin/foundation-role-applications?status=${tab}`)
      .then((r) => setApps(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(load, [tab]);

  const decide = async (app, status) => {
    try {
      await api.post(`/admin/foundation-role-applications/${app.id}/decision?status=${status}`, {
        admin_note: note,
      });
      toast.success(`Application ${status}.`);
      setOpen(null);
      setNote("");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Update failed.");
    }
  };

  return (
    <div className="container-page py-12" data-testid="admin-foundation-applications-page">
      <span className="label">Admin</span>
      <h1 className="editorial-h1 mt-2">Foundation role applications</h1>
      <p className="text-sm text-[#5C6B6B] mt-2 max-w-2xl">
        Triage queue for applications submitted at <code>/join-us/&lt;role&gt;</code>. Move applications through the pipeline as you review and interview.
      </p>
      <div className="divider-flame" />

      <div className="flex flex-wrap gap-2" data-testid="app-status-tabs">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setTab(s)}
            className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              tab === s ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`app-status-${s}`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-3">
        {loading && <p className="text-sm text-[#5C6B6B]">Loading...</p>}
        {!loading && apps.length === 0 && (
          <div className="card p-10 text-center">
            <p className="font-serif text-lg">No applications with status "{tab}".</p>
          </div>
        )}
        {apps.map((a) => (
          <button
            key={a.id}
            onClick={() => { setOpen(a); setNote(a.admin_note || ""); }}
            className="card p-5 w-full text-left hover:border-[#476B6B] transition"
            data-testid={`app-card-${a.id}`}
          >
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-serif text-lg">{a.name}</h3>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider ${STATUS_COLOR[a.status] || "bg-[#E5E1D8]"}`}>{a.status}</span>
                </div>
                <p className="text-xs text-[#5C6B6B] mt-1">
                  {a.role_title} · {a.email}
                  {a.current_role && ` · ${a.current_role}`}
                </p>
                <p className="text-sm text-[#1A2424] mt-2 line-clamp-2">{a.why_drawn}</p>
              </div>
              <p className="text-[10px] text-[#5C6B6B]">{new Date(a.created_at).toLocaleString()}</p>
            </div>
          </button>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={() => setOpen(null)}>
          <div className="bg-white max-w-3xl w-full rounded-xl p-6 max-h-[92vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="app-detail-modal">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="font-serif text-2xl">{open.name}</h2>
                <p className="text-xs text-[#5C6B6B] mt-1">Applying for: <strong>{open.role_title}</strong></p>
              </div>
              <button onClick={() => setOpen(null)}><X size={20} strokeWidth={1.5} /></button>
            </div>

            <div className="grid sm:grid-cols-2 gap-3 mb-5 text-sm">
              <a href={`mailto:${open.email}`} className="inline-flex items-center gap-2 text-[#476B6B] hover:underline"><Mail size={14} strokeWidth={1.5} />{open.email}</a>
              {open.phone && <span className="inline-flex items-center gap-2 text-[#1A2424]"><Phone size={14} strokeWidth={1.5} />{open.phone}</span>}
              {open.linkedin_url && <a href={open.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-[#476B6B] hover:underline"><Linkedin size={14} strokeWidth={1.5} />LinkedIn</a>}
              {open.resume_url && <a href={open.resume_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-[#476B6B] hover:underline"><FileText size={14} strokeWidth={1.5} />Résumé</a>}
            </div>

            {open.current_role && (
              <div className="mb-4">
                <p className="label">Current role</p>
                <p className="text-sm text-[#1A2424] mt-1">{open.current_role}</p>
              </div>
            )}
            <div className="mb-4">
              <p className="label">Why drawn to this work</p>
              <p className="text-sm text-[#1A2424] mt-2 leading-relaxed whitespace-pre-wrap">{open.why_drawn}</p>
            </div>

            <div className="mb-4">
              <label className="block text-xs uppercase tracking-wider text-[#5C6B6B] mb-1">Admin note (visible to board only)</label>
              <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className="input-field w-full text-sm" data-testid="app-admin-note" />
            </div>

            <div className="flex flex-wrap gap-2 pt-4 border-t border-[#E5E1D8]">
              {STATUSES.filter((s) => s !== open.status).map((s) => (
                <button
                  key={s}
                  onClick={() => decide(open, s)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium ${STATUS_COLOR[s] || ""} hover:opacity-80`}
                  data-testid={`decide-${s}`}
                >
                  Move to {s}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-[#5C6B6B] mt-3">
              Decisions are audit-logged. The applicant will be notified separately via direct email.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
