"""Phase 6B.5 — Research submissions queue + admin moderation.

Covers:
  - Partner POST artifact with status="published" gets clamped to pending_review.
  - Partner POST with status="draft" stays as draft.
  - Partner POST /me/research/{id}/submit-for-review moves draft → pending_review.
  - Admin POST /admin/research/{id}/approve publishes it (visible on /research).
  - Admin POST .../request-changes requires a note and sets changes_requested.
  - Admin POST .../reject requires a note and sets rejected.
  - PUT on a published artifact's content re-queues it to pending_review.
  - Moderation endpoints reject non-admin callers (403).
  - Moderation endpoints reject artifacts not currently in pending_review.
"""
from __future__ import annotations

import os
import uuid

import httpx
import pytest

BASE = os.environ.get("BIRTHRIGHT_API_BASE", "http://localhost:8001/api")
ADMIN_EMAIL = os.environ.get("BIRTHRIGHT_ADMIN_EMAIL", "admin@birthright.live")
ADMIN_PASS = os.environ.get("BIRTHRIGHT_ADMIN_PASS", "birthright2026")


def _login(email: str, password: str) -> str:
    r = httpx.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["token"]


def _h(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_tok() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def partner_tok(admin_tok: str) -> str:
    """Create a dedicated research-partner user + active profile via admin APIs."""
    suffix = uuid.uuid4().hex[:8]
    email = f"research-pytest-{suffix}@birthright.live"
    password = "Pytest!ResearchModeration2026"
    reg = httpx.post(
        f"{BASE}/auth/register",
        json={"email": email, "password": password, "first_name": "Rene", "last_name": "Search"},
        timeout=10,
    )
    assert reg.status_code in (200, 201), reg.text
    # Promote to partner role
    user_id = reg.json()["user"]["id"]
    httpx.put(
        f"{BASE}/admin/users/{user_id}/role",
        json={"role": "partner"},
        headers=_h(admin_tok),
        timeout=10,
    )
    # Seed an active research partner profile directly via DB-like admin shortcut.
    # We use the public partner-apply + admin-approve flow.
    apply = httpx.post(
        f"{BASE}/partners/apply",
        json={
            "partner_type": "research",
            "display_name": f"Pytest Research Lab {suffix}",
            "headline": "Attachment research for pytest regression",
            "bio": "Pytest fixture lab for Phase 6B.5 moderation regression tests.",
            "area_of_research": "Attachment in test fixtures",
        },
        headers=_h(_login(email, password)),
        timeout=10,
    )
    assert apply.status_code in (200, 201), apply.text
    app_id = apply.json()["id"]
    appr = httpx.post(
        f"{BASE}/admin/partners/applications/{app_id}/approve",
        json={"note": "auto-approved by pytest fixture"},
        headers=_h(admin_tok),
        timeout=10,
    )
    assert appr.status_code in (200, 201), appr.text
    return _login(email, password)


def _payload(title: str, status: str = "draft") -> dict:
    return {
        "title": title,
        "abstract": "Abstract for regression test. " * 3,
        "authors": "Pytest Author",
        "publication_date": "2026-05-25",
        "full_text_url": "https://example.org/paper.pdf",
        "tier": "brief",
        "status": status,
    }


# ============ TESTS ============

def test_partner_published_is_clamped_to_pending(partner_tok: str):
    r = httpx.post(
        f"{BASE}/me/research",
        json=_payload("Clamp-To-Pending", status="published"),
        headers=_h(partner_tok),
        timeout=10,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["status"] == "pending_review"
    assert body["submitted_at"]


def test_partner_draft_stays_draft_then_submit(partner_tok: str):
    r = httpx.post(
        f"{BASE}/me/research",
        json=_payload("Draft-Then-Submit", status="draft"),
        headers=_h(partner_tok),
        timeout=10,
    )
    assert r.status_code in (200, 201)
    aid = r.json()["id"]
    assert r.json()["status"] == "draft"

    s = httpx.post(
        f"{BASE}/me/research/{aid}/submit-for-review",
        headers=_h(partner_tok),
        timeout=10,
    )
    assert s.status_code == 200, s.text
    assert s.json()["status"] == "pending_review"


def test_admin_approve_publishes(partner_tok: str, admin_tok: str):
    r = httpx.post(
        f"{BASE}/me/research",
        json=_payload("Admin-Approve-Me", status="pending_review"),
        headers=_h(partner_tok),
        timeout=10,
    )
    aid = r.json()["id"]
    a = httpx.post(
        f"{BASE}/admin/research/{aid}/approve",
        json={"note": "Looks good"},
        headers=_h(admin_tok),
        timeout=10,
    )
    assert a.status_code == 200, a.text
    assert a.json()["status"] == "published"

    # Visible on public feed?
    pub = httpx.get(f"{BASE}/research?q=Approve-Me", timeout=10).json()
    assert any(x["id"] == aid for x in pub)


def test_admin_request_changes_requires_note(partner_tok: str, admin_tok: str):
    r = httpx.post(
        f"{BASE}/me/research",
        json=_payload("Need-Changes", status="pending_review"),
        headers=_h(partner_tok),
        timeout=10,
    )
    aid = r.json()["id"]
    empty = httpx.post(
        f"{BASE}/admin/research/{aid}/request-changes",
        json={"note": ""},
        headers=_h(admin_tok),
        timeout=10,
    )
    assert empty.status_code == 400

    ok = httpx.post(
        f"{BASE}/admin/research/{aid}/request-changes",
        json={"note": "Please add a references section."},
        headers=_h(admin_tok),
        timeout=10,
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "changes_requested"
    assert ok.json()["moderation_note"] == "Please add a references section."


def test_admin_reject_requires_note(partner_tok: str, admin_tok: str):
    r = httpx.post(
        f"{BASE}/me/research",
        json=_payload("Reject-Me", status="pending_review"),
        headers=_h(partner_tok),
        timeout=10,
    )
    aid = r.json()["id"]
    bad = httpx.post(
        f"{BASE}/admin/research/{aid}/reject",
        json={"note": ""},
        headers=_h(admin_tok),
        timeout=10,
    )
    assert bad.status_code == 400
    ok = httpx.post(
        f"{BASE}/admin/research/{aid}/reject",
        json={"note": "Off-mission topic."},
        headers=_h(admin_tok),
        timeout=10,
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "rejected"


def test_partner_edit_on_published_requeues(partner_tok: str, admin_tok: str):
    r = httpx.post(
        f"{BASE}/me/research",
        json=_payload("Requeue-On-Edit", status="pending_review"),
        headers=_h(partner_tok),
        timeout=10,
    )
    aid = r.json()["id"]
    httpx.post(
        f"{BASE}/admin/research/{aid}/approve",
        json={"note": None},
        headers=_h(admin_tok),
        timeout=10,
    )
    # Partner tweaks the title — should re-queue.
    upd = httpx.put(
        f"{BASE}/me/research/{aid}",
        json={"title": "Requeue-On-Edit (revised)"},
        headers=_h(partner_tok),
        timeout=10,
    )
    assert upd.status_code == 200
    assert upd.json()["status"] == "pending_review"


def test_non_admin_blocked_from_moderation(partner_tok: str):
    # Partner tries to call admin moderate endpoint → 403
    r = httpx.post(
        f"{BASE}/me/research",
        json=_payload("Non-Admin-Test", status="pending_review"),
        headers=_h(partner_tok),
        timeout=10,
    )
    aid = r.json()["id"]
    forbidden = httpx.post(
        f"{BASE}/admin/research/{aid}/approve",
        json={"note": None},
        headers=_h(partner_tok),
        timeout=10,
    )
    assert forbidden.status_code in (401, 403)


def test_moderate_only_works_on_pending(partner_tok: str, admin_tok: str):
    r = httpx.post(
        f"{BASE}/me/research",
        json=_payload("Only-Pending", status="draft"),
        headers=_h(partner_tok),
        timeout=10,
    )
    aid = r.json()["id"]
    # Status is draft — cannot moderate.
    bad = httpx.post(
        f"{BASE}/admin/research/{aid}/approve",
        json={"note": None},
        headers=_h(admin_tok),
        timeout=10,
    )
    assert bad.status_code == 400
