from __future__ import annotations

import os
import smtplib
import uuid
from email.message import EmailMessage
from typing import Dict, Any, List

import requests

from app.db import SessionLocal
from app.db import models


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _looks_like_slack_webhook(url: str) -> bool:
    url = (url or "").strip()
    return url.startswith("https://hooks.slack.com/services/")


ALERTS_ENABLED = _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false"))

SLACK_WEBHOOK_URL = os.getenv("LUMENAI_SLACK_WEBHOOK_URL", "").strip()
TEAMS_WEBHOOK_URL = os.getenv("LUMENAI_TEAMS_WEBHOOK_URL", "").strip()

SMTP_HOST = os.getenv("LUMENAI_SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("LUMENAI_SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("LUMENAI_SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("LUMENAI_SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("LUMENAI_SMTP_FROM", "lumenai@localhost").strip()
ALERT_EMAIL_TO = os.getenv("LUMENAI_ALERT_EMAIL_TO", "").strip()

# Safe rollout switches
SLACK_ENABLED = _truthy(os.getenv("LUMENAI_SLACK_ENABLED", "false"))
TEAMS_ENABLED = _truthy(os.getenv("LUMENAI_TEAMS_ENABLED", "false"))
EMAIL_ENABLED = _truthy(os.getenv("LUMENAI_EMAIL_ENABLED", "false"))


def format_alert_message(alert: Dict[str, Any]) -> str:
    return (
        f"LumenAI Alert\n\n"
        f"Inspection ID: {alert.get('inspection_id')}\n"
        f"File: {alert.get('file_name', 'unknown')}\n"
        f"Vendor: {alert.get('vendor_name', 'unknown')}\n"
        f"Instrument: {alert.get('instrument_type', 'unknown')}\n"
        f"Issue: {alert.get('detected_issue', 'unknown')}\n"
        f"Risk Score: {alert.get('risk_score', 0)}\n"
        f"Status: {alert.get('status', 'unknown')}\n\n"
        f"{alert.get('message', '')}"
    )


def _log_alert_event(
    alert: Dict[str, Any],
    channel: str,
    sent: bool,
    dispatch_batch_id: str,
    status_code: str = "",
    failure_reason: str = "",
) -> None:
    db = SessionLocal()
    try:
        row = models.AlertEvent(
            inspection_id=int(alert.get("inspection_id") or 0),
            vendor_name=str(alert.get("vendor_name") or "unknown"),
            instrument_type=str(alert.get("instrument_type") or "unknown"),
            detected_issue=str(alert.get("detected_issue") or "unknown"),
            risk_score=int(alert.get("risk_score") or 0),
            channel=channel,
            sent=bool(sent),
            status_code=str(status_code or "")[:50],
            failure_reason=str(failure_reason or "")[:500],
            dispatch_batch_id=dispatch_batch_id,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()


def send_slack_alert(alert: Dict[str, Any], dispatch_batch_id: str) -> Dict[str, Any]:
    if not SLACK_ENABLED:
        result = {"channel": "slack", "sent": False, "reason": "Slack channel disabled"}
        _log_alert_event(alert, "slack", False, dispatch_batch_id, status_code="DISABLED", failure_reason=result["reason"])
        return result

    if not SLACK_WEBHOOK_URL:
        result = {"channel": "slack", "sent": False, "reason": "Slack webhook not configured"}
        _log_alert_event(alert, "slack", False, dispatch_batch_id, status_code="NOT_CONFIGURED", failure_reason=result["reason"])
        return result

    if not _looks_like_slack_webhook(SLACK_WEBHOOK_URL):
        result = {"channel": "slack", "sent": False, "reason": "Slack webhook format is invalid"}
        _log_alert_event(alert, "slack", False, dispatch_batch_id, status_code="INVALID_WEBHOOK", failure_reason=result["reason"])
        return result

    payload = {
        "text": format_alert_message(alert)
    }

    try:
        resp = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json"},
        )

        response_text = (resp.text or "")[:500]
        sent = resp.status_code == 200 and response_text.strip().lower() == "ok"

        result = {
            "channel": "slack",
            "sent": sent,
            "status_code": resp.status_code,
            "response_text": response_text,
        }

        _log_alert_event(
            alert,
            "slack",
            sent,
            dispatch_batch_id,
            status_code=str(resp.status_code),
            failure_reason="" if sent else response_text,
        )
        return result

    except requests.Timeout:
        result = {"channel": "slack", "sent": False, "reason": "Slack request timed out"}
        _log_alert_event(alert, "slack", False, dispatch_batch_id, status_code="TIMEOUT", failure_reason=result["reason"])
        return result
    except requests.RequestException as exc:
        result = {"channel": "slack", "sent": False, "reason": str(exc)[:500]}
        _log_alert_event(alert, "slack", False, dispatch_batch_id, status_code="REQUEST_ERROR", failure_reason=result["reason"])
        return result


def send_teams_alert(alert: Dict[str, Any], dispatch_batch_id: str) -> Dict[str, Any]:
    if not TEAMS_ENABLED:
        result = {"channel": "teams", "sent": False, "reason": "Teams channel disabled"}
        _log_alert_event(alert, "teams", False, dispatch_batch_id, status_code="DISABLED", failure_reason=result["reason"])
        return result

    if not TEAMS_WEBHOOK_URL:
        result = {"channel": "teams", "sent": False, "reason": "Teams webhook not configured"}
        _log_alert_event(alert, "teams", False, dispatch_batch_id, status_code="NOT_CONFIGURED", failure_reason=result["reason"])
        return result

    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": f"LumenAI Alert #{alert.get('inspection_id')}",
        "themeColor": "E67E22" if int(alert.get("risk_score", 0) or 0) < 80 else "C0392B",
        "title": f"LumenAI Alert: Inspection {alert.get('inspection_id')}",
        "sections": [
            {
                "facts": [
                    {"name": "Vendor", "value": str(alert.get("vendor_name", "unknown"))},
                    {"name": "Instrument", "value": str(alert.get("instrument_type", "unknown"))},
                    {"name": "Issue", "value": str(alert.get("detected_issue", "unknown"))},
                    {"name": "Risk Score", "value": str(alert.get("risk_score", 0))},
                    {"name": "Status", "value": str(alert.get("status", "unknown"))},
                ],
                "text": str(alert.get("message", "")),
            }
        ],
    }

    try:
        resp = requests.post(TEAMS_WEBHOOK_URL, json=payload, timeout=15)
        sent = 200 <= resp.status_code < 300
        result = {
            "channel": "teams",
            "sent": sent,
            "status_code": resp.status_code,
            "response_text": (resp.text or "")[:500],
        }
        _log_alert_event(
            alert,
            "teams",
            sent,
            dispatch_batch_id,
            status_code=str(resp.status_code),
            failure_reason="" if sent else (resp.text or "")[:500],
        )
        return result
    except Exception as exc:
        result = {"channel": "teams", "sent": False, "reason": str(exc)[:500]}
        _log_alert_event(alert, "teams", False, dispatch_batch_id, status_code="REQUEST_ERROR", failure_reason=result["reason"])
        return result


def send_email_alert(alert: Dict[str, Any], dispatch_batch_id: str) -> Dict[str, Any]:
    if not EMAIL_ENABLED:
        result = {"channel": "email", "sent": False, "reason": "Email channel disabled"}
        _log_alert_event(alert, "email", False, dispatch_batch_id, status_code="DISABLED", failure_reason=result["reason"])
        return result

    if not (SMTP_HOST and ALERT_EMAIL_TO):
        result = {"channel": "email", "sent": False, "reason": "SMTP or recipient not configured"}
        _log_alert_event(alert, "email", False, dispatch_batch_id, status_code="NOT_CONFIGURED", failure_reason=result["reason"])
        return result

    msg = EmailMessage()
    msg["Subject"] = f"LumenAI Alert: Inspection {alert.get('inspection_id')}"
    msg["From"] = SMTP_FROM
    msg["To"] = ALERT_EMAIL_TO
    msg.set_content(format_alert_message(alert))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        result = {"channel": "email", "sent": True}
        _log_alert_event(alert, "email", True, dispatch_batch_id, status_code="200")
        return result
    except Exception as exc:
        result = {"channel": "email", "sent": False, "reason": str(exc)[:500]}
        _log_alert_event(alert, "email", False, dispatch_batch_id, status_code="REQUEST_ERROR", failure_reason=result["reason"])
        return result


def dispatch_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    dispatch_batch_id = str(uuid.uuid4())

    if not ALERTS_ENABLED:
        _log_alert_event(
            alert,
            "system",
            False,
            dispatch_batch_id,
            status_code="DISABLED",
            failure_reason="Alerts are disabled. Set LUMENAI_ALERTS_ENABLED=true to enable dispatch.",
        )
        return {
            "enabled": False,
            "dispatch_batch_id": dispatch_batch_id,
            "results": [],
            "message": "Alerts are disabled. Set LUMENAI_ALERTS_ENABLED=true to enable dispatch.",
        }

    results: List[Dict[str, Any]] = [
        send_slack_alert(alert, dispatch_batch_id),
        send_teams_alert(alert, dispatch_batch_id),
        send_email_alert(alert, dispatch_batch_id),
    ]
    return {
        "enabled": True,
        "dispatch_batch_id": dispatch_batch_id,
        "results": results,
    }
