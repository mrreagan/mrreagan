"""Pledge notification emails for sponsor campaigns.

Three touchpoints:
  1. On pledge submission → confirm to sponsor + notify admin(s).
  2. On admin mark "invoiced" → send invoice/payment-instructions to sponsor.
  3. On admin mark "paid" → send business receipt (with legal disclosure).

All use `utils.mailer.send_email` which safely dry-runs to `db.outbound_emails`
if `EMAIL_DRY_RUN=true` or the Resend key isn't set. Payment methods are
configurable via env vars so the ops team can update them without a code change.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from utils.mailer import send_email

logger = logging.getLogger("birthright.campaigns.notify")


def _admin_recipients() -> list[str]:
    raw = os.environ.get("CAMPAIGN_ADMIN_NOTIFY", "") or os.environ.get("ADMIN_NOTIFY_EMAIL", "")
    return [e.strip() for e in raw.split(",") if e.strip()]


def _payment_options_html() -> str:
    """Payment method block for sponsor invoice emails. Env-driven so ops can update."""
    stripe_link = os.environ.get("SPONSOR_PAY_STRIPE_LINK", "")
    zelle = os.environ.get("SPONSOR_PAY_ZELLE", "")
    wire = os.environ.get("SPONSOR_PAY_WIRE_INFO", "")
    ach = os.environ.get("SPONSOR_PAY_ACH_INFO", "")
    check_addr = os.environ.get("SPONSOR_PAY_CHECK_ADDRESS", "")
    parts: list[str] = []
    if stripe_link:
        parts.append(
            f'<p style="margin:0 0 10px"><strong>Pay by card / bank (recommended):</strong><br>'
            f'<a href="{stripe_link}" style="color:#476B6B">{stripe_link}</a></p>'
        )
    if zelle:
        parts.append(f'<p style="margin:0 0 10px"><strong>Zelle:</strong> {zelle}</p>')
    if ach:
        parts.append(f'<p style="margin:0 0 10px"><strong>ACH:</strong> {ach}</p>')
    if wire:
        parts.append(f'<p style="margin:0 0 10px"><strong>Wire:</strong> {wire}</p>')
    if check_addr:
        parts.append(
            f'<p style="margin:0 0 10px"><strong>Check (payable to Birthright Foundation):</strong><br>'
            f'{check_addr}</p>'
        )
    if not parts:
        parts.append(
            '<p style="margin:0 0 10px;color:#8B4513"><em>Payment instructions will follow '
            'by separate email from the Birthright team.</em></p>'
        )
    return "\n".join(parts)


def _sponsor_confirm_html(pledge: dict, campaign: dict) -> str:
    tier_line = ""
    if pledge.get("tier_snapshot"):
        t = pledge["tier_snapshot"]
        tier_line = f'<p style="margin:0 0 8px"><strong>Tier:</strong> {t.get("name")} — ${t.get("amount"):,.0f}</p>'
    return f"""
<div style="font-family:Georgia,serif;color:#1A2424;max-width:600px">
  <h2 style="font-size:22px;margin:0 0 12px">Thank you, {pledge['sponsor_name']}.</h2>
  <p>We've received your pledge to sponsor <strong>{campaign['title']}</strong>. Someone from
  the Birthright team will follow up personally within the next 3 business days to confirm
  details and send you an invoice with payment options.</p>

  <div style="background:#F4F1EA;padding:16px;border-radius:8px;margin:20px 0">
    <p style="margin:0 0 8px"><strong>Campaign:</strong> {campaign['title']}</p>
    <p style="margin:0 0 8px"><strong>Pledge amount:</strong> ${pledge['amount']:,.2f}</p>
    {tier_line}
    {f'<p style="margin:0 0 8px"><strong>Organization:</strong> {pledge["organization"]}</p>' if pledge.get('organization') else ''}
    {f'<p style="margin:0 0 8px"><strong>Public listing:</strong> {"Yes — I want to be named" if pledge.get("display_publicly") else "Anonymous"}</p>'}
    {f'<p style="margin:0 0 0"><strong>Your message:</strong> <em>{pledge["message"]}</em></p>' if pledge.get('message') else ''}
  </div>

  <div style="background:#FBF3E4;border:1px solid #E5D7B3;padding:12px;border-radius:6px;font-size:12px;color:#5C6B6B;margin:20px 0">
    <strong style="color:#8B4513">Not currently tax-deductible.</strong> Birthright Foundation
    has not yet submitted or received IRS 501(c)(3) determination. Your sponsorship will be
    receipted as a business contribution only. No representation is made about future tax status.
  </div>

  <p style="margin:20px 0 0">If any details are wrong, reply to this email and we'll fix them.</p>
  <p style="margin:20px 0 0">— The Birthright Foundation team</p>
</div>
""".strip()


def _admin_alert_html(pledge: dict, campaign: dict) -> str:
    tier_line = ""
    if pledge.get("tier_snapshot"):
        t = pledge["tier_snapshot"]
        tier_line = f"<p><strong>Tier:</strong> {t.get('name')} — ${t.get('amount'):,.0f}</p>"
    admin_link = os.environ.get("PUBLIC_APP_URL", "").rstrip("/") + "/admin/campaigns"
    return f"""
<div style="font-family:Arial,sans-serif;color:#1A2424;max-width:600px">
  <h2>New sponsor pledge — {campaign['title']}</h2>
  <p><strong>Sponsor:</strong> {pledge['sponsor_name']} &lt;{pledge['sponsor_email']}&gt;</p>
  {f"<p><strong>Organization:</strong> {pledge['organization']}</p>" if pledge.get('organization') else ''}
  <p><strong>Amount:</strong> ${pledge['amount']:,.2f}</p>
  {tier_line}
  <p><strong>Public listing:</strong> {'Yes' if pledge.get('display_publicly') else 'No (anonymous)'}</p>
  {f"<p><strong>Message:</strong> {pledge['message']}</p>" if pledge.get('message') else ''}
  <p><strong>Status:</strong> pending — awaiting your review.</p>
  <p><a href="{admin_link}" style="background:#476B6B;color:white;padding:8px 16px;text-decoration:none;border-radius:4px">Open admin campaigns</a></p>
</div>
""".strip()


def _sponsor_invoice_html(pledge: dict, campaign: dict, admin_note: Optional[str]) -> str:
    tier_line = ""
    if pledge.get("tier_snapshot"):
        t = pledge["tier_snapshot"]
        tier_line = f'<p style="margin:0 0 8px"><strong>Tier:</strong> {t.get("name")}</p>'
    note_block = ""
    if admin_note:
        note_block = (
            f'<div style="background:#F4F1EA;padding:12px;border-radius:6px;margin:16px 0">'
            f'<p style="margin:0"><em>{admin_note}</em></p></div>'
        )
    return f"""
<div style="font-family:Georgia,serif;color:#1A2424;max-width:600px">
  <h2 style="font-size:22px;margin:0 0 12px">Your sponsorship invoice — {campaign['title']}</h2>
  <p>Hi {pledge['sponsor_name']},</p>
  <p>Thank you again for your pledge to support the Birthright Foundation. Below are the details
  of your sponsorship and how to complete payment.</p>

  <div style="background:#F4F1EA;padding:16px;border-radius:8px;margin:20px 0">
    <p style="margin:0 0 8px"><strong>Campaign:</strong> {campaign['title']}</p>
    <p style="margin:0 0 8px"><strong>Amount due:</strong> ${pledge['amount']:,.2f} USD</p>
    {tier_line}
    <p style="margin:0 0 8px"><strong>Invoice ID:</strong> {pledge['id']}</p>
  </div>

  {note_block}

  <h3 style="margin:24px 0 8px">Payment options</h3>
  {_payment_options_html()}

  <div style="background:#FBF3E4;border:1px solid #E5D7B3;padding:12px;border-radius:6px;font-size:12px;color:#5C6B6B;margin:24px 0">
    <strong style="color:#8B4513">Not currently tax-deductible.</strong> Birthright Foundation
    has not yet submitted or received IRS 501(c)(3) determination. This invoice will be receipted
    as a business contribution only.
  </div>

  <p>Please reply if you have any questions or need alternate arrangements.</p>
  <p style="margin:20px 0 0">— The Birthright Foundation team</p>
</div>
""".strip()


def _sponsor_receipt_html(pledge: dict, campaign: dict) -> str:
    tier_line = ""
    if pledge.get("tier_snapshot"):
        t = pledge["tier_snapshot"]
        tier_line = f'<p style="margin:0 0 8px"><strong>Tier:</strong> {t.get("name")}</p>'
    return f"""
<div style="font-family:Georgia,serif;color:#1A2424;max-width:600px">
  <h2 style="font-size:22px;margin:0 0 12px">Payment received — thank you.</h2>
  <p>Hi {pledge['sponsor_name']},</p>
  <p>We've received your payment of <strong>${pledge['amount']:,.2f}</strong> in support of
  <strong>{campaign['title']}</strong>. This email is your business receipt.</p>

  <div style="background:#F4F1EA;padding:16px;border-radius:8px;margin:20px 0">
    <p style="margin:0 0 8px"><strong>Sponsor:</strong> {pledge['sponsor_name']}</p>
    {f'<p style="margin:0 0 8px"><strong>Organization:</strong> {pledge["organization"]}</p>' if pledge.get('organization') else ''}
    <p style="margin:0 0 8px"><strong>Amount:</strong> ${pledge['amount']:,.2f} USD</p>
    {tier_line}
    <p style="margin:0 0 8px"><strong>Campaign:</strong> {campaign['title']}</p>
    <p style="margin:0 0 0"><strong>Receipt ID:</strong> {pledge['id']}</p>
  </div>

  <div style="background:#FBF3E4;border:1px solid #E5D7B3;padding:12px;border-radius:6px;font-size:12px;color:#5C6B6B;margin:24px 0">
    <strong style="color:#8B4513">Not currently tax-deductible.</strong> Birthright Foundation
    has not yet submitted or received IRS 501(c)(3) determination. This contribution is
    receipted as a business contribution only and may not be deducted as a charitable donation.
    No representation is made about future tax status.
  </div>

  <p>Your recognition (if opted-in) will appear on the campaign page. We'll be in touch as the
  project progresses.</p>
  <p style="margin:20px 0 0">— The Birthright Foundation team</p>
</div>
""".strip()


async def send_pledge_confirmation(pledge: dict, campaign: dict) -> None:
    """Sponsor confirmation + admin alert on new pledge submission."""
    try:
        await send_email(
            to=pledge["sponsor_email"],
            subject=f"We received your pledge — {campaign['title']}",
            html=_sponsor_confirm_html(pledge, campaign),
            template_name="campaign_pledge_confirm",
            metadata={"pledge_id": pledge["id"], "campaign_id": campaign["id"]},
        )
    except Exception as e:
        logger.warning("Sponsor confirmation email failed: %s", e)

    admins = _admin_recipients()
    if admins:
        try:
            await send_email(
                to=admins,
                subject=f"[Pledge] ${pledge['amount']:,.0f} — {campaign['title']}",
                html=_admin_alert_html(pledge, campaign),
                template_name="campaign_pledge_admin_alert",
                metadata={"pledge_id": pledge["id"], "campaign_id": campaign["id"]},
            )
        except Exception as e:
            logger.warning("Admin pledge alert failed: %s", e)


async def send_invoice(pledge: dict, campaign: dict, admin_note: Optional[str] = None) -> None:
    """Email sponsor an invoice with payment options."""
    try:
        await send_email(
            to=pledge["sponsor_email"],
            subject=f"Your sponsorship invoice — {campaign['title']}",
            html=_sponsor_invoice_html(pledge, campaign, admin_note),
            template_name="campaign_pledge_invoice",
            metadata={"pledge_id": pledge["id"], "campaign_id": campaign["id"]},
        )
    except Exception as e:
        logger.warning("Sponsor invoice email failed: %s", e)


async def send_receipt(pledge: dict, campaign: dict) -> None:
    """Email sponsor a business receipt after payment."""
    try:
        await send_email(
            to=pledge["sponsor_email"],
            subject=f"Payment received — {campaign['title']}",
            html=_sponsor_receipt_html(pledge, campaign),
            template_name="campaign_pledge_receipt",
            metadata={"pledge_id": pledge["id"], "campaign_id": campaign["id"]},
        )
    except Exception as e:
        logger.warning("Sponsor receipt email failed: %s", e)
