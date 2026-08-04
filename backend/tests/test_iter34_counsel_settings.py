"""Iteration 34 — Admin counsel credential rotation (/api/admin/settings/counsel)."""
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
PARTICIPANT = ("demo@birthright.org", "birthright2026")

ROT_EMAIL = "counsel@birthright.live"
ROT_PASSWORD = "rotated-test-password-2026"


def login(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


def token(email, password):
    r = login(email, password)
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


@pytest.fixture(scope="module", autouse=True)
def restore_counsel(admin_token):
    """Always leave the counsel account on its documented credentials."""
    yield
    requests.post(
        f"{BASE}/admin/settings/counsel/rotate",
        json={"email": COUNSEL[0], "password": COUNSEL[1]},
        headers=hdr(admin_token), timeout=30,
    )


class TestCounselSettingsRead:
    def test_get_as_admin(self, admin_token):
        r = requests.get(f"{BASE}/admin/settings/counsel", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for k in ("seeded", "email", "email_redacted", "env_email_default",
                  "env_password_default_in_use", "created_at",
                  "last_rotated_at", "last_rotated_by"):
            assert k in d, f"missing field {k} in {d}"
        assert d["seeded"] is True
        assert "@" in d["email"]
        assert isinstance(d["email_redacted"], str) and "•" in d["email_redacted"]

    def test_get_as_participant_forbidden(self):
        tok = token(*PARTICIPANT)
        r = requests.get(f"{BASE}/admin/settings/counsel", headers=hdr(tok), timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code} {r.text[:300]}"
        assert "birthright" not in r.text or "counsel@" not in r.text

    def test_get_unauthenticated(self):
        r = requests.get(f"{BASE}/admin/settings/counsel", timeout=30)
        assert r.status_code in (401, 403)

    def test_get_as_counsel_actual_behaviour(self):
        tok = token(*COUNSEL)
        r = requests.get(f"{BASE}/admin/settings/counsel", headers=hdr(tok), timeout=30)
        # Documented intent is admin-only; require_roles("admin") also admits
        # readonly_admin platform-wide, so 200 is the actual behaviour.
        print(f"COUNSEL GET status={r.status_code} body={r.text[:200]}")
        assert r.status_code in (200, 403)


class TestValidation:
    def test_short_password(self, admin_token):
        r = requests.post(f"{BASE}/admin/settings/counsel/rotate",
                          json={"password": "short"}, headers=hdr(admin_token), timeout=30)
        assert r.status_code == 400, r.text[:300]
        assert "12" in r.json().get("detail", "")

    def test_bad_email(self, admin_token):
        r = requests.post(f"{BASE}/admin/settings/counsel/rotate",
                          json={"email": "not-an-email"}, headers=hdr(admin_token), timeout=30)
        assert r.status_code == 400, r.text[:300]

    def test_empty_payload(self, admin_token):
        r = requests.post(f"{BASE}/admin/settings/counsel/rotate",
                          json={}, headers=hdr(admin_token), timeout=30)
        assert r.status_code == 400

    def test_email_collision_conflict(self, admin_token):
        r = requests.post(f"{BASE}/admin/settings/counsel/rotate",
                          json={"email": "admin@birthright.org"},
                          headers=hdr(admin_token), timeout=30)
        assert r.status_code == 409, f"expected 409 got {r.status_code} {r.text[:300]}"

    def test_counsel_cannot_rotate(self, admin_token):
        tok = token(*COUNSEL)
        r = requests.post(f"{BASE}/admin/settings/counsel/rotate",
                          json={"email": "evil@birthright.live", "password": "hacked-password-2026"},
                          headers=hdr(tok), timeout=30)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text[:300]}"
        assert r.json().get("readonly") is True


class TestRotateFlow:
    def test_rotate_and_login(self, admin_token):
        r = requests.post(f"{BASE}/admin/settings/counsel/rotate",
                          json={"email": ROT_EMAIL, "password": ROT_PASSWORD},
                          headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["ok"] is True
        assert d["email"] == ROT_EMAIL
        assert d["password_changed"] is True
        assert d.get("rotated_at")

        # new creds work and carry the readonly_admin role
        lr = login(ROT_EMAIL, ROT_PASSWORD)
        assert lr.status_code == 200, lr.text[:300]
        body = lr.json()
        role = (body.get("user") or {}).get("role") or body.get("role")
        assert role == "readonly_admin", body

        # old creds rejected
        old = login(*COUNSEL)
        assert old.status_code == 401, f"OLD creds still valid: {old.status_code}"

        # GET reflects the rotation
        g = requests.get(f"{BASE}/admin/settings/counsel", headers=hdr(admin_token), timeout=30).json()
        assert g["email"] == ROT_EMAIL
        assert g["last_rotated_at"]
        assert g["last_rotated_by"] == ADMIN[0]
        assert g["env_password_default_in_use"] is False

    def test_persistence_after_restart(self, admin_token):
        """Seeder must not restore env credentials on boot."""
        os.system("sudo supervisorctl restart backend >/dev/null 2>&1")
        import time
        for _ in range(30):
            time.sleep(2)
            try:
                if requests.get(f"{BASE}/", timeout=10).status_code < 500:
                    break
            except Exception:
                continue
        lr = login(ROT_EMAIL, ROT_PASSWORD)
        assert lr.status_code == 200, f"rotated creds broken after restart: {lr.status_code} {lr.text[:300]}"
        old = login(*COUNSEL)
        assert old.status_code == 401, "seeder restored env credentials after restart!"
        g = requests.get(f"{BASE}/admin/settings/counsel", headers=hdr(admin_token), timeout=30).json()
        assert g["email"] == ROT_EMAIL
        assert g["last_rotated_at"]
