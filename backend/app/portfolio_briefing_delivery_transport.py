from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:18011").rstrip("/")


def ensure_delivery_transport_columns(db: Session) -> None:
    db.execute(
        text(
            """
            ALTER TABLE portfolio_briefing_deliveries
            ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0
            """
        )
    )
    db.execute(
        text(
            """
            ALTER TABLE portfolio_briefing_deliveries
            ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMP WITH TIME ZONE
            """
        )
    )
    db.execute(
        text(
            """
            ALTER TABLE portfolio_briefing_deliveries
            ADD COLUMN IF NOT EXISTS error_message TEXT
            """
        )
    )
    db.execute(
        text(
            """
            ALTER TABLE portfolio_briefing_deliveries
            ADD COLUMN IF NOT EXISTS transport_response_json TEXT NOT NULL DEFAULT '{}'
            """
        )
    )
    db.commit()


def _get_delivery(db: Session, delivery_id: int) -> dict[str, Any] | None:
    ensure_delivery_transport_columns(db)

    row = (
        db.execute(
            text(
                """
                SELECT *
                FROM portfolio_briefing_deliveries
                WHERE id = :delivery_id
                """
            ),
            {"delivery_id": delivery_id},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def _get_export(db: Session, export_id: int | None) -> dict[str, Any] | None:
    if not export_id:
        return None

    row = (
        db.execute(
            text(
                """
                SELECT *
                FROM portfolio_briefing_exports
                WHERE id = :export_id
                """
            ),
            {"export_id": export_id},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def _artifact_links(export_id: int | None) -> dict[str, str]:
    if not export_id:
        return {}

    base = _base_url()
    return {
        "docx": f"{base}/api/portfolio-briefings/exports/{export_id}/docx",
        "pptx": f"{base}/api/portfolio-briefings/exports/{export_id}/pptx",
        "pdf": f"{base}/api/portfolio-briefings/exports/{export_id}/pdf",
    }


def _update_delivery(
    db: Session,
    delivery_id: int,
    status: str,
    response: dict[str, Any],
    error_message: str | None = None,
) -> dict[str, Any]:
    row = (
        db.execute(
            text(
                """
                UPDATE portfolio_briefing_deliveries
                SET status = :status,
                    attempt_count = attempt_count + 1,
                    last_attempt_at = NOW(),
                    error_message = :error_message,
                    transport_response_json = :transport_response_json
                WHERE id = :delivery_id
                RETURNING *
                """
            ),
            {
                "delivery_id": delivery_id,
                "status": status,
                "error_message": error_message,
                "transport_response_json": json.dumps(response, default=str),
            },
        )
        .mappings()
        .first()
    )
    db.commit()
    return dict(row)


def _send_internal(delivery: dict[str, Any], export: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "transport": "internal",
        "sent": True,
        "delivery_id": delivery["id"],
        "export_id": delivery.get("export_id"),
        "links": _artifact_links(delivery.get("export_id")),
        "note": "Internal delivery audit recorded. No external transport attempted.",
        "sent_at": _now_iso(),
    }


def _send_webhook(delivery: dict[str, Any], export: dict[str, Any] | None) -> dict[str, Any]:
    target = str(delivery["delivery_target"])

    payload = {
        "event": "portfolio_briefing_delivery",
        "delivery_id": delivery["id"],
        "briefing_id": delivery["briefing_id"],
        "export_id": delivery.get("export_id"),
        "channel": delivery["delivery_channel"],
        "target": target,
        "artifact_links": _artifact_links(delivery.get("export_id")),
        "payload": json.loads(delivery.get("payload_json") or "{}"),
        "sent_at": _now_iso(),
    }

    response = requests.post(target, json=payload, timeout=20)
    response.raise_for_status()

    return {
        "transport": "webhook",
        "sent": True,
        "status_code": response.status_code,
        "response_text": response.text[:1000],
        "sent_at": _now_iso(),
    }


def _attach_file_if_exists(message: EmailMessage, path_value: str | None) -> None:
    if not path_value:
        return

    path = Path(path_value)
    if not path.exists():
        return

    data = path.read_bytes()
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        maintype, subtype = "application", "pdf"
    elif suffix == ".docx":
        maintype, subtype = "application", "vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif suffix == ".pptx":
        maintype, subtype = "application", "vnd.openxmlformats-officedocument.presentationml.presentation"
    else:
        maintype, subtype = "application", "octet-stream"

    message.add_attachment(
        data,
        maintype=maintype,
        subtype=subtype,
        filename=path.name,
    )


def _send_email(delivery: dict[str, Any], export: dict[str, Any] | None) -> dict[str, Any]:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "noreply@lumenai.local")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not smtp_host:
        raise RuntimeError("SMTP_HOST is not configured")

    target = str(delivery["delivery_target"])
    payload = json.loads(delivery.get("payload_json") or "{}")

    message = EmailMessage()
    message["Subject"] = f"LumenAI Portfolio Briefing Package — Briefing {delivery['briefing_id']}"
    message["From"] = smtp_from
    message["To"] = target

    links = _artifact_links(delivery.get("export_id"))
    body = payload.get("message") or "Portfolio briefing package is ready for review."

    message.set_content(
        body
        + "\n\nArtifact links:\n"
        + "\n".join([f"{key.upper()}: {value}" for key, value in links.items()])
        + "\n\nGenerated by LumenAI."
    )

    if export:
        _attach_file_if_exists(message, export.get("docx_path"))
        _attach_file_if_exists(message, export.get("pptx_path"))
        _attach_file_if_exists(message, export.get("pdf_path"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

    return {
        "transport": "email",
        "sent": True,
        "to": target,
        "smtp_host": smtp_host,
        "sent_at": _now_iso(),
        "links": links,
    }


def execute_delivery_transport(db: Session, delivery_id: int) -> dict[str, Any]:
    delivery = _get_delivery(db, delivery_id)
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} was not found")

    export = _get_export(db, delivery.get("export_id"))
    channel = str(delivery["delivery_channel"]).lower()

    try:
        if channel == "internal":
            response = _send_internal(delivery, export)
        elif channel == "webhook":
            response = _send_webhook(delivery, export)
        elif channel == "email":
            response = _send_email(delivery, export)
        else:
            raise ValueError(f"Unsupported delivery channel: {channel}")

        return _update_delivery(
            db=db,
            delivery_id=delivery_id,
            status="sent",
            response=response,
            error_message=None,
        )

    except Exception as exc:
        return _update_delivery(
            db=db,
            delivery_id=delivery_id,
            status="retry_pending",
            response={
                "transport": channel,
                "sent": False,
                "error": repr(exc),
                "failed_at": _now_iso(),
            },
            error_message=str(exc),
        )


def list_deliveries(
    db: Session,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_delivery_transport_columns(db)

    if status:
        rows = (
            db.execute(
                text(
                    """
                    SELECT *
                    FROM portfolio_briefing_deliveries
                    WHERE status = :status
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"status": status, "limit": limit},
            )
            .mappings()
            .all()
        )
    else:
        rows = (
            db.execute(
                text(
                    """
                    SELECT *
                    FROM portfolio_briefing_deliveries
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )

    return [dict(row) for row in rows]


def get_delivery(db: Session, delivery_id: int) -> dict[str, Any] | None:
    return _get_delivery(db, delivery_id)
