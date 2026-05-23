"""Iteration 7 / Phase 6A.2 — Governance & Legal Architecture backend tests.

Covers:
- GET/PUT /api/governance/defaults (admin gating, audit log)
- GET/PUT /api/governance/members (flags, ombudsman implies governance_member)
- POST/GET /api/governance/proposals + voting + close lifecycle
- /api/legal/indemnification (active, versions, sign, my-status)
- /api/audit (admin OR ombudsman read-only)
- UserProfile flags exposure on /api/auth/me
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://birthright-hub.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@birthright.org", "password": "birthright2026"}
ELENA = {"email": "elena@birthright.org", "password": "birthright2026"}
MARCUS = {"email": "marcus@birthright.org", "password": "birthright2026"}
DEMO = {"email": "demo@birthright.org", "password": "birthright2026"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.text}"
    return r.json()["token"], r.json()["user"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


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
def demo_auth():
    return _login(DEMO)


# ---------- /api/auth/me — Phase 6A.2 fields ----------

class TestUserProfileFlags:
    def test_admin_has_both_flags(self, admin_auth):
        token, user = admin_auth
        r = requests.get(f"{API}/auth/me", headers=_hdr(token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("governance_member") is True
        assert data.get("is_ombudsman") is True

    def test_demo_has_no_flags(self, demo_auth):
        token, _ = demo_auth
        r = requests.get(f"{API}/auth/me", headers=_hdr(token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("governance_member") is False
        assert data.get("is_ombudsman") is False

    def test_facilitator_is_governance_member(self, elena_auth):
        token, _ = elena_auth
        r = requests.get(f"{API}/auth/me", headers=_hdr(token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("governance_member") is True
        assert data.get("is_ombudsman") is False


# ---------- /api/governance/defaults ----------

class TestGlobalDefaults:
    def test_get_singleton_keys(self):
        r = requests.get(f"{API}/governance/defaults", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "rev_share" in d
        for ptype in ("facilitator", "community", "research", "vendor"):
            assert ptype in d["rev_share"], f"missing rev_share key: {ptype}"
            assert isinstance(d["rev_share"][ptype], list)

    def test_non_admin_put_forbidden(self, demo_auth):
        token, _ = demo_auth
        r = requests.put(
            f"{API}/governance/defaults",
            headers=_hdr(token),
            json={"min_listing_rating": 1.0},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_admin_put_updates_and_audits(self, admin_auth):
        token, _ = admin_auth
        current = requests.get(f"{API}/governance/defaults", timeout=15).json()
        new_rev = dict(current["rev_share"])
        # Bump facilitator pct safely
        fac = list(new_rev.get("facilitator", []))
        if fac:
            fac[0] = {**fac[0], "pct": 72.5}
        else:
            fac = [{"name": "standard", "pct": 72.5, "description": "test"}]
        new_rev["facilitator"] = fac
        r = requests.put(
            f"{API}/governance/defaults",
            headers=_hdr(token),
            json={"rev_share": new_rev, "min_listing_rating": 0.5},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["min_listing_rating"] == 0.5
        assert out["rev_share"]["facilitator"][0]["pct"] == 72.5

        # audit entry exists
        audit = requests.get(
            f"{API}/audit",
            headers=_hdr(token),
            params={"action_prefix": "governance.defaults.update", "limit": 5},
            timeout=15,
        )
        assert audit.status_code == 200
        rows = audit.json()
        assert any(e["action"] == "governance.defaults.update" for e in rows), "no audit row for defaults.update"


# ---------- /api/governance/members ----------

class TestMembers:
    def test_list_signed_in(self, demo_auth):
        token, _ = demo_auth
        r = requests.get(f"{API}/governance/members", headers=_hdr(token), timeout=15)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        # admin should appear with both flags true
        admin_row = next((m for m in rows if m.get("role") == "admin"), None)
        assert admin_row is not None, "admin not found in members list"
        assert admin_row["governance_member"] is True
        assert admin_row["is_ombudsman"] is True

    def test_non_admin_put_forbidden(self, demo_auth):
        token, user = demo_auth
        r = requests.put(
            f"{API}/governance/members/{user['id']}",
            headers=_hdr(token),
            json={"governance_member": True},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_admin_set_then_revert(self, admin_auth, demo_auth):
        a_token, _ = admin_auth
        _, demo_user = demo_auth
        # Set demo as ombudsman -> should implicitly set governance_member True
        r = requests.put(
            f"{API}/governance/members/{demo_user['id']}",
            headers=_hdr(a_token),
            json={"is_ombudsman": True},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        updated = r.json()
        assert updated["is_ombudsman"] is True
        assert updated["governance_member"] is True

        # Revert
        r2 = requests.put(
            f"{API}/governance/members/{demo_user['id']}",
            headers=_hdr(a_token),
            json={"is_ombudsman": False, "governance_member": False},
            timeout=15,
        )
        assert r2.status_code == 200
        rev = r2.json()
        assert rev["is_ombudsman"] is False
        assert rev["governance_member"] is False


# ---------- /api/governance/proposals ----------

class TestProposals:
    @pytest.fixture(scope="class")
    def created_proposal(self, elena_auth):
        token, _ = elena_auth
        title = f"Test proposal {int(time.time())}"
        r = requests.post(
            f"{API}/governance/proposals",
            headers=_hdr(token),
            json={
                "title": title,
                "summary": "Trying out the proposal create endpoint.",
                "body": "Body content with at least twenty characters of meaningful text.",
                "category": "policy",
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        return r.json()

    def test_participant_cannot_create(self, demo_auth):
        token, _ = demo_auth
        r = requests.post(
            f"{API}/governance/proposals",
            headers=_hdr(token),
            json={
                "title": "Demo wants to propose",
                "summary": "I am not a governance member but trying.",
                "body": "Body text with enough characters to pass validation here.",
            },
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_short_title_422(self, elena_auth):
        token, _ = elena_auth
        r = requests.post(
            f"{API}/governance/proposals",
            headers=_hdr(token),
            json={
                "title": "abc",
                "summary": "Short title test case.",
                "body": "Body content with at least twenty characters of meaningful text.",
            },
            timeout=15,
        )
        assert r.status_code == 422

    def test_short_body_422(self, elena_auth):
        token, _ = elena_auth
        r = requests.post(
            f"{API}/governance/proposals",
            headers=_hdr(token),
            json={
                "title": "Valid title here",
                "summary": "Short body test case.",
                "body": "too short",
            },
            timeout=15,
        )
        assert r.status_code == 422

    def test_created_status_open_and_closes_at(self, created_proposal):
        p = created_proposal
        assert p["status"] == "open"
        assert p["yes_count"] == 0 and p["no_count"] == 0 and p["abstain_count"] == 0
        assert p.get("voting_closes_at"), "voting_closes_at missing"

    def test_audit_entry_for_create(self, admin_auth, created_proposal):
        a_token, _ = admin_auth
        r = requests.get(
            f"{API}/audit",
            headers=_hdr(a_token),
            params={"action_prefix": "governance.proposal.create", "limit": 50},
            timeout=15,
        )
        assert r.status_code == 200
        assert any(e.get("target_id") == created_proposal["id"] for e in r.json())

    def test_list_filters(self, created_proposal):
        r = requests.get(f"{API}/governance/proposals", params={"status": "open"}, timeout=15)
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert created_proposal["id"] in ids

        r2 = requests.get(
            f"{API}/governance/proposals", params={"category": "policy"}, timeout=15
        )
        assert r2.status_code == 200
        for p in r2.json():
            assert p["category"] == "policy"

    def test_get_single_and_404(self, created_proposal):
        r = requests.get(f"{API}/governance/proposals/{created_proposal['id']}", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == created_proposal["id"]
        r2 = requests.get(f"{API}/governance/proposals/non-existent-id-xyz", timeout=15)
        assert r2.status_code == 404


# ---------- Voting ----------

class TestVoting:
    @pytest.fixture(scope="class")
    def proposal(self, elena_auth):
        token, _ = elena_auth
        r = requests.post(
            f"{API}/governance/proposals",
            headers=_hdr(token),
            json={
                "title": f"Voting proposal {int(time.time())}",
                "summary": "Used by vote tests.",
                "body": "Body content with at least twenty characters of meaningful text.",
                "category": "policy",
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        return r.json()

    def test_non_governance_cannot_vote(self, demo_auth, proposal):
        token, _ = demo_auth
        r = requests.post(
            f"{API}/governance/proposals/{proposal['id']}/vote",
            headers=_hdr(token),
            json={"vote": "yes"},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_vote_yes_then_recast_no(self, marcus_auth, proposal):
        token, user = marcus_auth
        r1 = requests.post(
            f"{API}/governance/proposals/{proposal['id']}/vote",
            headers=_hdr(token),
            json={"vote": "yes", "comment": "Initial yes"},
            timeout=15,
        )
        assert r1.status_code == 200, r1.text
        t1 = r1.json()
        assert t1.get("yes_count", 0) >= 1

        r2 = requests.post(
            f"{API}/governance/proposals/{proposal['id']}/vote",
            headers=_hdr(token),
            json={"vote": "no", "comment": "Changed mind"},
            timeout=15,
        )
        assert r2.status_code == 200
        t2 = r2.json()
        # The voter's yes should have decreased and no should have increased
        assert t2["no_count"] >= 1

        # Only one row per voter
        lst = requests.get(
            f"{API}/governance/proposals/{proposal['id']}/votes",
            headers=_hdr(token),
            timeout=15,
        )
        assert lst.status_code == 200
        my_rows = [v for v in lst.json() if v["voter_id"] == user["id"]]
        assert len(my_rows) == 1, f"expected 1 vote row, got {len(my_rows)}"
        assert my_rows[0]["vote"] == "no"


# ---------- Close lifecycle ----------

class TestCloseProposal:
    def _new_proposal(self, token):
        r = requests.post(
            f"{API}/governance/proposals",
            headers=_hdr(token),
            json={
                "title": f"Close proposal {int(time.time()*1000)}",
                "summary": "Used by close tests.",
                "body": "Body content with at least twenty characters of meaningful text.",
                "category": "policy",
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        return r.json()

    def test_admin_close_passes_with_yes_majority(self, admin_auth, elena_auth, marcus_auth):
        e_token, _ = elena_auth
        p = self._new_proposal(e_token)
        # yes vote from marcus
        m_token, _ = marcus_auth
        requests.post(
            f"{API}/governance/proposals/{p['id']}/vote",
            headers=_hdr(m_token),
            json={"vote": "yes"},
            timeout=15,
        )
        a_token, _ = admin_auth
        r = requests.post(
            f"{API}/governance/proposals/{p['id']}/close",
            headers=_hdr(a_token),
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "passed"

        # Re-close yields 400
        r2 = requests.post(
            f"{API}/governance/proposals/{p['id']}/close",
            headers=_hdr(a_token),
            timeout=15,
        )
        assert r2.status_code == 400

    def test_admin_close_fails_with_no_majority(self, admin_auth, elena_auth, marcus_auth):
        e_token, _ = elena_auth
        p = self._new_proposal(e_token)
        m_token, _ = marcus_auth
        requests.post(
            f"{API}/governance/proposals/{p['id']}/vote",
            headers=_hdr(m_token),
            json={"vote": "no"},
            timeout=15,
        )
        a_token, _ = admin_auth
        r = requests.post(
            f"{API}/governance/proposals/{p['id']}/close",
            headers=_hdr(a_token),
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "failed"

    def test_proposer_only_close_is_withdrawn(self, elena_auth):
        e_token, _ = elena_auth
        p = self._new_proposal(e_token)
        # Elena (proposer, not admin/ombudsman) closes own
        r = requests.post(
            f"{API}/governance/proposals/{p['id']}/close",
            headers=_hdr(e_token),
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "withdrawn"

    def test_ineligible_close_forbidden(self, elena_auth, demo_auth):
        e_token, _ = elena_auth
        p = self._new_proposal(e_token)
        d_token, _ = demo_auth
        r = requests.post(
            f"{API}/governance/proposals/{p['id']}/close",
            headers=_hdr(d_token),
            timeout=15,
        )
        assert r.status_code == 403


# ---------- Legal Indemnification ----------

class TestLegalIndemnification:
    def test_active_auto_bootstrap(self):
        r = requests.get(f"{API}/legal/indemnification/active", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["active"] is True
        assert d.get("version")
        assert d.get("body")

    def test_sign_idempotent_for_demo(self, demo_auth):
        token, _ = demo_auth
        r1 = requests.post(
            f"{API}/legal/indemnification/sign", headers=_hdr(token), timeout=15
        )
        assert r1.status_code == 200, r1.text
        # Either freshly signed or already signed; both acceptable
        r2 = requests.post(
            f"{API}/legal/indemnification/sign", headers=_hdr(token), timeout=15
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2.get("already_signed") is True
        assert d2.get("signed_at")

    def test_my_status_signed_true(self, demo_auth):
        token, _ = demo_auth
        # Ensure signed
        requests.post(f"{API}/legal/indemnification/sign", headers=_hdr(token), timeout=15)
        r = requests.get(
            f"{API}/legal/indemnification/my-status", headers=_hdr(token), timeout=15
        )
        assert r.status_code == 200
        d = r.json()
        assert d["signed"] is True

    def test_publish_new_version_resets_signature(self, admin_auth, demo_auth):
        a_token, _ = admin_auth
        d_token, _ = demo_auth
        ver = f"test-{int(time.time())}"
        body = "Updated indemnification body content with more than fifty characters of test text to satisfy validator."
        r = requests.post(
            f"{API}/legal/indemnification/versions",
            headers=_hdr(a_token),
            json={"version": ver, "body": body, "summary_of_changes": "Test publish"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        new_v = r.json()
        assert new_v["active"] is True

        # active endpoint should reflect new version
        active = requests.get(f"{API}/legal/indemnification/active", timeout=15).json()
        assert active["version"] == ver
        assert active["id"] == new_v["id"]

        # demo's signed status should flip to false (since version_id changed)
        st = requests.get(
            f"{API}/legal/indemnification/my-status", headers=_hdr(d_token), timeout=15
        ).json()
        assert st["signed"] is False

        # Duplicate publish -> 400
        dup = requests.post(
            f"{API}/legal/indemnification/versions",
            headers=_hdr(a_token),
            json={"version": ver, "body": body},
            timeout=15,
        )
        assert dup.status_code == 400

        # global_defaults pointer updated
        gd = requests.get(f"{API}/governance/defaults", timeout=15).json()
        assert gd.get("indemnification_active_version_id") == new_v["id"]

        # audit entry
        audit = requests.get(
            f"{API}/audit",
            headers=_hdr(a_token),
            params={"action_prefix": "legal.indemnification.activate", "limit": 20},
            timeout=15,
        )
        assert audit.status_code == 200
        assert any(e.get("target_id") == new_v["id"] for e in audit.json())


# ---------- Audit log gating ----------

class TestAudit:
    def test_admin_can_read(self, admin_auth):
        token, _ = admin_auth
        r = requests.get(f"{API}/audit", headers=_hdr(token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_participant_forbidden(self, demo_auth):
        token, _ = demo_auth
        r = requests.get(f"{API}/audit", headers=_hdr(token), timeout=15)
        assert r.status_code == 403

    def test_facilitator_non_ombudsman_forbidden(self, elena_auth):
        token, _ = elena_auth
        r = requests.get(f"{API}/audit", headers=_hdr(token), timeout=15)
        assert r.status_code == 403

    def test_filter_action_prefix(self, admin_auth):
        token, _ = admin_auth
        r = requests.get(
            f"{API}/audit",
            headers=_hdr(token),
            params={"action_prefix": "governance.", "limit": 50},
            timeout=15,
        )
        assert r.status_code == 200
        for e in r.json():
            assert e["action"].startswith("governance.")
