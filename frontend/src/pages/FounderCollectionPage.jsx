/**
 * FounderCollectionPage — full grid view of every item in the Founder
 * Collection. Linked from the teaser carousel on the Equip page via the
 * header, the headline, and the "See all" pill.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Sparkles, ShoppingBag, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import api from "../lib/api";
import { useCart } from "../contexts/CartContext";

export default function FounderCollectionPage() {
  const [items, setItems] = useState(null);
  const { addItem } = useCart();

  useEffect(() => {
    api.get("/products?type=merch").then((r) => {
      const rows = (r.data || [])
        .filter((p) => p.collection === "founder_collection")
        .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
      setItems(rows);
    }).catch(() => setItems([]));
  }, []);

  return (
    <div className="container-page py-10 sm:py-14" data-testid="founder-collection-page">
      <Link
        to="/equip"
        className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-8"
        data-testid="founder-collection-back"
      >
        <ArrowLeft size={14} strokeWidth={1.5} /> Back to Equip
      </Link>

      <header className="max-w-2xl mb-10">
        <div className="inline-flex items-center gap-2 text-[#A87A4A]">
          <Sparkles size={14} strokeWidth={1.5} />
          <span className="label !mt-0 text-[#A87A4A]">Founder Collection</span>
        </div>
        <h1 className="editorial-h1 mt-3">You are the founder of your own love story.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          A small, curated set of quiet objects to carry the practice into the world.
          Five hand-engraved leather phrases at $10 each (or the full set bundled for $40),
          plus journals, hats, and other ways to hold the work close. Made to order;
          everything ships from the artisan directly.
        </p>
      </header>

      {items === null && <p className="text-sm text-[#5C6B6B] italic">Loading…</p>}
      {items !== null && items.length === 0 && (
        <p className="text-sm text-[#5C6B6B] italic">The collection is being restocked.</p>
      )}

      {items !== null && items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="founder-collection-grid">
          {items.map((p) => (
            <FullCard key={p.id} product={p} onAdd={() => { addItem(p); toast.success(`Added ${p.name}`); }} />
          ))}
        </div>
      )}
    </div>
  );
}


function FullCard({ product, onAdd }) {
  const isExternal = !!product.is_off_site;
  return (
    <article
      className="card overflow-hidden flex flex-col"
      data-testid={`founder-collection-full-card-${product.id}`}
    >
      <Link to={`/equip/${product.id}`} className="block aspect-[4/3] bg-[#F4F1EA] overflow-hidden">
        <img
          src={product.image_url}
          alt={product.name}
          className="w-full h-full object-contain"
        />
      </Link>
      <div className="p-5 flex-1 flex flex-col">
        <Link to={`/equip/${product.id}`} className="font-serif text-lg leading-tight hover:text-[#476B6B]">
          {product.name}
        </Link>
        <p className="text-xs text-[#5C6B6B] mt-2 line-clamp-4 flex-1 whitespace-pre-wrap">{product.description}</p>
        {isExternal && product.vendor_name && (
          <p className="text-[10px] uppercase tracking-wider text-[#476B6B] mt-3">
            Made to order by {product.vendor_name}
          </p>
        )}
        <div className="mt-4 flex items-center justify-between gap-2">
          <div>
            <span className="font-medium text-lg">${product.price?.toFixed(2)}</span>
            {isExternal && (
              <span className="block text-[10px] uppercase tracking-wider text-[#A87A4A] mt-0.5">
                + shipping at checkout
              </span>
            )}
          </div>
          {isExternal ? (
            <Link
              to={`/equip/${product.id}`}
              className="text-xs flex items-center gap-1.5 px-3 py-2 rounded-full bg-[#2C4E5A] text-[#FAF8F5] hover:bg-[#1F3942] transition"
            >
              <ExternalLink size={12} strokeWidth={1.8} /> Order direct
            </Link>
          ) : (
            <button
              onClick={onAdd}
              className="text-xs flex items-center gap-1.5 px-3 py-2 rounded-full bg-[#C9A961] text-[#0F2424] hover:bg-[#D4B677] transition"
            >
              <ShoppingBag size={12} strokeWidth={1.8} /> Add to cart
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
