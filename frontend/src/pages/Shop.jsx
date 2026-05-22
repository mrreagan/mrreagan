import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useCart } from "../contexts/CartContext";
import { toast } from "sonner";
import { ShoppingBag, Lock } from "lucide-react";

export default function Shop() {
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState("merch");
  const [loading, setLoading] = useState(true);
  const { addItem } = useCart();

  useEffect(() => {
    setLoading(true);
    const params = filter === "all" ? "" : `?type=${filter}`;
    api
      .get(`/products${params}`)
      .then((r) => setProducts(r.data))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className="container-page py-16" data-testid="shop-page">
      <div className="max-w-2xl">
        <span className="label">Storefront</span>
        <h1 className="editorial-h1 mt-3">Made to live with the work.</h1>
        <div className="divider-flame" />
        <p className="text-base text-[#5C6B6B] leading-relaxed">
          Journals, mugs, totes, and quiet objects designed to keep the practice close. Workshop materials below are reserved for current participants.
        </p>
      </div>

      <div className="mt-8 flex gap-2 flex-wrap" data-testid="shop-filters">
        {[
          { id: "merch", label: "Public merch" },
          { id: "workshop_material", label: "Workshop materials" },
          { id: "all", label: "All" },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-4 py-2 rounded-full text-xs uppercase tracking-wider font-medium border transition ${
              filter === f.id ? "bg-[#476B6B] text-white border-[#476B6B]" : "bg-white text-[#1A2424] border-[#E5E1D8] hover:border-[#476B6B]"
            }`}
            data-testid={`shop-filter-${f.id}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-12">Loading...</p>
      ) : (
        <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6" data-testid="shop-products">
          {products.map((p) => (
            <div key={p.id} className="card card-hover overflow-hidden flex flex-col" data-testid={`product-card-${p.id}`}>
              <Link to={`/shop/${p.id}`} className="block aspect-square bg-[#E5E1D8] overflow-hidden">
                <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
              </Link>
              <div className="p-5 flex-1 flex flex-col">
                <div className="flex items-start justify-between gap-2">
                  <Link to={`/shop/${p.id}`} className="font-serif text-lg leading-tight hover:text-[#476B6B]">{p.name}</Link>
                  {p.type === "workshop_material" && <Lock size={14} strokeWidth={1.5} className="text-[#C9A961] shrink-0 mt-1" />}
                </div>
                <p className="text-xs text-[#5C6B6B] mt-1 line-clamp-2 flex-1">{p.description}</p>
                <div className="mt-4 flex items-center justify-between">
                  <span className="font-medium text-[#1A2424]">${p.price?.toFixed(2)}</span>
                  {p.type === "workshop_material" ? (
                    <Link to={`/shop/${p.id}`} className="text-xs text-[#476B6B] font-medium hover:underline">Participants only</Link>
                  ) : (
                    <button
                      onClick={() => {
                        addItem(p);
                        toast.success(`Added ${p.name}`);
                      }}
                      className="text-xs flex items-center gap-1.5 bg-[#476B6B] text-white px-3 py-1.5 rounded-full hover:bg-[#3A5858] transition"
                      data-testid={`product-add-${p.id}`}
                    >
                      <ShoppingBag size={12} strokeWidth={1.5} /> Add
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
