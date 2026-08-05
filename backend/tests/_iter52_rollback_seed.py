"""Seed one released ratification on 03-cookie-notice so the History/Rollback
preview modal can be exercised, then fully restore state."""
import io
import shutil
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

BASE_URL = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
be = dotenv_values("/app/backend/.env")
SLUG = "03-cookie-notice"
DOCS = Path("/app/backend/legal_docs")
SNAP = Path("/tmp/iter52_snap")
MD = "# Cookie Notice (TEST_iter52 RELEASE)\n\nTEST_iter52 release line\n\n## Section R\n\n- gamma\n"


def sess(email, pwd):
    t = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=60).json()["token"]
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {t}"})
    return s


def setup():
    SNAP.mkdir(exist_ok=True)
    for ext in (".md", ".docx"):
        p = DOCS / f"{SLUG}{ext}"
        if p.exists():
            shutil.copy2(p, SNAP / p.name)
    counsel = sess("counsel@birthright.live", "counsel-review-2026")
    admin = sess("admin@birthright.live", "birthright2026")
    admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard", json={"reason": "TEST_iter52 rb pre"}, timeout=60)
    print("upload", counsel.post(f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
          files={"file": ("d.md", io.BytesIO(MD.encode()), "text/markdown")}, timeout=120).status_code)
    print("mark-ready", counsel.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/mark-ready", json={}, timeout=60).status_code)
    r = admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                   json={"version": "TEST_iter52-rb", "notes": "TEST_iter52 rollback seed"}, timeout=120)
    print("release", r.status_code, str(r.json())[:200])
    # new WD on top so History + rollback preview is meaningful
    print("upload2", counsel.post(f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
          files={"file": ("d2.md", io.BytesIO((MD + "\n- delta\n").encode()), "text/markdown")}, timeout=120).status_code)


def teardown():
    admin = sess("admin@birthright.live", "birthright2026")
    admin.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/discard", json={"reason": "TEST_iter52 rb cleanup"}, timeout=60)
    db = MongoClient(be["MONGO_URL"])[be["DB_NAME"]]
    wd_ids = [w["id"] for w in db.legal_doc_working_drafts.find({"source_slug": SLUG}, {"id": 1})]
    print("comments", db.legal_working_draft_comments.delete_many({"$or": [{"working_draft_id": {"$in": wd_ids}}, {"source_slug": SLUG}]}).deleted_count)
    print("wds", db.legal_doc_working_drafts.delete_many({"source_slug": SLUG}).deleted_count)
    print("ratifs", db.legal_doc_ratifications.delete_many({"source_slug": SLUG}).deleted_count)
    print("digest emails", db.email_log.delete_many({"template": "legal_mention_digest"}).deleted_count)
    print("release emails", db.email_log.delete_many({"subject": {"$regex": "TEST_iter52"}}).deleted_count)
    for f in SNAP.glob("*"):
        shutil.copy2(f, DOCS / f.name)
        print("restored", f.name)


if __name__ == "__main__":
    (setup if sys.argv[1] == "setup" else teardown)()
