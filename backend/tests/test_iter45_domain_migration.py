"""
Iteration 45 — Domain migration verification (@birthright.live -> @birthright.live)

Covers:
  * Login smoke for all five seeded credentialed accounts on the new domain
  * Old @birthright.live emails must be rejected (401)
  * Counsel core read flows + write-lock still intact under new email
  * Admin counsel-settings read + password rotate + restore
  * Documentation content checks (test_credentials.md, counsel guide, legal briefing)
"""
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

PW = "birthright2026"
COUNSEL_EMAIL = "counsel@birthright.live"
COUNSEL_PW = "counsel-review-2026"

NEW_ACCOUNTS = [
    ("admin@birthright.live", PW, "admin"),
    ("demo@birthright.live", PW, "participant"),
    ("elena@birthright.live", PW, "facilitator"),
    ("marcus@birthright.live", PW, "facilitator"),
    (COUNSEL_EMAIL, COUNSEL_PW, "readonly_admin"),
]


def _login(email, password):
    return requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )


def _token(email, password):
    r = _login(email, password)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:300]}"
    body = r.json()
    tok = body.get("access_token") or body.get("token")
    assert tok, f"no token in login response: {body}"
    return tok


# ---------------------------------------------------------------- login smoke
class TestNewDomainLogins:
    @pytest.mark.parametrize("email,password,role", NEW_ACCOUNTS, ids=[a[0] for a in NEW_ACCOUNTS])
    def test_login_and_role(self, email, password, role):
        r = _login(email, password)
        assert r.status_code == 200, f"{email} -> {r.status_code} {r.text[:300]}"
        data = r.json()
        tok = data.get("access_token") or data.get("token")
        assert isinstance(tok, str) and len(tok) > 10
        user = data.get("user") or {}
        assert user.get("email") == email, f"echoed email mismatch: {user}"
        assert user.get("role") == role, f"expected role {role}, got {user.get('role')}"

        # verify token works and /me agrees
        me = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {tok}"},
            timeout=30,
        )
        assert me.status_code == 200, me.text[:300]
        me_body = me.json()
        assert me_body.get("email") == email
        assert me_body.get("role") == role


# ------------------------------------------------------------- old domain 401
class TestOldDomainRejected:
    @pytest.mark.parametrize(
        "email,password",
        [
            ("admin@birthright.org", PW),
            ("counsel@birthright.org", COUNSEL_PW),
            ("demo@birthright.org", PW),
            ("elena@birthright.org", PW),
            ("marcus@birthright.org", PW),
        ],
    )
    def test_old_email_401(self, email, password):
        r = _login(email, password)
        assert r.status_code == 401, f"{email} should be 401, got {r.status_code} {r.text[:200]}"


# ---------------------------------------------------------------- counsel flows
class TestCounselFlows:
    def test_counsel_read_and_write_lock(self):
        tok = _token(COUNSEL_EMAIL, COUNSEL_PW)
        h = {"Authorization": f"Bearer {tok}"}

        pages = requests.get(f"{BASE_URL}/api/legal/pages", headers=h, timeout=30)
        assert pages.status_code == 200, pages.text[:300]
        assert isinstance(pages.json(), (list, dict))

        payload = {
            "section": "12. Limitation of Liability",
            "kind": "redline",
            "quoted_text": "US $100",
            "suggested_replacement": "US $500",
            "body": "TEST_ iter45 domain migration verification.",
        }
        created = requests.post(
            f"{BASE_URL}/api/legal/comments/01-terms-of-service",
            headers=h,
            json=payload,
            timeout=30,
        )
        assert created.status_code == 200, f"comment create -> {created.status_code} {created.text[:400]}"
        body = created.json()
        assert body.get("kind") == "redline"
        assert body.get("author_role") == "readonly_admin"
        assert body.get("author_email") in (COUNSEL_EMAIL, None)
        comment_id = body.get("id")
        assert comment_id, f"no comment id returned: {body}"

        # verify persistence
        listed = requests.get(
            f"{BASE_URL}/api/legal/comments/01-terms-of-service", headers=h, timeout=30
        )
        assert listed.status_code == 200
        assert any(c["id"] == comment_id for c in listed.json())

        # apply-roundtrip must remain write-locked for readonly_admin
        rt = requests.post(
            f"{BASE_URL}/api/legal/comments/01-terms-of-service/apply-roundtrip",
            headers=h,
            json={"decisions": []},
            timeout=30,
        )
        assert rt.status_code == 403, f"apply-roundtrip -> {rt.status_code} {rt.text[:300]}"
        assert rt.json().get("readonly") is True, rt.text[:300]

    def test_zzz_cleanup_test_comments(self):
        import asyncio

        from motor.motor_asyncio import AsyncIOMotorClient

        env = dotenv_values("/app/backend/.env")
        mongo, dbn = env.get("MONGO_URL"), env.get("DB_NAME")

        async def _go():
            c = AsyncIOMotorClient(mongo)
            res = await c[dbn].legal_doc_comments.delete_many({"body": {"$regex": "^TEST_"}})
            c.close()
            return res.deleted_count

        n = asyncio.new_event_loop().run_until_complete(_go())
        print("cleaned test comments:", n)
        assert n >= 0


# ------------------------------------------------------------------ admin flows
class TestAdminCounselSettings:
    def test_settings_and_rotate(self):
        admin_tok = _token("admin@birthright.live", PW)
        h = {"Authorization": f"Bearer {admin_tok}"}

        s = requests.get(f"{BASE_URL}/api/admin/settings/counsel", headers=h, timeout=30)
        assert s.status_code == 200, s.text[:300]
        assert s.json().get("email") == COUNSEL_EMAIL, s.json()

        temp_pw = "temp-verify-migration-2026"
        try:
            rot = requests.post(
                f"{BASE_URL}/api/admin/settings/counsel/rotate",
                headers=h,
                json={"password": temp_pw},
                timeout=30,
            )
            assert rot.status_code == 200, f"rotate -> {rot.status_code} {rot.text[:300]}"
            assert _login(COUNSEL_EMAIL, temp_pw).status_code == 200
            assert _login(COUNSEL_EMAIL, COUNSEL_PW).status_code == 401
        finally:
            restore = requests.post(
                f"{BASE_URL}/api/admin/settings/counsel/rotate",
                headers=h,
                json={"password": COUNSEL_PW},
                timeout=30,
            )
            assert restore.status_code == 200, restore.text[:300]
            assert _login(COUNSEL_EMAIL, COUNSEL_PW).status_code == 200


# --------------------------------------------------------------------- doc checks
class TestDocs:
    def test_test_credentials_md(self):
        p = Path("/app/memory/test_credentials.md")
        assert p.exists()
        text = p.read_text(encoding="utf-8")
        for email in [a[0] for a in NEW_ACCOUNTS]:
            assert email in text, f"{email} missing from test_credentials.md"
        assert "birthright.org" not in text, "test_credentials.md still references @birthright.org"

    def test_counsel_user_guide(self):
        p = Path("/app/backend/legal_docs/00a-counsel-user-guide.md")
        text = p.read_text(encoding="utf-8")
        assert "counsel@birthright.live" in text
        assert "counsel@birthright.org" not in text

    def test_legal_briefing_contact_block(self):
        p = Path("/app/backend/legal_docs/LEGAL_BRIEFING_FOR_COUNSEL.md")
        text = p.read_text(encoding="utf-8")
        assert "birthright.live" in text
        stale = re.findall(r"[\w.+-]+@birthright\.org", text)
        assert not stale, f"stale org emails: {stale}"
