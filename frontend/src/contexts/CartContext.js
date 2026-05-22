import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";

const CartContext = createContext(null);
const STORAGE_KEY = "br_cart";

// Cart contents are non-sensitive (no PII, no tokens). sessionStorage clears on browser close,
// reducing surface for cross-tab snooping while preserving in-tab UX.
const readStorage = () => {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
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
