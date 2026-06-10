import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";import { toast } from "sonner";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { Users, Briefcase, Microscope, Store, AlertCircle, Palette, MapPin } from "lucide-react";
import StudioVendorNudge from "../components/StudioVendorNudge";

const TYPE_OPTIONS = [
  { value: "facilitator", label: "Facilitator", icon: Users, blurb: "Lead birthright workshops or present your own attachment-science material." },
  { value: "community",   label: "Community",   icon: Briefcase, blurb: "Refer participants and amplify the work through your network." },
  { value: "research",    label: "Research",    icon: Microscope, blurb: "Advance the science with empirical or clinical contributions." },
  { value: "vendor",      label: "Vendor",      icon: Store, blurb: "Offer complementary materials, services, or tools to participants." },
  { value: "artist",      label: "Artist",      icon: Palette, blurb: "Painter, photographer, sculptor, musician, ceramicist — practice as presence." },
  { value: "steward",     label: "Steward",     icon: MapPin, blurb: "Host and moderate one local Gather community node." },
];

const EMPTY = {
  partner_type: "facilitator",
  headline: "",
  bio: "",
  website_url: "",
  location: "",
  // facilitator
  presents_birthright_ip: null,
  credentials: "",
  training_history: "",
  sample_curriculum_url: "",
  // community
  organization: "",
  audience_size: "",
  referral_plan: "",
  // research
  institution: "",
  area_of_research: "",
  sample_publications_url: "",
  // vendor
  business_name: "",
  product_categories: "",
  mediums: "",
  artist_statement: "",
  own_gallery_url: "",
  representative_works_url: "",
  accepts_commissions: false,
  requested_community_slug: "",
  community_ties: "",
  moderation_experience: "",
  // founding partner request
  apply_as_founding_partner: false,
};

export default function PartnerApply() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [myApps, setMyApps] = useState([]);

  useEffect(() => {
    if (user) api.get("/partners/my-applications").then((r) => setMyApps(r.data)).catch(() => {});
  }, [user]);

  if (!user) {
    return (
      <div className="container-page py-16 max-w-md text-center" data-testid="apply-signin-prompt">
        <span className="label">Partner application</span>
        <h1 className="editorial-h1 mt-2">Sign in to apply</h1>
        <p className="text-sm text-[#5C6B6B] mt-4">Partner applications are tied to your birthright account.</p>
        <Link to="/login" className="btn-primary mt-6 inline-block">Sign in</Link>
      </div>
    );
  }

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (form.headline.trim().length < 5) { toast.error("Please add a one-line headline (5+ chars)."); return; }
    if (form.bio.trim().length < 20) { toast.error("Please write at least 20 characters of bio."); return; }
    if (form.partner_type === "facilitator" && form.presents_birthright_ip === null) {
      toast.error("Please indicate whether you'll present birthright IP materials.");
      return;
    }
    setSubmitting(true);
    try {
      const payload = { ...form };
      // strip empties + coerce audience_size
      Object.keys(payload).forEach((k) => {
        if (payload[k] === "" || payload[k] === null) delete payload[k];
      });
      if (form.audience_size !== "") payload.audience_size = parseInt(form.audience_size, 10) || 0;
      if (form.partner_type === "facilitator") payload.presents_birthright_ip = form.presents_birthright_ip;
      payload.apply_as_founding_partner = !!form.apply_as_founding_partner;
      await api.post("/partners/apply", payload);
      toast.success("Application submitted. We'll be in touch.");
      navigate("/dashboard/partner");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not submit application");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container-page py-12 max-w-3xl" data-testid="partner-apply-page">
      <span className="label">Partner network</span>
      <h1 className="editorial-h1 mt-2">Apply to partner</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B]">
        Welcome, {user.first_name}. Tell us how you'd like to work alongside birthright.
      </p>

      <StudioVendorNudge className="mt-6" />

      {myApps.length > 0 && (
        <div className="card p-4 mt-6" data-testid="my-applications-summary">
          <span className="label">Your applications</span>
          <ul className="mt-2 text-sm divide-y divide-[#E5E1D8]">
            {myApps.map((a) => (
              <li key={a.id} className="py-2 flex items-center justify-between">
                <span className="capitalize">{a.partner_type}</span>
                <span className={`text-[10px] uppercase tracking-wider ${a.status === "approved" ? "text-[#2E5C46]" : a.status === "rejected" ? "text-[#B86A5C]" : "text-[#C9A961]"}`}>
                  {a.status}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-[#5C6B6B] mt-2">Track everything on <Link to="/dashboard/partner" className="underline">your partner dashboard</Link>.</p>
        </div>
      )}

      <form onSubmit={submit} className="mt-6 space-y-5">
        <div>
          <label className="label">Partner type</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2" data-testid="apply-type-picker">
            {TYPE_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const active = form.partner_type === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => update("partner_type", opt.value)}
                  className={`card p-3 text-left ${active ? "border-[#476B6B] ring-1 ring-[#476B6B]" : ""}`}
                  data-testid={`apply-type-${opt.value}`}
                >
                  <Icon size={16} strokeWidth={1.5} className="text-[#C9A961]" />
                  <p className="font-medium text-sm mt-2">{opt.label}</p>
                  <p className="text-[10px] text-[#5C6B6B] mt-1 leading-snug">{opt.blurb}</p>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="label">Headline (one line)</label>
          <input className="input-field mt-1" value={form.headline} onChange={(e) => update("headline", e.target.value)} maxLength={160} data-testid="apply-headline" />
        </div>
        <div>
          <label className="label">About you / your work</label>
          <textarea className="input-field mt-1 min-h-[140px]" value={form.bio} onChange={(e) => update("bio", e.target.value)} maxLength={4000} data-testid="apply-bio" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="label">Website URL</label>
            <input className="input-field mt-1" value={form.website_url} onChange={(e) => update("website_url", e.target.value)} placeholder="https://" data-testid="apply-website" />
          </div>
          <div>
            <label className="label">Location</label>
            <input className="input-field mt-1" value={form.location} onChange={(e) => update("location", e.target.value)} placeholder="City, State/Region" data-testid="apply-location" maxLength={120} />
          </div>
        </div>

        {form.partner_type === "facilitator" && (
          <fieldset className="card p-4 space-y-3" data-testid="apply-facilitator-fields">
            <legend className="label px-1">Facilitator details</legend>
            <div className="bg-[#FAF8F5] border border-[#C9A961]/40 rounded p-3 flex items-start gap-2">
              <AlertCircle size={14} strokeWidth={1.5} className="text-[#C9A961] mt-0.5 shrink-0" />
              <p className="text-xs text-[#5C6B6B]">
                Facilitators are a special partner class. After approval you'll choose a <Link to="/partner/subscribe?type=facilitator" className="text-[#476B6B] underline">subscription plan</Link> (monthly / annual / 2-year). Subscription length sets your license window AND default revenue share — shorter terms carry a higher rev-share. Rev-share also differs for birthright IP materials vs. your own / vendor content. <strong>Tell us which you plan to present.</strong>
              </p>
            </div>
            <div>
              <label className="label">Do you plan to present birthright IP materials and workshops?</label>
              <div className="flex gap-2 mt-2" data-testid="apply-presents-birthright-ip">
                {[{ v: true, label: "Yes — birthright materials" }, { v: false, label: "No — only my own / other materials" }].map((opt) => (
                  <button
                    type="button"
                    key={String(opt.v)}
                    onClick={() => update("presents_birthright_ip", opt.v)}
                    className={`btn-outline text-sm ${form.presents_birthright_ip === opt.v ? "ring-2 ring-[#C9A961]" : ""}`}
                    data-testid={`apply-presents-${opt.v}`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Credentials & licensure</label>
              <textarea className="input-field mt-1" value={form.credentials} onChange={(e) => update("credentials", e.target.value)} placeholder="LCSW, LMFT, attachment-focused certifications..." data-testid="apply-credentials" maxLength={2000} />
            </div>
            <div>
              <label className="label">Training history</label>
              <textarea className="input-field mt-1" value={form.training_history} onChange={(e) => update("training_history", e.target.value)} placeholder="Where you trained, with whom, hours of practice..." data-testid="apply-training" maxLength={4000} />
            </div>
            <div>
              <label className="label">Sample curriculum / syllabus URL</label>
              <input className="input-field mt-1" value={form.sample_curriculum_url} onChange={(e) => update("sample_curriculum_url", e.target.value)} placeholder="https://" data-testid="apply-curriculum" />
            </div>
          </fieldset>
        )}

        {form.partner_type === "community" && (
          <fieldset className="card p-4 space-y-3" data-testid="apply-community-fields">
            <legend className="label px-1">Community partner details</legend>
            <div>
              <label className="label">Organization (if any)</label>
              <input className="input-field mt-1" value={form.organization} onChange={(e) => update("organization", e.target.value)} data-testid="apply-organization" maxLength={200} />
            </div>
            <div>
              <label className="label">Audience size (approx)</label>
              <input type="number" min="0" className="input-field mt-1" value={form.audience_size} onChange={(e) => update("audience_size", e.target.value)} data-testid="apply-audience-size" />
            </div>
            <div>
              <label className="label">How do you plan to refer / amplify?</label>
              <textarea className="input-field mt-1" value={form.referral_plan} onChange={(e) => update("referral_plan", e.target.value)} data-testid="apply-referral-plan" maxLength={2000} />
            </div>
          </fieldset>
        )}

        {form.partner_type === "research" && (
          <fieldset className="card p-4 space-y-3" data-testid="apply-research-fields">
            <legend className="label px-1">Research partner details</legend>
            <div>
              <label className="label">Institution / affiliation</label>
              <input className="input-field mt-1" value={form.institution} onChange={(e) => update("institution", e.target.value)} data-testid="apply-institution" maxLength={200} />
            </div>
            <div>
              <label className="label">Area of research</label>
              <input className="input-field mt-1" value={form.area_of_research} onChange={(e) => update("area_of_research", e.target.value)} placeholder="e.g. infant-caregiver attachment, repair after rupture..." data-testid="apply-area-of-research" maxLength={500} />
            </div>
            <div>
              <label className="label">Sample publications / portfolio URL</label>
              <input className="input-field mt-1" value={form.sample_publications_url} onChange={(e) => update("sample_publications_url", e.target.value)} placeholder="https://" data-testid="apply-publications" />
            </div>
          </fieldset>
        )}

        {form.partner_type === "vendor" && (
          <fieldset className="card p-4 space-y-3" data-testid="apply-vendor-fields">
            <legend className="label px-1">Vendor partner details</legend>
            <div>
              <label className="label">Business name</label>
              <input className="input-field mt-1" value={form.business_name} onChange={(e) => update("business_name", e.target.value)} data-testid="apply-business-name" maxLength={200} />
            </div>
            <div>
              <label className="label">Product categories</label>
              <input className="input-field mt-1" value={form.product_categories} onChange={(e) => update("product_categories", e.target.value)} placeholder="e.g. journals, audio courses, somatic tools..." data-testid="apply-categories" maxLength={500} />
            </div>
          </fieldset>
        )}

        {form.partner_type === "artist" && (
          <fieldset className="card p-4 space-y-3" data-testid="apply-artist-fields">
            <legend className="label px-1">Artist details</legend>
            <div>
              <label className="label">Mediums (comma-separated)</label>
              <input className="input-field mt-1" value={form.mediums || ""} onChange={(e) => update("mediums", e.target.value)} placeholder="e.g. oil painting, chamber music, ceramics, photography" data-testid="apply-mediums" maxLength={500} />
            </div>
            <div>
              <label className="label">Your own gallery / website URL</label>
              <input className="input-field mt-1" value={form.own_gallery_url || ""} onChange={(e) => update("own_gallery_url", e.target.value)} placeholder="https://yourname.com" data-testid="apply-own-gallery" />
              <p className="text-[10px] text-[#5C6B6B] mt-1">Required so we can verify list prices match across sites.</p>
            </div>
            <div>
              <label className="label">Representative works (link to portfolio, Instagram, SoundCloud…)</label>
              <input className="input-field mt-1" value={form.representative_works_url || ""} onChange={(e) => update("representative_works_url", e.target.value)} data-testid="apply-rep-works" />
            </div>
            <div>
              <label className="label">Artist statement (optional, can edit later)</label>
              <textarea className="input-field mt-1" rows={3} value={form.artist_statement || ""} onChange={(e) => update("artist_statement", e.target.value)} maxLength={4000} data-testid="apply-artist-statement" />
            </div>
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!form.accepts_commissions} onChange={(e) => update("accepts_commissions", e.target.checked)} data-testid="apply-accepts-commissions" />
              I accept commission inquiries
            </label>
            <p className="text-[10px] text-[#5C6B6B] italic">birthright lists your work at YOUR list price and adds a 20% gift to the foundation at checkout. The buyer sees the math; you keep your full price.</p>
          </fieldset>
        )}

        {form.partner_type === "steward" && (
          <fieldset className="card p-4 space-y-3" data-testid="apply-steward-fields">
            <legend className="label px-1">Steward details</legend>
            <div>
              <label className="label">Community you'd steward (slug path)</label>
              <input className="input-field mt-1" value={form.requested_community_slug || ""} onChange={(e) => update("requested_community_slug", e.target.value)} placeholder="north-america/us/california/santa-cruz" data-testid="apply-community-slug" maxLength={200} required />
              <p className="text-[10px] text-[#5C6B6B] mt-1">Visit <Link to="/gather" className="underline">Gather</Link> to find or propose your community first.</p>
            </div>
            <div>
              <label className="label">How are you rooted here?</label>
              <textarea className="input-field mt-1" rows={3} value={form.community_ties || ""} onChange={(e) => update("community_ties", e.target.value)} maxLength={4000} data-testid="apply-community-ties" />
            </div>
            <div>
              <label className="label">Moderation experience (optional)</label>
              <textarea className="input-field mt-1" rows={2} value={form.moderation_experience || ""} onChange={(e) => update("moderation_experience", e.target.value)} maxLength={2000} data-testid="apply-mod-experience" />
            </div>
            <p className="text-[10px] text-[#5C6B6B] italic">Steward is a service role — no revenue share. You'll be recognized as a steward of your local Gather space, with tools to welcome new neighbors, moderate, and pin local events.</p>
          </fieldset>
        )}

        <FoundingPartnerOptIn checked={form.apply_as_founding_partner} onChange={(v) => update("apply_as_founding_partner", v)} />

        <button type="submit" disabled={submitting} className="btn-primary" data-testid="apply-submit">
          {submitting ? "Submitting..." : "Submit application"}
        </button>
      </form>
    </div>
  );
}

function FoundingPartnerOptIn({ checked, onChange }) {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    api.get("/founding-partners/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);
  if (!stats) return null;
  const pct = stats.cap > 0 ? Math.min(100, Math.round((stats.taken / stats.cap) * 100)) : 0;
  return (
    <fieldset className="card p-5 bg-[#FFFBEF] border-l-4 border-[#C9A961]" data-testid="apply-founding-section">
      <legend className="label px-1 text-[#8B7128]">★ Founding Partner program</legend>
      <p className="text-sm text-[#1A2424] leading-relaxed">
        Founding Partners get a <strong>locked rev-share rate for 5 years</strong>, a visible badge across the directory, and a permanent seat in our origin story.
      </p>
      <div className="mt-3">
        <div className="flex justify-between text-xs text-[#5C6B6B]">
          <span data-testid="founding-counter">{stats.taken}/{stats.cap} seats taken</span>
          <span>{stats.available} remaining</span>
        </div>
        <div className="h-2 bg-[#E5E1D8] rounded-full mt-1 overflow-hidden">
          <div className="h-full bg-[#C9A961]" style={{ width: `${pct}%` }} />
        </div>
      </div>
      {stats.is_open ? (
        <label className="flex items-start gap-2 mt-4 cursor-pointer">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            className="mt-1"
            data-testid="apply-founding-checkbox"
          />
          <span className="text-sm text-[#1A2424]">
            <strong>I'd like to be considered for Founding Partner status.</strong> If accepted alongside my application, my locked rate runs for 5 years from approval.
          </span>
        </label>
      ) : (
        <p className="text-sm text-[#9E3C3C] mt-4" data-testid="apply-founding-full">
          All Founding Partner seats are currently filled. You can still apply as a standard partner.
        </p>
      )}
    </fieldset>
  );
}
