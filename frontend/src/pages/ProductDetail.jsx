import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { useCart } from "../contexts/CartContext";
import { toast } from "sonner";
import { ShoppingBag, Lock, ArrowLeft, ExternalLink, Palette } from "lucide-react";
import ReviewSection, { AggregateRatingBadge } from "../components/ReviewSection";
import ShareButton from "../components/ShareButton";
import FulfillmentBadge, { isPurchasable } from "../components/FulfillmentBadge";

export default function ProductDetail() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [qty, setQty] = useState(1);
  const [activeIdx, setActiveIdx] = useState(0);
  const { addItem } = useCart();

  useEffect(() => {
    api.get(`/products/${id}`).then((r) => { setP(r.data); setActiveIdx(0); }).catch(() => {});
  }, [id]);

  // Combined gallery: hero image first, then any additional angles. We dedupe
  // empty strings so partially-filled admin entries don't create blank tiles.
  const gallery = useMemo(() => {
    if (!p) return [];
    const extras = Array.isArray(p.additional_images) ? p.additional_images : [];
    return [p.image_url, ...extras].filter((u) => typeof u === "string" && u.trim().length > 0);
  }, [p]);

  if (!p) return <div className="container-page py-20" data-testid="product-loading">Loading...</div>;

  const heroSrc = gallery[activeIdx] || p.image_url;
  const heroAlt = p.image_caption || p.name;

  return (
    <div className="container-page py-12" data-testid="product-detail-page">
      <Link to="/equip" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Back to Equip
      </Link>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div data-testid="product-image-wrap">
          <div className="card overflow-hidden aspect-square bg-[#F4F1EA]">
            <img
              src={heroSrc}
              alt={heroAlt}
              className="w-full h-full object-cover"
              data-testid="product-hero-image"
            />
          </div>
          {gallery.length > 1 && (
            <div className="mt-3 flex gap-2 flex-wrap" data-testid="product-gallery-thumbs">
              {gallery.map((src, i) => (
                <button
                  key={`${src}-${i}`}
                  type="button"
                  onClick={() => setActiveIdx(i)}
                  className={`w-16 h-16 rounded-md overflow-hidden border-2 transition ${
                    i === activeIdx ? "border-[#476B6B]" : "border-transparent hover:border-[#C9A961]"
                  }`}
                  data-testid={`product-gallery-thumb-${i}`}
                  aria-label={`View image ${i + 1} of ${gallery.length}`}
                >
                  <img src={src} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
        <div>
          {p.type === "workshop_material" && (
            <span className="label text-[#C9A961] inline-flex items-center gap-2"><Lock size={12} strokeWidth={1.5} /> Workshop material</span>
          )}
          <h1 className="editorial-h1 mt-3" data-testid="product-name">{p.name}</h1>
          <div className="mt-3">
            <FulfillmentBadge product={p} size="lg" />
          </div>
          {p.is_vendor_product && p.vendor_name && (
            <p className="text-xs uppercase tracking-wider text-[#C9A961] mt-2" data-testid="product-vendor-badge">
              By{" "}
              {p.vendor_slug ? (
                <Link to={`/partner/${p.vendor_slug}`} className="text-[#476B6B] hover:underline">{p.vendor_name}</Link>
              ) : (
                <span className="text-[#476B6B]">{p.vendor_name}</span>
              )}
            </p>
          )}
          {p.is_gallery_artwork && (
            <p className="text-xs uppercase tracking-wider text-[#A87A4A] mt-2 inline-flex items-center gap-2" data-testid="product-artist-badge">
              <Palette size={12} strokeWidth={1.6} /> By{" "}
              {p.gallery_artist_slug ? (
                <Link to={`/gallery/${p.gallery_artist_slug}`} className="text-[#476B6B] hover:underline">{p.gallery_artist_name}</Link>
              ) : (
                <span className="text-[#476B6B]">{p.gallery_artist_name}</span>
              )}
              <span className="text-[#5C6B6B]">· ships directly from the artist&apos;s studio</span>
            </p>
          )}
          <div className="mt-2">
            <AggregateRatingBadge subjectType="product" subjectId={p.id} />
          </div>
          <p className="font-serif text-3xl text-[#1A2424] mt-4">${p.price?.toFixed(2)}</p>
          {p.is_gallery_artwork && !p.foundation_absorbs_markup && (
            <p className="text-xs text-[#A87A4A] italic mt-1" data-testid="product-patronage-note">
              + 20% Foundation patronage at checkout ($
              {(p.price * 0.2).toFixed(2)} supports artist gallery curation)
            </p>
          )}
          <p className="text-base text-[#5C6B6B] mt-6 leading-relaxed">{p.description}</p>

          {p.locked ? (
            <div className="card p-5 mt-8 bg-[#FAF8F5]" data-testid="product-locked">
              <p className="text-sm text-[#1A2424] font-medium">This material is reserved.</p>
              <p className="text-xs text-[#5C6B6B] mt-2">{p.lock_reason}</p>
              {p.workshop_id && (
                <Link to={`/practice`} className="btn-outline mt-4 text-sm" data-testid="product-find-workshop">
                  Find workshops
                </Link>
              )}
            </div>
          ) : p.is_off_site && p.vendor_slug ? (
            <div className="mt-8" data-testid="product-off-site-block">
              <div className="card p-5 bg-[#F4F1EA] border-2 border-[#476B6B]">
                <p className="label !mt-0 !text-[#476B6B] inline-flex items-center gap-1">
                  <ExternalLink size={11} strokeWidth={1.8} /> Sold on the vendor&apos;s own site
                </p>
                <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">
                  {p.vendor_name ? `${p.vendor_name} handles the order on their own store. ` : ""}
                  Clicking through stamps your visit so they know birthright sent you.
                </p>
                <a
                  href={`${process.env.REACT_APP_BACKEND_URL}/api/out/${p.vendor_slug}?product_id=${p.id}`}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="btn-primary text-sm mt-4 inline-flex items-center gap-2"
                  data-testid="product-buy-external"
                >
                  <ExternalLink size={14} strokeWidth={1.5} /> Buy on {p.vendor_name || "vendor site"} →
                </a>
              </div>
            </div>
          ) : !isPurchasable(p) ? (
            <div className="mt-8" data-testid="product-sample-block">
              <div className="card p-5 bg-[#FBF1DC] border-2 border-[#7C5316]/30">
                <p className="label !mt-0 !text-[#7C5316]">Sample · not yet for sale</p>
                <p className="text-sm text-[#5C6B6B] mt-2 leading-relaxed">
                  This is a concept image generated to show what the product could look like.
                  We don&apos;t have a fulfillment path for this item yet, so it isn&apos;t
                  available for purchase. If you&apos;d like to make this real, reach out via
                  the Need help bubble — we can connect you with a maker.
                </p>
              </div>
            </div>
          ) : (
            <div className="mt-8 space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex items-center border border-[#E5E1D8] rounded-full overflow-hidden">
                  <button onClick={() => setQty(Math.max(1, qty - 1))} className="px-4 py-2 hover:bg-[#FAF8F5]" data-testid="product-qty-minus">−</button>
                  <span className="px-4 py-2 font-medium" data-testid="product-qty">{qty}</span>
                  <button onClick={() => setQty(qty + 1)} className="px-4 py-2 hover:bg-[#FAF8F5]" data-testid="product-qty-plus">+</button>
                </div>
                <button
                  onClick={() => {
                    addItem(p, qty);
                    toast.success(`Added ${qty} × ${p.name}`);
                  }}
                  className="btn-primary"
                  data-testid="product-add-to-cart"
                >
                  <ShoppingBag size={16} strokeWidth={1.5} />
                  {p.is_gallery_artwork
                    ? "Patron with 20% Foundation support"
                    : "Add to cart"}
                </button>
              </div>

              {p.is_gallery_artwork && p.artist_external_url && (() => {
                const ext = p.artist_external_url;
                const sep = ext.includes("?") ? "&" : "?";
                const taggedHref = `${ext}${sep}via=birthright`;
                return (
                  <div
                    className="text-xs text-[#5C6B6B] flex items-center gap-2"
                    data-testid="product-artist-direct"
                  >
                    <span>or</span>
                    <a
                      href={taggedHref}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-[#476B6B] hover:underline inline-flex items-center gap-1"
                    >
                      visit this work on the artist&apos;s own site
                      <ExternalLink size={11} strokeWidth={1.6} />
                    </a>
                  </div>
                );
              })()}
            </div>
          )}

          {!p.is_off_site && (
            <p className="text-xs text-[#5C6B6B] mt-6">{p.inventory} in stock</p>
          )}
          {p.type !== "workshop_material" && (
            <div className="mt-4">
              <ShareButton
                surface="product"
                surfaceId={p.id}
                path={`/equip/${p.id}`}
                title={p.name}
                emailSubject={`From the birthright shop: ${p.name}`}
                showLabel
              />
            </div>
          )}
        </div>
      </div>

      <div className="mt-12">
        <ReviewSection
          subjectType="product"
          subjectId={p.id}
          subjectLabel="Customer reviews"
        />
      </div>
    </div>
  );
}
