from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _today() -> date:
    return datetime.now(timezone.utc).date()


def ensure_portfolio_tenant_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS portfolio_tenants (
                id SERIAL PRIMARY KEY,
                tenant_name VARCHAR(255) NOT NULL,
                industry VARCHAR(255) NOT NULL DEFAULT 'healthcare',
                go_live_status VARCHAR(100) NOT NULL DEFAULT 'not_started',
                health_status VARCHAR(100) NOT NULL DEFAULT 'watch',
                health_score INTEGER NOT NULL DEFAULT 70,
                renewal_risk BOOLEAN NOT NULL DEFAULT FALSE,
                implementation_risk BOOLEAN NOT NULL DEFAULT FALSE,
                governance_exception_count INTEGER NOT NULL DEFAULT 0,
                last_qbr_date DATE,
                next_qbr_date DATE,
                executive_owner VARCHAR(255) NOT NULL DEFAULT '',
                customer_success_owner VARCHAR(255) NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    db.commit()


def calculate_tenant_health(
    go_live_status: str,
    renewal_risk: bool,
    implementation_risk: bool,
    governance_exception_count: int,
    next_qbr_date: str | date | None,
) -> tuple[int, str]:
    score = 100

    if renewal_risk:
        score -= 25

    if implementation_risk:
        score -= 20

    if go_live_status not in {"live", "go_live_complete", "active"}:
        score -= 15

    exception_penalty = min(max(governance_exception_count, 0) * 5, 25)
    score -= exception_penalty

    if next_qbr_date:
        try:
            qbr_date = next_qbr_date if isinstance(next_qbr_date, date) else date.fromisoformat(str(next_qbr_date))
            if qbr_date < _today():
                score -= 10
        except Exception:
            pass

    score = max(0, min(100, score))

    if score >= 80:
        status = "healthy"
    elif score >= 60:
        status = "watch"
    elif score >= 40:
        status = "at_risk"
    else:
        status = "critical"

    return score, status


def create_portfolio_tenant(
    db: Session,
    tenant_name: str,
    industry: str = "healthcare",
    go_live_status: str = "not_started",
    renewal_risk: bool = False,
    implementation_risk: bool = False,
    governance_exception_count: int = 0,
    last_qbr_date: str | None = None,
    next_qbr_date: str | None = None,
    executive_owner: str = "",
    customer_success_owner: str = "",
    notes: str = "",
) -> dict[str, Any]:
    ensure_portfolio_tenant_table(db)

    health_score, health_status = calculate_tenant_health(
        go_live_status=go_live_status,
        renewal_risk=renewal_risk,
        implementation_risk=implementation_risk,
        governance_exception_count=governance_exception_count,
        next_qbr_date=next_qbr_date,
    )

    row = (
        db.execute(
            text(
                """
                INSERT INTO portfolio_tenants (
                    tenant_name,
                    industry,
                    go_live_status,
                    health_status,
                    health_score,
                    renewal_risk,
                    implementation_risk,
                    governance_exception_count,
                    last_qbr_date,
                    next_qbr_date,
                    executive_owner,
                    customer_success_owner,
                    notes
                )
                VALUES (
                    :tenant_name,
                    :industry,
                    :go_live_status,
                    :health_status,
                    :health_score,
                    :renewal_risk,
                    :implementation_risk,
                    :governance_exception_count,
                    :last_qbr_date,
                    :next_qbr_date,
                    :executive_owner,
                    :customer_success_owner,
                    :notes
                )
                RETURNING *
                """
            ),
            {
                "tenant_name": tenant_name,
                "industry": industry,
                "go_live_status": go_live_status,
                "health_status": health_status,
                "health_score": health_score,
                "renewal_risk": renewal_risk,
                "implementation_risk": implementation_risk,
                "governance_exception_count": governance_exception_count,
                "last_qbr_date": last_qbr_date,
                "next_qbr_date": next_qbr_date,
                "executive_owner": executive_owner,
                "customer_success_owner": customer_success_owner,
                "notes": notes,
            },
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)


def list_portfolio_tenants(db: Session, limit: int = 100) -> list[dict[str, Any]]:
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

    return [dict(row) for row in rows]


def get_portfolio_tenant(db: Session, tenant_id: int) -> dict[str, Any] | None:
    ensure_portfolio_tenant_table(db)

    row = (
        db.execute(
            text(
                """
                SELECT *
                FROM portfolio_tenants
                WHERE id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        .mappings()
        .first()
    )

    return dict(row) if row else None


def update_portfolio_tenant(db: Session, tenant_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
    ensure_portfolio_tenant_table(db)

    current = get_portfolio_tenant(db, tenant_id)
    if not current:
        return None

    allowed = {
        "tenant_name",
        "industry",
        "go_live_status",
        "renewal_risk",
        "implementation_risk",
        "governance_exception_count",
        "last_qbr_date",
        "next_qbr_date",
        "executive_owner",
        "customer_success_owner",
        "notes",
    }

    clean = {key: value for key, value in updates.items() if key in allowed}

    merged = {**current, **clean}
    health_score, health_status = calculate_tenant_health(
        go_live_status=str(merged.get("go_live_status") or "not_started"),
        renewal_risk=bool(merged.get("renewal_risk")),
        implementation_risk=bool(merged.get("implementation_risk")),
        governance_exception_count=int(merged.get("governance_exception_count") or 0),
        next_qbr_date=merged.get("next_qbr_date"),
    )

    clean["health_score"] = health_score
    clean["health_status"] = health_status

    set_clause = ", ".join([f"{key} = :{key}" for key in clean.keys()])
    params = {**clean, "tenant_id": tenant_id}

    row = (
        db.execute(
            text(
                f"""
                UPDATE portfolio_tenants
                SET {set_clause},
                    updated_at = NOW()
                WHERE id = :tenant_id
                RETURNING *
                """
            ),
            params,
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row) if row else None


def rescore_portfolio_tenants(db: Session) -> list[dict[str, Any]]:
    ensure_portfolio_tenant_table(db)

    tenants = list_portfolio_tenants(db, limit=10000)
    updated = []

    for tenant in tenants:
        result = update_portfolio_tenant(db, int(tenant["id"]), {})
        if result:
            updated.append(result)

    return updated


def portfolio_tenant_rollup(db: Session) -> dict[str, Any]:
    ensure_portfolio_tenant_table(db)

    rows = (
        db.execute(
            text(
                """
                SELECT health_status, COUNT(*) AS count
                FROM portfolio_tenants
                GROUP BY health_status
                """
            )
        )
        .mappings()
        .all()
    )

    status_counts = {row["health_status"]: int(row["count"]) for row in rows}

    tenant_count = int(
        db.execute(text("SELECT COUNT(*) FROM portfolio_tenants")).scalar() or 0
    )

    qbr_overdue_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM portfolio_tenants
                WHERE next_qbr_date IS NOT NULL
                  AND next_qbr_date < CURRENT_DATE
                """
            )
        ).scalar()
        or 0
    )

    governance_exception_total = int(
        db.execute(
            text(
                """
                SELECT COALESCE(SUM(governance_exception_count), 0)
                FROM portfolio_tenants
                """
            )
        ).scalar()
        or 0
    )

    top_risks = (
        db.execute(
            text(
                """
                SELECT id, tenant_name, health_status, health_score, renewal_risk,
                       implementation_risk, governance_exception_count,
                       next_qbr_date, executive_owner, customer_success_owner
                FROM portfolio_tenants
                ORDER BY health_score ASC, governance_exception_count DESC, id DESC
                LIMIT 5
                """
            )
        )
        .mappings()
        .all()
    )

    return {
        "tenant_count": tenant_count,
        "status_counts": status_counts,
        "healthy_count": status_counts.get("healthy", 0),
        "watch_count": status_counts.get("watch", 0),
        "at_risk_count": status_counts.get("at_risk", 0),
        "critical_count": status_counts.get("critical", 0),
        "qbr_overdue_count": qbr_overdue_count,
        "governance_exception_total": governance_exception_total,
        "top_risks": [dict(row) for row in top_risks],
    }


def generate_board_briefing_from_portfolio_tenants(
    db: Session,
    period_label: str,
    audience: str = "board",
) -> dict[str, Any]:
    ensure_portfolio_tenant_table(db)
    rollup = portfolio_tenant_rollup(db)

    top_risks = rollup["top_risks"]

    risk_names = [risk["tenant_name"] for risk in top_risks if risk["health_status"] in {"at_risk", "critical", "watch"}]
    risk_sentence = ", ".join(risk_names) if risk_names else "No top-risk accounts identified"

    summary = {
        "tenant_count": rollup["tenant_count"],
        "status_counts": rollup["status_counts"],
        "healthy_count": rollup["healthy_count"],
        "watch_count": rollup["watch_count"],
        "at_risk_count": rollup["at_risk_count"],
        "critical_count": rollup["critical_count"],
        "qbr_overdue_count": rollup["qbr_overdue_count"],
        "governance_exception_total": rollup["governance_exception_total"],
    }

    next_steps = [
        "Review top-risk accounts with executive leadership.",
        "Close open governance exceptions for watch, at-risk, and critical tenants.",
        "Prioritize overdue QBRs and executive check-ins.",
        "Stabilize tenants with implementation or go-live risk.",
        "Use portfolio health scoring to focus customer success interventions.",
    ]

    executive_summary = (
        f"Portfolio review for {period_label}. "
        f"The portfolio currently includes {rollup['tenant_count']} customer tenants. "
        f"Status mix includes {rollup['healthy_count']} healthy, {rollup['watch_count']} watch, "
        f"{rollup['at_risk_count']} at-risk, and {rollup['critical_count']} critical accounts. "
        f"Open governance exceptions total {rollup['governance_exception_total']}. "
        f"QBR overdue accounts total {rollup['qbr_overdue_count']}."
    )

    board_narrative = (
        f"Board-level customer portfolio briefing for {period_label}.\n\n"
        f"Total tenants: {rollup['tenant_count']}.\n"
        f"Healthy: {rollup['healthy_count']}.\n"
        f"Watch: {rollup['watch_count']}.\n"
        f"At-risk: {rollup['at_risk_count']}.\n"
        f"Critical: {rollup['critical_count']}.\n"
        f"Governance exceptions: {rollup['governance_exception_total']}.\n"
        f"QBR overdue accounts: {rollup['qbr_overdue_count']}.\n\n"
        f"Top-risk account posture:\n{risk_sentence}.\n\n"
        "Board focus should remain on customer health stabilization, QBR operating cadence, "
        "go-live readiness, governance exception closure, and renewal-risk mitigation."
    )

    row = (
        db.execute(
            text(
                """
                INSERT INTO portfolio_briefings (
                    briefing_type,
                    audience,
                    period_label,
                    title,
                    executive_summary,
                    board_narrative,
                    summary_json,
                    top_risks_json,
                    next_steps_json,
                    created_at
                )
                VALUES (
                    'board_portfolio',
                    :audience,
                    :period_label,
                    :title,
                    :executive_summary,
                    :board_narrative,
                    :summary_json,
                    :top_risks_json,
                    :next_steps_json,
                    NOW()
                )
                RETURNING *
                """
            ),
            {
                "audience": audience,
                "period_label": period_label,
                "title": f"Customer Portfolio Board Briefing — {period_label}",
                "executive_summary": executive_summary,
                "board_narrative": board_narrative,
                "summary_json": json.dumps(summary, default=str),
                "top_risks_json": json.dumps(top_risks, default=str),
                "next_steps_json": json.dumps(next_steps),
            },
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)
