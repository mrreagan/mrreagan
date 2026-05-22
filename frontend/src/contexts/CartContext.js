import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";

const CartContext = createContext(null);
const STORAGE_KEY = "br_cart";

// Cart contents are non-sensitive (no PII, no auth tokens) — just product references and quantities.
// We sanitize on read to reject any unexpected fields that could leak via XSS.
const ALLOWED_FIELDS = ["product_id", "name", "price", "image_url", "quantity"];

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
    setItems((prev) => {
      const existing = prev.find((p) => p.product_id === product.id);
      if (existing) {
        return prev.map((p) =>
          p.product_id === product.id ? { ...p, quantity: p.quantity + quantity } : p
        );
      }
      return [
        ...prev,
        {
          product_id: product.id,
          name: product.name,
          price: product.price,
          image_url: product.image_url,
          quantity,
        },
      ];
    });
  }, []);

  const updateQty = useCallback((product_id, quantity) => {
    setItems((prev) =>
      quantity <= 0
        ? prev.filter((p) => p.product_id !== product_id)
        : prev.map((p) => (p.product_id === product_id ? { ...p, quantity } : p))
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
