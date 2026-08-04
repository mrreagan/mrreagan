import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { Globe, MapPin, ArrowLeft, Sparkles } from "lucide-react";
import ShareButton from "../components/ShareButton";
import MessageButton from "../components/MessageButton";
import FileDisputeModal from "../components/FileDisputeModal";
import PartnerOfferings from "../components/PartnerOfferings";

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
  const [disputeOpen, setDisputeOpen] = useState(false);

  useEffect(() => {
    api.get(`/partners/${slug}`)
      .then((r) => setProfile(r.data))
      .catch((err) => setError(err.response?.status === 404 ? "not-found" : "error"));
  }, [slug]);

  if (error === "not-found") {
    return (
      <div className="container-page py-16 text-center" data-testid="partner-not-found">
        <p className="font-serif text-2xl">Partner not found.</p>
        <Link to="/partner" className="btn-outline mt-6 inline-block">Back to directory</Link>
      </div>
    );
  }
  if (!profile) return <div className="container-page py-16 text-sm text-[#5C6B6B]">Loading...</div>;

  return (
    <div className="container-page py-12 max-w-3xl" data-testid="partner-profile-page">
      <Link to="/partner" className="inline-flex items-center gap-1 text-xs text-[#476B6B] hover:underline">
        <ArrowLeft size={12} strokeWidth={1.5} /> Back to directory
      </Link>
      {profile.is_sample && (
        <div className="mt-4 card p-4 bg-[#FFF1F1] border-l-4 border-[#9E3C3C]" data-testid="sample-banner">
          <p className="text-xs uppercase tracking-wider text-[#9E3C3C] font-bold inline-flex items-center gap-1">
            <Sparkles size={12} strokeWidth={2} /> Sample profile · not a real partner
          </p>
          <p className="text-sm text-[#1A2424] mt-1">
            This is an illustrative persona showing what a great birthright {profile.partner_type} partner profile looks like. The person below is fictional — but the role, structure, and partnership terms are real.{" "}
            <Link to="/partner/apply" className="underline text-[#476B6B]">Apply to become a real partner →</Link>
          </p>
        </div>
      )}
      <div className="flex items-start gap-4 mt-4">
        {profile.photo_url ? (
          <img src={profile.photo_url} alt={profile.image_caption || `${profile.display_name} · ${TYPE_LABEL[profile.partner_type] || "Partner"}`} className="w-20 h-20 rounded-full object-cover" />
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
              path={`/partner/${profile.slug}`}
              title={profile.display_name}
              emailSubject={`birthright partner: ${profile.display_name}`}
              size="sm"
            />
          </div>
        )}
      </div>

      <article className="prose prose-sm max-w-none mt-6 whitespace-pre-wrap font-sans text-sm" data-testid="partner-bio">
        {profile.bio}
      </article>

      <PartnerOfferings slug={profile.slug} partnerName={profile.display_name} />

      {!profile.is_sample && profile.user_id && (
        <div className="mt-8 pt-4 border-t border-[#E5E1D8]">
          <button
            onClick={() => setDisputeOpen(true)}
            className="text-[10px] uppercase tracking-wider text-[#5C6B6B] hover:text-[#9E3C3C] hover:underline"
            data-testid="open-dispute-from-profile"
          >
            Something wrong? File a dispute
          </button>
        </div>
      )}
      <FileDisputeModal
        open={disputeOpen}
        onClose={() => setDisputeOpen(false)}
        againstUserId={profile.user_id}
        againstUserName={profile.display_name}
      />
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
