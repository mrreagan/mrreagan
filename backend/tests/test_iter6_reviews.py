"""Iteration 6A.1 — Universal Polymorphic Reviews backend tests.

Covers POST/GET /api/reviews (subject_type/subject_id and workshop_id back-compat),
aggregate, search, report, moderate.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://birthright-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@birthright.org", "password": "birthright2026"}
DEMO = {"email": "demo@birthright.org", "password": "birthright2026"}
ELENA = {"email": "elena@birthright.org", "password": "birthright2026"}
MARCUS = {"email": "marcus@birthright.org", "password": "birthright2026"}

PAST_WORKSHOP_SLUG = "foundations-spring-cohort-past"
UPCOMING_WORKSHOP_SLUG = "foundations-of-secure-bonds"
UNREGISTERED_WORKSHOP_SLUG = "repair-the-conversation-you-postponed"  # demo NOT registered here


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.text}"
    return r.json()["token"], r.json()["user"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def demo_auth():
    return _login(DEMO)


@pytest.fixture(scope="module")
def admin_auth():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def elena_auth():
    return _login(ELENA)


@pytest.fixture(scope="module")
def marcus_auth():
    return _login(MARCUS)


@pytest.fixture(scope="module")
def workshops():
    r = requests.get(f"{API}/workshops", timeout=15)
    assert r.status_code == 200
    out = {w["slug"]: w for w in r.json()}
    return out


@pytest.fixture(scope="module")
def products():
    r = requests.get(f"{API}/products", timeout=15)
    assert r.status_code == 200
    return r.json()


# ---------- POST /api/reviews ----------

class TestCreateReview:
    def test_workshop_review_as_paid_participant(self, demo_auth, workshops):
        token, user = demo_auth
        wid = workshops[PAST_WORKSHOP_SLUG]["id"]
        r = requests.post(
            f"{API}/reviews",
            headers=_hdr(token),
            json={"subject_type": "workshop", "subject_id": wid, "rating": 5,
                  "review_text": "Truly transformative content and facilitator." + str(time.time())},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["subject_type"] == "workshop"
        assert data["subject_category"] == "workshop"
        assert data["verified_purchase"] is True
        assert data["subject_id"] == wid

    def test_workshop_review_backcompat_workshop_id(self, demo_auth, workshops):
        token, _ = demo_auth
        wid = workshops[PAST_WORKSHOP_SLUG]["id"]
        # Use legacy alias only (no subject_type)
        r = requests.post(
            f"{API}/reviews",
            headers=_hdr(token),
            json={"workshop_id": wid, "rating": 4,
                  "review_text": "Back-compat path still works for legacy clients."},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["subject_type"] == "workshop"
        assert d["subject_id"] == wid

    def test_workshop_review_not_registered_forbidden(self, demo_auth, workshops):
        token, _ = demo_auth
        wid = workshops[UNREGISTERED_WORKSHOP_SLUG]["id"]  # demo not paid on this
        r = requests.post(
            f"{API}/reviews",
            headers=_hdr(token),
            json={"subject_type": "workshop", "subject_id": wid, "rating": 4,
                  "review_text": "Should be rejected since not registered."},
            timeout=15,
        )
        assert r.status_code == 403, r.text
        assert "registered" in r.json().get("detail", "").lower()

    def test_product_review_any_signed_in_user(self, demo_auth, products):
        token, _ = demo_auth
        prod = products[0]  # journals category
        r = requests.post(
            f"{API}/reviews",
            headers=_hdr(token),
            json={"subject_type": "product", "subject_id": prod["id"], "rating": 5,
                  "review_text": "Lovely journal for daily reflection."},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["subject_type"] == "product"
        assert d["subject_category"] == prod.get("category", "general")
        assert d["verified_purchase"] is False

    def test_second_review_updates_not_duplicates(self, demo_auth, products):
        token, _ = demo_auth
        prod = products[1]
        first = requests.post(
            f"{API}/reviews", headers=_hdr(token),
            json={"subject_type": "product", "subject_id": prod["id"], "rating": 3,
                  "review_text": "First impression, decent quality."},
            timeout=15)
        assert first.status_code == 200, first.text
        first_id = first.json()["id"]
        second = requests.post(
            f"{API}/reviews", headers=_hdr(token),
            json={"subject_type": "product", "subject_id": prod["id"], "rating": 5,
                  "review_text": "Updated my mind — actually loving it now."},
            timeout=15)
        assert second.status_code == 200, second.text
        second_id = second.json()["id"]
        assert first_id == second_id, "Second review must update, not create new"
        # Verify only one review for this (user, subject)
        lst = requests.get(f"{API}/reviews",
                           params={"subject_type": "product", "subject_id": prod["id"]},
                           timeout=15).json()
        mine = [r for r in lst if r.get("user_id") == demo_auth[1]["id"]]
        assert len(mine) == 1
        assert mine[0]["rating"] == 5

    def test_invalid_subject_type(self, demo_auth):
        token, _ = demo_auth
        r = requests.post(
            f"{API}/reviews", headers=_hdr(token),
            json={"subject_type": "unicorn", "subject_id": "x", "rating": 3,
                  "review_text": "Bogus subject type test."},
            timeout=15)
        # Pydantic literal validation rejects with 422
        assert r.status_code in (400, 422), r.text

    def test_missing_subject_id(self, demo_auth):
        token, _ = demo_auth
        r = requests.post(
            f"{API}/reviews", headers=_hdr(token),
            json={"rating": 3, "review_text": "No subject at all here."},
            timeout=15)
        assert r.status_code == 400

    def test_short_text_rejected_422(self, demo_auth, products):
        token, _ = demo_auth
        r = requests.post(
            f"{API}/reviews", headers=_hdr(token),
            json={"subject_type": "product", "subject_id": products[0]["id"], "rating": 4,
                  "review_text": "short"},
            timeout=15)
        assert r.status_code == 422

    def test_rating_out_of_range_422(self, demo_auth, products):
        token, _ = demo_auth
        r = requests.post(
            f"{API}/reviews", headers=_hdr(token),
            json={"subject_type": "product", "subject_id": products[0]["id"], "rating": 7,
                  "review_text": "Rating out of range edge case."},
            timeout=15)
        assert r.status_code == 422


# ---------- GET listing & aggregate & search ----------

class TestListAndAggregate:
    def test_list_by_subject(self, workshops):
        wid = workshops[PAST_WORKSHOP_SLUG]["id"]
        r = requests.get(f"{API}/reviews",
                         params={"subject_type": "workshop", "subject_id": wid},
                         timeout=15)
        assert r.status_code == 200
        for rev in r.json():
            assert rev.get("moderated") is not True  # hidden by default

    def test_list_backcompat_workshop_id(self, workshops):
        wid = workshops[PAST_WORKSHOP_SLUG]["id"]
        r = requests.get(f"{API}/reviews", params={"workshop_id": wid}, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_aggregate(self, workshops):
        wid = workshops[PAST_WORKSHOP_SLUG]["id"]
        r = requests.get(f"{API}/reviews/aggregate",
                         params={"subject_type": "workshop", "subject_id": wid},
                         timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert {"count", "avg", "verified_count"}.issubset(d.keys())
        # avg rounded to 2 decimals
        assert isinstance(d["avg"], (int, float))
        avg_str = f"{d['avg']}"
        if "." in avg_str:
            assert len(avg_str.split(".")[1]) <= 2
        assert d["verified_count"] <= d["count"]

    def test_search_filters(self, products):
        # All
        r = requests.get(f"{API}/reviews/search", timeout=15)
        assert r.status_code == 200
        all_results = r.json()
        assert isinstance(all_results, list)
        if all_results:
            for rev in all_results:
                assert "subject_label" in rev
        # Category filter
        r2 = requests.get(f"{API}/reviews/search",
                          params={"subject_category": "workshop"}, timeout=15)
        assert r2.status_code == 200
        for rev in r2.json():
            assert rev["subject_category"] == "workshop"
        # min_rating
        r3 = requests.get(f"{API}/reviews/search", params={"min_rating": 4}, timeout=15)
        assert r3.status_code == 200
        for rev in r3.json():
            assert rev["rating"] >= 4
        # q text search
        r4 = requests.get(f"{API}/reviews/search", params={"q": "tr"}, timeout=15)
        assert r4.status_code == 200
        # limit
        r5 = requests.get(f"{API}/reviews/search", params={"limit": 1}, timeout=15)
        assert r5.status_code == 200
        assert len(r5.json()) <= 1


# ---------- Report ----------

class TestReport:
    def test_report_increments_count(self, demo_auth, elena_auth, marcus_auth, products):
        # Demo writes; Elena & Marcus report it
        token_d, _ = demo_auth
        prod = products[2]
        cr = requests.post(f"{API}/reviews", headers=_hdr(token_d),
                           json={"subject_type": "product", "subject_id": prod["id"], "rating": 4,
                                 "review_text": "Solid tote, good seams and stitching."},
                           timeout=15)
        assert cr.status_code == 200
        rid = cr.json()["id"]

        token_e, _ = elena_auth
        r1 = requests.post(f"{API}/reviews/{rid}/report", headers=_hdr(token_e),
                           json={"reason": "Spammy content alert"}, timeout=15)
        assert r1.status_code == 200
        token_m, _ = marcus_auth
        r2 = requests.post(f"{API}/reviews/{rid}/report", headers=_hdr(token_m),
                           json={"reason": "Inappropriate language flagged"}, timeout=15)
        assert r2.status_code == 200

        # Fetch and verify count
        lst = requests.get(f"{API}/reviews",
                           params={"subject_type": "product", "subject_id": prod["id"]},
                           timeout=15).json()
        target = next(r for r in lst if r["id"] == rid)
        assert target["reported_count"] >= 2


# ---------- Moderate ----------

class TestModerate:
    def test_admin_can_hide_and_restore(self, demo_auth, admin_auth, products):
        token_d, _ = demo_auth
        prod = products[3]
        cr = requests.post(f"{API}/reviews", headers=_hdr(token_d),
                           json={"subject_type": "product", "subject_id": prod["id"], "rating": 2,
                                 "review_text": "Color looked different in person."},
                           timeout=15)
        assert cr.status_code == 200
        rid = cr.json()["id"]

        token_a, _ = admin_auth
        # Hide
        hide = requests.post(f"{API}/reviews/{rid}/moderate", headers=_hdr(token_a),
                             json={"moderated": True, "reason": "off-topic"}, timeout=15)
        assert hide.status_code == 200
        # Should not appear in default listing
        default = requests.get(f"{API}/reviews",
                               params={"subject_type": "product", "subject_id": prod["id"]},
                               timeout=15).json()
        assert all(r["id"] != rid for r in default)
        # Appears with include_moderated=true
        with_mod = requests.get(f"{API}/reviews",
                                params={"subject_type": "product", "subject_id": prod["id"],
                                        "include_moderated": "true"},
                                timeout=15).json()
        assert any(r["id"] == rid for r in with_mod)
        # Restore
        restore = requests.post(f"{API}/reviews/{rid}/moderate", headers=_hdr(token_a),
                                json={"moderated": False}, timeout=15)
        assert restore.status_code == 200
        again = requests.get(f"{API}/reviews",
                             params={"subject_type": "product", "subject_id": prod["id"]},
                             timeout=15).json()
        assert any(r["id"] == rid for r in again)

    def test_non_admin_forbidden(self, demo_auth, products):
        token, _ = demo_auth
        # Find any review on a product
        lst = requests.get(f"{API}/reviews",
                           params={"subject_type": "product", "subject_id": products[0]["id"]},
                           timeout=15).json()
        if not lst:
            pytest.skip("No review available to attempt moderation")
        rid = lst[0]["id"]
        r = requests.post(f"{API}/reviews/{rid}/moderate", headers=_hdr(token),
                          json={"moderated": True}, timeout=15)
        assert r.status_code == 403
