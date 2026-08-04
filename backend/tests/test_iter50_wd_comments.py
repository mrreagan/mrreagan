"""Iteration 50 — Working-draft inline comments (threaded Q&A in diff view).

Modules under test:
  - backend/routers/legal.py
      GET    /api/legal/working-drafts/{slug}/comments
      POST   /api/legal/working-drafts/{slug}/comments
      POST   /api/legal/working-drafts/{slug}/comments/{id}/resolve
      DELETE /api/legal/working-drafts/{slug}/comments/{id}
      GET    /api/legal/working-drafts  (comment_stats per row)
"""
import io
import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

if "/app/backend" not in sys.path:
    sys.path.insert(0, "/app/backend")

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")

backend_env = dotenv_values("/app/backend/.env")
MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")

COUNSEL = ("counsel@birthright.live", "counsel-review-2026")
ADMIN = ("admin@birthright.live", "birthright2026")

SLUG = "03-cookie-notice"
SLUG2 = "01-terms-of-service"

UPLOAD_MD = (
    "# Cookie Notice (TEST_iter50)\n\nTEST_iter50 line one\n\n"
    "## Section A\n\n- bullet one\n- bullet two\n"
)
UPLOAD_MD2 = (
    "# Terms of Service (TEST_iter50)\n\nTEST_iter50 tos line\n\n## Scope\n\n- alpha\n"
)


# ------------------------------------------------------------------ helpers
def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed for {email}: {r.status_code} {r.text[:300]}")
    body = r.json()
    return body["token"], body["user"]


def _session(creds, expected_role):
    token, user = _login(*creds)
    assert user["role"] == expected_role, f"expected {expected_role}, got {user['role']}"
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    s.user = user
    return s


def _upload(session, slug, content, filename="draft.md"):
    return session.post(
        f"{BASE_URL}/api/legal/docs/{slug}/upload",
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/markdown")},
        timeout=120,
    )


def _post_comment(session, slug, **payload):
    return session.post(f"{BASE_URL}/api/legal/working-drafts/{slug}/comments",
                        json=payload, timeout=60)


def _list_comments(session, slug):
    return session.get(f"{BASE_URL}/api/legal/working-drafts/{slug}/comments", timeout=60)


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def counsel():
    return _session(COUNSEL, "readonly_admin")


@pytest.fixture(scope="module")
def admin():
    return _session(ADMIN, "admin")


@pytest.fixture(scope="module")
def source_snapshots():
    legal_dir = Path("/app/backend/legal_docs")
    keep = {}
    for slug in (SLUG, SLUG2):
        for ext in (".md", ".docx"):
            p = legal_dir / f"{slug}{ext}"
            if p.exists():
                keep[p] = p.read_bytes()
    yield keep
    for p, raw in keep.items():
        if p.read_bytes() != raw:
            p.write_bytes(raw)


@pytest.fixture(scope="module", autouse=True)
def cleanup(mongo, admin, source_snapshots):
    yield
    for slug in (SLUG, SLUG2):
        try:
            admin.post(f"{BASE_URL}/api/legal/working-drafts/{slug}/discard",
                       json={"reason": "TEST_iter50 cleanup"}, timeout=60)
        except Exception:
            pass
    wd_ids = [w["id"] for w in mongo.legal_doc_working_drafts.find(
        {"source_slug": {"$in": [SLUG, SLUG2]}}, {"id": 1})]
    mongo.legal_working_draft_comments.delete_many({"working_draft_id": {"$in": wd_ids}})
    mongo.legal_working_draft_comments.delete_many({"source_slug": {"$in": [SLUG, SLUG2]}})
    mongo.legal_doc_working_drafts.delete_many(
        {"source_slug": {"$in": [SLUG, SLUG2]},
         "content_md": {"$regex": "TEST_iter50"}})


@pytest.fixture(scope="module")
def wd(admin, counsel, mongo):
    """Ensure exactly one open working draft on SLUG created by counsel."""
    # discard any pre-existing open WD so state is deterministic
    admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
               json={"reason": "TEST_iter50 pre-clean"}, timeout=60)
    r = _upload(counsel, SLUG, UPLOAD_MD)
    assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:400]}"
    d = admin.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}", timeout=60)
    assert d.status_code == 200, d.text[:300]
    return d.json()


# =========================================================== GET /comments
class TestListComments:
    def test_no_open_wd_returns_empty_list(self, admin):
        # SLUG2 has no open WD at this point
        admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG2}/discard",
                   json={"reason": "TEST_iter50 pre-clean"}, timeout=60)
        r = _list_comments(admin, SLUG2)
        assert r.status_code == 200, r.text[:300]
        assert r.json() == []

    def test_empty_for_fresh_wd(self, admin, wd):
        r = _list_comments(admin, SLUG)
        assert r.status_code == 200
        assert r.json() == []

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments", timeout=60)
        assert r.status_code in (401, 403), r.status_code


# ========================================================== POST /comments
class TestCreateComment:
    def test_happy_path_shape(self, admin, wd):
        r = _post_comment(admin, SLUG, body="TEST_iter50 admin line comment",
                          line_number=3, side="working")
        assert r.status_code in (200, 201), r.text[:400]
        c = r.json()
        for k in ("id", "working_draft_id", "source_slug", "line_number", "side",
                  "parent_id", "body", "author_id", "author_email", "author_role",
                  "created_at", "resolved", "resolved_at", "resolved_by_email"):
            assert k in c, f"missing key {k}"
        assert "_id" not in c
        assert c["working_draft_id"] == wd["id"]
        assert c["source_slug"] == SLUG
        assert c["line_number"] == 3
        assert c["side"] == "working"
        assert c["parent_id"] is None
        assert c["author_email"] == ADMIN[0]
        assert c["author_role"] == "admin"
        assert c["resolved"] is False
        # persisted?
        rows = _list_comments(admin, SLUG).json()
        assert any(x["id"] == c["id"] for x in rows)

    def test_counsel_can_post_and_reply(self, admin, counsel, wd):
        parent = _post_comment(admin, SLUG, body="TEST_iter50 parent q",
                               line_number=5, side="working").json()
        r = _post_comment(counsel, SLUG, body="TEST_iter50 counsel reply",
                          parent_id=parent["id"], line_number=5, side="working")
        assert r.status_code in (200, 201), r.text[:400]
        reply = r.json()
        assert reply["parent_id"] == parent["id"]
        assert reply["author_email"] == COUNSEL[0]
        assert reply["author_role"] == "readonly_admin"

    def test_sorted_created_at_asc(self, admin, wd):
        rows = _list_comments(admin, SLUG).json()
        stamps = [x["created_at"] for x in rows]
        assert stamps == sorted(stamps)

    @pytest.mark.parametrize("payload", [
        {},
        {"body": ""},
        {"body": "   "},
    ])
    def test_empty_body_400(self, admin, wd, payload):
        r = _post_comment(admin, SLUG, **payload)
        assert r.status_code == 400, f"{r.status_code} {r.text[:300]}"

    def test_body_too_long_400(self, admin, wd):
        r = _post_comment(admin, SLUG, body="x" * 4097)
        assert r.status_code == 400, r.text[:300]

    def test_body_at_limit_ok(self, admin, wd, mongo):
        r = _post_comment(admin, SLUG, body="T" * 4096)
        assert r.status_code in (200, 201), r.text[:300]
        mongo.legal_working_draft_comments.delete_one({"id": r.json()["id"]})

    def test_bad_side_400(self, admin, wd):
        r = _post_comment(admin, SLUG, body="TEST_iter50 bad side", side="middle")
        assert r.status_code == 400, r.text[:300]

    @pytest.mark.parametrize("line", [0, -1, "abc", ""])
    def test_invalid_line_number_coerced_to_general(self, admin, wd, mongo, line):
        r = _post_comment(admin, SLUG, body=f"TEST_iter50 line {line!r}",
                          line_number=line, side="general")
        assert r.status_code in (200, 201), f"{line!r} -> {r.status_code} {r.text[:300]}"
        c = r.json()
        assert c["line_number"] is None, f"{line!r} became {c['line_number']!r}"
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_float_line_number_truncates(self, admin, wd, mongo):
        """Documented behaviour: float line numbers truncate via int()."""
        r = _post_comment(admin, SLUG, body="TEST_iter50 float line",
                          line_number=1.9, side="working")
        assert r.status_code in (200, 201)
        c = r.json()
        assert c["line_number"] == 1
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_numeric_string_line_number_coerced_to_int(self, admin, wd, mongo):
        r = _post_comment(admin, SLUG, body="TEST_iter50 strline",
                          line_number="7", side="working")
        assert r.status_code in (200, 201)
        c = r.json()
        assert c["line_number"] == 7 and isinstance(c["line_number"], int)
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_default_side_general(self, admin, wd, mongo):
        r = _post_comment(admin, SLUG, body="TEST_iter50 default side")
        assert r.status_code in (200, 201)
        c = r.json()
        assert c["side"] == "general"
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_parent_on_other_wd_404(self, admin, counsel, wd, mongo):
        """Parent id belonging to a DIFFERENT working draft must 404."""
        r = _upload(counsel, SLUG2, UPLOAD_MD2)
        assert r.status_code == 200, r.text[:300]
        other = _post_comment(admin, SLUG2, body="TEST_iter50 other wd parent",
                              line_number=1, side="working")
        assert other.status_code in (200, 201), other.text[:300]
        other_id = other.json()["id"]
        bad = _post_comment(admin, SLUG, body="TEST_iter50 cross-wd reply",
                            parent_id=other_id)
        assert bad.status_code == 404, f"{bad.status_code} {bad.text[:300]}"

    def test_unknown_parent_404(self, admin, wd):
        r = _post_comment(admin, SLUG, body="TEST_iter50 ghost parent",
                          parent_id="does-not-exist")
        assert r.status_code == 404, r.text[:300]

    def test_no_open_wd_404(self, admin, mongo):
        slug3 = "13-ombudsman-charter"
        admin.post(f"{BASE_URL}/api/legal/working-drafts/{slug3}/discard",
                   json={"reason": "TEST_iter50 pre-clean"}, timeout=60)
        r = _post_comment(admin, slug3, body="TEST_iter50 no wd")
        assert r.status_code == 404, f"{r.status_code} {r.text[:300]}"
        assert "working draft" in r.json().get("detail", "").lower()


# ======================================================= comment_stats list
class TestCommentStats:
    def test_stats_present_and_correct(self, admin, wd):
        r = admin.get(f"{BASE_URL}/api/legal/working-drafts", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        by_id = {x["id"]: x for x in rows}
        assert wd["id"] in by_id, "open WD missing from list"
        for row in rows:
            assert "comment_stats" in row
            assert set(row["comment_stats"]) == {"total", "open"}
        expected_total = len(_list_comments(admin, SLUG).json())
        expected_open = len([c for c in _list_comments(admin, SLUG).json()
                             if not c["resolved"]])
        st = by_id[wd["id"]]["comment_stats"]
        assert st["total"] == expected_total, st
        assert st["open"] == expected_open, st

    def test_stats_isolated_per_wd(self, admin, wd):
        rows = admin.get(f"{BASE_URL}/api/legal/working-drafts", timeout=60).json()
        by_slug = {x["source_slug"]: x for x in rows}
        assert SLUG2 in by_slug, "second WD not listed"
        s2 = by_slug[SLUG2]["comment_stats"]
        s2_actual = _list_comments(admin, SLUG2).json()
        assert s2["total"] == len(s2_actual)
        assert s2["total"] >= 1
        assert by_slug[SLUG]["comment_stats"]["total"] != 0


# ================================================================== resolve
class TestResolve:
    def _fresh(self, session, mongo):
        c = _post_comment(session, SLUG, body="TEST_iter50 resolvable",
                          line_number=2, side="working").json()
        return c

    def test_resolve_true(self, admin, wd, mongo):
        c = self._fresh(admin, mongo)
        r = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c['id']}/resolve",
                       json={"resolved": True}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["resolved"] is True
        assert d["resolved_at"]
        assert d["resolved_by_email"] == ADMIN[0]
        persisted = [x for x in _list_comments(admin, SLUG).json() if x["id"] == c["id"]][0]
        assert persisted["resolved"] is True
        assert persisted["resolved_by_email"] == ADMIN[0]
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_unresolve(self, admin, wd, mongo):
        c = self._fresh(admin, mongo)
        admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c['id']}/resolve",
                   json={"resolved": True}, timeout=60)
        r = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c['id']}/resolve",
                       json={"resolved": False}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["resolved"] is False
        assert d["resolved_at"] is None
        assert d["resolved_by_email"] is None
        persisted = [x for x in _list_comments(admin, SLUG).json() if x["id"] == c["id"]][0]
        assert persisted["resolved"] is False
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_empty_body_defaults_true(self, admin, wd, mongo):
        c = self._fresh(admin, mongo)
        r = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c['id']}/resolve",
                       timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        assert r.json()["resolved"] is True
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_empty_json_defaults_true(self, admin, wd, mongo):
        c = self._fresh(admin, mongo)
        r = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c['id']}/resolve",
                       json={}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["resolved"] is True
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_counsel_can_resolve_admin_comment(self, admin, counsel, wd, mongo):
        c = self._fresh(admin, mongo)
        r = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c['id']}/resolve",
                         json={"resolved": True}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["resolved_by_email"] == COUNSEL[0]
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_unknown_comment_404(self, admin, wd):
        r = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/nope/resolve",
                       json={"resolved": True}, timeout=60)
        assert r.status_code == 404, r.text[:300]

    def test_cross_wd_comment_404(self, admin, wd):
        other = _list_comments(admin, SLUG2).json()
        assert other, "expected a comment on SLUG2"
        r = admin.post(
            f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{other[0]['id']}/resolve",
            json={"resolved": True}, timeout=60)
        assert r.status_code == 404, r.text[:300]


# =================================================================== delete
class TestDelete:
    def test_counsel_cannot_delete_admin_comment(self, admin, counsel, wd, mongo):
        c = _post_comment(admin, SLUG, body="TEST_iter50 admin owned",
                          line_number=4, side="working").json()
        r = counsel.delete(
            f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c['id']}", timeout=60)
        assert r.status_code == 403, f"{r.status_code} {r.text[:300]}"
        assert r.json().get("detail") == "You can only delete your own comments."
        # still there
        assert any(x["id"] == c["id"] for x in _list_comments(admin, SLUG).json())
        mongo.legal_working_draft_comments.delete_one({"id": c["id"]})

    def test_counsel_can_delete_own(self, counsel, admin, wd):
        c = _post_comment(counsel, SLUG, body="TEST_iter50 counsel owned",
                          line_number=4, side="working").json()
        r = counsel.delete(
            f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c['id']}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["deleted"] == 1
        assert not any(x["id"] == c["id"] for x in _list_comments(admin, SLUG).json())

    def test_admin_cascade_delete_removes_replies(self, admin, counsel, wd):
        parent = _post_comment(admin, SLUG, body="TEST_iter50 cascade parent",
                               line_number=6, side="working").json()
        reply1 = _post_comment(counsel, SLUG, body="TEST_iter50 cascade reply 1",
                               parent_id=parent["id"], line_number=6, side="working").json()
        reply2 = _post_comment(admin, SLUG, body="TEST_iter50 cascade reply 2",
                               parent_id=parent["id"], line_number=6, side="working").json()
        r = admin.delete(
            f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{parent['id']}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["deleted"] == 3, r.json()
        ids = {x["id"] for x in _list_comments(admin, SLUG).json()}
        assert parent["id"] not in ids
        assert reply1["id"] not in ids
        assert reply2["id"] not in ids

    def test_delete_unknown_404(self, admin, wd):
        r = admin.delete(
            f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/ghost", timeout=60)
        assert r.status_code == 404, r.text[:300]


# ==================================================== WD cycle / comment scope
class TestWdCycleScoping:
    def test_comments_survive_in_db_but_not_returned_after_discard(
            self, admin, counsel, mongo):
        """Discard the SLUG2 WD → its comments stay in DB but GET returns []."""
        wd2 = admin.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG2}", timeout=60).json()
        before = _list_comments(admin, SLUG2).json()
        assert before, "expected existing SLUG2 comments"
        d = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG2}/discard",
                       json={"reason": "TEST_iter50 scope check"}, timeout=60)
        assert d.status_code == 200, d.text[:300]
        assert _list_comments(admin, SLUG2).json() == []
        still = list(mongo.legal_working_draft_comments.find(
            {"working_draft_id": wd2["id"]}, {"_id": 0, "id": 1}))
        assert len(still) == len(before), "comments were deleted from DB"
        # new WD on same slug starts with zero comments
        r = _upload(counsel, SLUG2, UPLOAD_MD2 + "\n- beta\n")
        assert r.status_code == 200, r.text[:300]
        assert _list_comments(admin, SLUG2).json() == []
        rows = admin.get(f"{BASE_URL}/api/legal/working-drafts", timeout=60).json()
        new = [x for x in rows if x["source_slug"] == SLUG2][0]
        assert new["comment_stats"] == {"total": 0, "open": 0}, new["comment_stats"]
