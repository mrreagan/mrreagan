"""Iter15 — Foundation Roles + Sample Partners (Phase 6B.4.5b/c)"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Read from frontend .env as fallback
    from pathlib import Path
    env = Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break

API = f"{BASE_URL}/api"

ADMIN_CREDS = {"email": "admin@birthright.live", "password": "birthright2026"}
SAMPLE_SLUGS = {
    "facilitator": ["sample-maya-chen", "sample-aaron-kalu"],
    "vendor": ["sample-quiet-hours-studio", "sample-hearth-practice"],
    "community": ["sample-pat-lindholm", "sample-liz-okonkwo"],
    "research": ["sample-imani-okafor", "sample-daniel-brookes"],
}
ROLE_SLUGS = ["board-chair-cofounder", "research-advisor", "director-community-stewardship"]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json=ADMIN_CREDS, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    token = r.json().get("token") or r.json().get("access_token")
    assert token
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ============ Public foundation-roles ============

class TestPublicFoundationRoles:
    def test_list_open_roles(self):
        r = requests.get(f"{API}/foundation-roles", params={"open_only": "true"}, timeout=15)
        assert r.status_code == 200
        roles = r.json()
        assert isinstance(roles, list)
        slugs = {x["slug"] for x in roles}
        for s in ROLE_SLUGS:
            assert s in slugs, f"missing seeded role slug: {s}"
        # All should be open
        for role in roles:
            if role["slug"] in ROLE_SLUGS:
                assert role["open"] is True
                for field in ("title", "headline", "who_you_are", "what_youll_do",
                              "what_you_bring", "compensation_summary", "time_commitment"):
                    assert role.get(field), f"missing field {field} for {role['slug']}"
                # seeded_member_id should be present (linked to existing governing members)
                assert "seeded_member_id" in role
                assert role["seeded_member_id"] is not None, f"seeded_member_id is None for {role['slug']}"

    def test_get_single_role(self):
        r = requests.get(f"{API}/foundation-roles/board-chair-cofounder", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == "board-chair-cofounder"
        assert data["title"] == "Board Chair & Co-Founder"
        # Compensation summary doesn't contain dollar amounts
        assert "$" not in data["compensation_summary"]

    def test_get_unknown_role_404(self):
        r = requests.get(f"{API}/foundation-roles/does-not-exist-xyz", timeout=15)
        assert r.status_code == 404


# ============ Applications submission ============

class TestApplicationSubmission:
    def test_submit_valid_application(self):
        r = requests.post(
            f"{API}/foundation-role-applications",
            json={
                "role_slug": "board-chair-cofounder",
                "name": "TEST Applicant Iter15",
                "email": "test_iter15@example.com",
                "current_role": "Senior practitioner",
                "why_drawn": "TEST iter15 — drawn to relational healing and governance for many years.",
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "new"
        assert data["role_slug"] == "board-chair-cofounder"
        assert "id" in data
        pytest.app_id = data["id"]

    def test_submit_unknown_role_404(self):
        r = requests.post(
            f"{API}/foundation-role-applications",
            json={
                "role_slug": "does-not-exist-xyz",
                "name": "TEST Applicant Iter15",
                "email": "test_iter15_unknown@example.com",
                "why_drawn": "TEST iter15 long enough text to pass validation 1234.",
            },
            timeout=15,
        )
        assert r.status_code == 404

    def test_submit_short_why_drawn_422(self):
        r = requests.post(
            f"{API}/foundation-role-applications",
            json={
                "role_slug": "board-chair-cofounder",
                "name": "X",
                "email": "x@example.com",
                "why_drawn": "too short",
            },
            timeout=15,
        )
        assert r.status_code == 422


# ============ Admin foundation-roles auth & CRUD ============

class TestAdminFoundationRolesAuth:
    def test_admin_list_no_auth(self):
        r = requests.get(f"{API}/admin/foundation-roles", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_list_with_auth(self, admin_headers):
        r = requests.get(f"{API}/admin/foundation-roles", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        roles = r.json()
        slugs = {x["slug"] for x in roles}
        for s in ROLE_SLUGS:
            assert s in slugs


class TestAdminFoundationRolesCRUD:
    test_slug = "test-iter15-temp-role"

    def test_create_role(self, admin_headers):
        # cleanup if exists
        requests.delete(f"{API}/admin/foundation-roles/{self.test_slug}", headers=admin_headers)
        payload = {
            "slug": self.test_slug,
            "title": "TEST Temp Role iter15",
            "headline": "Temporary role for iter15 testing.",
            "who_you_are": "Someone test iter15.",
            "what_youll_do": "Things test iter15.",
            "what_you_bring": "Bringing test iter15.",
            "time_commitment": "1 hr/week",
            "compensation_summary": "Equity in mission.",
            "order": 99,
            "open": True,
        }
        r = requests.post(f"{API}/admin/foundation-roles", json=payload,
                          headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["slug"] == self.test_slug

    def test_create_duplicate_400(self, admin_headers):
        payload = {
            "slug": self.test_slug,
            "title": "duplicate title test",
            "headline": "Dup headline iter15 testing.",
            "who_you_are": "Dup iter15 who_you_are.",
            "what_youll_do": "Dup iter15 what_youll_do.",
            "what_you_bring": "Dup iter15 what_you_bring.",
            "time_commitment": "1 hr/week",
            "compensation_summary": "Equity in mission.",
            "order": 99, "open": True,
        }
        r = requests.post(f"{API}/admin/foundation-roles", json=payload,
                          headers=admin_headers, timeout=15)
        assert r.status_code == 400

    def test_update_role(self, admin_headers):
        r = requests.put(
            f"{API}/admin/foundation-roles/{self.test_slug}",
            json={"title": "TEST Temp Role iter15 UPDATED"},
            headers=admin_headers, timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["title"] == "TEST Temp Role iter15 UPDATED"

    def test_delete_role(self, admin_headers):
        r = requests.delete(f"{API}/admin/foundation-roles/{self.test_slug}",
                            headers=admin_headers, timeout=15)
        assert r.status_code == 200
        # Verify gone
        r2 = requests.get(f"{API}/foundation-roles/{self.test_slug}", timeout=15)
        assert r2.status_code == 404


# ============ Admin applications queue ============

class TestAdminApplicationsQueue:
    def test_list_no_auth(self):
        r = requests.get(f"{API}/admin/foundation-role-applications", timeout=15)
        assert r.status_code in (401, 403)

    def test_list_with_status_filter(self, admin_headers):
        r = requests.get(f"{API}/admin/foundation-role-applications",
                         params={"status": "new"}, headers=admin_headers, timeout=15)
        assert r.status_code == 200
        apps = r.json()
        assert isinstance(apps, list)
        # All should have status=new
        for a in apps:
            assert a["status"] == "new"

    def test_decision_invalid_status(self, admin_headers):
        # Get any app id
        r = requests.get(f"{API}/admin/foundation-role-applications",
                         headers=admin_headers, timeout=15)
        apps = r.json()
        if not apps:
            pytest.skip("no applications to decide on")
        app_id = apps[0]["id"]
        r2 = requests.post(
            f"{API}/admin/foundation-role-applications/{app_id}/decision",
            params={"status": "bogus"},
            json={"admin_note": "test"},
            headers=admin_headers, timeout=15,
        )
        assert r2.status_code == 400

    def test_decision_valid_status_moves(self, admin_headers):
        # Find the test app we submitted
        r = requests.get(f"{API}/admin/foundation-role-applications",
                         headers=admin_headers, timeout=15)
        apps = r.json()
        target = next((a for a in apps if a.get("email") == "test_iter15@example.com"), None)
        if not target:
            pytest.skip("test app not found")
        app_id = target["id"]
        r2 = requests.post(
            f"{API}/admin/foundation-role-applications/{app_id}/decision",
            params={"status": "reviewing"},
            json={"admin_note": "TEST iter15"},
            headers=admin_headers, timeout=15,
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "reviewing"

    def test_cleanup_test_apps(self, admin_headers):
        """Cleanup TEST_ apps via direct DB (not endpoint exposed, but ok via mongo)."""
        # No delete endpoint exists publicly; just leave under reviewing status.
        # Not blocking.
        pass


# ============ Partners samples query ============

class TestPartnersSamples:
    def test_default_excludes_samples(self):
        r = requests.get(f"{API}/partners", timeout=15)
        assert r.status_code == 200
        partners = r.json()
        all_sample_slugs = {s for slugs in SAMPLE_SLUGS.values() for s in slugs}
        returned_slugs = {p["slug"] for p in partners}
        # No overlap
        assert not (returned_slugs & all_sample_slugs), \
            f"default /partners leaked samples: {returned_slugs & all_sample_slugs}"
        # No is_sample=True row
        for p in partners:
            assert not p.get("is_sample", False), f"is_sample=True in default list: {p['slug']}"

    def test_samples_only_returns_8(self):
        r = requests.get(f"{API}/partners", params={"samples": 1}, timeout=15)
        assert r.status_code == 200
        partners = r.json()
        assert len(partners) == 8, f"expected 8 samples, got {len(partners)}"
        slugs = {p["slug"] for p in partners}
        all_sample_slugs = {s for ss in SAMPLE_SLUGS.values() for s in ss}
        assert slugs == all_sample_slugs
        for p in partners:
            assert p.get("is_sample") is True

    def test_samples_filter_by_type(self):
        r = requests.get(f"{API}/partners",
                         params={"samples": 1, "partner_type": "facilitator"}, timeout=15)
        assert r.status_code == 200
        partners = r.json()
        assert len(partners) == 2
        slugs = {p["slug"] for p in partners}
        assert slugs == set(SAMPLE_SLUGS["facilitator"])

    def test_get_sample_partner_detail(self):
        r = requests.get(f"{API}/partners/sample-maya-chen", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == "sample-maya-chen"
        assert data.get("is_sample") is True
        assert data["partner_type"] == "facilitator"
