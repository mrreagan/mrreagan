"""Iter 23 — v1.11.0 Step 10. Refund/clawback cascade + Agreement v2 gate.

Covers:
- Agreement v2.0 published as active (v1.0 inactive).
- Agreement gate: demo (unsigned v2) blocked on POST /api/dm/threads + POST /api/subscriptions/checkout.
- Sign v2.0 unblocks; non-gated endpoints (GET, dispute file) work either way.
- Refund cascade: workshop / subscription / featured / research_promotion / order / sponsor / donation.
- Already-refunded txn rejected.
- Clawback: earned credits flipped to reversed; paid credits enqueued to clawback_pending.
- GET /api/admin/clawbacks enriches partner_name/email; POST resolve flips status; double-resolve rejected.
- GET /api/admin/refunds list (filter txn_type) + GET /{cascade_id} detail.
- Dispute → refund integration: trigger_refund_cascade=true requires txn + non-dismissed outcome;
  cascade_id persisted on resolution + last event.
- Iter22 dispute filing regression (gate must NOT block disputes).
"""
import os
import time
import uuid

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN = {"email": "admin@birthright.org", "password": "birthright2026"}
DEMO = {"email": "demo@birthright.org", "password": "birthright2026"}
ELENA = {"email": "elena@birthright.org", "password": "birthright2026"}


# ---------- helpers ----------

def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    return s, r.json()["user"]


def _now_iso():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _mk_txn(db, *, txn_type, amount=50.0, session_id=None, metadata=None, user_id=None):
    session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
    txn = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": user_id,
        "type": txn_type,
        "amount": amount,
        "currency": "usd",
        "payment_status": "paid",
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }
    db.payment_transactions.insert_one(dict(txn))
    return txn


@pytest.fixture(scope="module")
def mongo_db():
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    yield db
    cli.close()


@pytest.fixture(scope="module")
def admin_client():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def demo_client():
    return _login(DEMO)


@pytest.fixture(scope="module", autouse=True)
def _cleanup_at_end(mongo_db):
    """Reset demo's v2 signature so the gate-block tests can re-run cleanly."""
    db = mongo_db
    demo = db.users.find_one({"email": DEMO["email"]})
    if demo:
        active = db.indemnification_versions.find_one({"active": True})
        if active:
            db.indemnification_signatures.delete_many({
                "user_id": demo["id"], "version_id": active["id"],
            })
    yield
    # Cleanup synthetic txns + cascades + clawbacks
    db.payment_transactions.delete_many({"session_id": {"$regex": "^sess_TEST_"}})
    db.refund_cascades.delete_many({"reason": {"$regex": "^TEST_"}})
    db.clawback_pending.delete_many({"original_payment_session_id": {"$regex": "^sess_TEST_"}})


# ============ 1. Agreement v2 published ============

class TestAgreementV2Published:
    def test_active_version_is_v2(self):
        r = requests.get(f"{BASE_URL}/api/legal/indemnification/active", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body["version"] == "2.0"
        assert body["active"] is True

    def test_versions_list_v1_inactive_v2_active(self, admin_client):
        s, _ = admin_client
        r = s.get(f"{BASE_URL}/api/legal/indemnification/versions", timeout=10)
        assert r.status_code == 200
        versions = {v["version"]: v for v in r.json()}
        assert "2.0" in versions and versions["2.0"]["active"] is True
        if "1.0" in versions:
            assert versions["1.0"]["active"] is False


# ============ 2. Agreement gate blocks DM + sub checkout ============

class TestAgreementGate:
    def test_demo_dm_thread_blocked_unsigned(self, demo_client, admin_client):
        # Demo (unsigned) tries to open a DM thread to admin -> 409 agreement_required.
        s, _ = demo_client
        _, admin_user = admin_client
        r = s.post(f"{BASE_URL}/api/dm/threads",
                   json={"recipient_id": admin_user["id"], "first_message": "TEST_iter23 gate"},
                   timeout=10)
        assert r.status_code == 409, r.text
        detail = r.json().get("detail")
        assert isinstance(detail, dict)
        assert detail.get("code") == "agreement_required"
        assert detail.get("active_version") == "2.0"

    def test_demo_sub_checkout_blocked_unsigned(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/subscriptions/checkout",
                   json={"plan_id": "any-plan", "origin_url": BASE_URL},
                   timeout=10)
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "agreement_required"

    def test_get_endpoints_not_gated(self, demo_client):
        # Reading available plans should NOT be gated.
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/subscriptions/me", timeout=10)
        assert r.status_code in (200, 404), r.text  # not 409

    def test_dispute_filing_not_gated(self, demo_client, admin_client):
        # Disputes endpoint not gated; should NOT 409. (Spec: only DM threads + sub checkout gated.)
        s, _ = demo_client
        _, admin_user = admin_client
        r = s.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": admin_user["id"],
            "category": "other",
            "title": "TEST_iter23 gate bypass",
            "description": "TEST_iter23 disputes must not be agreement-gated, sanity check.",
        }, timeout=10)
        # Either 201 (created) or some other non-409.
        assert r.status_code != 409, f"Disputes should not be gated; got {r.status_code} {r.text}"


# ============ 3. Sign v2 unblocks ============

class TestAgreementSignUnblocks:
    def test_sign_then_dm_open_succeeds(self, demo_client, admin_client):
        s, _ = demo_client
        _, admin_user = admin_client
        # Sign
        sign = s.post(f"{BASE_URL}/api/legal/indemnification/sign", json={}, timeout=10)
        assert sign.status_code == 200, sign.text
        # Now open thread (need unique recipient or it returns existing thread — either is fine).
        r = s.post(f"{BASE_URL}/api/dm/threads",
                   json={"recipient_id": admin_user["id"], "first_message": "TEST_iter23 post-sign"},
                   timeout=10)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert "id" in body or "thread" in body

    def test_sub_checkout_no_longer_409(self, demo_client):
        s, _ = demo_client
        r = s.post(f"{BASE_URL}/api/subscriptions/checkout",
                   json={"plan_id": "does-not-exist", "origin_url": BASE_URL},
                   timeout=10)
        # Gate cleared; backend will now produce a real plan validation error (likely 404/400),
        # NOT 409 agreement_required.
        assert r.status_code != 409, r.text


# ============ 4. Refund cascade — workshop ============

class TestWorkshopRefund:
    def test_workshop_refund_cancels_reg_and_increments_spots(self, admin_client, mongo_db):
        db = mongo_db
        s, admin_user = admin_client
        # Pick a workshop with spots_left
        ws = db.workshops.find_one({"spots_left": {"$gt": 0}})
        assert ws, "Need at least one workshop with spots"
        before_spots = ws["spots_left"]
        session_id = f"sess_TEST_ws_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="workshop", amount=100.0, session_id=session_id, user_id=admin_user["id"])
        reg = {
            "id": str(uuid.uuid4()),
            "workshop_id": ws["id"],
            "user_id": admin_user["id"],
            "payment_session_id": session_id,
            "status": "registered",
            "created_at": _now_iso(),
        }
        db.registrations.insert_one(dict(reg))

        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": txn["id"], "reason": "TEST_iter23 workshop refund", "skip_stripe": True},
                   timeout=20)
        assert r.status_code == 200, r.text
        cascade = r.json()
        assert cascade["txn_type"] == "workshop"
        assert cascade["side_effects"]["registration_id"] == reg["id"]

        # DB-level: registration cancelled
        reg_after = db.registrations.find_one({"id": reg["id"]})
        assert reg_after["status"] == "cancelled"
        # DB-level: spots_left incremented
        ws_after = db.workshops.find_one({"id": ws["id"]})
        assert ws_after["spots_left"] == before_spots + 1
        # txn marked refunded
        txn_after = db.payment_transactions.find_one({"id": txn["id"]})
        assert txn_after["payment_status"] == "refunded"
        assert txn_after.get("refund_result") is not None

        # Cleanup
        db.registrations.delete_one({"id": reg["id"]})
        db.workshops.update_one({"id": ws["id"]}, {"$set": {"spots_left": before_spots}})

    def test_double_refund_rejected(self, admin_client, mongo_db):
        db = mongo_db
        s, admin_user = admin_client
        session_id = f"sess_TEST_dbl_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="workshop", session_id=session_id, user_id=admin_user["id"])
        r1 = s.post(f"{BASE_URL}/api/admin/refunds",
                    json={"txn_id": txn["id"], "reason": "TEST_iter23 first", "skip_stripe": True},
                    timeout=15)
        assert r1.status_code == 200
        r2 = s.post(f"{BASE_URL}/api/admin/refunds",
                    json={"txn_id": txn["id"], "reason": "TEST_iter23 second", "skip_stripe": True},
                    timeout=15)
        assert r2.status_code == 400
        assert "already refunded" in r2.text.lower()

    def test_unknown_txn_400(self, admin_client):
        s, _ = admin_client
        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": "no-such-txn-id", "reason": "TEST_iter23 ghost", "skip_stripe": True},
                   timeout=10)
        assert r.status_code == 400
        assert "not found" in r.text.lower()


# ============ 5. Subscription / featured / research / order / sponsor / donation refunds ============

class TestOtherSideEffects:
    def test_subscription_refund(self, admin_client, mongo_db):
        db = mongo_db
        s, admin_user = admin_client
        session_id = f"sess_TEST_sub_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="subscription", session_id=session_id, amount=29.0, user_id=admin_user["id"])
        sub = {
            "id": str(uuid.uuid4()), "user_id": admin_user["id"],
            "payment_session_id": session_id, "status": "active",
            "plan_id": "tier1", "created_at": _now_iso(),
        }
        db.partner_subscriptions.insert_one(dict(sub))
        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": txn["id"], "reason": "TEST_iter23 sub", "skip_stripe": True}, timeout=15)
        assert r.status_code == 200, r.text
        sub_after = db.partner_subscriptions.find_one({"id": sub["id"]})
        assert sub_after["status"] == "revoked"
        assert sub_after.get("expires_at")
        db.partner_subscriptions.delete_one({"id": sub["id"]})

    def test_featured_slot_refund(self, admin_client, mongo_db):
        db = mongo_db
        s, admin_user = admin_client
        # Find or fabricate a partner profile
        prof = db.partner_profiles.find_one({})
        if not prof:
            prof = {"id": str(uuid.uuid4()), "slug": "test-iter23",
                    "name": "TEST_iter23", "created_at": _now_iso(),
                    "featured_until": "2099-01-01T00:00:00+00:00"}
            db.partner_profiles.insert_one(dict(prof))
            cleanup = True
        else:
            cleanup = False
            db.partner_profiles.update_one({"id": prof["id"]},
                {"$set": {"featured_until": "2099-01-01T00:00:00+00:00"}})

        session_id = f"sess_TEST_feat_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="featured_slot", session_id=session_id,
                      metadata={"partner_profile_id": prof["id"]}, user_id=admin_user["id"])
        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": txn["id"], "reason": "TEST_iter23 feat", "skip_stripe": True}, timeout=15)
        assert r.status_code == 200
        prof_after = db.partner_profiles.find_one({"id": prof["id"]})
        # featured_until pushed to now (<= now+1min); compare loose: must NOT still be 2099.
        assert prof_after["featured_until"].startswith("20") and "2099" not in prof_after["featured_until"]
        if cleanup:
            db.partner_profiles.delete_one({"id": prof["id"]})

    def test_research_promotion_refund(self, admin_client, mongo_db):
        db = mongo_db
        s, admin_user = admin_client
        artifact = {
            "id": str(uuid.uuid4()), "title": "TEST_iter23 artifact",
            "is_promoted": True, "promoted_until": "2099-01-01T00:00:00+00:00",
            "created_at": _now_iso(),
        }
        db.research_artifacts.insert_one(dict(artifact))
        session_id = f"sess_TEST_res_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="research_promotion", session_id=session_id,
                      metadata={"artifact_id": artifact["id"]}, user_id=admin_user["id"])
        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": txn["id"], "reason": "TEST_iter23 res", "skip_stripe": True}, timeout=15)
        assert r.status_code == 200
        a_after = db.research_artifacts.find_one({"id": artifact["id"]})
        assert a_after["is_promoted"] is False
        db.research_artifacts.delete_one({"id": artifact["id"]})

    def test_order_refund(self, admin_client, mongo_db):
        db = mongo_db
        s, admin_user = admin_client
        session_id = f"sess_TEST_ord_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="order", session_id=session_id, amount=42.0, user_id=admin_user["id"])
        order = {"id": str(uuid.uuid4()), "user_id": admin_user["id"],
                 "payment_session_id": session_id, "status": "paid",
                 "items": [], "total_usd": 42.0, "created_at": _now_iso()}
        db.orders.insert_one(dict(order))
        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": txn["id"], "reason": "TEST_iter23 order", "skip_stripe": True}, timeout=15)
        assert r.status_code == 200
        o_after = db.orders.find_one({"id": order["id"]})
        assert o_after["status"] == "refunded"
        db.orders.delete_one({"id": order["id"]})

    def test_sponsor_refund(self, admin_client, mongo_db):
        db = mongo_db
        s, admin_user = admin_client
        session_id = f"sess_TEST_spn_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="sponsorship", session_id=session_id, amount=500.0, user_id=admin_user["id"])
        sp = {"id": str(uuid.uuid4()), "user_id": admin_user["id"],
              "payment_session_id": session_id, "status": "active",
              "amount_usd": 500.0, "created_at": _now_iso()}
        db.sponsors.insert_one(dict(sp))
        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": txn["id"], "reason": "TEST_iter23 spn", "skip_stripe": True}, timeout=15)
        assert r.status_code == 200
        sp_after = db.sponsors.find_one({"id": sp["id"]})
        assert sp_after["status"] == "refunded"
        db.sponsors.delete_one({"id": sp["id"]})

    def test_donation_refund(self, admin_client, mongo_db):
        db = mongo_db
        s, admin_user = admin_client
        session_id = f"sess_TEST_don_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="donation", session_id=session_id, amount=20.0, user_id=admin_user["id"])
        dn = {"id": str(uuid.uuid4()), "user_id": admin_user["id"],
              "payment_session_id": session_id, "status": "received",
              "amount_usd": 20.0, "created_at": _now_iso()}
        db.donations.insert_one(dict(dn))
        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": txn["id"], "reason": "TEST_iter23 don", "skip_stripe": True}, timeout=15)
        assert r.status_code == 200
        dn_after = db.donations.find_one({"id": dn["id"]})
        assert dn_after["status"] == "refunded"
        db.donations.delete_one({"id": dn["id"]})


# ============ 6. Clawbacks ============

class TestClawbacks:
    def test_earned_reversed_and_paid_enqueued(self, admin_client, mongo_db, demo_client):
        db = mongo_db
        s, admin_user = admin_client
        _, demo_user = demo_client

        session_id = f"sess_TEST_cb_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="order", session_id=session_id, amount=120.0)
        # Earned referral
        earned = {"id": str(uuid.uuid4()), "partner_user_id": demo_user["id"],
                  "payment_session_id": session_id, "amount_usd": 12.0,
                  "status": "earned", "created_at": _now_iso()}
        db.referral_payouts.insert_one(dict(earned))
        # Paid referral
        paid = {"id": str(uuid.uuid4()), "partner_user_id": demo_user["id"],
                "payment_session_id": session_id, "amount_usd": 8.0,
                "status": "paid", "created_at": _now_iso()}
        db.referral_payouts.insert_one(dict(paid))
        # Earned off-site
        off_earned = {"id": str(uuid.uuid4()), "partner_user_id": demo_user["id"],
                      "source_session_id": session_id, "amount_usd": 5.0,
                      "status": "earned", "created_at": _now_iso()}
        db.partner_off_site_credits.insert_one(dict(off_earned))

        r = s.post(f"{BASE_URL}/api/admin/refunds",
                   json={"txn_id": txn["id"], "reason": "TEST_iter23 clawback flow", "skip_stripe": True}, timeout=15)
        assert r.status_code == 200, r.text
        cascade = r.json()
        assert cascade["credit_clawback"]["reversed_count"] == 2
        assert cascade["credit_clawback"]["paid_clawback_count"] == 1

        # DB verify reversed
        assert db.referral_payouts.find_one({"id": earned["id"]})["status"] == "reversed"
        assert db.referral_payouts.find_one({"id": earned["id"]}).get("reverse_reason") == "refund cascade"
        assert db.partner_off_site_credits.find_one({"id": off_earned["id"]})["status"] == "reversed"

        # clawback_pending row created
        cb = db.clawback_pending.find_one({"credit_id": paid["id"]})
        assert cb is not None
        assert cb["status"] == "pending_recovery"

        # GET /api/admin/clawbacks enriched
        list_r = s.get(f"{BASE_URL}/api/admin/clawbacks", timeout=10)
        assert list_r.status_code == 200
        rows = list_r.json()
        target = next((x for x in rows if x["id"] == cb["id"]), None)
        assert target is not None
        assert target["partner_email"] == demo_user["email"]
        assert "partner_name" in target

        # Resolve
        res = s.post(f"{BASE_URL}/api/admin/clawbacks/{cb['id']}/resolve",
                     json={"status": "recovered", "note": "TEST_iter23 recovered"}, timeout=10)
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "recovered"

        # Double-resolve rejected
        res2 = s.post(f"{BASE_URL}/api/admin/clawbacks/{cb['id']}/resolve",
                      json={"status": "written_off", "note": "TEST_iter23 again"}, timeout=10)
        assert res2.status_code == 400

        # Short note rejected (validation)
        # Re-insert a paid row + clawback so we have a fresh one
        cb_fresh_id = str(uuid.uuid4())
        db.clawback_pending.insert_one({
            "id": cb_fresh_id, "source": "on_site_referral", "credit_id": "x",
            "partner_user_id": demo_user["id"], "amount_usd": 1.0,
            "original_payment_session_id": session_id, "original_txn_id": txn["id"],
            "status": "pending_recovery", "created_at": _now_iso(),
        })
        short = s.post(f"{BASE_URL}/api/admin/clawbacks/{cb_fresh_id}/resolve",
                       json={"status": "recovered", "note": "ab"}, timeout=10)
        assert short.status_code == 422

        # Cleanup
        db.referral_payouts.delete_many({"id": {"$in": [earned["id"], paid["id"]]}})
        db.partner_off_site_credits.delete_one({"id": off_earned["id"]})


# ============ 7. List / detail cascade endpoints ============

class TestCascadeAdminEndpoints:
    def test_list_filter_and_detail(self, admin_client, mongo_db):
        s, _ = admin_client
        db = mongo_db
        r_all = s.get(f"{BASE_URL}/api/admin/refunds", timeout=10)
        assert r_all.status_code == 200
        rows = r_all.json()
        assert isinstance(rows, list)
        # sorted desc
        if len(rows) >= 2:
            assert rows[0]["created_at"] >= rows[1]["created_at"]
        # filter by txn_type=workshop should return only workshop cascades
        r_ws = s.get(f"{BASE_URL}/api/admin/refunds?txn_type=workshop", timeout=10)
        assert r_ws.status_code == 200
        assert all(c["txn_type"] == "workshop" for c in r_ws.json())

        if rows:
            cid = rows[0]["id"]
            r_det = s.get(f"{BASE_URL}/api/admin/refunds/{cid}", timeout=10)
            assert r_det.status_code == 200
            assert r_det.json()["id"] == cid
        r_404 = s.get(f"{BASE_URL}/api/admin/refunds/does-not-exist", timeout=10)
        assert r_404.status_code == 404

    def test_non_admin_cannot_access(self, demo_client):
        s, _ = demo_client
        r = s.get(f"{BASE_URL}/api/admin/refunds", timeout=10)
        assert r.status_code in (401, 403)
        r2 = s.post(f"{BASE_URL}/api/admin/refunds",
                    json={"txn_id": "x", "reason": "TEST_iter23 no", "skip_stripe": True}, timeout=10)
        assert r2.status_code in (401, 403)


# ============ 8. Dispute → refund integration ============

class TestDisputeRefundIntegration:
    def test_resolve_with_cascade_persists_cascade_id(self, admin_client, demo_client, mongo_db):
        db = mongo_db
        s_admin, admin_user = admin_client
        s_demo, demo_user = demo_client

        # Create txn
        session_id = f"sess_TEST_dispute_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="order", session_id=session_id, amount=33.0, user_id=demo_user["id"])
        # Create matching order
        order = {"id": str(uuid.uuid4()), "user_id": demo_user["id"],
                 "payment_session_id": session_id, "status": "paid",
                 "items": [], "total_usd": 33.0, "created_at": _now_iso()}
        db.orders.insert_one(dict(order))

        # Demo files a dispute (note: demo signed v2 in earlier test class — disputes not gated regardless)
        r_file = s_demo.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": admin_user["id"],
            "category": "payment",
            "title": "TEST_iter23 cascade dispute",
            "description": "TEST_iter23 dispute with txn for cascade integration check.",
            "transaction_id": txn["id"],
        }, timeout=10)
        assert r_file.status_code in (200, 201), r_file.text
        dispute = r_file.json()
        dispute_id = dispute["id"]

        # Admin resolves with cascade trigger
        r_res = s_admin.post(
            f"{BASE_URL}/api/admin/disputes/{dispute_id}/resolve",
            json={
                "outcome": "upheld",
                "resolution_note": "TEST_iter23 upholding + refunding via cascade.",
                "trigger_refund_cascade": True,
            }, timeout=20,
        )
        assert r_res.status_code == 200, r_res.text
        res_body = r_res.json()
        assert res_body["status"] == "resolved"
        cid = res_body["resolution"]["refund_cascade_id"]
        assert cid, "refund_cascade_id must be set on resolution"
        # Last event has cascade_id
        last_event = res_body["events"][-1]
        assert last_event.get("refund_cascade_id") == cid

        # Cascade row exists
        casc = db.refund_cascades.find_one({"id": cid})
        assert casc and casc.get("dispute_id") == dispute_id

        # Side-effect: order refunded
        assert db.orders.find_one({"id": order["id"]})["status"] == "refunded"

        db.orders.delete_one({"id": order["id"]})

    def test_resolve_cascade_requires_txn(self, admin_client, demo_client, mongo_db):
        db = mongo_db
        s_admin, admin_user = admin_client
        s_demo, _ = demo_client
        # File a dispute WITHOUT transaction_id
        r_file = s_demo.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": admin_user["id"],
            "category": "other",
            "title": "TEST_iter23 no-txn cascade",
            "description": "TEST_iter23 dispute without txn for cascade reject.",
        }, timeout=10)
        assert r_file.status_code in (200, 201), r_file.text
        did = r_file.json()["id"]
        r_res = s_admin.post(
            f"{BASE_URL}/api/admin/disputes/{did}/resolve",
            json={"outcome": "upheld",
                  "resolution_note": "TEST_iter23 cannot cascade without txn.",
                  "trigger_refund_cascade": True}, timeout=10,
        )
        assert r_res.status_code == 400
        assert "transaction" in r_res.text.lower() or "txn" in r_res.text.lower()
        # cleanup
        db.disputes.delete_one({"id": did})

    def test_resolve_cascade_rejects_dismissed(self, admin_client, demo_client, mongo_db):
        db = mongo_db
        s_admin, admin_user = admin_client
        s_demo, demo_user = demo_client
        session_id = f"sess_TEST_dis_{uuid.uuid4().hex[:8]}"
        txn = _mk_txn(db, txn_type="order", session_id=session_id, amount=10.0, user_id=demo_user["id"])
        r_file = s_demo.post(f"{BASE_URL}/api/disputes", json={
            "against_user_id": admin_user["id"],
            "category": "payment",
            "title": "TEST_iter23 dismiss-cascade",
            "description": "TEST_iter23 trying to cascade a dismissed dispute.",
            "transaction_id": txn["id"],
        }, timeout=10)
        assert r_file.status_code in (200, 201)
        did = r_file.json()["id"]
        r_res = s_admin.post(
            f"{BASE_URL}/api/admin/disputes/{did}/resolve",
            json={"outcome": "dismissed",
                  "resolution_note": "TEST_iter23 dismissing with cascade flag.",
                  "trigger_refund_cascade": True}, timeout=10,
        )
        assert r_res.status_code == 400
        db.disputes.delete_one({"id": did})
