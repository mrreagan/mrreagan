"""routers.legal — legal / counsel-console endpoints, split into
public, working_drafts, and comments sub-routers.

`server.py` and other callers import `router` from here. Tests and
`utils.scheduler` also import the shared helpers exposed at the top
level (`_strip_draft_disclaimer`, `_bump_minor`,
`_send_legal_mention_digests`, `DEFAULT_INDEMNIFICATION_BODY`).
"""
from __future__ import annotations

from fastapi import APIRouter

from . import _common as _common
from . import public as _public
from . import working_drafts as _working_drafts
from . import comments as _comments

# Re-export shared helpers/constants that external callers use directly.
from ._common import (  # noqa: F401  (public API surface)
    LEGAL_DOC_DIR,
    LEGAL_DOC_INDEX,
    DEFAULT_INDEMNIFICATION_BODY,
    PUBLIC_LEGAL_PAGES,
    _MID_DOC_DRAFT_BOILERPLATE_RE,
    _strip_draft_disclaimer,
    _bump_minor,
    _next_version,
    _released_md,
    _active_working_draft,
    _upsert_working_draft,
    _current_ratification,
    _md_body_hash,
    _docx_to_markdown,
    _email_working_draft_ready,
    _email_roundtrip_summary,
    _send_legal_mention_digests,
    _parse_mentions,
    _summarise_wd_change_log,
    _build_redline_docx,
    _run_docx_rebuild,
    _SOURCE_TO_PUBLIC,
    _WD_STATE_DRAFT,
    _WD_STATE_READY,
    _WD_STATE_RELEASED,
    _WD_STATE_DISCARDED,
)

router = APIRouter(prefix="/legal", tags=["legal"])
router.include_router(_public.router)
router.include_router(_working_drafts.router)
router.include_router(_comments.router)
