"""v1.7 — Technician Assignment & Workload Tracking (Deliverable 3).

Complements the existing per-technician quality rollup in
competency_service.technician_quality_dashboard() (coverage / AI-confidence
/ supervisor-agreement — quality of work) with an operational capacity
view: who's currently assigned what, how much is open, and how long
inspections actually take from creation to a completed disposition (real
elapsed time between audited WorkflowStateEvent rows, never estimated).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.workflow import COMPLETED, InspectionAssignment, WorkflowStateEvent
from app.services.workflow_state_service import aware_utc


def _current_assignments(db: Session, tenant_id: str) -> dict[int, str]:
    """inspection_id -> technician, using each inspection's latest assignment row."""
    rows = (
        db.query(InspectionAssignment)
        .filter(InspectionAssignment.tenant_id == tenant_id)
        .order_by(InspectionAssignment.id.asc())
        .all()
    )
    latest: dict[int, str] = {}
    for r in rows:
        latest[r.inspection_id] = r.technician  # later rows overwrite earlier ones
    return latest


def technician_workload(db: Session, tenant_id: str) -> dict:
    """Deliverable 3 — per-technician assigned/open/completed counts and
    average real inspection turnaround (creation to first Completed event).
    A technician with no completed inspections yet gets `None`, not a
    fabricated average."""
    assignments = _current_assignments(db, tenant_id)
    if not assignments:
        return {"technicians": [], "human_review_required": True}

    insp_ids = list(assignments.keys())
    inspections = {
        i.id: i for i in db.query(models.Inspection).filter(models.Inspection.id.in_(insp_ids)).all()
    }
    completed_events = (
        db.query(WorkflowStateEvent)
        .filter(WorkflowStateEvent.inspection_id.in_(insp_ids), WorkflowStateEvent.to_state == COMPLETED)
        .order_by(WorkflowStateEvent.id.asc())
        .all()
    )
    first_completed_at: dict[int, object] = {}
    for e in completed_events:
        first_completed_at.setdefault(e.inspection_id, e.created_at)

    by_technician: dict[str, dict] = {}
    for insp_id, technician in assignments.items():
        insp = inspections.get(insp_id)
        if insp is None:
            continue
        bucket = by_technician.setdefault(technician, {"open": 0, "completed": 0, "durations_min": []})
        completed_at = first_completed_at.get(insp_id)
        if completed_at is not None:
            bucket["completed"] += 1
            if insp.created_at:
                bucket["durations_min"].append(
                    (aware_utc(completed_at) - aware_utc(insp.created_at)).total_seconds() / 60
                )
        else:
            bucket["open"] += 1

    technicians = []
    for technician, bucket in by_technician.items():
        durations = bucket["durations_min"]
        technicians.append({
            "technician": technician,
            "open_inspections": bucket["open"],
            "completed_inspections": bucket["completed"],
            "workload": bucket["open"],
            "avg_inspection_time_minutes": round(sum(durations) / len(durations), 1) if durations else None,
        })

    technicians.sort(key=lambda t: t["workload"], reverse=True)
    return {"technicians": technicians, "human_review_required": True}
