import React from "react";
import { Link } from "react-router-dom";
import { Sparkles, ShoppingBag, ExternalLink } from "lucide-react";
import { useCart } from "../../contexts/CartContext";
import { toast } from "sonner";

/**
 * Founder Collection — editorial featured rail at the top of /shop.
 * Renders nothing if no products in the collection are available yet.
 */
export default function FounderCollectionRail({ products }) {
  const items = (products || []).filter(
    (p) => p.collection === "founder_collection" && p.moderation_status !== "unpublished"
  );
  if (items.length === 0) return null;

  return (
    <section
      className="mt-12 -mx-4 sm:mx-0 sm:rounded-3xl bg-[#0F2424] text-[#FAF8F5] px-6 sm:px-10 py-10 sm:py-12 overflow-hidden"
      data-testid="founder-collection-rail"
    >
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-3 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 text-[#C9A961]">
            <Sparkles size={14} strokeWidth={1.5} />
            <span className="label !mt-0 text-[#C9A961]">Founder Collection</span>
          </div>
          <h2 className="font-serif text-3xl sm:text-4xl mt-2 leading-tight !text-[#FAF8F5]">
            You are the founder of your own love story.
          </h2>
          <p className="text-sm text-[#FAF8F5]/80 mt-3 max-w-xl leading-relaxed">
            Quiet objects to carry the work with you. Five hand-engraved leather
            patches — each phrase one of birthright&apos;s load-bearing truths,
            burned into vegetable-tanned leather by{" "}
            <span className="text-[#C9A961] italic">7C&apos;s Farmstead</span>.
            Made to order. Buy any single phrase at $10, or the full set for $40.
          </p>
        </div>
        <p className="text-[10px] uppercase tracking-wider text-[#FAF8F5]/50 lg:text-right">
          Limited curated pieces · Made to order
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map((p) => (
          <FounderCard key={p.id} product={p} />
        ))}
      </div>
    </section>
  );
}

function FounderCard({ product }) {
  const { addItem, items } = useCart();
  const cap = Number.isFinite(product.max_per_order) ? product.max_per_order : null;
  const inCart = items.find((i) => i.product_id === product.id);
  const atCap = cap && inCart && inCart.quantity >= cap;
  const isExternal = !!product.is_off_site;

  return (
    <article
      className="rounded-2xl bg-[#FAF8F5] text-[#1A2424] overflow-hidden flex flex-col shadow-lg"
      data-testid={`founder-collection-card-${product.id}`}
    >
      <Link to={`/equip/${product.id}`} className="block aspect-[4/3] bg-[#F4F1EA] overflow-hidden">
        <img
          src={product.image_url}
          alt={product.name}
          className="w-full h-full object-contain"
        />
      </Link>
      <div className="p-5 flex-1 flex flex-col">
        <Link to={`/equip/${product.id}`} className="font-serif text-xl leading-tight hover:text-[#476B6B]">
          {product.name}
        </Link>
        <p className="text-xs text-[#5C6B6B] mt-2 line-clamp-3 flex-1">{product.description}</p>
        {isExternal && product.vendor_name && (
          <p className="text-[10px] uppercase tracking-wider text-[#476B6B] mt-2">
            Made to order by {product.vendor_name}
          </p>
        )}
        <div className="mt-4 flex items-center justify-between gap-2">
          <div>
            <span className="font-medium text-lg">${product.price?.toFixed(2)}</span>
            {cap === 1 && (
              <span className="block text-[10px] uppercase tracking-wider text-[#C9A961] mt-0.5">
                One set per buyer
              </span>
            )}
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
              onClick={() => {
                if (atCap) {
                  toast.message(`Limited to ${cap} per order — already in cart.`);
                  return;
                }
                addItem(product);
                toast.success(`Added ${product.name}`);
              }}
              disabled={atCap}
              className={`text-xs flex items-center gap-1.5 px-4 py-2 rounded-full transition ${
                atCap
                  ? "bg-[#E5E1D8] text-[#5C6B6B] cursor-not-allowed"
                  : "bg-[#C9A961] text-[#0F2424] hover:bg-[#D4B677]"
              }`}
              data-testid={`founder-collection-add-${product.id}`}
            >
              <ShoppingBag size={12} strokeWidth={1.8} /> {atCap ? "In cart" : "Add to cart"}
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
