"""Printful API client (Phase 2 — Admin "Make fulfillable" on AI Studio drafts).

Wraps the v1 endpoints we actually need:
  - GET  /products/{id}           — base-product detail (cost discovery)
  - POST /store/products          — create sync product with one variant + file URL

Token is a single-store private token, set via PRINTFUL_API_TOKEN.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("birthright.printful")

PRINTFUL_BASE = "https://api.printful.com"
TIMEOUT_S = 30.0


class PrintfulError(Exception):
    """Raised when Printful returns a non-2xx response."""


def get_token() -> str:
    tok = os.environ.get("PRINTFUL_API_TOKEN", "").strip()
    if not tok:
        raise PrintfulError("PRINTFUL_API_TOKEN is not configured")
    return tok


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, *, json: Optional[dict] = None) -> Any:
    url = f"{PRINTFUL_BASE}{path}"
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        resp = await client.request(method, url, headers=_headers(), json=json)
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}
        logger.error("Printful %s %s → %s | %s", method, path, resp.status_code, body)
        msg = (body.get("result") or body.get("error", {}).get("message") or resp.text[:200])
        raise PrintfulError(f"Printful {resp.status_code}: {msg}")
    return resp.json().get("result")


# ============ Catalog discovery ============

async def get_product_detail(product_id: int) -> Dict[str, Any]:
    """Return {product, variants[]} for a base catalog product."""
    return await _request("GET", f"/products/{product_id}")


async def get_variant_price(product_id: int, variant_id: int) -> Optional[float]:
    """Look up the base cost (USD) for a single variant. Best-effort."""
    try:
        data = await get_product_detail(product_id)
        for v in (data or {}).get("variants", []) or []:
            if int(v.get("id", 0)) == int(variant_id):
                return float(v.get("price") or 0.0)
    except Exception as exc:
        logger.warning("Printful variant price lookup failed: %s", exc)
    return None


# ============ Sync product creation ============

async def create_sync_product(
    *,
    name: str,
    variant_id: int,
    file_url: str,
    retail_price: Optional[str] = None,
    external_id: Optional[str] = None,
    thread_colors: Optional[List[str]] = None,
    embroidery_placement: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a sync product with ONE variant + ONE print file (front).

    For embroidered products (e.g. Yupoong 6606 caps):
      - file.type = embroidery_placement (e.g. "embroidery_front")
      - variant.options = [embroidery_type=flat, thread_colors=[...hex]]
    For printed products (tees/hoodies/mugs): file.url is enough.
    """
    sync_product: Dict[str, Any] = {"name": name[:200]}
    if external_id:
        sync_product["external_id"] = str(external_id)[:60]

    file_spec: Dict[str, Any] = {"url": file_url}
    if embroidery_placement:
        file_spec["type"] = embroidery_placement

    sync_variant: Dict[str, Any] = {
        "variant_id": int(variant_id),
        "files": [file_spec],
    }
    if thread_colors and embroidery_placement:
        sync_variant["options"] = [
            {"id": "embroidery_type", "value": "flat"},
            {"id": "thread_colors", "value": list(thread_colors)},
        ]
    if retail_price is not None:
        sync_variant["retail_price"] = f"{float(retail_price):.2f}"
    if external_id:
        sync_variant["external_id"] = f"{external_id}-v1"[:60]

    payload = {"sync_product": sync_product, "sync_variants": [sync_variant]}
    return await _request("POST", "/store/products", json=payload)


async def get_sync_product(sync_product_id: int) -> Dict[str, Any]:
    return await _request("GET", f"/store/products/{sync_product_id}")


async def delete_sync_product(sync_product_id: int) -> None:
    await _request("DELETE", f"/store/products/{sync_product_id}")


# ============ Pricing helper ============

def suggest_retail_price(base_cost_usd: float, multiplier: float = 2.0) -> float:
    """2× base cost, rounded up to next $.95. e.g. $13.29 → $26.95, $5.95 → $11.95."""
    if base_cost_usd <= 0:
        return 0.0
    raw = base_cost_usd * multiplier
    # Round up to next $.95 — feels intentional, never .99 (less aggressive).
    import math
    whole = math.floor(raw)
    cand = whole + 0.95
    if cand < raw:
        cand = whole + 1.95
    return round(cand, 2)
