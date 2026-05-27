import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { ShopFilters, ProductGrid } from "../components/shop/ShopParts";
import FounderCollectionRail from "../components/shop/FounderCollectionRail";

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

  // Founder Collection only renders on the public-merch view. Workshop materials
  // and "all" filters keep the existing untouched grid.
  const showFounderRail = filter === "merch" || filter === "all";
  const founderItems = showFounderRail
    ? products.filter((p) => p.collection === "founder_collection")
    : [];
  const restItems = showFounderRail
    ? products.filter((p) => p.collection !== "founder_collection")
    : products;

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

      {/* Featured Founder Collection rail — anchored so it can be linked directly */}
      <div id="founder-collection" />
      {founderItems.length > 0 && <FounderCollectionRail products={founderItems} />}

      <ShopFilters active={filter} onChange={setFilter} />
      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-12">Loading...</p>
      ) : (
        <ProductGrid products={restItems} />
      )}
    </div>
  );
}
