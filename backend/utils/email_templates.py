"""Birthright transactional email templates. Each function returns (subject, html, text).

Inline CSS only. No external fonts. Table-based layout for max client compatibility.
Tested for Gmail, Apple Mail, Outlook web. Colors mirror the brand palette.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

# Brand palette
TEAL = "#476B6B"
GOLD = "#C9A961"
CREAM = "#FAF8F5"
INK = "#1A2424"
SMOKE = "#5C6B6B"
LINE = "#E5E1D8"


def _shell(title: str, preheader: str, body_html: str) -> str:
    """Wrap any inner body in the brand letter shell."""
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title></head>
<body style="margin:0;padding:0;background:{CREAM};font-family:Georgia,'Times New Roman',serif;color:{INK};">
<span style="display:none;visibility:hidden;opacity:0;height:0;width:0;overflow:hidden;">{preheader}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CREAM};padding:32px 0;">
  <tr><td align="center">
    <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid {LINE};">
      <tr><td style="padding:32px 40px 8px 40px;">
        <table role="presentation" width="100%"><tr>
          <td style="font-family:Georgia,serif;font-size:22px;color:{INK};letter-spacing:0.5px;">birthright</td>
          <td align="right" style="font-family:Arial,sans-serif;font-size:11px;color:{GOLD};letter-spacing:2px;text-transform:uppercase;">Secure Bonds &gt; Thrive</td>
        </tr></table>
        <div style="height:1px;background:{LINE};margin:18px 0 0;"></div>
      </td></tr>
      <tr><td style="padding:24px 40px 32px;font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:{INK};">
        {body_html}
      </td></tr>
      <tr><td style="background:{CREAM};padding:20px 40px;font-family:Arial,sans-serif;font-size:11px;color:{SMOKE};border-top:1px solid {LINE};">
        Birthright Foundation · 2148 W Earll Dr, Phoenix, AZ 85015<br>
        Reply to this email and a human at the foundation will get it.
      </td></tr>
    </table>
  </td></tr>
</table></body></html>"""


def _button(href: str, label: str) -> str:
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:18px 0;"><tr><td '
        f'style="background:{TEAL};padding:14px 28px;"><a href="{href}" '
        f'style="color:#FFFFFF;text-decoration:none;font-family:Arial,sans-serif;font-size:14px;'
        f'letter-spacing:0.5px;text-transform:uppercase;">{label}</a></td></tr></table>'
    )


def _money(n: float) -> str:
    return f"${n:,.2f}"


def _fmt_date(iso: Optional[str]) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%A, %b %-d, %Y · %-I:%M %p")
    except Exception:
        return iso


# ============ TEMPLATES ============

def order_receipt(*, first_name: str, items: list[dict], total: float, order_id: str, app_url: str) -> tuple[str, str, str]:
    subject = "Your order from Birthright"
    rows = "".join(
        f'<tr><td style="padding:8px 0;border-bottom:1px solid {LINE};">{i["name"]} × {i["quantity"]}</td>'
        f'<td align="right" style="padding:8px 0;border-bottom:1px solid {LINE};">{_money(i["price"] * i["quantity"])}</td></tr>'
        for i in items
    )
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">Thank you, {first_name}.</p>
        <p>Your order is confirmed. We'll be in touch when it ships.</p>
        <table width="100%" style="margin-top:18px;font-family:Arial,sans-serif;font-size:14px;">
          <tr><td style="color:{SMOKE};padding:6px 0;border-bottom:1px solid {LINE};">Item</td>
              <td align="right" style="color:{SMOKE};padding:6px 0;border-bottom:1px solid {LINE};">Subtotal</td></tr>
          {rows}
          <tr><td style="padding-top:14px;font-weight:bold;">Total</td>
              <td align="right" style="padding-top:14px;font-weight:bold;">{_money(total)}</td></tr>
        </table>
        <p style="color:{SMOKE};font-size:13px;margin-top:18px;">Order reference: {order_id}</p>
        {_button(f"{app_url}/dashboard", "View order history")}
    """
    text = (
        f"Thank you, {first_name}.\n\n"
        f"Your order from Birthright is confirmed. Reference: {order_id}\n\n"
        + "\n".join(f"  - {i['name']} × {i['quantity']} = {_money(i['price'] * i['quantity'])}" for i in items)
        + f"\n\nTotal: {_money(total)}\n\nView your orders: {app_url}/dashboard"
    )
    return subject, _shell(subject, "Your order from Birthright is confirmed.", body), text


def workshop_confirmation(*, first_name: str, workshop: dict, registration: dict, check_in_code: str, app_url: str) -> tuple[str, str, str]:
    subject = f"You're in — {workshop['title']}"
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">You're in, {first_name}.</p>
        <p>{workshop['title']} is confirmed. Calendar invite is attached.</p>
        <table width="100%" style="margin-top:18px;font-family:Arial,sans-serif;font-size:14px;">
          <tr><td style="color:{SMOKE};padding:4px 0;width:140px;">When</td><td>{_fmt_date(workshop.get('start_date'))}</td></tr>
          <tr><td style="color:{SMOKE};padding:4px 0;">Where</td><td>{workshop.get('location_name','')}<br><span style="color:{SMOKE};">{workshop.get('location_address','')}</span></td></tr>
          <tr><td style="color:{SMOKE};padding:4px 0;">Paid</td><td>{_money(registration.get('amount_paid', 0))} ({registration.get('pricing_tier', 'regular').replace('_', ' ')})</td></tr>
        </table>
        <div style="margin-top:24px;background:{CREAM};border:1px solid {LINE};padding:18px;text-align:center;">
          <div style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:2px;color:{GOLD};text-transform:uppercase;">Your check-in code</div>
          <div style="font-family:Georgia,serif;font-size:32px;letter-spacing:6px;color:{INK};margin-top:6px;">{check_in_code}</div>
          <div style="font-family:Arial,sans-serif;font-size:12px;color:{SMOKE};margin-top:8px;">A QR version is attached. Show either at the door.</div>
        </div>
        {_button(f"{app_url}/dashboard", "Open my workshop hub")}
        <p style="font-size:13px;color:{SMOKE};margin-top:18px;">If anything changes, just reply to this email.</p>
    """
    text = (
        f"You're in, {first_name}.\n\n{workshop['title']}\n"
        f"When: {_fmt_date(workshop.get('start_date'))}\n"
        f"Where: {workshop.get('location_name','')}, {workshop.get('location_address','')}\n"
        f"Check-in code: {check_in_code}\n\nOpen your hub: {app_url}/dashboard"
    )
    return subject, _shell(subject, f"{workshop['title']} confirmed.", body), text


def waitlist_promotion(*, first_name: str, workshop: dict, app_url: str) -> tuple[str, str, str]:
    subject = f"A seat just opened in {workshop['title']}"
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">A seat opened, {first_name}.</p>
        <p>You were next on the list for <strong>{workshop['title']}</strong> on {_fmt_date(workshop.get('start_date'))}. The spot is yours if you want it — register in the next 24 hours.</p>
        {_button(f"{app_url}/workshops/{workshop.get('slug','')}", "Claim my seat")}
        <p style="font-size:13px;color:{SMOKE};">If we don't hear from you in 24 hours, we'll offer it to the next person.</p>
    """
    text = (
        f"A seat opened, {first_name}.\n\nYou were next on the list for {workshop['title']} on "
        f"{_fmt_date(workshop.get('start_date'))}. Claim it within 24 hours: "
        f"{app_url}/workshops/{workshop.get('slug','')}"
    )
    return subject, _shell(subject, f"A seat opened in {workshop['title']}.", body), text


def password_reset(*, first_name: str, reset_url: str) -> tuple[str, str, str]:
    subject = "Reset your Birthright password"
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">Hi {first_name}.</p>
        <p>Someone asked to reset the password for this email. If that was you, use the link below — it expires in one hour.</p>
        {_button(reset_url, "Reset my password")}
        <p style="font-size:13px;color:{SMOKE};">If this wasn't you, you can safely ignore this message and your password will remain the same.</p>
    """
    text = (
        f"Hi {first_name}.\n\nReset your Birthright password (expires in 1 hour):\n{reset_url}\n\n"
        "If this wasn't you, ignore this email."
    )
    return subject, _shell(subject, "Reset your Birthright password.", body), text


def qa_reply_notification(*, first_name: str, workshop: dict, reply_excerpt: str, app_url: str) -> tuple[str, str, str]:
    subject = f"A facilitator replied — {workshop['title']}"
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">A reply for you, {first_name}.</p>
        <p>Your question in <strong>{workshop['title']}</strong> just got a response from the facilitator.</p>
        <blockquote style="border-left:3px solid {GOLD};padding:8px 16px;color:{SMOKE};font-style:italic;margin:14px 0;">{reply_excerpt}</blockquote>
        {_button(f"{app_url}/dashboard", "Read the full thread")}
    """
    text = f"Your question in {workshop['title']} got a reply.\n\n\"{reply_excerpt}\"\n\nRead it: {app_url}/dashboard"
    return subject, _shell(subject, "A facilitator replied to your question.", body), text


def workshop_reminder(*, first_name: str, workshop: dict, check_in_code: str, app_url: str) -> tuple[str, str, str]:
    subject = f"Tomorrow — {workshop['title']}"
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">See you tomorrow, {first_name}.</p>
        <p><strong>{workshop['title']}</strong> begins {_fmt_date(workshop.get('start_date'))} at {workshop.get('location_name','')}.</p>
        <p style="color:{SMOKE};">{workshop.get('directions_notes','')}</p>
        <div style="margin-top:18px;background:{CREAM};border:1px solid {LINE};padding:14px;text-align:center;">
          <div style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:2px;color:{GOLD};text-transform:uppercase;">Check-in code</div>
          <div style="font-family:Georgia,serif;font-size:26px;letter-spacing:5px;color:{INK};margin-top:4px;">{check_in_code}</div>
        </div>
        {_button(f"{app_url}/dashboard", "Open my hub")}
    """
    text = (
        f"See you tomorrow, {first_name}.\n\n{workshop['title']} — {_fmt_date(workshop.get('start_date'))}\n"
        f"{workshop.get('location_name','')}, {workshop.get('location_address','')}\n"
        f"Check-in code: {check_in_code}\n\n{app_url}/dashboard"
    )
    return subject, _shell(subject, f"Tomorrow: {workshop['title']}.", body), text


def contact_autoreply(*, first_name: str) -> tuple[str, str, str]:
    subject = "We got your message"
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">Thank you, {first_name}.</p>
        <p>Your note reached the foundation. A human will read it and write back, typically within two business days.</p>
        <p style="color:{SMOKE};">In the meantime, if it's about a workshop you've registered for, the fastest path to a facilitator is through the workshop hub.</p>
    """
    text = (
        f"Thank you, {first_name}.\n\nYour note reached the foundation. "
        "A human will read it and write back, usually within two business days."
    )
    return subject, _shell(subject, "We got your message.", body), text


def contact_admin_notify(*, name: str, email: str, phone: str, subject_line: str, message: str) -> tuple[str, str, str]:
    subject = f"[Contact form] {subject_line or 'New message'} — {name}"
    body = f"""
        <p style="font-family:Georgia,serif;font-size:20px;color:{INK};margin:0 0 8px;">New contact-form message</p>
        <table width="100%" style="font-family:Arial,sans-serif;font-size:14px;margin-top:12px;">
          <tr><td style="color:{SMOKE};width:90px;padding:4px 0;">From</td><td>{name} &lt;{email}&gt;</td></tr>
          <tr><td style="color:{SMOKE};padding:4px 0;">Phone</td><td>{phone or '—'}</td></tr>
          <tr><td style="color:{SMOKE};padding:4px 0;">Subject</td><td>{subject_line or '—'}</td></tr>
        </table>
        <div style="margin-top:14px;padding:14px;background:{CREAM};border:1px solid {LINE};white-space:pre-line;">{message}</div>
    """
    text = f"New contact-form message from {name} <{email}>\nPhone: {phone}\nSubject: {subject_line}\n\n{message}"
    return subject, _shell(subject, "New contact-form message.", body), text


def newsletter_welcome(*, name: str) -> tuple[str, str, str]:
    subject = "Welcome to the Birthright letter"
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">Welcome{', ' + name if name else ''}.</p>
        <p>You'll hear from us once a month with one short reflection from the practice, upcoming workshop dates, and the occasional quiet recommendation. Nothing more.</p>
        <p style="color:{SMOKE};">If it ever stops feeling worth your inbox, unsubscribe is at the bottom of every email.</p>
    """
    text = (
        f"Welcome{', ' + name if name else ''}.\n\n"
        "You'll hear from us once a month with one short reflection from the practice, "
        "upcoming workshop dates, and the occasional quiet recommendation."
    )
    return subject, _shell(subject, "Welcome to the Birthright letter.", body), text


def workshop_cancelled(
    *, first_name: str, workshop: dict, refund_amount: float, refund_status: str, app_url: str
) -> tuple[str, str, str]:
    """Notify a registrant that their workshop was cancelled, with refund status."""
    subject = f"Cancelled — {workshop['title']}"
    refund_block = ""
    if refund_status == "succeeded":
        refund_block = (
            f'<p style="color:{INK};">A full refund of <strong>{_money(refund_amount)}</strong> has been issued to '
            f"your original payment method. It typically appears within 5–10 business days.</p>"
        )
    elif refund_status == "pending":
        refund_block = (
            f'<p style="color:{INK};">A refund of <strong>{_money(refund_amount)}</strong> is being processed. '
            "You'll see it on your original payment method within 5–10 business days.</p>"
        )
    else:
        refund_block = (
            f'<p style="color:{INK};">Your refund of <strong>{_money(refund_amount)}</strong> is being arranged manually. '
            "A human at the foundation will reach out within two business days to confirm.</p>"
        )
    body = f"""
        <p style="font-family:Georgia,serif;font-size:22px;color:{INK};margin:0 0 8px;">A note, {first_name}.</p>
        <p>We're writing to let you know that <strong>{workshop['title']}</strong>, scheduled for {_fmt_date(workshop.get('start_date'))}, has been cancelled.</p>
        {refund_block}
        <p style="color:{SMOKE};">We're sorry. If you'd like to be notified when this workshop returns to the calendar, just reply and we'll add you to the early list.</p>
        {_button(f"{app_url}/workshops", "Browse other workshops")}
    """
    text = (
        f"A note, {first_name}.\n\n"
        f"{workshop['title']} on {_fmt_date(workshop.get('start_date'))} has been cancelled.\n\n"
        f"Refund of {_money(refund_amount)} — status: {refund_status}.\n\n"
        "If you'd like to be notified when it returns, reply to this email."
    )
    return subject, _shell(subject, f"{workshop['title']} has been cancelled.", body), text
