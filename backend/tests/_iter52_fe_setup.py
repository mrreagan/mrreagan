"""Helper: create/teardown a working draft + @mention comment for iter52 frontend test."""
import io
import os
import sys

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

BASE_URL = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
be = dotenv_values("/app/backend/.env")
SLUG = "03-cookie-notice"
MD = "# Cookie Notice (TEST_iter52 FE)\n\nTEST_iter52 fe line one\n\n## Section FE\n\n- alpha\n- beta\n"


def sess(email, pwd):
    t = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=60).json()["token"]
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {t}"})
    return s


def setup():
    counsel = sess("counsel@birthright.live", "counsel-review-2026")
    admin = sess("admin@birthright.live", "birthright2026")
    admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard", json={"reason": "TEST_iter52 fe pre"}, timeout=60)
    r = counsel.post(f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
                     files={"file": ("d.md", io.BytesIO(MD.encode()), "text/markdown")}, timeout=120)
    print("upload", r.status_code)
    c = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments",
                     json={"body": "TEST_iter52 Hi @admin please check this line", "line_number": 3, "side": "working"},
                     timeout=60)
    print("comment", c.status_code, c.json().get("id"), c.json().get("mentions"))
    g = counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/comments",
                     json={"body": "TEST_iter52 general note for @counsel", "side": "general"}, timeout=60)
    print("general comment", g.status_code, g.json().get("id"))


def teardown():
    admin = sess("admin@birthright.live", "birthright2026")
    admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard", json={"reason": "TEST_iter52 fe cleanup"}, timeout=60)
    db = MongoClient(be["MONGO_URL"])[be["DB_NAME"]]
    wd_ids = [w["id"] for w in db.legal_doc_working_drafts.find({"source_slug": SLUG}, {"id": 1})]
    print("comments deleted", db.legal_working_draft_comments.delete_many({"$or": [{"working_draft_id": {"$in": wd_ids}}, {"source_slug": SLUG}]}).deleted_count)
    print("wds deleted", db.legal_doc_working_drafts.delete_many({"source_slug": SLUG}).deleted_count)
    print("ratif deleted", db.legal_doc_ratifications.delete_many({"source_slug": SLUG}).deleted_count)
    print("digest emails deleted", db.email_log.delete_many({"template": "legal_mention_digest"}).deleted_count)


if __name__ == "__main__":
    (setup if sys.argv[1] == "setup" else teardown)()
