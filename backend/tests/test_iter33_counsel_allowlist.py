"""Iteration 33 — re-verify counsel fixes: briefing fast-path in md+docx, tightened allow-list."""
import io
import os
import zipfile

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

COUNSEL = ("counsel@birthright.live", "counsel-review-2026")
FAST_PATH = "Counsel Fast Path"
FAST_PATH_FULL = "Counsel Fast Path — Minimise Your Billable Time"
SLUG = "01-terms-of-service"


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


# ---------- briefing fast-path section (md + docx) ----------
class TestBriefingFastPath:
    def test_md_contains_fast_path_near_top(self, counsel_client):
        r = counsel_client.get(f"{BASE_URL}/api/legal/docs/counsel-briefing-md", timeout=60)
        assert r.status_code == 200, r.text[:300]
        text = r.content.decode("utf-8", "ignore")
        assert FAST_PATH_FULL in text, text[:800]
        idx = text.index(FAST_PATH_FULL)
        # "near the top": before section 1 Entity Overview
        assert "## 1. Entity Overview" in text
        assert idx < text.index("## 1. Entity Overview"), (idx, text.index("## 1. Entity Overview"))

    def test_docx_contains_fast_path(self, counsel_client):
        r = counsel_client.get(f"{BASE_URL}/api/legal/docs/counsel-briefing-docx", timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:2] == b"PK"
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        assert FAST_PATH in xml, xml[:500]
        assert "Minimise Your Billable Time" in xml


# ---------- tightened allow-list ----------
class TestCounselAllowList:
    created = []

    def test_comment_create_still_allowed(self, counsel_client):
        payload = {
            "section": "12. Limitation of Liability",
            "kind": "redline",
            "quoted_text": "US $100",
            "suggested_replacement": "US $500",
            "body": "TEST_ iter33 allow-list regression.",
        }
        r = counsel_client.post(f"{BASE_URL}/api/legal/comments/{SLUG}", json=payload, timeout=30)
        assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
        d = r.json()
        assert d["kind"] == "redline"
        assert d["author_role"] == "readonly_admin"
        TestCounselAllowList.created.append(d["id"])
        g = counsel_client.get(f"{BASE_URL}/api/legal/comments/{SLUG}", timeout=30)
        assert any(c["id"] == d["id"] for c in g.json())

    def test_apply_roundtrip_blocked(self, counsel_client):
        r = counsel_client.post(
            f"{BASE_URL}/api/legal/comments/{SLUG}/apply-roundtrip",
            json={"decisions": []}, timeout=30)
        assert r.status_code == 403, f"{r.status_code}: {r.text[:400]}"
        assert r.json().get("readonly") is True, r.text[:300]

    def test_import_roundtrip_blocked(self, counsel_client):
        files = {"file": ("x.docx", b"PK\x03\x04dummy",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        r = counsel_client.post(
            f"{BASE_URL}/api/legal/comments/{SLUG}/import-roundtrip", files=files, timeout=60)
        assert r.status_code == 403, f"{r.status_code}: {r.text[:400]}"
        assert r.json().get("readonly") is True, r.text[:300]

    def test_resolve_blocked(self, counsel_client):
        cid = TestCounselAllowList.created[0] if TestCounselAllowList.created else "does-not-exist"
        r = counsel_client.post(f"{BASE_URL}/api/legal/comments/{SLUG}/{cid}/resolve", timeout=30)
        assert r.status_code == 403, f"{r.status_code}: {r.text[:400]}"
        assert r.json().get("readonly") is True, r.text[:300]

    def test_export_post_blocked_but_get_allowed(self, counsel_client):
        """Export is a GET (safe) route; a POST attempt must still be refused."""
        r = counsel_client.post(f"{BASE_URL}/api/legal/comments/{SLUG}/export", timeout=60)
        assert r.status_code == 403, f"{r.status_code}: {r.text[:300]}"
        assert r.json().get("readonly") is True, r.text[:300]
        g = counsel_client.get(f"{BASE_URL}/api/legal/comments/{SLUG}/export", timeout=60)
        assert g.status_code == 200, g.text[:300]
        assert g.content[:2] == b"PK"

    def test_ratification_post_and_delete_blocked(self, counsel_client):
        p = counsel_client.post(
            f"{BASE_URL}/api/legal/ratifications/{SLUG}",
            json={"version": "9.9", "notes": "TEST_", "ratified_by": "TEST_"}, timeout=30)
        assert p.status_code == 403, f"{p.status_code}: {p.text[:300]}"
        assert p.json().get("readonly") is True
        d = counsel_client.delete(f"{BASE_URL}/api/legal/ratifications/{SLUG}", timeout=30)
        assert d.status_code == 403, f"{d.status_code}: {d.text[:300]}"
        assert d.json().get("readonly") is True

    def test_rebuild_docx_blocked(self, counsel_client):
        r = counsel_client.post(f"{BASE_URL}/api/legal/rebuild-docx", timeout=60)
        assert r.status_code == 403, f"{r.status_code}: {r.text[:300]}"
        assert r.json().get("readonly") is True


# ---------- RSS ----------
def test_history_rss_valid_xml():
    import xml.etree.ElementTree as ET
    r = requests.get(f"{BASE_URL}/api/legal/history.rss", timeout=30)
    assert r.status_code == 200, r.text[:300]
    root = ET.fromstring(r.content)
    assert root.tag == "rss", root.tag
    channel = root.find("channel")
    assert channel is not None
    title = channel.findtext("title")
    assert title == "Birthright Foundation — Policy Ratifications", title
    self_link = channel.find("{http://www.w3.org/2005/Atom}link")
    assert self_link is not None, ET.tostring(channel)[:400]
    assert self_link.get("rel") == "self", self_link.attrib


# ---------- cleanup ----------
def test_zzz_cleanup():
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
