from __future__ import annotations

import os
import requests


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _slack_enabled() -> bool:
    return _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")) and _truthy(os.getenv("LUMENAI_SLACK_ENABLED", "false"))


def notify_retention_event(summary: dict) -> dict:
    channel = os.getenv("LUMENAI_RETENTION_NOTIFY_CHANNEL", "slack").strip().lower()

    blocked = int(summary.get("totals", {}).get("retention_blocks", 0) or 0)
    failures = int(summary.get("totals", {}).get("failures", 0) or 0)
    deleted = (
        int(summary.get("totals", {}).get("inspections_deleted", 0) or 0)
        + int(summary.get("totals", {}).get("audit_logs_deleted", 0) or 0)
        + int(summary.get("totals", {}).get("digest_deliveries_deleted", 0) or 0)
    )

    if channel != "slack":
        return {"sent": False, "status_code": "UNSUPPORTED", "reason": "Only slack notification is scaffolded"}

    if not _slack_enabled():
        return {"sent": False, "status_code": "DISABLED", "reason": "Slack notifications disabled"}

    webhook = os.getenv("LUMENAI_SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        return {"sent": False, "status_code": "NOT_CONFIGURED", "reason": "Slack webhook not configured"}

    text = (
        "LumenAI Retention Enforcement Report\n"
        f"- Deleted artifacts: {deleted}\n"
        f"- Blocked by legal hold: {blocked}\n"
        f"- Failures: {failures}\n"
        f"- Evaluated at: {summary.get('evaluated_at', '')}"
    )

    try:
        resp = requests.post(webhook, json={"text": text}, timeout=20)
        ok = resp.status_code == 200 and resp.text.strip().lower() == "ok"
        return {
            "sent": ok,
            "status_code": resp.status_code,
            "reason": "" if ok else resp.text[:1000],
        }
    except Exception as e:
        return {
            "sent": False,
            "status_code": "REQUEST_ERROR",
            "reason": str(e),
        }
