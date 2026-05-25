import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { Globe, MapPin, ArrowLeft, Sparkles } from "lucide-react";
import ShareButton from "../components/ShareButton";
import MessageButton from "../components/MessageButton";

const TYPE_LABEL = {
  facilitator: "Facilitator",
  community:   "Community partner",
  research:    "Research partner",
  vendor:      "Vendor partner",
};

export default function PartnerProfilePage() {
  const { slug } = useParams();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get(`/partners/${slug}`)
      .then((r) => setProfile(r.data))
      .catch((err) => setError(err.response?.status === 404 ? "not-found" : "error"));
  }, [slug]);

  if (error === "not-found") {
    return (
      <div className="container-page py-16 text-center" data-testid="partner-not-found">
        <p className="font-serif text-2xl">Partner not found.</p>
        <Link to="/partners" className="btn-outline mt-6 inline-block">Back to directory</Link>
      </div>
    );
  }
  if (!profile) return <div className="container-page py-16 text-sm text-[#5C6B6B]">Loading...</div>;

  return (
    <div className="container-page py-12 max-w-3xl" data-testid="partner-profile-page">
      <Link to="/partners" className="inline-flex items-center gap-1 text-xs text-[#476B6B] hover:underline">
        <ArrowLeft size={12} strokeWidth={1.5} /> Back to directory
      </Link>
      {profile.is_sample && (
        <div className="mt-4 card p-4 bg-[#FFFBEF] border-l-4 border-[#C9A961]" data-testid="sample-banner">
          <p className="text-xs uppercase tracking-wider text-[#8B7128] font-semibold inline-flex items-center gap-1">
            <Sparkles size={12} strokeWidth={2} /> Sample profile
          </p>
          <p className="text-sm text-[#1A2424] mt-1">
            This is an illustrative persona showing what a great Birthright partner profile looks like. Not a real, active partner.{" "}
            <Link to="/partners/apply" className="underline text-[#476B6B]">Apply to become a partner</Link>.
          </p>
        </div>
      )}
      <div className="flex items-start gap-4 mt-4">
        {profile.photo_url ? (
          <img src={profile.photo_url} alt="" className="w-20 h-20 rounded-full object-cover" />
        ) : (
          <div className="w-20 h-20 rounded-full bg-[#FAF8F5] border border-[#E5E1D8]" />
        )}
        <div className="flex-1 min-w-0">
          <span className="label">{TYPE_LABEL[profile.partner_type] || "Partner"}</span>
          <h1 className="editorial-h1 mt-1">{profile.display_name}</h1>
          <div className="flex flex-wrap gap-2 mt-2">
            {profile.featured_until && new Date(profile.featured_until) > new Date() && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold bg-[#C9A961] text-[#1A2424]" data-testid="featured-badge">
                <Sparkles size={10} strokeWidth={2} /> Featured partner
              </span>
            )}
            {profile.is_founding_partner && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-semibold bg-[#2E5C46] text-white" data-testid="founding-badge">
                ★ Founding Partner
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="divider-flame" />
      <p className="font-serif text-xl">{profile.headline}</p>

      <div className="flex flex-wrap gap-4 mt-4 text-xs text-[#5C6B6B] items-center">
        {profile.location && <span className="inline-flex items-center gap-1"><MapPin size={11} strokeWidth={1.5} /> {profile.location}</span>}
        {profile.website_url && (
          <ExternalLink profile={profile} testid="partner-website-link" />
        )}
        {!profile.is_sample && (
          <div className="ml-auto flex items-center gap-2">
            <MessageButton recipientId={profile.user_id} recipientName={profile.display_name} size="sm" />
            <ShareButton
              surface="partner"
              surfaceId={profile.slug}
              path={`/partners/${profile.slug}`}
              title={profile.display_name}
              emailSubject={`Birthright partner: ${profile.display_name}`}
              size="sm"
            />
          </div>
        )}
      </div>

      <article className="prose prose-sm max-w-none mt-6 whitespace-pre-wrap font-sans text-sm" data-testid="partner-bio">
        {profile.bio}
      </article>
    </div>
  );
}

const OUTBOUND_TYPES = new Set(["vendor", "community"]);

function ExternalLink({ profile, testid }) {
  // Vendors + community partners route through /api/out/{slug} for attribution.
  // Other types use a plain external link.
  const useOutbound = OUTBOUND_TYPES.has(profile.partner_type);
  if (useOutbound) {
    const apiBase = process.env.REACT_APP_BACKEND_URL || "";
    const href = `${apiBase}/api/out/${profile.slug}`;
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer noopener"
        className="inline-flex items-center gap-1 text-[#476B6B] hover:underline"
        data-testid={testid}
      >
        <Globe size={11} strokeWidth={1.5} /> Visit external site
      </a>
    );
  }
  return (
    <a
      href={profile.website_url}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 text-[#476B6B] hover:underline"
      data-testid={testid}
    >
      <Globe size={11} strokeWidth={1.5} /> Website
    </a>
  );
}
