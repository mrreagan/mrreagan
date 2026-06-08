"""Foundation revenue — POD margin reporting.

Aggregates Printful + Lulu margins from paid orders. For each line item in
an order we join against the product to get fulfillment provider and base
cost, then compute:

  revenue   = sum(line_item.price * line_item.quantity)         per provider
  cost      = sum(product.<provider>_base_cost_usd * quantity)  per provider
  margin    = revenue - cost
  margin_pct = margin / revenue

The endpoint also returns per-provider unit counts and an overall combined
total. Read-only; admin-gated.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Query

from auth_utils import require_roles

logger = logging.getLogger("birthright.foundation_revenue")

admin_router = APIRouter(
    prefix="/admin/foundation",
    tags=["foundation-revenue"],
)


def _provider_for(product: dict) -> Optional[str]:
    """Return 'printful' / 'lulu' / None based on the product's
    fulfillment configuration."""
    f = (product or {}).get("fulfillable_via")
    if f in ("printful", "lulu"):
        return f
    return None


def _base_cost_for(product: dict) -> float:
    """Pull the stored POD wholesale cost for the product's provider.
    Returns 0.0 if missing (item is treated as 100% margin, flagged)."""
    p = _provider_for(product)
    if p == "printful":
        return float(product.get("printful_base_cost_usd") or 0.0)
    if p == "lulu":
        return float(product.get("lulu_base_cost_usd") or 0.0)
    return 0.0


@admin_router.get("/revenue/pod-margin")
async def pod_margin_summary(
    days: int = Query(default=0, ge=0, le=3650,
                       description="If > 0, only orders from the last N days"),
    user: dict = Depends(require_roles("admin")),
) -> Dict:
    """Aggregate Printful + Lulu margin across all paid orders.

    Returns a structure that's drop-in for a small dashboard tile:

        {
          "printful": { revenue, cost, margin, margin_pct, units, sku_count },
          "lulu":     { revenue, cost, margin, margin_pct, units, sku_count },
          "combined": { revenue, cost, margin, margin_pct, units },
          "missing_cost_skus": ["sku-a", "sku-b"],   # data hygiene flag
          "window_days": <days>,
          "order_count": <int>,
        }
    """
    from database import db
    query: Dict = {"status": "paid"}
    if days > 0:
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query["created_at"] = {"$gte": cutoff}

    orders = await db.orders.find(query, {"_id": 0, "items": 1}).to_list(50_000)

    # Build a set of product_ids we actually need to fetch.
    product_ids = {
        li.get("product_id")
        for o in orders
        for li in (o.get("items") or [])
        if li.get("product_id")
    }
    products = await db.products.find(
        {"id": {"$in": list(product_ids)}},
        {"_id": 0, "id": 1, "name": 1, "fulfillable_via": 1,
         "printful_base_cost_usd": 1, "lulu_base_cost_usd": 1},
    ).to_list(len(product_ids) + 1)
    by_id = {p["id"]: p for p in products}

    agg: Dict[str, Dict] = {
        "printful": {"revenue": 0.0, "cost": 0.0, "units": 0,
                     "sku_ids": set()},
        "lulu":     {"revenue": 0.0, "cost": 0.0, "units": 0,
                     "sku_ids": set()},
    }
    missing_cost: set = set()

    for o in orders:
        for li in o.get("items") or []:
            pid = li.get("product_id")
            prod = by_id.get(pid)
            if not prod:
                continue
            provider = _provider_for(prod)
            if not provider:
                continue
            qty = int(li.get("quantity") or 0)
            unit_price = float(li.get("price") or 0.0)
            base_cost = _base_cost_for(prod)
            if base_cost <= 0:
                missing_cost.add(prod.get("name") or pid)

            agg[provider]["revenue"] += unit_price * qty
            agg[provider]["cost"] += base_cost * qty
            agg[provider]["units"] += qty
            agg[provider]["sku_ids"].add(pid)

    def _finalize(bucket: Dict) -> Dict:
        rev = round(bucket["revenue"], 2)
        cost = round(bucket["cost"], 2)
        margin = round(rev - cost, 2)
        pct = round((margin / rev) * 100, 1) if rev else 0.0
        return {
            "revenue": rev,
            "cost": cost,
            "margin": margin,
            "margin_pct": pct,
            "units": bucket["units"],
            "sku_count": len(bucket["sku_ids"]),
        }

    printful = _finalize(agg["printful"])
    lulu = _finalize(agg["lulu"])
    combined_rev = round(printful["revenue"] + lulu["revenue"], 2)
    combined_cost = round(printful["cost"] + lulu["cost"], 2)
    combined_margin = round(combined_rev - combined_cost, 2)
    combined_pct = round((combined_margin / combined_rev) * 100, 1) \
        if combined_rev else 0.0

    return {
        "printful": printful,
        "lulu": lulu,
        "combined": {
            "revenue": combined_rev,
            "cost": combined_cost,
            "margin": combined_margin,
            "margin_pct": combined_pct,
            "units": printful["units"] + lulu["units"],
        },
        "missing_cost_skus": sorted(missing_cost),
        "window_days": days,
        "order_count": len(orders),
    }
