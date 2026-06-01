"""Iter 44 — Partnership Agreement v2 re-sign hardening.

Covers admin UI endpoints, gate broadening (research/payouts/studio),
per-partner blocked_actions list, publish flow, admin bypass and sign.

Important: publishing a new version flips active state and would
break gating for other tests in the suite. We use a unique version
string and (a) restore the prior active version at teardown, OR
(b) re-sign as the affected fixtures. We pick a teardown rollback.
"""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@birthright.org"
ELENA_EMAIL = "elena@birthright.org"
DEMO_EMAIL = "demo@birthright.org"
PWD = "birthright2026"


def _login(email):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL)


@pytest.fixture(scope="module")
def elena_token():
    return _login(ELENA_EMAIL)


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---- (2) versions list ----
def test_versions_list(admin_token):
    r = requests.get(f"{API}/legal/indemnification/versions", headers=H(admin_token), timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "versions" in d and "active_partner_count" in d
    assert isinstance(d["active_partner_count"], int)
    assert isinstance(d["versions"], list) and len(d["versions"]) >= 1
    for v in d["versions"]:
        assert "signature_count" in v
        assert isinstance(v["signature_count"], int)


# ---- (3) default v2 draft ----
def test_default_v2_draft(admin_token):
    r = requests.get(f"{API}/legal/indemnification/default-v2-draft", headers=H(admin_token), timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["version"] == "2.0"
    assert "summary_of_changes" in d
    assert len(d["body"]) >= 7000, f"body length only {len(d['body'])}"


def test_default_v2_draft_requires_admin(elena_token):
    r = requests.get(f"{API}/legal/indemnification/default-v2-draft", headers=H(elena_token), timeout=20)
    assert r.status_code in (401, 403), r.status_code


# ---- (4) signatures hydration ----
def test_signatures_hydration(admin_token):
    # Pick the active version id from versions list
    r = requests.get(f"{API}/legal/indemnification/versions", headers=H(admin_token), timeout=20)
    versions = r.json()["versions"]
    active = next((v for v in versions if v.get("active")), versions[0])
    r2 = requests.get(
        f"{API}/legal/indemnification/signatures",
        headers=H(admin_token),
        params={"version_id": active["id"]},
        timeout=20,
    )
    assert r2.status_code == 200, r2.text
    sigs = r2.json()
    assert isinstance(sigs, list)
    for s in sigs:
        assert "user_email" in s
        assert "ip_address" in s


# ---- (6) blocked_actions list for elena (research partner) ----
def test_elena_blocked_actions(elena_token):
    r = requests.get(f"{API}/legal/indemnification/my-status", headers=H(elena_token), timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    if d.get("signed"):
        pytest.skip("Elena already signed active version; cannot validate unsigned blocked list")
    blocked = set(d.get("blocked_actions") or [])
    expected = {
        "Open new direct message threads",
        "Start or change a subscription",
        "Generate new AI Studio drafts",
        "Publish research artifacts",
        "Purchase featured slots",
        "Update W9 or payout method",
    }
    missing = expected - blocked
    assert not missing, f"Elena missing blocked actions: {missing}; got={blocked}"


# ---- (7) Gate: elena POST /api/me/research ----
def test_gate_fires_research(elena_token):
    payload = {"title": "TEST artifact", "summary": "x" * 80, "kind": "report"}
    r = requests.post(f"{API}/me/research", headers=H(elena_token), json=payload, timeout=20)
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "agreement_required"
    assert "active_version" in detail


# ---- (8) Gate: elena PUT /api/me/payouts/w9 ----
def test_gate_fires_w9(elena_token):
    payload = {"full_name": "Elena Test", "tin_last4": "1234", "address_line1": "1 Main", "city": "C", "state": "CA", "zip": "94000"}
    r = requests.put(f"{API}/me/payouts/w9", headers=H(elena_token), json=payload, timeout=20)
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "agreement_required"


# ---- (9) Gate: elena PUT /api/me/payouts/method ----
def test_gate_fires_payout_method(elena_token):
    payload = {"method": "ach", "account_last4": "1234"}
    r = requests.put(f"{API}/me/payouts/method", headers=H(elena_token), json=payload, timeout=20)
    assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"
    assert r.json().get("detail", {}).get("code") == "agreement_required"


# ---- (10) Admin bypass on /studio/generate ----
def test_admin_bypass_studio(admin_token):
    payload = {"brief": "Write a short blurb about a memoir on family healing.", "tone": "warm"}
    r = requests.post(f"{API}/studio/generate", headers=H(admin_token), json=payload, timeout=60)
    assert r.status_code != 409, f"admin got blocked by gate: {r.status_code} {r.text}"


# ---- (11) Admin bypass on /me/research and /me/payouts/w9 ----
def test_admin_bypass_research(admin_token):
    payload = {"title": "TEST admin artifact", "summary": "x" * 80, "kind": "report"}
    r = requests.post(f"{API}/me/research", headers=H(admin_token), json=payload, timeout=20)
    assert r.status_code != 409, f"admin blocked on research: {r.status_code} {r.text}"


def test_admin_bypass_w9(admin_token):
    payload = {"full_name": "Admin Test", "tin_last4": "9999", "address_line1": "1 Main", "city": "C", "state": "CA", "zip": "94000"}
    r = requests.put(f"{API}/me/payouts/w9", headers=H(admin_token), json=payload, timeout=20)
    assert r.status_code != 409, f"admin blocked on w9: {r.status_code} {r.text}"


# ---- (13) Agreement page: active version body ----
def test_active_version_returns_body():
    r = requests.get(f"{API}/legal/indemnification/active", timeout=20)
    # active is public
    assert r.status_code == 200, r.text
    d = r.json()
    assert "body" in d and isinstance(d["body"], str) and len(d["body"]) > 0
    assert "version" in d


# ---- (14) Sign flow — make a NEW signature for a throwaway demo session ----
# We DO NOT sign elena (other tests rely on her being unsigned).
# Instead we sign as a fresh-ish user via demo, then verify my-status.
def test_demo_sign_flow():
    token = _login(DEMO_EMAIL)
    r0 = requests.get(f"{API}/legal/indemnification/my-status", headers=H(token), timeout=20)
    assert r0.status_code == 200
    r1 = requests.post(f"{API}/legal/indemnification/sign", headers=H(token), timeout=20)
    assert r1.status_code == 200, r1.text
    r2 = requests.get(f"{API}/legal/indemnification/my-status", headers=H(token), timeout=20)
    assert r2.status_code == 200
    d = r2.json()
    assert d.get("signed") is True
    assert d.get("blocked_actions") == []


# ---- (5) Publish flow (must run LAST in this file) ----
# Marked with a high alphabetic order via name; pytest runs in definition order
# within a file by default, so this is placed at the end.
def test_publish_new_version_and_rollback(admin_token):
    # 1. Capture current active version id so we can restore
    r0 = requests.get(f"{API}/legal/indemnification/versions", headers=H(admin_token), timeout=20)
    assert r0.status_code == 200
    prior_versions = r0.json()["versions"]
    prior_active = next((v for v in prior_versions if v.get("active")), None)
    assert prior_active is not None, "No active version found before publish"

    # 2. Publish a unique throwaway version
    unique_v = f"t44-{int(time.time())}"  # must be <=20 chars per IndemnificationCreate
    body = "x" * 7500  # long enough to be plausible
    r = requests.post(
        f"{API}/legal/indemnification/versions",
        headers=H(admin_token),
        json={"version": unique_v, "body": body, "summary_of_changes": "test publish"},
        timeout=30,
    )
    assert r.status_code == 200, f"publish failed: {r.status_code} {r.text}"
    new_doc = r.json()
    assert new_doc["version"] == unique_v
    assert new_doc["active"] is True

    # 3. Verify it is now the active version
    r2 = requests.get(f"{API}/legal/indemnification/active", timeout=20)
    assert r2.status_code == 200
    assert r2.json()["version"] == unique_v

    # 4. ROLLBACK — restore prior active by directly hitting Mongo via API is not
    # possible, so we re-publish a record-restore? Not allowed (duplicate version
    # check). Instead, use a small admin-side workaround via direct DB ops.
    # We import db inline to perform rollback (this runs INSIDE the same container).
    try:
        import asyncio
        import sys
        sys.path.insert(0, "/app/backend")
        from database import db  # type: ignore

        async def _rollback():
            await db.indemnification_versions.update_many({"active": True}, {"$set": {"active": False}})
            await db.indemnification_versions.update_one(
                {"id": prior_active["id"]}, {"$set": {"active": True}}
            )
            await db.foundation_settings.update_one(
                {"key": "global_defaults"},
                {"$set": {"indemnification_active_version_id": prior_active["id"]}},
                upsert=True,
            )
            # Delete the throwaway test version doc so versions list stays clean
            await db.indemnification_versions.delete_one({"id": new_doc["id"]})
        asyncio.get_event_loop().run_until_complete(_rollback())
    except Exception as ex:
        pytest.fail(f"rollback failed (active version is still throwaway!): {ex}")

    # 5. Confirm rollback
    r3 = requests.get(f"{API}/legal/indemnification/active", timeout=20)
    assert r3.status_code == 200
    assert r3.json()["version"] == prior_active["version"], "rollback did not restore prior active"
