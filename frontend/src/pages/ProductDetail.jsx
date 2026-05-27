import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { useCart } from "../contexts/CartContext";
import { toast } from "sonner";
import { ShoppingBag, Lock, ArrowLeft } from "lucide-react";
import ReviewSection, { AggregateRatingBadge } from "../components/ReviewSection";
import ShareButton from "../components/ShareButton";

export default function ProductDetail() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [qty, setQty] = useState(1);
  const { addItem } = useCart();

  useEffect(() => {
    api.get(`/products/${id}`).then((r) => setP(r.data)).catch(() => {});
  }, [id]);

  if (!p) return <div className="container-page py-20" data-testid="product-loading">Loading...</div>;

  return (
    <div className="container-page py-12" data-testid="product-detail-page">
      <Link to="/shop" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Back to shop
      </Link>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div className="card overflow-hidden aspect-square bg-[#F4F1EA] flex items-center justify-center">
          <img src={p.image_url} alt={p.name} className="w-full h-full object-contain p-3" />
        </div>
        <div>
          {p.type === "workshop_material" && (
            <span className="label text-[#C9A961] inline-flex items-center gap-2"><Lock size={12} strokeWidth={1.5} /> Workshop material</span>
          )}
          <h1 className="editorial-h1 mt-3" data-testid="product-name">{p.name}</h1>
          {p.is_vendor_product && p.vendor_name && (
            <p className="text-xs uppercase tracking-wider text-[#C9A961] mt-2" data-testid="product-vendor-badge">
              By{" "}
              {p.vendor_slug ? (
                <Link to={`/partners/${p.vendor_slug}`} className="text-[#476B6B] hover:underline">{p.vendor_name}</Link>
              ) : (
                <span className="text-[#476B6B]">{p.vendor_name}</span>
              )}
            </p>
          )}
          <div className="mt-2">
            <AggregateRatingBadge subjectType="product" subjectId={p.id} />
          </div>
          <p className="font-serif text-3xl text-[#1A2424] mt-4">${p.price?.toFixed(2)}</p>
          <p className="text-base text-[#5C6B6B] mt-6 leading-relaxed">{p.description}</p>

          {p.locked ? (
            <div className="card p-5 mt-8 bg-[#FAF8F5]" data-testid="product-locked">
              <p className="text-sm text-[#1A2424] font-medium">This material is reserved.</p>
              <p className="text-xs text-[#5C6B6B] mt-2">{p.lock_reason}</p>
              {p.workshop_id && (
                <Link to={`/workshops`} className="btn-outline mt-4 text-sm" data-testid="product-find-workshop">
                  Find workshops
                </Link>
              )}
            </div>
          ) : (
            <div className="mt-8 flex items-center gap-4">
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
                <ShoppingBag size={16} strokeWidth={1.5} /> Add to cart
              </button>
            </div>
          )}

          <p className="text-xs text-[#5C6B6B] mt-6">{p.inventory} in stock</p>
          {p.type !== "workshop_material" && (
            <div className="mt-4">
              <ShareButton
                surface="product"
                surfaceId={p.id}
                path={`/shop/${p.id}`}
                title={p.name}
                emailSubject={`From the Birthright shop: ${p.name}`}
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
