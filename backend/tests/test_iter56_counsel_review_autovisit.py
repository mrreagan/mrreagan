"""Iteration 56 — counsel review-status auto_visited path-matching fix.

Covers `routers/counsel_audit.py::_slug_from_activity_path` end-to-end:
counsel hits the NEW legal endpoints, and `/api/counsel/review-status`
(admin) must show `auto_visited: true` for those slugs.
"""
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

ADMIN = {"email": "admin@birthright.live", "password": "birthright2026"}
COUNSEL = {"email": "counsel@birthright.live", "password": "counsel-review-2026"}
TERMS = "01-terms-of-service"


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=45)
    if r.status_code != 200:
        pytest.fail(f"login failed {creds['email']}: {r.status_code} {r.text[:300]}")
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def counsel_client():
    return _login(COUNSEL)


def _rows(admin_client):
    r = admin_client.get(f"{BASE_URL}/api/counsel/review-status", timeout=60)
    assert r.status_code == 200, f"review-status {r.status_code}: {r.text[:400]}"
    data = r.json()
    assert isinstance(data, list) and data, "review-status returned empty list"
    return {row["slug"]: row for row in data}


# ---------- module: counsel path->slug mapper (unit) ----------
class TestSlugMapper:
    def test_mapper_recognises_all_current_paths(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from routers.counsel_audit import _slug_from_activity_path as f

        cases = {
            "/api/legal/working-drafts/birthright-hub": "birthright-hub",
            "/api/legal/working-drafts/birthright-hub/mark-ready": "birthright-hub",
            "/api/legal/working-drafts/birthright-hub/discard": "birthright-hub",
            "/api/legal/working-drafts/birthright-hub/comments": "birthright-hub",
            "/api/legal/docs/birthright-hub/upload": "birthright-hub",
            "/api/legal/docs/birthright-hub/comments": "birthright-hub",
            "/api/legal/docs/birthright-hub": "birthright-hub",
            "/api/legal/comments/birthright-hub/export": "birthright-hub",
            "/api/legal/history-timeline/birthright-hub": "birthright-hub",
            "/api/legal/pages/birthright-hub": "birthright-hub",
            "/api/legal/drafts/birthright-hub": "birthright-hub",
            "/api/legal/docs/counsel-briefing-docx": "counsel-briefing",
            "/api/legal/docs/counsel-briefing": "counsel-briefing",
        }
        for path, expected in cases.items():
            assert f(path) == expected, f"{path} -> {f(path)} (want {expected})"

        for path in ("/api/products", "/api/legal/pages", "", "/api/legal/ratifications"):
            assert f(path) is None, f"{path} should not map, got {f(path)}"


# ---------- feature: auto_visited flips after counsel activity ----------
class TestAutoVisited:
    def test_counsel_activity_then_auto_visited_true(self, counsel_client, admin_client):
        before = _rows(admin_client).get(TERMS)
        assert before is not None, f"{TERMS} missing from review-status"
        before_count = before["auto_visit_count"]

        # counsel activity on the new endpoints
        r1 = counsel_client.get(f"{BASE_URL}/api/legal/working-drafts/{TERMS}", timeout=60)
        assert r1.status_code in (200, 404), f"WD fetch {r1.status_code}: {r1.text[:200]}"
        r2 = counsel_client.get(f"{BASE_URL}/api/legal/history-timeline/{TERMS}", timeout=60)
        assert r2.status_code == 200, f"history-timeline {r2.status_code}: {r2.text[:200]}"
        r3 = counsel_client.get(f"{BASE_URL}/api/legal/comments/{TERMS}", timeout=60)
        assert r3.status_code == 200, f"comments list {r3.status_code}: {r3.text[:200]}"

        after = _rows(admin_client)[TERMS]
        assert after["auto_visited"] is True, "auto_visited still False after counsel activity"
        assert after["auto_visit_count"] > before_count, (
            f"visit count did not grow: {before_count} -> {after['auto_visit_count']}"
        )
        assert after["auto_last_visited_at"], "auto_last_visited_at not populated"
        assert after["auto_last_visited_by"] == COUNSEL["email"], (
            f"auto_last_visited_by = {after['auto_last_visited_by']}"
        )

    def test_comment_post_counts_as_visit(self, counsel_client, admin_client):
        before = _rows(admin_client)[TERMS]["auto_visit_count"]
        r = counsel_client.post(
            f"{BASE_URL}/api/legal/comments/{TERMS}",
            json={"body": "TEST_iter56 automated verification comment", "kind": "comment"},
            timeout=60,
        )
        assert r.status_code in (200, 201), f"post comment {r.status_code}: {r.text[:300]}"
        cid = r.json().get("id")
        after = _rows(admin_client)[TERMS]
        assert after["auto_visit_count"] > before
        assert after["auto_visited"] is True
        # cleanup
        if cid:
            counsel_client.delete(f"{BASE_URL}/api/legal/comments/{TERMS}/{cid}", timeout=45)

    def test_counsel_briefing_prefix_still_matches(self, counsel_client, admin_client):
        before = _rows(admin_client)["counsel-briefing"]["auto_visit_count"]
        r = counsel_client.get(f"{BASE_URL}/api/legal/docs/counsel-briefing-docx", timeout=60)
        assert r.status_code == 200, f"briefing download {r.status_code}"
        after = _rows(admin_client)["counsel-briefing"]
        assert after["auto_visited"] is True
        assert after["auto_visit_count"] > before

    def test_legacy_draft_path_still_counts(self, counsel_client, admin_client):
        slug = "02-privacy-policy"
        before = _rows(admin_client)[slug]["auto_visit_count"]
        r = counsel_client.get(f"{BASE_URL}/api/legal/drafts/{slug}", timeout=60)
        assert r.status_code == 200, f"legacy draft {r.status_code}: {r.text[:200]}"
        after = _rows(admin_client)[slug]
        assert after["auto_visited"] is True
        assert after["auto_visit_count"] > before

    def test_admin_activity_not_logged_as_counsel_visit(self, admin_client):
        """Admin browsing must NOT inflate counsel visit counts (middleware
        only logs readonly_admin)."""
        slug = "03-cookie-notice"
        before = _rows(admin_client)[slug]["auto_visit_count"]
        r = admin_client.get(f"{BASE_URL}/api/legal/drafts/{slug}", timeout=60)
        assert r.status_code == 200
        after = _rows(admin_client)[slug]["auto_visit_count"]
        assert after == before, "admin activity leaked into counsel visit aggregation"


# ---------- feature: manual mark still works ----------
class TestManualMark:
    def test_manual_mark_roundtrip(self, admin_client):
        slug = "13-ombudsman-charter"
        r = admin_client.put(
            f"{BASE_URL}/api/counsel/review-status/{slug}",
            json={"reviewed": True, "initials": "QA", "notes": "TEST_iter56"},
            timeout=45,
        )
        assert r.status_code == 200, f"mark {r.status_code}: {r.text[:300]}"
        row = _rows(admin_client)[slug]
        assert row["manual_reviewed"] is True
        assert row["manual_initials"] == "QA"
        # revert
        r2 = admin_client.put(
            f"{BASE_URL}/api/counsel/review-status/{slug}",
            json={"reviewed": False},
            timeout=45,
        )
        assert r2.status_code == 200
        assert _rows(admin_client)[slug]["manual_reviewed"] is False

    def test_unknown_slug_404(self, admin_client):
        r = admin_client.put(
            f"{BASE_URL}/api/counsel/review-status/TEST_nope",
            json={"reviewed": True},
            timeout=45,
        )
        assert r.status_code == 404
