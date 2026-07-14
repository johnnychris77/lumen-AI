"""Advisor — Phase 7 §8: Safety Monitoring.

A persisted, reviewable log distinct from ``PilotErrorLog`` (operational
failures — upload/AI-analysis/report-generation errors, no clinical-
safety review workflow) and from Shadow's ``shadow_safety_monitor.py``
(computed views over shadow predictions, pre-visibility). Every event
here requires an explicit human review — never auto-closed, never
defaulted reviewed.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.advisory_pilot import AdvisorySafetyEvent

EVENT_TYPES = (
    "unsafe_recommendation", "near_miss", "repeated_override", "unexpected_behavior",
    "model_failure", "workflow_failure", "critical_incident",
)


def report_event(
    db: Session, *, tenant_id: str, model_id: str = "", event_type: str, inspection_id: int | None = None,
    description: str = "", severity: str = "medium", reported_by: str,
) -> AdvisorySafetyEvent:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event_type '{event_type}'. Must be one of {EVENT_TYPES}.")
    row = AdvisorySafetyEvent(
        tenant_id=tenant_id, model_id=model_id, event_type=event_type, inspection_id=inspection_id,
        description=description, severity=severity, reported_by=reported_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def review_event(db: Session, event: AdvisorySafetyEvent, *, reviewed_by: str, resolution_notes: str = "") -> AdvisorySafetyEvent:
    event.reviewed = True
    event.reviewed_by = reviewed_by
    event.reviewed_at = datetime.now(timezone.utc)
    event.resolution_notes = resolution_notes
    db.commit()
    db.refresh(event)
    return event


def safety_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    events = db.query(AdvisorySafetyEvent).filter(AdvisorySafetyEvent.tenant_id == tenant_id).all()
    unreviewed = [e for e in events if not e.reviewed]
    critical_unreviewed = [e for e in unreviewed if e.severity == "critical"]
    return {
        "total_events": len(events),
        "by_event_type": dict(Counter(e.event_type for e in events)),
        "by_severity": dict(Counter(e.severity for e in events)),
        "unreviewed_count": len(unreviewed),
        "critical_unreviewed_count": len(critical_unreviewed),
        "human_review_required": True,
    }


def safety_objectives_achieved(db: Session, tenant_id: str) -> bool:
    """§13 promotion-gate evidence — no unresolved safety concerns at all.
    A single unreviewed event (of any severity) blocks this; every safety
    concern must be reviewed before the pilot can be considered to have
    met its safety objectives."""
    summary = safety_summary(db, tenant_id)
    return summary["unreviewed_count"] == 0
