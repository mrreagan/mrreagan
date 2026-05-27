import React from "react";
import { Link } from "react-router-dom";
import { ShoppingBag, Lock } from "lucide-react";
import { useCart } from "../../contexts/CartContext";
import { toast } from "sonner";
import { AggregateRatingBadge } from "../ReviewSection";
import ShareButton from "../ShareButton";

const FILTERS = [
  { id: "merch", label: "Public merch" },
  { id: "workshop_material", label: "Workshop materials" },
  { id: "all", label: "All" },
];

export function ShopFilters({ active, onChange }) {
  return (
    <div className="mt-8 flex gap-2 flex-wrap" data-testid="shop-filters">
      {FILTERS.map((f) => (
        <button
          key={f.id}
          onClick={() => onChange(f.id)}
          className={`px-4 py-2 rounded-full text-xs uppercase tracking-wider font-medium border transition ${
            active === f.id ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
          }`}
          data-testid={`shop-filter-${f.id}`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}

export function ProductCard({ product }) {
  const { addItem } = useCart();
  const isMaterial = product.type === "workshop_material";
  const isVendor = product.is_vendor_product;

  return (
    <div className="card card-hover overflow-hidden flex flex-col" data-testid={`product-card-${product.id}`}>
      <Link to={`/equip/${product.id}`} className="block aspect-square bg-[#F4F1EA] overflow-hidden">
        <img src={product.image_url} alt={product.name} className="w-full h-full object-contain p-2" />
      </Link>
      <div className="p-5 flex-1 flex flex-col">
        <div className="flex items-start justify-between gap-2">
          <Link to={`/equip/${product.id}`} className="font-serif text-lg leading-tight hover:text-[#476B6B]">
            {product.name}
          </Link>
          {isMaterial && <Lock size={14} strokeWidth={1.5} className="text-[#C9A961] shrink-0 mt-1" />}
        </div>
        {isVendor && product.vendor_name && (
          <p className="text-[10px] uppercase tracking-wider text-[#C9A961] mt-1" data-testid={`product-vendor-badge-${product.id}`}>
            By{" "}
            {product.vendor_slug ? (
              <Link to={`/partner/${product.vendor_slug}`} className="text-[#476B6B] hover:underline" onClick={(e) => e.stopPropagation()}>
                {product.vendor_name}
              </Link>
            ) : (
              <span className="text-[#476B6B]">{product.vendor_name}</span>
            )}
          </p>
        )}
        <p className="text-xs text-[#5C6B6B] mt-1 line-clamp-2 flex-1">{product.description}</p>
        <div className="mt-2">
          <AggregateRatingBadge subjectType="product" subjectId={product.id} />
        </div>
        <div className="mt-4 flex items-center justify-between gap-2">
          <span className="font-medium text-[#1A2424]">${product.price?.toFixed(2)}</span>
          <div className="flex items-center gap-1.5">
            {!isMaterial && (
              <ShareButton
                surface="product"
                surfaceId={product.id}
                path={`/equip/${product.id}`}
                title={product.name}
                emailSubject={`From the Birthright shop: ${product.name}`}
                size="sm"
              />
            )}
            {isMaterial ? (
              <Link to={`/equip/${product.id}`} className="text-xs text-[#476B6B] font-medium hover:underline">
                Participants only
              </Link>
            ) : (
              <button
                onClick={() => {
                  addItem(product);
                  toast.success(`Added ${product.name}`);
                }}
                className="text-xs flex items-center gap-1.5 bg-[#476B6B] text-white px-3 py-1.5 rounded-full hover:bg-[#3A5858] transition"
                data-testid={`product-add-${product.id}`}
              >
                <ShoppingBag size={12} strokeWidth={1.5} /> Add
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function ProductGrid({ products }) {
  return (
    <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="shop-products">
      {products.map((p) => <ProductCard key={p.id} product={p} />)}
    </div>
  );
}
