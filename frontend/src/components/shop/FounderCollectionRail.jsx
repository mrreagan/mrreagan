/**
 * FounderCollectionRail — featured-3 swipeable teaser.
 *
 * Replaces the previous "show every item in a horizontal scroll" layout.
 * Now functions like a magazine front-of-book:
 *   - The window shows ONE featured item at a time
 *   - Three featured items total (the most recently curated + the
 *     is_homepage_feature winner pinned at front)
 *   - Native horizontal scroll-snap on touch devices; arrow controls on
 *     desktop. CSS-only — no swiper/embla dependency.
 *   - Tap the "FOUNDER COLLECTION" header, the headline, or the "See all"
 *     pill to enter the full collection view at /equip/collection/founder.
 */
import React, { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, ChevronLeft, ChevronRight, ArrowRight, ExternalLink, ShoppingBag } from "lucide-react";
import { useCart } from "../../contexts/CartContext";
import { toast } from "sonner";

// Pick the carousel slides:
//   1. Items with carousel_rank ∈ {1,2,3} take their assigned slot (admin
//      control surface lives at /admin/founder-carousel).
//   2. If fewer than 3 ranked items exist, backfill with `is_homepage_feature`
//      (legacy flag) and then most-recent items so the carousel never goes
//      empty.
function pickFeatured(products) {
  const ranked = products
    .filter((p) => [1, 2, 3].includes(p.carousel_rank))
    .sort((a, b) => a.carousel_rank - b.carousel_rank);
  const rankedIds = new Set(ranked.map((p) => p.id));
  const sorted = [...products]
    .filter((p) => !rankedIds.has(p.id))
    .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
  const legacyHero = sorted.find((p) => p.is_homepage_feature);
  const rest = sorted.filter((p) => p.id !== legacyHero?.id);
  return [...ranked, legacyHero, ...rest].filter(Boolean).slice(0, 3);
}

export default function FounderCollectionRail({ products }) {
  const featured = useMemo(() => pickFeatured(products || []), [products]);
  if (featured.length === 0) return null;
  return (
    <section
      className="rounded-2xl bg-[#0F2424] text-[#FAF8F5] my-10 overflow-hidden"
      data-testid="founder-collection-rail"
    >
      <FeaturedCarousel featured={featured} total={products.length} />
    </section>
  );
}

function FeaturedCarousel({ featured, total }) {
  const trackRef = useRef(null);
  const [idx, setIdx] = useState(0);

  const scrollTo = (newIdx) => {
    const next = Math.max(0, Math.min(featured.length - 1, newIdx));
    setIdx(next);
    const track = trackRef.current;
    if (track) {
      const slide = track.children[next];
      slide?.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });
    }
  };

  // Update idx as the user swipes natively (scroll-snap). Throttled via
  // requestAnimationFrame so we don't thrash setState on every scroll event.
  const rafRef = useRef(0);
  const onScroll = () => {
    if (rafRef.current) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = 0;
      const track = trackRef.current;
      if (!track) return;
      const w = track.clientWidth;
      const i = Math.round(track.scrollLeft / w);
      if (i !== idx) setIdx(i);
    });
  };

  return (
    <>
      <header className="p-6 pb-4 sm:p-8 sm:pb-5 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <Link
            to="/equip/collection/founder"
            data-testid="founder-collection-header-link"
            className="inline-flex items-center gap-2 text-[#C9A961] hover:text-[#D4B677] transition"
          >
            <Sparkles size={14} strokeWidth={1.5} />
            <span className="label !mt-0 text-[#C9A961]">Founder Collection</span>
          </Link>
          <Link to="/equip/collection/founder" className="block group">
            <h2 className="font-serif text-2xl sm:text-3xl mt-2 leading-tight !text-[#FAF8F5] group-hover:text-[#C9A961] transition">
              You are the founder of your own love story.
            </h2>
          </Link>
          <p className="text-sm text-[#FAF8F5]/70 mt-2 max-w-md">
            A curated few. Tap any card to read; tap{" "}
            <span className="text-[#C9A961]">See all {total}</span>{" "}
            to enter the full collection.
          </p>
        </div>
        <Link
          to="/equip/collection/founder"
          data-testid="founder-collection-see-all"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-[#FAF8F5]/30 text-[#FAF8F5] text-xs hover:border-[#C9A961] hover:text-[#C9A961] transition"
        >
          See all {total} <ArrowRight size={12} strokeWidth={1.8} />
        </Link>
      </header>

      <div className="relative px-6 pb-6 sm:px-8 sm:pb-8">
        <div
          ref={trackRef}
          onScroll={onScroll}
          className="flex overflow-x-auto snap-x snap-mandatory gap-4 scroll-smooth pb-2 -mx-1 px-1"
          style={{ scrollbarWidth: "none" }}
          data-testid="founder-collection-track"
        >
          {featured.map((p) => (
            <FeaturedCard key={p.id} product={p} />
          ))}
        </div>

        {/* Dots + desktop arrows */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex gap-1.5" data-testid="founder-collection-dots">
            {featured.map((_, i) => (
              <button
                key={i}
                onClick={() => scrollTo(i)}
                aria-label={`Go to slide ${i + 1}`}
                className={`w-1.5 h-1.5 rounded-full transition ${i === idx ? "bg-[#C9A961] w-6" : "bg-[#FAF8F5]/30 hover:bg-[#FAF8F5]/50"}`}
              />
            ))}
          </div>
          <div className="hidden sm:flex gap-1.5">
            <button
              onClick={() => scrollTo(idx - 1)}
              disabled={idx === 0}
              aria-label="Previous"
              data-testid="founder-collection-prev"
              className="flex items-center justify-center w-8 h-8 rounded-full border border-[#FAF8F5]/30 text-[#FAF8F5] hover:border-[#C9A961] hover:text-[#C9A961] disabled:opacity-30 disabled:cursor-not-allowed transition"
            >
              <ChevronLeft size={16} strokeWidth={1.8} />
            </button>
            <button
              onClick={() => scrollTo(idx + 1)}
              disabled={idx === featured.length - 1}
              aria-label="Next"
              data-testid="founder-collection-next"
              className="flex items-center justify-center w-8 h-8 rounded-full border border-[#FAF8F5]/30 text-[#FAF8F5] hover:border-[#C9A961] hover:text-[#C9A961] disabled:opacity-30 disabled:cursor-not-allowed transition"
            >
              <ChevronRight size={16} strokeWidth={1.8} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}


// One full-bleed card per slide. Image left / copy right on desktop;
// stacked on mobile. The whole image block is a Link to the product
// detail; the buttons live inside the copy column to avoid nested links.
function FeaturedCard({ product }) {
  const { addItem } = useCart();
  const isExternal = !!product.is_off_site;
  return (
    <article
      className="snap-start shrink-0 w-full rounded-xl bg-[#FAF8F5] text-[#1A2424] overflow-hidden grid grid-cols-1 md:grid-cols-2"
      data-testid={`founder-collection-card-${product.id}`}
    >
      <Link
        to={`/equip/${product.id}`}
        className="block aspect-[4/3] bg-[#F4F1EA] overflow-hidden"
      >
        <img
          src={product.image_url}
          alt={product.name}
          className="w-full h-full object-contain"
        />
      </Link>
      <div className="p-5 sm:p-6 flex flex-col">
        <Link
          to={`/equip/${product.id}`}
          className="font-serif text-xl sm:text-2xl leading-tight hover:text-[#476B6B]"
        >
          {product.name}
        </Link>
        <p className="text-sm text-[#5C6B6B] mt-3 flex-1 line-clamp-4 whitespace-pre-wrap">
          {product.description}
        </p>
        {isExternal && product.vendor_name && (
          <p className="text-[10px] uppercase tracking-wider text-[#476B6B] mt-3">
            Made to order by {product.vendor_name}
          </p>
        )}
        <div className="mt-4 flex items-center justify-between gap-3">
          <div>
            <span className="font-medium text-xl">${product.price?.toFixed(2)}</span>
            {isExternal && (
              <span className="block text-[10px] uppercase tracking-wider text-[#A87A4A] mt-0.5">
                + shipping at checkout
              </span>
            )}
          </div>
          {isExternal ? (
            <Link
              to={`/equip/${product.id}`}
              className="text-xs flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#2C4E5A] text-[#FAF8F5] hover:bg-[#1F3942] transition"
              data-testid={`founder-collection-external-${product.id}`}
            >
              <ExternalLink size={12} strokeWidth={1.8} /> Order direct
            </Link>
          ) : (
            <button
              onClick={() => { addItem(product); toast.success(`Added ${product.name}`); }}
              className="text-xs flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#C9A961] text-[#0F2424] hover:bg-[#D4B677] transition"
              data-testid={`founder-collection-add-${product.id}`}
            >
              <ShoppingBag size={12} strokeWidth={1.8} /> Add to cart
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
