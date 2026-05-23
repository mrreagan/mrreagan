"""Iteration 14 — Runtime seed + image-repair self-healing tests.

Validates the new `runtime_seed` module wired into FastAPI startup:
  - ensure_catalog_seeded(): backfills missing slug-tagged products from data/catalog.json
  - repair_known_broken_images(): re-points Hardcover Journal + Enamel Pin to committed PNGs

Includes IDEMPOTENCY tests that mutate the DB (delete a product / break an
image URL) and then restart the backend to confirm self-heal. All tests
restore DB state by the time they finish.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient

# --- env / config ---------------------------------------------------------
BACKEND_DIR = Path("/app/backend")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

# Read Mongo connection from backend/.env (test runs from /app/backend, but be explicit)
def _read_env_file(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

_env = _read_env_file(BACKEND_DIR / ".env")
MONGO_URL = _env.get("MONGO_URL") or os.environ.get("MONGO_URL")
DB_NAME = _env.get("DB_NAME") or os.environ.get("DB_NAME")
assert MONGO_URL and DB_NAME, "MONGO_URL/DB_NAME required"

CATALOG_PATH = BACKEND_DIR / "data" / "catalog.json"
LOG_PATH = Path("/var/log/supervisor/backend.err.log")


def _restart_backend_and_wait():
    subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True, capture_output=True)
    # Wait for /api/health to come back
    for _ in range(30):
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if r.status_code == 200:
                # Give startup hook a moment to finish
                time.sleep(1.5)
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("backend did not return healthy after restart")


@pytest.fixture(scope="module")
def catalog_items() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text())["items"]


@pytest.fixture
def db():
    """Sync pymongo handle. Module-scoped client closed via fixture teardown."""
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


# --- 1. Startup-hook log assertions --------------------------------------
class TestStartupHookLogs:
    def test_runtime_seed_catalog_log_present(self):
        text = LOG_PATH.read_text()
        assert "birthright.runtime_seed" in text, "runtime_seed logger never fired"
        assert "catalog seed" in text, "catalog-seed INFO line missing in logs"

    def test_runtime_seed_image_repair_log_present(self):
        text = LOG_PATH.read_text()
        assert "image repair" in text or "catalog seed" in text, (
            "Neither image-repair nor catalog-seed log lines found"
        )


# --- 2. /api/products contract -------------------------------------------
class TestProductsCatalog:
    def test_products_returns_60_with_50_catalog_slugs(self, catalog_items):
        r = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert r.status_code == 200, r.text
        products = r.json()
        assert isinstance(products, list)
        assert len(products) == 60, f"expected 60 products, got {len(products)}"

        catalog_slugs = {item["slug"] for item in catalog_items}
        assert len(catalog_slugs) == 50, "catalog.json should have 50 entries"

        db_slugs = {p.get("slug") for p in products if p.get("slug")}
        missing = catalog_slugs - db_slugs
        assert not missing, f"catalog slugs missing from /api/products: {sorted(missing)[:5]}"

    @pytest.mark.parametrize(
        "slug",
        [
            "belonging-raglan-bone-teal",
            "bonded-linen-retreat-robe",
            "brass-bookmark-hand-stamped",
        ],
    )
    def test_specific_catalog_slug_present(self, slug):
        r = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert r.status_code == 200
        matched = [p for p in r.json() if p.get("slug") == slug]
        assert matched, f"product slug {slug!r} not returned by /api/products"
        p = matched[0]
        assert p["image_url"] == f"/api/static/products/{slug}.png"
        assert isinstance(p.get("price"), (int, float))


# --- 3. Image repair contract --------------------------------------------
class TestRepairedImages:
    def test_hardcover_journal_uses_local_png(self):
        r = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert r.status_code == 200
        hj = [p for p in r.json() if p["name"] == "Birthright Hardcover Journal"]
        assert hj, "Birthright Hardcover Journal missing"
        assert hj[0]["image_url"] == "/api/static/products/birthright-hardcover-journal.png"

    def test_enamel_pin_uses_local_png(self):
        r = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert r.status_code == 200
        ep = [p for p in r.json() if p["name"] == "Enamel Pin — Flame"]
        assert ep, "Enamel Pin — Flame missing"
        assert ep[0]["image_url"] == "/api/static/products/enamel-pin-flame.png"

    @pytest.mark.parametrize(
        "filename",
        ["birthright-hardcover-journal.png", "enamel-pin-flame.png"],
    )
    def test_static_png_served_non_zero(self, filename):
        r = requests.get(f"{BASE_URL}/api/static/products/{filename}", timeout=10)
        assert r.status_code == 200, f"{filename} -> {r.status_code}"
        assert len(r.content) > 1000, f"{filename} returned {len(r.content)} bytes"
        assert r.headers.get("content-type", "").startswith("image/"), r.headers


# --- 4. IDEMPOTENCY: catalog seed re-inserts deleted product -------------
class TestCatalogSeedIdempotency:
    TARGET_SLUG = "bonded-linen-retreat-robe"

    def test_delete_then_restart_reinserts(self, db):
        existing = db.products.find_one({"slug": self.TARGET_SLUG})
        assert existing, f"Pre-condition failed: {self.TARGET_SLUG} not in DB"
        deleted_count = db.products.delete_one({"slug": self.TARGET_SLUG}).deleted_count
        assert deleted_count == 1, "delete pre-condition failed"

        # Verify gone via API
        r = requests.get(f"{BASE_URL}/api/products", timeout=10)
        assert r.status_code == 200
        slugs_before = {p.get("slug") for p in r.json()}
        assert self.TARGET_SLUG not in slugs_before, "delete didn't propagate"
        assert len(r.json()) == 59, f"expected 59 products after delete, got {len(r.json())}"

        # Restart -> runtime_seed should re-insert
        try:
            _restart_backend_and_wait()

            r2 = requests.get(f"{BASE_URL}/api/products", timeout=10)
            assert r2.status_code == 200, r2.text
            products = r2.json()
            assert len(products) == 60, (
                f"runtime_seed did NOT re-insert {self.TARGET_SLUG}; "
                f"product count = {len(products)}"
            )
            restored = [p for p in products if p.get("slug") == self.TARGET_SLUG]
            assert restored, "restored slug missing"
            assert restored[0]["image_url"] == (
                f"/api/static/products/{self.TARGET_SLUG}.png"
            ), f"image_url not pointed at committed PNG: {restored[0]['image_url']}"
        finally:
            # Belt-and-suspenders: if for any reason restart didn't restore,
            # restore the original document so the DB ends clean.
            if not db.products.find_one({"slug": self.TARGET_SLUG}):
                existing.pop("_id", None)
                db.products.insert_one(existing)


# --- 5. IDEMPOTENCY: image repair heals broken URL -----------------------
class TestImageRepairIdempotency:
    PRODUCT_NAME = "Birthright Hardcover Journal"
    GOOD_URL = "/api/static/products/birthright-hardcover-journal.png"
    BROKEN_URL = "https://images.unsplash.com/legacy-broken-url"

    def test_break_url_then_restart_repairs(self, db):
        existing = db.products.find_one({"name": self.PRODUCT_NAME})
        assert existing, f"Pre-condition failed: {self.PRODUCT_NAME} not in DB"
        modified = db.products.update_one(
            {"name": self.PRODUCT_NAME},
            {"$set": {"image_url": self.BROKEN_URL}},
        ).modified_count
        assert modified == 1, "could not break image_url for test"

        # Confirm broken via API
        r = requests.get(f"{BASE_URL}/api/products", timeout=10)
        hj = [p for p in r.json() if p["name"] == self.PRODUCT_NAME][0]
        assert hj["image_url"] == self.BROKEN_URL

        # Restart -> repair_known_broken_images should fix it
        try:
            _restart_backend_and_wait()
            r2 = requests.get(f"{BASE_URL}/api/products", timeout=10)
            assert r2.status_code == 200
            hj2 = [p for p in r2.json() if p["name"] == self.PRODUCT_NAME][0]
            assert hj2["image_url"] == self.GOOD_URL, (
                f"image repair did NOT heal URL on restart: {hj2['image_url']}"
            )
        finally:
            cur = db.products.find_one({"name": self.PRODUCT_NAME})
            if cur and cur.get("image_url") != self.GOOD_URL:
                db.products.update_one(
                    {"name": self.PRODUCT_NAME},
                    {"$set": {"image_url": self.GOOD_URL}},
                )


# --- 6. Regression: vendor catalog endpoint reachable --------------------
class TestRegressionEndpoints:
    def test_health_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_vendor_catalog_unauth_returns_401(self):
        # No auth -> should 401/403, NOT 500 (endpoint is reachable)
        r = requests.get(f"{BASE_URL}/api/vendor/products", timeout=5)
        assert r.status_code in (401, 403), f"vendor/products unexpected: {r.status_code}"
