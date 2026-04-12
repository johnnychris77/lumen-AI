from __future__ import annotations

from app.notifications.dunning_notifications import send_dunning_notification


def deliver_report(channel: str, target: str, payload: dict) -> dict:
    if not channel:
        return {"sent": False, "channel": "", "reason": "No delivery channel configured"}

    if channel == "slack":
        result = send_dunning_notification(
            {
                "tenant_name": payload.get("tenant_name", ""),
                "plan_name": payload.get("report_type", "report"),
                "status": "report_ready",
                "last_payment_status": "",
                "dunning_status": "",
                "suspension_status": "",
                "current_period_end": "",
                "days_to_renewal": "",
            },
            "renewal_due",
        )
        return {"sent": True, "channel": "slack", "target": target, "result": result}

    if channel == "email":
        result = send_dunning_notification(
            {
                "tenant_name": payload.get("tenant_name", ""),
                "plan_name": payload.get("report_type", "report"),
                "status": "report_ready",
                "last_payment_status": "",
                "dunning_status": "",
                "suspension_status": "",
                "current_period_end": "",
                "days_to_renewal": "",
            },
            "renewal_due",
        )
        return {"sent": True, "channel": "email", "target": target, "result": result}

    return {"sent": False, "channel": channel, "reason": f"Unsupported delivery channel: {channel}"}
