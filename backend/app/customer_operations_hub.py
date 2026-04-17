from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.customer_health import build_customer_health_summary, create_health_snapshot
from app.customer_success import renewal_risk_summary, run_renewal_risk
from app.governance_command_center import build_work_items, command_center_summary
from app.governance_sla_scanner import run_scanner_once
from app.implementation_readiness import readiness_summary
from app.release_governance_dashboard import dashboard_summary as release_dashboard_summary


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def operating_status(health_score: int, readiness_score: float, go_live_ready: bool, open_cases: int, exception_count: int) -> str:
    if not go_live_ready:
        return "implementation_in_progress"
    if health_score < 50 or open_cases > 2 or exception_count > 3:
        return "at_risk"
    if health_score < 75:
        return "watch"
    return "healthy"


def top_recommendations(
    *,
    health: dict,
    readiness: dict,
    governance: dict,
    renewal: dict,
) -> list[str]:
    recs: list[str] = []

    if not readiness.get("go_live_ready", False):
        recs.append("Complete blocked implementation items and finish go-live checkpoints.")
    if governance.get("exception_count", 0) > 0:
        recs.append("Resolve release governance exceptions and blocked packet workflows.")
    if health.get("health_score", 0) < 60:
        recs.append("Increase adoption with scheduled reports, scorecards, and leadership packets.")
    if renewal.get("open_case_count", 0) > 0:
        recs.append("Work open renewal-risk cases and execute customer success playbooks.")
    if health.get("summary", {}).get("distribution_list_count", 0) == 0:
        recs.append("Configure executive distribution lists for governed delivery.")
    if health.get("summary", {}).get("notification_template_count", 0) == 0:
        recs.append("Configure notification templates to improve automation maturity.")
    if health.get("summary", {}).get("open_sla_count", 0) > 0:
        recs.append("Clear overdue SLA exceptions and validate escalation thresholds.")

    if not recs:
        recs.append("Tenant is operating well. Maintain cadence and continue monitoring adoption and governance.")

    return recs[:8]


def tenant_status_summary(db: Session, tenant_id: str, tenant_name: str) -> dict:
    health = build_customer_health_summary(db, tenant_id, tenant_name, 30)
    readiness = readiness_summary(db, tenant_id, tenant_name)
    governance = release_dashboard_summary(db, tenant_id, tenant_name)
    renewal = renewal_risk_summary(db, tenant_id, tenant_name)
    command = command_center_summary(db, tenant_id, tenant_name)

    status = operating_status(
        health_score=int(health.get("health_score", 0)),
        readiness_score=float(readiness.get("readiness_score", 0)),
        go_live_ready=bool(readiness.get("go_live_ready", False)),
        open_cases=int(renewal.get("open_case_count", 0)),
        exception_count=int(governance.get("exception_count", 0)),
    )

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "generated_at": _now(),
        "operating_status": status,
        "health": {
            "score": health.get("health_score", 0),
            "status": health.get("health_status", "unknown"),
            "risk_flags": health.get("risk_flags", []),
        },
        "readiness": {
            "score": readiness.get("readiness_score", 0),
            "checkpoint_score": readiness.get("checkpoint_score", 0),
            "go_live_ready": readiness.get("go_live_ready", False),
            "blocked_count": readiness.get("blocked_count", 0),
        },
        "governance": {
            "exception_count": governance.get("exception_count", 0),
            "readiness_counts": governance.get("readiness_counts", {}),
        },
        "renewal": {
            "open_case_count": renewal.get("open_case_count", 0),
            "health_status": renewal.get("health_status", "unknown"),
        },
        "command_center": {
            "work_item_count": command.get("work_items", {}).get("count", 0),
            "critical_count": command.get("work_items", {}).get("critical_count", 0),
            "warning_count": command.get("work_items", {}).get("warning_count", 0),
        },
        "top_recommendations": top_recommendations(
            health=health,
            readiness=readiness,
            governance=governance,
            renewal=renewal,
        ),
    }


def tenant_work_queue(db: Session, tenant_id: str, tenant_name: str) -> dict:
    command = command_center_summary(db, tenant_id, tenant_name)
    readiness = readiness_summary(db, tenant_id, tenant_name)
    renewal = renewal_risk_summary(db, tenant_id, tenant_name)

    items = []

    for item in command.get("work_items", {}).get("items", []):
        items.append({
            "source": "governance",
            "priority": "high" if item.get("severity") == "critical" else "medium",
            "title": item.get("title"),
            "resource_type": item.get("resource_type"),
            "resource_id": item.get("resource_id"),
            "reason": item.get("reason"),
            "recommended_action": item.get("recommended_action"),
        })

    for item in readiness.get("items", []):
        if item.get("status") in {"blocked", "not_started"} and item.get("is_required"):
            items.append({
                "source": "implementation",
                "priority": "high" if item.get("status") == "blocked" else "medium",
                "title": item.get("title"),
                "resource_type": "implementation_readiness_item",
                "resource_id": item.get("id"),
                "reason": item.get("blocker_reason") or f"Status is {item.get('status')}",
                "recommended_action": "Complete or unblock this required go-live item.",
            })

    for case in renewal.get("cases", []):
        if case.get("status") == "open":
            items.append({
                "source": "customer_success",
                "priority": "high" if case.get("risk_level") in {"critical", "high"} else "medium",
                "title": f"Renewal Risk Case #{case.get('id')}",
                "resource_type": "renewal_risk_case",
                "resource_id": case.get("id"),
                "reason": case.get("trigger_reason"),
                "recommended_action": ", ".join((case.get("recommended_actions") or [])[:2]) or "Work the customer success playbook.",
            })

    priority_order = {"high": 0, "medium": 1, "low": 2}
    items = sorted(items, key=lambda x: (priority_order.get(x["priority"], 9), x["source"], str(x["title"])))

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "generated_at": _now(),
        "count": len(items),
        "items": items[:100],
    }


def operations_hub_summary(db: Session, tenant_id: str, tenant_name: str) -> dict:
    status = tenant_status_summary(db, tenant_id, tenant_name)
    queue = tenant_work_queue(db, tenant_id, tenant_name)

    return {
        **status,
        "work_queue": {
            "count": queue["count"],
            "items": queue["items"][:20],
        },
    }


def run_health_snapshot_action(db: Session, tenant_id: str, tenant_name: str) -> dict:
    row, summary = create_health_snapshot(db, tenant_id, tenant_name, 30)
    return {
        "snapshot_id": row.id,
        "health_score": summary["health_score"],
        "health_status": summary["health_status"],
    }


def run_renewal_risk_action(db: Session, tenant_id: str, tenant_name: str) -> dict:
    return run_renewal_risk(db, tenant_id, tenant_name)


def run_sla_scan_action() -> dict:
    return run_scanner_once()
