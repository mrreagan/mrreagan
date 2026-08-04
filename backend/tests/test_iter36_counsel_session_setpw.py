"""Iteration 36 — counsel session revocation + send-set-password-link flow.

Covers:
  - backend/auth_utils.py get_current_user session revocation via user_token_revocations
  - backend/routers/admin_settings.py  /counsel/send-set-password-link
  - backend/routers/admin_settings.py  /counsel/set-password-from-token
  - legal_docs/CLOUDFLARE_RESEND_SETUP.md presence
"""
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@birthright.live", "password": "birthright2026"}
COUNSEL_EMAIL = "counsel@birthright.live"
COUNSEL_PW = "counsel-review-2026"
AUTH_ENDPOINT = f"{API}/legal/comments/01-terms-of-service"

MONGO_URL = backend_env.get("MONGO_URL") or os.environ.get("MONGO_URL")
DB_NAME = backend_env.get("DB_NAME") or os.environ.get("DB_NAME")


@pytest.fixture(scope="module")
def mdb():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


def login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


def token_for(email, password):
    r = login(email, password)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:300]}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok, f"no token in login response: {data}"
    return tok


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


def rotate_counsel(admin_tok, password):
    return requests.post(f"{API}/admin/settings/counsel/rotate",
                         json={"password": password}, headers=h(admin_tok), timeout=30)


@pytest.fixture(scope="module", autouse=True)
def cleanup(mdb):
    yield
    admin_tok = token_for(**ADMIN)
    rotate_counsel(admin_tok, COUNSEL_PW)
    mdb.counsel_password_tokens.delete_many({})
    mdb.user_token_revocations.delete_many({})


def seed_token(mdb, hours=1, used=False):
    raw = secrets.token_urlsafe(32)
    user = mdb.users.find_one({"email": COUNSEL_EMAIL})
    assert user, "counsel user not seeded"
    mdb.counsel_password_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(),
        "used_at": datetime.now(timezone.utc).isoformat() if used else None,
        "created_by_email": "test",
    })
    return raw


# ---------- doc existence ----------
class TestDoc:
    def test_cloudflare_resend_doc(self):
        p = Path("/app/backend/legal_docs/CLOUDFLARE_RESEND_SETUP.md")
        assert p.exists()
        body = p.read_text()
        assert len(body.encode()) > 2048, f"doc too small: {len(body.encode())} bytes"
        assert "Cloudflare Email Routing" in body
        assert "Resend" in body


# ---------- session revocation ----------
class TestSessionRevocation:
    def test_revocation_kills_old_token(self, mdb):
        tok_a = token_for(COUNSEL_EMAIL, COUNSEL_PW)
        r = requests.get(AUTH_ENDPOINT, headers=h(tok_a), timeout=30)
        assert r.status_code == 200, f"pre-rotate auth call failed: {r.status_code} {r.text[:200]}"

        admin_tok = token_for(**ADMIN)
        rr = rotate_counsel(admin_tok, "session-revoke-test-2026")
        assert rr.status_code == 200, f"rotate failed: {rr.status_code} {rr.text[:300]}"

        r2 = requests.get(AUTH_ENDPOINT, headers=h(tok_a), timeout=30)
        assert r2.status_code == 401, f"expected 401 got {r2.status_code}: {r2.text[:300]}"
        assert "Session revoked" in r2.text, r2.text[:300]

        # regression: fresh login with new password works
        tok_b = token_for(COUNSEL_EMAIL, "session-revoke-test-2026")
        r3 = requests.get(AUTH_ENDPOINT, headers=h(tok_b), timeout=30)
        assert r3.status_code == 200, f"new token rejected: {r3.status_code} {r3.text[:300]}"

        # admin session unaffected
        ra = requests.get(f"{API}/admin/settings/counsel", headers=h(admin_tok), timeout=30)
        assert ra.status_code == 200, f"admin token broken: {ra.status_code} {ra.text[:200]}"

        # restore
        assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200


# ---------- send link ----------
class TestSendLink:
    def test_send_link_happy(self, mdb):
        admin_tok = token_for(**ADMIN)
        r = requests.post(f"{API}/admin/settings/counsel/send-set-password-link",
                          headers=h(admin_tok), timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        assert data["ok"] is True
        assert data["email_sent_to"] == COUNSEL_EMAIL
        assert "expires_at" in data
        user = mdb.users.find_one({"email": COUNSEL_EMAIL})
        doc = mdb.counsel_password_tokens.find_one({"user_id": user["id"]})
        assert doc, "no token document persisted"
        assert doc["used_at"] is None
        exp = datetime.fromisoformat(doc["expires_at"].replace("Z", "+00:00"))
        assert exp > datetime.now(timezone.utc)
        assert data.get("email_id"), "email_id missing/None — mailer failed"

    def test_send_link_counsel_forbidden(self):
        tok = token_for(COUNSEL_EMAIL, COUNSEL_PW)
        r = requests.post(f"{API}/admin/settings/counsel/send-set-password-link",
                          headers=h(tok), timeout=30)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:300]}"


# ---------- set-password-from-token ----------
class TestSetPasswordFromToken:
    URL = f"{API}/admin/settings/counsel/set-password-from-token"

    def test_happy_path_and_session_kill(self, mdb):
        tok_x = token_for(COUNSEL_EMAIL, COUNSEL_PW)
        assert requests.get(AUTH_ENDPOINT, headers=h(tok_x), timeout=30).status_code == 200

        raw = seed_token(mdb)
        newpw = "self-service-pw-2026"
        r = requests.post(self.URL, json={"token": raw, "password": newpw}, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        assert r.json() == {"ok": True, "email": COUNSEL_EMAIL}

        # login with new password
        lr = login(COUNSEL_EMAIL, newpw)
        assert lr.status_code == 200, f"login with new pw failed: {lr.status_code} {lr.text[:300]}"
        assert lr.json()["user"]["role"] == "readonly_admin"

        # old session revoked
        r2 = requests.get(AUTH_ENDPOINT, headers=h(tok_x), timeout=30)
        assert r2.status_code == 401 and "Session revoked" in r2.text, f"{r2.status_code} {r2.text[:300]}"

        # token now used → reuse rejected
        r3 = requests.post(self.URL, json={"token": raw, "password": "another-pw-999999"}, timeout=30)
        assert r3.status_code == 400 and "already been used" in r3.text, f"{r3.status_code} {r3.text[:300]}"

        # restore
        admin_tok = token_for(**ADMIN)
        assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200

    def test_missing_token(self):
        r = requests.post(self.URL, json={"password": "abcdefghijklmno"}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_unknown_token(self):
        r = requests.post(self.URL, json={"token": "no-such-token", "password": "abcdefghijklmno"}, timeout=30)
        assert r.status_code == 400 and "Invalid" in r.text, r.text[:200]

    def test_expired_token(self, mdb):
        raw = seed_token(mdb, hours=-2)
        r = requests.post(self.URL, json={"token": raw, "password": "abcdefghijklmno"}, timeout=30)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"
        assert "expired" in r.text.lower(), r.text[:200]

    def test_short_password(self, mdb):
        raw = seed_token(mdb)
        r = requests.post(self.URL, json={"token": raw, "password": "short"}, timeout=30)
        assert r.status_code == 400 and "12" in r.text, r.text[:200]
