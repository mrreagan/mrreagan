"""Iteration: counsel-facing features verification (legal docs, counsel guide, KB)."""
import os
import re
import time

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

COUNSEL = ("counsel@birthright.live", "counsel-review-2026")
ADMIN = ("admin@birthright.live", "birthright2026")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    return s, r


@pytest.fixture(scope="module")
def counsel_client():
    s, r = _login(*COUNSEL)
    if r.status_code != 200:
        pytest.fail(f"counsel login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    s, r = _login(*ADMIN)
    if r.status_code != 200:
        pytest.fail(f"admin login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


# ---------- auth / role ----------
class TestCounselAuth:
    def test_counsel_login_role(self):
        _, r = _login(*COUNSEL)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        token = data.get("token") or data.get("access_token")
        assert token, f"no token in {list(data.keys())}"
        import jwt as pyjwt
        payload = pyjwt.decode(token, options={"verify_signature": False})
        assert payload.get("role") == "readonly_admin", payload


# ---------- legal docs index ----------
class TestLegalDocs:
    def test_docs_index_contains_counsel_entries(self, counsel_client):
        r = counsel_client.get(f"{BASE_URL}/api/legal/docs", timeout=30)
        assert r.status_code == 200, r.text[:300]
        keys = {d["key"] for d in r.json()}
        assert "draft-00a-counsel-user-guide" in keys, keys
        assert "counsel-briefing-docx" in keys, keys

    def test_counsel_guide_draft_download(self):
        r = requests.get(f"{BASE_URL}/api/legal/drafts/00a-counsel-user-guide", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert len(r.content) > 10 * 1024, len(r.content)
        assert r.content[:2] == b"PK"

    def test_counsel_review_plan_draft_download(self):
        r = requests.get(f"{BASE_URL}/api/legal/drafts/00-counsel-review-plan", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert len(r.content) > 10 * 1024, len(r.content)

    def test_briefing_docx_and_md_fast_path(self, counsel_client):
        r = counsel_client.get(f"{BASE_URL}/api/legal/docs/counsel-briefing-docx", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:2] == b"PK"
        rm = counsel_client.get(f"{BASE_URL}/api/legal/docs/counsel-briefing-md", timeout=60)
        assert rm.status_code == 200, rm.text[:300]
        text = rm.content.decode("utf-8", "ignore")
        assert "Counsel Fast Path" in text, text[:500]
        assert "Minimise Your Billable Time" in text

    def test_counsel_guide_md_has_correct_password(self, counsel_client):
        """Guide should publish the corrected counsel password."""
        p = "/app/backend/legal_docs/00a-counsel-user-guide.md"
        md = open(p, encoding="utf-8").read()
        assert "counsel-review-2026" in md
        assert "counsel-review-2025" not in md

    def test_counsel_guide_advises_pushing_billable_work_to_admin(self):
        md = open("/app/backend/legal_docs/00a-counsel-user-guide.md", encoding="utf-8").read()
        low = md.lower()
        assert "billable" in low
        assert "site admin" in low or "admin" in low


# ---------- public legal pages ----------
class TestPublicLegal:
    def test_pages_six_slugs(self):
        r = requests.get(f"{BASE_URL}/api/legal/pages", timeout=30)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        slugs = {x["slug"] for x in rows}
        # These six MUST be present. `indemnification` and any future
        # additions are welcome — assert subset, not equality.
        required = {"terms", "privacy", "cookie-notice", "refunds",
                    "scholarships", "community-standards"}
        assert required.issubset(slugs), f"missing: {required - slugs}"

    def test_page_terms_body(self):
        r = requests.get(f"{BASE_URL}/api/legal/pages/terms", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("slug") == "terms"
        body = d.get("html") or d.get("body") or d.get("markdown") or ""
        assert len(body) > 500, list(d.keys())
        assert d.get("has_draft_disclaimer") in (True, False)

    def test_history_and_rss(self):
        r = requests.get(f"{BASE_URL}/api/legal/history", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert isinstance(r.json(), (list, dict))
        rr = requests.get(f"{BASE_URL}/api/legal/history.rss", timeout=30)
        assert rr.status_code == 200, rr.text[:300]
        assert "<rss" in rr.text or "<feed" in rr.text


# ---------- comments & readonly enforcement ----------
class TestCounselWrites:
    created = []

    def test_counsel_can_read_comments(self, counsel_client):
        r = counsel_client.get(f"{BASE_URL}/api/legal/comments/01-terms-of-service", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert isinstance(r.json(), list)

    def test_counsel_can_post_comment(self, counsel_client):
        payload = {
            "section": "12. Limitation of Liability",
            "kind": "redline",
            "quoted_text": "US $100",
            "suggested_replacement": "US $500",
            "body": "TEST_ Raise floor.",
        }
        r = counsel_client.post(
            f"{BASE_URL}/api/legal/comments/01-terms-of-service", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["kind"] == "redline"
        assert d["body"] == "TEST_ Raise floor."
        assert d["author_role"] == "readonly_admin"
        TestCounselWrites.created.append(d["id"])
        # verify persistence
        g = counsel_client.get(f"{BASE_URL}/api/legal/comments/01-terms-of-service", timeout=30)
        assert any(c["id"] == d["id"] for c in g.json())

    def test_counsel_ratification_blocked(self, counsel_client):
        r = counsel_client.post(
            f"{BASE_URL}/api/legal/ratifications/01-terms-of-service",
            json={"version": "9.9", "notes": "TEST_", "ratified_by": "TEST_"}, timeout=30)
        assert r.status_code == 403, f"{r.status_code}: {r.text[:300]}"
        assert r.json().get("readonly") is True, r.text[:300]

    def test_counsel_rebuild_blocked(self, counsel_client):
        r = counsel_client.post(f"{BASE_URL}/api/legal/rebuild-docx", timeout=60)
        assert r.status_code == 403, f"{r.status_code}: {r.text[:300]}"

    def test_admin_ratification_succeeds_and_revoke(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/legal/ratifications/01-terms-of-service",
            json={"version": "9.9", "notes": "TEST_ ratification", "ratified_by": "TEST_ Firm"},
            timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["version"] == "9.9"
        assert d["source_slug"] == "01-terms-of-service"
        # verify listed
        lst = admin_client.get(f"{BASE_URL}/api/legal/ratifications", timeout=30)
        assert lst.status_code == 200
        assert any(x["id"] == d["id"] for x in lst.json())
        # cleanup
        dele = admin_client.delete(
            f"{BASE_URL}/api/legal/ratifications/01-terms-of-service", timeout=30)
        assert dele.status_code == 200, dele.text[:300]
        lst2 = admin_client.get(f"{BASE_URL}/api/legal/ratifications", timeout=30)
        assert not any(x["id"] == d["id"] for x in lst2.json())

    def test_admin_rebuild_docx(self, admin_client):
        r = admin_client.post(f"{BASE_URL}/api/legal/rebuild-docx", timeout=240)
        assert r.status_code == 200, r.text[:500]
        assert r.json().get("ok") is True, r.text[:300]


def test_zz_cleanup_comments():
    """Remove test comments created above via mongo (no delete endpoint)."""
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    env = dotenv_values("/app/backend/.env")
    mongo = env.get("MONGO_URL")
    dbn = env.get("DB_NAME")
    if not (mongo and dbn and TestCounselWrites.created):
        return

    async def _go():
        c = AsyncIOMotorClient(mongo)
        res = await c[dbn].legal_doc_comments.delete_many(
            {"id": {"$in": TestCounselWrites.created}})
        c.close()
        return res.deleted_count
    assert asyncio.get_event_loop().run_until_complete(_go()) >= 0


# ---------- help KB ----------
class TestHelpKB:
    def test_counsel_fast_path_kb(self):
        r = requests.post(f"{BASE_URL}/api/help/chat", json={
            "message": "how do i start reviewing as counsel",
            "session_id": "counsel-kb-1",
        }, timeout=90)
        assert r.status_code == 200, r.text[:300]
        reply = r.json().get("reply") or r.json().get("message") or ""
        assert "LEGAL_BRIEFING_FOR_COUNSEL.docx" in reply, reply[:600]

    def test_counsel_redline_kb(self):
        r = requests.post(f"{BASE_URL}/api/help/chat", json={
            "message": "how do i add a redline",
            "session_id": "counsel-kb-2",
        }, timeout=90)
        assert r.status_code == 200, r.text[:300]
        reply = r.json().get("reply") or r.json().get("message") or ""
        assert "legal@birthright.live" in reply, reply[:600]


# ---------- allow-list scope check (security) ----------
class TestCounselAllowListScope:
    """The readonly allow-list uses the prefix /api/legal/comments/ which also
    covers /apply-roundtrip and /resolve — verify whether counsel can reach
    those mutating endpoints."""

    def test_counsel_apply_roundtrip_reachability(self, counsel_client):
        r = counsel_client.post(
            f"{BASE_URL}/api/legal/comments/01-terms-of-service/apply-roundtrip",
            json={"decisions": "not-a-list"}, timeout=30)
        print("apply-roundtrip as counsel ->", r.status_code, r.text[:200])
        assert r.status_code == 403, (
            f"counsel reached apply-roundtrip (source .md mutator): {r.status_code} {r.text[:200]}")

    def test_counsel_resolve_comment_reachability(self, counsel_client):
        r = counsel_client.post(
            f"{BASE_URL}/api/legal/comments/01-terms-of-service/does-not-exist/resolve",
            timeout=30)
        print("resolve as counsel ->", r.status_code, r.text[:200])
        assert r.status_code == 403, (
            f"counsel reached comment resolve endpoint: {r.status_code} {r.text[:200]}")


def test_zzz_cleanup_playwright_comments():
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    env = dotenv_values("/app/backend/.env")
    mongo, dbn = env.get("MONGO_URL"), env.get("DB_NAME")

    async def _go():
        c = AsyncIOMotorClient(mongo)
        res = await c[dbn].legal_doc_comments.delete_many(
            {"body": {"$regex": "^TEST_"}})
        c.close()
        return res.deleted_count
    n = asyncio.new_event_loop().run_until_complete(_go())
    print("cleaned test comments:", n)
