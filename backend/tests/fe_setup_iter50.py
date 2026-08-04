"""Seed / teardown helper for iteration-50 frontend testing.

Usage:  python fe_setup_iter50.py seed
        python fe_setup_iter50.py teardown
"""
import io
import os
import sys

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


def sess(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": creds[0], "password": creds[1]}, timeout=60)
    r.raise_for_status()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


def seed():
    a = sess(ADMIN)
    c = sess(COUNSEL)
    a.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
           json={"reason": "TEST_iter50fe pre-clean"}, timeout=60)
    md = ("# Cookie Notice (TEST_iter50fe)\n\nTEST_iter50fe intro line\n\n"
          "## Section A\n\n- bullet one\n- bullet two\n- bullet three\n")
    r = c.post(f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
               files={"file": ("d.md", io.BytesIO(md.encode()), "text/markdown")}, timeout=120)
    print("upload", r.status_code)
    c1 = a.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments",
                json={"body": "TEST_iter50fe open admin question on line 3",
                      "line_number": 3, "side": "working"}, timeout=60).json()
    c2 = c.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments",
                json={"body": "TEST_iter50fe counsel note to be resolved",
                      "line_number": 5, "side": "working"}, timeout=60).json()
    a.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments/{c2['id']}/resolve",
           json={"resolved": True}, timeout=60)
    rows = a.get(f"{BASE_URL}/api/legal/working-drafts", timeout=60).json()
    row = [x for x in rows if x["source_slug"] == SLUG][0]
    print("comment ids", c1["id"], c2["id"])
    print("stats", row["comment_stats"])


def teardown():
    a = sess(ADMIN)
    a.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard",
           json={"reason": "TEST_iter50fe cleanup"}, timeout=60)
    cl = MongoClient(MONGO_URL)
    db = cl[DB_NAME]
    ids = [w["id"] for w in db.legal_doc_working_drafts.find({"source_slug": SLUG}, {"id": 1})]
    print("comments removed",
          db.legal_working_draft_comments.delete_many({"working_draft_id": {"$in": ids}}).deleted_count)
    print("wds removed",
          db.legal_doc_working_drafts.delete_many(
              {"source_slug": SLUG, "content_md": {"$regex": "TEST_iter50"}}).deleted_count)
    print("leftover comments for slug",
          db.legal_working_draft_comments.count_documents({"source_slug": SLUG}))
    cl.close()


if __name__ == "__main__":
    {"seed": seed, "teardown": teardown}[sys.argv[1]]()
