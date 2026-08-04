"""Seed working drafts for iteration-48 frontend diff-modal testing.

Usage: python seed_iter48_frontend.py seed | clean
"""
import io
import os
import sys

import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or frontend_env["REACT_APP_BACKEND_URL"]).rstrip("/")
COUNSEL = ("counsel@birthright.live", "counsel-review-2026")
ADMIN = ("admin@birthright.live", "birthright2026")
SLUG = "03-cookie-notice"
SLUG_IDENTICAL = "10-sliding-scale-scholarship-terms"


def sess(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=60)
    r.raise_for_status()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


def upload(s, slug, text):
    return s.post(f"{BASE_URL}/api/legal/docs/{slug}/upload",
                  files={"file": ("draft.md", io.BytesIO(text.encode()), "text/markdown")},
                  timeout=120)


def seed():
    c = sess(*COUNSEL)
    released = requests.get(f"{BASE_URL}/api/legal/pages/cookie-notice", timeout=60)
    body = (
        "# Cookie & Tracking Notice (TEST_iter48 EDIT)\n\n"
        "TEST_iter48 added paragraph one.\n\n"
        "## What we track\n\n- session cookie\n- analytics cookie (TEST_iter48)\n"
    )
    print("cookie upload:", upload(c, SLUG, body).status_code, released.status_code)
    # identical-content working draft for the other slug
    a = sess(*ADMIN)
    rel = requests.get(f"{BASE_URL}/api/legal/drafts/{SLUG_IDENTICAL}", timeout=60)
    print("released fetch:", rel.status_code)
    # use the working-draft GET after a throwaway upload to grab released_md
    print("tmp upload:", upload(c, SLUG_IDENTICAL, "# tmp\n").status_code)
    wd = c.get(f"{BASE_URL}/api/legal/working-drafts/{SLUG_IDENTICAL}", timeout=60).json()
    print("identical upload:", upload(c, SLUG_IDENTICAL, wd["released_md"]).status_code)


def clean():
    a = sess(*ADMIN)
    for slug in (SLUG, SLUG_IDENTICAL):
        r = a.post(f"{BASE_URL}/api/legal/working-drafts/{slug}/discard",
                   json={"reason": "TEST_iter48 frontend cleanup"}, timeout=60)
        print("discard", slug, r.status_code)


if __name__ == "__main__":
    (seed if (len(sys.argv) > 1 and sys.argv[1] == "seed") else clean)()
