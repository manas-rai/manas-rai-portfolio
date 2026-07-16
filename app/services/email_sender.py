from __future__ import annotations

import smtplib
from email.message import EmailMessage

import httpx

from app.config import Settings


class EmailError(Exception):
    """Raised when a contact message could not be delivered. Callers surface a
    graceful fallback to the user (design doc §6.1) rather than a 500."""


def _body(name: str, sender_email: str, message: str) -> str:
    return f"From: {name} <{sender_email}>\n\n{message}"


def send_contact_message(
    settings: Settings, *, name: str, sender_email: str, message: str
) -> None:
    """Deliver a contact-form submission. Uses Resend when an API key is
    configured, otherwise SMTP. Raises EmailError on any delivery failure."""
    subject = f"Portfolio contact from {name}"
    text = _body(name, sender_email, message)

    if settings.resend_api_key:
        _send_via_resend(settings, subject=subject, text=text, reply_to=sender_email)
    elif settings.smtp_host:
        _send_via_smtp(settings, subject=subject, text=text, reply_to=sender_email)
    else:
        raise EmailError("No email transport configured (set RESEND_API_KEY or SMTP_HOST)")


def _send_via_resend(
    settings: Settings, *, subject: str, text: str, reply_to: str
) -> None:
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.email_from,
                "to": [settings.email_to],
                "reply_to": reply_to,
                "subject": subject,
                "text": text,
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise EmailError(f"Resend delivery failed: {exc}") from exc


def _send_via_smtp(
    settings: Settings, *, subject: str, text: str, reply_to: str
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = settings.email_to
    msg["Reply-To"] = reply_to
    msg.set_content(text)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10.0) as smtp:
            smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailError(f"SMTP delivery failed: {exc}") from exc
