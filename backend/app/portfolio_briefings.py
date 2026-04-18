from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.portfolio_dashboard import executive_portfolio_dashboard


def _compact(value: Any, limit: int = 4000) -> str:
    return json.dumps(value, default=str)[:limit]


def _portfolio_exec_summary(period_label: str, portfolio: dict, qbr_rollup: dict) -> str:
    tenant_count = portfolio.get("tenant_count", 0)
    status_counts = portfolio.get("status_counts", {})
    risk_accounts = portfolio.get("top_risk_accounts", [])

    return (
        f"Portfolio review for {period_label}. "
        f"The portfolio currently includes {tenant_count} customer tenants. "
        f"Status mix includes {status_counts.get('healthy', 0)} healthy, "
        f"{status_counts.get('watch', 0)} watch, and "
        f"{status_counts.get('at_risk', 0)} at-risk accounts. "
        f"Cross-account QBR operations currently show {qbr_rollup.get('review_count', 0)} reviews, "
        f"{qbr_rollup.get('export_count', 0)} exports, and "
        f"{qbr_rollup.get('delivery_count', 0)} deliveries. "
        f"Top-risk accounts under current review total {len(risk_accounts)}."
    )


def _portfolio_board_narrative(period_label: str, dashboard: dict) -> str:
    portfolio = dashboard.get("portfolio", {})
    qbr_rollup = dashboard.get("qbr_rollup", {})
    top_risk = portfolio.get("top_risk_accounts", [])[:5]

    lines = [
        f"Board-level portfolio briefing for {period_label}.",
        "",
        f"Total tenants: {portfolio.get('tenant_count', 0)}.",
        f"QBR review count: {qbr_rollup.get('review_count', 0)}.",
        f"QBR export count: {qbr_rollup.get('export_count', 0)}.",
        f"Scheduled QBR jobs: {qbr_rollup.get('scheduled_count', 0)}.",
        f"QBR deliveries: {qbr_rollup.get('delivery_count', 0)}.",
        "",
        "Top-risk account posture:",
    ]

    if not top_risk:
        lines.append("No top-risk accounts identified.")
    else:
        for item in top_risk:
            lines.append(
                f"- {item.get('tenant_name')}: status {item.get('operating_status')}, "
                f"health {item.get('health_score')}, "
                f"governance exceptions {item.get('governance_exception_count')}, "
                f"open renewal cases {item.get('open_renewal_cases')}."
            )

    lines.extend([
        "",
        "Board focus should remain on customer health stabilization, go-live readiness, governance exception closure, and QBR operating cadence across the portfolio.",
    ])
    return "\n".join(lines)


def _top_risks(dashboard: dict) -> list[str]:
    risks: list[str] = []
    for item in dashboard.get("portfolio", {}).get("top_risk_accounts", [])[:10]:
        tenant_name = item.get("tenant_name", "Unknown Tenant")
        if item.get("operating_status") in {"at_risk", "implementation_in_progress"}:
            risks.append(f"{tenant_name}: operating status is {item.get('operating_status')}")
        if item.get("governance_exception_count", 0) > 0:
            risks.append(f"{tenant_name}: governance exceptions remain open")
        if item.get("open_renewal_cases", 0) > 0:
            risks.append(f"{tenant_name}: renewal-risk cases remain open")
        if not item.get("go_live_ready", False):
            risks.append(f"{tenant_name}: go-live readiness not complete")
    return risks[:12]


def _next_steps(dashboard: dict) -> list[str]:
    steps = [
        "Review top-risk accounts with executive leadership.",
        "Stabilize accounts with open governance exceptions and renewal-risk cases.",
        "Increase scheduled QBR coverage for high-priority tenants.",
        "Drive implementation closure for accounts not yet go-live ready.",
        "Use portfolio rollups to prioritize customer success intervention.",
    ]

    top_risk = dashboard.get("portfolio", {}).get("top_risk_accounts", [])[:5]
    for item in top_risk:
        recs = item.get("top_recommendations", [])[:2]
        for rec in recs:
            steps.append(f"{item.get('tenant_name')}: {rec}")

    seen = set()
    ordered = []
    for item in steps:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered[:12]


def generate_portfolio_briefing(
    db: Session,
    *,
    briefing_type: str = "board_portfolio",
    audience: str = "board",
    period_label: str = "",
) -> models.PortfolioBriefing:
    dashboard = executive_portfolio_dashboard(db)
    portfolio = dashboard.get("portfolio", {})
    qbr_rollup = dashboard.get("qbr_rollup", {})

    title = f"Portfolio Board Briefing — {period_label or 'Current Period'}"
    executive_summary = _portfolio_exec_summary(period_label or "Current Period", portfolio, qbr_rollup)
    board_narrative = _portfolio_board_narrative(period_label or "Current Period", dashboard)
    top_risks = _top_risks(dashboard)
    next_steps = _next_steps(dashboard)

    summary = {
        "tenant_count": portfolio.get("tenant_count", 0),
        "status_counts": portfolio.get("status_counts", {}),
        "review_count": qbr_rollup.get("review_count", 0),
        "export_count": qbr_rollup.get("export_count", 0),
        "scheduled_count": qbr_rollup.get("scheduled_count", 0),
        "delivery_count": qbr_rollup.get("delivery_count", 0),
    }

    row = models.PortfolioBriefing(
        briefing_type=briefing_type,
        audience=audience,
        period_label=period_label or "Current Period",
        title=title,
        executive_summary=executive_summary[:12000],
        board_narrative=board_narrative[:12000],
        summary_json=_compact(summary),
        top_risks_json=_compact(top_risks),
        next_steps_json=_compact(next_steps),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
