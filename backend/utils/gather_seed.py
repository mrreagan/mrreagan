"""Seed the Gather hierarchy with continents + countries + major regions.

Idempotent: only inserts nodes that don't already exist. Run via the
`utils.gather_seed.seed_geographic_tree(db)` function — auto-invoked on
backend startup (see server.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

# Curated hybrid hierarchy. Stewards propose cities/neighborhoods below this.
# kind ∈ continent | country | region (US/CA states, UK nations)
SEED_TREE: list[dict] = [
    # ---- North America ----
    {"slug": "north-america", "label": "North America", "kind": "continent", "parent": None, "lat": 54, "lng": -105},
    {"slug": "north-america/us", "label": "United States", "kind": "country", "parent": "north-america", "lat": 39.8, "lng": -98.6},
    {"slug": "north-america/ca", "label": "Canada", "kind": "country", "parent": "north-america", "lat": 56, "lng": -106},
    {"slug": "north-america/mx", "label": "Mexico", "kind": "country", "parent": "north-america", "lat": 23.6, "lng": -102.5},
    # US states (top 12 by population — admins can grow this list, stewards can propose cities under any of them)
    {"slug": "north-america/us/california", "label": "California", "kind": "region", "parent": "north-america/us", "lat": 36.7, "lng": -119.4},
    {"slug": "north-america/us/texas", "label": "Texas", "kind": "region", "parent": "north-america/us", "lat": 31.0, "lng": -99.0},
    {"slug": "north-america/us/florida", "label": "Florida", "kind": "region", "parent": "north-america/us", "lat": 27.8, "lng": -81.6},
    {"slug": "north-america/us/new-york", "label": "New York", "kind": "region", "parent": "north-america/us", "lat": 42.9, "lng": -75.5},
    {"slug": "north-america/us/pennsylvania", "label": "Pennsylvania", "kind": "region", "parent": "north-america/us", "lat": 41.2, "lng": -77.2},
    {"slug": "north-america/us/illinois", "label": "Illinois", "kind": "region", "parent": "north-america/us", "lat": 40.0, "lng": -89.0},
    {"slug": "north-america/us/ohio", "label": "Ohio", "kind": "region", "parent": "north-america/us", "lat": 40.4, "lng": -82.9},
    {"slug": "north-america/us/georgia", "label": "Georgia", "kind": "region", "parent": "north-america/us", "lat": 33.0, "lng": -83.6},
    {"slug": "north-america/us/north-carolina", "label": "North Carolina", "kind": "region", "parent": "north-america/us", "lat": 35.6, "lng": -79.8},
    {"slug": "north-america/us/michigan", "label": "Michigan", "kind": "region", "parent": "north-america/us", "lat": 44.3, "lng": -85.6},
    {"slug": "north-america/us/washington", "label": "Washington", "kind": "region", "parent": "north-america/us", "lat": 47.4, "lng": -120.7},
    {"slug": "north-america/us/colorado", "label": "Colorado", "kind": "region", "parent": "north-america/us", "lat": 39.0, "lng": -105.5},
    {"slug": "north-america/us/massachusetts", "label": "Massachusetts", "kind": "region", "parent": "north-america/us", "lat": 42.4, "lng": -71.4},
    # Canadian provinces (top 5)
    {"slug": "north-america/ca/ontario", "label": "Ontario", "kind": "region", "parent": "north-america/ca", "lat": 50.0, "lng": -85.3},
    {"slug": "north-america/ca/quebec", "label": "Quebec", "kind": "region", "parent": "north-america/ca", "lat": 53.0, "lng": -71.6},
    {"slug": "north-america/ca/british-columbia", "label": "British Columbia", "kind": "region", "parent": "north-america/ca", "lat": 53.7, "lng": -127.6},
    {"slug": "north-america/ca/alberta", "label": "Alberta", "kind": "region", "parent": "north-america/ca", "lat": 53.9, "lng": -116.5},
    {"slug": "north-america/ca/manitoba", "label": "Manitoba", "kind": "region", "parent": "north-america/ca", "lat": 53.7, "lng": -98.8},

    # ---- Europe ----
    {"slug": "europe", "label": "Europe", "kind": "continent", "parent": None, "lat": 54, "lng": 15},
    {"slug": "europe/uk", "label": "United Kingdom", "kind": "country", "parent": "europe", "lat": 55.4, "lng": -3.4},
    {"slug": "europe/ie", "label": "Ireland", "kind": "country", "parent": "europe", "lat": 53.4, "lng": -8.2},
    {"slug": "europe/de", "label": "Germany", "kind": "country", "parent": "europe", "lat": 51.2, "lng": 10.5},
    {"slug": "europe/fr", "label": "France", "kind": "country", "parent": "europe", "lat": 46.6, "lng": 1.9},
    {"slug": "europe/it", "label": "Italy", "kind": "country", "parent": "europe", "lat": 41.9, "lng": 12.6},
    {"slug": "europe/es", "label": "Spain", "kind": "country", "parent": "europe", "lat": 40.5, "lng": -3.7},
    {"slug": "europe/nl", "label": "Netherlands", "kind": "country", "parent": "europe", "lat": 52.1, "lng": 5.3},
    {"slug": "europe/se", "label": "Sweden", "kind": "country", "parent": "europe", "lat": 60.1, "lng": 18.6},
    {"slug": "europe/no", "label": "Norway", "kind": "country", "parent": "europe", "lat": 60.5, "lng": 8.5},
    {"slug": "europe/dk", "label": "Denmark", "kind": "country", "parent": "europe", "lat": 56.3, "lng": 9.5},
    {"slug": "europe/pt", "label": "Portugal", "kind": "country", "parent": "europe", "lat": 39.4, "lng": -8.2},
    # UK nations
    {"slug": "europe/uk/england", "label": "England", "kind": "region", "parent": "europe/uk", "lat": 52.4, "lng": -1.6},
    {"slug": "europe/uk/scotland", "label": "Scotland", "kind": "region", "parent": "europe/uk", "lat": 56.5, "lng": -4.2},
    {"slug": "europe/uk/wales", "label": "Wales", "kind": "region", "parent": "europe/uk", "lat": 52.1, "lng": -3.8},
    {"slug": "europe/uk/northern-ireland", "label": "Northern Ireland", "kind": "region", "parent": "europe/uk", "lat": 54.8, "lng": -6.5},

    # ---- Asia ----
    {"slug": "asia", "label": "Asia", "kind": "continent", "parent": None, "lat": 35, "lng": 100},
    {"slug": "asia/in", "label": "India", "kind": "country", "parent": "asia", "lat": 20.6, "lng": 78.9},
    {"slug": "asia/jp", "label": "Japan", "kind": "country", "parent": "asia", "lat": 36.2, "lng": 138.3},
    {"slug": "asia/kr", "label": "South Korea", "kind": "country", "parent": "asia", "lat": 35.9, "lng": 127.8},
    {"slug": "asia/sg", "label": "Singapore", "kind": "country", "parent": "asia", "lat": 1.3, "lng": 103.8},
    {"slug": "asia/hk", "label": "Hong Kong", "kind": "country", "parent": "asia", "lat": 22.3, "lng": 114.2},
    {"slug": "asia/ph", "label": "Philippines", "kind": "country", "parent": "asia", "lat": 12.9, "lng": 121.8},
    {"slug": "asia/th", "label": "Thailand", "kind": "country", "parent": "asia", "lat": 15.9, "lng": 100.9},
    {"slug": "asia/id", "label": "Indonesia", "kind": "country", "parent": "asia", "lat": -0.8, "lng": 113.9},
    {"slug": "asia/vn", "label": "Vietnam", "kind": "country", "parent": "asia", "lat": 14.1, "lng": 108.3},

    # ---- Oceania ----
    {"slug": "oceania", "label": "Oceania", "kind": "continent", "parent": None, "lat": -22, "lng": 140},
    {"slug": "oceania/au", "label": "Australia", "kind": "country", "parent": "oceania", "lat": -25.3, "lng": 133.8},
    {"slug": "oceania/nz", "label": "New Zealand", "kind": "country", "parent": "oceania", "lat": -40.9, "lng": 174.9},

    # ---- South America ----
    {"slug": "south-america", "label": "South America", "kind": "continent", "parent": None, "lat": -14, "lng": -58},
    {"slug": "south-america/br", "label": "Brazil", "kind": "country", "parent": "south-america", "lat": -14.2, "lng": -51.9},
    {"slug": "south-america/ar", "label": "Argentina", "kind": "country", "parent": "south-america", "lat": -38.4, "lng": -63.6},
    {"slug": "south-america/cl", "label": "Chile", "kind": "country", "parent": "south-america", "lat": -35.7, "lng": -71.5},
    {"slug": "south-america/co", "label": "Colombia", "kind": "country", "parent": "south-america", "lat": 4.6, "lng": -74.3},
    {"slug": "south-america/pe", "label": "Peru", "kind": "country", "parent": "south-america", "lat": -9.2, "lng": -75.0},

    # ---- Africa ----
    {"slug": "africa", "label": "Africa", "kind": "continent", "parent": None, "lat": 1, "lng": 20},
    {"slug": "africa/za", "label": "South Africa", "kind": "country", "parent": "africa", "lat": -30.6, "lng": 22.9},
    {"slug": "africa/ke", "label": "Kenya", "kind": "country", "parent": "africa", "lat": -0.0, "lng": 37.9},
    {"slug": "africa/ng", "label": "Nigeria", "kind": "country", "parent": "africa", "lat": 9.1, "lng": 8.7},
    {"slug": "africa/eg", "label": "Egypt", "kind": "country", "parent": "africa", "lat": 26.8, "lng": 30.8},
    {"slug": "africa/gh", "label": "Ghana", "kind": "country", "parent": "africa", "lat": 7.9, "lng": -1.0},
]


async def seed_geographic_tree(db) -> dict:
    """Insert any missing nodes. Returns {"inserted": N, "total_now": M}."""
    now = datetime.now(timezone.utc).isoformat()
    existing_slugs = set()
    async for c in db.communities.find({}, {"_id": 0, "slug": 1}):
        existing_slugs.add(c["slug"])
    inserted = 0
    for node in SEED_TREE:
        if node["slug"] in existing_slugs:
            continue
        await db.communities.insert_one({
            "id": str(uuid.uuid4()),
            "slug": node["slug"],
            "label": node["label"],
            "parent_slug": node["parent"],
            "kind": node["kind"],
            "lat": node.get("lat"),
            "lng": node.get("lng"),
            "status": "active",
            "steward_user_ids": [],
            "welcome_text": "",
            "post_count": 0,
            "event_count": 0,
            "member_count": 0,
            "created_at": now,
            "updated_at": now,
            "created_by": "seed",
            "approved_by": "seed",
            "approved_at": now,
        })
        inserted += 1
    total = await db.communities.count_documents({})
    return {"inserted": inserted, "total_now": total}
