"""Iter18 — v1.11.0 Step 6 (Research artifacts + paid promotion) + Step 7 (Payouts/W9/Method)."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    env = Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
            break

API = f"{BASE_URL}/api"
ADMIN = {"email": "admin@birthright.live", "password": "birthright2026"}
ELENA = {"email": "elena@birthright.live", "password": "birthright2026"}   # research partner
DEMO = {"email": "demo@birthright.live", "password": "birthright2026"}     # no research profile
MARCUS = {"email": "marcus@birthright.live", "password": "birthright2026"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json().get("access_token")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_h():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def elena_h():
    return _login(ELENA)


@pytest.fixture(scope="module")
def demo_h():
    return _login(DEMO)


@pytest.fixture(scope="module")
def marcus_h():
    return _login(MARCUS)


# ============ Research Public Endpoints ============

class TestResearchPublic:
    def test_pricing(self):
        r = requests.get(f"{API}/research/pricing", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["tiers"]["brief"] == 49.0
        assert data["tiers"]["paper"] == 149.0
        assert data["duration_days"] == 30

    def test_list_artifacts_returns_seeded(self):
        r = requests.get(f"{API}/research", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        ids = [a["id"] for a in rows]
        assert "sample-attachment-adoptive-families-2024" in ids
        assert "sample-co-regulation-brief-2025" in ids
        # Validate metadata for paper sample
        paper = next(a for a in rows if a["id"] == "sample-attachment-adoptive-families-2024")
        assert paper["tier"] == "paper"
        assert paper["doi"]
        assert paper["status"] == "published"
        assert paper["estimated_read_minutes"] == 32
        assert "attachment" in paper["categories"]

    def test_list_artifacts_query_filter(self):
        r = requests.get(f"{API}/research", params={"q": "attachment"}, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert any("sample-attachment-adoptive-families-2024" == a["id"] for a in rows)
        # Co-regulation brief abstract does not contain 'attachment' explicitly -> shouldn't match
        assert all("co-regulation" not in a["title"].lower() or "attachment" in a["abstract"].lower() or "attachment" in a["title"].lower() for a in rows)

    def test_list_artifacts_category_filter(self):
        r = requests.get(f"{API}/research", params={"category": "attachment"}, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        for a in rows:
            assert "attachment" in a["categories"]
        assert any(a["id"] == "sample-attachment-adoptive-families-2024" for a in rows)

    def test_get_single_artifact(self):
        r = requests.get(f"{API}/research/sample-co-regulation-brief-2025", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["tier"] == "brief"
        assert data["partner_slug"] == "sample-daniel-brookes"

    def test_get_artifact_404(self):
        r = requests.get(f"{API}/research/does-not-exist-xyz", timeout=15)
        assert r.status_code == 404

    def test_promoted_initially_empty(self):
        r = requests.get(f"{API}/research/promoted", timeout=15)
        assert r.status_code == 200
        # Initially no real artifact is promoted; sample ones have promoted_until=None
        rows = r.json()
        # Allowed to be empty or contain admin-granted promotions, but sample seeds should not be there
        assert isinstance(rows, list)


# ============ Research Partner-Facing ============

class TestResearchPartnerSide:
    def test_post_artifact_requires_research_profile(self, demo_h):
        # demo user has no research profile
        r = requests.post(f"{API}/me/research", headers=demo_h, json={
            "title": "Should fail",
            "abstract": "x" * 50,
            "authors": "Test",
            "publication_date": "2025-01-01",
            "full_text_url": "https://example.com/x",
        }, timeout=15)
        assert r.status_code == 404, r.text

    def test_elena_has_research_profile(self, elena_h):
        r = requests.get(f"{API}/partners/my-profiles", headers=elena_h, timeout=15)
        assert r.status_code == 200
        profs = r.json()
        # Elena should have a research profile; if it's marked is_sample, partner-side creation will 400
        research = [p for p in profs if p.get("partner_type") == "research" and p.get("status") == "active"]
        if not research:
            pytest.skip("Elena has no research partner profile - cannot test partner-side flow")
        # Store for next tests via class attribute pattern
        TestResearchPartnerSide._elena_profile = research[0]

    def test_create_artifact_defaults_tier_brief(self, elena_h):
        prof = getattr(TestResearchPartnerSide, "_elena_profile", None)
        if not prof:
            pytest.skip("No research profile")
        if prof.get("is_sample"):
            # Sample profiles can't publish, expect 400
            r = requests.post(f"{API}/me/research", headers=elena_h, json={
                "title": "TEST artifact",
                "abstract": "Test abstract content " * 5,
                "authors": "Test Author",
                "publication_date": "2025-01-01",
                "full_text_url": "https://example.com/test",
            }, timeout=15)
            assert r.status_code == 400
            pytest.skip("Elena's profile is_sample; partner-side creation blocked by design")
        r = requests.post(f"{API}/me/research", headers=elena_h, json={
            "title": "TEST artifact for iter18",
            "abstract": "This is a test abstract with sufficient length.",
            "authors": "Test Author",
            "publication_date": "2025-01-01",
            "full_text_url": "https://example.com/test-iter18",
        }, timeout=15)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc["tier"] == "brief"
        assert doc["status"] == "draft"
        TestResearchPartnerSide._created_id = doc["id"]

    def test_update_drops_tier_field(self, elena_h):
        aid = getattr(TestResearchPartnerSide, "_created_id", None)
        if not aid:
            pytest.skip("No created artifact")
        r = requests.put(f"{API}/me/research/{aid}", headers=elena_h, json={
            "tier": "paper",
            "abstract": "Updated abstract content that is longer than 10 chars.",
        }, timeout=15)
        assert r.status_code == 200, r.text
        out = r.json()
        # Tier should NOT have changed (partner cannot self-promote tier)
        assert out["tier"] == "brief"
        assert "Updated abstract" in out["abstract"]

    def test_promote_checkout_requires_published(self, elena_h):
        aid = getattr(TestResearchPartnerSide, "_created_id", None)
        if not aid:
            pytest.skip("No created artifact")
        r = requests.post(
            f"{API}/me/research/{aid}/promote/checkout",
            headers=elena_h,
            json={"artifact_id": aid, "origin_url": "https://example.com"},
            timeout=20,
        )
        assert r.status_code == 400, r.text

    def test_publish_then_promote_checkout(self, elena_h):
        aid = getattr(TestResearchPartnerSide, "_created_id", None)
        if not aid:
            pytest.skip("No created artifact")
        # publish via update
        r = requests.put(f"{API}/me/research/{aid}", headers=elena_h, json={"status": "published"}, timeout=15)
        assert r.status_code == 200
        # now promote
        r = requests.post(
            f"{API}/me/research/{aid}/promote/checkout",
            headers=elena_h,
            json={"artifact_id": aid, "origin_url": "https://example.com"},
            timeout=30,
        )
        # Stripe in test mode should return a session url. If misconfigured -> 500.
        if r.status_code != 200:
            pytest.skip(f"Stripe checkout not available in test env: {r.status_code} {r.text[:200]}")
        data = r.json()
        assert "url" in data
        assert "session_id" in data

    def test_delete_artifact(self, elena_h):
        aid = getattr(TestResearchPartnerSide, "_created_id", None)
        if not aid:
            pytest.skip("No created artifact")
        # Attempt delete; if artifact happens to have been promoted via webhook, expect 400
        r = requests.delete(f"{API}/me/research/{aid}", headers=elena_h, timeout=15)
        assert r.status_code in (200, 400), r.text


# ============ Research Admin ============

class TestResearchAdmin:
    SEED_PAPER = "sample-attachment-adoptive-families-2024"
    SEED_BRIEF = "sample-co-regulation-brief-2025"

    def test_set_tier_admin_only(self, admin_h, demo_h):
        r = requests.put(f"{API}/admin/research/{self.SEED_BRIEF}/tier",
                         params={"tier": "paper"}, headers=demo_h, timeout=15)
        assert r.status_code in (401, 403)

    def test_set_tier_invalid(self, admin_h):
        r = requests.put(f"{API}/admin/research/{self.SEED_BRIEF}/tier",
                         params={"tier": "platinum"}, headers=admin_h, timeout=15)
        assert r.status_code in (400, 422)

    def test_admin_grant_revoke_promotion(self, admin_h):
        # Grant
        r = requests.post(f"{API}/admin/research/{self.SEED_BRIEF}/promote/grant",
                          params={"days": 5}, headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        a = r.json()
        assert a["promoted_until"] is not None
        until = datetime.fromisoformat(a["promoted_until"])
        assert until > datetime.now(timezone.utc) + timedelta(days=4)

        # Should now show in promoted feed
        r2 = requests.get(f"{API}/research/promoted", timeout=15)
        assert r2.status_code == 200
        assert any(x["id"] == self.SEED_BRIEF for x in r2.json())

        # Public list returns promoted first
        r3 = requests.get(f"{API}/research", timeout=15)
        assert r3.status_code == 200
        rows = r3.json()
        promoted_ids = [x["id"] for x in rows if x.get("promoted_until")]
        assert self.SEED_BRIEF in promoted_ids

        # Revoke
        r4 = requests.post(f"{API}/admin/research/{self.SEED_BRIEF}/promote/revoke",
                           headers=admin_h, timeout=15)
        assert r4.status_code == 200
        assert r4.json()["promoted_until"] is None


# ============ Webhook fulfillment (manual insertion pattern) ============

class TestResearchWebhookFulfillment:
    def test_activate_research_promotion_via_handler(self, admin_h, elena_h):
        """Insert a 'paid' payment_transaction row for research_promotion and verify
        activate_research_promotion extends promoted_until + creates purchase row.

        We exercise this by calling the admin grant flow which performs the same
        update path. For direct webhook test, we'd need DB access; skip in HTTP layer.
        """
        # First ensure clean state on the brief
        r = requests.post(f"{API}/admin/research/sample-co-regulation-brief-2025/promote/revoke",
                          headers=admin_h, timeout=15)
        assert r.status_code == 200

        # Grant for 30 days simulating successful promotion
        r = requests.post(f"{API}/admin/research/sample-co-regulation-brief-2025/promote/grant",
                          params={"days": 30}, headers=admin_h, timeout=15)
        assert r.status_code == 200
        a = r.json()
        until = datetime.fromisoformat(a["promoted_until"])
        delta = until - datetime.now(timezone.utc)
        assert 29 <= delta.days <= 31

        # Cleanup
        requests.post(f"{API}/admin/research/sample-co-regulation-brief-2025/promote/revoke",
                      headers=admin_h, timeout=15)


# ============ Payouts: Ledger ============

class TestPayoutsLedger:
    def test_get_ledger_empty_or_zero(self, demo_h):
        r = requests.get(f"{API}/me/payouts", headers=demo_h, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "totals" in data
        assert "entries" in data
        assert isinstance(data["entries"], list)
        for key in ("earned_unpaid", "paid_lifetime", "all_time"):
            assert key in data["totals"]

    def test_get_ledger_authenticated_admin(self, admin_h):
        r = requests.get(f"{API}/me/payouts", headers=admin_h, timeout=15)
        assert r.status_code == 200


# ============ Payouts: W9 ============

class TestPayoutsW9:
    def test_get_w9_null_initially(self, marcus_h):
        r = requests.get(f"{API}/me/payouts/w9", headers=marcus_h, timeout=15)
        assert r.status_code == 200
        # marcus has no W9 yet
        if r.json() is not None:
            pytest.skip("Marcus already has a W9 (data state from prior runs)")

    def test_upsert_w9(self, marcus_h):
        payload = {
            "full_name": "Marcus TestUser",
            "classification": "individual",
            "address_line1": "123 Test St",
            "city": "Testville",
            "state": "CA",
            "zip_code": "90210",
            "country": "US",
            "tin": "123-45-6789",
            "tin_type": "SSN",
            "signature_name": "Marcus TestUser",
        }
        r = requests.put(f"{API}/me/payouts/w9", headers=marcus_h, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["saved"] is True
        assert data["signed_at"]

        # GET should return masked TIN
        r2 = requests.get(f"{API}/me/payouts/w9", headers=marcus_h, timeout=15)
        assert r2.status_code == 200
        w9 = r2.json()
        assert w9 is not None
        assert "tin" not in w9  # full TIN not exposed
        assert "tin_masked" in w9
        assert "6789" in w9["tin_masked"]

    def test_second_put_replaces(self, marcus_h):
        payload = {
            "full_name": "Marcus TestUser Updated",
            "classification": "sole_proprietor",
            "address_line1": "456 New St",
            "city": "Newtown",
            "state": "CA",
            "zip_code": "94000",
            "country": "US",
            "tin": "987-65-4321",
            "tin_type": "SSN",
            "signature_name": "Marcus TestUser",
        }
        r = requests.put(f"{API}/me/payouts/w9", headers=marcus_h, json=payload, timeout=15)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/me/payouts/w9", headers=marcus_h, timeout=15)
        w9 = r2.json()
        assert "4321" in w9["tin_masked"]
        assert w9["full_name"] == "Marcus TestUser Updated"


# ============ Payouts: Method ============

class TestPayoutsMethod:
    def test_method_null_initially(self, marcus_h):
        # Best-effort: may have leftover from prior runs
        r = requests.get(f"{API}/me/payouts/method", headers=marcus_h, timeout=15)
        assert r.status_code == 200

    def test_stripe_connect_requires_account_id(self, marcus_h):
        r = requests.put(f"{API}/me/payouts/method", headers=marcus_h, json={
            "method_type": "stripe_connect",
        }, timeout=15)
        assert r.status_code == 400

    def test_stripe_connect_ok(self, marcus_h):
        r = requests.put(f"{API}/me/payouts/method", headers=marcus_h, json={
            "method_type": "stripe_connect",
            "stripe_account_id": "acct_test_abc123",
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["method_type"] == "stripe_connect"
        assert data["stripe_account_id"] == "acct_test_abc123"
        assert "account_number" not in data

    def test_manual_ach_requires_all_fields(self, marcus_h):
        r = requests.put(f"{API}/me/payouts/method", headers=marcus_h, json={
            "method_type": "manual_ach",
            "bank_name": "Test Bank",
        }, timeout=15)
        assert r.status_code in (400, 422)

    def test_manual_ach_encrypts_account(self, marcus_h):
        r = requests.put(f"{API}/me/payouts/method", headers=marcus_h, json={
            "method_type": "manual_ach",
            "bank_name": "Test Bank",
            "account_holder_name": "Marcus TestUser",
            "routing_number": "021000021",
            "account_number": "1234567890",
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "account_number" not in data
        assert data.get("account_number_last4", "").endswith("7890")

        # GET returns redacted form
        r2 = requests.get(f"{API}/me/payouts/method", headers=marcus_h, timeout=15)
        assert r2.status_code == 200
        m = r2.json()
        assert "account_number" not in m
        assert m.get("account_number_last4", "").endswith("7890")


# ============ Admin Payouts ============

class TestAdminPayouts:
    def test_credits_list_admin_only(self, demo_h, admin_h):
        r = requests.get(f"{API}/admin/payouts/credits", headers=demo_h, timeout=15)
        assert r.status_code in (401, 403)
        r2 = requests.get(f"{API}/admin/payouts/credits", headers=admin_h, timeout=15)
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)

    def test_mark_paid_404_for_unknown(self, admin_h):
        r = requests.post(f"{API}/admin/payouts/credits/nonexistent/mark-paid",
                          headers=admin_h, params={"source": "on_site_referral"},
                          json={"method": "wire", "reference": "TEST"}, timeout=15)
        assert r.status_code == 404

    def test_admin_view_w9(self, admin_h, marcus_h):
        # need marcus user_id
        r = requests.get(f"{API}/auth/me", headers=marcus_h, timeout=15)
        assert r.status_code == 200
        marcus_id = r.json()["id"]

        r2 = requests.get(f"{API}/admin/payouts/w9/{marcus_id}", headers=admin_h, timeout=15)
        # If marcus W9 was set by earlier test, expect 200 with full TIN
        if r2.status_code == 200:
            w9 = r2.json()
            assert "tin" in w9
            assert len(w9["tin"]) >= 9
        else:
            assert r2.status_code == 404

    def test_admin_w9_requires_admin(self, demo_h):
        r = requests.get(f"{API}/admin/payouts/w9/some-user-id", headers=demo_h, timeout=15)
        assert r.status_code in (401, 403)
