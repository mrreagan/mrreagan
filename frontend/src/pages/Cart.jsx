import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useCart } from "../contexts/CartContext";
import api from "../lib/api";
import { toast } from "sonner";
import { Trash2, ArrowLeft } from "lucide-react";

export default function Cart() {
  const { items, updateQty, removeItem, total, clear } = useCart();
  const [loading, setLoading] = useState(false);

  const checkout = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/checkout/products", {
        items: items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
        origin_url: window.location.origin,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Checkout failed");
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-16" data-testid="cart-page">
      <Link to="/shop" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Continue shopping
      </Link>
      <h1 className="editorial-h1">Your cart</h1>
      <div className="divider-flame" />

      {items.length === 0 ? (
        <div className="card p-12 text-center mt-8" data-testid="cart-empty">
          <p className="text-[#5C6B6B]">Your cart is empty.</p>
          <Link to="/shop" className="btn-primary mt-6 inline-flex">Visit the shop</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          <div className="lg:col-span-2 space-y-4" data-testid="cart-items">
            {items.map((i) => (
              <div key={i.product_id} className="card p-5 flex gap-4" data-testid={`cart-item-${i.product_id}`}>
                <img src={i.image_url} alt={i.name} className="w-24 h-24 object-cover rounded-lg" />
                <div className="flex-1">
                  <p className="font-serif text-lg">{i.name}</p>
                  <p className="text-sm text-[#5C6B6B] mt-1">${i.price.toFixed(2)} each</p>
                  <div className="flex items-center gap-3 mt-3">
                    <div className="flex items-center border border-[#E5E1D8] rounded-full overflow-hidden text-sm">
                      <button onClick={() => updateQty(i.product_id, i.quantity - 1)} className="px-3 py-1 hover:bg-[#FAF8F5]">−</button>
                      <span className="px-3">{i.quantity}</span>
                      <button onClick={() => updateQty(i.product_id, i.quantity + 1)} className="px-3 py-1 hover:bg-[#FAF8F5]">+</button>
                    </div>
                    <button onClick={() => removeItem(i.product_id)} className="text-xs text-[#9E3C3C] inline-flex items-center gap-1 hover:underline" data-testid={`cart-remove-${i.product_id}`}>
                      <Trash2 size={12} strokeWidth={1.5} /> Remove
                    </button>
                  </div>
                </div>
                <p className="font-medium">${(i.price * i.quantity).toFixed(2)}</p>
              </div>
            ))}
          </div>
          <div className="card p-6 h-fit sticky top-24" data-testid="cart-summary">
            <span className="label">Summary</span>
            <div className="mt-4 flex justify-between text-sm">
              <span className="text-[#5C6B6B]">Subtotal</span>
              <span className="font-medium">${total.toFixed(2)}</span>
            </div>
            <div className="mt-2 flex justify-between text-sm">
              <span className="text-[#5C6B6B]">Shipping</span>
              <span className="text-[#5C6B6B]">Calculated at next step</span>
            </div>
            <div className="border-t border-[#E5E1D8] mt-4 pt-4 flex justify-between">
              <span className="font-serif text-lg">Total</span>
              <span className="font-serif text-lg">${total.toFixed(2)}</span>
            </div>
            <button onClick={checkout} disabled={loading} className="btn-primary w-full justify-center mt-6" data-testid="cart-checkout-btn">
              {loading ? "Loading..." : "Proceed to checkout"}
            </button>
            <button onClick={clear} className="btn-ghost w-full mt-2 text-xs">Clear cart</button>
          </div>
        </div>
      )}
    </div>
  );
}
