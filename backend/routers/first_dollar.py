"""First-Dollar Wall — public social-proof feed of first purchases.

For each user, exposes their FIRST paid order (min created_at) with a
minimally-identifying display name (first name + last initial) so early
supporters see their impact land as a marquee on the homepage without
leaking PII. Public — no auth required.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from models import now_iso  # noqa: F401  (kept for parity with sibling routers)

logger = logging.getLogger("birthright.first_dollar")
router = APIRouter(prefix="/first-dollar", tags=["first-dollar"])


def _display_name(u: Optional[dict]) -> str:
    if not u:
        return "A new supporter"
    first = (u.get("first_name") or "").strip()
    last = (u.get("last_name") or "").strip()
    if first and last:
        return f"{first} {last[0]}."
    if first:
        return first
    email = u.get("email") or ""
    return email.split("@")[0][:24] or "A new supporter"


def _item_label(items: list) -> str:
    if not items:
        return "Birthright Foundation"
    first = items[0] or {}
    # Order items store either a `name` or `title` key depending on
    # whether they came from the storefront or workshop registration path.
    return (
        first.get("name")
        or first.get("title")
        or first.get("product_name")
        or "Birthright Foundation"
    )


@router.get("/recent")
async def first_dollar_recent(limit: int = Query(default=12, ge=1, le=50)):
    """Return the most recent N first-time supporters.

    A "first-time" order is a user's earliest `status == 'paid'` order.
    Returns a list of `{display_name, item_label, at, amount_cents}`
    entries sorted newest-first. Redacted to first-name + last-initial;
    guest orders (no `user_id`) fall back to a generic label. No IP, no
    email, no address ever crosses this boundary.
    """
    from database import db

    # Pull a small window of recent paid orders and, for each one, check
    # if it's the user's first. Window is `limit * 4` so we can survive
    # some repeat-buyers without a second query.
    window = max(limit * 4, 40)
    recent_cursor = db.orders.find(
        {"status": "paid"},
        {"_id": 0, "id": 1, "user_id": 1, "items": 1, "total": 1, "created_at": 1},
    ).sort("created_at", -1).limit(window)

    firsts: list[dict] = []
    seen_users: set[str] = set()
    async for order in recent_cursor:
        uid = order.get("user_id")
        # Only track FIRST purchase per user. If we've already emitted
        # for this user in the window, skip.
        if uid and uid in seen_users:
            continue
        if uid:
            # Confirm this really is the user's earliest paid order.
            earlier = await db.orders.find_one(
                {"user_id": uid, "status": "paid",
                 "created_at": {"$lt": order.get("created_at")}},
                {"_id": 0, "id": 1},
            )
            if earlier:
                continue  # not their first — skip
            seen_users.add(uid)
            u = await db.users.find_one(
                {"id": uid},
                {"_id": 0, "first_name": 1, "last_name": 1, "email": 1},
            )
        else:
            u = None
        firsts.append({
            "display_name": _display_name(u),
            "item_label": _item_label(order.get("items") or []),
            "at": order.get("created_at"),
            "amount_cents": int(order.get("total") or 0),
        })
        if len(firsts) >= limit:
            break
    return firsts
