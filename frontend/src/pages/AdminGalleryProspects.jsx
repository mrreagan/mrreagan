/* Admin Gallery Prospects — outreach tracker for foundation-curated featured artists.
 *
 * Foundation leaders log artists they've reached out to (or are about to),
 * record interactions over time, and promote a prospect into a Foundation
 * Featured Artist by issuing a tokenized Explore-before-Embrace invitation.
 */
import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../lib/api";
import {
  Users, Plus, Send, MessageSquare, Trash2, ExternalLink,
  CheckCircle2, Phone, Mail, MapPin, Sparkles, Eye,
} from "lucide-react";

const STATUS_LABEL = {
  outreach_sent: "Outreach sent",
  responded_interested: "Responded · interested",
  in_conversation: "In conversation",
  invited: "Invitation sent",
  responded_declined: "Declined",
  dormant: "Dormant",
  promoted_to_featured: "Featured · enrolled",
  archived: "Archived",
};

const CHANNEL_LABEL = {
  email: "Email", phone: "Phone", text: "Text", in_person: "In-person",
  studio_visit: "Studio visit", social_dm: "Social DM", referral: "Referral",
  event: "Event", other: "Other",
};

export default function AdminGalleryProspects() {
  const [data, setData] = useState({ prospects: [], counts: {} });
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [q, setQ] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [openId, setOpenId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (q.trim().length >= 2) params.q = q.trim();
      const r = await api.get("/gallery/admin/prospects", { params });
      setData(r.data);
    } catch (e) {
      toast.error("Couldn't load prospects.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [statusFilter]);

  return (
    <div className="container-page py-10" data-testid="admin-gallery-prospects">
      <span className="label">Foundation operations</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Users size={26} strokeWidth={1.2} /> Featured Artist prospects
      </h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        Track artists Foundation leaders are cultivating before they accept featured status.
        Log interactions, watch responses come in, then promote a prospect into a tokenized
        invitation — they explore the full featured experience before committing.
      </p>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 mt-6">
        {["all", "outreach_sent", "responded_interested", "in_conversation", "invited", "promoted_to_featured", "responded_declined", "archived"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs border transition ${
              statusFilter === s
                ? "bg-[#1A2424] text-white border-[#1A2424]"
                : "border-[#E5DDD0] text-[#5C6B6B] hover:border-[#C9A961]"
            }`}
            data-testid={`prospect-filter-${s}`}
          >
            {s === "all" ? "All" : STATUS_LABEL[s] || s}
            {data.counts[s] > 0 && <span className="ml-1.5 opacity-75">({data.counts[s]})</span>}
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-2 items-center justify-between">
        <div className="relative max-w-md flex-1">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Search by name, location, mediums…"
            className="input-field"
            data-testid="prospect-search-input"
          />
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2" data-testid="add-prospect-btn">
          <Plus size={14} /> Log a new prospect
        </button>
      </div>

      {showCreate && (
        <CreateProspectForm
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); load(); }}
        />
      )}

      <div className="mt-8 space-y-3">
        {loading ? (
          <p className="text-sm text-[#5C6B6B]">Loading…</p>
        ) : data.prospects.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] italic" data-testid="prospects-empty">
            No prospects in this view yet. Log the first one above.
          </p>
        ) : data.prospects.map((p) => (
          <ProspectCard
            key={p.id}
            prospect={p}
            isOpen={openId === p.id}
            onToggle={() => setOpenId(openId === p.id ? null : p.id)}
            onChanged={load}
          />
        ))}
      </div>
    </div>
  );
}

function CreateProspectForm({ onClose, onCreated }) {
  const [form, setForm] = useState({
    display_name: "", contact_email: "", contact_phone: "",
    social_url: "", portfolio_url: "", location: "", mediums: "",
    statement_excerpt: "", referred_by: "", internal_notes: "",
    initial_interaction_channel: "studio_visit",
    initial_interaction_notes: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (form.display_name.trim().length < 2) {
      toast.error("Display name is required.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/gallery/admin/prospects", form);
      toast.success("Prospect logged.");
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't log prospect.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card p-5 mt-6 bg-[#FAF8F5]" data-testid="create-prospect-form">
      <p className="font-serif text-lg text-[#1A2424]">New prospect</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
        <Field label="Display name" required value={form.display_name} onChange={(v) => setForm({ ...form, display_name: v })} testid="prospect-name-input" />
        <Field label="Contact email" type="email" value={form.contact_email} onChange={(v) => setForm({ ...form, contact_email: v })} testid="prospect-email-input" />
        <Field label="Contact phone" value={form.contact_phone} onChange={(v) => setForm({ ...form, contact_phone: v })} testid="prospect-phone-input" />
        <Field label="Location" value={form.location} onChange={(v) => setForm({ ...form, location: v })} testid="prospect-location-input" />
        <Field label="Portfolio / own gallery URL" value={form.portfolio_url} onChange={(v) => setForm({ ...form, portfolio_url: v })} testid="prospect-portfolio-input" />
        <Field label="Social URL" value={form.social_url} onChange={(v) => setForm({ ...form, social_url: v })} testid="prospect-social-input" />
        <Field label="Mediums" value={form.mediums} onChange={(v) => setForm({ ...form, mediums: v })} placeholder="plein-air oils, watercolor" testid="prospect-mediums-input" />
        <Field label="Referred by" value={form.referred_by} onChange={(v) => setForm({ ...form, referred_by: v })} testid="prospect-referred-input" />
      </div>
      <div className="mt-3">
        <p className="label">Statement excerpt</p>
        <textarea value={form.statement_excerpt} onChange={(e) => setForm({ ...form, statement_excerpt: e.target.value })} rows={2} className="input-field" placeholder="A line or two from their own writing (or pulled from their portfolio)…" data-testid="prospect-statement-input" />
      </div>
      <div className="mt-3">
        <p className="label">Internal notes (Foundation-only)</p>
        <textarea value={form.internal_notes} onChange={(e) => setForm({ ...form, internal_notes: e.target.value })} rows={2} className="input-field" placeholder="Why are they on your radar? Any context to remember." data-testid="prospect-notes-input" />
      </div>
      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <p className="label">First interaction channel</p>
          <select className="input-field" value={form.initial_interaction_channel} onChange={(e) => setForm({ ...form, initial_interaction_channel: e.target.value })} data-testid="prospect-channel-input">
            {Object.entries(CHANNEL_LABEL).map(([k, v]) => (<option key={k} value={k}>{v}</option>))}
          </select>
        </div>
        <Field label="First interaction notes" value={form.initial_interaction_notes} onChange={(v) => setForm({ ...form, initial_interaction_notes: v })} placeholder="Where, when, gist of the conversation" testid="prospect-first-notes-input" />
      </div>
      <div className="mt-4 flex gap-2">
        <button onClick={submit} disabled={submitting} className="btn-primary" data-testid="create-prospect-submit">{submitting ? "Saving…" : "Save prospect"}</button>
        <button onClick={onClose} className="btn-secondary" data-testid="create-prospect-cancel">Cancel</button>
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

function ProspectCard({ prospect, isOpen, onToggle, onChanged }) {
  const [intChannel, setIntChannel] = useState("email");
  const [intNotes, setIntNotes] = useState("");
  const [intResponded, setIntResponded] = useState(false);
  const [submittingInt, setSubmittingInt] = useState(false);
  const [showPromote, setShowPromote] = useState(false);

  const addInteraction = async () => {
    if (intNotes.trim().length < 2) return toast.error("Notes are required.");
    setSubmittingInt(true);
    try {
      await api.post(`/gallery/admin/prospects/${prospect.id}/interactions`, {
        channel: intChannel, notes: intNotes.trim(),
        response_received: intResponded,
      });
      setIntNotes(""); setIntResponded(false);
      toast.success("Interaction logged.");
      onChanged();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't log.");
    } finally {
      setSubmittingInt(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete prospect "${prospect.display_name}"? This removes the record permanently. Use status=archived to preserve the trail.`)) return;
    try {
      await api.delete(`/gallery/admin/prospects/${prospect.id}`);
      toast.success("Deleted.");
      onChanged();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't delete.");
    }
  };

  return (
    <div className="card p-4" data-testid="prospect-card">
      <div className="flex items-start justify-between gap-3 cursor-pointer" onClick={onToggle} data-testid={`prospect-toggle-${prospect.id}`}>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-3 flex-wrap">
            <p className="font-serif text-base text-[#1A2424] truncate">{prospect.display_name}</p>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#FAF8F5] border border-[#E5DDD0] text-[#476B6B]">
              {STATUS_LABEL[prospect.status] || prospect.status}
            </span>
            {prospect.foundation_score != null && (
              <span className="text-[10px] text-[#C9A961]">★ {prospect.foundation_score}/5</span>
            )}
          </div>
          <div className="text-xs text-[#5C6B6B] flex items-center gap-3 mt-1 flex-wrap">
            {prospect.location && <span className="flex items-center gap-1"><MapPin size={11} />{prospect.location}</span>}
            {prospect.mediums && <span>{prospect.mediums}</span>}
            {prospect.contact_email && <span className="flex items-center gap-1"><Mail size={11} />{prospect.contact_email}</span>}
            {prospect.contact_phone && <span className="flex items-center gap-1"><Phone size={11} />{prospect.contact_phone}</span>}
          </div>
          <p className="text-xs text-[#476B6B] mt-2">{(prospect.interactions || []).length} interaction{prospect.interactions?.length === 1 ? "" : "s"} · last updated {prospect.updated_at?.slice(0, 10)}</p>
        </div>
      </div>

      {isOpen && (
        <div className="mt-4 space-y-4 border-t border-[#E5DDD0] pt-4">
          {prospect.statement_excerpt && (
            <blockquote className="text-sm text-[#1A2424] italic border-l-2 border-[#C9A961] pl-3">"{prospect.statement_excerpt}"</blockquote>
          )}
          {prospect.internal_notes && (
            <div className="bg-[#FAF8F5] border border-[#E5DDD0] rounded p-3 text-xs text-[#5C6B6B]">
              <strong className="text-[#1A2424]">Internal notes:</strong> {prospect.internal_notes}
            </div>
          )}

          {/* Interactions */}
          <div>
            <p className="label">Interaction history</p>
            <ul className="mt-2 space-y-2">
              {(prospect.interactions || []).slice().reverse().map((i) => (
                <li key={i.id} className="text-sm text-[#1A2424] border-l-2 pl-3" style={{ borderColor: i.response_received ? "#476B6B" : "#E5DDD0" }} data-testid={`interaction-${i.id}`}>
                  <div className="text-xs text-[#5C6B6B]">
                    {CHANNEL_LABEL[i.channel] || i.channel} · {i.occurred_at?.slice(0, 10)}
                    {i.response_received && <span className="text-[#476B6B] ml-2">· responded</span>}
                  </div>
                  <p className="text-sm mt-0.5">{i.notes}</p>
                </li>
              ))}
            </ul>
          </div>

          {/* Add interaction */}
          <div className="bg-[#FAF8F5] p-3 rounded border border-[#E5DDD0]">
            <p className="label">Log a new interaction</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2">
              <select className="input-field" value={intChannel} onChange={(e) => setIntChannel(e.target.value)} data-testid={`interaction-channel-${prospect.id}`}>
                {Object.entries(CHANNEL_LABEL).map(([k, v]) => (<option key={k} value={k}>{v}</option>))}
              </select>
              <label className="text-xs text-[#1A2424] flex items-center gap-2">
                <input type="checkbox" checked={intResponded} onChange={(e) => setIntResponded(e.target.checked)} data-testid={`interaction-responded-${prospect.id}`} />
                Artist responded
              </label>
            </div>
            <textarea
              value={intNotes}
              onChange={(e) => setIntNotes(e.target.value)}
              rows={2}
              placeholder="What happened? (For the Foundation's record only.)"
              className="input-field mt-2"
              data-testid={`interaction-notes-${prospect.id}`}
            />
            <button onClick={addInteraction} disabled={submittingInt} className="btn-secondary mt-2 inline-flex items-center gap-2" data-testid={`log-interaction-btn-${prospect.id}`}>
              <MessageSquare size={14} /> Log interaction
            </button>
          </div>

          {/* Promote */}
          {prospect.status !== "promoted_to_featured" && prospect.status !== "invited" && (
            !showPromote ? (
              <button onClick={() => setShowPromote(true)} className="btn-primary inline-flex items-center gap-2" data-testid={`promote-prospect-btn-${prospect.id}`}>
                <Send size={14} /> Issue Foundation invitation
              </button>
            ) : (
              <PromoteForm
                prospect={prospect}
                onCancel={() => setShowPromote(false)}
                onDone={() => { setShowPromote(false); onChanged(); }}
              />
            )
          )}
          {(prospect.active_invite_token || prospect.promoted_to_slot_id) && (
            <div className="bg-[#FAF8F5] border border-[#C9A961] rounded p-3 text-xs flex items-start gap-2">
              <CheckCircle2 size={14} className="text-[#C9A961] mt-0.5" />
              <div className="flex-1">
                {prospect.active_invite_token && (
                  <div>
                    <strong className="text-[#1A2424]">Active invitation</strong> — preview link:
                    <a className="ml-1 underline text-[#9E3C3C] mr-3" target="_blank" rel="noopener noreferrer" href={`/gallery/invite/${prospect.active_invite_token}`} data-testid={`preview-link-${prospect.id}`}>
                      /gallery/invite/{prospect.active_invite_token.slice(0, 8)}… <ExternalLink size={11} className="inline" />
                    </a>
                    <a className="underline text-[#476B6B] inline-flex items-center gap-1" target="_blank" rel="noopener noreferrer" href={`/gallery/invite/${prospect.active_invite_token}`} data-testid={`sanity-check-link-${prospect.id}`}>
                      <Eye size={11} /> Sanity-check before send
                    </a>
                  </div>
                )}
                {prospect.promoted_to_slot_id && (
                  <div className="mt-1"><strong className="text-[#1A2424]">Enrolled</strong> — featured slot {prospect.promoted_to_slot_id.slice(0, 8)}…</div>
                )}
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
  const today = new Date();
  const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, 1);
  const [month, setMonth] = useState(`${nextMonth.getFullYear()}-${String(nextMonth.getMonth() + 1).padStart(2, "0")}`);
  const [reason, setReason] = useState("");
  const [periodLabel, setPeriodLabel] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (reason.trim().length < 10) return toast.error("Add a published reason (at least 10 chars).");
    setSubmitting(true);
    try {
      const r = await api.post(`/gallery/admin/prospects/${prospect.id}/promote`, {
        feature_in_month: month,
        period_label: periodLabel.trim() || undefined,
        editorial_reason: reason.trim(),
      });
      toast.success(`Invitation sent. Preview: ${r.data.preview_url}`);
      onDone();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't promote.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-[#FAF8F5] border border-[#C9A961] rounded p-4 space-y-3" data-testid={`promote-form-${prospect.id}`}>
      <p className="font-serif text-base flex items-center gap-2"><Sparkles size={14} className="text-[#C9A961]" /> Issue Foundation invitation</p>
      <p className="text-xs text-[#5C6B6B]">
        Sends a tokenized invitation email to <strong className="text-[#1A2424]">{prospect.contact_email}</strong>.
        They can explore the full featured experience before committing — only enrolling creates their account.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <p className="label">Feature in month (YYYY-MM)</p>
          <input className="input-field" value={month} onChange={(e) => setMonth(e.target.value)} placeholder="2026-08" data-testid={`promote-month-${prospect.id}`} />
        </div>
        <div>
          <p className="label">Period label (optional)</p>
          <input className="input-field" value={periodLabel} onChange={(e) => setPeriodLabel(e.target.value)} placeholder="August 2026" data-testid={`promote-label-${prospect.id}`} />
        </div>
      </div>
      <div>
        <p className="label">Why this artist? <span className="text-[#5C6B6B]">· published with the feature</span></p>
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} className="input-field" placeholder="One short paragraph the audience will see on the featured card." data-testid={`promote-reason-${prospect.id}`} />
      </div>
      <div className="flex gap-2 pt-1">
        <button onClick={submit} disabled={submitting} className="btn-primary" data-testid={`promote-submit-${prospect.id}`}>{submitting ? "Sending…" : "Send invitation"}</button>
        <button onClick={onCancel} className="btn-secondary" data-testid={`promote-cancel-${prospect.id}`}>Cancel</button>
      </div>
    </div>
  );
}
