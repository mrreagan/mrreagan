/* eslint-disable */
import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "../lib/api";
import { Users, Briefcase, Microscope, Store, Search, Sparkles, Palette, Compass } from "lucide-react";
import ShareButton from "../components/ShareButton";
import MessageButton from "../components/MessageButton";
import StudioVendorNudge from "../components/StudioVendorNudge";

const TYPE_CONFIG = {
  facilitator: { label: "Facilitators", singular: "Facilitator", icon: Users,      color: "#476B6B", description: "Practitioners trained to lead birthright workshops." },
  community:   { label: "Community",    singular: "Community",   icon: Briefcase,  color: "#C9A961", description: "Organizations and individuals who refer participants and amplify the work." },
  research:    { label: "Research",     singular: "Research",    icon: Microscope, color: "#2E5C46", description: "Academic and clinical partners advancing attachment science." },
  vendor:      { label: "Vendors",      singular: "Vendor",      icon: Store,      color: "#B86A5C", description: "Aligned vendors of complementary materials and services." },
  artist:      { label: "Artists",      singular: "Artist",      icon: Palette,    color: "#8B5E3C", description: "Featured artists whose work threads attachment, repair, and presence into the world." },
  steward:     { label: "Stewards",     singular: "Steward",     icon: Compass,    color: "#5C6B6B", description: "Community elders and mentors who hold long-term presence for others." },
};

export default function PartnersDirectory() {
  const [searchParams, setSearchParams] = useSearchParams();
  const samplesMode = searchParams.get("samples") === "1";

  // Initialize filters from URL so the AI Concierge (and any deep link) can
  // land users directly on a filtered view, e.g. /partners?partner_type=vendor.
  const validTypes = ["all", "facilitator", "vendor", "community", "research", "artist", "steward"];
  const initialType = (() => {
    const t = searchParams.get("partner_type");
    return validTypes.includes(t) ? t : "all";
  })();
  const [partnerType, setPartnerType] = useState(initialType);
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [partners, setPartners] = useState([]);
  const [loading, setLoading] = useState(true);

  // Keep URL in sync when filters change (so refresh / share preserves view).
  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (partnerType !== "all") next.set("partner_type", partnerType);
    else next.delete("partner_type");
    if (q.trim().length >= 2) next.set("q", q.trim());
    else next.delete("q");
    // Avoid replacing the URL on the very first render if nothing changed.
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [partnerType, q]);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (partnerType !== "all") params.set("partner_type", partnerType);
    if (q.trim().length >= 2) params.set("q", q.trim());
    if (samplesMode) params.set("samples", "1");
    api.get(`/partners?${params}`)
      .then((r) => setPartners(r.data))
      .finally(() => setLoading(false));
  }, [partnerType, q, samplesMode]);

  const counts = useMemo(() => {
    const c = { all: partners.length };
    for (const p of partners) c[p.partner_type] = (c[p.partner_type] || 0) + 1;
    return c;
  }, [partners]);

  const toggleSamples = () => {
    if (samplesMode) {
      const p = new URLSearchParams(searchParams);
      p.delete("samples");
      setSearchParams(p);
    } else {
      setSearchParams({ samples: "1" });
    }
  };

  return (
    <div className="container-page py-12" data-testid="partners-directory">
      <span className="label">Partner network</span>
      <h1 className="editorial-h1 mt-2">Partners</h1>
      <div className="divider-flame" />
      <p className="text-sm text-[#5C6B6B] max-w-2xl">
        The people and organizations who carry birthright&apos;s work into communities, classrooms, and clinics. Want to join us?{" "}
        <Link to="/partner/apply" className="text-[#476B6B] underline" data-testid="apply-cta">Apply to partner</Link>.
      </p>

      {/* Prominent navigation to the partner plans comparison + the artist
          tier breakdown. Both pages already existed but were unreachable
          from this directory view, leading users to think they had been
          removed. */}
      <div
        className="mt-6 card p-5 bg-gradient-to-br from-[#FAF8F5] to-[#F4F1EA] border border-[#C9A961]/30"
        data-testid="partner-compare-banner"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="max-w-xl">
            <p className="label !mt-0 text-[#A87A4A]">See the cost before you spend it.</p>
            <h2 className="font-serif text-xl mt-1 leading-tight">
              Compare all six partner types side-by-side.
            </h2>
            <p className="text-sm text-[#5C6B6B] mt-1">
              One pager with revenue share, what you do, what the foundation
              gets, and how each role lines up with mission.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 shrink-0">
            <Link
              to="/partner/types"
              className="btn-primary text-sm whitespace-nowrap"
              data-testid="partners-compare-link"
            >
              Compare partner plans →
            </Link>
            <Link
              to="/partner/artist"
              className="btn-outline text-sm whitespace-nowrap"
              data-testid="partners-artist-tiers-link"
            >
              Artist tier breakdown →
            </Link>
          </div>
        </div>
      </div>

      {samplesMode && (
        <div className="mt-6 card p-5 bg-[#FFFBEF] border-l-4 border-[#C9A961]" data-testid="samples-banner">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="label text-[#8B7128] inline-flex items-center gap-1">
                <Sparkles size={12} strokeWidth={1.5} /> Sample profiles
              </p>
              <p className="text-sm text-[#1A2424] mt-1">
                These are illustrative partner personas to show prospective partners what a great birthright profile looks like. None are real, active partners yet.
              </p>
            </div>
            <button onClick={toggleSamples} className="btn-outline text-sm" data-testid="exit-samples">
              View real partners →
            </button>
          </div>
        </div>
      )}

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
        {!samplesMode && (
          <button
            onClick={toggleSamples}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] uppercase tracking-wider font-medium border border-[#C9A961] text-[#8B7128] hover:bg-[#FFFBEF] transition ml-1"
            data-testid="show-samples"
          >
            <Sparkles size={11} strokeWidth={1.5} /> View sample profiles
          </button>
        )}
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
        <div className="mt-4 flex flex-wrap items-baseline gap-3">
          <p className="text-sm text-[#5C6B6B] italic flex-1 min-w-[260px]">
            {TYPE_CONFIG[partnerType].description}
          </p>
          {partnerType === "artist" && (
            <Link
              to="/partner/artist"
              className="text-xs uppercase tracking-wider text-[#A87A4A] hover:text-[#1A2424] underline"
              data-testid="partners-artist-deeplink"
            >
              See artist tier rates →
            </Link>
          )}
          <Link
            to={`/partner/types#${partnerType}`}
            className="text-xs uppercase tracking-wider text-[#476B6B] hover:text-[#1A2424] underline"
            data-testid={`partners-type-detail-${partnerType}`}
          >
            See revenue share for {TYPE_CONFIG[partnerType].singular.toLowerCase()} →
          </Link>
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="partner-cards">
        {loading ? (
          <p className="text-sm text-[#5C6B6B] col-span-full">Loading partners...</p>
        ) : partners.length === 0 ? (
          <div className="col-span-full card p-10 text-center">
            <p className="font-serif text-lg">No partners match this filter yet.</p>
            <p className="text-xs text-[#5C6B6B] mt-2">Help us build the network — <Link to="/partner/apply" className="underline text-[#476B6B]">apply</Link>.</p>
          </div>
        ) : (
          partners.map((p) => <PartnerCard key={p.id} profile={p} sampleMode={samplesMode} />)
        )}
      </div>

      <StudioVendorNudge variant="footer" className="mt-16 -mx-4 sm:mx-0 sm:rounded-3xl" />
    </div>
  );
}

function PartnerCard({ profile, sampleMode }) {
  const navigate = useNavigate();
  const cfg = TYPE_CONFIG[profile.partner_type] || TYPE_CONFIG.community;
  const Icon = cfg.icon;
  const isSample = profile.is_sample;
  const isFeatured = profile.featured_until && new Date(profile.featured_until) > new Date();
  const isFounding = profile.is_founding_partner;
  const goToProfile = () => navigate(`/partner/${profile.slug}`);
  return (
    <div
      role="link"
      tabIndex={0}
      onClick={goToProfile}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") goToProfile(); }}
      className={`card p-5 hover:border-[#476B6B] transition block relative cursor-pointer ${isSample ? "ring-1 ring-[#C9A961]/40" : ""} ${isFeatured ? "ring-2 ring-[#C9A961]" : ""}`}
      data-testid={`partner-card-${profile.slug}`}
    >
      <div className="absolute top-3 right-3 flex flex-col gap-1 items-end">
        {isFeatured && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] uppercase tracking-wider font-semibold bg-[#C9A961] text-[#1A2424]" data-testid={`featured-ribbon-${profile.slug}`}>
            <Sparkles size={9} strokeWidth={2} /> Featured
          </span>
        )}
        {isSample && (
          <span
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] uppercase tracking-wider font-bold bg-[#9E3C3C] text-white shadow-sm"
            title="This is a sample profile illustrating the partner persona — not a real partner."
            data-testid={`sample-ribbon-${profile.slug}`}
          >
            <Sparkles size={9} strokeWidth={2} /> Sample profile
          </span>
        )}
        {isFounding && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] uppercase tracking-wider font-semibold bg-[#2E5C46] text-white" data-testid={`founding-ribbon-${profile.slug}`}>
            ★ Founding
          </span>
        )}
      </div>
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
      {(profile.partner_type === "vendor" || profile.partner_type === "community") && profile.website_url && (
        <a
          href={`${process.env.REACT_APP_BACKEND_URL || ""}/api/out/${profile.slug}`}
          target="_blank"
          rel="noreferrer noopener"
          onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider mt-3 text-[#476B6B] hover:underline"
          data-testid={`outbound-link-${profile.slug}`}
        >
          Visit external site →
        </a>
      )}
      {!isSample && (
        <div className="mt-3 flex items-center justify-end gap-2">
          {profile.user_id && (
            <MessageButton
              recipientId={profile.user_id}
              recipientName={profile.display_name}
              size="sm"
              showLabel={false}
              stopPropagation
            />
          )}
          <ShareButton
            surface="partner"
            surfaceId={profile.slug}
            path={`/partner/${profile.slug}`}
            title={profile.display_name}
            emailSubject={`Birthright partner: ${profile.display_name}`}
            size="sm"
            stopPropagation
          />
        </div>
      )}
    </div>
  );
}
