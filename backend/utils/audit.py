"""Append-only audit log for governance, admin, and legal actions.

Every state-changing governance/admin/legal action calls `log_action()` so the
ombudsman and admins have a tamper-evident trail. We never update or delete
entries from this collection — only append.
"""
from __future__ import annotations

import logging
from typing import Optional

from models import gen_id, now_iso

logger = logging.getLogger("birthright.audit")


async def log_action(
    db,
    actor: Optional[dict],
    action: str,
    *,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> str:
    """Append an audit entry. Returns the entry id.

    actor: the user dict performing the action (None for system actions).
    action: dotted string e.g. 'governance.proposal.create'.
    target_type / target_id: optional reference to the affected resource.
    metadata: free-form contextual dict (small; do not log secrets/PII).
    """
    entry = {
        "id": gen_id(),
        "actor_id": (actor or {}).get("id"),
        "actor_role": (actor or {}).get("role"),
        "actor_name": (
            f"{actor.get('first_name','')} {actor.get('last_name','')}".strip()
            if actor else None
        ) or None,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "metadata": metadata or {},
        "created_at": now_iso(),
    }
    try:
        await db.audit_log.insert_one(entry)
    except Exception as e:  # never let audit failure break the action
        logger.error(f"audit log insert failed for action={action}: {e}")
    return entry["id"]
