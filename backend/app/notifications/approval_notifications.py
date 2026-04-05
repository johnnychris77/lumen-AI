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


def approval_message(approval: dict, mode: str = "new") -> str:
    prefix = "NEW APPROVAL REQUEST" if mode == "new" else "APPROVAL ESCALATION"
    return (
        f"{prefix}\n"
        f"- Tenant: {approval.get('tenant_name', '')}\n"
        f"- Request Type: {approval.get('request_type', '')}\n"
        f"- Target: {approval.get('target_resource', '')} ({approval.get('target_resource_id', '')})\n"
        f"- Requested By: {approval.get('requested_by', '')}\n"
        f"- Status: {approval.get('status', '')}\n"
        f"- Created At: {approval.get('created_at', '')}\n"
        f"- Payload: {approval.get('requested_payload', '')}"
    )


def notify_approval(approval: dict, mode: str = "new") -> dict:
    if not _truthy(os.getenv("LUMENAI_APPROVAL_NOTIFICATIONS_ENABLED", "false")):
        return {"enabled": False, "results": []}

    results = []
    channels = [x.strip().lower() for x in os.getenv("LUMENAI_APPROVAL_NOTIFY_CHANNELS", "slack").split(",") if x.strip()]
    message = approval_message(approval, mode=mode)

    if "slack" in channels:
        webhook = os.getenv("LUMENAI_SLACK_WEBHOOK_URL", "").strip()
        if not _slack_enabled():
            results.append({"channel": "slack", "sent": False, "reason": "Slack disabled"})
        elif not webhook:
            results.append({"channel": "slack", "sent": False, "reason": "Slack webhook not configured"})
        else:
            try:
                resp = requests.post(webhook, json={"text": message}, timeout=20)
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
            results.append({"channel": "email", "sent": False, "reason": "Approval email recipients not configured"})
        else:
            subject = "LumenAI Governance Approval Required" if mode == "new" else "LumenAI Governance Approval Escalation"
            email_result = send_email_with_attachment(subject=subject, body=message)
            results.append({
                "channel": "email",
                "sent": bool(email_result.get("sent", False)),
                "status_code": email_result.get("status_code", ""),
                "reason": email_result.get("failure_reason", ""),
            })

    return {"enabled": True, "results": results}
