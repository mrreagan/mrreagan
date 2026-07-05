import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useCart } from "../contexts/CartContext";
import api from "../lib/api";
import { toast } from "sonner";
import { Trash2, ArrowLeft, Truck } from "lucide-react";

function EmptyCart() {
  return (
    <div className="card p-12 text-center mt-8" data-testid="cart-empty">
      <p className="text-[#5C6B6B]">Your cart is empty.</p>
      <Link to="/equip" className="btn-primary mt-6 inline-flex">
        Visit the shop
      </Link>
    </div>
  );
}

function CartItem({ item, onUpdate, onRemove }) {
  const isPod = ["printful", "lulu"].includes(item.fulfillable_via);
  return (
    <div className="card p-5 flex gap-4" data-testid={`cart-item-${item.product_id}`}>
      <img src={item.image_url} alt={item.name} className="w-24 h-24 object-cover rounded-lg" />
      <div className="flex-1">
        <p className="font-serif text-lg">{item.name}</p>
        <p className="text-sm text-[#5C6B6B] mt-1">${item.price.toFixed(2)} each</p>
        {isPod && (
          <p className="text-[10px] uppercase tracking-wider text-[#476B6B] mt-1 inline-flex items-center gap-1">
            <Truck size={11} strokeWidth={1.8} /> Printed on demand · {item.fulfillable_via === "lulu" ? "book / journal" : "apparel & merch"}
          </p>
        )}
        <div className="flex items-center gap-3 mt-3">
          <div className="flex items-center border border-[#E5E1D8] rounded-full overflow-hidden text-sm">
            <button onClick={() => onUpdate(item.product_id, item.quantity - 1)} className="px-3 py-1 hover:bg-[#FAF8F5]">−</button>
            <span className="px-3">{item.quantity}</span>
            <button onClick={() => onUpdate(item.product_id, item.quantity + 1)} className="px-3 py-1 hover:bg-[#FAF8F5]">+</button>
          </div>
          <button onClick={() => onRemove(item.product_id)} className="text-xs text-[#9E3C3C] inline-flex items-center gap-1 hover:underline" data-testid={`cart-remove-${item.product_id}`}>
            <Trash2 size={12} strokeWidth={1.5} /> Remove
          </button>
        </div>
      </div>
      <p className="font-medium">${(item.price * item.quantity).toFixed(2)}</p>
    </div>
  );
}

function ShippingForm({ value, onChange }) {
  const set = (k) => (e) => onChange({ ...value, [k]: e.target.value });
  return (
    <div className="card p-5 space-y-3" data-testid="cart-shipping-form">
      <div className="flex items-center gap-2">
        <Truck size={16} strokeWidth={1.5} className="text-[#476B6B]" />
        <span className="font-serif text-lg">Where should we ship?</span>
      </div>
      <p className="text-xs text-[#5C6B6B] -mt-2">Required for printed items. We pass this directly to the print partner.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B] sm:col-span-2">
          Full name
          <input value={value.name} onChange={set("name")} className="input-field mt-1 text-sm" data-testid="ship-name" />
        </label>
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B] sm:col-span-2">
          Street address
          <input value={value.address1} onChange={set("address1")} placeholder="123 Main St" className="input-field mt-1 text-sm" data-testid="ship-address1" />
        </label>
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B] sm:col-span-2">
          Apt / Suite (optional)
          <input value={value.address2} onChange={set("address2")} className="input-field mt-1 text-sm" data-testid="ship-address2" />
        </label>
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          City
          <input value={value.city} onChange={set("city")} className="input-field mt-1 text-sm" data-testid="ship-city" />
        </label>
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          State (e.g. NC)
          <input value={value.state_code} onChange={set("state_code")} maxLength={3} className="input-field mt-1 text-sm uppercase" data-testid="ship-state" />
        </label>
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          Postal code
          <input value={value.postcode} onChange={set("postcode")} className="input-field mt-1 text-sm" data-testid="ship-postcode" />
        </label>
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B]">
          Country
          <input value={value.country_code} onChange={set("country_code")} maxLength={2} className="input-field mt-1 text-sm uppercase" data-testid="ship-country" />
        </label>
        <label className="text-xs uppercase tracking-wider text-[#5C6B6B] sm:col-span-2">
          Phone (optional, helps couriers)
          <input value={value.phone_number} onChange={set("phone_number")} className="input-field mt-1 text-sm" data-testid="ship-phone" />
        </label>
      </div>
    </div>
  );
}

function CartSummary({ total, onCheckout, onClear, loading, needsShipping, shippingValid }) {
  const disabled = loading || (needsShipping && !shippingValid);
  return (
    <div className="card p-6 h-fit sticky top-24" data-testid="cart-summary">
      <span className="label">Summary</span>
      <div className="mt-4 flex justify-between text-sm">
        <span className="text-[#5C6B6B]">Subtotal</span>
        <span className="font-medium">${total.toFixed(2)}</span>
      </div>
      <div className="mt-2 flex justify-between text-sm">
        <span className="text-[#5C6B6B]">Shipping</span>
        <span className="text-[#5C6B6B]">{needsShipping ? "Per print partner" : "Free"}</span>
      </div>
      <div className="border-t border-[#E5E1D8] mt-4 pt-4 flex justify-between">
        <span className="font-serif text-lg">Total</span>
        <span className="font-serif text-lg">${total.toFixed(2)}</span>
      </div>
      <button onClick={onCheckout} disabled={disabled} className="btn-primary w-full justify-center mt-6" data-testid="cart-checkout-btn">
        {loading ? "Loading..." : "Proceed to checkout"}
      </button>
      {needsShipping && !shippingValid && (
        <p className="text-[10px] text-[#9E3C3C] mt-2 text-center">Complete shipping address to continue</p>
      )}
      <button onClick={onClear} className="btn-ghost w-full mt-2 text-xs">
        Clear cart
      </button>
    </div>
  );
}

export default function Cart() {
  const { items, updateQty, removeItem, total, clear } = useCart();
  const [loading, setLoading] = useState(false);
  const [address, setAddress] = useState({
    name: "", address1: "", address2: "",
    city: "", state_code: "", postcode: "",
    country_code: "US", phone_number: "",
  });

  const needsShipping = useMemo(
    () => items.some((i) => ["printful", "lulu"].includes(i.fulfillable_via)),
    [items],
  );
  const shippingValid =
    address.name.trim() && address.address1.trim() && address.city.trim() &&
    address.state_code.trim().length >= 2 && address.postcode.trim().length >= 3;

  const handleCheckout = async () => {
    setLoading(true);
    try {
      const payload = {
        items: items.map((i) => ({
          product_id: i.product_id,
          quantity: i.quantity,
          attachment_ids: i.attachment_ids || [],
        })),
        origin_url: window.location.origin,
      };
      if (needsShipping) payload.shipping_address = address;
      const { data } = await api.post("/checkout/products", payload);
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Checkout failed");
      setLoading(false);
    }
  };

  return (
    <div className="container-page py-16" data-testid="cart-page">
      <Link to="/equip" className="inline-flex items-center gap-1 text-sm text-[#5C6B6B] hover:text-[#476B6B] mb-6">
        <ArrowLeft size={14} strokeWidth={1.5} /> Continue shopping
      </Link>
      <h1 className="editorial-h1">Your cart</h1>
      <div className="divider-flame" />

      {items.length === 0 ? (
        <EmptyCart />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          <div className="lg:col-span-2 space-y-4" data-testid="cart-items">
            {items.map((i) => (
              <CartItem key={i.product_id} item={i} onUpdate={updateQty} onRemove={removeItem} />
            ))}
            {needsShipping && <ShippingForm value={address} onChange={setAddress} />}
          </div>
          <CartSummary
            total={total}
            onCheckout={handleCheckout}
            onClear={clear}
            loading={loading}
            needsShipping={needsShipping}
            shippingValid={shippingValid}
          />
        </div>
      )}
    </div>
  );
}
