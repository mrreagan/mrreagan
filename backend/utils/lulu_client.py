"""Lulu Direct Print API client (Phase 5 — Admin "Make fulfillable on Lulu").

Lulu's API is stateless — unlike Printful, there are no "sync products". Every
print job carries its own pod_package_id + PDF URLs. So "Make fulfillable" on
our side is purely about recording config + base cost on our product doc.

This module wraps:
  - OAuth2 client-credentials token fetch (OIDC realm: glasstree)
  - Token caching with safety margin
  - /print-job-cost-calculations/   → cost preview
  - /print-jobs/                    → create a real (or sandbox) print job
  - GET /print-jobs/{id}/           → status lookup

Env: LULU_ENV=sandbox|production decides which credentials + base URL we use.
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from httpx import BasicAuth

logger = logging.getLogger("birthright.lulu")

TIMEOUT_S = 20.0
TOKEN_SAFETY_MARGIN_S = 30


class LuluError(Exception):
    """Raised when Lulu returns a non-2xx response or env is mis-configured."""


def _env() -> str:
    return (os.environ.get("LULU_ENV") or "sandbox").strip().lower()


def get_base_url() -> str:
    return "https://api.sandbox.lulu.com" if _env() == "sandbox" else "https://api.lulu.com"


def _credentials() -> tuple[str, str]:
    prefix = "LULU_SANDBOX" if _env() == "sandbox" else "LULU_PRODUCTION"
    cid = (os.environ.get(f"{prefix}_CLIENT_ID") or "").strip()
    sec = (os.environ.get(f"{prefix}_CLIENT_SECRET") or "").strip()
    if not cid or not sec:
        raise LuluError(f"{prefix}_CLIENT_ID / {prefix}_CLIENT_SECRET not configured")
    return cid, sec


# ============ Token manager ============
class _TokenManager:
    def __init__(self) -> None:
        self._tokens: dict[str, dict[str, float | str]] = {}  # keyed by env
        self._lock = asyncio.Lock()

    async def get(self) -> str:
        env = _env()
        cached = self._tokens.get(env)
        now = time.time()
        if cached and now < float(cached["expires_at"]) - TOKEN_SAFETY_MARGIN_S:
            return str(cached["access_token"])
        async with self._lock:
            cached = self._tokens.get(env)
            now = time.time()
            if cached and now < float(cached["expires_at"]) - TOKEN_SAFETY_MARGIN_S:
                return str(cached["access_token"])
            cid, sec = _credentials()
            url = f"{get_base_url()}/auth/realms/glasstree/protocol/openid-connect/token"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url, auth=BasicAuth(cid, sec),
                    data={"grant_type": "client_credentials"},
                )
            if resp.status_code >= 400:
                raise LuluError(f"Lulu auth failed: {resp.status_code} {resp.text[:200]}")
            payload = resp.json()
            self._tokens[env] = {
                "access_token": payload["access_token"],
                "expires_at": now + int(payload.get("expires_in", 3600)),
            }
            logger.info("lulu: fetched new %s token (expires in %ss)", env, payload.get("expires_in"))
            return str(self._tokens[env]["access_token"])


_token_manager = _TokenManager()


# ============ Core request ============
async def _request(method: str, path: str, *, json_body: Optional[dict] = None) -> Any:
    token = await _token_manager.get()
    url = f"{get_base_url()}{path}"
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        resp = await client.request(
            method, url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=json_body,
        )
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}
        logger.error("Lulu %s %s → %s | %s", method, path, resp.status_code, body)
        raise LuluError(f"Lulu {resp.status_code}: {body}")
    if not resp.content:
        return None
    return resp.json()


# ============ Public API ============
US_TEST_ADDRESS: Dict[str, Any] = {
    "name": "Birthright Estimator",
    "street1": "100 Mission St",
    "city": "Asheville",
    "state_code": "NC",
    "postcode": "28801",
    "country_code": "US",
    "phone_number": "555-555-5555",
}


async def calculate_cost(
    *,
    pod_package_id: str,
    page_count: int,
    quantity: int = 1,
    shipping_address: Optional[Dict[str, Any]] = None,
    shipping_option: str = "MAIL",
) -> Dict[str, Any]:
    """Hit /print-job-cost-calculations/. Returns the raw Lulu response."""
    payload = {
        "line_items": [{
            "pod_package_id": pod_package_id,
            "page_count": int(page_count),
            "quantity": int(quantity),
        }],
        "shipping_address": shipping_address or US_TEST_ADDRESS,
        "shipping_option": shipping_option,
    }
    return await _request("POST", "/print-job-cost-calculations/", json_body=payload)


async def create_print_job(
    *,
    contact_email: str,
    external_id: str,
    pod_package_id: str,
    page_count: int,
    title: str,
    cover_url: str,
    interior_url: str,
    shipping_address: Dict[str, Any],
    shipping_option: str = "MAIL",
    quantity: int = 1,
    production_delay_minutes: Optional[int] = 60,
) -> Dict[str, Any]:
    """Create a real print job (sandbox = no real production)."""
    payload: Dict[str, Any] = {
        "contact_email": contact_email,
        "external_id": str(external_id)[:60],
        "shipping_address": shipping_address,
        "shipping_level": shipping_option,
        "line_items": [{
            "external_id": f"{external_id}-1"[:60],
            "printable_normalization": {
                "cover": {"source_url": cover_url},
                "interior": {"source_url": interior_url},
                "pod_package_id": pod_package_id,
            },
            "quantity": int(quantity),
            "title": title[:200],
        }],
    }
    if production_delay_minutes is not None:
        payload["production_delay"] = int(production_delay_minutes)
    return await _request("POST", "/print-jobs/", json_body=payload)


async def get_print_job(print_job_id: int) -> Dict[str, Any]:
    return await _request("GET", f"/print-jobs/{int(print_job_id)}/")


# ============ Webhook subscriptions (admin-side; lives on Lulu, not on us) ============
WEBHOOK_TOPICS = ["PRINT_JOB_STATUS_CHANGED"]


async def create_webhook(*, url: str, topics: Optional[List[str]] = None) -> Dict[str, Any]:
    """Subscribe to Lulu webhooks. Returns the created subscription resource."""
    return await _request(
        "POST", "/webhooks/",
        json_body={"url": url, "topics": topics or WEBHOOK_TOPICS, "is_active": True},
    )


async def list_webhooks() -> List[Dict[str, Any]]:
    """List current Lulu webhook subscriptions on this account."""
    raw = await _request("GET", "/webhooks/")
    # Lulu returns a paginated envelope: {"count": N, "results": [...]}.
    # Newer endpoints return a bare list. Handle both.
    if isinstance(raw, dict):
        return list(raw.get("results") or [])
    return list(raw or [])


async def delete_webhook(webhook_id: str) -> None:
    await _request("DELETE", f"/webhooks/{webhook_id}/")


async def send_webhook_test(webhook_id: str, topic: str = "PRINT_JOB_STATUS_CHANGED") -> Dict[str, Any]:
    """Lulu /webhooks/{id}/test/ — sends a dummy payload to our endpoint."""
    return await _request(
        "POST", f"/webhooks/{webhook_id}/test/",
        json_body={"topic": topic},
    )


# ============ Pricing helpers ============
def summarise_cost(raw: Dict[str, Any]) -> Dict[str, float]:
    """Pull the dollar fields we care about out of Lulu's cost-calc response."""
    line_items = raw.get("line_item_costs") or []
    line_cost_excl_tax = sum(float(li.get("total_cost_excl_tax", 0)) for li in line_items)
    shipping = float((raw.get("shipping_cost") or {}).get("total_cost_excl_tax", 0))
    fulfillment = float((raw.get("fulfillment_cost") or {}).get("total_cost_excl_tax", 0))
    tax = float(raw.get("total_tax", 0))
    total_incl_tax = float(raw.get("total_cost_incl_tax", 0))
    return {
        "line_cost_usd": round(line_cost_excl_tax, 2),
        "shipping_cost_usd": round(shipping, 2),
        "fulfillment_cost_usd": round(fulfillment, 2),
        "tax_usd": round(tax, 2),
        "total_cost_usd": round(total_incl_tax, 2),
        "base_cost_excl_tax_usd": round(line_cost_excl_tax + shipping + fulfillment, 2),
    }


def suggest_retail_price(base_cost_usd: float, multiplier: float = 2.0) -> float:
    """2× base cost rounded up to next $.95 — same approach as Printful Phase 2."""
    if base_cost_usd <= 0:
        return 0.0
    raw = base_cost_usd * multiplier
    whole = math.floor(raw)
    cand = whole + 0.95
    if cand < raw:
        cand = whole + 1.95
    return round(cand, 2)
