"""Outbound email via Resend, with a dry-run fallback that queues emails to MongoDB.

The fallback exists so the application can run (and devs can see what would be sent)
even before a real RESEND_API_KEY is configured. To enable real sending:

    RESEND_API_KEY=re_xxx
    SENDER_EMAIL=hello@birthright.live   (must be a Resend-verified sender)
    REPLY_TO_EMAIL=support@birthright.live
    EMAIL_DRY_RUN=false

All sends are recorded in `db.email_log` (sent) or `db.outbound_emails` (dry-run queued)
for inspection from the admin UI.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Optional, Iterable

import resend
from database import db
from models import gen_id, now_iso

logger = logging.getLogger("birthright.mailer")


def _is_real_send_enabled() -> bool:
    """Real send is enabled only when EMAIL_DRY_RUN is not 'true' AND a key is present."""
    if (os.environ.get("EMAIL_DRY_RUN", "true").lower() == "true"):
        return False
    key = os.environ.get("RESEND_API_KEY", "")
    return bool(key and key.startswith("re_"))


async def send_email(
    to: str | Iterable[str],
    subject: str,
    html: str,
    text: Optional[str] = None,
    reply_to: Optional[str] = None,
    attachments: Optional[list[dict]] = None,
    template_name: str = "generic",
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """Send (or dry-run-queue) one transactional email.

    Args:
        to: single email address or iterable of addresses
        subject: subject line
        html: HTML body (inline CSS only — see email clients limitations)
        text: optional plaintext alt body
        reply_to: optional reply-to override (defaults to REPLY_TO_EMAIL)
        attachments: list of {"filename": str, "content": base64-str, "content_type": str}
        template_name: short label recorded in email_log for analytics
        metadata: optional dict persisted with the log entry

    Returns:
        Resend email id on real send, generated id on dry-run, or None on hard failure.
    """
    recipients = [to] if isinstance(to, str) else list(to)
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
    reply = reply_to or os.environ.get("REPLY_TO_EMAIL") or sender

    log_doc = {
        "id": gen_id(),
        "to": recipients,
        "from": sender,
        "reply_to": reply,
        "subject": subject,
        "template": template_name,
        "metadata": metadata or {},
        "created_at": now_iso(),
    }

    if not _is_real_send_enabled():
        # Queue locally for later replay + visibility
        log_doc.update({
            "status": "queued_dry_run",
            "html_preview": html[:500],
            "text_preview": (text or "")[:500],
            "has_attachments": bool(attachments),
        })
        await db.outbound_emails.insert_one(log_doc)
        logger.info(f"[DRY-RUN] queued email '{subject}' -> {recipients} (id={log_doc['id']})")
        return log_doc["id"]

    # Real send via Resend
    resend.api_key = os.environ["RESEND_API_KEY"]
    params: dict = {
        "from": sender,
        "to": recipients,
        "subject": subject,
        "html": html,
        "reply_to": reply,
    }
    if text:
        params["text"] = text
    if attachments:
        params["attachments"] = attachments

    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        email_id = (result or {}).get("id")
        log_doc.update({"status": "sent", "email_id": email_id})
        await db.email_log.insert_one(log_doc)
        logger.info(f"sent email '{subject}' -> {recipients} (resend_id={email_id})")
        return email_id
    except Exception as e:
        log_doc.update({"status": "failed", "error": str(e)})
        await db.email_log.insert_one(log_doc)
        logger.error(f"FAILED email '{subject}' -> {recipients}: {e}")
        return None


def attachment_from_bytes(filename: str, raw: bytes, content_type: str) -> dict:
    """Build a Resend-format attachment payload from raw bytes."""
    return {
        "filename": filename,
        "content": base64.b64encode(raw).decode("ascii"),
        "content_type": content_type,
    }
