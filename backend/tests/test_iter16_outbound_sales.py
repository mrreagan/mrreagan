"""Iter16 — v1.11.0 Step 2 + 3: Outbound clicks + Off-site sales reconciliation."""
import hashlib
import hmac
import json
import os
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
ADMIN_CREDS = {"email": "admin@birthright.live", "password": "birthright2026"}
DEMO_CREDS = {"email": "demo@birthright.live", "password": "birthright2026"}

SAMPLE_VENDOR = "sample-quiet-hours-studio"  # has external_site_url set
SAMPLE_VENDOR_EXT = "https://example.com/quiet-hours-shop"
DEMO_VENDOR_SLUG = "sam-rivera-vendor"


# ============ Fixtures ============

@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{API}/auth/login", json=ADMIN_CREDS, timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json().get("access_token")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def demo_headers():
    r = requests.post(f"{API}/auth/login", json=DEMO_CREDS, timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json().get("token") or r.json().get("access_token")
    return {"Authorization": f"Bearer {tok}"}


# ============ Step 2: Outbound click attribution ============

class TestOutboundRedirect:
    def test_known_slug_302_to_external(self):
        r = requests.get(f"{API}/out/{SAMPLE_VENDOR}", allow_redirects=False, timeout=15)
        assert r.status_code == 302
        assert r.headers["location"] == SAMPLE_VENDOR_EXT

    def test_unknown_slug_redirects_to_partners(self):
        r = requests.get(f"{API}/out/this-slug-does-not-exist", allow_redirects=False, timeout=15)
        assert r.status_code == 302
        assert r.headers["location"] == "/partners"

    def test_dest_same_host_honored(self):
        dest = "https://example.com/quiet-hours-shop/path"
        r = requests.get(f"{API}/out/{SAMPLE_VENDOR}", params={"dest": dest},
                         allow_redirects=False, timeout=15)
        assert r.status_code == 302
        assert r.headers["location"] == dest

    def test_dest_cross_host_ignored(self):
        r = requests.get(f"{API}/out/{SAMPLE_VENDOR}", params={"dest": "https://evil.com/x"},
                         allow_redirects=False, timeout=15)
        assert r.status_code == 302
        assert r.headers["location"] == SAMPLE_VENDOR_EXT

    def test_utm_params_logged(self, admin_headers):
        # Trigger a click with UTM
        r = requests.get(
            f"{API}/out/{SAMPLE_VENDOR}",
            params={"utm_source": "newsletter", "utm_campaign": "may"},
            allow_redirects=False, timeout=15,
        )
        assert r.status_code == 302
        # Read back the latest click via admin list
        clicks = requests.get(f"{API}/admin/outbound-clicks",
                              params={"partner_slug": SAMPLE_VENDOR},
                              headers=admin_headers, timeout=15).json()
        assert isinstance(clicks, list) and len(clicks) > 0
        latest = clicks[0]
        assert latest["partner_slug"] == SAMPLE_VENDOR
        assert latest["partner_type"] == "vendor"
        assert latest["dest_url"] == SAMPLE_VENDOR_EXT
        assert latest.get("utm_params", {}).get("utm_source") == "newsletter"
        assert latest.get("utm_params", {}).get("utm_campaign") == "may"
        # Required fields exist
        for k in ("partner_id", "user_id", "session_id", "referrer",
                  "user_agent", "ip", "is_sample", "created_at"):
            assert k in latest, f"missing key {k}"
        assert latest["is_sample"] is True
        assert len(latest.get("user_agent") or "") <= 500


# ============ Step 3: Partner self-report ============

class TestPartnerSelfReport:
    def test_submit_community_report(self, demo_headers):
        payload = {
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
            "gross_revenue_usd": 500.00,
            "attributed_orders": 5,
            "note": "TEST iter16 community",
        }
        r = requests.post(f"{API}/partner-sales-reports",
                          params={"partner_type": "community"},
                          json=payload, headers=demo_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "submitted"
        assert data["source"] == "self_report"
        assert "id" in data
        assert data["partner_type"] == "community"
        pytest.community_report_id = data["id"]

    def test_submit_vendor_report(self, demo_headers):
        payload = {
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "gross_revenue_usd": 1000.00,
            "attributed_orders": 10,
            "note": "TEST iter16 vendor self",
        }
        r = requests.post(f"{API}/partner-sales-reports",
                          params={"partner_type": "vendor"},
                          json=payload, headers=demo_headers, timeout=15)
        assert r.status_code == 200, r.text
        pytest.vendor_report_id = r.json()["id"]

    def test_no_active_profile_404(self, demo_headers):
        # facilitator profile doesn't exist for demo
        payload = {
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
            "gross_revenue_usd": 100,
            "attributed_orders": 1,
        }
        r = requests.post(f"{API}/partner-sales-reports",
                          params={"partner_type": "facilitator"},
                          json=payload, headers=demo_headers, timeout=15)
        assert r.status_code == 404

    def test_invalid_period_400(self, demo_headers):
        payload = {
            "period_start": "2026-05-31",
            "period_end": "2026-05-01",
            "gross_revenue_usd": 10,
            "attributed_orders": 1,
        }
        r = requests.post(f"{API}/partner-sales-reports",
                          params={"partner_type": "community"},
                          json=payload, headers=demo_headers, timeout=15)
        assert r.status_code == 400

    def test_list_my_reports(self, demo_headers):
        r = requests.get(f"{API}/partner-sales-reports/my",
                         headers=demo_headers, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        ids = {row["id"] for row in rows}
        assert pytest.community_report_id in ids
        assert pytest.vendor_report_id in ids


# ============ Webhook mint + rotate ============

class TestWebhookMintRotate:
    def test_get_webhook_info_idempotent(self, demo_headers):
        r1 = requests.get(f"{API}/partner-sales-reports/my/webhook",
                          params={"partner_type": "community"},
                          headers=demo_headers, timeout=15)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert d1["signature_header"] == "X-Birthright-Signature"
        assert "secret" in d1 and len(d1["secret"]) >= 32
        assert "webhook_path" in d1
        assert "sample_payload" in d1
        # Idempotent
        r2 = requests.get(f"{API}/partner-sales-reports/my/webhook",
                          params={"partner_type": "community"},
                          headers=demo_headers, timeout=15)
        assert r2.json()["secret"] == d1["secret"]
        pytest.community_secret = d1["secret"]
        pytest.community_webhook_path = d1["webhook_path"]

    def test_regenerate_rotates(self, demo_headers):
        prev = pytest.community_secret
        r = requests.post(f"{API}/partner-sales-reports/my/webhook/regenerate",
                          params={"partner_type": "community"},
                          headers=demo_headers, timeout=15)
        assert r.status_code == 200
        new_secret = r.json()["secret"]
        assert new_secret != prev
        pytest.community_secret = new_secret


# ============ HMAC Webhook submit ============

class TestWebhookSubmit:
    def test_missing_signature_401(self, demo_headers):
        # Use community profile slug from demo (sam-rivera-community)
        # Find slug via /my/webhook info
        info = requests.get(f"{API}/partner-sales-reports/my/webhook",
                            params={"partner_type": "community"},
                            headers=demo_headers, timeout=15).json()
        path = info["webhook_path"]
        url = f"{BASE_URL}{path}"
        r = requests.post(url, data=json.dumps({"period_start": "2026-06-01",
                                                "period_end": "2026-06-30",
                                                "gross_revenue_usd": 1,
                                                "attributed_orders": 1}),
                          headers={"Content-Type": "application/json"}, timeout=15)
        assert r.status_code == 401

    def test_wrong_signature_401(self, demo_headers):
        info = requests.get(f"{API}/partner-sales-reports/my/webhook",
                            params={"partner_type": "community"},
                            headers=demo_headers, timeout=15).json()
        url = f"{BASE_URL}{info['webhook_path']}"
        body = json.dumps({"period_start": "2026-06-01", "period_end": "2026-06-30",
                           "gross_revenue_usd": 200, "attributed_orders": 2})
        r = requests.post(url, data=body, headers={
            "Content-Type": "application/json",
            "X-Birthright-Signature": "sha256=deadbeef",
        }, timeout=15)
        assert r.status_code == 401

    def test_valid_signature_creates_report(self, demo_headers):
        info = requests.get(f"{API}/partner-sales-reports/my/webhook",
                            params={"partner_type": "community"},
                            headers=demo_headers, timeout=15).json()
        secret = info["secret"]
        url = f"{BASE_URL}{info['webhook_path']}"
        payload = {
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
            "gross_revenue_usd": 800.0,
            "attributed_orders": 8,
            "note": "TEST iter16 webhook",
        }
        body = json.dumps(payload)
        sig = "sha256=" + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        r = requests.post(url, data=body, headers={
            "Content-Type": "application/json",
            "X-Birthright-Signature": sig,
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["received"] is True
        assert d["status"] == "submitted"
        pytest.webhook_report_id = d["report_id"]

    def test_partner_without_minted_secret_400(self, admin_headers):
        # Use a sample partner whose secret has never been minted.
        # sample-hearth-practice is vendor and has no webhook_secret by default.
        url = f"{API}/webhooks/partner-sales/sample-hearth-practice"
        body = json.dumps({"period_start": "2026-06-01", "period_end": "2026-06-30",
                           "gross_revenue_usd": 1, "attributed_orders": 1})
        r = requests.post(url, data=body, headers={
            "Content-Type": "application/json",
            "X-Birthright-Signature": "sha256=00",
        }, timeout=15)
        # Should be 400 unless that profile was minted previously.
        assert r.status_code in (400, 401), r.text


# ============ Admin: list + decisions ============

class TestAdminDecisions:
    def test_admin_list_protected(self):
        r = requests.get(f"{API}/admin/partner-sales-reports", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_list_with_filter(self, admin_headers):
        r = requests.get(f"{API}/admin/partner-sales-reports",
                         params={"status": "submitted"},
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200
        for row in r.json():
            assert row["status"] == "submitted"

    def test_dispute_no_credit(self, admin_headers):
        rid = pytest.vendor_report_id
        r = requests.post(
            f"{API}/admin/partner-sales-reports/{rid}/decision",
            params={"status": "dispute"},
            json={"admin_note": "TEST iter16 dispute"},
            headers=admin_headers, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "disputed"
        assert r.json().get("credit_id") in (None, "")

    def test_revise_allows_resubmit(self, admin_headers, demo_headers):
        # Submit fresh, revise, ensure status='revised'
        payload = {
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
            "gross_revenue_usd": 300.0,
            "attributed_orders": 3,
            "note": "TEST iter16 revise",
        }
        r = requests.post(f"{API}/partner-sales-reports",
                          params={"partner_type": "vendor"},
                          json=payload, headers=demo_headers, timeout=15)
        assert r.status_code == 200
        rid = r.json()["id"]
        r2 = requests.post(
            f"{API}/admin/partner-sales-reports/{rid}/decision",
            params={"status": "revise"},
            json={"admin_note": "Please refine notes"},
            headers=admin_headers, timeout=15,
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "revised"

    def test_approve_creates_credit(self, admin_headers):
        rid = pytest.community_report_id
        r = requests.post(
            f"{API}/admin/partner-sales-reports/{rid}/decision",
            params={"status": "approve"},
            json={"admin_note": "TEST iter16 approve"},
            headers=admin_headers, timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "approved"
        assert d["credit_id"]
        assert d["approved_pct"] is not None
        assert d["approved_pct_source"] in ("override", "fallback_subscription",
                                            "fallback_global_default", "fallback_none")
        assert d["approved_gross_usd"] == 500.0
        # payout = gross * pct / 100
        expected = round(500.0 * float(d["approved_pct"]) / 100, 2)
        assert d["approved_payout_usd"] == expected
        pytest.credit_id_approved = d["credit_id"]

    def test_approve_overrides(self, admin_headers, demo_headers):
        # Create a new report
        payload = {
            "period_start": "2026-02-01",
            "period_end": "2026-02-28",
            "gross_revenue_usd": 100.0,
            "attributed_orders": 1,
            "note": "TEST iter16 override approve",
        }
        rid = requests.post(f"{API}/partner-sales-reports",
                            params={"partner_type": "community"},
                            json=payload, headers=demo_headers, timeout=15).json()["id"]
        r = requests.post(
            f"{API}/admin/partner-sales-reports/{rid}/decision",
            params={"status": "approve"},
            json={"admin_note": "override test",
                  "override_gross_usd": 200.0,
                  "override_pct": 25.0},
            headers=admin_headers, timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["approved_pct"] == 25.0
        assert d["approved_gross_usd"] == 200.0
        assert d["approved_payout_usd"] == 50.0
        assert d["approved_pct_source"] == "admin_override"

    def test_double_approve_400(self, admin_headers):
        rid = pytest.community_report_id  # already approved
        r = requests.post(
            f"{API}/admin/partner-sales-reports/{rid}/decision",
            params={"status": "approve"},
            json={"admin_note": "again"},
            headers=admin_headers, timeout=15,
        )
        assert r.status_code == 400

    def test_invalid_status_400(self, admin_headers, demo_headers):
        # Fresh report
        payload = {
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "gross_revenue_usd": 100.0,
            "attributed_orders": 1,
        }
        rid = requests.post(f"{API}/partner-sales-reports",
                            params={"partner_type": "community"},
                            json=payload, headers=demo_headers, timeout=15).json()["id"]
        r = requests.post(
            f"{API}/admin/partner-sales-reports/{rid}/decision",
            params={"status": "bogus"},
            json={"admin_note": "x"},
            headers=admin_headers, timeout=15,
        )
        assert r.status_code == 400

    def test_non_admin_403(self, demo_headers):
        r = requests.get(f"{API}/admin/partner-sales-reports",
                         headers=demo_headers, timeout=15)
        assert r.status_code == 403
