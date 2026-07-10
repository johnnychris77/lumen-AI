"""v4.6 — Project Vanguard, Section 4: Operational Intelligence.

Composes real signals already computed by `or_connect_service.
executive_dashboard` (OR delays, repair backlog, inspection turnaround,
bottlenecks), `pulse_kpi_service.live_kpis` (inspection quality/
throughput/instrument availability proxies), and `competency_service.
technician_quality_dashboard` (staffing) into one operational snapshot —
nothing here recomputes any of those functions' own arithmetic.

"Correlate" (Section 4's literal word) is implemented as a real Pearson
correlation coefficient between two aligned weekly time series (repair
backlog vs. delayed-case count) — not a fabricated relationship, and not
a claim of causation (the surrounding `human_review_required`/disclaimer
convention applies here as everywhere else in this codebase).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.or_connect import REPAIR_IN_PROGRESS, REPAIR_PENDING, CaseReadinessScoreRecord, RepairRequest
from app.services import competency_service, or_connect_service, pulse_kpi_service


def _week_key(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _pearson_correlation(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    return round(cov / (var_x ** 0.5 * var_y ** 0.5), 3)


def _repair_backlog_vs_delayed_cases_correlation(db: Session, tenant_id: str, *, weeks: int = 12) -> dict:
    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    repairs = db.query(RepairRequest).filter(
        RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since,
        RepairRequest.status.in_((REPAIR_PENDING, REPAIR_IN_PROGRESS)),
    ).all()
    scores = db.query(CaseReadinessScoreRecord).filter(
        CaseReadinessScoreRecord.tenant_id == tenant_id, CaseReadinessScoreRecord.created_at >= since,
    ).all()

    repair_by_week: dict[str, int] = {}
    for r in repairs:
        repair_by_week[_week_key(r.created_at)] = repair_by_week.get(_week_key(r.created_at), 0) + 1

    delayed_by_week: dict[str, int] = {}
    for s in scores:
        if s.score < 70:
            delayed_by_week[_week_key(s.created_at)] = delayed_by_week.get(_week_key(s.created_at), 0) + 1

    all_weeks = sorted(set(repair_by_week) | set(delayed_by_week))
    repair_series = [repair_by_week.get(w, 0) for w in all_weeks]
    delayed_series = [delayed_by_week.get(w, 0) for w in all_weeks]

    return {
        "weeks_observed": len(all_weeks),
        "correlation_coefficient": _pearson_correlation(repair_series, delayed_series),
        "note": (
            "Pearson correlation between weekly open-repair counts and weekly delayed-case-readiness-score "
            "counts. A correlation is not causation — human review required before acting on this signal."
            if all_weeks else "Not enough weekly data yet to compute a correlation."
        ),
    }


def operational_intelligence(db: Session, tenant_id: str) -> dict:
    executive = or_connect_service.executive_dashboard(db, tenant_id)
    kpis = pulse_kpi_service.live_kpis(db, tenant_id)
    staffing = competency_service.technician_quality_dashboard(db, tenant_id)

    return {
        "inspection_quality": {
            "ai_confidence_avg": kpis["ai_confidence_avg"],
            "coverage_pct_avg": kpis["coverage_pct_avg"],
            "high_risk_findings_count": kpis["high_risk_findings_count"],
        },
        "or_delays": {
            "delay_causes": executive["delay_causes"],
            "operational_bottlenecks": executive["operational_bottlenecks"],
        },
        "repair_backlog": {
            "repair_queue_length": kpis["repair_queue_length"],
            "cases_with_open_repairs": executive["repair_impact"]["cases_with_open_repairs"],
            "avg_repair_turnaround_days": executive["repair_impact"]["avg_repair_turnaround_days"],
        },
        "instrument_availability": {
            "digital_twin_health_pct": kpis["digital_twin_health_pct"],
        },
        "staffing": {
            "technician_count": len(staffing["technicians"]),
            "avg_ai_agreement_pct": (
                round(sum(t["avg_ai_confidence_pct"] or 0 for t in staffing["technicians"]) / len(staffing["technicians"]), 1)
                if staffing["technicians"] else None
            ),
        },
        "throughput": {
            "inspection_throughput": kpis["inspection_throughput"],
        },
        "readiness": {
            "case_readiness_trend": executive["case_readiness_trend"],
        },
        "repair_backlog_vs_delayed_cases_correlation": _repair_backlog_vs_delayed_cases_correlation(db, tenant_id),
        "human_review_required": True,
    }
