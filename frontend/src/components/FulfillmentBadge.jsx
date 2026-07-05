/**
 * FulfillmentBadge — small pill that tells the buyer how a product ships.
 *
 * Status is derived from product flags (no extra API call):
 *   • foundation (green)  — Printful / Lulu POD via birthright
 *   • partner    (blue)   — off-site vendor handles the order
 *   • artist     (purple) — gallery artwork ships from the artist's studio
 *   • sample     (amber)  — concept only, no fulfillment path yet
 *
 * Sample products should have their Add-to-cart disabled (see `isPurchasable`).
 */
import React from "react";

export function fulfillmentStatus(p) {
  if (!p) return "sample";
  const via = (p.fulfillable_via || "").toLowerCase();
  if (via === "printful" || via === "lulu") return "foundation";
  if (via === "vendor_custom_form") return "custom_vendor";
  if (p.is_off_site && p.vendor_slug) return "partner";
  if (p.is_gallery_artwork) return "artist";
  return "sample";
}

export function isPurchasable(p) {
  return fulfillmentStatus(p) !== "sample";
}

const STYLES = {
  foundation: {
    label: "Ships from birthright",
    cls: "bg-[#E8F0E8] text-[#2F5D32] border-[#2F5D32]/30",
  },
  custom_vendor: {
    label: "Handcrafted by partner",
    cls: "bg-[#E8F0E8] text-[#2F5D32] border-[#2F5D32]/30",
  },
  partner: {
    label: "Direct from partner",
    cls: "bg-[#E6EEF4] text-[#1F3942] border-[#1F3942]/30",
  },
  artist: {
    label: "Direct from artist",
    cls: "bg-[#F0E6F4] text-[#5C2E6B] border-[#5C2E6B]/30",
  },
  sample: {
    label: "Sample · not yet for sale",
    cls: "bg-[#FBF1DC] text-[#7C5316] border-[#7C5316]/30",
  },
};

export default function FulfillmentBadge({ product, size = "sm", labelOverride }) {
  const status = fulfillmentStatus(product);
  const s = STYLES[status];
  const padding = size === "lg" ? "px-3 py-1.5 text-[11px]" : "px-2 py-0.5 text-[10px]";
  let label = labelOverride || s.label;
  if (status === "custom_vendor" && product.vendor_name) {
    label = `Handcrafted by ${product.vendor_name}`;
  } else if (status === "partner" && product.vendor_name) {
    label = `Direct from ${product.vendor_name}`;
  }
  return (
    <span
      className={`inline-flex items-center rounded-full border uppercase tracking-wider font-medium ${padding} ${s.cls}`}
      data-testid={`fulfillment-badge-${status}`}
      title={
        status === "sample"
          ? "Concept image generated for demonstration. We can't ship this yet."
          : undefined
      }
    >
      {label}
    </span>
  );
}
