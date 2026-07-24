"""Cron-like background scheduler for time-based notifications.

Runs on FastAPI startup. Currently scheduled jobs:
- workshop_reminders: every hour, send 24h-before reminders to paid attendees who haven't been reminded yet.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.mailer import send_email
from utils.email_templates import workshop_reminder

logger = logging.getLogger("birthright.scheduler")
_scheduler: AsyncIOScheduler | None = None


async def _send_workshop_reminders() -> None:
    """Find workshops starting in 24-25h and email each not-yet-reminded paid registrant."""
    from database import db
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=23, minutes=30)
    window_end = now + timedelta(hours=24, minutes=30)

    workshops = await db.workshops.find(
        {
            "status": {"$in": ["upcoming", "in_progress"]},
            "start_date": {
                "$gte": window_start.isoformat(),
                "$lte": window_end.isoformat(),
            },
        },
        {"_id": 0},
    ).to_list(100)

    if not workshops:
        return

    app_url = os.environ.get("PUBLIC_APP_URL", "https://birthright.live")
    sent = 0
    for w in workshops:
        regs = await db.registrations.find(
            {"workshop_id": w["id"], "payment_status": "paid", "reminder_sent": {"$ne": True}},
            {"_id": 0},
        ).to_list(500)
        for r in regs:
            user = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "password_hash": 0})
            if not (user and user.get("email")):
                continue
            try:
                subject, html, text = workshop_reminder(
                    first_name=user["first_name"], workshop=w,
                    check_in_code=w.get("check_in_code", "—"), app_url=app_url,
                )
                await send_email(
                    to=user["email"], subject=subject, html=html, text=text,
                    template_name="workshop_reminder",
                    metadata={"workshop_id": w["id"], "registration_id": r["id"]},
                )
                await db.registrations.update_one(
                    {"id": r["id"]}, {"$set": {"reminder_sent": True, "reminder_sent_at": datetime.now(timezone.utc).isoformat()}}
                )
                sent += 1
            except Exception as e:
                logger.error(f"reminder send failed for reg {r['id']}: {e}")
    if sent:
        logger.info(f"workshop reminders sent: {sent}")


async def _degrade_stale_sponsors():
    from database import db
    try:
        from utils.sponsor_partner import degrade_stale_sponsors
        count = await degrade_stale_sponsors(db)
        if count:
            logger.info(f"sponsor_partner_maintenance: degraded {count}")
    except Exception as e:
        logger.error(f"sponsor_partner_maintenance error: {e}")


def start_scheduler() -> None:
    """Idempotent scheduler start. Safe to call from FastAPI startup."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(_send_workshop_reminders, "interval", minutes=30, id="workshop_reminders", coalesce=True, max_instances=1)
    _scheduler.add_job(_degrade_stale_sponsors, "interval", hours=24, id="sponsor_partner_maintenance", coalesce=True, max_instances=1)
    _scheduler.start()
    logger.info("scheduler started (workshop_reminders every 30m; sponsor_partner_maintenance every 24h)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
