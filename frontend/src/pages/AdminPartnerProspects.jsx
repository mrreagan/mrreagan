/* Admin Partner Prospects — generic outreach tracker for ALL partner types.
 * Companion to /admin/gallery/prospects (artist-specific featuring path);
 * this page handles facilitator / community / research / vendor / steward
 * / artist prospects and issues tokenized Explore-before-Embrace invitations.
 */
import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import {
  Users, Plus, Send, MessageSquare, Trash2, ExternalLink,
  CheckCircle2, Phone, Mail, MapPin, Sparkles, Eye,
} from "lucide-react";

const PARTNER_TYPES = ["facilitator", "community", "research", "vendor", "artist", "steward"];

const STATUS_LABEL = {
  outreach_sent: "Outreach sent",
  responded_interested: "Responded · interested",
  in_conversation: "In conversation",
  invited: "Invitation sent",
  responded_declined: "Declined",
  dormant: "Dormant",
  promoted: "Enrolled",
  archived: "Archived",
};
const CHANNEL_LABEL = {
  email: "Email", phone: "Phone", text: "Text", in_person: "In-person",
  studio_visit: "Studio visit", social_dm: "Social DM", referral: "Referral",
  event: "Event", other: "Other",
};

export default function AdminPartnerProspects() {
  const [data, setData] = useState({ prospects: [], counts_by_type: {}, counts_by_status: {} });
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [q, setQ] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [openId, setOpenId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (typeFilter !== "all") params.partner_type = typeFilter;
      if (statusFilter !== "all") params.status = statusFilter;
      if (q.trim().length >= 2) params.q = q.trim();
      const r = await api.get("/partners/admin/prospects", { params });
      setData(r.data);
    } catch (e) {
      toast.error("Couldn't load prospects.");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [typeFilter, statusFilter]);

  return (
    <div className="container-page py-10" data-testid="admin-partner-prospects">
      <span className="label">Foundation operations</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Users size={26} strokeWidth={1.2} /> Partner prospects
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Single outreach tracker for every partner role. Log prospects, record interactions,
        then issue an Explore-before-Embrace invitation — they browse the role first, enroll
        only when ready.
      </p>

      {/* Type tabs */}
      <div className="flex flex-wrap gap-2 mt-6">
        <button onClick={() => setTypeFilter("all")} className={`px-3 py-1.5 rounded-full text-xs border ${typeFilter === "all" ? "bg-[#1A2424] text-white border-[#1A2424]" : "border-[#E5DDD0] text-[#5C6B6B] hover:border-[#C9A961]"}`} data-testid="type-filter-all">All types</button>
        {PARTNER_TYPES.map((pt) => (
          <button
            key={pt}
            onClick={() => setTypeFilter(pt)}
            className={`px-3 py-1.5 rounded-full text-xs border capitalize transition ${
              typeFilter === pt ? "bg-[#1A2424] text-white border-[#1A2424]" : "border-[#E5DDD0] text-[#5C6B6B] hover:border-[#C9A961]"
            }`}
            data-testid={`type-filter-${pt}`}
          >
            {pt}
            {data.counts_by_type?.[pt] > 0 && <span className="ml-1.5 opacity-75">({data.counts_by_type[pt]})</span>}
          </button>
        ))}
      </div>

      {/* Status tabs */}
      <div className="flex flex-wrap gap-2 mt-3">
        {["all", "outreach_sent", "responded_interested", "in_conversation", "invited", "promoted", "responded_declined", "archived"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-[11px] border ${statusFilter === s ? "bg-[#476B6B] text-white border-[#476B6B]" : "border-[#E5DDD0] text-[#5C6B6B] hover:border-[#C9A961]"}`}
            data-testid={`status-filter-${s}`}
          >
            {s === "all" ? "All statuses" : STATUS_LABEL[s] || s}
            {data.counts_by_status?.[s] > 0 && <span className="ml-1 opacity-75">({data.counts_by_status[s]})</span>}
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-2 items-center justify-between">
        <div className="relative max-w-md flex-1">
          <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} placeholder="Search name, location, notes…" className="input-field" data-testid="prospect-search-input" />
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2" data-testid="add-prospect-btn">
          <Plus size={14} /> Log a new prospect
        </button>
      </div>

      {showCreate && <CreateForm onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load(); }} />}

      <div className="mt-8 space-y-3">
        {loading ? <p className="text-sm text-[#5C6B6B]">Loading…</p> :
          data.prospects.length === 0 ? (
            <p className="text-sm text-[#5C6B6B] italic" data-testid="prospects-empty">No prospects in this view yet.</p>
          ) : data.prospects.map((p) => (
            <Card key={p.id} prospect={p} isOpen={openId === p.id} onToggle={() => setOpenId(openId === p.id ? null : p.id)} onChanged={load} />
          ))
        }
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", required, placeholder, testid }) {
  return (
    <div>
      <p className="label">{label}{required && <span className="text-[#9E3C3C]">*</span>}</p>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="input-field" placeholder={placeholder} data-testid={testid} />
    </div>
  );
}

function CreateForm({ onClose, onCreated }) {
  const [form, setForm] = useState({
    partner_type: "facilitator", display_name: "", contact_email: "", contact_phone: "",
    location: "", headline_excerpt: "", bio_excerpt: "", portfolio_url: "", social_url: "",
    referred_by: "", internal_notes: "",
    initial_interaction_channel: "email", initial_interaction_notes: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (form.display_name.trim().length < 2) return toast.error("Display name required.");
    setSubmitting(true);
    try {
      await api.post("/partners/admin/prospects", form);
      toast.success("Prospect logged.");
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't log prospect.");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="card p-5 mt-6 bg-[#FAF8F5]" data-testid="create-prospect-form">
      <p className="font-serif text-lg text-[#1A2424]">New prospect</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
        <div>
          <p className="label">Partner type<span className="text-[#9E3C3C]">*</span></p>
          <select value={form.partner_type} onChange={(e) => setForm({ ...form, partner_type: e.target.value })} className="input-field capitalize" data-testid="prospect-type-input">
            {PARTNER_TYPES.map((pt) => <option key={pt} value={pt}>{pt}</option>)}
          </select>
        </div>
        <Field label="Display name" required value={form.display_name} onChange={(v) => setForm({ ...form, display_name: v })} testid="prospect-name-input" />
        <Field label="Contact email" type="email" value={form.contact_email} onChange={(v) => setForm({ ...form, contact_email: v })} testid="prospect-email-input" />
        <Field label="Contact phone" value={form.contact_phone} onChange={(v) => setForm({ ...form, contact_phone: v })} testid="prospect-phone-input" />
        <Field label="Location" value={form.location} onChange={(v) => setForm({ ...form, location: v })} testid="prospect-location-input" />
        <Field label="Portfolio URL" value={form.portfolio_url} onChange={(v) => setForm({ ...form, portfolio_url: v })} testid="prospect-portfolio-input" />
        <Field label="Social URL" value={form.social_url} onChange={(v) => setForm({ ...form, social_url: v })} testid="prospect-social-input" />
        <Field label="Referred by" value={form.referred_by} onChange={(v) => setForm({ ...form, referred_by: v })} testid="prospect-referred-input" />
      </div>
      <div className="mt-3">
        <p className="label">Headline (excerpt — used as their default profile headline)</p>
        <input value={form.headline_excerpt} onChange={(e) => setForm({ ...form, headline_excerpt: e.target.value })} className="input-field" data-testid="prospect-headline-input" />
      </div>
      <div className="mt-3">
        <p className="label">Bio excerpt (their words or paraphrased — used as their default bio)</p>
        <textarea value={form.bio_excerpt} onChange={(e) => setForm({ ...form, bio_excerpt: e.target.value })} rows={2} className="input-field" data-testid="prospect-bio-input" />
      </div>
      <div className="mt-3">
        <p className="label">Internal notes (Foundation-only)</p>
        <textarea value={form.internal_notes} onChange={(e) => setForm({ ...form, internal_notes: e.target.value })} rows={2} className="input-field" data-testid="prospect-notes-input" />
      </div>
      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <p className="label">First interaction channel</p>
          <select className="input-field" value={form.initial_interaction_channel} onChange={(e) => setForm({ ...form, initial_interaction_channel: e.target.value })} data-testid="prospect-channel-input">
            {Object.entries(CHANNEL_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <Field label="First interaction notes" value={form.initial_interaction_notes} onChange={(v) => setForm({ ...form, initial_interaction_notes: v })} testid="prospect-first-notes-input" />
      </div>
      <div className="mt-4 flex gap-2">
        <button onClick={submit} disabled={submitting} className="btn-primary" data-testid="create-prospect-submit">{submitting ? "Saving…" : "Save prospect"}</button>
        <button onClick={onClose} className="btn-secondary" data-testid="create-prospect-cancel">Cancel</button>
      </div>
    </div>
  );
}

function Card({ prospect, isOpen, onToggle, onChanged }) {
  const [intChannel, setIntChannel] = useState("email");
  const [intNotes, setIntNotes] = useState("");
  const [intResponded, setIntResponded] = useState(false);
  const [submittingInt, setSubmittingInt] = useState(false);
  const [showPromote, setShowPromote] = useState(false);

  const addInteraction = async () => {
    if (intNotes.trim().length < 2) return toast.error("Notes required.");
    setSubmittingInt(true);
    try {
      await api.post(`/partners/admin/prospects/${prospect.id}/interactions`, {
        channel: intChannel, notes: intNotes.trim(), response_received: intResponded,
      });
      setIntNotes(""); setIntResponded(false);
      toast.success("Interaction logged.");
      onChanged();
    } catch (e) { toast.error(e.response?.data?.detail || "Couldn't log."); }
    finally { setSubmittingInt(false); }
  };

  const remove = async () => {
    if (!window.confirm(`Delete "${prospect.display_name}"? Permanent — use Archived status to preserve trail.`)) return;
    try {
      await api.delete(`/partners/admin/prospects/${prospect.id}`);
      toast.success("Deleted."); onChanged();
    } catch (e) { toast.error(e.response?.data?.detail || "Couldn't delete."); }
  };

  return (
    <div className="card p-4" data-testid={`prospect-card-${prospect.id}`}>
      <div className="flex items-start justify-between gap-3 cursor-pointer" onClick={onToggle} data-testid={`prospect-toggle-${prospect.id}`}>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-3 flex-wrap">
            <p className="font-serif text-base text-[#1A2424] truncate">{prospect.display_name}</p>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#FAF8F5] border border-[#C9A961] text-[#476B6B] capitalize">{prospect.partner_type}</span>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#FAF8F5] border border-[#E5DDD0] text-[#476B6B]">{STATUS_LABEL[prospect.status] || prospect.status}</span>
            {prospect.foundation_score != null && <span className="text-[10px] text-[#C9A961]">★ {prospect.foundation_score}/5</span>}
          </div>
          <div className="text-xs text-[#5C6B6B] flex items-center gap-3 mt-1 flex-wrap">
            {prospect.location && <span className="flex items-center gap-1"><MapPin size={11} />{prospect.location}</span>}
            {prospect.contact_email && <span className="flex items-center gap-1"><Mail size={11} />{prospect.contact_email}</span>}
            {prospect.contact_phone && <span className="flex items-center gap-1"><Phone size={11} />{prospect.contact_phone}</span>}
          </div>
          <p className="text-xs text-[#476B6B] mt-2">{(prospect.interactions || []).length} interaction{prospect.interactions?.length === 1 ? "" : "s"} · updated {prospect.updated_at?.slice(0, 10)}</p>
        </div>
      </div>

      {isOpen && (
        <div className="mt-4 space-y-4 border-t border-[#E5DDD0] pt-4">
          {prospect.headline_excerpt && <p className="text-sm text-[#1A2424]"><strong>Headline:</strong> {prospect.headline_excerpt}</p>}
          {prospect.bio_excerpt && <blockquote className="text-sm text-[#1A2424] italic border-l-2 border-[#C9A961] pl-3">"{prospect.bio_excerpt}"</blockquote>}
          {prospect.internal_notes && <div className="bg-[#FAF8F5] border border-[#E5DDD0] rounded p-3 text-xs text-[#5C6B6B]"><strong className="text-[#1A2424]">Notes:</strong> {prospect.internal_notes}</div>}

          <div>
            <p className="label">Interaction history</p>
            <ul className="mt-2 space-y-2">
              {(prospect.interactions || []).slice().reverse().map((i) => (
                <li key={i.id} className="text-sm text-[#1A2424] border-l-2 pl-3" style={{ borderColor: i.response_received ? "#476B6B" : "#E5DDD0" }} data-testid={`interaction-${i.id}`}>
                  <div className="text-xs text-[#5C6B6B]">{CHANNEL_LABEL[i.channel] || i.channel} · {i.occurred_at?.slice(0, 10)}{i.response_received && <span className="text-[#476B6B] ml-2">· responded</span>}</div>
                  <p className="text-sm mt-0.5">{i.notes}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-[#FAF8F5] p-3 rounded border border-[#E5DDD0]">
            <p className="label">Log a new interaction</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2">
              <select className="input-field" value={intChannel} onChange={(e) => setIntChannel(e.target.value)} data-testid={`interaction-channel-${prospect.id}`}>
                {Object.entries(CHANNEL_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <label className="text-xs text-[#1A2424] flex items-center gap-2">
                <input type="checkbox" checked={intResponded} onChange={(e) => setIntResponded(e.target.checked)} data-testid={`interaction-responded-${prospect.id}`} />
                Artist responded
              </label>
            </div>
            <textarea value={intNotes} onChange={(e) => setIntNotes(e.target.value)} rows={2} placeholder="What happened?" className="input-field mt-2" data-testid={`interaction-notes-${prospect.id}`} />
            <button onClick={addInteraction} disabled={submittingInt} className="btn-secondary mt-2 inline-flex items-center gap-2" data-testid={`log-interaction-btn-${prospect.id}`}>
              <MessageSquare size={14} /> Log interaction
            </button>
          </div>

          {prospect.status !== "promoted" && prospect.status !== "invited" && (
            !showPromote ? (
              <button onClick={() => setShowPromote(true)} className="btn-primary inline-flex items-center gap-2" data-testid={`promote-prospect-btn-${prospect.id}`}>
                <Send size={14} /> Issue Foundation invitation
              </button>
            ) : (
              <PromoteForm prospect={prospect} onCancel={() => setShowPromote(false)} onDone={() => { setShowPromote(false); onChanged(); }} />
            )
          )}

          {prospect.active_invite_token && (
            <div className="bg-[#FAF8F5] border border-[#C9A961] rounded p-3 text-xs flex items-start gap-2">
              <CheckCircle2 size={14} className="text-[#C9A961] mt-0.5" />
              <div className="flex-1">
                <strong className="text-[#1A2424]">Active invitation</strong>
                {' · '}
                <a className="underline text-[#9E3C3C] mr-3" target="_blank" rel="noopener noreferrer" href={`/partner/invite/${prospect.active_invite_token}`} data-testid={`preview-link-${prospect.id}`}>
                  Preview as the prospect would see it <ExternalLink size={11} className="inline" />
                </a>
                <a className="underline text-[#476B6B] inline-flex items-center gap-1" target="_blank" rel="noopener noreferrer" href={`/partner/invite/${prospect.active_invite_token}`} data-testid={`sanity-check-link-${prospect.id}`}>
                  <Eye size={11} /> Sanity-check before send
                </a>
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button onClick={remove} className="text-xs text-[#9E3C3C] hover:underline inline-flex items-center gap-1" data-testid={`delete-prospect-${prospect.id}`}><Trash2 size={11} /> Delete</button>
          </div>
        </div>
      )}
    </div>
  );
}

function PromoteForm({ prospect, onCancel, onDone }) {
  const [note, setNote] = useState("");
  const [tier, setTier] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await api.post(`/partners/admin/prospects/${prospect.id}/promote`, {
        note_to_prospect: note.trim() || undefined,
        suggested_subscription_tier: tier || undefined,
      });
      toast.success(`Invitation sent. Preview: ${r.data.preview_url}`);
      onDone();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't issue invitation.");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="bg-[#FAF8F5] border border-[#C9A961] rounded p-4 space-y-3" data-testid={`promote-form-${prospect.id}`}>
      <p className="font-serif text-base flex items-center gap-2"><Sparkles size={14} className="text-[#C9A961]" /> Issue Foundation invitation</p>
      <p className="text-xs text-[#5C6B6B]">
        Sends a tokenized email to <strong className="text-[#1A2424]">{prospect.contact_email}</strong>. They explore the {prospect.partner_type} role before committing.
      </p>
      <div>
        <p className="label">Personal note (optional)</p>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className="input-field" placeholder="A line from your last conversation, or context they should know." data-testid={`promote-note-${prospect.id}`} />
      </div>
      <div>
        <p className="label">Suggested subscription tier (optional)</p>
        <select value={tier} onChange={(e) => setTier(e.target.value)} className="input-field" data-testid={`promote-tier-${prospect.id}`}>
          <option value="">— let them choose —</option>
          <option value="monthly">Monthly</option>
          <option value="annual">Annual (most chosen)</option>
          <option value="two_year">2-year</option>
        </select>
      </div>
      <div className="flex gap-2 pt-1">
        <button onClick={submit} disabled={submitting} className="btn-primary" data-testid={`promote-submit-${prospect.id}`}>{submitting ? "Sending…" : "Send invitation"}</button>
        <button onClick={onCancel} className="btn-secondary" data-testid={`promote-cancel-${prospect.id}`}>Cancel</button>
      </div>
    </div>
  );
}
