import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Palette, Search } from "lucide-react";
import FeaturedArtistsRibbon from "../components/gallery/FeaturedArtistsRibbon";

export default function GalleryLanding() {
  const [artists, setArtists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [featured, setFeatured] = useState({ slots: [], period_label: null });

  useEffect(() => {
    api.get("/gallery/artists").then((r) => setArtists(r.data || [])).finally(() => setLoading(false));
    api.get("/gallery/featured/pipeline").then((r) => {
      const cm = r.data?.current_month || {};
      setFeatured({ slots: cm.slots || [], period_label: cm.period_label });
    }).catch(() => {});
  }, []);

  const filtered = q.trim().length < 2 ? artists : artists.filter((a) =>
    (a.display_name + " " + a.headline + " " + a.bio + " " + a.location).toLowerCase().includes(q.trim().toLowerCase()),
  );

  return (
    <div className="container-page py-12" data-testid="gallery-landing">
      <span className="label">Gallery</span>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Palette size={26} strokeWidth={1.2} /> Artists in the room
      </h1>
      <div className="divider-flame" />
      <p className="text-base text-[#5C6B6B] max-w-2xl">
        Painters, photographers, sculptors, ceramicists, chamber musicians — friends whose practice
        is presence. Every purchase here pays the artist their full list price and adds a 20% gift
        to the foundation. The math is shown at checkout, with a thank-you to everyone who supports
        both.
      </p>

      <div className="mt-6 max-w-xl">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5C6B6B]" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search artists…" className="input-field pl-9" data-testid="gallery-search-input" />
        </div>
      </div>

      <FeaturedArtistsRibbon slots={featured.slots} periodLabel={featured.period_label} />

      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-8">Loading…</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-[#5C6B6B] italic mt-8" data-testid="gallery-empty">
          No artists in the room yet. Are you one? <Link to="/partner/apply" className="underline">Apply as an Artist partner</Link>.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6" data-testid="gallery-artists-grid">
          {filtered.map((a) => (
            <Link key={a.slug} to={`/gallery/${a.slug}`} className="card overflow-hidden hover:shadow-md transition flex flex-col" data-testid={`gallery-artist-${a.slug}`}>
              <div className="aspect-[4/3] bg-[#F4F1EA] flex items-center justify-center overflow-hidden">
                {a.hero_image_url ? (
                  <img src={a.hero_image_url} alt={a.display_name} className="w-full h-full object-cover" />
                ) : a.photo_url ? (
                  <img src={a.photo_url} alt={a.display_name} className="w-full h-full object-cover" />
                ) : (
                  <Palette size={36} strokeWidth={1} className="text-[#9E3C3C]" />
                )}
              </div>
              <div className="p-4 flex-1 flex flex-col">
                <p className="font-serif text-lg leading-tight">{a.display_name}</p>
                <p className="text-xs text-[#476B6B] mt-1">{a.location || ""}</p>
                <p className="text-sm text-[#5C6B6B] mt-2 line-clamp-3 leading-relaxed">{a.headline}</p>
                <p className="text-xs text-[#5C6B6B] mt-auto pt-3">
                  {a.available_count > 0 ? `${a.available_count} available` : "No works listed"}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
