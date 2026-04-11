from __future__ import annotations

import os
import requests

from app.notifications.email_delivery import send_email_with_attachment


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _slack_enabled() -> bool:
    return _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")) and _truthy(os.getenv("LUMENAI_SLACK_ENABLED", "false"))


def _email_enabled() -> bool:
    return _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")) and _truthy(os.getenv("LUMENAI_EMAIL_ENABLED", "false"))


def _message(payload: dict, mode: str) -> str:
    prefix = {
        "renewal_due": "LumenAI Renewal Reminder",
        "payment_failed": "LumenAI Payment Failed",
        "suspended": "LumenAI Account Suspended",
        "recovered": "LumenAI Payment Recovered",
    }.get(mode, "LumenAI Dunning Update")

    return (
        f"{prefix}\n"
        f"- Tenant: {payload.get('tenant_name', '')}\n"
        f"- Plan: {payload.get('plan_name', '')}\n"
        f"- Status: {payload.get('status', '')}\n"
        f"- Payment Status: {payload.get('last_payment_status', '')}\n"
        f"- Dunning: {payload.get('dunning_status', '')}\n"
        f"- Suspension: {payload.get('suspension_status', '')}\n"
        f"- Current Period End: {payload.get('current_period_end', '')}\n"
        f"- Days To Renewal: {payload.get('days_to_renewal', '')}"
    )


def send_dunning_notification(payload: dict, mode: str) -> dict:
    channels = [x.strip().lower() for x in os.getenv("LUMENAI_DUNNING_NOTIFY_CHANNELS", "slack").split(",") if x.strip()]
    text = _message(payload, mode)
    results = []

    if "slack" in channels:
        webhook = os.getenv("LUMENAI_SLACK_WEBHOOK_URL", "").strip()
        if not _slack_enabled():
            results.append({"channel": "slack", "sent": False, "reason": "Slack disabled"})
        elif not webhook:
            results.append({"channel": "slack", "sent": False, "reason": "Slack webhook not configured"})
        else:
            try:
                resp = requests.post(webhook, json={"text": text}, timeout=20)
                ok = resp.status_code == 200 and resp.text.strip().lower() == "ok"
                results.append({
                    "channel": "slack",
                    "sent": ok,
                    "status_code": resp.status_code,
                    "reason": "" if ok else resp.text[:500],
                })
            except Exception as e:
                results.append({"channel": "slack", "sent": False, "reason": str(e)})

    if "email" in channels:
        recipients = _parse_csv_env("LUMENAI_APPROVAL_EMAILS")
        if not _email_enabled():
            results.append({"channel": "email", "sent": False, "reason": "Email disabled"})
        elif not recipients:
            results.append({"channel": "email", "sent": False, "reason": "Email recipients not configured"})
        else:
            subject = {
                "renewal_due": "LumenAI Renewal Reminder",
                "payment_failed": "LumenAI Payment Failed",
                "suspended": "LumenAI Account Suspended",
                "recovered": "LumenAI Payment Recovered",
            }.get(mode, "LumenAI Dunning Update")
            email_result = send_email_with_attachment(subject=subject, body=text)
            results.append({
                "channel": "email",
                "sent": bool(email_result.get("sent", False)),
                "status_code": email_result.get("status_code", ""),
                "reason": email_result.get("failure_reason", ""),
            })

    return {"mode": mode, "results": results}
