"""Iteration 38 — millisecond-precision session revocation (auth_utils.create_token iat_ms).

Covers:
  - iat_ms claim present in freshly issued JWTs
  - SAME-SECOND revocation now precise: login -> immediate rotate -> old token 401
  - Fresh login immediately after rotate still works (no false revocation)
"""
import os
import time

import jwt
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


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


def login(email, password):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)


def token_for(email, password):
    r = login(email, password)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:300]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in login response: {r.json()}"
    return tok


def rotate_counsel(admin_tok, password):
    return requests.post(f"{API}/admin/settings/counsel/rotate",
                         json={"password": password}, headers=h(admin_tok), timeout=30)


@pytest.fixture(scope="module", autouse=True)
def cleanup(mdb):
    yield
    admin_tok = token_for(**ADMIN)
    assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200
    mdb.counsel_password_tokens.delete_many({})
    mdb.user_token_revocations.delete_many({})


class TestIatMsClaim:
    def test_fresh_token_has_iat_ms(self):
        tok = token_for(COUNSEL_EMAIL, COUNSEL_PW)
        payload = jwt.decode(tok, options={"verify_signature": False})
        assert "iat_ms" in payload, f"iat_ms missing: {payload}"
        assert isinstance(payload["iat_ms"], int), type(payload["iat_ms"])
        now_ms = int(time.time() * 1000)
        assert abs(now_ms - payload["iat_ms"]) < 60_000, (payload["iat_ms"], now_ms)
        # ms value must be consistent with the whole-second iat
        assert payload["iat_ms"] // 1000 == int(payload["iat"])
        # not a whole-second-only value masquerading as ms (informational)
        assert payload["iat_ms"] > 1_700_000_000_000


class TestSameSecondRevocation:
    """Login then IMMEDIATELY rotate (same wall-clock second) -> old token must die."""

    def test_same_second_revocation_5x(self):
        admin_tok = token_for(**ADMIN)
        failures = []
        try:
            for i in range(5):
                tok_a = token_for(COUNSEL_EMAIL, COUNSEL_PW if i == 0 else COUNSEL_PW)
                t_login = time.time()
                rr = rotate_counsel(admin_tok, f"same-sec-pw-{i}-2026")
                assert rr.status_code == 200, f"iter {i} rotate failed: {rr.status_code} {rr.text[:300]}"
                gap = time.time() - t_login
                ar = requests.get(AUTH_ENDPOINT, headers=h(tok_a), timeout=30)
                if ar.status_code != 200:
                    pass
                if ar.status_code != 401 or "Session revoked" not in ar.text:
                    payload = jwt.decode(tok_a, options={"verify_signature": False})
                    failures.append(
                        f"iter {i}: expected 401 Session revoked, got {ar.status_code} {ar.text[:150]} "
                        f"(login->rotate gap {gap:.3f}s, iat_ms={payload.get('iat_ms')})"
                    )
                # restore password so the next iteration can log in
                assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200
            assert not failures, "; ".join(failures)
        finally:
            assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200


class TestFreshLoginAfterRotate:
    def test_fresh_login_after_rotate_5x(self):
        admin_tok = token_for(**ADMIN)
        failures = []
        try:
            for i in range(5):
                pw = f"fresh-login-pw-{i}-2026"
                rr = rotate_counsel(admin_tok, pw)
                assert rr.status_code == 200, f"iter {i} rotate failed: {rr.status_code} {rr.text[:300]}"
                lr = login(COUNSEL_EMAIL, pw)
                assert lr.status_code == 200, f"iter {i} login failed: {lr.status_code} {lr.text[:300]}"
                tok_b = lr.json().get("token") or lr.json().get("access_token")
                ar = requests.get(AUTH_ENDPOINT, headers=h(tok_b), timeout=30)
                if ar.status_code != 200:
                    failures.append(f"iter {i}: fresh token rejected {ar.status_code} {ar.text[:150]}")
            assert not failures, "; ".join(failures)
        finally:
            assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200


class TestOlderTokenRegression:
    def test_older_token_revoked(self):
        tok = token_for(COUNSEL_EMAIL, COUNSEL_PW)
        assert requests.get(AUTH_ENDPOINT, headers=h(tok), timeout=30).status_code == 200
        time.sleep(2)
        admin_tok = token_for(**ADMIN)
        try:
            assert rotate_counsel(admin_tok, "older-tok-iter38-2026").status_code == 200
            r = requests.get(AUTH_ENDPOINT, headers=h(tok), timeout=30)
            assert r.status_code == 401, f"expected 401 got {r.status_code}: {r.text[:300]}"
            assert "Session revoked" in r.text, r.text[:300]
        finally:
            assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200
