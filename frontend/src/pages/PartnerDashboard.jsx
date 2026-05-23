import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { CheckCircle2, Clock, XCircle, Pencil, Globe, Eye, EyeOff } from "lucide-react";

const STATUS_BADGE = {
  pending:  { label: "Pending",  cls: "bg-[#C9A961]/15 text-[#8B7128] border-[#C9A961]/40", icon: Clock },
  approved: { label: "Approved", cls: "bg-[#2E5C46]/10 text-[#2E5C46] border-[#2E5C46]/30", icon: CheckCircle2 },
  rejected: { label: "Not approved", cls: "bg-[#B86A5C]/10 text-[#B86A5C] border-[#B86A5C]/30", icon: XCircle },
};

const PROFILE_STATUS_BADGE = {
  active:  { label: "Live", cls: "bg-[#2E5C46]/10 text-[#2E5C46]" },
  paused:  { label: "Paused", cls: "bg-[#C9A961]/15 text-[#8B7128]" },
  revoked: { label: "Revoked", cls: "bg-[#B86A5C]/10 text-[#B86A5C]" },
};

export default function PartnerDashboard() {
  const { user } = useAuth();
  const [apps, setApps] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get("/partners/my-applications"),
      api.get("/partners/my-profiles"),
    ]).then(([a, p]) => {
      setApps(a.data);
      setProfiles(p.data);
    }).finally(() => setLoading(false));
  };
  useEffect(load, []);

  if (!user) return null;

  return (
    <div className="container-page py-12" data-testid="partner-dashboard-page">
      <span className="label">Partner network</span>
      <h1 className="editorial-h1 mt-2">Your partner workspace</h1>
      <div className="divider-flame" />

      {loading && <p className="text-sm text-[#5C6B6B]">Loading...</p>}

      {!loading && profiles.length === 0 && apps.length === 0 && (
        <div className="card p-10 text-center" data-testid="empty-state">
          <p className="font-serif text-xl">You haven't applied yet.</p>
          <p className="text-sm text-[#5C6B6B] mt-2">Become a Birthright partner — facilitator, community ally, researcher, or vendor.</p>
          <Link to="/partners/apply" className="btn-primary mt-6 inline-block">Apply now</Link>
        </div>
      )}

      {profiles.length > 0 && (
        <section className="mt-2" data-testid="my-profiles-section">
          <h2 className="font-serif text-xl">Your live partner profiles</h2>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
            {profiles.map((p) => <ProfileCard key={p.id} profile={p} onChange={load} />)}
          </div>
        </section>
      )}

      <section className="mt-10" data-testid="my-applications-section">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-xl">Your applications</h2>
          <Link to="/partners/apply" className="btn-outline text-xs" data-testid="apply-another-btn">Apply for another type</Link>
        </div>
        {apps.length === 0 ? (
          <p className="text-sm text-[#5C6B6B] mt-3">No applications yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-[#E5E1D8]">
            {apps.map((a) => {
              const cfg = STATUS_BADGE[a.status] || STATUS_BADGE.pending;
              const Icon = cfg.icon;
              return (
                <li key={a.id} className="py-3 flex items-start justify-between gap-3" data-testid={`my-app-${a.id}`}>
                  <div>
                    <p className="font-medium capitalize">{a.partner_type} partner</p>
                    <p className="text-xs text-[#5C6B6B] mt-1">
                      Submitted {new Date(a.created_at).toLocaleDateString()}
                      {a.decided_at && ` · Decided ${new Date(a.decided_at).toLocaleDateString()}`}
                    </p>
                    {a.admin_note && a.status === "rejected" && (
                      <p className="text-xs italic text-[#B86A5C] mt-1">Note from admin: {a.admin_note}</p>
                    )}
                  </div>
                  <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider px-2 py-1 rounded-full border ${cfg.cls}`} data-testid={`app-status-${a.id}`}>
                    <Icon size={11} strokeWidth={1.5} /> {cfg.label}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function ProfileCard({ profile, onChange }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    headline: profile.headline || "",
    bio: profile.bio || "",
    website_url: profile.website_url || "",
    location: profile.location || "",
    photo_url: profile.photo_url || "",
    public: profile.public !== false,
  });
  const [saving, setSaving] = useState(false);
  const statusCfg = PROFILE_STATUS_BADGE[profile.status] || PROFILE_STATUS_BADGE.active;
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put(`/partners/my-profiles/${profile.partner_type}`, form);
      toast.success("Profile updated");
      setEditing(false);
      onChange();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not update");
    } finally { setSaving(false); }
  };

  return (
    <div className="card p-5" data-testid={`my-profile-${profile.partner_type}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-[#C9A961]">{profile.partner_type}</p>
          <h3 className="font-serif text-lg mt-0.5">{profile.headline || "(no headline yet)"}</h3>
        </div>
        <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full ${statusCfg.cls}`}>{statusCfg.label}</span>
      </div>

      {!editing ? (
        <>
          <p className="text-sm text-[#5C6B6B] mt-3 line-clamp-4">{profile.bio}</p>
          <div className="flex flex-wrap gap-2 mt-3 text-[10px] text-[#5C6B6B]">
            {profile.location && <span>📍 {profile.location}</span>}
            {profile.website_url && <a href={profile.website_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[#476B6B] hover:underline"><Globe size={10} /> Website</a>}
            <span className="inline-flex items-center gap-1">
              {profile.public ? <Eye size={10} /> : <EyeOff size={10} />}
              {profile.public ? "Public" : "Hidden from directory"}
            </span>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={() => setEditing(true)} className="btn-outline text-xs inline-flex items-center gap-1" data-testid={`edit-profile-${profile.partner_type}`}>
              <Pencil size={11} strokeWidth={1.5} /> Edit
            </button>
            {profile.status === "active" && (
              <Link to={`/partners/${profile.slug}`} className="btn-outline text-xs">View public page</Link>
            )}
          </div>
        </>
      ) : (
        <form onSubmit={save} className="mt-3 space-y-2">
          <input className="input-field text-sm" placeholder="Headline" value={form.headline} onChange={(e) => update("headline", e.target.value)} maxLength={160} required />
          <textarea className="input-field text-sm min-h-[120px]" placeholder="Bio" value={form.bio} onChange={(e) => update("bio", e.target.value)} maxLength={4000} required />
          <input className="input-field text-sm" placeholder="Website URL" value={form.website_url} onChange={(e) => update("website_url", e.target.value)} />
          <input className="input-field text-sm" placeholder="Location" value={form.location} onChange={(e) => update("location", e.target.value)} maxLength={120} />
          <input className="input-field text-sm" placeholder="Photo URL" value={form.photo_url} onChange={(e) => update("photo_url", e.target.value)} />
          <label className="flex items-center gap-2 text-xs">
            <input type="checkbox" checked={form.public} onChange={(e) => update("public", e.target.checked)} />
            Show on the public partner directory
          </label>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="btn-primary text-xs">{saving ? "Saving..." : "Save"}</button>
            <button type="button" onClick={() => setEditing(false)} className="btn-outline text-xs">Cancel</button>
          </div>
        </form>
      )}
    </div>
  );
}
