"""Transactional email. SMTP is optional — callers degrade gracefully if
unset (e.g. the forgot-password endpoint still succeeds so it never leaks
whether an account exists).
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


def _send(to_emails: list[str], subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not to_emails:
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user or "noreply@localhost"
    msg["To"] = ", ".join(to_emails)
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception as exc:
        # Log for debugging, but never raise — a notification failure must
        # not break the caller's request/pipeline.
        print(f"email send failed ({subject!r}): {exc}")


def send_password_reset_email(to_email: str, token: str) -> None:
    settings = get_settings()
    link = f"{settings.frontend_url.rstrip('/')}/reset-password/{token}"
    minutes = max(1, settings.password_reset_expiry // 60)
    body = (
        "A password reset was requested for your Thermal Source Monitor account.\n\n"
        f"Reset your password: {link}\n\n"
        f"This link expires in {minutes} minutes and can only be used once.\n"
        "If you did not request this, you can ignore this email."
    )
    _send([to_email], "Reset your password", body)


def send_alert_notification(alerts: list[dict], recipients: list[str]) -> None:
    """One email listing every newly-detected / unregistered thermal source.
    `alerts` items are the dicts from `app.processing.alerts.build_alerts`."""
    lines = []
    for a in alerts:
        lines.append(
            f"- [{a['severity'].upper()}] source #{a['source_id']} "
            f"({a['lat']:.4f}, {a['lon']:.4f}) — {a['predicted_class'] or 'unclassified'}: "
            f"{a['reason']}\n"
            f"  map: https://www.google.com/maps?q={a['lat']},{a['lon']}"
        )
    body = (
        f"{len(alerts)} thermal source alert(s) from the latest ingest:\n\n"
        + "\n\n".join(lines)
    )
    _send(recipients, f"[Thermal Source Monitor] {len(alerts)} new alert(s)", body)
