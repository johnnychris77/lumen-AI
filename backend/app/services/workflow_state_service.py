"""v1.7 — Inspection Workflow State Machine (Deliverable 4).

Current state is always the `to_state` of the latest audited
WorkflowStateEvent row for an inspection — never a mutated single-column
"current state" that would erase transition history. Transitions are
appended at the real moment they happen (technician assignment, the
synchronous image-capture+AI-analysis that already occurs inside one
POST /api/inspections call, a supervisor's disposition action, or an
explicit cancellation) rather than re-derived after the fact from
unrelated signals — this mirrors the same honesty principle already
applied in readiness_timeline_service.py.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.workflow import (
    AI_ANALYSIS,
    ASSIGNED,
    CANCELLED,
    COMPLETED,
    IMAGE_CAPTURE,
    RECLEAN,
    REPAIR,
    SUPERVISOR_REVIEW,
    WAITING,
    InspectionAssignment,
    WorkflowStateEvent,
)

TERMINAL_STATES = {COMPLETED, CANCELLED}


def aware_utc(dt: datetime) -> datetime:
    """SQLite round-trips DateTime columns as naive; Postgres keeps them
    timezone-aware. Normalize to aware-UTC before any subtraction so
    turnaround-time math never raises on either backend."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

# Disposition action -> the workflow state that action drives the inspection to.
_ACTION_TO_STATE = {
    "approve": COMPLETED,
    "reclean": RECLEAN,
    "repair": REPAIR,
    "manufacturer_review": REPAIR,
    "remove_from_service": COMPLETED,
    "escalate": SUPERVISOR_REVIEW,
    "modify": SUPERVISOR_REVIEW,
}


def latest_assignment(db: Session, inspection_id: int) -> InspectionAssignment | None:
    return (
        db.query(InspectionAssignment)
        .filter(InspectionAssignment.inspection_id == inspection_id)
        .order_by(InspectionAssignment.id.desc())
        .first()
    )


def latest_event(db: Session, inspection_id: int) -> WorkflowStateEvent | None:
    return (
        db.query(WorkflowStateEvent)
        .filter(WorkflowStateEvent.inspection_id == inspection_id)
        .order_by(WorkflowStateEvent.id.desc())
        .first()
    )


def current_state(db: Session, insp) -> str:
    """The inspection's current workflow state. Falls back to an honest
    default (Assigned/Waiting) only when no transition has ever been
    recorded for it — real state once any event exists."""
    event = latest_event(db, insp.id)
    if event is not None:
        return event.to_state
    if latest_assignment(db, insp.id) is not None:
        return ASSIGNED
    return WAITING


def _append(db: Session, *, insp, tenant_id: str, to_state: str, actor: str, reason: str = "") -> WorkflowStateEvent:
    from_state = current_state(db, insp)
    row = WorkflowStateEvent(
        inspection_id=insp.id, tenant_id=tenant_id,
        from_state=from_state, to_state=to_state, actor=actor, reason=reason,
    )
    db.add(row)
    return row


def assign_technician(db: Session, *, insp, tenant_id: str, technician: str, assigned_by: str, note: str = "") -> InspectionAssignment:
    """Deliverable 3 — supervisor assigns (or reassigns) a technician.
    Only advances the workflow state to Assigned when the inspection is still
    Waiting — reassigning an in-progress or completed inspection just records
    who is now responsible, it never regresses a finished workflow."""
    row = InspectionAssignment(
        inspection_id=insp.id, tenant_id=tenant_id, technician=technician,
        assigned_by=assigned_by, note=note,
    )
    db.add(row)
    if current_state(db, insp) == WAITING:
        _append(db, insp=insp, tenant_id=tenant_id, to_state=ASSIGNED, actor=assigned_by, reason="Technician assigned")
    return row


def record_capture_and_analysis(db: Session, *, insp, tenant_id: str, actor: str) -> None:
    """Called once, at inspection-creation time, when an image was submitted.
    Image capture and AI analysis happen synchronously in the same request —
    both events share that real timestamp rather than fabricating a gap
    between them, consistent with readiness_timeline_service's documented
    approach to the same synchronous-submission architecture."""
    if current_state(db, insp) in TERMINAL_STATES:
        return
    _append(db, insp=insp, tenant_id=tenant_id, to_state=IMAGE_CAPTURE, actor=actor, reason="Image submitted")
    _append(db, insp=insp, tenant_id=tenant_id, to_state=AI_ANALYSIS, actor=actor, reason="AI analysis completed")


def record_disposition_action(db: Session, *, insp, tenant_id: str, action: str, actor: str, reason: str = "") -> None:
    """Called when a supervisor submits a disposition action (v1.6
    /disposition-action endpoint) — advances the workflow state to match."""
    to_state = _ACTION_TO_STATE.get(action)
    if to_state is None:
        return
    _append(db, insp=insp, tenant_id=tenant_id, to_state=to_state, actor=actor, reason=reason or f"Disposition action: {action}")


def enter_supervisor_review(db: Session, *, insp, tenant_id: str, actor: str, reason: str = "") -> None:
    """Advance to Supervisor Review once AI analysis has finished and the
    disposition engine says a human must weigh in — a no-op if the
    inspection is already past that point (terminal or already looping
    through Reclean/Repair)."""
    state = current_state(db, insp)
    if state in TERMINAL_STATES or state == SUPERVISOR_REVIEW:
        return
    _append(db, insp=insp, tenant_id=tenant_id, to_state=SUPERVISOR_REVIEW, actor=actor, reason=reason or "Awaiting supervisor review")


def cancel_inspection(db: Session, *, insp, tenant_id: str, actor: str, reason: str) -> WorkflowStateEvent:
    """Deliverable 4 — explicit, terminal cancellation. Never inferred."""
    return _append(db, insp=insp, tenant_id=tenant_id, to_state=CANCELLED, actor=actor, reason=reason)


def state_history(db: Session, inspection_id: int) -> list[WorkflowStateEvent]:
    return (
        db.query(WorkflowStateEvent)
        .filter(WorkflowStateEvent.inspection_id == inspection_id)
        .order_by(WorkflowStateEvent.id.asc())
        .all()
    )
