/* eslint-disable */
/**
 * AdminFounderCarousel — single screen to manage the 3 featured slots on
 * the Equip page Founder Collection teaser.
 *
 * Left column: 3 numbered slots, each showing the currently-assigned
 * product (or "Empty" placeholder). Click "Remove" to free a slot.
 *
 * Right column: every other product in collection=founder_collection.
 * Click any "Set as slot N" button to assign it. The backend
 * auto-frees the previous holder of that slot.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Sparkles, X, Plus, RefreshCw } from "lucide-react";
import api from "../lib/api";

export default function AdminFounderCarousel() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try {
      const r = await api.get("/products/founder-carousel/manage");
      setData(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Couldn't load carousel data");
    }
  };

  useEffect(() => { refresh(); }, []);

  const assign = async (productId, rank) => {
    setBusy(true);
    try {
      await api.post("/products/founder-carousel/manage", { product_id: productId, rank });
      toast.success(`Set as slot ${rank}`);
      await refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Assignment failed");
    } finally { setBusy(false); }
  };

  const unassign = async (productId) => {
    setBusy(true);
    try {
      await api.delete("/products/founder-carousel/manage", {
        data: { product_id: productId },
      });
      toast.success("Removed from carousel");
      await refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Removal failed");
    } finally { setBusy(false); }
  };

  if (!data) {
    return (
      <div className="container-page py-10">
        <p className="text-sm text-[#5C6B6B] italic">Loading…</p>
      </div>
    );
  }

  // Build the 3 slots: featured items mapped by rank, blanks for empty slots.
  const slots = [1, 2, 3].map((rank) => ({
    rank,
    product: data.featured.find((p) => p.carousel_rank === rank) || null,
  }));

  return (
    <div className="container-page py-10 sm:py-14" data-testid="admin-founder-carousel">
      <Link
        to="/admin/products"
        className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6"
      >
        <ArrowLeft size={14} strokeWidth={1.5} /> Back to products
      </Link>
      <header className="mb-8">
        <div className="inline-flex items-center gap-2 text-[#C9A961]">
          <Sparkles size={14} strokeWidth={1.5} />
          <span className="label !mt-0 text-[#C9A961]">Founder Collection</span>
        </div>
        <h1 className="font-serif text-3xl mt-2 leading-tight">Carousel control</h1>
        <p className="text-sm text-[#5C6B6B] max-w-2xl mt-2 leading-relaxed">
          Choose the three items that surface on the swipeable teaser at <code className="text-[#476B6B]">/equip</code>.
          Slot 1 appears first (the hero), then slots 2 and 3. Items not assigned
          to a slot still appear in the full collection grid at <code className="text-[#476B6B]">/equip/collection/founder</code>.
        </p>
        <button
          onClick={refresh}
          className="mt-4 inline-flex items-center gap-1.5 text-xs text-[#476B6B] hover:text-[#1A2424]"
        >
          <RefreshCw size={12} strokeWidth={1.7} /> Refresh
        </button>
      </header>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Slots column */}
        <section>
          <h2 className="label text-[#A87A4A] mb-3">Featured slots (live on /equip)</h2>
          <ol className="space-y-3" data-testid="carousel-slots">
            {slots.map(({ rank, product }) => (
              <li
                key={rank}
                className={`card p-4 flex items-center gap-4 ${product ? "bg-[#FAF8F5]" : "bg-[#FBF9F4] border-dashed"}`}
                data-testid={`carousel-slot-${rank}`}
              >
                <span className="flex items-center justify-center w-10 h-10 rounded-full bg-[#0F2424] text-[#C9A961] font-serif text-lg shrink-0">
                  {rank}
                </span>
                {product ? (
                  <>
                    <img
                      src={product.image_url}
                      alt={product.name}
                      className="w-14 h-14 rounded object-cover bg-[#F4F1EA] shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-serif text-sm leading-tight truncate">{product.name}</p>
                      <p className="text-[11px] text-[#5C6B6B]">${product.price?.toFixed(2)}</p>
                    </div>
                    <button
                      onClick={() => unassign(product.id)}
                      disabled={busy}
                      className="text-xs text-[#A87A4A] hover:text-[#1A2424] inline-flex items-center gap-1"
                      data-testid={`carousel-slot-${rank}-remove`}
                    >
                      <X size={12} strokeWidth={1.8} /> Remove
                    </button>
                  </>
                ) : (
                  <p className="text-sm italic text-[#9DA8A8]">Empty — pick from the right →</p>
                )}
              </li>
            ))}
          </ol>
        </section>

        {/* Available products column */}
        <section>
          <h2 className="label text-[#476B6B] mb-3">
            Other items in Founder Collection ({data.available.length})
          </h2>
          {data.available.length === 0 ? (
            <p className="text-sm italic text-[#5C6B6B]">
              Every founder_collection item is already in a slot.
            </p>
          ) : (
            <ul className="space-y-2" data-testid="carousel-available">
              {data.available.map((p) => (
                <li
                  key={p.id}
                  className="card p-3 flex items-center gap-3"
                  data-testid={`carousel-available-${p.id}`}
                >
                  <img
                    src={p.image_url}
                    alt={p.name}
                    className="w-12 h-12 rounded object-cover bg-[#F4F1EA] shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-serif text-sm leading-tight truncate">{p.name}</p>
                    <p className="text-[11px] text-[#5C6B6B]">${p.price?.toFixed(2)}</p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    {[1, 2, 3].map((r) => (
                      <button
                        key={r}
                        onClick={() => assign(p.id, r)}
                        disabled={busy}
                        className="text-[10px] uppercase tracking-wider px-2 py-1 rounded border border-[#E5E1D8] hover:bg-[#C9A961] hover:text-[#0F2424] hover:border-[#C9A961] transition"
                        title={`Set as slot ${r}`}
                        data-testid={`carousel-assign-${p.id}-${r}`}
                      >
                        <Plus size={9} strokeWidth={2} className="inline mr-0.5" />{r}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <p className="text-xs text-[#9DA8A8] italic mt-10">
        Tip: you can also set carousel rank per-product from <Link to="/admin/products" className="underline">/admin/products</Link>.
        This screen is just the faster way to manage all three slots at once.
      </p>
    </div>
  );
}
