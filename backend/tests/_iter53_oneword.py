"""iter53: realistic one-word-edit scenario — the exact user complaint.

Working draft = released body (stripped) with ONE word changed.
Expected: diff should be ~1 added / ~1 removed, NOT +135/-45.
"""
import difflib
import os
import sys

import requests
from dotenv import dotenv_values

if "/app/backend" not in sys.path:
    sys.path.insert(0, "/app/backend")

BASE = (os.environ.get("REACT_APP_BACKEND_URL")
        or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
SLUG = "03-cookie-notice"

from routers.legal import LEGAL_DOC_DIR, _strip_draft_disclaimer  # noqa: E402


def token(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw}, timeout=60)
    r.raise_for_status()
    d = r.json()
    return d.get("access_token") or d.get("token")


h = {"Authorization": f"Bearer {token('admin@birthright.live', 'birthright2026')}"}

raw = (LEGAL_DOC_DIR / f"{SLUG}.md").read_text(encoding="utf-8")
stripped, had = _strip_draft_disclaimer(raw)
print("released raw lines:", len(raw.splitlines()), "| stripped lines:", len(stripped.splitlines()),
      "| had_disclaimer:", had)

# one-word edit: change "Categories" -> "Kinds"
assert "Categories" in stripped
working = stripped.replace("Categories", "Kinds", 1)
assert working != stripped

files = {"file": (f"{SLUG}.md", working.encode(), "text/markdown")}
r = requests.post(f"{BASE}/api/legal/docs/{SLUG}/upload", headers=h, files=files, timeout=90)
print("upload:", r.status_code)

g = requests.get(f"{BASE}/api/legal/working-drafts/{SLUG}", headers=h, timeout=60)
d = g.json()
rel = (d["released_md"] or "").splitlines()
wrk = (d["content_md"] or "").splitlines()
diff = list(difflib.unified_diff(rel, wrk, lineterm=""))
added = [l for l in diff if l.startswith("+") and not l.startswith("+++")]
removed = [l for l in diff if l.startswith("-") and not l.startswith("---")]
print(f"ONE-WORD-EDIT DIFF: +{len(added)} / -{len(removed)}")
print("added:", added)
print("removed:", removed)
print("is_stale:", d["is_stale"])
print("disclaimer in diff?", any("PENDING COUNSEL RATIFICATION" in l for l in added + removed))
print("lowercase footer in diff?", any("pending counsel ratification" in l.lower() for l in added + removed))
