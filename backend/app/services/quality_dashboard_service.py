"""v1.5 — Quality Intelligence Dashboard: core KPIs, benchmarking, and the
executive quality score.

Every metric here is computed live from real Inspection/SupervisorReview rows
for the requesting tenant — nothing is mocked or simulated. A metric with no
underlying data returns None (not zero, not a fabricated placeholder) so the
dashboard can honestly show "not enough data yet."
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import models
from app.models.supervisor_review import SupervisorReview

_REPAIRABLE_ISSUES = {"crack", "corrosion", "insulation_damage"}


def _rate(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


def _period_start(period: str, now: datetime | None = None) -> datetime | None:
    """Start of the named period, or None for 'all_time'."""
    now = now or datetime.now(timezone.utc)
    if period == "day":
        return now - timedelta(days=1)
    if period == "week":
        return now - timedelta(weeks=1)
    if period == "month":
        return now - timedelta(days=30)
    if period == "quarter":
        return now - timedelta(days=90)
    if period == "year":
        return now - timedelta(days=365)
    return None  # "all_time"


def _inspections(db: Session, tenant_id: str, period: str = "all_time"):
    q = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id)
    start = _period_start(period)
    if start is not None:
        q = q.filter(models.Inspection.created_at >= start)
    return q.all()


def dashboard_summary(db: Session, tenant_id: str, period: str = "all_time") -> dict:
    """Deliverable 1 — Quality Intelligence Dashboard KPIs."""
    rows = _inspections(db, tenant_id, period)
    return {"period": period, **_summarize_rows(rows), "human_review_required": True}


# ── Benchmarking (Deliverable 9) ─────────────────────────────────────────────
def _classify_change(current: float | None, previous: float | None, *, higher_is_better: bool) -> str:
    if current is None or previous is None:
        return "insufficient_data"
    delta = current - previous
    if abs(delta) < 1.0:
        return "stable"
    improved = delta > 0 if higher_is_better else delta < 0
    return "improvement" if improved else "regression"


# Metrics where a higher percentage is a WORSE outcome.
_LOWER_IS_BETTER = {"reclean_rate_pct", "remove_from_service_rate_pct", "supervisor_override_rate_pct"}


def benchmark(db: Session, tenant_id: str) -> dict:
    """Deliverable 9 — current month vs previous month vs quarter vs rolling 12mo."""
    now = datetime.now(timezone.utc)
    current_month_start = now - timedelta(days=30)
    previous_month_start = now - timedelta(days=60)

    current = dashboard_summary(db, tenant_id, "month")

    prev_rows = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            models.Inspection.created_at >= previous_month_start,
            models.Inspection.created_at < current_month_start,
        )
        .all()
    )
    previous = _summarize_rows(prev_rows)
    quarter = dashboard_summary(db, tenant_id, "quarter")
    rolling_year = dashboard_summary(db, tenant_id, "year")

    comparisons = {}
    for metric in (
        "pass_rate_pct", "reclean_rate_pct", "repair_rate_pct",
        "remove_from_service_rate_pct", "supervisor_override_rate_pct",
        "baseline_compliance_pct", "coverage_compliance_pct", "ai_confidence_trend_pct",
    ):
        comparisons[metric] = _classify_change(
            current.get(metric), previous.get(metric),
            higher_is_better=metric not in _LOWER_IS_BETTER,
        )

    return {
        "current_month": current,
        "previous_month": previous,
        "quarter": quarter,
        "rolling_12_months": rolling_year,
        "comparison_current_vs_previous_month": comparisons,
    }


def _summarize_rows(rows: list) -> dict:
    """Same shape as dashboard_summary but from an already-fetched row list
    (used for the previous-month window, which isn't a simple "since" filter)."""
    scored = [r for r in rows if r.has_image and r.disposition]
    total = len(scored)
    pass_ct = sum(1 for r in scored if r.disposition == "PASS")
    reclean_ct = sum(1 for r in scored if r.disposition == "REPROCESS")
    remove_ct = sum(1 for r in scored if r.disposition == "REMOVE FROM SERVICE")
    repair_ct = sum(
        1 for r in scored
        if r.disposition == "REMOVE FROM SERVICE" and (r.detected_issue or "") in _REPAIRABLE_ISSUES
    )
    override_ct = sum(1 for r in rows if (r.override_by or "").strip())
    baseline_ct = sum(1 for r in rows if r.has_image)
    baseline_found_ct = sum(1 for r in rows if r.baseline_status == "approved_baseline_found")
    coverage_assessed = [r for r in rows if r.coverage_pct is not None]
    confidences = [r.ai_confidence for r in rows if r.has_image and r.ai_confidence is not None]

    return {
        "inspection_volume": len(rows),
        "pass_rate_pct": _rate(pass_ct, total),
        "reclean_rate_pct": _rate(reclean_ct, total),
        "repair_rate_pct": _rate(repair_ct, total),
        "remove_from_service_rate_pct": _rate(remove_ct, total),
        "supervisor_override_rate_pct": _rate(override_ct, len(rows)),
        "baseline_compliance_pct": _rate(baseline_found_ct, baseline_ct),
        "coverage_compliance_pct": (
            round(sum(r.coverage_pct for r in coverage_assessed) / len(coverage_assessed), 1)
            if coverage_assessed else None
        ),
        "ai_confidence_trend_pct": (
            round(100 * sum(confidences) / len(confidences), 1) if confidences else None
        ),
    }


# ── Executive Quality Score (Deliverable 10) ─────────────────────────────────
# Weighted factors, each normalized to 0-100 before weighting. Weights sum to 1.
_SCORE_WEIGHTS = {
    "pass_rate_pct": 0.25,
    "coverage_compliance_pct": 0.15,
    "supervisor_agreement_pct": 0.15,
    "low_high_risk_findings_pct": 0.15,  # inverted: 100 - remove_from_service rate
    "low_repeat_findings_pct": 0.10,      # inverted: 100 - repeat-error rate
    "competency_pct": 0.10,
    "baseline_compliance_pct": 0.10,
}


def executive_quality_score(db: Session, tenant_id: str) -> dict:
    """Deliverable 10 — a single 0-100 Quality Intelligence Score.

    Any factor with no underlying data is excluded from the weighted average
    (re-normalizing the remaining weights) rather than defaulted to a
    fabricated value — the score is honest about how much data backs it.
    """
    summary = dashboard_summary(db, tenant_id, "quarter")

    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    agreement_pct = _rate(sum(1 for r in reviews if r.agreement == "agree"), len(reviews))

    from app.models.competency_event import CompetencyEvent

    corrections = (
        db.query(func.count(CompetencyEvent.id))
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "supervisor_correction")
        .scalar() or 0
    )
    repeats = (
        db.query(func.count(CompetencyEvent.id))
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "repeated_error")
        .scalar() or 0
    )
    repeat_rate = _rate(repeats, corrections)
    education_completed = (
        db.query(func.count(CompetencyEvent.id))
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "education_completed")
        .scalar() or 0
    )
    reviewed = (
        db.query(func.count(CompetencyEvent.id))
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "finding_reviewed")
        .scalar() or 0
    )
    competency_pct = _rate(education_completed, reviewed) if reviewed else None

    factors = {
        "pass_rate_pct": summary["pass_rate_pct"],
        "coverage_compliance_pct": summary["coverage_compliance_pct"],
        "supervisor_agreement_pct": agreement_pct,
        "low_high_risk_findings_pct": (
            100 - summary["remove_from_service_rate_pct"]
            if summary["remove_from_service_rate_pct"] is not None else None
        ),
        "low_repeat_findings_pct": 100 - repeat_rate if repeat_rate is not None else None,
        "competency_pct": competency_pct,
        "baseline_compliance_pct": summary["baseline_compliance_pct"],
    }

    available = {k: v for k, v in factors.items() if v is not None}
    if not available:
        return {"score": None, "factors": factors, "note": "Not enough data yet to compute a quality score."}

    total_weight = sum(_SCORE_WEIGHTS[k] for k in available)
    score = sum(available[k] * _SCORE_WEIGHTS[k] for k in available) / total_weight

    return {
        "score": round(score),
        "factors": factors,
        "weights": _SCORE_WEIGHTS,
        "factors_used": list(available.keys()),
        "note": (
            "Computed from real inspection/review/competency data for this tenant "
            "over the trailing quarter. Missing factors are excluded, not defaulted."
        ),
    }
