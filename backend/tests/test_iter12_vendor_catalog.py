"""Phase 6B.4 — Vendor Autonomous Catalog tests."""
import os
import uuid
import pytest
import requests
from pathlib import Path

# Load REACT_APP_BACKEND_URL from frontend/.env and MONGO_URL/DB_NAME from backend/.env
def _load_env(path):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)

_load_env("/app/frontend/.env")
_load_env("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@birthright.live", "password": "birthright2026"}
VENDOR = {"email": "demo@birthright.live", "password": "birthright2026"}
NON_VENDOR = {"email": "elena@birthright.live", "password": "birthright2026"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def vendor_headers():
    return {"Authorization": f"Bearer {_login(VENDOR)}"}


@pytest.fixture(scope="module")
def non_vendor_headers():
    return {"Authorization": f"Bearer {_login(NON_VENDOR)}"}


@pytest.fixture(scope="module")
def created_product_ids():
    """Track products created during testing for cleanup."""
    ids = []
    yield ids
    # Cleanup as admin via direct delete - vendor products can be removed via /api/admin/vendor-products
    # Easier: use the admin foundation delete (which deletes any product by id)
    try:
        h = {"Authorization": f"Bearer {_login(ADMIN)}"}
        for pid in ids:
            requests.delete(f"{API}/products/{pid}", headers=h, timeout=15)
    except Exception:
        pass


# ============ ACCESS CONTROL ============

class TestAccessControl:
    def test_non_vendor_cannot_create(self, non_vendor_headers):
        r = requests.post(
            f"{API}/vendor/products",
            headers=non_vendor_headers,
            json={"name": "TEST_x", "description": "desc desc desc", "price": 10},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_non_vendor_list_empty(self, non_vendor_headers):
        # Elena has no vendor products — list should return empty (no 403; list is allowed but empty)
        r = requests.get(f"{API}/vendor/products", headers=non_vendor_headers, timeout=15)
        assert r.status_code == 200
        # Elena should NOT see demo's products
        for p in r.json():
            assert p.get("vendor_user_id") != "demo"

    def test_unauthenticated_blocked(self):
        r = requests.get(f"{API}/vendor/products", timeout=15)
        assert r.status_code in (401, 403)


# ============ VENDOR CRUD ============

class TestVendorCRUD:
    def test_create_product_auto_fields(self, vendor_headers, created_product_ids):
        payload = {
            "name": f"TEST_Wool Scarf {uuid.uuid4().hex[:6]}",
            "description": "A handwoven test scarf for backend regression.",
            "price": 42.50,
            "category": "Apparel",
        }
        r = requests.post(f"{API}/vendor/products", headers=vendor_headers, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["is_vendor_product"] is True
        assert p["moderation_status"] == "active"
        assert p["type"] == "merch"
        assert p["vendor_user_id"]
        assert p["vendor_partner_id"]
        assert p["vendor_slug"]
        assert p["vendor_name"]  # prefers business_name
        assert p["category"] == "apparel"  # lowercased
        assert p["price"] == 42.5
        created_product_ids.append(p["id"])

    def test_list_only_my_products(self, vendor_headers, created_product_ids):
        r = requests.get(f"{API}/vendor/products", headers=vendor_headers, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        ids = [p["id"] for p in rows]
        # The new product we just created should be there
        assert created_product_ids[0] in ids
        # All rows must belong to demo (same vendor_user_id across rows)
        vendor_uids = set(p["vendor_user_id"] for p in rows)
        assert len(vendor_uids) <= 1

    def test_update_own_product(self, vendor_headers, created_product_ids):
        pid = created_product_ids[0]
        r = requests.put(
            f"{API}/vendor/products/{pid}",
            headers=vendor_headers,
            json={"name": "TEST_Wool Scarf Updated", "price": 55.0},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["name"] == "TEST_Wool Scarf Updated"
        assert p["price"] == 55.0

    def test_update_non_owner_404(self, non_vendor_headers, created_product_ids):
        pid = created_product_ids[0]
        r = requests.put(
            f"{API}/vendor/products/{pid}",
            headers=non_vendor_headers,
            json={"name": "TEST_hijack attempt"},
            timeout=15,
        )
        assert r.status_code == 404

    def test_delete_with_paid_orders_blocked(self, vendor_headers, admin_headers, created_product_ids):
        """Insert a paid order via second product, then attempt delete."""
        # Create a second product for this test
        payload = {
            "name": f"TEST_SoldOut {uuid.uuid4().hex[:6]}",
            "description": "Will have a fake paid order.",
            "price": 20.0,
        }
        r = requests.post(f"{API}/vendor/products", headers=vendor_headers, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        created_product_ids.append(pid)

        # Insert synthetic paid order via direct mongo through admin's foundation
        # We don't have an admin "create order" endpoint, so use Python to insert directly via pymongo
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        assert mongo_url and db_name
        client = MongoClient(mongo_url)
        order_id = f"TEST_order_{uuid.uuid4().hex[:8]}"
        client[db_name].orders.insert_one({
            "id": order_id,
            "status": "paid",
            "items": [{"product_id": pid, "quantity": 1}],
            "created_at": "2026-01-01T00:00:00Z",
            "_test": True,
        })

        try:
            r2 = requests.delete(f"{API}/vendor/products/{pid}", headers=vendor_headers, timeout=15)
            assert r2.status_code == 400, r2.text
        finally:
            client[db_name].orders.delete_one({"id": order_id})
            client.close()

    def test_delete_own_clean_product(self, vendor_headers, created_product_ids):
        # The second product (SoldOut) still exists. Delete after cleaning orders.
        pid_to_delete = created_product_ids[-1]
        r = requests.delete(f"{API}/vendor/products/{pid_to_delete}", headers=vendor_headers, timeout=15)
        assert r.status_code == 200, r.text
        # Confirm gone from my list
        r2 = requests.get(f"{API}/vendor/products", headers=vendor_headers, timeout=15)
        ids = [p["id"] for p in r2.json()]
        assert pid_to_delete not in ids
        created_product_ids.remove(pid_to_delete)


# ============ ADMIN MODERATION ============

class TestAdminModeration:
    def test_admin_list_all(self, admin_headers, created_product_ids):
        r = requests.get(f"{API}/admin/vendor-products", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        ids = [p["id"] for p in rows]
        assert created_product_ids[0] in ids

    def test_non_admin_blocked(self, vendor_headers):
        r = requests.get(f"{API}/admin/vendor-products", headers=vendor_headers, timeout=15)
        assert r.status_code == 403

    def test_status_filter(self, admin_headers):
        r = requests.get(f"{API}/admin/vendor-products?status=active", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        for p in r.json():
            assert p["moderation_status"] == "active"

    def test_flag_then_hidden_from_public(self, admin_headers, created_product_ids):
        pid = created_product_ids[0]
        r = requests.post(
            f"{API}/admin/vendor-products/{pid}/flag",
            headers=admin_headers,
            json={"moderation_note": "Test flag"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["moderation_status"] == "flagged"
        assert r.json()["moderation_note"] == "Test flag"

        # Public listing should hide it
        pub = requests.get(f"{API}/products", timeout=15).json()
        assert pid not in [p["id"] for p in pub]

        # Public detail returns 404 (no auth)
        det = requests.get(f"{API}/products/{pid}", timeout=15)
        assert det.status_code == 404

        # Admin can still see it
        adet = requests.get(f"{API}/products/{pid}", headers=admin_headers, timeout=15)
        assert adet.status_code == 200

    def test_owner_can_see_flagged(self, vendor_headers, created_product_ids):
        pid = created_product_ids[0]
        r = requests.get(f"{API}/products/{pid}", headers=vendor_headers, timeout=15)
        assert r.status_code == 200

    def test_update_unpublished_blocked(self, admin_headers, vendor_headers, created_product_ids):
        pid = created_product_ids[0]
        # Unpublish
        r = requests.post(
            f"{API}/admin/vendor-products/{pid}/unpublish",
            headers=admin_headers,
            json={"moderation_note": "Test takedown"},
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["moderation_status"] == "unpublished"

        # Vendor can't edit it now
        r2 = requests.put(
            f"{API}/vendor/products/{pid}",
            headers=vendor_headers,
            json={"name": "TEST_should_fail"},
            timeout=15,
        )
        assert r2.status_code == 400

    def test_restore(self, admin_headers, created_product_ids):
        pid = created_product_ids[0]
        r = requests.post(f"{API}/admin/vendor-products/{pid}/restore", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["moderation_status"] == "active"

        # Now visible publicly
        pub = requests.get(f"{API}/products", timeout=15).json()
        assert pid in [p["id"] for p in pub]

    def test_unflag(self, admin_headers, vendor_headers, created_product_ids):
        pid = created_product_ids[0]
        # Flag and unflag
        requests.post(
            f"{API}/admin/vendor-products/{pid}/flag",
            headers=admin_headers,
            json={"moderation_note": "tmp"},
            timeout=15,
        )
        r = requests.post(f"{API}/admin/vendor-products/{pid}/unflag", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["moderation_status"] == "active"


# ============ PUBLIC LISTING / FILTERS ============

class TestPublicListing:
    def test_foundation_products_unchanged(self):
        r = requests.get(f"{API}/products", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        # Should have foundation products (is_vendor_product != true)
        foundation = [p for p in rows if not p.get("is_vendor_product")]
        assert len(foundation) > 0

    def test_vendor_id_filter(self, admin_headers, created_product_ids):
        # Get vendor_partner_id from admin list of created product
        r = requests.get(f"{API}/admin/vendor-products", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        target = next((p for p in rows if p["id"] == created_product_ids[0]), None)
        assert target is not None
        partner_id = target["vendor_partner_id"]
        r2 = requests.get(f"{API}/products?vendor_id={partner_id}", timeout=15)
        assert r2.status_code == 200
        rows2 = r2.json()
        assert len(rows2) >= 1
        for p in rows2:
            assert p.get("vendor_partner_id") == partner_id


# ============ REGRESSION ============

class TestRegression:
    def test_referrals_my_link_still_works(self, vendor_headers):
        r = requests.get(f"{API}/me/referrals/my-link", headers=vendor_headers, timeout=15)
        # Demo has community profile from Phase 6B.3
        assert r.status_code in (200, 404)  # 404 if no community profile

    def test_admin_reports_still_works(self, admin_headers):
        r = requests.get(f"{API}/admin/reports", headers=admin_headers, timeout=15)
        assert r.status_code == 200

    def test_admin_can_still_crud_foundation_product(self, admin_headers):
        # Create
        r = requests.post(
            f"{API}/products",
            headers=admin_headers,
            json={
                "name": "TEST_Foundation Item",
                "description": "regression",
                "price": 10.0,
                "type": "merch",
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        # Delete cleanup
        requests.delete(f"{API}/products/{pid}", headers=admin_headers, timeout=15)
