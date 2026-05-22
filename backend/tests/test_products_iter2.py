"""Iteration 2 — Product migration + Admin Products CRUD tests.

Scope:
- 60 total products (10 seeded + 50 generated)
- 56 merch, 4 workshop_material
- ~14 apparel category
- Static image serving at /api/static/products/<slug>.png
- Detail by id includes image_url starting with /api/static/products/
- POST/PUT/DELETE products with admin auth
- RBAC: POST without admin returns 401/403
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://birthright-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@birthright.org", "password": "birthright2026"}
DEMO = {"email": "demo@birthright.org", "password": "birthright2026"}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def _login(s, creds):
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def admin_token(s):
    return _login(s, ADMIN)["token"]


@pytest.fixture(scope="module")
def demo_token(s):
    return _login(s, DEMO)["token"]


def H(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Catalog counts ----
class TestProductCatalogCounts:
    def test_total_60(self, s):
        r = s.get(f"{API}/products", timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 60, f"Expected 60 products, got {len(items)}"

    def test_merch_56(self, s):
        r = s.get(f"{API}/products?type=merch", timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 56, f"Expected 56 merch items, got {len(items)}"
        assert all(p["type"] == "merch" for p in items)

    def test_workshop_material_4(self, s):
        r = s.get(f"{API}/products?type=workshop_material", timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 4, f"Expected 4 workshop_material, got {len(items)}"

    def test_apparel_filter(self, s):
        r = s.get(f"{API}/products?category=apparel", timeout=30)
        assert r.status_code == 200
        items = r.json()
        # Spec says ~14
        assert 10 <= len(items) <= 20, f"Expected ~14 apparel items, got {len(items)}"
        assert all(p.get("category") == "apparel" for p in items)


# ---- Static serving ----
class TestStaticServing:
    def test_static_inside_out_work_tee(self, s):
        url = f"{API}/static/products/inside-out-work-tee-cream.png"
        r = s.get(url, timeout=30)
        assert r.status_code == 200, f"Static image failed: {r.status_code}"
        assert "image/png" in r.headers.get("content-type", "").lower()
        assert len(r.content) > 1000, "Image content too small"

    def test_inside_out_work_tee_in_catalog(self, s):
        r = s.get(f"{API}/products", timeout=30)
        items = r.json()
        matches = [p for p in items if "Inside-Out Work Tee" in p.get("name", "")]
        assert len(matches) >= 1, "Inside-Out Work Tee not in catalog"
        p = matches[0]
        assert p["image_url"].startswith("/api/static/products/"), (
            f"image_url should start with /api/static/products/, got {p['image_url']}"
        )

    def test_get_product_by_id_has_correct_image(self, s):
        r = s.get(f"{API}/products", timeout=30)
        items = r.json()
        target = next((p for p in items if "Inside-Out Work Tee" in p.get("name", "")), None)
        assert target is not None
        r2 = s.get(f"{API}/products/{target['id']}", timeout=30)
        assert r2.status_code == 200
        detail = r2.json()
        assert detail["image_url"].startswith("/api/static/products/")
        # And the static image at that path is fetchable
        img_path = detail["image_url"].replace("/api/", "")
        img_url = f"{API}/{img_path}"
        r3 = s.get(img_url, timeout=30)
        assert r3.status_code == 200
        assert "image/png" in r3.headers.get("content-type", "").lower()


# ---- Admin CRUD ----
class TestAdminProductCRUD:
    created_id = None

    def test_create_requires_admin(self, s):
        """No auth -> 401/403."""
        r = s.post(f"{API}/products", json={
            "name": "TEST_unauth_product",
            "description": "x", "price": 1.0, "type": "merch",
            "image_url": "", "inventory": 1, "category": "general"
        }, timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_create_blocked_for_non_admin(self, s, demo_token):
        r = s.post(f"{API}/products", headers=H(demo_token), json={
            "name": "TEST_nonadmin_product",
            "description": "x", "price": 1.0, "type": "merch",
            "image_url": "", "inventory": 1, "category": "general"
        }, timeout=15)
        assert r.status_code in (401, 403)

    def test_create_as_admin(self, s, admin_token):
        payload = {
            "name": f"TEST_Product_Z_{uuid.uuid4().hex[:6]}",
            "description": "Test product description",
            "price": 9.99,
            "type": "merch",
            "image_url": "",
            "inventory": 5,
            "category": "general",
        }
        r = s.post(f"{API}/products", headers=H(admin_token), json=payload, timeout=30)
        assert r.status_code == 200, f"create failed: {r.status_code} {r.text}"
        d = r.json()
        assert "id" in d
        assert d["name"] == payload["name"]
        assert d["price"] == 9.99
        assert d["inventory"] == 5
        TestAdminProductCRUD.created_id = d["id"]
        # Verify via GET
        r2 = s.get(f"{API}/products/{d['id']}", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["name"] == payload["name"]

    def test_update_as_admin(self, s, admin_token):
        pid = TestAdminProductCRUD.created_id
        assert pid, "creation must have succeeded first"
        r = s.put(f"{API}/products/{pid}", headers=H(admin_token),
                  json={"price": 19.99, "inventory": 50}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["price"] == 19.99
        assert d["inventory"] == 50
        # Verify persistence
        r2 = s.get(f"{API}/products/{pid}", timeout=15)
        assert r2.json()["price"] == 19.99

    def test_delete_as_admin(self, s, admin_token):
        pid = TestAdminProductCRUD.created_id
        assert pid
        r = s.delete(f"{API}/products/{pid}", headers=H(admin_token), timeout=15)
        assert r.status_code == 200
        # Verify gone
        r2 = s.get(f"{API}/products/{pid}", timeout=15)
        assert r2.status_code == 404


# ---- Slug field present on new products ----
class TestSlugField:
    def test_new_products_have_slug(self, s):
        r = s.get(f"{API}/products?type=merch", timeout=30)
        items = r.json()
        # Slug should be present on at least 50 of the new products
        with_slug = [p for p in items if p.get("slug")]
        assert len(with_slug) >= 50, f"Expected >=50 products with slug, got {len(with_slug)}"
