"""v2.4 — Recurrence Detection (Clinical Memory, Section 3).

Given one physical instrument's condition history (already assembled by
`instrument_condition_service.instrument_condition_history`), flags finding
types, repairs, and supervisor overrides that repeat across that instrument's
own inspections — real counts from real rows, never an inferred pattern.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.supervisor_review import SupervisorReview

CONTAMINATION_TYPES = {"blood", "bone", "tissue", "debris", "other_organic_residue"}
DAMAGE_TYPES = {"corrosion", "crack", "insulation_damage", "rust", "pitting"}

_RECURRENCE_THRESHOLD = 2


def detect_recurring_issues(db: Session, tenant_id: str, condition: dict) -> dict:
    """Recurring Issue Alerts for one instrument's history: repeated finding
    types, repeated repairs, repeated supervisor overrides."""
    history = condition["history"]

    finding_counts: dict[str, int] = {}
    for h in history:
        for finding_type in h["cleaning_findings"] + h["damage_findings"]:
            finding_counts[finding_type] = finding_counts.get(finding_type, 0) + 1

    alerts: list[dict] = []
    for finding_type, count in sorted(finding_counts.items(), key=lambda kv: -kv[1]):
        if count >= _RECURRENCE_THRESHOLD:
            alerts.append({
                "type": "recurring_finding",
                "finding_type": finding_type,
                "occurrences": count,
                "message": (
                    f"Repeated {finding_type.replace('_', ' ')} identified in "
                    f"{count} of {condition['inspection_count']} inspections."
                ),
            })

    if condition["repair_count"] >= _RECURRENCE_THRESHOLD:
        alerts.append({
            "type": "recurring_repair",
            "occurrences": condition["repair_count"],
            "message": (
                f"This instrument has been removed from service/repaired "
                f"{condition['repair_count']} times."
            ),
        })

    inspection_ids = [h["inspection_id"] for h in history]
    override_count = (
        db.query(SupervisorReview)
        .filter(
            SupervisorReview.tenant_id == tenant_id,
            SupervisorReview.inspection_id.in_(inspection_ids),
            SupervisorReview.override_action.isnot(None),
            SupervisorReview.override_action != "",
        )
        .count()
        if inspection_ids else 0
    )
    if override_count >= _RECURRENCE_THRESHOLD:
        alerts.append({
            "type": "recurring_override",
            "occurrences": override_count,
            "message": (
                f"A supervisor has overridden the AI recommendation "
                f"{override_count} times for this instrument."
            ),
        })

    return {
        "alerts": alerts,
        "has_recurring_issues": bool(alerts),
        "finding_counts": finding_counts,
        "override_count": override_count,
    }
