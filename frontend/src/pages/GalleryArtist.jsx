import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Palette, ShoppingBag, ExternalLink, Mail, Mic, Video, Calendar } from "lucide-react";
import api from "../lib/api";
import { useCart } from "../contexts/CartContext";

const ACCENT_RING = {
  flame: "ring-[#9E3C3C]/40",
  moss: "ring-[#476B6B]/40",
  river: "ring-[#5B8DA8]/40",
  ochre: "ring-[#C9A961]/40",
  indigo: "ring-[#3F4A8C]/40",
  graphite: "ring-[#5C6B6B]/40",
};

export default function GalleryArtist() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const cart = useCart();
  const [inquiry, setInquiry] = useState({ name: "", email: "", message: "" });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get(`/gallery/${slug}`).then((r) => setData(r.data))
      .catch((e) => toast.error(e?.response?.data?.detail || "Couldn't load"))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading || !data) return <div className="container-page py-12">Loading…</div>;
  const { artist, space, works, collections, markup_pct } = data;
  const accent = ACCENT_RING[space?.accent_color] || ACCENT_RING.flame;

  const buy = (work) => {
    cart.addItem({
      product_id: work.id,
      name: work.name,
      price: work.price,
      quantity: 1,
      image_url: work.image_url,
      fulfillable_via: "gallery",
      gallery_artist_name: artist.display_name,
      foundation_markup_per_unit: work.foundation_absorbs_markup ? 0 : Math.round(work.price * 0.2 * 100) / 100,
    });
    toast.success(`Added "${work.name}" to cart · ${markup_pct}% supports the foundation`);
  };

  const submitInquiry = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/gallery/inquiries", { artist_slug: slug, ...inquiry });
      toast.success("Inquiry sent to the artist");
      setInquiry({ name: "", email: "", message: "" });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Inquiry failed");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="container-page py-12" data-testid="gallery-artist-page">
      <Link to="/gallery" className="text-xs text-[#476B6B] hover:underline">← back to gallery</Link>
      <h1 className="editorial-h1 mt-2 inline-flex items-center gap-3">
        <Palette size={24} strokeWidth={1.2} /> {artist.display_name}
      </h1>
      <p className="text-sm text-[#476B6B] mt-1">{artist.location || ""}</p>
      <div className="divider-flame" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <div className="lg:col-span-1 space-y-4">
          {space?.hero_image_url && (
            <img src={space.hero_image_url} alt={`${artist.display_name} hero`} className={`w-full rounded-xl ring-2 ${accent}`} data-testid="gallery-hero" />
          )}
          <p className="text-base leading-relaxed font-serif text-[#0F2424]" data-testid="gallery-statement">
            {space?.statement || artist.bio}
          </p>
          {space?.studio_photo_url && (
            <img src={space.studio_photo_url} alt="In the studio" className="w-full rounded-lg" data-testid="gallery-studio-photo" />
          )}
          {space?.audio_intro_url && (
            <audio controls className="w-full" data-testid="gallery-audio">
              <source src={space.audio_intro_url} />
            </audio>
          )}
          {space?.video_reel_url && (
            <a href={space.video_reel_url} target="_blank" rel="noreferrer noopener" className="btn-outline text-xs inline-flex items-center gap-1" data-testid="gallery-video-link">
              <Video size={12} /> Watch performance reel
            </a>
          )}
          {space?.open_studio_text && (
            <div className="card p-3 bg-[#FAF8F5]" data-testid="gallery-open-studio">
              <p className="text-xs uppercase tracking-wider text-[#476B6B]">Open studio</p>
              <p className="text-sm mt-1 whitespace-pre-wrap">{space.open_studio_text}</p>
            </div>
          )}
          {space?.performance_schedule && (
            <div className="card p-3 bg-[#F4F1EA]" data-testid="gallery-perf-schedule">
              <p className="text-xs uppercase tracking-wider text-[#476B6B] inline-flex items-center gap-1"><Calendar size={11} />Performances</p>
              <p className="text-sm mt-1 whitespace-pre-wrap">{space.performance_schedule}</p>
            </div>
          )}
          {space?.own_gallery_url && (
            <a href={space.own_gallery_url} target="_blank" rel="noreferrer noopener" className="text-xs text-[#476B6B] hover:underline inline-flex items-center gap-1" data-testid="gallery-own-link">
              <ExternalLink size={11} /> Visit artist's own gallery
            </a>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="rounded-lg border-2 border-dashed border-[#C9A961] bg-[#FFF8E1] p-3 mb-4 text-xs text-[#8B7128]" data-testid="gallery-markup-disclosure">
            Every purchase here pays {artist.display_name} their full list price.
            A <strong>{markup_pct}%</strong> gift is added at checkout to support the foundation.
            <span className="block mt-1">
              <span className="italic">Thank you for generously supporting both the artist and the foundation.</span>
            </span>
          </div>

          {collections && collections.length > 0 && (
            <div className="mb-4 text-xs" data-testid="gallery-collections">
              <span className="uppercase tracking-wider text-[#5C6B6B]">Collections:</span>
              {collections.map((c) => (
                <span key={c.slug} className="ml-2 inline-block px-2 py-0.5 rounded-full bg-[#F4F1EA]" data-testid={`gallery-collection-${c.slug}`}>{c.label}</span>
              ))}
            </div>
          )}

          {works.length === 0 ? (
            <p className="text-sm text-[#5C6B6B] italic" data-testid="gallery-no-works">
              {artist.display_name} hasn't published any works here yet. Check back soon — or use the
              commission form below if it's open.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="gallery-works-grid">
              {works.map((w) => {
                const markup = w.foundation_absorbs_markup ? 0 : Math.round(w.price * 0.2 * 100) / 100;
                const total = w.price + markup;
                return (
                  <div key={w.id} className="card overflow-hidden" data-testid={`gallery-work-${w.id}`}>
                    <div className="aspect-square bg-[#F4F1EA] overflow-hidden">
                      <img src={w.image_url} alt={w.name} className="w-full h-full object-contain" />
                    </div>
                    <div className="p-3">
                      <p className="font-serif text-base leading-tight">{w.name}</p>
                      <p className="text-[10px] uppercase tracking-wider text-[#5C6B6B] mt-1">
                        {[w.medium, w.dimensions, w.year, w.edition].filter(Boolean).join(" · ")}
                      </p>
                      <div className="text-xs mt-2">
                        <p>Artist: <strong>${w.price.toFixed(2)}</strong></p>
                        {markup > 0 && <p className="text-[#8B7128]">Foundation gift: ${markup.toFixed(2)}</p>}
                        <p className="font-medium mt-0.5">Total: ${total.toFixed(2)}</p>
                      </div>
                      {w.availability === "available" ? (
                        <button onClick={() => buy(w)} className="btn-primary text-xs w-full mt-2 inline-flex items-center justify-center gap-1" data-testid={`gallery-buy-${w.id}`}>
                          <ShoppingBag size={12} /> Add to cart
                        </button>
                      ) : (
                        <p className="text-xs text-[#5C6B6B] mt-2 italic capitalize text-center">{w.availability.replace("_", " ")}</p>
                      )}
                      {w.living_with_text && (
                        <details className="mt-2 text-xs text-[#5C6B6B]">
                          <summary className="cursor-pointer">Living with this piece</summary>
                          <p className="mt-1 whitespace-pre-wrap leading-relaxed">{w.living_with_text}</p>
                        </details>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {space?.commissions_open && (
            <div className="card p-4 mt-6 bg-[#FAF8F5]" data-testid="gallery-commission-form">
              <h2 className="font-serif text-xl inline-flex items-center gap-2"><Mail size={16} /> Commission inquiry</h2>
              {space.commission_inquiry_text && (
                <p className="text-sm text-[#5C6B6B] mt-2 whitespace-pre-wrap">{space.commission_inquiry_text}</p>
              )}
              <form onSubmit={submitInquiry} className="mt-3 space-y-2 max-w-md">
                <input value={inquiry.name} onChange={(e) => setInquiry({ ...inquiry, name: e.target.value })} placeholder="Your name" className="input-field text-sm" required data-testid="gallery-inquiry-name" />
                <input value={inquiry.email} onChange={(e) => setInquiry({ ...inquiry, email: e.target.value })} placeholder="Your email" type="email" className="input-field text-sm" required data-testid="gallery-inquiry-email" />
                <textarea value={inquiry.message} onChange={(e) => setInquiry({ ...inquiry, message: e.target.value })} placeholder="What do you have in mind?" className="input-field text-sm" rows={4} required data-testid="gallery-inquiry-message" />
                <button disabled={submitting} className="btn-primary text-sm" data-testid="gallery-inquiry-submit">{submitting ? "Sending…" : "Send inquiry"}</button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
