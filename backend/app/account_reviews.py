from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.customer_health import build_customer_health_summary
from app.customer_operations_hub import operations_hub_summary
from app.customer_success import renewal_risk_summary
from app.db import models
from app.governance_sla import sla_dashboard
from app.implementation_readiness import readiness_summary
from app.release_governance_dashboard import dashboard_summary as release_dashboard_summary


def _compact(value: Any, limit: int = 4000) -> str:
    return json.dumps(value, default=str)[:limit]


def _status_word(score: int) -> str:
    if score >= 80:
        return "strong"
    if score >= 60:
        return "stable with some risk"
    return "at risk"


def _build_risks(health: dict, readiness: dict, governance: dict, renewal: dict, sla: dict) -> list[str]:
    risks: list[str] = []

    for flag in health.get("risk_flags", []):
        risks.append(flag)

    if not readiness.get("go_live_ready", False):
        risks.append("go_live_not_ready")
    if readiness.get("blocked_count", 0) > 0:
        risks.append("implementation_blockers_open")
    if governance.get("exception_count", 0) > 0:
        risks.append("governance_exceptions_open")
    if renewal.get("open_case_count", 0) > 0:
        risks.append("renewal_risk_cases_open")
    if sla.get("open_count", 0) > 0:
        risks.append("sla_events_open")

    seen = set()
    ordered = []
    for item in risks:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _build_next_steps(ops: dict, health: dict, readiness: dict) -> list[str]:
    steps = list(ops.get("top_recommendations", [])[:6])

    if health.get("summary", {}).get("distribution_list_count", 0) == 0:
        steps.append("Configure executive distribution lists for governed review delivery.")
    if health.get("summary", {}).get("notification_template_count", 0) == 0:
        steps.append("Configure notification templates for executive and governance workflows.")
    if not readiness.get("go_live_ready", False):
        steps.append("Complete go-live checkpoints and close required readiness items.")

    seen = set()
    ordered = []
    for item in steps:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered[:8]


def _executive_summary(tenant_name: str, period_label: str, health: dict, readiness: dict, governance: dict, renewal: dict) -> str:
    health_score = int(health.get("health_score", 0))
    status_word = _status_word(health_score)

    return (
        f"{tenant_name} is in a {status_word} position for {period_label}. "
        f"Current health score is {health_score}, implementation readiness is {readiness.get('readiness_score', 0)}%, "
        f"go-live ready status is {'yes' if readiness.get('go_live_ready', False) else 'no'}, "
        f"open governance exceptions total {governance.get('exception_count', 0)}, "
        f"and open renewal-risk cases total {renewal.get('open_case_count', 0)}."
    )


def _qbr_narrative(tenant_name: str, period_label: str, health: dict, readiness: dict, governance: dict, sla: dict, renewal: dict, ops: dict) -> str:
    return (
        f"Quarterly business review for {tenant_name} covering {period_label}.\n\n"
        f"Health status: {health.get('health_status', 'unknown')} with score {health.get('health_score', 0)}. "
        f"Usage score is {health.get('usage_score', 0)}, governance score is {health.get('governance_score', 0)}, "
        f"and adoption score is {health.get('adoption_score', 0)}.\n\n"
        f"Implementation readiness is {readiness.get('readiness_score', 0)}% with "
        f"{readiness.get('blocked_count', 0)} blocked items. "
        f"Go-live ready: {'yes' if readiness.get('go_live_ready', False) else 'no'}.\n\n"
        f"Governance exceptions: {governance.get('exception_count', 0)}. "
        f"Open SLA events: {sla.get('open_count', 0)}. "
        f"Open renewal-risk cases: {renewal.get('open_case_count', 0)}.\n\n"
        f"Operating status from the customer operations hub is {ops.get('operating_status', 'unknown')}."
    )


def generate_account_review_packet(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    review_type: str = "qbr",
    period_label: str = "",
) -> models.AccountReviewPacket:
    health = build_customer_health_summary(db, tenant_id, tenant_name, 30)
    readiness = readiness_summary(db, tenant_id, tenant_name)
    governance = release_dashboard_summary(db, tenant_id, tenant_name)
    renewal = renewal_risk_summary(db, tenant_id, tenant_name)
    sla = sla_dashboard(db, tenant_id, tenant_name)
    ops = operations_hub_summary(db, tenant_id, tenant_name)

    risks = _build_risks(health, readiness, governance, renewal, sla)
    next_steps = _build_next_steps(ops, health, readiness)

    title = f"{tenant_name} — {review_type.upper()} Review"
    executive_summary = _executive_summary(tenant_name, period_label, health, readiness, governance, renewal)
    qbr_narrative = _qbr_narrative(tenant_name, period_label, health, readiness, governance, sla, renewal, ops)

    summary = {
        "health_score": health.get("health_score", 0),
        "health_status": health.get("health_status", "unknown"),
        "usage_score": health.get("usage_score", 0),
        "governance_score": health.get("governance_score", 0),
        "adoption_score": health.get("adoption_score", 0),
        "readiness_score": readiness.get("readiness_score", 0),
        "go_live_ready": readiness.get("go_live_ready", False),
        "governance_exception_count": governance.get("exception_count", 0),
        "open_sla_count": sla.get("open_count", 0),
        "open_renewal_cases": renewal.get("open_case_count", 0),
        "operating_status": ops.get("operating_status", "unknown"),
    }

    row = models.AccountReviewPacket(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        review_type=review_type,
        period_label=period_label,
        title=title,
        executive_summary=executive_summary[:12000],
        qbr_narrative=qbr_narrative[:12000],
        summary_json=_compact(summary),
        risks_json=_compact(risks),
        next_steps_json=_compact(next_steps),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
