import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import { Briefcase, Mail, CheckCircle2, XCircle, Users, Microscope, Store } from "lucide-react";

const TYPE_ICON = { facilitator: Users, community: Briefcase, research: Microscope, vendor: Store };

const STATUS_TABS = ["pending", "approved", "rejected"];

export default function AdminPartners() {
  const [tab, setTab] = useState("pending");
  const [partnerType, setPartnerType] = useState("");
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams({ status: tab });
    if (partnerType) params.set("partner_type", partnerType);
    api.get(`/admin/partners/applications?${params}`)
      .then((r) => setApps(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [tab, partnerType]);

  return (
    <div className="container-page py-12" data-testid="admin-partners-page">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <span className="label">Admin</span>
          <h1 className="editorial-h1 mt-2">Partner applications</h1>
        </div>
        <button onClick={() => setShowInvite(true)} className="btn-primary" data-testid="invite-partner-btn">
          <Mail size={14} strokeWidth={1.5} className="inline mr-1" /> Invite partner
        </button>
      </div>
      <div className="divider-flame" />

      <div className="flex flex-wrap gap-2" data-testid="admin-status-tabs">
        {STATUS_TABS.map((s) => (
          <button
            key={s}
            onClick={() => setTab(s)}
            className={`px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
              tab === s ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`admin-status-${s}`}
          >
            {s}
          </button>
        ))}
        <select
          value={partnerType}
          onChange={(e) => setPartnerType(e.target.value)}
          className="input-field text-xs ml-auto max-w-[160px]"
          data-testid="admin-type-filter"
        >
          <option value="">All types</option>
          <option value="facilitator">Facilitator</option>
          <option value="community">Community</option>
          <option value="research">Research</option>
          <option value="vendor">Vendor</option>
        </select>
      </div>

      <div className="mt-6 space-y-3" data-testid="admin-applications-list">
        {loading ? (
          <p className="text-sm text-[#5C6B6B]">Loading...</p>
        ) : apps.length === 0 ? (
          <div className="card p-10 text-center">
            <p className="font-serif text-lg">No {tab} applications.</p>
          </div>
        ) : (
          apps.map((a) => <ApplicationRow key={a.id} app={a} onUpdate={load} />)
        )}
      </div>

      {showInvite && <InviteModal onClose={() => setShowInvite(false)} onInvited={() => { setShowInvite(false); load(); }} />}
    </div>
  );
}

function ApplicationRow({ app, onUpdate }) {
  const [expanded, setExpanded] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const Icon = TYPE_ICON[app.partner_type] || Briefcase;

  const decide = async (action) => {
    setBusy(true);
    try {
      await api.post(`/admin/partners/applications/${app.id}/${action}`, { admin_note: note });
      toast.success(`Application ${action === "approve" ? "approved" : "rejected"}`);
      onUpdate();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Action failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="card p-5" data-testid={`admin-app-${app.id}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <Icon size={20} strokeWidth={1.5} className="text-[#C9A961] mt-1" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] uppercase tracking-wider text-[#C9A961]">{app.partner_type}</span>
              <span className="text-[10px] uppercase tracking-wider">{app.status}</span>
            </div>
            <p className="font-medium mt-1">
              {app.applicant_name || app.applicant_email || "(unknown applicant)"}
              {app.invited_by_admin_id && <span className="ml-2 text-[10px] uppercase tracking-wider text-[#476B6B]">Invited</span>}
            </p>
            <p className="text-xs text-[#5C6B6B]">{app.applicant_email} · Submitted {new Date(app.created_at).toLocaleString()}</p>
            {app.data?.headline && <p className="font-serif text-base mt-2">{app.data.headline}</p>}
          </div>
        </div>
        <button onClick={() => setExpanded((v) => !v)} className="btn-outline text-xs" data-testid={`toggle-app-${app.id}`}>
          {expanded ? "Hide" : "Details"}
        </button>
      </div>
      {expanded && (
        <div className="mt-4 border-t border-[#E5E1D8] pt-4 space-y-2" data-testid={`app-details-${app.id}`}>
          {app.data?.bio && <DetailRow label="Bio" value={app.data.bio} />}
          {app.data?.presents_birthright_ip != null && (
            <DetailRow label="Presents Birthright IP" value={app.data.presents_birthright_ip ? "Yes" : "No"} />
          )}
          {app.data?.credentials && <DetailRow label="Credentials" value={app.data.credentials} />}
          {app.data?.training_history && <DetailRow label="Training" value={app.data.training_history} />}
          {app.data?.sample_curriculum_url && <DetailRow label="Curriculum" value={app.data.sample_curriculum_url} link />}
          {app.data?.organization && <DetailRow label="Organization" value={app.data.organization} />}
          {app.data?.audience_size != null && <DetailRow label="Audience size" value={String(app.data.audience_size)} />}
          {app.data?.referral_plan && <DetailRow label="Referral plan" value={app.data.referral_plan} />}
          {app.data?.institution && <DetailRow label="Institution" value={app.data.institution} />}
          {app.data?.area_of_research && <DetailRow label="Research area" value={app.data.area_of_research} />}
          {app.data?.sample_publications_url && <DetailRow label="Publications" value={app.data.sample_publications_url} link />}
          {app.data?.business_name && <DetailRow label="Business" value={app.data.business_name} />}
          {app.data?.product_categories && <DetailRow label="Categories" value={app.data.product_categories} />}
          {app.data?.website_url && <DetailRow label="Website" value={app.data.website_url} link />}
          {app.data?.location && <DetailRow label="Location" value={app.data.location} />}
          {app.data?.apply_as_founding_partner && (
            <div className="px-2 py-1.5 rounded bg-[#FFFBEF] border-l-4 border-[#C9A961] text-xs text-[#8B7128]" data-testid={`founding-requested-${app.id}`}>
              ★ Applicant requested <strong>Founding Partner</strong> status. Approving will auto-grant the flag if a seat is available.
            </div>
          )}
          {app.admin_note && <DetailRow label="Admin note" value={app.admin_note} />}

          {app.status === "pending" && (
            <div className="mt-4 space-y-2">
              <input
                className="input-field text-sm"
                placeholder="Optional note (visible to applicant on rejection, audit-logged on approval)"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={2000}
                data-testid={`admin-note-${app.id}`}
              />
              <div className="flex gap-2">
                <button onClick={() => decide("approve")} disabled={busy || !app.user_id} className="btn-primary inline-flex items-center gap-1" data-testid={`approve-${app.id}`}>
                  <CheckCircle2 size={14} strokeWidth={1.5} /> Approve
                </button>
                <button onClick={() => decide("reject")} disabled={busy} className="btn-outline inline-flex items-center gap-1" data-testid={`reject-${app.id}`}>
                  <XCircle size={14} strokeWidth={1.5} /> Reject
                </button>
                {!app.user_id && (
                  <p className="text-xs italic text-[#5C6B6B] self-center">Invitee must register + finalize application before approval.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value, link }) {
  return (
    <div>
      <span className="text-[10px] uppercase tracking-wider text-[#5C6B6B]">{label}</span>
      {link ? (
        <a href={value} target="_blank" rel="noreferrer" className="block text-sm text-[#476B6B] hover:underline break-all">{value}</a>
      ) : (
        <p className="text-sm whitespace-pre-wrap">{value}</p>
      )}
    </div>
  );
}

function InviteModal({ onClose, onInvited }) {
  const [form, setForm] = useState({ email: "", partner_type: "facilitator", admin_note: "" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/admin/partners/invite", form);
      toast.success(`Invited ${form.email}`);
      onInvited();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not invite");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#1A2424]/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid="invite-modal">
      <div className="bg-white w-full max-w-md rounded-xl p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-2xl">Invite a partner</h2>
          <button onClick={onClose} className="text-[#5C6B6B] hover:text-[#1A2424]" data-testid="close-invite">✕</button>
        </div>
        <p className="text-xs text-[#5C6B6B] mt-1">We'll email them an invitation. They finalize the application themselves after registering.</p>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <div>
            <label className="label">Email</label>
            <input type="email" required className="input-field mt-1" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} data-testid="invite-email" />
          </div>
          <div>
            <label className="label">Partner type</label>
            <select className="input-field mt-1" value={form.partner_type} onChange={(e) => setForm((f) => ({ ...f, partner_type: e.target.value }))} data-testid="invite-type">
              <option value="facilitator">Facilitator</option>
              <option value="community">Community</option>
              <option value="research">Research</option>
              <option value="vendor">Vendor</option>
            </select>
          </div>
          <div>
            <label className="label">Note (included in invite email)</label>
            <textarea className="input-field mt-1" value={form.admin_note} onChange={(e) => setForm((f) => ({ ...f, admin_note: e.target.value }))} maxLength={1000} data-testid="invite-note" />
          </div>
          <button type="submit" disabled={busy} className="btn-primary w-full" data-testid="invite-submit">{busy ? "Sending..." : "Send invitation"}</button>
        </form>
      </div>
    </div>
  );
}
