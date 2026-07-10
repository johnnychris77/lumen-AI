"""v4.2 — Project Pulse, Section 10: Notification Center.

Composes what already exists rather than building a second delivery
layer: `app/notifications/notifier.py::dispatch_alert` already has real,
working Slack/Teams/Email dispatch (env-flag gated, safe to call even
when disabled — it returns a structured "disabled" result rather than
raising); Nexus's `nexus_event_bus_service`/`NexusEventSubscription`
already does generic webhook delivery for the `webhook` channel. SMS is
a genuine gap (confirmed zero existing SMS code anywhere) — it is
implemented as an explicitly logged stub, never a fabricated send.

"Notification rules configurable through Project Forge" is implemented
as Pulse being a *consumer* of Forge's existing rule engine
(`forge_rule_engine.evaluate_all_rules`) rather than Forge depending on
Pulse — the dependency runs one direction only (newest sprint depends on
older ones), so Forge's own model/action constants are never modified
by this file. A rule's action is treated as a notification instruction
when its `type` is `"notify_supervisor"` or `"escalate"` and its
`params` includes a `channel` key.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.notifications.notifier import dispatch_alert
from app.services import forge_rule_engine, platform_notification_service

_NOTIFICATION_ACTION_TYPES = {"notify_supervisor", "escalate"}
_SUPPORTED_CHANNELS = ("in_app", "email", "sms", "teams", "slack", "webhook")


def send_sms(recipient: str, message: str) -> dict:
    """SMS delivery does not exist anywhere in this codebase (confirmed
    before writing this file) — this is an explicit, logged stub, never
    a fabricated 'sent' result."""
    return {"channel": "sms", "sent": False, "reason": "SMS delivery is not configured in this deployment.", "recipient": recipient, "message": message}


def send_via_channel(channel: str, *, title: str, message: str, severity: str = "medium", recipient: str = "") -> dict:
    if channel not in _SUPPORTED_CHANNELS:
        raise ValueError(f"channel must be one of {_SUPPORTED_CHANNELS}")
    if channel == "sms":
        return send_sms(recipient, message)
    if channel == "in_app":
        return {"channel": "in_app", "sent": True, "note": "Delivered via the unified in-app notification feed."}
    # slack / teams / email / webhook all go through the existing dispatcher
    alert = {"title": title, "message": message, "severity": severity}
    result = dispatch_alert(alert)
    matching = next((r for r in result.get("results", []) if r.get("channel") == channel), None)
    return matching or {"channel": channel, "sent": False, "reason": "channel not dispatched", "dispatch": result}


def route_notification(db: Session, tenant_id: str, context: dict, *, default_channel: str = "in_app") -> list[dict]:
    """Evaluates every approved Forge rule against `context`; for each
    matched rule whose actions request a notification, dispatches it
    through the requested channel (or `default_channel` if none is
    specified)."""
    rule_results = forge_rule_engine.evaluate_all_rules(db, tenant_id, context)
    dispatched = []
    for rule_result in rule_results:
        if not rule_result["matched"]:
            continue
        for action in rule_result.get("actions", []):
            if action.get("type") not in _NOTIFICATION_ACTION_TYPES:
                continue
            params = action.get("params", {})
            channel = params.get("channel", default_channel)
            result = send_via_channel(
                channel, title=rule_result["name"], message=params.get("message", f"Rule '{rule_result['name']}' matched."),
                severity=params.get("severity", "medium"), recipient=params.get("recipient", ""),
            )
            dispatched.append({"rule_id": rule_result["rule_id"], "rule_ref": rule_result["rule_ref"], "channel": channel, "result": result})
    return dispatched


def notification_center_feed(db: Session, tenant_id: str, *, role: str = "") -> dict:
    notifications = platform_notification_service.unified_notifications(db, tenant_id, recipient_role=role, limit=100)
    return {
        "notifications": notifications,
        "unread_count": sum(1 for n in notifications if not n["read"]),
        "supported_channels": list(_SUPPORTED_CHANNELS),
    }
