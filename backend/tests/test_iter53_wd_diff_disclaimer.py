"""Iteration 53 — P0 verification: diff viewer must not show the auto-injected
"FIRST DRAFT — PENDING COUNSEL RATIFICATION" disclaimer as a false-positive hunk.

Modules under test:
  - backend/routers/legal.py
      GET  /api/legal/working-drafts/{source_slug}   (the fixed endpoint, L1071-1099)
      POST /api/legal/docs/{source_slug}/upload      (creates a working draft)
      POST /api/legal/working-drafts/{slug}/comments (regression)
      GET  /api/legal/docs-bundle.zip                (regression)
      helper _strip_draft_disclaimer (unit level)
"""
import hashlib
import io
import os
import re
import sys
import zipfile

import pytest
import requests
from dotenv import dotenv_values

if "/app/backend" not in sys.path:
    sys.path.insert(0, "/app/backend")

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")

ADMIN = ("admin@birthright.live", "birthright2026")
COUNSEL = ("counsel@birthright.live", "counsel-review-2026")

SLUG = "03-cookie-notice"
DISCLAIMER_TEXT = "FIRST DRAFT — PENDING COUNSEL RATIFICATION"

WORKING_MD = (
    "# Cookie & Tracking Notice (TEST_iter53)\n\n"
    "TEST_iter53 body — one word edited.\n\n"
    "## Section A\n\n- bullet one\n- bullet two\n"
)


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if not tok:
        pytest.fail(f"no token in login response: {r.text[:300]}")
    return tok


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def counsel_token():
    return _login(*COUNSEL)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def working_draft(admin_token):
    """Ensure an open working draft exists for SLUG (uploading a .md creates one).
    The uploaded body deliberately has NO disclaimer, while the released .md DOES.
    """
    files = {"file": (f"{SLUG}.md", WORKING_MD.encode("utf-8"), "text/markdown")}
    r = requests.post(f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
                      headers=_h(admin_token), files=files, timeout=90)
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:400]}"
    data = r.json()
    assert data.get("working_draft_id") or data.get("id"), f"no wd id: {data}"
    yield data
    # teardown: discard the working draft so we leave the env clean
    requests.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
                  headers=_h(admin_token), json={"note": "TEST_iter53 cleanup"}, timeout=60)


# ----------------------------------------------------- unit: strip helper
class TestStripHelper:
    def test_strips_leading_blockquote(self):
        from routers.legal import _strip_draft_disclaimer
        raw = ("> **FIRST DRAFT — PENDING COUNSEL RATIFICATION**\n>\n> blah\n\n"
               "# Real Title\n\nbody\n")
        out, had = _strip_draft_disclaimer(raw)
        assert had is True
        assert DISCLAIMER_TEXT not in out
        assert out.startswith("# Real Title")

    def test_noop_when_absent(self):
        from routers.legal import _strip_draft_disclaimer
        raw = "# Real Title\n\nbody\n"
        out, had = _strip_draft_disclaimer(raw)
        assert had is False
        assert out == raw

    def test_released_source_actually_has_disclaimer(self):
        """Guard: the fix is only meaningful if the released .md carries it."""
        from routers.legal import LEGAL_DOC_DIR
        md = (LEGAL_DOC_DIR / f"{SLUG}.md").read_text(encoding="utf-8")
        assert DISCLAIMER_TEXT in md, "released source doc no longer has the disclaimer"


# ------------------------------------------- P0: GET working-drafts/{slug}
class TestWorkingDraftDiffPayload:
    def test_both_sides_stripped(self, admin_token, working_draft):
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}",
                         headers=_h(admin_token), timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        d = r.json()
        assert "content_md" in d and "released_md" in d
        for field in ("content_md", "released_md"):
            val = d[field] or ""
            assert DISCLAIMER_TEXT not in val, f"{field} still contains the disclaimer"
            assert "AI-GENERATED FIRST DRAFT" not in val, f"{field} has AI-GENERATED banner"
            assert not val.lstrip().startswith(">"), f"{field} still starts with a blockquote"
        assert "_id" not in d

    def test_released_hash_matches_stripped_body(self, admin_token, working_draft):
        from routers.legal import LEGAL_DOC_DIR, _md_body_hash, _strip_draft_disclaimer
        raw = (LEGAL_DOC_DIR / f"{SLUG}.md").read_text(encoding="utf-8")
        stripped, had = _strip_draft_disclaimer(raw)
        assert had is True
        expected = _md_body_hash(stripped)
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}",
                         headers=_h(admin_token), timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["released_body_hash"] == expected
        # and the hash must NOT be the hash of the raw (disclaimer-bearing) body
        assert d["released_body_hash"] != _md_body_hash(raw)
        assert d["released_md"] == stripped

    def test_is_stale_false_right_after_creation(self, admin_token, working_draft):
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}",
                         headers=_h(admin_token), timeout=60)
        d = r.json()
        assert d["is_stale"] is False, (
            f"base_released_hash={d.get('base_released_hash')} "
            f"released_body_hash={d.get('released_body_hash')}"
        )

    def test_diff_is_small_not_whole_document(self, admin_token, working_draft):
        """The whole point of the P0: the diff should be a handful of lines, not
        the entire disclaimer preamble."""
        import difflib
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}",
                         headers=_h(admin_token), timeout=60)
        d = r.json()
        rel = (d["released_md"] or "").splitlines()
        wrk = (d["content_md"] or "").splitlines()
        diff = list(difflib.unified_diff(rel, wrk, lineterm=""))
        added = [ln for ln in diff if ln.startswith("+") and not ln.startswith("+++")]
        removed = [ln for ln in diff if ln.startswith("-") and not ln.startswith("---")]
        joined = "\n".join(added + removed)
        assert DISCLAIMER_TEXT not in joined, "disclaimer appears in the diff hunks"
        assert not any("PENDING COUNSEL" in ln for ln in added + removed)

    def test_404_for_slug_without_open_draft(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts/zz-no-such-slug-iter53",
                         headers=_h(admin_token), timeout=60)
        assert r.status_code == 404

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}", timeout=60)
        assert r.status_code in (401, 403)

    def test_counsel_access(self, counsel_token, working_draft):
        """Counsel (readonly_admin) is on the require_roles('admin') allow-list.
        Note the observed status; 403 would be acceptable current behaviour."""
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}",
                         headers=_h(counsel_token), timeout=60)
        assert r.status_code in (200, 403), f"unexpected {r.status_code}: {r.text[:300]}"
        if r.status_code == 200:
            d = r.json()
            assert DISCLAIMER_TEXT not in (d.get("released_md") or "")
            assert DISCLAIMER_TEXT not in (d.get("content_md") or "")


# --------------------------------------------------------- regressions
class TestRegressions:
    def test_upload_creates_draft_and_lists(self, admin_token, working_draft):
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts",
                         headers=_h(admin_token), timeout=60)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        slugs = [row["source_slug"] for row in rows]
        assert SLUG in slugs
        row = next(r_ for r_ in rows if r_["source_slug"] == SLUG)
        assert row["state"] in ("draft", "awaiting_admin")
        assert "comment_stats" in row

    def test_line_anchored_comment(self, admin_token, working_draft):
        payload = {"body": "TEST_iter53 line-anchored comment", "line_number": 3,
                   "side": "working"}
        r = requests.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments",
                          headers=_h(admin_token), json=payload, timeout=60)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:400]}"
        created = r.json()
        cid = created.get("id") or (created.get("comment") or {}).get("id")
        assert cid, f"no comment id: {created}"
        g = requests.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments",
                         headers=_h(admin_token), timeout=60)
        assert g.status_code == 200
        body = g.json()
        rows = body if isinstance(body, list) else body.get("comments", [])
        match = [c for c in rows if c.get("id") == cid]
        assert match, "comment did not persist"
        assert match[0]["line_number"] == 3
        assert match[0]["side"] == "working"
        assert "_id" not in match[0]
        # cleanup
        requests.delete(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{cid}",
                        headers=_h(admin_token), timeout=60)

    def test_docs_bundle_zip(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/legal/docs-bundle.zip",
                         headers=_h(admin_token), timeout=120)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert r.content[:2] == b"PK", "not a zip payload"
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert zf.testzip() is None
        names = zf.namelist()
        assert len(names) > 3, names
        assert any(n.endswith(".md") or n.endswith(".docx") for n in names)

    def test_public_page_still_renders_without_disclaimer_body(self):
        r = requests.get(f"{BASE_URL}/api/legal/pages/cookie-notice", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d.get("has_draft_disclaimer") in (True, False)
        assert "html" in d
