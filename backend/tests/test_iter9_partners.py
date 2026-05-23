"""Iter 9 — Partner Onboarding Foundation (Phase 6B.1) backend tests.

Covers:
- Applicant: /partners/apply, /partners/my-applications, /partners/my-profiles, PUT /partners/my-profiles/{type}
- Public: GET /partners, GET /partners/{slug}
- Admin: /admin/partners/invite, applications list, approve, reject, revoke, reinstate
- Regression: governance/legal/reviews/workshops still respond
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

def _read_env_file(path: str) -> str:
    try:
        with open(path, "r") as fh:
            for line in fh:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        return ""
    return ""


def _load_backend_url() -> str:
    val = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not val:
        val = _read_env_file("/app/frontend/.env")
    return val.rstrip("/")


BASE_URL = _load_backend_url()
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

ADMIN = ("admin@birthright.org", "birthright2026")
ELENA = ("elena@birthright.org", "birthright2026")
DEMO = ("demo@birthright.org", "birthright2026")


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def tokens() -> dict:
    return {
        "admin": _login(*ADMIN),
        "elena": _login(*ELENA),
        "demo": _login(*DEMO),
    }


# ====== /partners/apply ======
class TestApply:
    def test_apply_anonymous_401(self):
        r = requests.post(f"{API}/partners/apply", json={
            "partner_type": "community", "headline": "Helping bring this work to my circle",
            "bio": "I have been running a small community circle for over two years and want to refer participants."
        }, timeout=20)
        assert r.status_code in (401, 403), r.text

    def test_apply_facilitator_missing_presents_400(self, tokens):
        # Use elena fresh (no prior facilitator profile)
        r = requests.post(f"{API}/partners/apply", headers=_h(tokens["elena"]), json={
            "partner_type": "facilitator",
            "headline": "Seasoned facilitator with 10 yrs",
            "bio": "I have over a decade of experience facilitating attachment-focused workshops.",
        }, timeout=20)
        assert r.status_code == 400, r.text
        assert "Birthright IP" in r.text or "birthright ip" in r.text.lower()

    def test_apply_headline_too_short_422(self, tokens):
        r = requests.post(f"{API}/partners/apply", headers=_h(tokens["elena"]), json={
            "partner_type": "research",
            "headline": "abc",
            "bio": "long enough bio content to pass the minimum threshold xxxxxx",
        }, timeout=20)
        assert r.status_code == 422

    def test_apply_bio_too_short_422(self, tokens):
        r = requests.post(f"{API}/partners/apply", headers=_h(tokens["elena"]), json={
            "partner_type": "research",
            "headline": "Looking to bring this to academia",
            "bio": "short",
        }, timeout=20)
        assert r.status_code == 422

    def test_demo_already_has_community_profile_blocks_reapply(self, tokens):
        # Demo has approved community profile per pre-state
        r = requests.post(f"{API}/partners/apply", headers=_h(tokens["demo"]), json={
            "partner_type": "community",
            "headline": "Another community application",
            "bio": "Trying to reapply when already approved should fail with 400 explicitly.",
        }, timeout=20)
        assert r.status_code == 400, r.text
        assert "already" in r.text.lower()

    def test_apply_research_then_block_pending_reapply(self, tokens):
        # Use elena → apply research (idempotency aware: if pending exists already, that's fine)
        first = requests.post(f"{API}/partners/apply", headers=_h(tokens["elena"]), json={
            "partner_type": "research",
            "headline": "Bringing this work into research",
            "bio": "I want to study attachment outcomes for cohort participants in a longitudinal way.",
        }, timeout=20)
        # accept 200/201 OR 400 if pending already exists from a prior test run
        assert first.status_code in (200, 201, 400), first.text
        # Now re-applying must fail
        second = requests.post(f"{API}/partners/apply", headers=_h(tokens["elena"]), json={
            "partner_type": "research",
            "headline": "Bringing this work into research again",
            "bio": "Second attempt should be blocked because pending application exists.",
        }, timeout=20)
        assert second.status_code == 400, second.text
        assert "pending" in second.text.lower() or "already" in second.text.lower()

    def test_facilitator_with_presents_birthright_ip_succeeds(self, tokens):
        # ensure elena doesn't already have one
        existing = requests.get(f"{API}/partners/my-applications", headers=_h(tokens["elena"]), timeout=20).json()
        has_fac_pending = any(a["partner_type"] == "facilitator" and a["status"] == "pending" for a in existing)
        if has_fac_pending:
            pytest.skip("elena already has pending facilitator application; idempotent skip")
        r = requests.post(f"{API}/partners/apply", headers=_h(tokens["elena"]), json={
            "partner_type": "facilitator",
            "headline": "Experienced Birthright-aligned facilitator",
            "bio": "Senior facilitator with over a decade of work; intends to teach Birthright IP.",
            "presents_birthright_ip": True,
            "credentials": "MA Counseling",
        }, timeout=20)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body["partner_type"] == "facilitator"
        assert body["status"] == "pending"
        assert body["data"]["presents_birthright_ip"] is True


# ====== /partners/my-applications + my-profiles ======
class TestMyApplicationsAndProfiles:
    def test_my_applications_requires_auth(self):
        r = requests.get(f"{API}/partners/my-applications", timeout=20)
        assert r.status_code in (401, 403)

    def test_demo_my_applications_returns_only_own(self, tokens):
        r = requests.get(f"{API}/partners/my-applications", headers=_h(tokens["demo"]), timeout=20)
        assert r.status_code == 200
        apps = r.json()
        assert isinstance(apps, list)
        # all rows must be demo's; we don't know demo's id directly but check newest-first
        if len(apps) >= 2:
            assert apps[0]["created_at"] >= apps[1]["created_at"]

    def test_demo_my_profiles_includes_community(self, tokens):
        r = requests.get(f"{API}/partners/my-profiles", headers=_h(tokens["demo"]), timeout=20)
        assert r.status_code == 200
        profiles = r.json()
        types = [p["partner_type"] for p in profiles]
        assert "community" in types, f"expected community profile for demo, got {types}"


# ====== PUT /partners/my-profiles/{type} ======
class TestUpdateMyProfile:
    def test_invalid_partner_type_400(self, tokens):
        r = requests.put(f"{API}/partners/my-profiles/wizard", headers=_h(tokens["demo"]),
                         json={"headline": "Updated headline"}, timeout=20)
        assert r.status_code == 400

    def test_no_such_profile_404(self, tokens):
        # demo doesn't have research profile
        r = requests.put(f"{API}/partners/my-profiles/research", headers=_h(tokens["demo"]),
                         json={"headline": "Updated headline now longer"}, timeout=20)
        assert r.status_code == 404

    def test_update_community_profile_persists(self, tokens):
        new_headline = f"Updated by iter9 test {uuid.uuid4().hex[:6]}"
        r = requests.put(f"{API}/partners/my-profiles/community", headers=_h(tokens["demo"]),
                         json={"headline": new_headline, "location": "Brooklyn, NY"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["headline"] == new_headline
        assert body["location"] == "Brooklyn, NY"
        # GET via public directory and confirm
        time.sleep(0.3)
        listing = requests.get(f"{API}/partners", params={"partner_type": "community"}, timeout=20).json()
        match = next((p for p in listing if p["slug"] == body["slug"]), None)
        assert match is not None
        assert match["headline"] == new_headline


# ====== Public directory ======
class TestPublicDirectory:
    def test_public_list_no_auth(self):
        r = requests.get(f"{API}/partners", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # only status=active & public=true
        for p in items:
            assert p["status"] == "active"
            assert p["public"] is True

    def test_sam_rivera_visible_in_directory(self):
        items = requests.get(f"{API}/partners", timeout=20).json()
        slugs = [p["slug"] for p in items]
        assert "sam-rivera-community" in slugs, f"expected sam-rivera-community in {slugs}"

    def test_partner_type_filter(self):
        items = requests.get(f"{API}/partners", params={"partner_type": "community"}, timeout=20).json()
        assert all(p["partner_type"] == "community" for p in items)

    def test_search_q_short_ignored(self):
        # q with 1 char must not error and returns same as no filter (no $or applied)
        r = requests.get(f"{API}/partners", params={"q": "a"}, timeout=20)
        assert r.status_code == 200

    def test_search_q_filters(self):
        # Searching for the well-known sam-rivera headline keyword
        items = requests.get(f"{API}/partners", params={"q": "Sam"}, timeout=20).json()
        # Either matches Sam Rivera or empty if headline doesn't contain "Sam";
        # at minimum should not throw and result list filtered by regex
        assert isinstance(items, list)

    def test_get_partner_by_slug(self):
        r = requests.get(f"{API}/partners/sam-rivera-community", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["slug"] == "sam-rivera-community"
        assert body["status"] == "active"

    def test_get_unknown_slug_404(self):
        r = requests.get(f"{API}/partners/no-such-partner-xyz", timeout=20)
        assert r.status_code == 404

    def test_invalid_partner_type_filter_400(self):
        r = requests.get(f"{API}/partners", params={"partner_type": "wizard"}, timeout=20)
        assert r.status_code == 400


# ====== Admin invite + applications list ======
class TestAdminInviteAndList:
    def test_invite_requires_admin(self, tokens):
        r = requests.post(f"{API}/admin/partners/invite", headers=_h(tokens["demo"]),
                          json={"email": "x@example.com", "partner_type": "vendor"}, timeout=20)
        assert r.status_code in (401, 403)

    def test_admin_invite_creates_pending(self, tokens):
        unique_email = f"iter9-vendor-{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/admin/partners/invite", headers=_h(tokens["admin"]),
                          json={"email": unique_email, "partner_type": "vendor",
                                "admin_note": "iter9 invite test"}, timeout=20)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body["status"] == "pending"
        assert body["invitee_email"] == unique_email
        assert body["partner_type"] == "vendor"
        assert body.get("invited_by_admin_id")
        TestAdminInviteAndList.invited_app_id = body["id"]
        TestAdminInviteAndList.invited_email = unique_email

    def test_applications_list_filters(self, tokens):
        r = requests.get(f"{API}/admin/partners/applications",
                         headers=_h(tokens["admin"]),
                         params={"status": "pending", "partner_type": "vendor"}, timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert all(a["status"] == "pending" and a["partner_type"] == "vendor" for a in items)
        # enrichment fields present
        if items:
            assert "applicant_email" in items[0]
            assert "applicant_name" in items[0]

    def test_approve_invite_without_user_fails(self, tokens):
        # The invited email is not a registered user → approve should 400
        app_id = TestAdminInviteAndList.invited_app_id
        r = requests.post(f"{API}/admin/partners/applications/{app_id}/approve",
                          headers=_h(tokens["admin"]), json={"admin_note": ""}, timeout=20)
        assert r.status_code == 400, r.text
        assert "user" in r.text.lower() or "register" in r.text.lower()

    def test_non_admin_list_403(self, tokens):
        r = requests.get(f"{API}/admin/partners/applications",
                         headers=_h(tokens["demo"]), timeout=20)
        assert r.status_code in (401, 403)


# ====== Approve / Reject ======
class TestApproveReject:
    def test_approve_elena_research_then_reject_branch(self, tokens):
        # Find elena's pending research application
        apps = requests.get(f"{API}/admin/partners/applications",
                            headers=_h(tokens["admin"]),
                            params={"status": "pending", "partner_type": "research"}, timeout=20).json()
        elena_app = next((a for a in apps if a.get("applicant_email") == "elena@birthright.org"), None)
        if not elena_app:
            pytest.skip("No elena research pending app to approve")
        r = requests.post(f"{API}/admin/partners/applications/{elena_app['id']}/approve",
                          headers=_h(tokens["admin"]), json={"admin_note": "Welcome!"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["application_status"] == "approved"
        profile = body["profile"]
        assert profile["partner_type"] == "research"
        assert profile["status"] == "active"
        assert profile["public"] is True
        assert profile["slug"]
        TestApproveReject.research_profile_id = profile["id"]
        TestApproveReject.research_slug = profile["slug"]

        # Approving again → 400
        r2 = requests.post(f"{API}/admin/partners/applications/{elena_app['id']}/approve",
                           headers=_h(tokens["admin"]), json={"admin_note": ""}, timeout=20)
        assert r2.status_code == 400

    def test_approved_profile_visible_in_directory(self, tokens):
        slug = getattr(TestApproveReject, "research_slug", None)
        if not slug:
            pytest.skip("no profile approved in prior test")
        r = requests.get(f"{API}/partners/{slug}", timeout=20)
        assert r.status_code == 200

    def test_reject_facilitator_app(self, tokens):
        # Find elena pending facilitator
        apps = requests.get(f"{API}/admin/partners/applications",
                            headers=_h(tokens["admin"]),
                            params={"status": "pending", "partner_type": "facilitator"}, timeout=20).json()
        elena_app = next((a for a in apps if a.get("applicant_email") == "elena@birthright.org"), None)
        if not elena_app:
            pytest.skip("no elena pending facilitator app")
        r = requests.post(f"{API}/admin/partners/applications/{elena_app['id']}/reject",
                          headers=_h(tokens["admin"]),
                          json={"admin_note": "Testing rejection branch"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "rejected"
        assert body["admin_note"] == "Testing rejection branch"


# ====== Revoke / Reinstate ======
class TestRevokeReinstate:
    def test_revoke_then_reinstate_research_profile(self, tokens):
        profile_id = getattr(TestApproveReject, "research_profile_id", None)
        slug = getattr(TestApproveReject, "research_slug", None)
        if not profile_id:
            pytest.skip("no research profile to revoke")

        r = requests.post(f"{API}/admin/partners/profiles/{profile_id}/revoke",
                          headers=_h(tokens["admin"]),
                          json={"admin_note": "iter9 test revoke"}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "revoked"
        assert body["public"] is False

        # No longer in public directory
        listing = requests.get(f"{API}/partners", timeout=20).json()
        assert all(p["id"] != profile_id for p in listing)
        # And slug 404
        r404 = requests.get(f"{API}/partners/{slug}", timeout=20)
        assert r404.status_code == 404

        # Update on revoked → 403
        r_upd = requests.put(f"{API}/partners/my-profiles/research", headers=_h(tokens["elena"]),
                             json={"headline": "trying to update revoked"}, timeout=20)
        assert r_upd.status_code == 403

        # Reinstate
        r2 = requests.post(f"{API}/admin/partners/profiles/{profile_id}/reinstate",
                           headers=_h(tokens["admin"]), timeout=20)
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["status"] == "active"
        assert b2["public"] is True


# ====== Regression ======
class TestRegression:
    def test_governance_defaults(self):
        r = requests.get(f"{API}/governance/defaults", timeout=20)
        assert r.status_code == 200

    def test_legal_indemnification_active(self):
        r = requests.get(f"{API}/legal/indemnification/active", timeout=20)
        # 200 if present; 404 acceptable only if endpoint exists but no active row
        assert r.status_code in (200, 404)

    def test_reviews_search(self):
        r = requests.get(f"{API}/reviews/search", timeout=20)
        assert r.status_code == 200

    def test_workshops_list(self):
        r = requests.get(f"{API}/workshops", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
