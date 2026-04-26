from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.portfolio_tenants import ensure_portfolio_tenant_table, get_portfolio_tenant


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


def build_tenant_insight(tenant: dict[str, Any]) -> dict[str, Any]:
    risk_drivers: list[str] = []
    recommended_actions: list[str] = []

    tenant_name = tenant.get("tenant_name", "Tenant")
    health_status = str(tenant.get("health_status") or "watch")
    health_score = int(tenant.get("health_score") or 0)
    go_live_status = str(tenant.get("go_live_status") or "not_started")
    governance_exception_count = int(tenant.get("governance_exception_count") or 0)

    renewal_risk = bool(tenant.get("renewal_risk"))
    implementation_risk = bool(tenant.get("implementation_risk"))
    next_qbr_date = _parse_date(tenant.get("next_qbr_date"))

    if renewal_risk:
        risk_drivers.append("renewal risk is active")
        recommended_actions.append("Schedule executive renewal-risk review and define retention actions.")

    if implementation_risk:
        risk_drivers.append("implementation risk is active")
        recommended_actions.append("Create implementation stabilization plan with accountable owner and due date.")

    if go_live_status not in {"live", "go_live_complete", "active"}:
        risk_drivers.append(f"go-live status is {go_live_status}")
        recommended_actions.append("Confirm go-live readiness barriers and escalate blockers.")

    if governance_exception_count > 0:
        risk_drivers.append(f"{governance_exception_count} governance exception(s) remain open")
        recommended_actions.append("Close governance exceptions through a tracked remediation plan.")

    if next_qbr_date and next_qbr_date < _today():
        risk_drivers.append("QBR is overdue")
        recommended_actions.append("Schedule overdue QBR and document executive follow-up actions.")

    if health_score < 60:
        recommended_actions.append("Review account in weekly executive risk huddle until stabilized.")

    if not risk_drivers:
        risk_drivers.append("no material risk drivers identified")
        recommended_actions.append("Maintain standard customer success cadence and QBR schedule.")

    board_attention_required = (
        health_status in {"critical", "at_risk"}
        or renewal_risk
        or implementation_risk
        or governance_exception_count >= 3
        or health_score < 60
    )

    if health_status == "critical":
        risk_level = "critical"
    elif health_status == "at_risk":
        risk_level = "high"
    elif health_status == "watch":
        risk_level = "moderate"
    else:
        risk_level = "low"

    executive_summary = (
        f"{tenant_name} is currently classified as {health_status} "
        f"with a health score of {health_score}. "
        f"Primary risk drivers include {', '.join(risk_drivers)}."
    )

    board_narrative = (
        f"{tenant_name} requires {'board/executive attention' if board_attention_required else 'standard monitoring'} "
        f"based on its current portfolio health posture. "
        f"The account is scored at {health_score}, categorized as {health_status}, "
        f"and has {governance_exception_count} governance exception(s). "
        f"Recommended focus: {'; '.join(recommended_actions)}"
    )

    return {
        "tenant_id": tenant.get("id"),
        "tenant_name": tenant_name,
        "health_status": health_status,
        "health_score": health_score,
        "risk_level": risk_level,
        "board_attention_required": board_attention_required,
        "risk_drivers": risk_drivers,
        "recommended_actions": recommended_actions,
        "executive_summary": executive_summary,
        "board_narrative": board_narrative,
        "executive_owner": tenant.get("executive_owner"),
        "customer_success_owner": tenant.get("customer_success_owner"),
        "next_qbr_date": str(tenant.get("next_qbr_date") or ""),
    }


def get_tenant_insight(db: Session, tenant_id: int) -> dict[str, Any] | None:
    ensure_portfolio_tenant_table(db)
    tenant = get_portfolio_tenant(db, tenant_id)
    if not tenant:
        return None
    return build_tenant_insight(tenant)


def get_top_risk_tenant_insights(db: Session, limit: int = 10) -> list[dict[str, Any]]:
    ensure_portfolio_tenant_table(db)

    rows = (
        db.execute(
            text(
                """
                SELECT *
                FROM portfolio_tenants
                ORDER BY health_score ASC, governance_exception_count DESC, id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )

    return [build_tenant_insight(dict(row)) for row in rows]


def portfolio_insight_rollup(db: Session) -> dict[str, Any]:
    insights = get_top_risk_tenant_insights(db, limit=1000)

    board_attention = [item for item in insights if item["board_attention_required"]]
    critical = [item for item in insights if item["health_status"] == "critical"]
    high_or_moderate = [item for item in insights if item["risk_level"] in {"high", "moderate"}]

    return {
        "tenant_insight_count": len(insights),
        "board_attention_count": len(board_attention),
        "critical_count": len(critical),
        "high_or_moderate_count": len(high_or_moderate),
        "top_board_attention_items": board_attention[:5],
        "executive_focus_summary": (
            f"{len(board_attention)} tenant(s) require executive attention. "
            f"{len(critical)} tenant(s) are critical. "
            f"{len(high_or_moderate)} tenant(s) are high or moderate risk."
        ),
    }
