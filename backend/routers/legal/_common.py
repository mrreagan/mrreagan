"""routers.legal._common — shared helpers, constants, and models used by
the public, working_drafts, and comments sub-routers.

This module has no @router routes — it only holds state and helpers.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from models import gen_id, now_iso
from utils.audit import log_action  # noqa: F401  (re-exported / used by helpers below)

logger = logging.getLogger("birthright.legal")


# ---- LEGAL_DOC_DIR (was L28-L28) ----
LEGAL_DOC_DIR = Path(__file__).resolve().parent.parent.parent / "legal_docs"

# ---- _build_index (was L31-L69) ----
def _build_index():
    """Assemble the download index — the counsel briefing + every generated
    draft `.docx` in /app/backend/legal_docs/. .docx is the standard output
    format for this project."""
    idx = {
        "counsel-briefing-docx": {
            "filename": "LEGAL_BRIEFING_FOR_COUNSEL.docx",
            "display_name": "Legal Briefing for Counsel (birthright.live).docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "category": "Briefing",
            "source_slug": None,   # not in the working-draft manifest
        },
        "counsel-briefing-md": {
            "filename": "LEGAL_BRIEFING_FOR_COUNSEL.md",
            "display_name": "Legal Briefing for Counsel (source).md",
            "content_type": "text/markdown; charset=utf-8",
            "category": "Briefing",
            "source_slug": None,
        },
    }
    # Auto-discover drafts by manifest slug — .docx preferred, .md fallback.
    try:
        import sys
        sys.path.insert(0, str(LEGAL_DOC_DIR))
        from _manifest import DRAFT_LEGAL_DOCS  # type: ignore
    except Exception:
        DRAFT_LEGAL_DOCS = []
    for d in DRAFT_LEGAL_DOCS:
        slug = d["slug"]
        docx_file = f"{slug}.docx"
        if (LEGAL_DOC_DIR / docx_file).exists():
            idx[f"draft-{slug}"] = {
                "filename": docx_file,
                "display_name": f"{d['display_name']}.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "category": d.get("category", "Draft"),
                "source_slug": slug,   # for /working-drafts endpoints
            }
    return idx

# ---- LEGAL_DOC_INDEX (was L72-L72) ----
LEGAL_DOC_INDEX = _build_index()

# ---- DEFAULT_INDEMNIFICATION_BODY (was L75-L88) ----
DEFAULT_INDEMNIFICATION_BODY = """# Universal Indemnification & Hold-Harmless Agreement

**Placeholder text — not legal advice.** Birthright Foundation will replace this with counsel-reviewed copy before launch.

By accepting this agreement, you acknowledge that:

1. **Voluntary participation.** Workshops, materials, and partner services are educational in nature. You participate at your own discretion.
2. **No professional advice.** Content is not a substitute for licensed mental-health, medical, or legal advice.
3. **Hold harmless.** You agree not to hold Birthright Foundation, its governing board, facilitators, vendors, or community partners liable for outcomes arising from your participation, except in cases of gross negligence.
4. **Respectful conduct.** You agree to abide by the community standards and to engage facilitators, fellow participants, and partners with respect.
5. **Data & privacy.** Personal information you provide is governed by the Birthright privacy policy.

This agreement is versioned. If we substantively change it, you will be asked to review and sign the new version before further participation in workshops or partner programs.
"""

# ---- _notify_partners_of_new_version (was L204-L276) ----
async def _notify_partners_of_new_version(version: dict) -> None:
    """Email every active partner that a new agreement version is live.

    Looks up users via the partner_profiles collection (active +
    non-sample) and de-duplicates by user_id so a partner with multiple
    roles only gets one email. Failures per-recipient are logged and
    swallowed.
    """
    from database import db
    from utils.mailer import send_email
    import os
    app_url = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
    review_url = f"{app_url}/legal/agreement" if app_url else "/legal/agreement"

    # Collect unique user_ids with at least one active non-sample profile.
    seen_user_ids: set[str] = set()
    async for prof in db.partner_profiles.find(
        {
            "status": "active",
            "$or": [{"is_sample": {"$exists": False}}, {"is_sample": False}],
        },
        {"_id": 0, "user_id": 1},
    ).limit(2000):
        if prof.get("user_id"):
            seen_user_ids.add(prof["user_id"])
    if not seen_user_ids:
        logger.info("Agreement v%s published — no active partners to notify.", version["version"])
        return

    users_to_email: list[dict] = []
    async for u in db.users.find(
        {"id": {"$in": list(seen_user_ids)}},
        {"_id": 0, "id": 1, "email": 1, "first_name": 1},
    ).limit(500):
        if u.get("email"):
            users_to_email.append(u)

    summary = (version.get("summary_of_changes") or "").strip() or "Substantive update to the partner agreement."
    subject = f"Action required: Birthright Agreement v{version['version']}"
    sent = 0
    for u in users_to_email:
        try:
            await send_email(
                to=u["email"],
                subject=subject,
                html=(
                    f"<p>Hi {u.get('first_name','there')},</p>"
                    f"<p>We've published <strong>Agreement v{version['version']}</strong>. "
                    f"Continued access to partner write-side features (publishing products, "
                    f"artifacts, featured slots, AI Studio drafts, subscription changes) "
                    f"requires your acceptance of the new version. Browsing and earnings "
                    f"reads are not affected.</p>"
                    f"<p><strong>What changed</strong><br>{summary}</p>"
                    f"<p><a href='{review_url}' style='display:inline-block;padding:10px 18px;"
                    f"background:#476B6B;color:#FAF8F5;text-decoration:none;border-radius:6px'>"
                    f"Review &amp; accept v{version['version']}</a></p>"
                    f"<p>The in-product banner will also prompt you next time you sign in.</p>"
                    f"<p>— Birthright Foundation</p>"
                ),
                text=(
                    f"Hi {u.get('first_name','there')},\n\n"
                    f"Birthright Agreement v{version['version']} is now active. Accept it before "
                    f"publishing new partner content or changing your subscription.\n\n"
                    f"What changed: {summary}\n\n"
                    f"Review & accept: {review_url}\n\n— Birthright Foundation"
                ),
                template_name="agreement_resign",
                metadata={"version_id": version["id"], "version": version["version"]},
            )
            sent += 1
        except Exception as ex:
            logger.warning("Agreement v%s notify failed for %s: %s", version["version"], u.get("email"), ex)
    logger.info("Agreement v%s notify: %d/%d sent.", version["version"], sent, len(users_to_email))

# ---- PUBLIC_LEGAL_PAGES (was L540-L569) ----
PUBLIC_LEGAL_PAGES: dict[str, dict] = {
    "terms": {
        "source_slug": "01-terms-of-service",
        "title": "Terms of Service",
    },
    "privacy": {
        "source_slug": "02-privacy-policy",
        "title": "Privacy Policy",
    },
    "cookie-notice": {
        "source_slug": "03-cookie-notice",
        "title": "Cookie & Tracking Notice",
    },
    "refunds": {
        "source_slug": "15-refund-returns-policy",
        "title": "Refund & Returns Policy",
    },
    "scholarships": {
        "source_slug": "10-sliding-scale-scholarship-terms",
        "title": "Sliding-Scale & Scholarship Terms",
    },
    "community-standards": {
        "source_slug": "14-community-standards",
        "title": "Community Standards",
    },
    "indemnification": {
        "source_slug": "04-indemnification-hold-harmless",
        "title": "Universal Indemnification & Hold-Harmless Agreement",
    },
}

# ---- _MID_DOC_DRAFT_BOILERPLATE_RE (was L572-L590) ----
_MID_DOC_DRAFT_BOILERPLATE_RE = re.compile(
    # Matches the mid/footer draft-boilerplate block injected by
    # scripts/generate_legal_drafts_v2.py, e.g.:
    #
    #     ---
    #     *First draft — pending counsel ratification. Comments to
    #     legal@birthright.live.*
    #
    # Also swallows the leading `---` horizontal rule, an optional trailing
    # `---`, and any blank lines that would otherwise collapse into an
    # empty section. Case-insensitive on "First draft"; the em-dash and
    # asterisks are literal so we don't over-strip legitimate italic text.
    r"(?:^|\n)[ \t]*---[ \t]*\n"           # opening hr
    r"[ \t]*\*first draft[^*\n]*\n"        # `*First draft — pending counsel ratification. Comments to`
    r"[ \t]*[^*\n]*\*[ \t]*\n?"            # `legal@birthright.live.*`
    r"(?:[ \t]*\n)*"                       # blank lines
    r"(?:[ \t]*---[ \t]*\n?)?",            # optional closing hr (only if dangling)
    flags=re.IGNORECASE,
)

# ---- _strip_draft_disclaimer (was L593-L628) ----
def _strip_draft_disclaimer(md: str) -> tuple[str, bool]:
    """Peel off draft-only boilerplate so the diff viewer and rendered
    page don't see it as content:

    1. Leading `> ⚠️ AI-GENERATED FIRST DRAFT` blockquote (banner-style).
    2. Mid-document `*First draft — pending counsel ratification.
       Comments to legal@birthright.live.*` italic block (with its
       surrounding `---` rules).

    Both blocks are injected by the DOCX-rebuild / draft-generation
    pipeline and are IDENTICAL on the released side and the working
    draft side — but any tweak to the wording would otherwise produce
    huge false-positive diff hunks. Returns (cleaned_markdown,
    had_disclaimer). `had_disclaimer` reflects the leading blockquote
    only (backwards-compat with existing callers that use it to render
    the "not yet counsel-reviewed" banner).
    """
    lines = md.splitlines()
    had_leading = False
    if lines and lines[0].startswith(">"):
        i = 0
        while i < len(lines) and (lines[i].startswith(">") or lines[i].strip() == ""):
            # Stop when we hit content that isn't a blockquote and isn't blank
            if lines[i].strip() == "" and i + 1 < len(lines) and not lines[i + 1].startswith(">"):
                i += 1
                break
            i += 1
        md = "\n".join(lines[i:]).lstrip()
        had_leading = True

    # Symmetric strip of the mid-document boilerplate block. Safe even
    # when the block is missing (regex simply doesn't match).
    md = _MID_DOC_DRAFT_BOILERPLATE_RE.sub("\n", md)
    # Collapse any triple+ newlines the removal may have introduced.
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + ("\n" if md.endswith("\n") else "")
    return md, had_leading

# ---- _md_body_hash (was L703-L708) ----

import hashlib as _hashlib


def _md_body_hash(cleaned_md: str) -> str:
    return _hashlib.sha256(cleaned_md.encode("utf-8")).hexdigest()[:16]

# ---- _current_ratification (was L711-L715) ----
async def _current_ratification(source_slug: str) -> Optional[dict]:
    from database import db
    return await db.legal_doc_ratifications.find_one(
        {"source_slug": source_slug}, {"_id": 0}, sort=[("ratified_at", -1)]
    )

# ---- _docx_to_markdown (was L886-L947) ----
def _docx_to_markdown(blob: bytes) -> str:
    """Best-effort .docx → Markdown conversion for full-notice uploads.

    We only need enough fidelity to keep counsel's structure round-trippable:
    heading levels, paragraphs, list items, and inline emphasis. Anything
    fancier (tables, footnotes, images) is dropped with a comment marker so
    the admin knows to inspect the source before ratifying.
    """
    from io import BytesIO
    from docx import Document

    doc = Document(BytesIO(blob))
    out: list[str] = []
    dropped: list[str] = []

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        style = (para.style.name if para.style else "") or ""

        if not text:
            out.append("")
            continue

        # Heading detection: "Heading 1".."Heading 6" (Word default) or "Title".
        heading_level = 0
        if style.lower().startswith("heading "):
            try:
                heading_level = int(style.split()[-1])
            except ValueError:
                heading_level = 0
        elif style.lower() == "title":
            heading_level = 1

        if heading_level >= 1:
            out.append(f"{'#' * min(heading_level, 6)} {text}")
            continue

        # List detection: Word marks numbered/bulleted lists via numId in
        # paragraph properties. Best-effort: fall back to plain paragraph.
        try:
            numpr = para._p.pPr.numPr if (para._p.pPr is not None) else None
        except Exception:
            numpr = None
        if numpr is not None:
            out.append(f"- {text}")
            continue

        out.append(text)

    # Flag unhandled content (tables, images) so admin knows to check.
    if doc.tables:
        dropped.append(f"{len(doc.tables)} table(s)")
    if doc.inline_shapes:
        dropped.append(f"{len(doc.inline_shapes)} inline image(s)")

    md = "\n\n".join(line for line in out).replace("\n\n\n\n", "\n\n").strip() + "\n"
    if dropped:
        md += (
            f"\n<!-- Uploaded .docx contained: {', '.join(dropped)}. "
            "These were not converted; please review the original file. -->\n"
        )
    return md

# ---- _WD_STATE_DRAFT (was L958-L961) ----
_WD_STATE_DRAFT = "draft"
_WD_STATE_READY = "awaiting_admin"
_WD_STATE_RELEASED = "released"
_WD_STATE_DISCARDED = "discarded"

# ---- _released_md (was L964-L968) ----
def _released_md(source_slug: str) -> str:
    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")
    return fp.read_text(encoding="utf-8")

# ---- _active_working_draft (was L971-L979) ----
async def _active_working_draft(source_slug: str) -> Optional[dict]:
    """Return the current OPEN working draft for this slug (state ∈
    {draft, awaiting_admin}), or None."""
    from database import db
    return await db.legal_doc_working_drafts.find_one(
        {"source_slug": source_slug,
         "state": {"$in": [_WD_STATE_DRAFT, _WD_STATE_READY]}},
        {"_id": 0},
    )

# ---- _upsert_working_draft (was L982-L1052) ----
async def _upsert_working_draft(
    source_slug: str,
    content_md: str,
    user: dict,
    action: str,
    note: str = "",
) -> dict:
    """Create or update the open working draft for this slug.

    Every write appends to `change_log` so we have an audit trail of who
    touched what. If a working draft was previously marked
    `awaiting_admin`, a new edit knocks it back to `draft` so admin can't
    accidentally release stale content.
    """
    from database import db

    now = now_iso()
    cleaned, _ = _strip_draft_disclaimer(content_md)
    body_hash = _md_body_hash(cleaned)
    entry = {
        "at": now,
        "by_user_id": user["id"],
        "by_email": user.get("email"),
        "by_role": user.get("role"),
        "action": action,
        "note": note,
        "bytes": len(content_md.encode("utf-8")),
    }

    existing = await _active_working_draft(source_slug)
    if existing:
        change_log = list(existing.get("change_log") or [])
        change_log.append(entry)
        updates = {
            "content_md": content_md,
            "body_hash": body_hash,
            "last_edited_at": now,
            "last_edited_by_user_id": user["id"],
            "last_edited_by_email": user.get("email"),
            "last_edited_by_role": user.get("role"),
            "state": _WD_STATE_DRAFT,   # editing knocks it back from awaiting_admin
            "change_log": change_log,
        }
        await db.legal_doc_working_drafts.update_one(
            {"id": existing["id"]}, {"$set": updates},
        )
        return {**existing, **updates}

    # No open draft — create fresh. Snapshot the released body_hash so we
    # can detect if the underlying .md changed while the draft was open.
    released_hash = _md_body_hash(_strip_draft_disclaimer(_released_md(source_slug))[0])
    doc = {
        "id": gen_id(),
        "source_slug": source_slug,
        "content_md": content_md,
        "body_hash": body_hash,
        "base_released_hash": released_hash,
        "state": _WD_STATE_DRAFT,
        "created_at": now,
        "created_by_user_id": user["id"],
        "created_by_email": user.get("email"),
        "created_by_role": user.get("role"),
        "last_edited_at": now,
        "last_edited_by_user_id": user["id"],
        "last_edited_by_email": user.get("email"),
        "last_edited_by_role": user.get("role"),
        "change_log": [entry],
    }
    await db.legal_doc_working_drafts.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc

# ---- _bump_minor (was L1055-L1066) ----
def _bump_minor(version: str) -> str:
    """1.2 → 1.3 · 2 → 2.1 · '' → 1.0 · unparseable → append .1"""
    if not version:
        return "1.0"
    parts = str(version).split(".")
    try:
        if len(parts) == 1:
            return f"{int(parts[0])}.1"
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    except ValueError:
        return f"{version}.1"

# ---- _next_version (was L1069-L1075) ----
async def _next_version(source_slug: str) -> str:
    from database import db
    latest = await db.legal_doc_ratifications.find_one(
        {"source_slug": source_slug}, {"_id": 0, "version": 1},
        sort=[("ratified_at", -1)],
    )
    return _bump_minor(latest.get("version", "") if latest else "")

# ---- _email_working_draft_ready (was L1251-L1310) ----
async def _email_working_draft_ready(
    source_slug: str,
    wd: dict,
    marker: dict,
) -> Optional[str]:
    """Email every admin user that a working draft is ready to release.

    Uses the shared dry-run-safe mailer (no-op if SENDER_EMAIL / Resend
    aren't configured). Never raises — a failed send returns None and
    logs a warning.
    """
    from database import db
    from utils.mailer import send_email

    _, title = _SOURCE_TO_PUBLIC.get(source_slug, (source_slug, source_slug.replace("-", " ").title()))
    recipients: list[str] = []
    async for u in db.users.find({"role": "admin"}, {"_id": 0, "email": 1}):
        if u.get("email") and u["email"] not in recipients:
            recipients.append(u["email"])
    if not recipients:
        return None

    site_url = os.environ.get("PUBLIC_SITE_URL", "").rstrip("/")
    changes = len(wd.get("change_log") or [])
    subject = f"Working draft ready · {title} · from {marker.get('email', 'counsel')}"
    html = f"""
    <div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;color:#1A2424">
      <h2 style="font-family:'Cormorant Garamond',serif;color:#0F2424">Working draft ready for release</h2>
      <p><strong>Document:</strong> {title}</p>
      <p><strong>Marked ready by:</strong> {marker.get('email', 'counsel')} ({marker.get('role')}) · {now_iso()}</p>
      <p><strong>Working draft id:</strong> <code>{wd.get('id', '')}</code></p>
      <p><strong>Edits accumulated:</strong> {changes}</p>
      <p style="color:#5C6B6B;font-size:14px">
        Review the diff and release (or discard) at
        <a href="{site_url}/counsel" style="color:#476B6B"><strong>{site_url or '/counsel'}/counsel</strong></a>.
      </p>
      <p style="color:#5C6B6B;font-size:12px">
        Nothing on the public site changes until an admin clicks Release.
      </p>
    </div>
    """
    text = (
        f"Working draft ready for release · {title}\n"
        f"Marked ready by: {marker.get('email', 'counsel')} ({marker.get('role')}) at {now_iso()}\n"
        f"Working draft id: {wd.get('id', '')}\n"
        f"Edits accumulated: {changes}\n\n"
        f"Review at: {site_url}/counsel\n"
    )
    try:
        return await send_email(
            to=recipients,
            subject=subject,
            html=html,
            text=text,
            template_name="legal_working_draft_ready",
            metadata={"source_slug": source_slug, "working_draft_id": wd.get("id")},
        )
    except Exception as exc:
        logger.warning("legal.working.ready.email: %s", exc)
        return None

# ---- _MENTION_RX_and_helpers (was L1569-L1582) ----
_MENTION_RX = re.compile(r"(?<![\w.])@(admin|counsel)\b", re.IGNORECASE)

def _parse_mentions(body: str) -> list[str]:
    """Return the deduped list of @roles present in the comment body.

    Only `@admin` and `@counsel` are recognised. Case-insensitive.
    Returns the roles lowercased.
    """
    found: list[str] = []
    for m in _MENTION_RX.finditer(body or ""):
        role = m.group(1).lower()
        if role not in found:
            found.append(role)
    return found

# ---- _send_legal_mention_digests (was L1585-L1739) ----
async def _send_legal_mention_digests() -> dict:
    """Daily digest job — one email per role summarising every unresolved
    @mention that hasn't been notified yet.

    Groups pending mentions by target role. Sends at most 2 emails total
    (one to `role=admin`, one to `role=readonly_admin`), each listing the
    matched comments with doc title, anchor, author, and body preview.
    Marks each included comment `mention_digest_sent_at=now` so the next
    run doesn't repeat them.

    Returns a small stats dict for logging/manual-trigger UI.
    """
    from database import db
    from utils.mailer import send_email

    # Pull unresolved comments with mentions that haven't been notified
    # for EVERY role they mention. `mention_digest_sent_roles` is the
    # set of roles already digested for this comment; the daily job
    # excludes a comment only when every mentioned role has already been
    # notified. Legacy comments with `mention_digest_sent_at != None`
    # (from the pre-per-role model) are treated as fully notified.
    pending_cursor = db.legal_working_draft_comments.find({
        "resolved": False,
        "mentions": {"$ne": []},
        "mention_digest_sent_at": None,
    }, {"_id": 0}).sort("created_at", 1)
    pending = await pending_cursor.to_list(500)
    hit_cap = len(pending) == 500
    if hit_cap:
        logger.warning("legal_mention_digest: hit 500-comment cap; extras will be handled next run")
    if not pending:
        return {"pending": 0, "sent": 0, "recipients": 0}

    # Filter down to comments whose WD is still open.
    open_wd_ids = set()
    async for wd in db.legal_doc_working_drafts.find(
        {"state": {"$in": [_WD_STATE_DRAFT, _WD_STATE_READY]}},
        {"_id": 0, "id": 1},
    ):
        open_wd_ids.add(wd["id"])
    pending = [c for c in pending if c.get("working_draft_id") in open_wd_ids]
    if not pending:
        return {"pending": 0, "sent": 0, "recipients": 0}

    # Partition by target role.
    per_role: dict[str, list[dict]] = {"admin": [], "counsel": []}
    for c in pending:
        for m in (c.get("mentions") or []):
            if m in per_role:
                per_role[m].append(c)

    # Look up users per role.
    role_to_recipients: dict[str, list[str]] = {}
    for role, mapped_role in (("admin", "admin"), ("counsel", "readonly_admin")):
        if not per_role[role]:
            continue
        emails: list[str] = []
        async for u in db.users.find({"role": mapped_role}, {"_id": 0, "email": 1}):
            em = u.get("email")
            if em and em not in emails:
                emails.append(em)
        if emails:
            role_to_recipients[role] = emails

    if not role_to_recipients:
        return {"pending": len(pending), "sent": 0, "recipients": 0}

    site_url = os.environ.get("PUBLIC_SITE_URL", "").rstrip("/") or ""
    sent_count = 0
    # Track (comment_id → set of roles successfully notified this run) so
    # a partial-failure across roles doesn't silently drop the still-pending
    # role.
    role_success_by_comment: dict[str, set[str]] = {}

    for role, recipients in role_to_recipients.items():
        comments = per_role[role]
        # Compose an HTML digest with a list per comment.
        rows_html = []
        for c in comments:
            _, title = _SOURCE_TO_PUBLIC.get(
                c.get("source_slug"),
                (c.get("source_slug"), (c.get("source_slug") or "").replace("-", " ").title()),
            )
            anchor = f"line {c.get('line_number')}" if c.get("line_number") else "general note"
            body_esc = (c.get("body") or "").replace("<", "&lt;").replace(">", "&gt;")
            author = c.get("author_email") or "someone"
            rows_html.append(f"""
              <div style="border-left:3px solid #C9A961;margin:12px 0;padding:8px 12px;background:#FAF7F0">
                <p style="margin:0;color:#0F2424"><strong>{title}</strong> · <em>{anchor}</em></p>
                <p style="margin:4px 0;color:#5C6B6B;font-size:12px">from {author} · {c.get('created_at','')}</p>
                <p style="margin:6px 0 0;color:#0F2424;white-space:pre-wrap">{body_esc}</p>
              </div>
            """)
        subject = f"Legal review digest · {len(comments)} unresolved @{role} mention{'s' if len(comments) != 1 else ''}"
        html = f"""
        <div style="font-family:Georgia,serif;max-width:640px;margin:0 auto;color:#1A2424">
          <h2 style="font-family:'Cormorant Garamond',serif;color:#0F2424">Legal review digest</h2>
          <p>You have <strong>{len(comments)}</strong> unresolved mention{'s' if len(comments) != 1 else ''} across the legal review workflow.</p>
          {''.join(rows_html)}
          <p style="color:#5C6B6B;font-size:14px">
            Reply, resolve, or reassign at
            <a href="{site_url}/counsel" style="color:#476B6B"><strong>{site_url or ''}/counsel</strong></a>.
          </p>
          <p style="color:#5C6B6B;font-size:12px">
            This is a once-daily digest. You won't get a fresh email for these mentions again — but any NEW @{role} mentions posted after this digest will appear tomorrow.
          </p>
        </div>
        """
        text = (
            f"Legal review digest — {len(comments)} unresolved @{role} mention(s)\n"
            + "\n\n".join(
                f"• {_SOURCE_TO_PUBLIC.get(c.get('source_slug'), (c.get('source_slug'), c.get('source_slug')))[1]}"
                f" · {'line ' + str(c.get('line_number')) if c.get('line_number') else 'general note'}\n"
                f"  from {c.get('author_email')} · {c.get('created_at')}\n"
                f"  {c.get('body','').strip()[:400]}"
                for c in comments
            )
            + f"\n\nOpen at {site_url}/counsel\n"
        )
        try:
            await send_email(
                to=recipients,
                subject=subject,
                html=html,
                text=text,
                template_name="legal_mention_digest",
                metadata={"role": role, "count": len(comments)},
            )
            sent_count += 1
            for c in comments:
                role_success_by_comment.setdefault(c["id"], set()).add(role)
        except Exception as exc:
            logger.warning("legal.mention.digest send failed for %s: %s", role, exc)

    # Only mark a comment fully-notified when every role it mentions has
    # been successfully sent. Others stay pending for the next run.
    now = now_iso()
    fully_notified: list[str] = []
    for c in pending:
        needed = set(c.get("mentions") or [])
        sent = role_success_by_comment.get(c["id"], set())
        if needed and needed.issubset(sent):
            fully_notified.append(c["id"])
    if fully_notified:
        await db.legal_working_draft_comments.update_many(
            {"id": {"$in": fully_notified}},
            {"$set": {"mention_digest_sent_at": now}},
        )
    return {
        "pending": len(pending),
        "sent": sent_count,
        "notified_comment_ids": fully_notified,
        "recipients_by_role": {r: len(v) for r, v in role_to_recipients.items()},
        "hit_cap": hit_cap,
    }

# ---- _summarise_wd_change_log (was L1835-L1863) ----
def _summarise_wd_change_log(change_log: list) -> dict:
    """Boil a working draft's change_log into a headline for release history.

    Returns something like:
      {
        "edits": 5,
        "authors": ["counsel@birthright.live"],
        "first_edit_at": "...",
        "last_edit_at": "...",
        "actions": {"upload_full": 2, "apply_roundtrip": 3},
      }
    """
    edits = [e for e in (change_log or []) if e.get("action") not in {"mark_ready", "release"}]
    authors: list[str] = []
    for e in edits:
        em = e.get("by_email")
        if em and em not in authors:
            authors.append(em)
    actions: dict[str, int] = {}
    for e in edits:
        a = e.get("action") or "unknown"
        actions[a] = actions.get(a, 0) + 1
    return {
        "edits": len(edits),
        "authors": authors,
        "first_edit_at": (edits[0].get("at") if edits else None),
        "last_edit_at": (edits[-1].get("at") if edits else None),
        "actions": actions,
    }

# ---- _SOURCE_TO_PUBLIC (was L2171-L2178) ----
_SOURCE_TO_PUBLIC = {
    "01-terms-of-service": ("terms", "Terms of Service"),
    "02-privacy-policy": ("privacy", "Privacy Policy"),
    "03-cookie-notice": ("cookie-notice", "Cookie & Tracking Notice"),
    "10-sliding-scale-scholarship-terms": ("scholarships", "Sliding-Scale & Scholarship Terms"),
    "14-community-standards": ("community-standards", "Community Standards"),
    "15-refund-returns-policy": ("refunds", "Refund & Returns Policy"),
}

# ---- _build_redline_docx (was L2283-L2345) ----
def _build_redline_docx(source_slug: str, doc_title: str, redlines: list[dict]) -> bytes:
    """Emit a Word .docx that renders as tracked changes on open.

    Real Word revisions require w:ins and w:del elements with monotonic
    ids, author, and date. We wrap python-docx paragraphs with raw OXML
    so the resulting file opens in Word 2016+ with track changes visible.
    """
    from io import BytesIO
    from docx import Document
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from datetime import datetime, timezone

    doc = Document()
    doc.core_properties.title = f"Counsel Redlines — {doc_title}"
    doc.core_properties.comments = (
        "Open in Word to review as tracked changes. Accept or reject each "
        "revision; save; return to Birthright."
    )

    h = doc.add_heading(f"Counsel Redlines — {doc_title}", level=1)
    doc.add_paragraph(
        f"Source: {source_slug}.md · Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
        f"{len(redlines)} unresolved redline(s)."
    )
    doc.add_paragraph(
        "Each numbered item below is a proposed change. Deleted text is "
        "shown struck through; inserted text is underlined. Open in Word "
        "or LibreOffice to accept or reject each revision using the Review "
        "toolbar."
    )

    now_iso_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    for i, r in enumerate(redlines, start=1):
        section = r.get("section") or "(no section)"
        author = r.get("author_email") or "counsel"
        p_h = doc.add_paragraph()
        run = p_h.add_run(f"{i}. {section}")
        run.bold = True

        rationale = r.get("body") or ""
        if rationale:
            doc.add_paragraph(rationale, style="Intense Quote")

        quoted = r.get("quoted_text") or ""
        replacement = r.get("suggested_replacement") or ""

        # Only render revision markup if there's something to strike or insert.
        if quoted or replacement:
            p = doc.add_paragraph()
            if quoted:
                _append_revision_run(p, quoted, kind="del", author=author,
                                     date=now_iso_utc, rev_id=i * 2 - 1)
            if replacement:
                _append_revision_run(p, replacement, kind="ins", author=author,
                                     date=now_iso_utc, rev_id=i * 2)

        doc.add_paragraph()  # spacer

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()

# ---- _append_revision_run (was L2348-L2391) ----
def _append_revision_run(paragraph, text: str, kind: str, author: str, date: str, rev_id: int):
    """Attach a w:ins or w:del run to `paragraph` with proper revision markup.

    `kind` is either "ins" (insertion) or "del" (deletion). Word / LibreOffice
    read this as a tracked change owned by `author` at `date`.
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    revision = OxmlElement(f"w:{kind}")
    revision.set(qn("w:id"), str(rev_id))
    revision.set(qn("w:author"), author)
    revision.set(qn("w:date"), date)

    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    if kind == "del":
        strike = OxmlElement("w:strike")
        strike.set(qn("w:val"), "true")
        rpr.append(strike)
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "C00000")
        rpr.append(color)
        r.append(rpr)
        # w:delText carries deleted text
        t = OxmlElement("w:delText")
        t.set(qn("xml:space"), "preserve")
        t.text = text
        r.append(t)
    else:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rpr.append(u)
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "2E5C46")
        rpr.append(color)
        r.append(rpr)
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = text
        r.append(t)

    revision.append(r)
    paragraph._p.append(revision)

# ---- _extract_paragraph_text (was L2448-L2466) ----
def _extract_paragraph_text(paragraph) -> str:
    """Return the visible-after-accept text of a docx paragraph.

    Word revision runs (`w:ins` and `w:del`) do not appear via
    `paragraph.text` even though they are the meaningful content. This
    walks the OXML and collects both plain runs and inserted runs while
    dropping deleted-text runs (`w:delText`) so we get what the final
    version WOULD read like if every remaining insertion were accepted.
    """
    from docx.oxml.ns import qn
    pieces: list[str] = []

    for child in paragraph._p.iter():
        tag = child.tag
        if tag == qn("w:delText"):
            continue                  # dropped text — treat as accepted-delete
        if tag == qn("w:t"):
            pieces.append(child.text or "")
    return "".join(pieces)

# ---- _parse_roundtrip_docx (was L2469-L2521) ----
def _parse_roundtrip_docx(blob: bytes) -> list[dict]:
    """Walk the returned .docx and, for every numbered redline block
    ('N. Section title'), return the reader-visible resolved text.

    Returns list of {index, section, resolved_text}. The frontend pairs
    these to comment ids in order (the export writes redlines in
    ascending `created_at`, so index N maps to the Nth open redline
    fetched with the same sort).
    """
    import re
    from io import BytesIO
    from docx import Document

    doc = Document(BytesIO(blob))
    numbered = re.compile(r"^\s*(\d+)\.\s+(.*)$")
    blocks: list[dict] = []
    current: Optional[dict] = None

    for para in doc.paragraphs:
        text = _extract_paragraph_text(para).strip()
        if not text:
            continue
        m = numbered.match(text)
        if m:
            if current:
                blocks.append(current)
            current = {
                "index": int(m.group(1)),
                "section": m.group(2).strip(),
                "resolved_lines": [],
            }
            continue
        if current is not None:
            # Skip the fixed intro paragraphs that come before the first
            # numbered heading, and the "Intense Quote" rationale (we
            # detect by matching known bodies later — for now just keep
            # everything after the numbered heading as candidate text).
            current["resolved_lines"].append(text)

    if current:
        blocks.append(current)

    out = []
    for b in blocks:
        # Collapse consecutive lines back to a single paragraph. The
        # first non-empty line that isn't obviously the rationale is the
        # counsel-resolved replacement.
        out.append({
            "index": b["index"],
            "section": b["section"],
            "resolved_text": "\n".join(b["resolved_lines"]).strip(),
        })
    return out

# ---- _run_docx_rebuild (was L2741-L2768) ----
async def _run_docx_rebuild(user: dict) -> bool:
    """Best-effort .docx rebuild. Kicks off the same script `rebuild-docx`
    calls but never raises — the roundtrip result is more important than
    the .docx refresh, and admin can still click the manual Rebuild
    button if something goes wrong."""
    from database import db
    import subprocess, sys
    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "eu_compliance_and_docx.py"
    if not script.exists():
        logger.warning("legal.rebuild: build script missing at %s", script)
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(script.parent.parent),
            capture_output=True, text=True, timeout=180,
        )
        ok = proc.returncode == 0
        await log_action(
            db, user, "legal.doc.rebuild.auto",
            target_type="legal_docs", target_id="all",
            metadata={"ok": ok, "returncode": proc.returncode,
                      "stderr_tail": proc.stderr[-200:] if proc.stderr else None},
        )
        return ok
    except Exception as exc:
        logger.warning("legal.rebuild.auto: %s", exc)
        return False

# ---- _email_roundtrip_summary (was L2771-L2840) ----
async def _email_roundtrip_summary(
    source_slug: str,
    applier: dict,
    counts: dict,
    rebuild_ok: bool,
) -> Optional[str]:
    """Send a short summary email to the admin who applied the roundtrip
    plus every user with role=readonly_admin (counsel). Uses the shared
    dry-run-safe mailer so this is a no-op in preview without SENDER_EMAIL
    configured."""
    from database import db
    from utils.mailer import send_email

    # Human-friendly title so counsel doesn't need to translate slugs.
    _, title = _SOURCE_TO_PUBLIC.get(source_slug, (source_slug, source_slug.replace("-", " ").title()))

    # Applier + every read-only admin (counsel).
    recipients: list[str] = []
    if applier.get("email"):
        recipients.append(applier["email"])
    async for u in db.users.find({"role": "readonly_admin"}, {"_id": 0, "email": 1}):
        if u.get("email") and u["email"] not in recipients:
            recipients.append(u["email"])
    if not recipients:
        return None

    subject = f"Roundtrip applied · {title} · {counts['applied']} accepted, {counts['rejected']} rejected"
    html = f"""
    <div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;color:#1A2424">
      <h2 style="font-family:'Cormorant Garamond',serif;color:#0F2424">Roundtrip applied</h2>
      <p><strong>Document:</strong> {title}</p>
      <p><strong>Applied by:</strong> {applier.get('email', 'admin')} · {now_iso()}</p>
      <table style="border-collapse:collapse;margin:16px 0;font-family:sans-serif;font-size:14px">
        <tr><td style="padding:4px 10px;color:#2E5C46"><strong>{counts['applied']}</strong> accepted</td></tr>
        <tr><td style="padding:4px 10px;color:#9E3C3C"><strong>{counts['rejected']}</strong> rejected</td></tr>
        <tr><td style="padding:4px 10px;color:#7A5A1A"><strong>{counts['skipped']}</strong> skipped</td></tr>
        {'<tr><td style="padding:4px 10px;color:#9E3C3C"><strong>' + str(counts['unmatched']) + '</strong> unmatched</td></tr>' if counts.get('unmatched') else ''}
        <tr><td style="padding:4px 10px;color:#5C6B6B">total {counts['total']}</td></tr>
      </table>
      <p style="color:#5C6B6B;font-size:13px">
        Counsel-briefing .docx bundle: <strong>{'refreshed automatically' if rebuild_ok else 'refresh failed — an admin should re-run the Rebuild button'}</strong>.
      </p>
      <p style="color:#5C6B6B;font-size:13px">
        See the full history at
        <a href="{os.environ.get('PUBLIC_SITE_URL', '')}/admin/legal/ratifications" style="color:#476B6B">/admin/legal/ratifications</a>.
      </p>
    </div>
    """
    text = (
        f"Roundtrip applied · {title}\n"
        f"Applied by: {applier.get('email', 'admin')} at {now_iso()}\n\n"
        f"Accepted: {counts['applied']}\n"
        f"Rejected: {counts['rejected']}\n"
        f"Skipped:  {counts['skipped']}\n"
        + (f"Unmatched: {counts['unmatched']}\n" if counts.get('unmatched') else "")
        + f"Total:    {counts['total']}\n\n"
        f"Bundle rebuild: {'ok' if rebuild_ok else 'FAILED — an admin should re-run manually'}\n"
    )
    try:
        return await send_email(
            to=recipients,
            subject=subject,
            html=html,
            text=text,
            template_name="legal_roundtrip_summary",
            metadata={"source_slug": source_slug, "counts": counts},
        )
    except Exception as exc:
        logger.warning("legal.roundtrip.email: %s", exc)
        return None
