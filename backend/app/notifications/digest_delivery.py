from __future__ import annotations

import os
import uuid
import requests
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.notifications.email_delivery import send_email_with_attachment
from app.routes.board_reporting import build_board_report_xlsx_bytes


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _log_digest_delivery(
    db: Session,
    *,
    digest_type: str,
    channel: str,
    recipients: list[str],
    sent: bool,
    status_code: str,
    failure_reason: str,
    delivery_batch_id: str,
    payload_summary: str,
):
    row = models.DigestDelivery(
        digest_type=digest_type,
        channel=channel,
        recipients=",".join(recipients),
        sent=sent,
        status_code=status_code,
        failure_reason=failure_reason,
        delivery_batch_id=delivery_batch_id,
        payload_summary=payload_summary[:4000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _slack_enabled() -> bool:
    return _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")) and _truthy(os.getenv("LUMENAI_SLACK_ENABLED", "false"))


def _email_enabled() -> bool:
    return _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")) and _truthy(os.getenv("LUMENAI_EMAIL_ENABLED", "false"))


def build_digest_message(digest: dict[str, Any]) -> str:
    s = digest.get("executive_summary", {})
    narrative = digest.get("leadership_narrative", {})
    top_sites = ", ".join([f"{x['label']} ({x['count']})" for x in s.get("top_sites", [])[:3]]) or "none"
    top_vendors = ", ".join([f"{x['label']} ({x['count']})" for x in s.get("top_vendors", [])[:3]]) or "none"

    return (
        f"LumenAI Weekly Executive Digest\n"
        f"- Total inspections: {s.get('total_inspections', 0)}\n"
        f"- Completion rate: {round(float(s.get('completion_rate', 0.0)) * 100, 1)}%\n"
        f"- Open alerts: {s.get('open_alerts', 0)}\n"
        f"- High risk findings: {s.get('high_risk_count', 0)}\n"
        f"- QA override rate: {round(float(s.get('qa_override_rate', 0.0)) * 100, 1)}%\n"
        f"- Top sites: {top_sites}\n"
        f"- Top vendors: {top_vendors}\n\n"
        f"{narrative.get('headline', '')}\n"
        f"{narrative.get('quality_note', '')}\n"
        f"{narrative.get('operations_note', '')}"
    ).strip()


def deliver_digest(
    db: Session,
    *,
    digest_type: str,
    digest_payload: dict[str, Any],
) -> dict[str, Any]:
    enabled = _truthy(os.getenv("LUMENAI_DIGEST_AUTOMATION_ENABLED", "false"))
    batch_id = str(uuid.uuid4())
    message = build_digest_message(digest_payload)
    results: list[dict[str, Any]] = []

    if not enabled:
        _log_digest_delivery(
            db,
            digest_type=digest_type,
            channel="system",
            recipients=[],
            sent=False,
            status_code="DISABLED",
            failure_reason="Digest automation disabled",
            delivery_batch_id=batch_id,
            payload_summary=message,
        )
        return {
            "enabled": False,
            "delivery_batch_id": batch_id,
            "results": [],
            "message": "Digest automation disabled",
        }

    channels = [x.strip().lower() for x in os.getenv("LUMENAI_DIGEST_AUTOMATION_CHANNEL", "slack").split(",") if x.strip()]

    if "slack" in channels:
        webhook = os.getenv("LUMENAI_SLACK_WEBHOOK_URL", "").strip()
        recipients = [os.getenv("LUMENAI_EXECUTIVE_SLACK_CHANNEL", "").strip()] if os.getenv("LUMENAI_EXECUTIVE_SLACK_CHANNEL", "").strip() else []
        if not _slack_enabled():
            _log_digest_delivery(
                db, digest_type=digest_type, channel="slack", recipients=recipients,
                sent=False, status_code="DISABLED", failure_reason="Slack channel disabled",
                delivery_batch_id=batch_id, payload_summary=message
            )
            results.append({"channel": "slack", "sent": False, "reason": "Slack channel disabled"})
        elif not webhook:
            _log_digest_delivery(
                db, digest_type=digest_type, channel="slack", recipients=recipients,
                sent=False, status_code="NOT_CONFIGURED", failure_reason="Slack webhook not configured",
                delivery_batch_id=batch_id, payload_summary=message
            )
            results.append({"channel": "slack", "sent": False, "reason": "Slack webhook not configured"})
        else:
            try:
                resp = requests.post(webhook, json={"text": message}, timeout=20)
                ok = resp.status_code == 200 and resp.text.strip().lower() == "ok"
                _log_digest_delivery(
                    db, digest_type=digest_type, channel="slack", recipients=recipients,
                    sent=ok, status_code=str(resp.status_code), failure_reason="" if ok else resp.text[:2000],
                    delivery_batch_id=batch_id, payload_summary=message
                )
                results.append({
                    "channel": "slack",
                    "sent": ok,
                    "status_code": resp.status_code,
                    "response_text": resp.text[:500],
                })
            except Exception as e:
                _log_digest_delivery(
                    db, digest_type=digest_type, channel="slack", recipients=recipients,
                    sent=False, status_code="REQUEST_ERROR", failure_reason=str(e),
                    delivery_batch_id=batch_id, payload_summary=message
                )
                results.append({"channel": "slack", "sent": False, "reason": str(e)})

    if "email" in channels:
        recipients = _parse_csv_env("LUMENAI_EXECUTIVE_EMAILS")
        if not _email_enabled():
            _log_digest_delivery(
                db, digest_type=digest_type, channel="email", recipients=recipients,
                sent=False, status_code="DISABLED", failure_reason="Email channel disabled",
                delivery_batch_id=batch_id, payload_summary=message
            )
            results.append({"channel": "email", "sent": False, "reason": "Email channel disabled"})
        else:
            xlsx_bytes = build_board_report_xlsx_bytes(digest_payload)
            email_result = send_email_with_attachment(
                subject="LumenAI Weekly Executive Digest",
                body=message,
                attachment_bytes=xlsx_bytes,
                attachment_filename="lumenai_board_ready_weekly.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            _log_digest_delivery(
                db,
                digest_type=digest_type,
                channel="email",
                recipients=email_result.get("recipients", recipients),
                sent=bool(email_result.get("sent", False)),
                status_code=str(email_result.get("status_code", "")),
                failure_reason=str(email_result.get("failure_reason", "")),
                delivery_batch_id=batch_id,
                payload_summary=message,
            )
            results.append({
                "channel": "email",
                "sent": bool(email_result.get("sent", False)),
                "status_code": email_result.get("status_code", ""),
                "reason": email_result.get("failure_reason", ""),
            })

    return {
        "enabled": True,
        "delivery_batch_id": batch_id,
        "results": results,
    }
