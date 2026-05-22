import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShoppingBag } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";
import { useCart } from "../../contexts/CartContext";

function MaterialCard({ product, onAdd }) {
  return (
    <div className="card overflow-hidden" data-testid={`material-${product.id}`}>
      <div className="aspect-square bg-[#E5E1D8]">
        <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
      </div>
      <div className="p-5">
        <p className="font-serif text-lg">{product.name}</p>
        <p className="text-xs text-[#5C6B6B] mt-1 line-clamp-2">{product.description}</p>
        <div className="mt-4 flex items-center justify-between">
          <span className="font-medium">${product.price?.toFixed(2)}</span>
          <button
            onClick={() => {
              onAdd(product);
              toast.success("Added");
            }}
            className="text-xs flex items-center gap-1.5 bg-[#476B6B] text-white px-3 py-1.5 rounded-full hover:bg-[#3A5858] transition"
            data-testid={`material-add-${product.id}`}
          >
            <ShoppingBag size={12} strokeWidth={1.5} /> Add
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MaterialsTab({ workshop }) {
  const [products, setProducts] = useState([]);
  const { addItem } = useCart();

  useEffect(() => {
    api
      .get(`/products?workshop_id=${workshop.id}&type=workshop_material`)
      .then((r) => setProducts(r.data))
      .catch((err) => console.error("Materials load failed:", err?.message || err));
  }, [workshop.id]);

  return (
    <div data-testid="tab-materials">
      <p className="text-sm text-[#5C6B6B] mb-5">
        These materials are reserved for participants of this workshop.
      </p>
      {products.length === 0 ? (
        <div className="card p-10 text-center text-sm text-[#5C6B6B]">No materials available yet.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {products.map((p) => <MaterialCard key={p.id} product={p} onAdd={addItem} />)}
        </div>
      )}
      <p className="text-xs text-[#5C6B6B] mt-6">
        Items go to your <Link to="/cart" className="text-[#476B6B] hover:underline">cart</Link>.
      </p>
    </div>
  );
}
