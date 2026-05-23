"""Revenue-share resolution helper.

Resolves the applicable rev-share percentage for a partner at a moment in time.
Order of precedence:
  1. If the partner has an ACTIVE subscription, use its plan's rate.
     - For facilitator plans: `birthright_ip_pct` when presenting Birthright IP,
       otherwise `other_content_pct`.
  2. Else fall back to the global default from `foundation_settings.global_defaults`.
  3. Else 0%.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


async def _active_subscription(db, user_id: str, partner_type: str) -> Optional[dict]:
    now = datetime.now(timezone.utc).isoformat()
    return await db.partner_subscriptions.find_one(
        {
            "user_id": user_id,
            "partner_type": partner_type,
            "status": "active",
            "expires_at": {"$gt": now},
        },
        {"_id": 0},
        sort=[("created_at", -1)],
    )


async def _global_default_pct(db, partner_type: str) -> float:
    doc = await db.foundation_settings.find_one(
        {"key": "global_defaults"}, {"_id": 0, "rev_share": 1}
    )
    if not doc:
        return 0.0
    tiers = (doc.get("rev_share") or {}).get(partner_type) or []
    return float(tiers[0]["pct"]) if tiers else 0.0


async def resolve_rev_share(
    db, user_id: str, partner_type: str, *, presents_birthright_ip: bool = False
) -> dict:
    """Return {pct, source, expires_at?, plan_id?, plan_name?, tier_key?}.

    `source` ∈ {'subscription', 'global_default', 'none'}.
    `tier_key` is 'birthright_ip' or 'other_content' for facilitators, 'default'
    for other partner types.
    """
    sub = await _active_subscription(db, user_id, partner_type)
    if sub:
        plan = await db.subscription_plans.find_one({"id": sub["plan_id"]}, {"_id": 0})
        if plan:
            if partner_type == "facilitator":
                pct = plan.get("birthright_ip_pct") if presents_birthright_ip else plan.get("other_content_pct")
                tier_key = "birthright_ip" if presents_birthright_ip else "other_content"
            else:
                pct = plan.get("default_pct")
                tier_key = "default"
            return {
                "pct": float(pct or 0),
                "source": "subscription",
                "expires_at": sub["expires_at"],
                "plan_id": plan["id"],
                "plan_name": plan["name"],
                "tier_key": tier_key,
                "duration_months": plan["duration_months"],
            }
    # Fallback
    pct = await _global_default_pct(db, partner_type)
    return {
        "pct": pct,
        "source": "global_default" if pct > 0 else "none",
        "expires_at": None,
        "plan_id": None,
        "plan_name": None,
        "tier_key": "default",
        "duration_months": None,
    }
