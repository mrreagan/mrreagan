import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Users, Briefcase, Microscope, Store, Search } from "lucide-react";

const TYPE_CONFIG = {
  facilitator: { label: "Facilitators", singular: "Facilitator", icon: Users, color: "#476B6B", description: "Practitioners trained to lead Birthright workshops." },
  community:   { label: "Community",    singular: "Community",   icon: Briefcase, color: "#C9A961", description: "Organizations and individuals who refer participants and amplify the work." },
  research:    { label: "Research",     singular: "Research",    icon: Microscope, color: "#2E5C46", description: "Academic and clinical partners advancing attachment science." },
  vendor:      { label: "Vendors",      singular: "Vendor",      icon: Store, color: "#B86A5C", description: "Aligned vendors of complementary materials and services." },
};

export default function PartnersDirectory() {
  const [partnerType, setPartnerType] = useState("all");
  const [q, setQ] = useState("");
  const [partners, setPartners] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (partnerType !== "all") params.set("partner_type", partnerType);
    if (q.trim().length >= 2) params.set("q", q.trim());
    api.get(`/partners?${params}`)
      .then((r) => setPartners(r.data))
      .finally(() => setLoading(false));
  }, [partnerType, q]);

  const counts = useMemo(() => {
    const c = { all: partners.length };
    for (const p of partners) c[p.partner_type] = (c[p.partner_type] || 0) + 1;
    return c;
  }, [partners]);

  return (
    <div className="container-page py-12" data-testid="partners-directory">
      <span className="label">Partner network</span>
      <h1 className="editorial-h1 mt-2">Partners</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        The people and organizations who carry Birthright's work into communities, classrooms, and clinics. Want to join us?{" "}
        <Link to="/partners/apply" className="text-[#476B6B] underline" data-testid="apply-cta">Apply to partner</Link>.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-2" data-testid="partner-type-tabs">
        {["all", ...Object.keys(TYPE_CONFIG)].map((t) => {
          const cfg = TYPE_CONFIG[t];
          const Icon = cfg?.icon;
          const active = partnerType === t;
          return (
            <button
              key={t}
              onClick={() => setPartnerType(t)}
              className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border transition ${
                active ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
              }`}
              data-testid={`tab-${t}`}
            >
              {Icon && <Icon size={11} strokeWidth={1.5} />}
              {t === "all" ? "All" : cfg.label}
              {counts[t] != null && <span className="opacity-60">· {counts[t]}</span>}
            </button>
          );
        })}
        <div className="ml-auto relative">
          <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, location, focus..."
            className="input-field pl-9 text-sm w-72 max-w-full"
            data-testid="partner-search"
          />
        </div>
      </div>

      {partnerType !== "all" && TYPE_CONFIG[partnerType] && (
        <p className="text-sm text-[#5C6B6B] mt-4 italic">{TYPE_CONFIG[partnerType].description}</p>
      )}

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="partner-cards">
        {loading ? (
          <p className="text-sm text-[#5C6B6B] col-span-full">Loading partners...</p>
        ) : partners.length === 0 ? (
          <div className="col-span-full card p-10 text-center">
            <p className="font-serif text-lg">No partners match this filter yet.</p>
            <p className="text-xs text-[#5C6B6B] mt-2">Help us build the network — <Link to="/partners/apply" className="underline text-[#476B6B]">apply</Link>.</p>
          </div>
        ) : (
          partners.map((p) => <PartnerCard key={p.id} profile={p} />)
        )}
      </div>
    </div>
  );
}

function PartnerCard({ profile }) {
  const cfg = TYPE_CONFIG[profile.partner_type] || TYPE_CONFIG.community;
  const Icon = cfg.icon;
  return (
    <Link to={`/partners/${profile.slug}`} className="card p-5 hover:border-[#476B6B] transition block" data-testid={`partner-card-${profile.slug}`}>
      <div className="flex items-center gap-3">
        {profile.photo_url ? (
          <img src={profile.photo_url} alt="" className="w-12 h-12 rounded-full object-cover" />
        ) : (
          <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: `${cfg.color}20` }}>
            <Icon size={20} strokeWidth={1.5} style={{ color: cfg.color }} />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className="font-serif text-lg truncate">{profile.display_name}</p>
          <p className="text-[10px] uppercase tracking-wider" style={{ color: cfg.color }} data-testid={`partner-card-type-${profile.partner_type}`}>{cfg.singular}</p>
        </div>
      </div>
      <p className="font-medium text-sm mt-3 line-clamp-2">{profile.headline}</p>
      <p className="text-xs text-[#5C6B6B] mt-2 line-clamp-3">{profile.bio}</p>
      {profile.location && <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mt-3">📍 {profile.location}</p>}
    </Link>
  );
}
