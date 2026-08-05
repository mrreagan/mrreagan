"""routers.legal.working_drafts — counsel working-draft workflow.

Covers /docs/{slug}/upload, /working-drafts/*, /ratifications write ops,
release history timeline, rollback preview + execution, and admin docx
rebuild trigger.
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
    LEGAL_DOC_INDEX,
    _strip_draft_disclaimer,
    _md_body_hash,
    _current_ratification,
    _docx_to_markdown,
    _released_md,
    _active_working_draft,
    _upsert_working_draft,
    _bump_minor,
    _next_version,
    _email_working_draft_ready,
    _summarise_wd_change_log,
    _WD_STATE_DRAFT,
    _WD_STATE_READY,
    _WD_STATE_RELEASED,
    _WD_STATE_DISCARDED,
    _run_docx_rebuild,
    logger,
)

router = APIRouter()


# ---- add_ratification (was L728-L769) ----
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

# ---- revoke_ratification (was L772-L785) ----
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

# ---- upload_full_replacement (was L797-L883) ----
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

# ---- list_working_drafts (was L1078-L1109) ----
@router.get("/working-drafts")
async def list_working_drafts(user: dict = Depends(require_roles("admin"))):
    """List every OPEN working draft (state ∈ {draft, awaiting_admin}).

    Counsel (`readonly_admin`) can also read this via the shared
    `require_roles('admin')` allow-list — the counsel console renders
    from this endpoint. Each row carries a `comment_stats` field so the
    console can show a "N open comments" badge without a second call.
    """
    from database import db
    rows = await db.legal_doc_working_drafts.find(
        {"state": {"$in": [_WD_STATE_DRAFT, _WD_STATE_READY]}},
        {"_id": 0, "content_md": 0},   # skip body for list view
    ).sort("last_edited_at", -1).to_list(200)

    # Bulk-count comments per working draft in one aggregate query.
    ids = [r["id"] for r in rows]
    stats: dict[str, dict] = {i: {"total": 0, "open": 0} for i in ids}
    if ids:
        pipeline = [
            {"$match": {"working_draft_id": {"$in": ids}}},
            {"$group": {
                "_id": "$working_draft_id",
                "total": {"$sum": 1},
                "open": {"$sum": {"$cond": [{"$eq": ["$resolved", False]}, 1, 0]}},
            }},
        ]
        async for agg in db.legal_working_draft_comments.aggregate(pipeline):
            stats[agg["_id"]] = {"total": agg["total"], "open": agg["open"]}
    for row in rows:
        row["comment_stats"] = stats.get(row["id"], {"total": 0, "open": 0})
    return rows

# ---- get_working_draft (was L1112-L1140) ----
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
    released_md_raw = _released_md(source_slug)
    # Strip the auto-injected disclaimer from BOTH sides before returning.
    # These blocks are rewritten by the DOCX-rebuild pipeline every
    # release, so leaving them in the diff produces a huge spurious
    # "+135 / -45" difference for what may only be a one-word counsel
    # edit. body_hash is still computed on the stripped content so
    # `is_stale` stays consistent with `base_released_hash` (which is
    # written at draft-creation time on the strip-only content).
    released_md_stripped, _ = _strip_draft_disclaimer(released_md_raw)
    working_md_stripped, _ = _strip_draft_disclaimer(wd.get("content_md") or "")
    released_hash = _md_body_hash(released_md_stripped)

    # Cosmetic-whitespace + soft-wrap normalisation for the diff view
    # only. Strips trailing whitespace per line, collapses runs of 2+
    # internal spaces to 1, and — critically — UNWRAPS soft-wrapped
    # paragraphs and multi-line bullets so hard-wrap column drift
    # doesn't produce false-positive diff hunks. Source .md files on
    # disk are untouched.
    def _diff_normalise(md: str) -> str:
        import re as _re
        # Pass 1: rstrip + collapse internal double-spaces.
        raw = [_re.sub(r" {2,}", " ", ln.rstrip()) for ln in md.splitlines()]

        def _line_kind(ln: str) -> str:
            s = ln.lstrip()
            if not s: return "blank"
            if s.startswith("#"): return "heading"
            if s.startswith("|"): return "table"
            if s.startswith("---"): return "hr"
            if s.startswith("> "): return "blockquote"
            if s.startswith("- ") or _re.match(r"^\d+\.\s", s): return "list"
            return "para"

        def _canon_table_sep(ln: str) -> str:
            """Canonicalize a `| --- | --- |` separator row so 3-dash vs
            20-dash cell width doesn't register as a diff."""
            if not ln.strip().startswith("|"):
                return ln
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if cells and all(_re.fullmatch(r":?-+:?", c or "") for c in cells):
                return "| " + " | ".join(["---"] * len(cells)) + " |"
            return ln

        def _join_wrapped(parts):
            merged = parts[0]
            for nxt in parts[1:]:
                nxt_s = nxt.strip()
                if not nxt_s: continue
                # If merged ends with `-` and next starts lowercase, treat
                # as an intra-word soft wrap and join without a space
                # (`print-on-\n  demand` → `print-on-demand`). Otherwise
                # keep the trailing char and space-separate.
                if merged.endswith("-") and nxt_s and nxt_s[0].islower():
                    merged = merged + nxt_s
                else:
                    merged = merged.rstrip() + " " + nxt_s
            return merged

        out: list[str] = []
        i = 0
        while i < len(raw):
            k = _line_kind(raw[i])
            if k == "blank":
                out.append("")
                i += 1
                continue
            # Collect a run of consecutive lines of the SAME kind (blank
            # boundary OR kind change breaks the run).
            if k == "list":
                items, cur = [], []
                while i < len(raw):
                    lk = _line_kind(raw[i])
                    if lk == "list":
                        if cur:
                            items.append(cur)
                        cur = [raw[i].lstrip()]
                        i += 1
                    elif lk == "para" and cur:
                        # Continuation of the current bullet.
                        cur.append(raw[i])
                        i += 1
                    else:
                        break
                if cur:
                    items.append(cur)
                for it in items:
                    out.append(_join_wrapped(it))
            elif k == "para":
                block = []
                while i < len(raw) and _line_kind(raw[i]) == "para":
                    block.append(raw[i]); i += 1
                out.append(_join_wrapped(block))
            elif k in ("heading", "hr", "blockquote"):
                out.append(raw[i]); i += 1
            elif k == "table":
                while i < len(raw) and _line_kind(raw[i]) == "table":
                    out.append(_canon_table_sep(raw[i])); i += 1
            else:
                out.append(raw[i]); i += 1

        cleaned = _re.sub(r"\n{3,}", "\n\n", "\n".join(out))
        # Remove the blank line between a heading and its immediately-
        # following content — both sides should read as
        # `## Heading\ncontent`, not `## Heading\n\ncontent`. Purely
        # cosmetic drift from the docx round-trip.
        cleaned = _re.sub(r"(?m)^(#{1,6} .+)\n\n(?=\S)", r"\1\n", cleaned)
        # Also remove the blank line between a paragraph ending in `:`
        # and a following bullet — source docs write these as a
        # continuous list; the docx round-trip inserts a paragraph
        # break. Same normalisation on both sides.
        cleaned = _re.sub(r"(?m)^(.+:)\n\n(?=[-*] )", r"\1\n", cleaned)
        return cleaned.strip() + "\n"

    # Apply diff-view normalisation on separate display fields so the
    # raw `content_md` / `released_md` still match storage exactly.
    return {
        **wd,
        # Raw stripped bodies — match storage; DiffModal now reads the
        # `*_diff` copies below for cosmetic parity across sides.
        "content_md": working_md_stripped,
        "released_md": released_md_stripped,
        # Normalised copies (paragraphs unwrapped, table separators
        # canonicalized, heading-blank collapsed, intra-word hyphens
        # rejoined) so the frontend diff view doesn't trip over
        # cosmetic drift on identical uploads.
        "content_md_diff": _diff_normalise(working_md_stripped),
        "released_md_diff": _diff_normalise(released_md_stripped),
        "released_body_hash": released_hash,
        "is_stale": wd.get("base_released_hash") != released_hash,
    }

# ---- download_working_draft (was L1143-L1188) ----
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

# ---- mark_ready (was L1191-L1248) ----
@router.post("/working-drafts/{source_slug}/mark-ready")
async def mark_ready(
    source_slug: str,
    background: BackgroundTasks,
    user: dict = Depends(require_roles("admin")),
):
    """Counsel signals the working draft is ready for admin review.

    Side effect: emails every user with `role=admin` so a release never
    sits waiting on a stale dashboard. Sent inline (not via
    BackgroundTasks) so we can (a) return the underlying `email_id` for
    UI/receipt display and (b) guarantee the recipient fanout reflects
    the admin roster at the moment counsel clicked (not whenever the
    BG worker got around to it). The mailer has a dry-run mode and its
    own try/except, so a Resend outage still returns 200. Idempotent:
    marking ready twice in a row is a no-op on the email (returns
    email_scheduled=False the second time).
    """
    from database import db
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft.")
    already_ready = wd.get("state") == _WD_STATE_READY
    now = now_iso()
    change_log = list(wd.get("change_log") or [])
    change_log.append({
        "at": now,
        "by_user_id": user["id"],
        "by_email": user.get("email"),
        "by_role": user.get("role"),
        "action": "mark_ready",
        "note": "Marked ready for admin review" + (" (repeat)" if already_ready else ""),
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
        metadata={"working_draft_id": wd["id"], "repeat": already_ready},
    )
    scheduled = False
    email_id: Optional[str] = None
    if not already_ready:
        # Send inline so the response carries the email_id and the
        # recipient list reflects the current admin roster.
        email_id = await _email_working_draft_ready(source_slug, wd, user)
        scheduled = True
    return {
        "state": _WD_STATE_READY,
        "working_draft_id": wd["id"],
        "email_scheduled": scheduled,
        "email_id": email_id,
    }

# ---- release_working_draft (was L1313-L1417) ----
@router.post("/working-drafts/{source_slug}/release")
async def release_working_draft(
    source_slug: str,
    payload: Optional[dict] = Body(default=None),
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

    # Rebuild first — the rebuild script appends the EU/UK compliance
    # addendum to the .md before generating the .docx bundle, so we must
    # hash the FINAL on-disk content (post-rebuild) or the ratification
    # body_hash won't match what the public page renders.
    rebuild_ok = await _run_docx_rebuild(user=user)
    final_md = fp.read_text(encoding="utf-8")
    cleaned, _ = _strip_draft_disclaimer(final_md)
    body_hash = _md_body_hash(cleaned)

    version = ((payload or {}).get("version") or "").strip() or await _next_version(source_slug)
    ratified_by = ((payload or {}).get("ratified_by") or "").strip() or user.get("email") or "admin"
    notes = ((payload or {}).get("notes") or "").strip() or f"Released working draft {wd['id']}"

    # Compute change summary from the working draft's change_log so the
    # history timeline can show at-a-glance "5 edits by counsel@" summaries
    # without having to reload every WD row.
    change_summary = _summarise_wd_change_log(wd.get("change_log") or [])

    rat = {
        "id": gen_id(),
        "source_slug": source_slug,
        "version": version,
        "body_hash": body_hash,
        # Snapshot the final on-disk .md so admins can rollback later.
        # Also stores the pre-addendum content_md so a rollback restores
        # counsel-authored text (the addendum will be re-appended by the
        # rebuild step during rollback).
        "content_md_snapshot": final_md,
        "notes": notes,
        "ratified_by": ratified_by,
        "ratified_at": now_iso(),
        "ratified_by_user_id": user["id"],
        "ratified_by_user_email": user.get("email"),
        "released_from_working_draft_id": wd["id"],
        "change_summary": change_summary,
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

# ---- discard_working_draft (was L1420-L1460) ----
@router.post("/working-drafts/{source_slug}/discard")
async def discard_working_draft(
    source_slug: str,
    payload: Optional[dict] = Body(default=None),
    user: dict = Depends(require_roles("admin")),
):
    """ADMIN — throw away the working draft. Released .md is untouched."""
    from database import db
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can discard a working draft.")
    wd = await _active_working_draft(source_slug)
    if not wd:
        raise HTTPException(status_code=404, detail="No open working draft to discard.")
    reason = ((payload or {}).get("reason") or "").strip() or "no reason given"
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

# ---- history_timeline (was L1866-L1909) ----
@router.get("/history-timeline/{source_slug}")
async def history_timeline(
    source_slug: str,
    limit: int = Query(default=5, ge=1, le=50),
    user: dict = Depends(require_roles("admin")),
):
    """Release history for one doc.

    Returns the newest `limit` versions (default 5), the total count, and
    the current released version + body_hash. Each version carries its
    change_summary and a `can_rollback` flag (false for legacy
    ratifications that don't have a content snapshot).
    """
    from database import db
    total = await db.legal_doc_ratifications.count_documents({"source_slug": source_slug})
    # Secondary sort by id so releases minted in the same clock tick
    # (or with a caller-supplied ratified_at) order deterministically.
    latest = await db.legal_doc_ratifications.find(
        {"source_slug": source_slug},
        {"_id": 0, "content_md_snapshot": 0},
    ).sort([("ratified_at", -1), ("id", -1)]).to_list(limit)

    # Only check the rows we're returning for snapshot presence — bounded
    # to len(latest), not the full history of this slug.
    page_ids = [r["id"] for r in latest]
    ids_with_snapshot = set()
    if page_ids:
        async for r in db.legal_doc_ratifications.find(
            {"id": {"$in": page_ids},
             "content_md_snapshot": {"$exists": True, "$ne": None}},
            {"id": 1, "_id": 0},
        ):
            ids_with_snapshot.add(r["id"])
    for row in latest:
        row["can_rollback"] = row["id"] in ids_with_snapshot

    current = latest[0] if latest else None
    return {
        "source_slug": source_slug,
        "total_versions": total,
        "current_version": current.get("version") if current else None,
        "current_body_hash": current.get("body_hash") if current else None,
        "versions": latest,
    }

# ---- rollback_preview (was L1912-L1953) ----
@router.get("/history/{source_slug}/rollback-preview/{ratification_id}")
async def rollback_preview(
    source_slug: str,
    ratification_id: str,
    user: dict = Depends(require_roles("admin")),
):
    """Return the target ratification's snapshot alongside the current
    on-disk `.md` so the UI can diff them before an admin confirms a
    rollback. Admin-only via `require_roles('admin')` allow-list; the
    body is text-only, no side effects.
    """
    from database import db
    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")
    target = await db.legal_doc_ratifications.find_one(
        {"id": ratification_id, "source_slug": source_slug}, {"_id": 0},
    )
    if not target:
        raise HTTPException(status_code=404, detail="Ratification not found for this slug.")
    snapshot = target.get("content_md_snapshot")
    if not snapshot:
        raise HTTPException(
            status_code=400,
            detail="This version has no content snapshot — rollback is not possible.",
        )
    current_md = fp.read_text(encoding="utf-8")
    # Find the current ratification to expose its version for the header.
    current = await db.legal_doc_ratifications.find_one(
        {"source_slug": source_slug}, {"_id": 0, "version": 1, "ratified_at": 1, "ratified_by": 1},
        sort=[("ratified_at", -1), ("id", -1)],
    )
    return {
        "source_slug": source_slug,
        "target_version": target.get("version"),
        "target_ratified_at": target.get("ratified_at"),
        "target_ratified_by": target.get("ratified_by"),
        "target_md": snapshot,
        "current_version": (current or {}).get("version"),
        "current_ratified_at": (current or {}).get("ratified_at"),
        "current_md": current_md,
    }

# ---- rollback_to_version (was L1956-L2080) ----
@router.post("/history/{source_slug}/rollback/{ratification_id}")
async def rollback_to_version(
    source_slug: str,
    ratification_id: str,
    payload: Optional[dict] = Body(default=None),
    user: dict = Depends(require_roles("admin")),
):
    """ADMIN — restore a past ratification as a NEW release.

    Steps:
      1. Load the target ratification's `content_md_snapshot`
      2. Write to /legal_docs/<slug>.md
      3. Rebuild the .docx bundle
      4. Create a new ratification with an auto-bumped minor version
         (or `payload.version` override) and notes flagging the rollback
      5. Any open working draft is discarded (releasing invalidates WIP)

    The original ratification stays in history — this is an additive
    restore, not a delete.
    """
    from database import db
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can rollback.")

    fp = LEGAL_DOC_DIR / f"{source_slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Unknown source doc")

    target = await db.legal_doc_ratifications.find_one(
        {"id": ratification_id, "source_slug": source_slug}, {"_id": 0},
    )
    if not target:
        raise HTTPException(status_code=404, detail="Ratification not found for this slug.")
    snapshot = target.get("content_md_snapshot")
    if not snapshot:
        raise HTTPException(
            status_code=400,
            detail="This version has no content snapshot — rollback is not possible.",
        )

    fp.write_text(snapshot, encoding="utf-8")
    rebuild_ok = await _run_docx_rebuild(user=user)
    final_md = fp.read_text(encoding="utf-8")
    cleaned, _ = _strip_draft_disclaimer(final_md)
    body_hash = _md_body_hash(cleaned)

    version = ((payload or {}).get("version") or "").strip() or await _next_version(source_slug)
    reason = ((payload or {}).get("reason") or "").strip()
    # Localise the target's ratified_at to a friendly date for the notes
    # line — the raw ISO string looked out-of-place next to the rest of
    # the counsel console dates.
    try:
        from datetime import datetime
        ratified_str = datetime.fromisoformat(str(target.get("ratified_at")).replace("Z", "+00:00")).strftime("%b %d %Y")
    except Exception:
        ratified_str = str(target.get("ratified_at"))
    notes = (
        f"Rollback to v{target.get('version')} · originally ratified "
        f"{ratified_str} by {target.get('ratified_by')}."
        + (f" Reason: {reason}" if reason else "")
    )

    rat = {
        "id": gen_id(),
        "source_slug": source_slug,
        "version": version,
        "body_hash": body_hash,
        "content_md_snapshot": final_md,
        "notes": notes,
        "ratified_by": user.get("email") or "admin",
        "ratified_at": now_iso(),
        "ratified_by_user_id": user["id"],
        "ratified_by_user_email": user.get("email"),
        "rolled_back_from_ratification_id": ratification_id,
        "change_summary": {
            "edits": 0,
            "authors": [user.get("email")],
            "actions": {"rollback": 1},
            "rolled_back_from_version": target.get("version"),
        },
    }
    await db.legal_doc_ratifications.insert_one(dict(rat))

    # Discard any open working draft so it doesn't stealth-overwrite the
    # rollback next time counsel edits.
    wd = await _active_working_draft(source_slug)
    if wd:
        wd_now = now_iso()
        wd_log = list(wd.get("change_log") or [])
        wd_log.append({
            "at": wd_now,
            "by_user_id": user["id"],
            "by_email": user.get("email"),
            "by_role": "admin",
            "action": "discard",
            "note": f"Auto-discarded during rollback to v{target.get('version')}"
                    + (f" · reason: {reason}" if reason else ""),
            "bytes": len((wd.get("content_md") or "").encode("utf-8")),
        })
        await db.legal_doc_working_drafts.update_one(
            {"id": wd["id"]},
            {"$set": {
                "state": _WD_STATE_DISCARDED,
                "discarded_at": wd_now,
                "discarded_by_email": user.get("email"),
                "discard_reason": f"Rollback to v{target.get('version')}",
                "change_log": wd_log,
            }},
        )

    await log_action(
        db, user, "legal.doc.history.rollback",
        target_type="legal_doc", target_id=source_slug,
        metadata={"rolled_back_from": ratification_id,
                  "from_version": target.get("version"),
                  "new_version": version,
                  "rebuilt": rebuild_ok},
    )
    return {
        "ratification_id": rat["id"],
        "version": version,
        "rolled_back_from_version": target.get("version"),
        "rebuilt_docx": rebuild_ok,
        "working_draft_discarded": bool(wd),
    }

# ---- rebuild_docx_bundle (was L2860-L2889) ----
@router.post("/rebuild-docx")
async def rebuild_docx_bundle(user: dict = Depends(require_roles("admin"))):
    """One-click rebuild of every draft's .docx plus the combined
    LEGAL_BRIEFING_FOR_COUNSEL.docx. Called after a roundtrip is applied
    so the counsel-facing bundle downloads reflect the latest source.
    """
    from database import db
    import subprocess, sys
    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "eu_compliance_and_docx.py"
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
