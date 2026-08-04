"""Seed / teardown helper for iteration-51 frontend testing.

seed:      2 releases on 03-cookie-notice (so History has a rollback target)
           + one open working draft with a comment containing @admin/@counsel
teardown:  discard WD, delete TEST_iter51fe comments/WDs/ratifications/emails,
           restore the on-disk .md/.docx from the pre-seed snapshot.

Usage:  python fe_setup_iter51.py seed
        python fe_setup_iter51.py teardown
"""
import io
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL")).rstrip("/")
benv = dotenv_values("/app/backend/.env")
MONGO_URL = os.environ.get("MONGO_URL") or benv.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or benv.get("DB_NAME")

SLUG = "03-cookie-notice"
ADMIN = ("admin@birthright.live", "birthright2026")
COUNSEL = ("counsel@birthright.live", "counsel-review-2026")
LEGAL_DIR = Path("/app/backend/legal_docs")
SNAP_DIR = Path("/tmp/iter51_snapshot")

REL_A = ("# Cookie Notice (TEST_iter51fe A)\n\nTEST_iter51fe alpha paragraph\n\n"
         "## Section A\n\n- alpha one\n- alpha two\n")
REL_B = ("# Cookie Notice (TEST_iter51fe B)\n\nTEST_iter51fe beta paragraph rewritten\n\n"
         "## Section B\n\n- beta one\n- beta two\n- beta three\n")
WD_MD = ("# Cookie Notice (TEST_iter51fe WD)\n\nTEST_iter51fe working draft line\n\n"
         "## Section C\n\n- wd one\n- wd two\n")


def sess(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": creds[0], "password": creds[1]}, timeout=60)
    r.raise_for_status()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


def _upload(s, md):
    return s.post(f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
                  files={"file": ("d.md", io.BytesIO(md.encode()), "text/markdown")}, timeout=120)


def seed():
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    for ext in (".md", ".docx"):
        p = LEGAL_DIR / f"{SLUG}{ext}"
        if p.exists():
            (SNAP_DIR / p.name).write_bytes(p.read_bytes())
    a = sess(ADMIN)
    c = sess(COUNSEL)
    a.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
           json={"reason": "TEST_iter51fe pre-clean"}, timeout=60)
    made = []
    for md in (REL_A, REL_B):
        print("upload", _upload(c, md).status_code)
        r = a.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                   json={"notes": "TEST_iter51fe release"}, timeout=180)
        print("release", r.status_code, r.json().get("version") if r.ok else r.text[:200])
        made.append(r.json().get("version"))
    # open WD for the diff/comment tests
    print("wd upload", _upload(c, WD_MD).status_code)
    cm = c.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments",
                json={"body": "TEST_iter51fe Hey @admin and @counsel please review",
                      "line_number": 3, "side": "working"}, timeout=60)
    print("comment", cm.status_code, cm.json().get("mentions"))
    t = a.get(f"{BASE_URL}/api/legal/history-timeline/{SLUG}", params={"limit": 10}, timeout=60)
    print("versions", json.dumps([v["version"] for v in t.json()["versions"]]))
    print("comment_id", cm.json().get("id"))


def teardown():
    a = sess(ADMIN)
    a.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
           json={"reason": "TEST_iter51fe cleanup"}, timeout=60)
    cl = MongoClient(MONGO_URL)
    db = cl[DB_NAME]
    ids = [w["id"] for w in db.legal_doc_working_drafts.find({"source_slug": SLUG}, {"id": 1})]
    print("comments removed",
          db.legal_working_draft_comments.delete_many(
              {"working_draft_id": {"$in": ids}}).deleted_count)
    print("comments removed (slug)",
          db.legal_working_draft_comments.delete_many({"source_slug": SLUG}).deleted_count)
    print("wds removed",
          db.legal_doc_working_drafts.delete_many({"source_slug": SLUG}).deleted_count)
    print("ratifications removed",
          db.legal_doc_ratifications.delete_many(
              {"source_slug": SLUG,
               "$or": [{"notes": {"$regex": "TEST_iter51"}},
                       {"content_md_snapshot": {"$regex": "TEST_iter51"}}]}).deleted_count)
    print("mention emails removed",
          db.email_log.delete_many({"subject": {"$regex": "You were mentioned in a"}}).deleted_count,
          db.outbound_emails.delete_many(
              {"subject": {"$regex": "You were mentioned in a"}}).deleted_count)
    print("leftover ratifications", db.legal_doc_ratifications.count_documents({"source_slug": SLUG}))
    cl.close()
    for ext in (".md", ".docx"):
        snap = SNAP_DIR / f"{SLUG}{ext}"
        if snap.exists():
            (LEGAL_DIR / snap.name).write_bytes(snap.read_bytes())
            print("restored", snap.name)


if __name__ == "__main__":
    {"seed": seed, "teardown": teardown}[sys.argv[1]]()
