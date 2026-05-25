import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Sparkles, ArrowRight, ExternalLink as LinkIcon } from "lucide-react";

export default function Featured() {
  const [partners, setPartners] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/featured")
      .then((r) => setPartners(r.data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="container-page py-12" data-testid="featured-page">
      <span className="label">Featured this month</span>
      <h1 className="editorial-h1 mt-2">In the spotlight</h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Partners who have purchased a featured slot to share signature content with our community.
        Each window runs 30 days. Want to feature yourself?{" "}
        <Link to="/dashboard/partner/featured" className="text-[#476B6B] underline">Buy a slot from your partner dashboard</Link>.
      </p>

      {loading && <p className="text-sm text-[#5C6B6B] mt-8">Loading featured partners...</p>}

      {!loading && partners.length === 0 && (
        <div className="card p-12 text-center mt-10" data-testid="featured-empty">
          <Sparkles size={36} strokeWidth={1.2} className="text-[#C9A961] mx-auto" />
          <p className="font-serif text-2xl mt-4">No featured partners right now.</p>
          <p className="text-sm text-[#5C6B6B] mt-2">Check back soon — the spotlight rotates with each new month.</p>
          <Link to="/partners" className="btn-outline mt-6 inline-block" data-testid="back-to-partners">Browse all partners →</Link>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10" data-testid="featured-cards">
        {partners.map((p) => <FeaturedCard key={p.id} profile={p} />)}
      </div>
    </div>
  );
}

function FeaturedCard({ profile }) {
  const cta = profile.featured_custom_cta || "Visit partner →";
  const ctaUrl = profile.featured_custom_cta_url || (profile.external_site_url
    ? `${process.env.REACT_APP_BACKEND_URL || ""}/api/out/${profile.slug}`
    : `/partners/${profile.slug}`);
  const apiBase = process.env.REACT_APP_BACKEND_URL || "";
  const outboundHref = profile.external_site_url ? `${apiBase}/api/out/${profile.slug}` : null;

  return (
    <article className="card p-6 relative overflow-hidden" data-testid={`featured-card-${profile.slug}`}>
      <span className="absolute top-4 right-4 inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-semibold bg-[#C9A961] text-[#1A2424]" data-testid="featured-ribbon">
        <Sparkles size={10} strokeWidth={2} /> Featured
      </span>

      <div className="flex items-center gap-3 pr-20">
        {profile.photo_url ? (
          <img src={profile.photo_url} alt="" className="w-14 h-14 rounded-full object-cover" />
        ) : (
          <div className="w-14 h-14 rounded-full bg-[#F4F1EA]" />
        )}
        <div className="flex-1 min-w-0">
          <Link to={`/partners/${profile.slug}`} className="font-serif text-xl hover:underline" data-testid={`featured-name-${profile.slug}`}>
            {profile.display_name}
          </Link>
          <p className="text-[10px] uppercase tracking-wider text-[#476B6B] mt-0.5">{profile.partner_type} partner</p>
          {profile.is_founding_partner && (
            <p className="text-[10px] uppercase tracking-wider text-[#8B7128] mt-0.5">★ Founding Partner</p>
          )}
        </div>
      </div>

      {profile.featured_mission_alignment && (
        <div className="mt-5 p-4 bg-[#FFFBEF] rounded border-l-4 border-[#C9A961]">
          <p className="label text-[#8B7128]">Mission alignment</p>
          <p className="text-sm text-[#1A2424] mt-1 leading-relaxed">{profile.featured_mission_alignment}</p>
        </div>
      )}

      {profile.featured_signature_content && (
        <p className="text-sm text-[#1A2424] mt-4 leading-relaxed whitespace-pre-wrap line-clamp-6">
          {profile.featured_signature_content}
        </p>
      )}

      {profile.featured_video_url && (
        <a href={profile.featured_video_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-sm text-[#476B6B] mt-3 hover:underline" data-testid={`featured-video-${profile.slug}`}>
          <LinkIcon size={12} strokeWidth={1.5} /> Watch their video
        </a>
      )}

      {Array.isArray(profile.featured_image_urls) && profile.featured_image_urls.length > 0 && (
        <div className="grid grid-cols-3 gap-2 mt-4" data-testid={`featured-gallery-${profile.slug}`}>
          {profile.featured_image_urls.slice(0, 3).map((url, i) => (
            <img key={i} src={url} alt="" className="w-full h-20 object-cover rounded" />
          ))}
        </div>
      )}

      <div className="flex items-center justify-between mt-5 pt-4 border-t border-[#E5E1D8]">
        <Link to={`/partners/${profile.slug}`} className="text-xs text-[#5C6B6B] hover:underline">Full profile</Link>
        {outboundHref || profile.featured_custom_cta_url ? (
          <a
            href={ctaUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="btn-primary text-sm inline-flex items-center gap-1"
            data-testid={`featured-cta-${profile.slug}`}
          >
            {cta} <ArrowRight size={12} strokeWidth={1.5} />
          </a>
        ) : (
          <Link to={`/partners/${profile.slug}`} className="btn-primary text-sm inline-flex items-center gap-1">
            Learn more <ArrowRight size={12} strokeWidth={1.5} />
          </Link>
        )}
      </div>
    </article>
  );
}
