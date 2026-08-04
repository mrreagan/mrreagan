"""Legal: versioned universal indemnification + signature tracking.

Anyone authenticated can view the active version and sign it. Admin can publish
new versions; activating a new version automatically deactivates prior ones and
updates the global_defaults pointer. Signatures are append-only and tied to a
specific version, so we have evidence of WHAT each user signed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from auth_utils import get_current_user, require_roles
from models import IndemnificationCreate, gen_id, now_iso
from utils.audit import log_action

logger = logging.getLogger("birthright.legal")
router = APIRouter(prefix="/legal", tags=["legal"])

# Static legal documents shipped alongside the backend. Add new files here
# (Markdown or PDF) and expose them via /api/legal/docs/{key} below.
LEGAL_DOC_DIR = Path(__file__).resolve().parent.parent / "legal_docs"


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
        },
        "counsel-briefing-md": {
            "filename": "LEGAL_BRIEFING_FOR_COUNSEL.md",
            "display_name": "Legal Briefing for Counsel (source).md",
            "content_type": "text/markdown; charset=utf-8",
            "category": "Briefing",
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
            }
    return idx


LEGAL_DOC_INDEX = _build_index()


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


# ============ VERSIONS ============

@router.get("/indemnification/active")
async def get_active_version():
    from database import db
    v = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not v:
        # Bootstrap: create v1.0 placeholder
        v = {
            "id": gen_id(),
            "version": "1.0",
            "body": DEFAULT_INDEMNIFICATION_BODY,
            "summary_of_changes": "Initial placeholder text.",
            "active": True,
            "created_by": "system",
            "created_at": now_iso(),
            "activated_at": now_iso(),
        }
        await db.indemnification_versions.insert_one(dict(v))
        v.pop("_id", None)
    return v


@router.get("/indemnification/versions")
async def list_versions(user: dict = Depends(require_roles("admin"))):
    from database import db
    versions = await db.indemnification_versions.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Hydrate with signature counts so the admin UI doesn't need a 2nd round-trip.
    counts: dict[str, int] = {}
    async for r in db.indemnification_signatures.aggregate([
        {"$group": {"_id": "$version_id", "n": {"$sum": 1}}},
    ]):
        counts[r["_id"]] = int(r.get("n") or 0)
    for v in versions:
        v["signature_count"] = counts.get(v["id"], 0)
    # Total active partner pool size — useful denominator for "% signed".
    active_partner_count = await db.partner_profiles.count_documents({
        "status": "active",
        "$or": [{"is_sample": {"$exists": False}}, {"is_sample": False}],
    })
    return {"versions": versions, "active_partner_count": active_partner_count}


@router.get("/indemnification/default-v2-draft")
async def default_v2_draft(user: dict = Depends(require_roles("admin"))):
    """Return the Birthright-curated v2 body + summary so the admin UI can
    seed its draft editor with a real, production-grade starting point.

    The body still must be reviewed by counsel — that's called out in the
    body itself — but it covers the structural sections (rev share, AI
    markup, licensing, sunset, refunds) so admins aren't authoring from
    scratch.
    """
    from agreements.v2_body import V2_VERSION, V2_SUMMARY_OF_CHANGES, V2_BODY
    return {
        "version": V2_VERSION,
        "summary_of_changes": V2_SUMMARY_OF_CHANGES,
        "body": V2_BODY,
    }


@router.post("/indemnification/versions")
async def create_version(
    data: IndemnificationCreate,
    user: dict = Depends(require_roles("admin")),
):
    """Publish a new version. It becomes active immediately and deactivates the prior one.

    On activation, fires a fire-and-forget notification email to every
    active partner (anyone with at least one non-sample active
    partner_profile) so the rollout meets the §11 re-sign notice
    requirement. Email failures are logged but do not roll back the
    publish — the in-product banner is the second comms channel.
    """
    from database import db
    existing = await db.indemnification_versions.find_one({"version": data.version})
    if existing:
        raise HTTPException(status_code=400, detail=f"Version {data.version} already exists")
    # deactivate all prior
    await db.indemnification_versions.update_many({"active": True}, {"$set": {"active": False}})
    version_id = gen_id()
    doc = {
        "id": version_id,
        "version": data.version.strip(),
        "body": data.body,
        "summary_of_changes": (data.summary_of_changes or "").strip(),
        "active": True,
        "created_by": user["id"],
        "created_at": now_iso(),
        "activated_at": now_iso(),
    }
    await db.indemnification_versions.insert_one(dict(doc))
    # also update global_defaults pointer for convenience
    await db.foundation_settings.update_one(
        {"key": "global_defaults"},
        {"$set": {"indemnification_active_version_id": version_id, "updated_at": now_iso()}},
        upsert=True,
    )
    await log_action(
        db, user, "legal.indemnification.activate",
        target_type="indemnification_version", target_id=version_id,
        metadata={"version": data.version},
    )
    # Fire-and-forget partner notification — don't block the response.
    import asyncio
    try:
        asyncio.create_task(_notify_partners_of_new_version(doc))
    except Exception as ex:
        logger.warning("Partner notification dispatch failed: %s", ex)
    doc.pop("_id", None)
    return doc


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


# ============ SIGNATURES ============

@router.post("/indemnification/sign")
async def sign_active(request: Request, user: dict = Depends(get_current_user)):
    from database import db
    # IC acknowledgement (optional — only sent by frontend when the user
    # holds an IC-classified partner profile). Persist on the signature so
    # the audit trail records the classification the user accepted under.
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    ic_acknowledged = bool(payload.get("ic_acknowledged"))

    active = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not active:
        raise HTTPException(status_code=400, detail="No active indemnification version")
    existing = await db.indemnification_signatures.find_one({
        "user_id": user["id"], "version_id": active["id"],
    })
    if existing:
        return {"already_signed": True, "version": active["version"], "signed_at": existing.get("signed_at")}
    sig = {
        "id": gen_id(),
        "version_id": active["id"],
        "version": active["version"],
        "user_id": user["id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "user_role": user.get("role", "participant"),
        "ic_acknowledged": ic_acknowledged,
        "signed_at": now_iso(),
        "ip": (request.client.host if request and request.client else None),
    }
    await db.indemnification_signatures.insert_one(dict(sig))
    await log_action(
        db, user, "legal.indemnification.sign",
        target_type="indemnification_version", target_id=active["id"],
        metadata={"version": active["version"], "ic_acknowledged": ic_acknowledged},
    )
    try:
        from utils.user_activity import log_event, CAT_SIGN
        await log_event(
            db, user_id=user["id"], email=user.get("email"), role=user.get("role"),
            event_type="signing.indemnification_signed", category=CAT_SIGN,
            method="POST", path="/api/legal/indemnification/sign", status_code=200,
            metadata={"version": active["version"], "version_id": active["id"]},
            request=request,
        )
    except Exception:
        pass
    sig.pop("_id", None)
    return {"already_signed": False, **sig}


@router.get("/indemnification/my-status")
async def my_status(user: dict = Depends(get_current_user)):
    """Check whether the signed-in user has accepted the active version.

    Also returns `blocked_actions` — a per-partner-role list of write-side
    features the user will lose access to until they sign. Used by the
    AgreementResignBanner to render specific, honest copy instead of
    generic "you might lose access" wording.
    """
    from database import db
    active = await db.indemnification_versions.find_one({"active": True}, {"_id": 0})
    if not active:
        return {"active_version": None, "signed": False, "blocked_actions": []}
    sig = await db.indemnification_signatures.find_one(
        {"user_id": user["id"], "version_id": active["id"]}, {"_id": 0}
    )
    signed = bool(sig)

    blocked: list[str] = []
    ic_partner_types: list[str] = []
    roles: set[str] = set()
    async for prof in db.partner_profiles.find(
        {"user_id": user["id"], "status": "active",
         "$or": [{"is_sample": {"$exists": False}}, {"is_sample": False}]},
        {"_id": 0, "partner_type": 1},
    ):
        if prof.get("partner_type"):
            roles.add(prof["partner_type"])
    # Kept in sync with backend/routers/partner_prospects.py::IC_PARTNER_TYPES
    IC_SET = {"facilitator", "steward", "vendor", "artist", "community"}
    ic_partner_types = sorted(roles & IC_SET)

    if not signed:
        # Compute the per-role blocked list from the user's active profiles.
        # We always include the universal pair (DMs + subscriptions) since
        # those gates apply to everyone, signed-in or not.
        blocked.append("Open new direct message threads")
        blocked.append("Start or change a subscription")
        if "vendor" in roles or "facilitator" in roles or "artist" in roles or "research" in roles:
            blocked.append("Generate new AI Studio drafts")
        if "research" in roles:
            blocked.append("Publish research artifacts")
        if roles:
            blocked.append("Purchase featured slots")
            blocked.append("Update W9 or payout method")

    return {
        "active_version": {"id": active["id"], "version": active["version"]},
        "signed": signed,
        "signed_at": sig.get("signed_at") if sig else None,
        "blocked_actions": blocked,
        # Broadcast the user's IC-classified partner types so the frontend
        # can require an IC acknowledgement on the re-sign form.
        "ic_partner_types": ic_partner_types,
    }


@router.get("/indemnification/signatures")
async def list_signatures(
    version_id: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    query = {"version_id": version_id} if version_id else {}
    sigs = await db.indemnification_signatures.find(query, {"_id": 0}).sort("signed_at", -1).to_list(2000)
    # Hydrate with user email + IP normalization for the admin ledger UI.
    user_ids = list({s.get("user_id") for s in sigs if s.get("user_id")})
    emails: dict[str, str] = {}
    if user_ids:
        async for u in db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "email": 1}):
            emails[u["id"]] = u.get("email")
    for s in sigs:
        s["user_email"] = emails.get(s.get("user_id"))
        s["ip_address"] = s.get("ip")  # alias for the older field name
    return sigs



# ============ COUNSEL-FACING STATIC LEGAL DOCS ============

@router.get("/docs")
async def list_legal_docs(user: dict = Depends(require_roles("admin"))):
    """List the static legal documents an admin can download.

    Kept admin-only because these docs (currently the counsel briefing) can
    contain internal notes not meant for public consumption.
    """
    out = []
    for key, meta in LEGAL_DOC_INDEX.items():
        fp = LEGAL_DOC_DIR / meta["filename"]
        if not fp.exists():
            continue
        out.append({
            "key": key,
            "display_name": meta["display_name"],
            "category": meta.get("category", "Draft"),
            "size_bytes": fp.stat().st_size,
            "download_url": f"/api/legal/docs/{key}",
        })
    return out


@router.get("/docs/{key}")
async def download_legal_doc(key: str, user: dict = Depends(require_roles("admin"))):
    """Stream the requested legal document as a download. Admin-only."""
    meta = LEGAL_DOC_INDEX.get(key)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown legal document")
    fp = LEGAL_DOC_DIR / meta["filename"]
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Document file missing on server")
    return FileResponse(
        path=str(fp),
        media_type=meta["content_type"],
        filename=meta["display_name"],
    )


@router.get("/drafts/{slug}")
async def public_draft(slug: str):
    """PUBLIC download of a first-draft legal document (no auth required).

    These drafts are AI-generated first drafts explicitly labelled "not legal
    advice" and are intended to be shareable with outside counsel without
    creating an admin account. Only serves files whose slug is registered in
    the manifest — no arbitrary file access.
    """
    try:
        import sys
        sys.path.insert(0, str(LEGAL_DOC_DIR))
        from _manifest import DRAFT_LEGAL_DOCS  # type: ignore
    except Exception:
        DRAFT_LEGAL_DOCS = []
    entry = next((d for d in DRAFT_LEGAL_DOCS if d["slug"] == slug), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Unknown draft")
    fp = LEGAL_DOC_DIR / f"{slug}.docx"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Draft file missing on server")
    return FileResponse(
        path=str(fp),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{entry['display_name']}.docx",
    )


# ============ PUBLIC LEGAL RENDERER ============
# Live HTML rendering of the public-facing Markdown drafts so users don't
# have to download a .docx to read the Terms / Privacy / Cookie Notice.
# Only slugs mapped in PUBLIC_LEGAL_PAGES are served publicly.

# User-friendly slug → manifest slug. Anything not in this dict returns 404.
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
}


def _strip_draft_disclaimer(md: str) -> tuple[str, bool]:
    """Peel off the leading `> ⚠️ AI-GENERATED FIRST DRAFT` blockquote so the
    rendered page can surface it as a distinct banner instead of a wall of
    quoted text. Returns (cleaned_markdown, had_disclaimer).
    """
    lines = md.splitlines()
    if not lines or not lines[0].startswith(">"):
        return md, False
    i = 0
    while i < len(lines) and (lines[i].startswith(">") or lines[i].strip() == ""):
        # Stop when we hit content that isn't a blockquote and isn't blank
        if lines[i].strip() == "" and i + 1 < len(lines) and not lines[i + 1].startswith(">"):
            i += 1
            break
        i += 1
    return "\n".join(lines[i:]).lstrip(), True


@router.get("/pages")
async def list_public_pages():
    """List every public-facing legal page (slug + title) so the frontend
    can build a table of contents (e.g. footer legal menu)."""
    out = []
    for slug, meta in PUBLIC_LEGAL_PAGES.items():
        fp = LEGAL_DOC_DIR / f"{meta['source_slug']}.md"
        if fp.exists():
            out.append({"slug": slug, "title": meta["title"]})
    return out


@router.get("/pages/{slug}")
async def get_public_page(slug: str):
    """Render a public legal page as HTML. Returns the rendered HTML plus
    metadata (title, updated_at, has_draft_disclaimer) so the frontend can
    surface a "not yet counsel-reviewed" banner separately from the body."""
    meta = PUBLIC_LEGAL_PAGES.get(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown legal page")
    fp = LEGAL_DOC_DIR / f"{meta['source_slug']}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Source markdown missing")

    raw_md = fp.read_text(encoding="utf-8")
    cleaned_md, had_disclaimer = _strip_draft_disclaimer(raw_md)

    import markdown as md_lib
    html = md_lib.markdown(
        cleaned_md,
        extensions=["extra", "sane_lists", "toc", "tables"],
        output_format="html5",
    )

    from datetime import datetime, timezone
    updated_at = datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc).isoformat()

    # Look up the current ratification record (if any). Once counsel has
    # marked a version as ratified, we suppress the draft-disclaimer banner
    # in the client. The next content edit lands with a new revision and
    # the banner returns until re-ratified.
    ratification = await _current_ratification(meta["source_slug"])

    body_hash = _md_body_hash(cleaned_md)
    ratified = bool(
        ratification
        and ratification.get("body_hash") == body_hash
    )

    return {
        "slug": slug,
        "source_slug": meta["source_slug"],
        "title": meta["title"],
        "html": html,
        "updated_at": updated_at,
        # Only surface the "first draft" banner if we do NOT have a
        # ratification record matching the current body hash.
        "has_draft_disclaimer": had_disclaimer and not ratified,
        "ratified": ratified,
        "ratified_version": ratification.get("version") if ratification else None,
        "ratified_at": ratification.get("ratified_at") if ratification else None,
        "ratified_by": ratification.get("ratified_by") if ratification else None,
        # Download link for the counsel-facing DOCX (same content, formatted).
        "docx_url": f"/api/legal/drafts/{meta['source_slug']}",
    }


# ============ VERSIONED PUBLISH FLOW ============
# Once outside counsel signs off on a draft, an admin marks it as
# "counsel-ratified v{N}". The frontend uses this to suppress the
# "first draft" banner. Any subsequent content change invalidates the
# ratification (body-hash mismatch) and the banner comes back.

import hashlib as _hashlib


def _md_body_hash(cleaned_md: str) -> str:
    return _hashlib.sha256(cleaned_md.encode("utf-8")).hexdigest()[:16]


async def _current_ratification(source_slug: str) -> Optional[dict]:
    from database import db
    return await db.legal_doc_ratifications.find_one(
        {"source_slug": source_slug}, {"_id": 0}, sort=[("ratified_at", -1)]
    )


@router.get("/ratifications")
async def list_ratifications(user: dict = Depends(require_roles("admin"))):
    """Admin — every ratification record, newest first."""
    from database import db
    rows = await db.legal_doc_ratifications.find(
        {}, {"_id": 0}
    ).sort("ratified_at", -1).to_list(500)
    return rows


@router.post("/ratifications/{source_slug}")
async def add_ratification(
    source_slug: str,
    payload: dict,
    request: Request,
    user: dict = Depends(require_roles("admin")),
):
    """Admin — mark a doc as counsel-ratified v{N}.

    Payload:  { "version": "1.0", "notes": "...", "ratified_by": "Firm & Co." }
    """
    from database import db
    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")

    raw_md = fp.read_text(encoding="utf-8")
    cleaned_md, _ = _strip_draft_disclaimer(raw_md)

    version = str(payload.get("version") or "").strip()
    if not version:
        raise HTTPException(status_code=400, detail="version required (e.g. '1.0')")

    rec = {
        "id": gen_id(),
        "source_slug": source_slug,
        "version": version,
        "body_hash": _md_body_hash(cleaned_md),
        "notes": (payload.get("notes") or "").strip() or None,
        "ratified_by": (payload.get("ratified_by") or "").strip() or None,
        "ratified_at": now_iso(),
        "ratified_by_user_id": user["id"],
        "ratified_by_user_email": user.get("email"),
    }
    await db.legal_doc_ratifications.insert_one(dict(rec))
    await log_action(
        db, user, "legal.doc.ratify",
        target_type="legal_doc", target_id=source_slug,
        metadata={"version": version, "body_hash": rec["body_hash"]},
    )
    rec.pop("_id", None)
    return rec


@router.delete("/ratifications/{source_slug}")
async def revoke_ratification(
    source_slug: str,
    user: dict = Depends(require_roles("admin")),
):
    """Admin — revoke the current ratification (banner returns)."""
    from database import db
    r = await db.legal_doc_ratifications.delete_many({"source_slug": source_slug})
    await log_action(
        db, user, "legal.doc.ratify_revoke",
        target_type="legal_doc", target_id=source_slug,
        metadata={"deleted": r.deleted_count},
    )
    return {"deleted": r.deleted_count}


# ============ FULL-DOC REPLACEMENT (counsel + admin) ============
# Lets counsel — or an admin — replace the entire source of a legal
# document by uploading a new .md OR .docx file. This is the "big red
# button" alternative to inline redlines: when counsel wants to rewrite
# a whole notice rather than annotate diffs, they upload the final draft
# here and it becomes the new source. Any existing ratification is
# preserved as a record but stops matching (body-hash mismatch), so the
# "first draft" banner returns until re-ratified.

@router.post("/docs/{source_slug}/upload")
async def upload_full_replacement(
    source_slug: str,
    request: Request,
    user: dict = Depends(require_roles("admin")),
):
    """Upload a full replacement for `<source_slug>.md`.

    Accepts multipart form-data with one file:
      - `.md`   → written verbatim as the working-draft source
      - `.docx` → text is extracted paragraph-by-paragraph, headings are
                  detected via style name (`Heading 1..6`) and converted to
                  `#`..`######`, then written as the working-draft source

    Behaviour (as of the working-draft workflow):
      - The public source .md is NOT touched. Instead, the content lands
        in `legal_doc_working_drafts` as a WORKING VERSION. The public site
        keeps rendering the released .md until admin promotes the working
        draft via `POST /legal/working-drafts/{slug}/release`.
      - Records an audit entry (`legal.doc.working.upload`)
      - Returns the new byte-count, body-hash, working-draft id, and state.
    """
    from database import db
    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")

    form = await request.form()
    upload = form.get("file")
    if not upload or not hasattr(upload, "filename"):
        raise HTTPException(status_code=400, detail="Missing `file` form field")

    filename = (upload.filename or "").lower()
    blob = await upload.read()
    if not blob:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(blob) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 2 MB cap.")

    if filename.endswith(".md") or filename.endswith(".markdown") or filename.endswith(".txt"):
        try:
            new_md = blob.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Not valid UTF-8: {exc}")
    elif filename.endswith(".docx"):
        new_md = _docx_to_markdown(blob)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload `.md`, `.markdown`, `.txt`, or `.docx`.",
        )

    if not new_md.strip():
        raise HTTPException(status_code=400, detail="Converted content is empty; refusing to save.")

    wd = await _upsert_working_draft(
        source_slug=source_slug,
        content_md=new_md,
        user=user,
        action="upload_full",
        note=f"Uploaded {upload.filename} ({len(blob)} bytes)",
    )

    await log_action(
        db, user, "legal.doc.working.upload",
        target_type="legal_doc", target_id=source_slug,
        metadata={
            "filename": upload.filename,
            "bytes": len(blob),
            "converted_bytes": len(new_md.encode("utf-8")),
            "working_draft_id": wd["id"],
            "state": wd["state"],
            "uploaded_by_role": user.get("role"),
        },
    )
    return {
        "source_slug": source_slug,
        "filename": upload.filename,
        "bytes_written": len(new_md.encode("utf-8")),
        "working_draft_id": wd["id"],
        "state": wd["state"],
        "message": (
            "Working draft updated. The public site still shows the released "
            "version. An admin must click Release to publish this working "
            "version."
        ),
    }


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


# ============ WORKING-DRAFT STAGING AREA ============
# A parallel table `legal_doc_working_drafts` where every counsel/admin
# edit lands as a WORKING VERSION. The public source .md is only touched
# when an admin explicitly RELEASES the working draft. This keeps the
# public site stable while counsel iterates.
#
# States: draft → awaiting_admin → released | discarded

_WD_STATE_DRAFT = "draft"
_WD_STATE_READY = "awaiting_admin"
_WD_STATE_RELEASED = "released"
_WD_STATE_DISCARDED = "discarded"


def _released_md(source_slug: str) -> str:
    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")
    return fp.read_text(encoding="utf-8")


async def _active_working_draft(source_slug: str) -> Optional[dict]:
    """Return the current OPEN working draft for this slug (state ∈
    {draft, awaiting_admin}), or None."""
    from database import db
    return await db.legal_doc_working_drafts.find_one(
        {"source_slug": source_slug,
         "state": {"$in": [_WD_STATE_DRAFT, _WD_STATE_READY]}},
        {"_id": 0},
    )


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


async def _next_version(source_slug: str) -> str:
    from database import db
    latest = await db.legal_doc_ratifications.find_one(
        {"source_slug": source_slug}, {"_id": 0, "version": 1},
        sort=[("ratified_at", -1)],
    )
    return _bump_minor(latest.get("version", "") if latest else "")


@router.get("/working-drafts")
async def list_working_drafts(user: dict = Depends(require_roles("admin"))):
    """List every OPEN working draft (state ∈ {draft, awaiting_admin}).

    Counsel (`readonly_admin`) can also read this via the shared
    `require_roles('admin')` allow-list — the counsel console renders
    from this endpoint.
    """
    from database import db
    rows = await db.legal_doc_working_drafts.find(
        {"state": {"$in": [_WD_STATE_DRAFT, _WD_STATE_READY]}},
        {"_id": 0, "content_md": 0},   # skip body for list view
    ).sort("last_edited_at", -1).to_list(200)
    return rows


@router.get("/working-drafts/{source_slug}")
async def get_working_draft(
    source_slug: str,
    user: dict = Depends(require_roles("admin")),
):
    """Detail view: released body + working body + change log + stale flag.

    Returns 404 if no open working draft exists for this slug.
    """
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft for this slug.")
    released_md = _released_md(source_slug)
    released_hash = _md_body_hash(_strip_draft_disclaimer(released_md)[0])
    return {
        **wd,
        "released_md": released_md,
        "released_body_hash": released_hash,
        "is_stale": wd.get("base_released_hash") != released_hash,
    }


@router.get("/working-drafts/{source_slug}/download")
async def download_working_draft(
    source_slug: str,
    user: dict = Depends(require_roles("admin")),
):
    """Download the open working draft as a .docx so counsel can edit
    offline. Uses the same DOCX builder the rest of the pipeline uses so
    round-tripping stays byte-identical shape-wise.
    """
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft for this slug.")

    # Build the .docx in-memory from the working-draft markdown.
    from io import BytesIO
    from docx import Document
    from starlette.responses import StreamingResponse

    doc = Document()
    for line in (wd["content_md"] or "").splitlines():
        stripped = line.rstrip()
        if not stripped:
            doc.add_paragraph("")
            continue
        # Heading detection
        if stripped.startswith("#"):
            level = 0
            while level < len(stripped) and stripped[level] == "#":
                level += 1
            text = stripped[level:].strip()
            doc.add_heading(text, level=min(level, 6))
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
            continue
        doc.add_paragraph(stripped)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = f"{source_slug}.working-draft.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/working-drafts/{source_slug}/mark-ready")
async def mark_ready(
    source_slug: str,
    user: dict = Depends(require_roles("admin")),
):
    """Counsel signals the working draft is ready for admin review."""
    from database import db
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft.")
    now = now_iso()
    change_log = list(wd.get("change_log") or [])
    change_log.append({
        "at": now,
        "by_user_id": user["id"],
        "by_email": user.get("email"),
        "by_role": user.get("role"),
        "action": "mark_ready",
        "note": "Marked ready for admin review",
        "bytes": len((wd.get("content_md") or "").encode("utf-8")),
    })
    await db.legal_doc_working_drafts.update_one(
        {"id": wd["id"]},
        {"$set": {"state": _WD_STATE_READY,
                  "last_edited_at": now,
                  "change_log": change_log}},
    )
    await log_action(
        db, user, "legal.doc.working.mark_ready",
        target_type="legal_doc", target_id=source_slug,
        metadata={"working_draft_id": wd["id"]},
    )
    return {"state": _WD_STATE_READY, "working_draft_id": wd["id"]}


@router.post("/working-drafts/{source_slug}/release")
async def release_working_draft(
    source_slug: str,
    payload: dict,
    user: dict = Depends(require_roles("admin")),
):
    """ADMIN — promote the working draft to the released `.md`.

    Steps:
      1. Write working draft content_md → /legal_docs/<slug>.md
      2. Auto-rebuild the .docx bundle (best-effort)
      3. Create a ratification record with auto-bumped minor version
         (payload.version overrides if provided)
      4. Mark the working draft state=released
    """
    from database import db
    # Counsel MUST NOT be able to release. require_roles('admin') accepts
    # readonly_admin globally, so we defend in depth here.
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can release a working draft.")

    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft to release.")

    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")

    new_md = wd["content_md"] or ""
    fp.write_text(new_md, encoding="utf-8")
    cleaned, _ = _strip_draft_disclaimer(new_md)
    body_hash = _md_body_hash(cleaned)

    rebuild_ok = await _run_docx_rebuild(user=user)

    version = (payload.get("version") or "").strip() or await _next_version(source_slug)
    ratified_by = (payload.get("ratified_by") or "").strip() or user.get("email") or "admin"
    notes = (payload.get("notes") or "").strip() or f"Released working draft {wd['id']}"
    rat = {
        "id": gen_id(),
        "source_slug": source_slug,
        "version": version,
        "body_hash": body_hash,
        "notes": notes,
        "ratified_by": ratified_by,
        "ratified_at": now_iso(),
        "ratified_by_user_id": user["id"],
        "ratified_by_user_email": user.get("email"),
        "released_from_working_draft_id": wd["id"],
    }
    await db.legal_doc_ratifications.insert_one(dict(rat))

    now = now_iso()
    change_log = list(wd.get("change_log") or [])
    change_log.append({
        "at": now,
        "by_user_id": user["id"],
        "by_email": user.get("email"),
        "by_role": "admin",
        "action": "release",
        "note": f"Released as v{version}",
        "bytes": len(new_md.encode("utf-8")),
    })
    await db.legal_doc_working_drafts.update_one(
        {"id": wd["id"]},
        {"$set": {
            "state": _WD_STATE_RELEASED,
            "released_at": now,
            "released_by_email": user.get("email"),
            "released_as_version": version,
            "change_log": change_log,
        }},
    )

    await log_action(
        db, user, "legal.doc.working.release",
        target_type="legal_doc", target_id=source_slug,
        metadata={"working_draft_id": wd["id"], "version": version,
                  "rebuilt": rebuild_ok, "body_hash": body_hash},
    )
    return {
        "released_as_version": version,
        "ratification_id": rat["id"],
        "rebuilt_docx": rebuild_ok,
        "working_draft_id": wd["id"],
        "state": _WD_STATE_RELEASED,
    }


@router.post("/working-drafts/{source_slug}/discard")
async def discard_working_draft(
    source_slug: str,
    payload: dict,
    user: dict = Depends(require_roles("admin")),
):
    """ADMIN — throw away the working draft. Released .md is untouched."""
    from database import db
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can discard a working draft.")
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft to discard.")
    reason = (payload.get("reason") or "").strip() or "no reason given"
    now = now_iso()
    change_log = list(wd.get("change_log") or [])
    change_log.append({
        "at": now,
        "by_user_id": user["id"],
        "by_email": user.get("email"),
        "by_role": "admin",
        "action": "discard",
        "note": reason,
        "bytes": len((wd.get("content_md") or "").encode("utf-8")),
    })
    await db.legal_doc_working_drafts.update_one(
        {"id": wd["id"]},
        {"$set": {
            "state": _WD_STATE_DISCARDED,
            "discarded_at": now,
            "discarded_by_email": user.get("email"),
            "discard_reason": reason,
            "change_log": change_log,
        }},
    )
    await log_action(
        db, user, "legal.doc.working.discard",
        target_type="legal_doc", target_id=source_slug,
        metadata={"working_draft_id": wd["id"], "reason": reason},
    )
    return {"state": _WD_STATE_DISCARDED, "working_draft_id": wd["id"]}


# ============ INLINE REDLINES / COUNSEL COMMENTS ============
# Lightweight comment thread per legal doc. Sections are opaque strings
# (usually the H2 heading) so counsel can pin comments to a specific
# section without a full inline-diff engine.

@router.get("/comments/{source_slug}")
async def list_comments(
    source_slug: str,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    rows = await db.legal_doc_comments.find(
        {"source_slug": source_slug}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return rows


@router.post("/comments/{source_slug}")
async def add_comment(
    source_slug: str,
    payload: dict,
    request: Request,
    user: dict = Depends(require_roles("admin")),
):
    """Add a redline comment (or a general note) on a legal doc."""
    from database import db
    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="body required")
    rec = {
        "id": gen_id(),
        "source_slug": source_slug,
        "section": (payload.get("section") or "").strip() or None,
        "quoted_text": (payload.get("quoted_text") or "").strip() or None,
        "suggested_replacement": (payload.get("suggested_replacement") or "").strip() or None,
        "body": body,
        "kind": payload.get("kind") or "comment",   # comment | redline | resolved
        "resolved": False,
        "resolved_at": None,
        "resolved_by": None,
        "author_id": user["id"],
        "author_email": user.get("email"),
        "author_role": user.get("role"),
        "created_at": now_iso(),
    }
    await db.legal_doc_comments.insert_one(dict(rec))
    await log_action(
        db, user, "legal.doc.comment.add",
        target_type="legal_doc", target_id=source_slug,
        metadata={"kind": rec["kind"], "section": rec["section"]},
    )
    rec.pop("_id", None)
    return rec


@router.post("/comments/{source_slug}/{comment_id}/resolve")
async def resolve_comment(
    source_slug: str,
    comment_id: str,
    user: dict = Depends(require_roles("admin")),
):
    from database import db
    r = await db.legal_doc_comments.update_one(
        {"id": comment_id, "source_slug": source_slug},
        {"$set": {
            "resolved": True,
            "resolved_at": now_iso(),
            "resolved_by": user.get("email"),
        }},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found")
    await log_action(
        db, user, "legal.doc.comment.resolve",
        target_type="legal_doc_comment", target_id=comment_id,
    )
    return {"resolved": True}


# ============ PUBLIC RATIFICATION HISTORY ============
# Runs at /api/legal/history so /legal/history on the frontend can render
# a public change-log of every ratification (which policy, which version,
# ratifying firm, date). Kept intentionally sparse — no internal notes.

# Reverse-lookup from source_slug (manifest) → public slug (URL).
_SOURCE_TO_PUBLIC = {
    "01-terms-of-service": ("terms", "Terms of Service"),
    "02-privacy-policy": ("privacy", "Privacy Policy"),
    "03-cookie-notice": ("cookie-notice", "Cookie & Tracking Notice"),
    "10-sliding-scale-scholarship-terms": ("scholarships", "Sliding-Scale & Scholarship Terms"),
    "14-community-standards": ("community-standards", "Community Standards"),
    "15-refund-returns-policy": ("refunds", "Refund & Returns Policy"),
}


@router.get("/history")
async def public_ratification_history():
    """Public — newest-first list of every ratification of a public doc.

    Returns only public docs (Terms/Privacy/Cookie/Refunds/Scholarships/
    Community Standards). Internal notes are stripped so the change-log
    stays user-facing.
    """
    from database import db
    rows = await db.legal_doc_ratifications.find(
        {"source_slug": {"$in": list(_SOURCE_TO_PUBLIC.keys())}},
        {"_id": 0, "source_slug": 1, "version": 1, "ratified_at": 1, "ratified_by": 1},
    ).sort("ratified_at", -1).to_list(500)
    out = []
    for r in rows:
        public_slug, title = _SOURCE_TO_PUBLIC.get(r["source_slug"], (r["source_slug"], r["source_slug"]))
        out.append({
            "slug": public_slug,
            "title": title,
            "version": r["version"],
            "ratified_at": r["ratified_at"],
            "ratified_by": r.get("ratified_by"),
        })
    return out


@router.get("/history.rss")
async def public_ratification_rss(request: Request):
    """Public RSS 2.0 feed of ratifications for partners + press to
    subscribe. Uses the site's REACT_APP_BACKEND_URL / current host as
    the item permalink base so feed readers de-dupe cleanly.
    """
    from database import db
    from fastapi.responses import Response
    from xml.sax.saxutils import escape as _esc
    import os

    rows = await db.legal_doc_ratifications.find(
        {"source_slug": {"$in": list(_SOURCE_TO_PUBLIC.keys())}},
        {"_id": 0, "source_slug": 1, "version": 1, "ratified_at": 1, "ratified_by": 1},
    ).sort("ratified_at", -1).to_list(200)

    # Public base: prefer explicit env, fall back to request host.
    base = os.environ.get("PUBLIC_SITE_URL")
    if not base:
        host = request.headers.get("host", "birthright.live")
        scheme = "https" if request.url.scheme == "https" else "http"
        base = f"{scheme}://{host}"

    def _rfc822(iso: str) -> str:
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.strftime("%a, %d %b %Y %H:%M:%S %z") or dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except Exception:
            return ""

    items_xml = []
    for r in rows:
        public_slug, title = _SOURCE_TO_PUBLIC.get(r["source_slug"], (r["source_slug"], r["source_slug"]))
        firm = r.get("ratified_by") or "outside counsel"
        item_title = f"{title} · v{r['version']} ratified"
        item_desc = (
            f"Birthright Foundation policy '{title}' was ratified at version "
            f"{r['version']} by {firm}. The updated policy is now live at "
            f"{base}/legal/{public_slug}."
        )
        link = f"{base}/legal/{public_slug}"
        guid = f"{base}/legal/{public_slug}#v{r['version']}"
        items_xml.append(
            "<item>"
            f"<title>{_esc(item_title)}</title>"
            f"<link>{_esc(link)}</link>"
            f"<guid isPermaLink=\"false\">{_esc(guid)}</guid>"
            f"<pubDate>{_esc(_rfc822(r['ratified_at']))}</pubDate>"
            f"<description>{_esc(item_desc)}</description>"
            "</item>"
        )

    channel_updated = rows[0]["ratified_at"] if rows else ""
    body = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<rss version=\"2.0\" xmlns:atom=\"http://www.w3.org/2005/Atom\">"
        "<channel>"
        f"<title>Birthright Foundation — Policy Ratifications</title>"
        f"<link>{_esc(base)}/legal/history</link>"
        f"<atom:link href=\"{_esc(base)}/api/legal/history.rss\" rel=\"self\" type=\"application/rss+xml\" />"
        "<description>Notifications whenever outside counsel ratifies a version of a public Birthright policy.</description>"
        "<language>en-US</language>"
        f"<lastBuildDate>{_esc(_rfc822(channel_updated))}</lastBuildDate>"
        + "".join(items_xml) +
        "</channel></rss>"
    )
    return Response(content=body, media_type="application/rss+xml; charset=utf-8")


# ============ REDLINE EXPORT (Word track-changes .docx) ============
# Emits a Word document with real w:ins / w:del revision markup so counsel
# can open it in Word/LibreOffice and accept/reject each proposed change
# offline. Only unresolved redlines are exported (comments-only entries
# are skipped — they're advisory, not track-change markup).

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


@router.get("/comments/{source_slug}/export")
async def export_unresolved_redlines(
    source_slug: str,
    user: dict = Depends(require_roles("admin")),
):
    """Download every UNRESOLVED redline for a doc as a Word file that
    renders as tracked changes. Comment-only entries are excluded.

    Counsel (readonly_admin) is allow-listed via require_roles so their
    firm can open the file, mark up changes, and return offline.
    """
    from database import db
    from fastapi.responses import Response

    # Look up the public title for the header.
    public_slug, title = _SOURCE_TO_PUBLIC.get(source_slug, (source_slug, source_slug))
    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")

    redlines = await db.legal_doc_comments.find(
        {"source_slug": source_slug, "resolved": False, "kind": "redline"},
        {"_id": 0},
    ).sort("created_at", 1).to_list(500)

    if not redlines:
        raise HTTPException(status_code=404, detail="No unresolved redlines to export")

    blob = _build_redline_docx(source_slug, title, redlines)

    await log_action(
        db, user, "legal.doc.redlines.export",
        target_type="legal_doc", target_id=source_slug,
        metadata={"count": len(redlines)},
    )

    filename = f"redlines-{public_slug}.docx"
    return Response(
        content=blob,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============ REDLINE ROUNDTRIP (import edited .docx) ============
# Counsel opens the exported .docx, accepts / rejects / edits each track
# change in Word, saves, and returns the file. Admin uploads the file
# here; we parse each numbered redline block (they map 1:1 to the redline
# comment ids from the export) and extract counsel's resolved text. Admin
# then previews and selectively applies edits to the source .md, marking
# the corresponding comments resolved with a `rejected` flag when counsel
# threw the redline out.


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


@router.post("/comments/{source_slug}/import-roundtrip")
async def import_roundtrip_preview(
    source_slug: str,
    request: Request,
    user: dict = Depends(require_roles("admin")),
):
    """Parse an uploaded track-changes .docx and return a preview.

    Response pairs each parsed block with the matching UNRESOLVED redline
    comment (by 1-based order) and computes the proposed action:
      - accept:  counsel kept the suggested_replacement
      - reject:  counsel restored the quoted_text
      - edit:    counsel wrote something else
    """
    from database import db

    form = await request.form()
    upload = form.get("file")
    if not upload:
        raise HTTPException(status_code=400, detail="file required (multipart 'file')")
    blob = await upload.read()
    try:
        parsed = _parse_roundtrip_docx(blob)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse .docx: {e}")

    open_redlines = await db.legal_doc_comments.find(
        {"source_slug": source_slug, "resolved": False, "kind": "redline"},
        {"_id": 0},
    ).sort("created_at", 1).to_list(500)

    def _classify(quoted: str, replacement: str, resolved_text: str) -> str:
        if not resolved_text:
            return "reject"
        if replacement and replacement.strip() in resolved_text:
            return "accept"
        if quoted and quoted.strip() in resolved_text and (not replacement or replacement.strip() not in resolved_text):
            return "reject"
        return "edit"

    preview = []
    for block in parsed:
        idx = block["index"] - 1
        if idx < 0 or idx >= len(open_redlines):
            preview.append({
                "index": block["index"],
                "section": block["section"],
                "resolved_text": block["resolved_text"],
                "match": None,
                "action": "orphan",
            })
            continue
        red = open_redlines[idx]
        action = _classify(red.get("quoted_text") or "", red.get("suggested_replacement") or "", block["resolved_text"])
        preview.append({
            "index": block["index"],
            "section": block["section"],
            "resolved_text": block["resolved_text"],
            "match": {
                "id": red["id"],
                "section": red.get("section"),
                "quoted_text": red.get("quoted_text"),
                "suggested_replacement": red.get("suggested_replacement"),
                "body": red.get("body"),
            },
            "action": action,
        })
    return {"count": len(preview), "items": preview}


@router.post("/comments/{source_slug}/apply-roundtrip")
async def apply_roundtrip(
    source_slug: str,
    payload: dict,
    request: Request,
    user: dict = Depends(require_roles("admin")),
):
    """Apply the admin-approved subset of the parsed roundtrip.

    Payload:
      { "decisions": [ { "comment_id": "...", "action": "accept|reject|skip",
                         "final_text": "..." } ] }

    Behaviour:
      - accept: string-replace `quoted_text` → `final_text` in the source
        .md and mark the redline resolved (rejected=false).
      - reject: mark the redline resolved with rejected=true; no .md edit.
      - skip:   leave the redline open.

    After edits the source .md is written back and the caller SHOULD
    trigger the .docx rebuild separately (POST /legal/rebuild-docx) if
    they want the counsel-briefing .docx refreshed.
    """
    from database import db
    decisions = payload.get("decisions") or []
    if not isinstance(decisions, list):
        raise HTTPException(status_code=400, detail="decisions must be a list")

    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")
    # Read from the open working draft if one exists, else from the
    # released .md. Writes always go to the working draft so the public
    # site stays stable until admin releases.
    open_wd = await _active_working_draft(source_slug)
    raw = (open_wd["content_md"] if open_wd else fp.read_text(encoding="utf-8"))

    applied = 0
    rejected = 0
    skipped = 0
    misses: list[str] = []

    # Load the open redlines once (id → doc) for fast lookup.
    by_id: dict[str, dict] = {}
    async for r in db.legal_doc_comments.find(
        {"source_slug": source_slug, "resolved": False}, {"_id": 0}
    ):
        by_id[r["id"]] = r

    for d in decisions:
        cid = d.get("comment_id")
        action = d.get("action")
        if action == "skip" or cid not in by_id:
            skipped += 1
            continue
        red = by_id[cid]
        if action == "accept":
            quoted = red.get("quoted_text") or ""
            final_text = (d.get("final_text") or red.get("suggested_replacement") or "").strip()
            if quoted and quoted in raw and final_text:
                raw = raw.replace(quoted, final_text, 1)
                applied += 1
            else:
                misses.append(cid)
            await db.legal_doc_comments.update_one(
                {"id": cid},
                {"$set": {
                    "resolved": True,
                    "resolved_at": now_iso(),
                    "resolved_by": user.get("email"),
                    "rejected": False,
                    "final_text": final_text,
                }},
            )
        elif action == "reject":
            rejected += 1
            await db.legal_doc_comments.update_one(
                {"id": cid},
                {"$set": {
                    "resolved": True,
                    "resolved_at": now_iso(),
                    "resolved_by": user.get("email"),
                    "rejected": True,
                }},
            )

    # Persist the working draft with the modified body. The released .md
    # is intentionally untouched — admin promotes via
    # POST /legal/working-drafts/{slug}/release.
    wd = await _upsert_working_draft(
        source_slug=source_slug,
        content_md=raw,
        user=user,
        action="apply_roundtrip",
        note=f"Roundtrip applied · +{applied} -{rejected} skipped {skipped}",
    )

    # Persist a per-doc roundtrip record so counsel can see the audit
    # trail of how their work landed (visible on /admin/legal/ratifications
    # under "Roundtrip history").
    roundtrip_rec = {
        "id": gen_id(),
        "source_slug": source_slug,
        "applied_at": now_iso(),
        "applied_by_user_id": user["id"],
        "applied_by_user_email": user.get("email"),
        "working_draft_id": wd["id"],
        "counts": {
            "applied": applied,
            "rejected": rejected,
            "skipped": skipped,
            "unmatched": len(misses),
            "total": len(decisions),
        },
        "unmatched_comment_ids": misses,
    }
    await db.legal_doc_roundtrips.insert_one(dict(roundtrip_rec))

    await log_action(
        db, user, "legal.doc.redlines.roundtrip.apply",
        target_type="legal_doc", target_id=source_slug,
        metadata={"applied": applied, "rejected": rejected, "skipped": skipped,
                  "misses": len(misses), "working_draft_id": wd["id"]},
    )

    # Best-effort email — the .docx bundle is NOT rebuilt here because
    # the released .md hasn't changed; the bundle refresh happens at
    # release time instead.
    email_id = await _email_roundtrip_summary(
        source_slug=source_slug,
        applier=user,
        counts=roundtrip_rec["counts"],
        rebuild_ok=False,  # no rebuild at roundtrip time under working-draft model
    )

    return {
        "applied": applied,
        "rejected": rejected,
        "skipped": skipped,
        "unmatched_comment_ids": misses,
        "roundtrip_id": roundtrip_rec["id"],
        "working_draft_id": wd["id"],
        "state": wd["state"],
        "email_id": email_id,
    }


async def _run_docx_rebuild(user: dict) -> bool:
    """Best-effort .docx rebuild. Kicks off the same script `rebuild-docx`
    calls but never raises — the roundtrip result is more important than
    the .docx refresh, and admin can still click the manual Rebuild
    button if something goes wrong."""
    from database import db
    import subprocess, sys
    script = Path(__file__).resolve().parent.parent / "scripts" / "eu_compliance_and_docx.py"
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


@router.get("/roundtrips/{source_slug}")
async def list_roundtrips(
    source_slug: str,
    user: dict = Depends(require_roles("admin")),
):
    """Per-doc history of every roundtrip application (newest first).

    Counsel (`readonly_admin`) inherits admin read access via
    `require_roles`, so counsel can also see how their work landed.
    """
    from database import db
    rows = await db.legal_doc_roundtrips.find(
        {"source_slug": source_slug}, {"_id": 0},
    ).sort("applied_at", -1).to_list(200)
    return rows


@router.post("/rebuild-docx")
async def rebuild_docx_bundle(user: dict = Depends(require_roles("admin"))):
    """One-click rebuild of every draft's .docx plus the combined
    LEGAL_BRIEFING_FOR_COUNSEL.docx. Called after a roundtrip is applied
    so the counsel-facing bundle downloads reflect the latest source.
    """
    from database import db
    import subprocess, sys
    script = Path(__file__).resolve().parent.parent / "scripts" / "eu_compliance_and_docx.py"
    if not script.exists():
        raise HTTPException(status_code=500, detail="Build script missing")
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(script.parent.parent),
        capture_output=True, text=True, timeout=180,
    )
    ok = proc.returncode == 0
    await log_action(
        db, user, "legal.doc.rebuild",
        target_type="legal_docs", target_id="all",
        metadata={"ok": ok, "returncode": proc.returncode},
    )
    if not ok:
        raise HTTPException(
            status_code=500,
            detail=f"Rebuild failed (rc={proc.returncode}): {proc.stderr[-400:]}",
        )
    # Return a short summary of what was regenerated.
    summary_lines = [ln for ln in proc.stdout.splitlines() if "→" in ln or "Rebuilt" in ln][-40:]
    return {"ok": True, "summary": summary_lines}

