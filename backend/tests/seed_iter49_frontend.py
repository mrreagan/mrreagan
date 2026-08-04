"""Seed / cleanup helper for iteration 49 frontend history-timeline testing.

Usage:
  python seed_iter49_frontend.py seed     # create 7 releases for 03-cookie-notice
  python seed_iter49_frontend.py cleanup  # delete created rows, restore .md, rebuild
"""
import io
import os
import shutil
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
backend_env = dotenv_values("/app/backend/.env")
db = MongoClient(os.environ.get("MONGO_URL") or backend_env["MONGO_URL"])[
    os.environ.get("DB_NAME") or backend_env["DB_NAME"]]

SLUG = "03-cookie-notice"
DOC_PATH = Path("/app/backend/legal_docs") / f"{SLUG}.md"
BACKUP_PATH = Path("/tmp/iter49/03-cookie-notice.md.bak")
IDS_FILE = Path("/tmp/iter49/seeded_ids.txt")

COUNSEL = ("counsel@birthright.live", "counsel-review-2026")
ADMIN = ("admin@birthright.live", "birthright2026")


def sess(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": creds[0], "password": creds[1]}, timeout=60)
    r.raise_for_status()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


def seed(n=7):
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP_PATH.exists():
        shutil.copy(DOC_PATH, BACKUP_PATH)
    pre_r = [r["id"] for r in db.legal_doc_ratifications.find({"source_slug": SLUG}, {"id": 1})]
    pre_w = [w["id"] for w in db.legal_doc_working_drafts.find({"source_slug": SLUG}, {"id": 1})]
    IDS_FILE.write_text("\n".join(["R:" + i for i in pre_r] + ["W:" + i for i in pre_w]))
    c, a = sess(COUNSEL), sess(ADMIN)
    for i in range(1, n + 1):
        body = (f"# Cookie Notice (TEST_iter49 v{i})\n\nTEST_iter49 marker BODY-{i}\n\n"
                f"## Section {i}\n\n- one\n- two\n")
        for k, extra in enumerate(("", f"\n- edit {i}\n")):
            r = c.post(f"{BASE_URL}/api/legal/docs/{SLUG}/upload",
                       files={"file": (f"iter49-{i}-{k}.md",
                                       io.BytesIO((body + extra).encode()), "text/markdown")},
                       timeout=120)
            r.raise_for_status()
        rel = a.post(f"{BASE_URL}/api/legal/working-drafts/{SLUG}/release",
                     json={"notes": f"TEST_iter49 seeded release pass {i}"}, timeout=180)
        rel.raise_for_status()
        print("released", rel.json()["released_as_version"])
    print("total ratifications:",
          db.legal_doc_ratifications.count_documents({"source_slug": SLUG}))


def cleanup():
    keep_r, keep_w = [], []
    if IDS_FILE.exists():
        for line in IDS_FILE.read_text().splitlines():
            if line.startswith("R:"):
                keep_r.append(line[2:])
            elif line.startswith("W:"):
                keep_w.append(line[2:])
    print("deleted rats:", db.legal_doc_ratifications.delete_many(
        {"source_slug": SLUG, "id": {"$nin": keep_r}}).deleted_count)
    print("deleted wds:", db.legal_doc_working_drafts.delete_many(
        {"source_slug": SLUG, "id": {"$nin": keep_w}}).deleted_count)
    if BACKUP_PATH.exists():
        shutil.copy(BACKUP_PATH, DOC_PATH)
    a = sess(ADMIN)
    print("rebuild:", a.post(f"{BASE_URL}/api/legal/rebuild-docx", timeout=180).status_code)
    print("remaining rats:",
          db.legal_doc_ratifications.count_documents({"source_slug": SLUG}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    seed(int(sys.argv[2]) if len(sys.argv) > 2 else 7) if cmd == "seed" else cleanup()
