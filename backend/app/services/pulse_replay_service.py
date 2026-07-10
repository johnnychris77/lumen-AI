"""v4.2 — Project Pulse, Section 11: Operational Replay.

Confirmed genuinely new: Sentinel's Clinical Scenario Engine (v2.5)
replays a single inspection's what-if scenarios, and Forge's Simulator
replays one workflow against one historical inspection — neither
replays a *time range* of activity across many inspections, alerts, and
decisions. This module composes the real event sources that already
exist (`AuditLog`, Nexus's `NexusEvent`, `SupervisorReview`, Forge's
`WorkflowExecution`) into one ordered timeline over a caller-supplied
window — it builds no new event-of-record table of its own.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.nexus_integration import NexusEvent
from app.models.pulse_operations import PulseAlert
from app.models.supervisor_review import SupervisorReview
from app.models.workflow_forge import WorkflowExecution


def _as_naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def replay_timerange(db: Session, tenant_id: str, start: datetime, end: datetime) -> dict:
    start_naive, end_naive = _as_naive(start), _as_naive(end)
    timeline: list[dict] = []

    for row in db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id).all():
        created = _as_naive(row.created_at)
        if start_naive <= created <= end_naive:
            timeline.append({"kind": "audit", "timestamp": row.created_at.isoformat(), "action_type": row.action_type, "actor": row.actor_email, "resource_type": row.resource_type})

    for row in db.query(NexusEvent).filter(NexusEvent.tenant_id == tenant_id).all():
        published = _as_naive(row.published_at)
        if start_naive <= published <= end_naive:
            timeline.append({"kind": "event", "timestamp": row.published_at.isoformat(), "event_type": row.event_type, "actor": row.actor})

    for row in db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all():
        created = _as_naive(row.created_at)
        if start_naive <= created <= end_naive:
            timeline.append({"kind": "supervisor_decision", "timestamp": row.created_at.isoformat(), "agreement": row.agreement, "reviewer": row.reviewer_name, "inspection_id": row.inspection_id})

    for row in db.query(WorkflowExecution).filter(WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.is_simulation.is_(False)).all():
        started = _as_naive(row.started_at)
        if start_naive <= started <= end_naive:
            timeline.append({"kind": "workflow_execution", "timestamp": row.started_at.isoformat(), "workflow_id": row.workflow_id, "status": row.status, "execution_id": row.id})

    for row in db.query(PulseAlert).filter(PulseAlert.tenant_id == tenant_id).all():
        created = _as_naive(row.created_at)
        if start_naive <= created <= end_naive:
            timeline.append({"kind": "alert", "timestamp": row.created_at.isoformat(), "alert_type": row.alert_type, "severity": row.severity})

    timeline.sort(key=lambda i: i["timestamp"])
    return {
        "tenant_id": tenant_id, "start": start.isoformat(), "end": end.isoformat(),
        "event_count": len(timeline), "timeline": timeline,
    }


def replay_shift(db: Session, tenant_id: str, shift_start: datetime, *, shift_hours: int = 8) -> dict:
    return replay_timerange(db, tenant_id, shift_start, shift_start + timedelta(hours=shift_hours))


def replay_day(db: Session, tenant_id: str, day_start: datetime) -> dict:
    return replay_timerange(db, tenant_id, day_start, day_start + timedelta(days=1))


def replay_incident(db: Session, tenant_id: str, alert_id: int, *, window_hours: int = 4) -> dict | None:
    alert = db.query(PulseAlert).filter(PulseAlert.id == alert_id, PulseAlert.tenant_id == tenant_id).first()
    if alert is None:
        return None
    window = timedelta(hours=window_hours)
    result = replay_timerange(db, tenant_id, alert.created_at - window, alert.created_at + window)
    result["incident_alert_id"] = alert_id
    result["incident_alert_type"] = alert.alert_type
    return result
