import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { ShopFilters, ProductGrid } from "../components/shop/ShopParts";

export default function Shop() {
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState("merch");
  const [loading, setLoading] = useState(true);

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
      <ShopFilters active={filter} onChange={setFilter} />
      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-12">Loading...</p>
      ) : (
        <ProductGrid products={products} />
      )}
    </div>
  );
}
