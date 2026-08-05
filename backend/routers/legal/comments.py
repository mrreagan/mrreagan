"""routers.legal.comments — working-draft comment threads, mention
digests, public-comment API, and .docx round-trip (export/import/apply)
pipeline.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, Request

from auth_utils import get_current_user, require_roles
from models import gen_id, now_iso
from utils.audit import log_action

from ._common import (
    LEGAL_DOC_DIR,
    _strip_draft_disclaimer,
    _md_body_hash,
    _released_md,
    _active_working_draft,
    _upsert_working_draft,
    _parse_mentions,
    _send_legal_mention_digests,
    _SOURCE_TO_PUBLIC,
    _build_redline_docx,
    _extract_paragraph_text,
    _parse_roundtrip_docx,
    _email_roundtrip_summary,
    _WD_STATE_DRAFT,
    logger,
)

router = APIRouter()


# ---- list_wd_comments (was L1468-L1486) ----
@router.get("/working-drafts/{source_slug}/comments")
async def list_wd_comments(
    source_slug: str,
    user: dict = Depends(require_roles("admin")),
):
    """Return every comment (including resolved) for the open WD.

    Returns [] if no open WD exists — the diff view uses that to skip
    rendering the comments panel.
    """
    from database import db
    wd = await _active_working_draft(source_slug)
    if not wd:
        return []
    rows = await db.legal_working_draft_comments.find(
        {"working_draft_id": wd["id"]},
        {"_id": 0},
    ).sort("created_at", 1).to_list(1000)
    return rows

# ---- create_wd_comment (was L1489-L1564) ----
@router.post("/working-drafts/{source_slug}/comments")
async def create_wd_comment(
    source_slug: str,
    payload: dict,
    background: BackgroundTasks,
    user: dict = Depends(require_roles("admin")),
):
    """Post an inline comment (or reply) on the open working draft.

    Payload:
      body        (str, required)          — the comment text (max 4 KB)
      line_number (int, optional)          — anchors to a line; None = general
      side        ("released"|"working"|"general") — column context in the diff
      parent_id   (str, optional)          — if replying to another comment

    Side effect: if the body contains @admin or @counsel, emails the
    corresponding party via BackgroundTasks. Fire-and-forget — email
    failures do not break the post.
    """
    from database import db
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft to comment on.")
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Comment body required.")
    if len(body) > 4096:
        raise HTTPException(status_code=400, detail="Comment exceeds 4 KB.")

    side = payload.get("side") or "general"
    if side not in ("released", "working", "general"):
        raise HTTPException(status_code=400, detail="side must be 'released', 'working', or 'general'.")
    line_number = payload.get("line_number")
    if line_number is not None:
        try:
            line_number = int(line_number)
            if line_number < 1:
                line_number = None
        except (TypeError, ValueError):
            line_number = None

    parent_id = payload.get("parent_id")
    if parent_id:
        parent = await db.legal_working_draft_comments.find_one(
            {"id": parent_id, "working_draft_id": wd["id"]}, {"_id": 0, "id": 1},
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found on this working draft.")

    mentions = _parse_mentions(body)
    doc = {
        "id": gen_id(),
        "working_draft_id": wd["id"],
        "source_slug": source_slug,
        "line_number": line_number,
        "side": side,
        "parent_id": parent_id or None,
        "body": body,
        "mentions": mentions,
        # Digest bookkeeping — the daily job flips this to an ISO ts once
        # this mention has been included in a digest email so we don't
        # notify twice for the same mention.
        "mention_digest_sent_at": None,
        "author_id": user["id"],
        "author_email": user.get("email"),
        "author_role": user.get("role"),
        "created_at": now_iso(),
        "resolved": False,
        "resolved_at": None,
        "resolved_by_email": None,
    }
    await db.legal_working_draft_comments.insert_one(dict(doc))
    # Per-comment mention email intentionally removed — mentions now
    # roll up into a once-daily digest to prevent inbox flooding.
    # See _send_legal_mention_digests scheduler job.
    return doc

# ---- manual_mention_digest (was L1742-L1757) ----
@router.post("/admin/mention-digest/send-now")
async def manual_mention_digest(user: dict = Depends(require_roles("admin"))):
    """Manual trigger for the daily @mention digest. Useful for testing
    and for admins who want to flush the queue without waiting until the
    next scheduler tick.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can trigger the digest.")
    result = await _send_legal_mention_digests()
    from database import db
    await log_action(
        db, user, "legal.mention_digest.manual",
        target_type="legal", target_id="digest",
        metadata=result,
    )
    return result

# ---- resolve_wd_comment (was L1760-L1792) ----
@router.post("/working-drafts/{source_slug}/comments/{comment_id}/resolve")
async def resolve_wd_comment(
    source_slug: str,
    comment_id: str,
    payload: Optional[dict] = Body(default=None),
    user: dict = Depends(require_roles("admin")),
):
    """Toggle resolve/unresolve on a comment.

    Payload:
      resolved (bool, optional) — sets the state explicitly; defaults to `true`
    """
    from database import db
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft.")
    c = await db.legal_working_draft_comments.find_one(
        {"id": comment_id, "working_draft_id": wd["id"]}, {"_id": 0},
    )
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found on this working draft.")
    resolved = (payload or {}).get("resolved")
    if resolved is None:
        resolved = True
    updates = {
        "resolved": bool(resolved),
        "resolved_at": now_iso() if resolved else None,
        "resolved_by_email": user.get("email") if resolved else None,
    }
    await db.legal_working_draft_comments.update_one(
        {"id": comment_id}, {"$set": updates},
    )
    return {**c, **updates}

# ---- delete_wd_comment (was L1795-L1832) ----
@router.delete("/working-drafts/{source_slug}/comments/{comment_id}")
async def delete_wd_comment(
    source_slug: str,
    comment_id: str,
    user: dict = Depends(require_roles("admin")),
):
    """Delete a comment. Admins can delete any; counsel can only delete
    their own. Deleting a parent removes its replies too (thread cascade).
    """
    from database import db
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft.")
    c = await db.legal_working_draft_comments.find_one(
        {"id": comment_id, "working_draft_id": wd["id"]}, {"_id": 0},
    )
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found on this working draft.")
    if user.get("role") != "admin" and c.get("author_id") != user.get("id"):
        raise HTTPException(status_code=403, detail="You can only delete your own comments.")
    # Cascade to ALL descendants, not just direct children. Threads are
    # rare-but-possible deeper than one level via direct API use.
    to_delete = {comment_id}
    frontier = {comment_id}
    while frontier:
        children = await db.legal_working_draft_comments.find(
            {"working_draft_id": wd["id"], "parent_id": {"$in": list(frontier)}},
            {"id": 1, "_id": 0},
        ).to_list(1000)
        child_ids = {c["id"] for c in children} - to_delete
        if not child_ids:
            break
        to_delete |= child_ids
        frontier = child_ids
    r = await db.legal_working_draft_comments.delete_many({
        "working_draft_id": wd["id"], "id": {"$in": list(to_delete)},
    })
    return {"deleted": r.deleted_count}

# ---- list_comments (was L2088-L2097) ----
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

# ---- add_comment (was L2100-L2138) ----
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

# ---- resolve_comment (was L2141-L2162) ----
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

# ---- export_unresolved_redlines (was L2394-L2435) ----
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

# ---- import_roundtrip_preview (was L2524-L2591) ----
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

# ---- apply_roundtrip (was L2594-L2738) ----
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

# ---- list_roundtrips (was L2843-L2857) ----
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
