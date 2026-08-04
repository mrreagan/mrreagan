"""Iteration 35 — verification of the strict-admin gate on
/api/admin/settings/counsel (counsel/readonly_admin must get 403 on read too).
"""
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = base_url.rstrip("/") + "/api"

ADMIN = ("admin@birthright.org", "birthright2026")
COUNSEL = ("counsel@birthright.org", "counsel-review-2026")


def token(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text[:300]}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok, f"no token in login response: {data}"
    return tok


def hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return token(*ADMIN)


@pytest.fixture(scope="module")
def counsel_token():
    return token(*COUNSEL)


class TestCounselStrictGate:
    """Counsel (readonly_admin) must not read or write counsel credentials."""

    def test_counsel_get_forbidden(self, counsel_token):
        r = requests.get(f"{BASE}/admin/settings/counsel", headers=hdr(counsel_token), timeout=30)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text[:300]}"
        assert "env_password_default_in_use" not in r.text

    def test_counsel_rotate_forbidden(self, counsel_token):
        r = requests.post(
            f"{BASE}/admin/settings/counsel/rotate",
            json={"password": "counsel-tries-this-2026"},
            headers=hdr(counsel_token), timeout=30,
        )
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text[:300]}"

    def test_counsel_credentials_unchanged_after_attempt(self):
        # counsel login still works with documented password
        token(*COUNSEL)


class TestAdminRegression:
    """Admin retains full access (200 read + 200 rotate)."""

    def test_admin_get_ok(self, admin_token):
        r = requests.get(f"{BASE}/admin/settings/counsel", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        d = r.json()
        assert d.get("seeded") is True
        assert isinstance(d.get("email"), str) and "@" in d["email"]
        assert "env_password_default_in_use" in d
        assert "_id" not in d

    def test_admin_rotate_and_restore(self, admin_token):
        # rotate password to a temp value, verify login, then restore
        tmp_pw = "temp-rotate-pw-2026"
        r = requests.post(
            f"{BASE}/admin/settings/counsel/rotate",
            json={"password": tmp_pw}, headers=hdr(admin_token), timeout=30,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        body = r.json()
        assert body.get("ok") is True
        assert body.get("password_changed") is True

        assert token(COUNSEL[0], tmp_pw)

        # restore documented default
        rr = requests.post(
            f"{BASE}/admin/settings/counsel/rotate",
            json={"email": COUNSEL[0], "password": COUNSEL[1]},
            headers=hdr(admin_token), timeout=30,
        )
        assert rr.status_code == 200, f"restore failed {rr.status_code} {rr.text[:300]}"
        assert token(*COUNSEL)

        g = requests.get(f"{BASE}/admin/settings/counsel", headers=hdr(admin_token), timeout=30).json()
        assert g["email"] == COUNSEL[0]
        assert g["env_password_default_in_use"] is True
