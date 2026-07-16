"""Advisor — Phase 7 §10: Success Metrics.

Reuses existing month-over-month comparison machinery
(``quality_dashboard_service.benchmark()``) for repeat-inspection
(reclean) rate and override-rate trends rather than building a second
baseline-comparison mechanism. Reuses ``pulse_ai_ops_service.
ai_operations_monitor()``'s real ``model_availability_pct`` for system
availability rather than fabricating an uptime number. Adds a
missed-findings (false-negative rate) month-over-month comparison, since
no existing service tracks that trend specifically, using the same
current-month-vs-previous-month split ``benchmark()`` already
establishes as this codebase's pattern.

Every metric is honestly ``None``/``"insufficient_data"`` when the
underlying period has no data — never a fabricated improvement.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.supervisor_review import SupervisorReview
from app.services import advisory_user_feedback_service, pulse_ai_ops_service, quality_dashboard_service
from app.services.ml import pilot_validation


def _classify(current: float | None, previous: float | None) -> str:
    return quality_dashboard_service._classify_change(current, previous, higher_is_better=False)


def missed_findings_trend(db: Session, tenant_id: str) -> dict[str, Any]:
    """Month-over-month false-negative-rate comparison, mirroring
    ``quality_dashboard_service.benchmark()``'s current-vs-previous-month
    split."""
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=30)
    previous_start = now - timedelta(days=60)

    current_rows = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= current_start)
        .all()
    )
    previous_rows = (
        db.query(SupervisorReview)
        .filter(
            SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= previous_start,
            SupervisorReview.created_at < current_start,
        )
        .all()
    )
    current_fnr = pilot_validation.clinical_metrics(current_rows)["false_negative_rate"]
    previous_fnr = pilot_validation.clinical_metrics(previous_rows)["false_negative_rate"]
    return {
        "current_month_false_negative_rate": current_fnr,
        "previous_month_false_negative_rate": previous_fnr,
        "trend": _classify(current_fnr, previous_fnr),
    }


def success_metrics(db: Session, tenant_id: str) -> dict[str, Any]:
    """§10 — the full success metrics payload."""
    benchmark = quality_dashboard_service.benchmark(db, tenant_id)
    ai_ops = pulse_ai_ops_service.ai_operations_monitor(db, tenant_id)
    feedback = advisory_user_feedback_service.feedback_summary(db, tenant_id)

    return {
        "reduction_in_missed_findings": missed_findings_trend(db, tenant_id),
        "reduction_in_repeat_inspections": {
            "current_month_reclean_rate_pct": benchmark["current_month"]["reclean_rate_pct"],
            "previous_month_reclean_rate_pct": benchmark["previous_month"]["reclean_rate_pct"],
            "trend": benchmark["comparison_current_vs_previous_month"]["reclean_rate_pct"],
        },
        "inspection_consistency": {
            "current_month_pass_rate_pct": benchmark["current_month"]["pass_rate_pct"],
            "trend": benchmark["comparison_current_vs_previous_month"]["pass_rate_pct"],
        },
        "supervisor_workload": {
            "current_month_override_rate_pct": benchmark["current_month"]["supervisor_override_rate_pct"],
            "trend": benchmark["comparison_current_vs_previous_month"]["supervisor_override_rate_pct"],
        },
        "user_satisfaction": feedback["overall"],
        "operational_reliability": {
            "model_drift_detected": ai_ops["model_drift_detected"],
        },
        "system_availability": {
            "model_availability_pct": ai_ops["model_availability_pct"],
        },
        "human_review_required": True,
        "note": (
            "Trends are month-over-month comparisons of real, already-recorded data; "
            "'insufficient_data' means one or both periods have no qualifying rows — "
            "never a fabricated improvement or regression."
        ),
    }
