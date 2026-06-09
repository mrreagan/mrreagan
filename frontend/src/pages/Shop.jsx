/* eslint-disable */
import React, { useEffect, useMemo, useState } from "react";
import api from "../lib/api";
import { ShopFilters, ShopSourceFilters, ProductGrid } from "../components/shop/ShopParts";
import FounderCollectionRail from "../components/shop/FounderCollectionRail";

export default function Shop() {
  const [products, setProducts] = useState([]);
  const [filter, setFilter] = useState("merch");
  const [source, setSource] = useState("any");          // any | foundation | vendor
  const [vendor, setVendor] = useState("all");           // slug | name | "all"
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = filter === "all" ? "" : `?type=${filter}`;
    api
      .get(`/products${params}`)
      .then((r) => setProducts(r.data))
      .finally(() => setLoading(false));
  }, [filter]);

  // Reset vendor selection whenever source switches away from "vendor".
  useEffect(() => { if (source !== "vendor") setVendor("all"); }, [source]);

  // Distinct vendors derived from the current product set. Only shown when
  // the user filters by "Vendor partners" so the dropdown stays compact.
  const vendors = useMemo(() => {
    const map = new Map();
    products.forEach((p) => {
      if (p.is_vendor_product && p.vendor_name) {
        const key = p.vendor_slug || p.vendor_name;
        if (!map.has(key)) map.set(key, { slug: p.vendor_slug, name: p.vendor_name });
      }
    });
    return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
  }, [products]);

  // Apply the new source / vendor filters on top of the type filter.
  const sourceFiltered = useMemo(() => {
    let rows = products;
    if (source === "foundation") rows = rows.filter((p) => !p.is_vendor_product);
    else if (source === "vendor") rows = rows.filter((p) => p.is_vendor_product);
    if (source === "vendor" && vendor !== "all") {
      rows = rows.filter((p) => (p.vendor_slug || p.vendor_name) === vendor);
    }
    return rows;
  }, [products, source, vendor]);

  // Founder Collection only renders on the public-merch view AND when not
  // filtered down to vendor-only items (the rail is Foundation-curated).
  const showFounderRail = (filter === "merch" || filter === "all") && source !== "vendor";
  // Sort founder items by created_at desc so the most recently curated
  // pieces surface first. The patches series was backdated to 2026-03-01
  // intentionally so it leads the rail.
  const founderItems = showFounderRail
    ? sourceFiltered
        .filter((p) => p.collection === "founder_collection")
        .slice()
        .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")))
    : [];
  const restItems = showFounderRail
    ? sourceFiltered.filter((p) => p.collection !== "founder_collection")
    : sourceFiltered;

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
      <ShopSourceFilters
        source={source}
        onSourceChange={setSource}
        vendor={vendor}
        onVendorChange={setVendor}
        vendors={vendors}
      />
      {loading ? (
        <p className="text-sm text-[#5C6B6B] mt-12">Loading...</p>
      ) : (
        <>
          {restItems.length === 0 && (
            <p className="text-sm text-[#5C6B6B] italic mt-12" data-testid="shop-empty-filtered">
              No products match these filters. Try a different source or type.
            </p>
          )}
          {restItems.length > 0 && <ProductGrid products={restItems} />}
        </>
      )}
    </div>
  );
}
