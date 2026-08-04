"""Legal: versioned universal indemnification + signature tracking.

Anyone authenticated can view the active version and sign it. Admin can publish
new versions; activating a new version automatically deactivates prior ones and
updates the global_defaults pointer. Signatures are append-only and tied to a
specific version, so we have evidence of WHAT each user signed.
"""
from __future__ import annotations

import logging
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

