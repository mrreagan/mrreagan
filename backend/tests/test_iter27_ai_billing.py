"""Phase 6C.4 — AI billing, wallet, research collab, vendor AI, assistant metering."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://birthright-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@birthright.org", "birthright2026")
ELENA = ("elena@birthright.org", "birthright2026")  # research partner
DAVID = ("demo@birthright.org", "birthright2026")  # vendor partner — demo has active vendor profile per seed
DEMO  = ("demo@birthright.org",  "birthright2026")  # participant


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    body = r.json()
    return body["token"], body["user"]


def _hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# -------------------- AI WALLET: ME --------------------

class TestAiWalletMe:
    def test_wallet_me_for_signed_in_user(self):
        token, user = _login(*DEMO)
        r = requests.get(f"{API}/ai-wallet/me", headers=_hdr(token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "wallet" in data
        w = data["wallet"]
        assert "balance_usd" in w
        assert "lifetime_topup_usd" in w
        assert "lifetime_spend_usd" in w
        assert data["topup_packs_usd"] == [10, 25, 50, 100]
        assert isinstance(data["recent_usage"], list)
        assert isinstance(data["recent_entries"], list)

    def test_wallet_me_requires_auth(self):
        r = requests.get(f"{API}/ai-wallet/me", timeout=15)
        assert r.status_code in (401, 403)


# -------------------- AUTO-RECHARGE --------------------

class TestAutoRecharge:
    def test_set_auto_recharge(self):
        token, _ = _login(*DEMO)
        r = requests.put(
            f"{API}/ai-wallet/auto-recharge",
            headers=_hdr(token),
            json={"enabled": True, "threshold_usd": 5.0, "amount_usd": 25.0},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        w = r.json()
        assert w["auto_recharge_enabled"] is True
        assert w["auto_recharge_threshold_usd"] == 5.0
        assert w["auto_recharge_amount_usd"] == 25.0

        # verify persistence via /me
        me = requests.get(f"{API}/ai-wallet/me", headers=_hdr(token)).json()
        assert me["wallet"]["auto_recharge_enabled"] is True

    def test_auto_recharge_validation(self):
        token, _ = _login(*DEMO)
        # threshold too high
        r = requests.put(
            f"{API}/ai-wallet/auto-recharge",
            headers=_hdr(token),
            json={"enabled": True, "threshold_usd": 9999, "amount_usd": 25},
            timeout=15,
        )
        assert r.status_code == 422


# -------------------- TOPUP CHECKOUT --------------------

class TestTopupCheckout:
    def test_topup_checkout_returns_stripe_url(self):
        token, _ = _login(*DEMO)
        r = requests.post(
            f"{API}/ai-wallet/topup/checkout",
            headers=_hdr(token),
            json={"amount_usd": 25.0, "origin_url": BASE_URL},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "url" in body and body["url"].startswith("http")
        assert "session_id" in body and len(body["session_id"]) > 5

    def test_topup_min_validation(self):
        token, _ = _login(*DEMO)
        r = requests.post(
            f"{API}/ai-wallet/topup/checkout",
            headers=_hdr(token),
            json={"amount_usd": 1.0, "origin_url": BASE_URL},
            timeout=15,
        )
        assert r.status_code == 422

    def test_topup_max_validation(self):
        token, _ = _login(*DEMO)
        r = requests.post(
            f"{API}/ai-wallet/topup/checkout",
            headers=_hdr(token),
            json={"amount_usd": 9999.0, "origin_url": BASE_URL},
            timeout=15,
        )
        assert r.status_code == 422


# -------------------- ADMIN: GRANT + USAGE REPORT --------------------

class TestAdminAiWallet:
    def test_admin_grant_credits_user_wallet(self):
        admin_token, _ = _login(*ADMIN)
        _, david_user = _login(*DAVID)
        david_id = david_user["id"]

        # Capture balance before
        david_token = _login(*DAVID)[0]
        before = requests.get(f"{API}/ai-wallet/me", headers=_hdr(david_token)).json()["wallet"]["balance_usd"]

        # Grant
        r = requests.post(
            f"{API}/admin/ai-wallet/grant",
            headers=_hdr(admin_token),
            json={"user_id": david_id, "amount_usd": 5.0, "note": "TEST_iter27 vendor credit"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        w = r.json()
        assert w["user_id"] == david_id
        assert w["balance_usd"] >= before + 5.0 - 1e-6

        # Verify via david's /me
        me = requests.get(f"{API}/ai-wallet/me", headers=_hdr(david_token)).json()
        assert me["wallet"]["balance_usd"] >= 5.0

    def test_admin_grant_requires_admin(self):
        token, _ = _login(*DEMO)
        r = requests.post(
            f"{API}/admin/ai-wallet/grant",
            headers=_hdr(token),
            json={"user_id": "anything", "amount_usd": 1.0},
            timeout=15,
        )
        assert r.status_code == 403

    def test_admin_usage_report(self):
        admin_token, _ = _login(*ADMIN)
        r = requests.get(
            f"{API}/admin/ai-wallet/usage-report?days=30",
            headers=_hdr(admin_token),
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "total_events" in data
        assert "total_cost_usd" in data
        assert isinstance(data["by_user_feature"], list)
        assert isinstance(data["wallets"], list)
        assert data["days"] == 30

    def test_admin_usage_report_requires_admin(self):
        token, _ = _login(*DEMO)
        r = requests.get(f"{API}/admin/ai-wallet/usage-report?days=30", headers=_hdr(token), timeout=15)
        assert r.status_code == 403


# -------------------- RESEARCH COLLAB --------------------

class TestResearchCollab:
    def test_admin_blocked_from_research_collab(self):
        admin_token, _ = _login(*ADMIN)
        r = requests.post(
            f"{API}/research-collab/suggest-tags",
            headers=_hdr(admin_token),
            json={"title": "test", "abstract": "this is a small test abstract for tagging only."},
            timeout=20,
        )
        assert r.status_code == 403
        assert "research partner" in r.text.lower()

    def test_demo_blocked_from_research_collab(self):
        token, _ = _login(*DEMO)
        r = requests.post(
            f"{API}/research-collab/suggest-tags",
            headers=_hdr(token),
            json={"title": "test", "abstract": "this is a small test abstract for tagging only."},
            timeout=20,
        )
        assert r.status_code == 403

    def test_elena_research_partner_grant_balance(self):
        """Ensure Elena has at least $1 for testing live LLM calls."""
        admin_token, _ = _login(*ADMIN)
        _, elena_user = _login(*ELENA)
        elena_token = _login(*ELENA)[0]
        me = requests.get(f"{API}/ai-wallet/me", headers=_hdr(elena_token)).json()
        if me["wallet"]["balance_usd"] < 1.0:
            r = requests.post(
                f"{API}/admin/ai-wallet/grant",
                headers=_hdr(admin_token),
                json={"user_id": elena_user["id"], "amount_usd": 5.0, "note": "TEST_iter27 elena"},
                timeout=20,
            )
            assert r.status_code == 200, r.text

    def test_elena_synthesize_literature_live(self):
        elena_token, _ = _login(*ELENA)
        r = requests.post(
            f"{API}/research-collab/synthesize-literature",
            headers=_hdr(elena_token),
            json={"topic": "attachment repair in adoptive families", "depth": "brief"},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "markdown" in data
        assert len(data["markdown"]) > 200
        assert "cost_usd" in data
        assert data["cost_usd"] >= 0.0
        # Verify the prompt sections show up
        md_lower = data["markdown"].lower()
        assert "##" in data["markdown"]  # markdown sections present

    def test_elena_suggest_tags_live(self):
        elena_token, _ = _login(*ELENA)
        r = requests.post(
            f"{API}/research-collab/suggest-tags",
            headers=_hdr(elena_token),
            json={
                "title": "Repair after rupture in adoptive dyads",
                "abstract": "We examine micro-repair sequences between adoptive parents and adolescents and how they recalibrate attachment security over a six-month window.",
            },
            timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "tags" in data or "raw" in data
        assert "cost_usd" in data


# -------------------- VENDOR AI --------------------

class TestVendorAi:
    def test_admin_blocked_from_vendor_ai(self):
        admin_token, _ = _login(*ADMIN)
        r = requests.post(
            f"{API}/vendor-ai/write-description",
            headers=_hdr(admin_token),
            json={"brief": "A linen tote bag with calm sage embroidery.", "category": "bag"},
            timeout=20,
        )
        assert r.status_code == 403

    def test_david_write_description_live(self):
        # Ensure David has credit (granted in TestAdminAiWallet, but be defensive)
        admin_token, _ = _login(*ADMIN)
        _, david_user = _login(*DAVID)
        david_token = _login(*DAVID)[0]
        me = requests.get(f"{API}/ai-wallet/me", headers=_hdr(david_token)).json()
        if me["wallet"]["balance_usd"] < 1.0:
            requests.post(
                f"{API}/admin/ai-wallet/grant",
                headers=_hdr(admin_token),
                json={"user_id": david_user["id"], "amount_usd": 5.0, "note": "TEST_iter27 david"},
                timeout=20,
            )

        r = requests.post(
            f"{API}/vendor-ai/write-description",
            headers=_hdr(david_token),
            json={"brief": "A linen tote bag with calm sage embroidery, suitable for everyday use.", "category": "bag", "target_words": 80},
            timeout=120,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "description" in data and len(data["description"]) > 50
        assert "cost_usd" in data and data["cost_usd"] > 0

    def test_david_suggest_price_live(self):
        david_token, _ = _login(*DAVID)
        r = requests.post(
            f"{API}/vendor-ai/suggest-price",
            headers=_hdr(david_token),
            json={"description": "A 100% linen tote bag, screen-printed in small batches, with soft cotton straps.", "category": "bag"},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "cost_usd" in data
        # Either parsed JSON or raw fallback
        assert ("low_usd" in data) or ("rationale" in data)


# Assistant metering tests removed alongside the agentic Concierge feature
# itself on 2026-02-09. The class previously here lives in
# /app/archive/agentic_concierge/backend/tests/test_iter27_assistant_metering_excerpt.py
# for reference. The Help assistant (/api/help) has its own dedicated test
# coverage in tests/test_iter40_help_assistant.py.
