"""Iteration 36b — regression tests for the counsel session-revocation race.

Covers backend/auth_utils.py::_is_token_revoked boundary behaviour:
  - a login in the SAME whole second as a rotate must NOT be revoked
  - a token minted in an EARLIER second than the rotate MUST be revoked
  - same-second fabricated revocation record must accept a same-second iat
"""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
backend_env = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@birthright.org", "password": "birthright2026"}
COUNSEL_EMAIL = "counsel@birthright.org"
COUNSEL_PW = "counsel-review-2026"
AUTH_ENDPOINT = f"{API}/legal/comments/01-terms-of-service"

MONGO_URL = backend_env.get("MONGO_URL") or os.environ.get("MONGO_URL")
DB_NAME = backend_env.get("DB_NAME") or os.environ.get("DB_NAME")
JWT_SECRET = backend_env.get("JWT_SECRET") or os.environ.get("JWT_SECRET", "change-me")


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
    r = rotate_counsel(admin_tok, COUNSEL_PW)
    assert r.status_code == 200, f"teardown rotate failed: {r.status_code} {r.text[:200]}"
    mdb.counsel_password_tokens.delete_many({})
    mdb.user_token_revocations.delete_many({})


class TestRotateLoginRace:
    """Back-to-back rotate -> immediate login -> auth call, 5 iterations."""

    def test_no_false_revocation_5x(self):
        admin_tok = token_for(**ADMIN)
        failures = []
        try:
            for i in range(5):
                pw = f"race-test-pw-{i}-2026"
                t0 = time.time()
                rr = rotate_counsel(admin_tok, pw)
                assert rr.status_code == 200, f"iter {i} rotate failed: {rr.status_code} {rr.text[:300]}"
                lr = login(COUNSEL_EMAIL, pw)
                assert lr.status_code == 200, f"iter {i} login failed: {lr.status_code} {lr.text[:300]}"
                tok = lr.json().get("token") or lr.json().get("access_token")
                assert tok, f"iter {i} no token: {lr.json()}"
                ar = requests.get(AUTH_ENDPOINT, headers=h(tok), timeout=30)
                gap = time.time() - t0
                if ar.status_code != 200:
                    failures.append(
                        f"iter {i}: auth call after fresh login returned {ar.status_code} "
                        f"{ar.text[:200]} (rotate->auth gap {gap:.3f}s)"
                    )
            assert not failures, "; ".join(failures)
        finally:
            assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200


class TestOlderTokenStillRevoked:
    def test_old_token_revoked(self):
        tok_a = token_for(COUNSEL_EMAIL, COUNSEL_PW)
        assert requests.get(AUTH_ENDPOINT, headers=h(tok_a), timeout=30).status_code == 200
        time.sleep(2)
        admin_tok = token_for(**ADMIN)
        try:
            assert rotate_counsel(admin_tok, "older-token-revoke-2026").status_code == 200
            r = requests.get(AUTH_ENDPOINT, headers=h(tok_a), timeout=30)
            assert r.status_code == 401, f"expected 401 got {r.status_code}: {r.text[:300]}"
            assert "Session revoked" in r.text, r.text[:300]
        finally:
            assert rotate_counsel(admin_tok, COUNSEL_PW).status_code == 200


class TestSameSecondBoundary:
    def test_same_second_iat_accepted(self, mdb):
        user = mdb.users.find_one({"email": COUNSEL_EMAIL})
        assert user, "counsel user not seeded"
        whole = datetime.now(timezone.utc).replace(microsecond=0)
        mdb.user_token_revocations.delete_many({"user_id": user["id"]})
        mdb.user_token_revocations.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "revoked_at": whole.isoformat(),
            "reason": "TEST_boundary",
        })
        try:
            same_second_tok = jwt.encode(
                {"sub": user["id"], "role": user.get("role", "readonly_admin"),
                 "iat": whole, "exp": datetime.now(timezone.utc) + timedelta(days=1)},
                JWT_SECRET, algorithm="HS256")
            r = requests.get(AUTH_ENDPOINT, headers=h(same_second_tok), timeout=30)
            assert r.status_code == 200, f"same-second token rejected: {r.status_code} {r.text[:300]}"

            earlier_tok = jwt.encode(
                {"sub": user["id"], "role": user.get("role", "readonly_admin"),
                 "iat": whole - timedelta(seconds=5),
                 "exp": datetime.now(timezone.utc) + timedelta(days=1)},
                JWT_SECRET, algorithm="HS256")
            r2 = requests.get(AUTH_ENDPOINT, headers=h(earlier_tok), timeout=30)
            assert r2.status_code == 401, f"earlier-second token accepted: {r2.status_code} {r2.text[:300]}"
            assert "Session revoked" in r2.text, r2.text[:300]
        finally:
            mdb.user_token_revocations.delete_many({"user_id": user["id"]})
