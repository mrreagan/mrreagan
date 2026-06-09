"""Artist tier resolver — community-of-interest progressive rate model.

Resolves an artist's referral tier from their trailing-12-month
*Birthright-attributed gross revenue*:

  basis = (patronage on-site sales at list price)
        + (off-site sales self-reported as via=birthright)

The five tiers (gentler than vendor terms by design):

  🌱 Emerging       $0       – $5,000     inbound 10%   outbound  0%
  🌿 Sustaining     $5,001   – $15,000    inbound  8%   outbound  2%
  🌳 Established    $15,001  – $40,000    inbound  6%   outbound  4%
  🌸 Thriving       $40,001  – $100,000   inbound  5%   outbound  6%
  🌟 Flourishing    $100,001+             inbound  5%   outbound  8%

Outbound (Foundation collects from artist's off-site referred sales)
uses MARGINAL brackets, like progressive tax — only revenue above each
threshold pays that tier's rate.

Inbound (artist earns from sending buyers to Birthright) uses a flat
lookup of the artist's current tier.

Tier transitions take effect the 1st of the following month for
predictability; a row in `db.artist_tier_history` records each change.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from models import gen_id, now_iso


# Bracket lower-edges; each tier owns revenue >= lo and <= hi.
# (hi=None means "+infinity")
TIERS: List[Dict] = [
    {"key": "emerging",   "label": "Emerging",     "icon": "🌱",
     "lo": 0,       "hi": 5_000,    "inbound_pct": 10.0, "outbound_pct": 0.0},
    {"key": "sustaining", "label": "Sustaining",   "icon": "🌿",
     "lo": 5_001,   "hi": 15_000,   "inbound_pct":  8.0, "outbound_pct": 2.0},
    {"key": "established","label": "Established",  "icon": "🌳",
     "lo": 15_001,  "hi": 40_000,   "inbound_pct":  6.0, "outbound_pct": 4.0},
    {"key": "thriving",   "label": "Thriving",     "icon": "🌸",
     "lo": 40_001,  "hi": 100_000,  "inbound_pct":  5.0, "outbound_pct": 6.0},
    {"key": "flourishing","label": "Flourishing",  "icon": "🌟",
     "lo": 100_001, "hi": None,     "inbound_pct":  5.0, "outbound_pct": 8.0},
]

# Cheap ordinal index for direction (up vs down) detection in tier history.
TIER_ORDER = [t["key"] for t in TIERS]


def tier_for_basis(basis: float) -> dict:
    """Return the tier dict whose [lo, hi] bracket the basis falls into."""
    for t in TIERS:
        if t["hi"] is None or basis <= t["hi"]:
            if basis >= t["lo"]:
                return t
    return TIERS[0]


def marginal_outbound_owed(basis: float) -> float:
    """Compute the Foundation's marginal outbound take across all tiers.

    Each bracket's rate applies ONLY to the revenue within that bracket.
    Example: basis=$20,000 →
        $0–5K at 0%   = $0
        $5,001–15K at 2% = $200
        $15,001–20K at 4% = $200
        Total: $400 (effective 2.0%).
    """
    if basis <= 0:
        return 0.0
    owed = 0.0
    for t in TIERS:
        lo = t["lo"]
        hi = t["hi"] if t["hi"] is not None else float("inf")
        if basis < lo:
            break
        bracket_top = min(basis, hi)
        bracket_amount = max(0.0, bracket_top - max(lo - 1, 0))
        # Bracket spans (lo-1) → hi; we treat lo as the first dollar of
        # this bracket. Conceptually: bracket-revenue =
        #   max(0, min(basis, hi) - (lo - 1))
        # which collapses to bracket_top - (lo - 1) when basis >= lo.
        owed += bracket_amount * t["outbound_pct"] / 100.0
    return round(owed, 2)


async def compute_basis_12mo(db, artist_user_id: str) -> float:
    """Sum of artist's Birthright-attributed gross revenue in the trailing
    12 months:

      • on-site patronage: sum of list_price × qty for line items in PAID
        orders, where the line item's product has gallery_artist_user_id
        = artist_user_id, in the last 365 days.
      • off-site self-reported: sum of partner_sales_reports.amount_usd
        where partner_user_id = artist_user_id and the report's
        period_end falls in the last 365 days.
    """
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=365)
    cutoff = cutoff_dt.isoformat()

    # On-site patronage.
    orders = await db.orders.find(
        {"status": "paid", "created_at": {"$gte": cutoff}},
        {"_id": 0, "items": 1},
    ).to_list(50_000)
    pids = {li.get("product_id")
            for o in orders for li in (o.get("items") or [])
            if li.get("product_id")}
    if pids:
        artist_products = await db.products.find(
            {"id": {"$in": list(pids)},
             "is_gallery_artwork": True,
             "gallery_artist_user_id": artist_user_id},
            {"_id": 0, "id": 1, "price": 1},
        ).to_list(len(pids) + 1)
        price_by_id = {p["id"]: float(p.get("price") or 0) for p in artist_products}
    else:
        price_by_id = {}

    onsite = 0.0
    for o in orders:
        for li in o.get("items") or []:
            pid = li.get("product_id")
            if pid in price_by_id:
                onsite += price_by_id[pid] * int(li.get("quantity") or 0)

    # Off-site self-reported.
    offsite = 0.0
    reports = await db.partner_sales_reports.find(
        {"partner_user_id": artist_user_id,
         "period_end": {"$gte": cutoff[:10]}},
        {"_id": 0, "amount_usd": 1},
    ).to_list(2000)
    for r in reports:
        offsite += float(r.get("amount_usd") or 0)

    return round(onsite + offsite, 2)


def runway_to_next(basis: float) -> dict:
    """Friendly 'how far to the next tier' helper for the artist dashboard."""
    current = tier_for_basis(basis)
    cur_idx = TIERS.index(current)
    if cur_idx >= len(TIERS) - 1:
        return {"next_tier": None, "distance_usd": 0.0,
                "next_threshold": None}
    nxt = TIERS[cur_idx + 1]
    return {
        "next_tier_key": nxt["key"],
        "next_tier_label": nxt["label"],
        "next_threshold": nxt["lo"],
        "distance_usd": round(max(0.0, nxt["lo"] - basis), 2),
    }


async def log_tier_change(
    db, artist_user_id: str, basis: float, tier_key: str,
) -> Optional[dict]:
    """Persist an `artist_tier_history` row when the artist's tier_key
    changes. Tracking starts going forward from the first ever call —
    the initial baseline is recorded with `direction='initial'` and
    `share_dismissed=True` so it doesn't trigger a celebration banner.

    Returns the newly inserted change document if a real transition
    (up or down) was recorded, else None.
    """
    latest = await db.artist_tier_history.find_one(
        {"user_id": artist_user_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    if latest is None:
        await db.artist_tier_history.insert_one({
            "id": gen_id(),
            "user_id": artist_user_id,
            "from_tier_key": None,
            "to_tier_key": tier_key,
            "direction": "initial",
            "basis_at_change": float(basis),
            "created_at": now_iso(),
            "share_dismissed": True,
        })
        return None
    if latest.get("to_tier_key") == tier_key:
        return None
    old_idx = TIER_ORDER.index(latest["to_tier_key"]) \
        if latest.get("to_tier_key") in TIER_ORDER else 0
    new_idx = TIER_ORDER.index(tier_key) if tier_key in TIER_ORDER else 0
    direction = "up" if new_idx > old_idx else "down"
    doc = {
        "id": gen_id(),
        "user_id": artist_user_id,
        "from_tier_key": latest.get("to_tier_key"),
        "to_tier_key": tier_key,
        "direction": direction,
        "basis_at_change": float(basis),
        "created_at": now_iso(),
        "share_dismissed": False,
    }
    await db.artist_tier_history.insert_one(dict(doc))
    return doc


async def resolve_artist_tier(db, artist_user_id: str) -> dict:
    """One call returns everything an artist needs to see on their dashboard.

    Side-effect: records a row in `artist_tier_history` if this is the
    first observation for the artist OR the tier_key changed since the
    previous one.

    Returns:
        {
          tier_key, tier_label, tier_icon,
          inbound_pct, outbound_pct,
          basis_12mo,
          next_tier_key, next_tier_label, distance_usd, next_threshold,
          effective_outbound_pct,   # if you applied marginal across basis
          source: 'computed' | 'admin_override',
          override_reason?: str,
        }
    """
    # Admin override?
    override = await db.artist_tier_overrides.find_one(
        {"user_id": artist_user_id, "active": True}, {"_id": 0},
    )
    if override:
        t = next((x for x in TIERS if x["key"] == override["tier_key"]),
                  TIERS[0])
        basis = await compute_basis_12mo(db, artist_user_id)
        runway = runway_to_next(basis)
        owed = marginal_outbound_owed(basis)
        eff = round((owed / basis) * 100, 2) if basis else 0.0
        await log_tier_change(db, artist_user_id, basis, t["key"])
        return {
            "tier_key": t["key"], "tier_label": t["label"],
            "tier_icon": t["icon"],
            "inbound_pct": t["inbound_pct"],
            "outbound_pct": t["outbound_pct"],
            "basis_12mo": basis,
            "effective_outbound_pct": eff,
            **runway,
            "source": "admin_override",
            "override_reason": override.get("reason", ""),
        }

    basis = await compute_basis_12mo(db, artist_user_id)
    t = tier_for_basis(basis)
    runway = runway_to_next(basis)
    owed = marginal_outbound_owed(basis)
    eff = round((owed / basis) * 100, 2) if basis else 0.0
    await log_tier_change(db, artist_user_id, basis, t["key"])
    return {
        "tier_key": t["key"], "tier_label": t["label"],
        "tier_icon": t["icon"],
        "inbound_pct": t["inbound_pct"],
        "outbound_pct": t["outbound_pct"],
        "basis_12mo": basis,
        "effective_outbound_pct": eff,
        **runway,
        "source": "computed",
    }
