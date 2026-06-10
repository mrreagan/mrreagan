import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import api from "../lib/api";

/**
 * On-birthright offerings rail for a partner profile.
 *
 * Core principle: keep visitors here first. Every product on this rail links
 * to the on-birthright product detail page (`/equip/<slug>`) — even when
 * fulfillment is off-site — so we capture attribution + the partnership
 * revenue share. The "Visit external site" link on the profile stays
 * available, but it stops being the dominant CTA.
 *
 * Renders nothing if the partner has zero on-birthright offerings.
 */
export default function PartnerOfferings({ slug, partnerName }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    api.get(`/partners/${slug}/offerings`)
      .then((r) => { if (!cancelled) setData(r.data); })
      .catch(() => { if (!cancelled) setData({ count: 0, items: [] }); });
    return () => { cancelled = true; };
  }, [slug]);

  if (!data || !data.count) return null;

  return (
    <section
      id="offerings"
      className="mt-8 border-t border-[#E5E1D8] pt-6"
      data-testid="partner-offerings-section"
    >
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h2 className="font-serif text-2xl">
          {partnerName ? `${partnerName} on birthright` : "Their birthright offerings"}
        </h2>
        <p className="text-[11px] uppercase tracking-wider text-[#5C6B6B]" data-testid="offering-count">
          {data.count} {data.count === 1 ? "listing" : "listings"}
          {data.on_site_count > 0 && data.off_site_count > 0 && (
            <> · {data.on_site_count} on-site · {data.off_site_count} partner-fulfilled</>
          )}
        </p>
      </div>
      <p className="text-xs text-[#5C6B6B] mt-2 max-w-prose">
        Browse and start your order here. Every purchase made through birthright
        supports the foundation&apos;s work and the partner network — the partnership
        share funds the next workshop, the next research artifact, the next
        repair.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-5">
        {data.items.slice(0, 9).map((p) => (
          <OfferingTile key={p.slug} product={p} />
        ))}
      </div>

      {data.count > 9 && (
        <div className="mt-4">
          <Link
            to={`/equip?vendor=${encodeURIComponent(slug)}`}
            className="text-xs uppercase tracking-wider text-[#476B6B] hover:underline inline-flex items-center gap-1"
            data-testid="see-all-offerings"
          >
            See all {data.count} listings <ArrowUpRight size={11} strokeWidth={1.5} />
          </Link>
        </div>
      )}
    </section>
  );
}

function OfferingTile({ product }) {
  const href = `/equip/${product.slug}`;
  const priceLabel = typeof product.price === "number" ? `$${product.price.toFixed(0)}` : null;
  const offSite = !!product.is_off_site;
  return (
    <Link
      to={href}
      className="group block card p-0 overflow-hidden hover:border-[#476B6B] transition"
      data-testid={`offering-tile-${product.slug}`}
    >
      <div className="aspect-square bg-[#FAF8F5] overflow-hidden">
        {product.image_url ? (
          <img
            src={product.image_url.startsWith("http") ? product.image_url : product.image_url}
            alt=""
            loading="lazy"
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform"
          />
        ) : (
          <div className="w-full h-full" />
        )}
      </div>
      <div className="p-3">
        <p className="font-serif text-sm line-clamp-2 leading-tight" data-testid={`offering-name-${product.slug}`}>
          {product.name}
        </p>
        <div className="flex items-center justify-between mt-2 gap-2">
          {priceLabel && (
            <span className="text-xs font-semibold text-[#1A2424]">{priceLabel}</span>
          )}
          {offSite && (
            <span
              className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-[#FAF8F5] border border-[#E5E1D8] text-[#5C6B6B]"
              title="Order routes through birthright; partner fulfills off-site"
            >
              partner-fulfilled
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
