"""Seed an open working draft for frontend diff-modal verification (iter 53)."""
import os
import requests
from dotenv import dotenv_values

BASE = (os.environ.get("REACT_APP_BACKEND_URL")
        or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
SLUG = "03-cookie-notice"

WORKING_MD = (
    "# Cookie & Tracking Notice (TEST_iter53)\n\n"
    "**Effective date:** 2026-07-01\n\n"
    "We use cookies for essential site functionality ONLY.\n\n"
    "## 1. What we set\n\n- session cookie\n- csrf token\n\n"
    "## 2. Your choices\n\nYou may clear cookies at any time.\n"
)


def token(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw}, timeout=60)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


t = token("admin@birthright.live", "birthright2026")
h = {"Authorization": f"Bearer {t}"}
files = {"file": (f"{SLUG}.md", WORKING_MD.encode(), "text/markdown")}
r = requests.post(f"{BASE}/api/legal/docs/{SLUG}/upload", headers=h, files=files, timeout=90)
print("upload:", r.status_code, r.text[:200])

g = requests.get(f"{BASE}/api/legal/working-drafts/{SLUG}", headers=h, timeout=60)
print("get:", g.status_code)
d = g.json()
print("released_md head:", repr((d.get("released_md") or "")[:90]))
print("content_md head:", repr((d.get("content_md") or "")[:90]))
print("is_stale:", d.get("is_stale"))

ct = token("counsel@birthright.live", "counsel-review-2026")
cg = requests.get(f"{BASE}/api/legal/working-drafts/{SLUG}",
                  headers={"Authorization": f"Bearer {ct}"}, timeout=60)
print("counsel status:", cg.status_code)
