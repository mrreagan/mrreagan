"""routers.legal.public — public-facing legal endpoints.

Covers universal indemnification (view/sign/status/history), the
download-hub for source docs, the public rendered pages, and the
release-history / RSS feed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from auth_utils import get_current_user, require_roles
from models import IndemnificationCreate, gen_id, now_iso
from utils.audit import log_action

from ._common import (
    LEGAL_DOC_DIR,
    LEGAL_DOC_INDEX,
    DEFAULT_INDEMNIFICATION_BODY,
    PUBLIC_LEGAL_PAGES,
    _strip_draft_disclaimer,
    _md_body_hash,
    _current_ratification,
    _notify_partners_of_new_version,
    _SOURCE_TO_PUBLIC,
    logger,
)

router = APIRouter()


# ---- get_active_version (was L93-L111) ----
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

# ---- list_versions (was L114-L131) ----
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

# ---- default_v2_draft (was L134-L149) ----
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

# ---- create_version (was L152-L201) ----
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

# ---- sign_active (was L281-L330) ----
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

# ---- my_status (was L333-L387) ----
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

# ---- list_signatures (was L390-L407) ----
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

# ---- list_legal_docs (was L413-L435) ----
@router.get("/docs")
async def list_legal_docs():
    """List the static legal documents anyone can download.

    Public — the /counsel console lets any visitor download the current
    draft artefacts (briefing, public-facing policies, partner agreements,
    etc.). Admin + counsel additionally see the full working-draft
    workflow gated in the UI.
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
            "source_slug": meta.get("source_slug"),
            "size_bytes": fp.stat().st_size,
            "download_url": f"/api/legal/docs/{key}",
        })
    return out

# ---- download_legal_doc (was L438-L451) ----
@router.get("/docs/{key}")
async def download_legal_doc(key: str):
    """Stream the requested legal document as a download. Public."""
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

# ---- bulk_download_legal_docs (was L454-L503) ----
@router.get("/docs-bundle.zip")
async def bulk_download_legal_docs(
    category: Optional[str] = None,
    user: dict = Depends(require_roles("admin")),
):
    """Zip up every legal doc (optionally filtered by category) and stream
    it back. Admin + counsel (via require_roles allow-list) only — this
    is bulk offline-archiving, not a general public bulk endpoint.
    """
    import io
    import zipfile
    from datetime import datetime, timezone
    from starlette.responses import StreamingResponse

    matches = [
        (key, meta) for key, meta in LEGAL_DOC_INDEX.items()
        if not category or meta.get("category") == category
    ]
    if not matches:
        raise HTTPException(status_code=404, detail=f"No documents found for category '{category}'.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Group files under folders named after their category so unzip
        # produces a tidy `Briefing/…`, `Public-facing/…` layout.
        for key, meta in matches:
            fp = LEGAL_DOC_DIR / meta["filename"]
            if not fp.exists():
                continue
            folder = (meta.get("category") or "Other").replace("/", "-").strip()
            zf.write(fp, arcname=f"{folder}/{meta['display_name']}")
        # Include a small manifest.txt so archivers know when this was pulled.
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        zf.writestr(
            "README.txt",
            f"Birthright Foundation legal-docs bundle\n"
            f"Generated: {stamp} UTC\n"
            f"Category filter: {category or '(all)'}\n"
            f"Files: {len(matches)}\n"
            f"Pulled by: {user.get('email')} ({user.get('role')})\n",
        )
    buf.seek(0)

    fname_slug = (category or "all").lower().replace(" ", "-").replace("/", "-").strip("-")
    filename = f"birthright-legal-docs-{fname_slug}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# ---- public_draft (was L506-L531) ----
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

# ---- list_public_pages (was L631-L640) ----
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

# ---- get_public_page (was L643-L695) ----
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

# ---- list_ratifications (was L718-L725) ----
@router.get("/ratifications")
async def list_ratifications(user: dict = Depends(require_roles("admin"))):
    """Admin — every ratification record, newest first."""
    from database import db
    rows = await db.legal_doc_ratifications.find(
        {}, {"_id": 0}
    ).sort("ratified_at", -1).to_list(500)
    return rows

# ---- public_ratification_history (was L2181-L2204) ----
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

# ---- public_ratification_rss (was L2207-L2274) ----
@router.get("/history.rss")
async def public_ratification_rss(request: Request):
    """Public RSS 2.0 feed of ratifications for partners + press to
    subscribe. Uses the site's REACT_APP_BACKEND_URL / current host as
    the item permalink base so feed readers de-dupe cleanly.
    """
    from database import db
    from fastapi.responses import Response
    from xml.sax.saxutils import escape as _esc

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
