from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def send_email_with_attachment(
    *,
    subject: str,
    body: str,
    attachment_bytes: bytes | None = None,
    attachment_filename: str | None = None,
    mime_type: str = "application/octet-stream",
) -> dict:
    host = os.getenv("LUMENAI_SMTP_HOST", "").strip()
    port = int(os.getenv("LUMENAI_SMTP_PORT", "587").strip() or 587)
    username = os.getenv("LUMENAI_SMTP_USERNAME", "").strip()
    password = os.getenv("LUMENAI_SMTP_PASSWORD", "").strip()
    sender = os.getenv("LUMENAI_SMTP_FROM", "").strip() or username
    recipients = _parse_csv_env("LUMENAI_EXECUTIVE_EMAILS") or _parse_csv_env("LUMENAI_ALERT_EMAIL_TO")

    if not host or not username or not password or not sender or not recipients:
        return {
            "sent": False,
            "status_code": "NOT_CONFIGURED",
            "failure_reason": "SMTP settings or executive email recipients not configured",
        }

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    if attachment_bytes and attachment_filename:
        maintype, subtype = mime_type.split("/", 1) if "/" in mime_type else ("application", "octet-stream")
        msg.add_attachment(
            attachment_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_filename,
        )

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)

        return {
            "sent": True,
            "status_code": "200",
            "failure_reason": "",
            "recipients": recipients,
        }
    except Exception as e:
        return {
            "sent": False,
            "status_code": "REQUEST_ERROR",
            "failure_reason": str(e),
            "recipients": recipients,
        }
