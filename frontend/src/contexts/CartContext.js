import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";

const CartContext = createContext(null);
const STORAGE_KEY = "br_cart";

// Cart contents are non-sensitive (no PII, no auth tokens) — just product references and quantities.
// We sanitize on read to reject any unexpected fields that could leak via XSS.
const ALLOWED_FIELDS = ["product_id", "name", "price", "image_url", "quantity", "max_per_order", "fulfillable_via"];

const sanitizeItem = (raw) => {
  if (!raw || typeof raw !== "object") return null;
  const item = {};
  for (const key of ALLOWED_FIELDS) {
    item[key] = raw[key];
  }
  if (typeof item.product_id !== "string" || !item.product_id) return null;
  if (typeof item.name !== "string") item.name = String(item.name || "");
  item.price = Number(item.price) || 0;
  item.quantity = Math.max(1, parseInt(item.quantity, 10) || 1);
  item.image_url = typeof item.image_url === "string" ? item.image_url : "";
  item.max_per_order = Number.isFinite(item.max_per_order) ? item.max_per_order : null;
  item.fulfillable_via = typeof item.fulfillable_via === "string" ? item.fulfillable_via : null;
  return item;
};

const readStorage = () => {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    const parsed = stored ? JSON.parse(stored) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.map(sanitizeItem).filter(Boolean);
  } catch {
    return [];
  }
};

export function CartProvider({ children }) {
  const [items, setItems] = useState(readStorage);

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items]);

  const addItem = useCallback((product, quantity = 1) => {
    let toastReason = null;
    setItems((prev) => {
      const existing = prev.find((p) => p.product_id === product.id);
      const cap = Number.isFinite(product.max_per_order) ? product.max_per_order : null;
      const currentQty = existing ? existing.quantity : 0;
      let newQty = currentQty + quantity;
      if (cap && newQty > cap) {
        newQty = cap;
        toastReason = `Limited to ${cap} per order — already in cart.`;
        if (currentQty >= cap) return prev; // nothing to change
      }
      if (existing) {
        return prev.map((p) =>
          p.product_id === product.id ? { ...p, quantity: newQty } : p
        );
      }
      return [
        ...prev,
        {
          product_id: product.id,
          name: product.name,
          price: product.price,
          image_url: product.image_url,
          quantity: newQty,
          max_per_order: cap,
          fulfillable_via: product.fulfillable_via || null,
        },
      ];
    });
    if (toastReason) {
      // toast lives in sonner; we lazy-require here to avoid a cyclic import.
      // Best-effort — silently ignored if sonner isn't loaded.
      import("sonner").then((m) => m.toast?.message(toastReason)).catch(() => {});
    }
  }, []);

  const updateQty = useCallback((product_id, quantity) => {
    setItems((prev) =>
      quantity <= 0
        ? prev.filter((p) => p.product_id !== product_id)
        : prev.map((p) => {
            if (p.product_id !== product_id) return p;
            const cap = Number.isFinite(p.max_per_order) ? p.max_per_order : null;
            return { ...p, quantity: cap ? Math.min(quantity, cap) : quantity };
          })
    );
  }, []);

  const removeItem = useCallback((product_id) => {
    setItems((prev) => prev.filter((p) => p.product_id !== product_id));
  }, []);

  const clear = useCallback(() => setItems([]), []);

  // Split into 2 memos to keep dep counts low
  const totals = useMemo(
    () => ({
      total: items.reduce((sum, i) => sum + i.price * i.quantity, 0),
      count: items.reduce((sum, i) => sum + i.quantity, 0),
    }),
    [items]
  );
  const actions = useMemo(
    () => ({ addItem, updateQty, removeItem, clear }),
    [addItem, updateQty, removeItem, clear]
  );
  const value = useMemo(
    () => ({ items, ...totals, ...actions }),
    [items, totals, actions]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export const useCart = () => useContext(CartContext);
