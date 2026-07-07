"""v1.7 — SLA Monitoring (Deliverable 6).

Turnaround times are computed only from real, audited WorkflowStateEvent
transitions (workflow_state_service.py) — never estimated. An inspection
that hasn't reached a given stage yet contributes no data point for it, and
a currently-open stage is flagged as a breach only once it has genuinely
exceeded the target, using the real elapsed time so far.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.workflow import COMPLETED, RECLEAN, REPAIR, SUPERVISOR_REVIEW, WorkflowStateEvent
from app.services.workflow_state_service import aware_utc

SLA_TARGET_MINUTES = {
    "supervisor_review_minutes": 480,   # 8h
    "reclean_turnaround_minutes": 240,  # 4h
    "repair_referral_minutes": 1440,    # 24h
    "overall_turnaround_minutes": 1440,  # 24h
}


def _stage_durations(db: Session, tenant_id: str, from_state: str) -> tuple[list[float], list[dict]]:
    """Elapsed minutes for every completed occurrence of `from_state` (the
    stage was entered then later left), plus any occurrence still open
    (for breach detection)."""
    events = (
        db.query(WorkflowStateEvent)
        .filter(WorkflowStateEvent.tenant_id == tenant_id)
        .order_by(WorkflowStateEvent.inspection_id.asc(), WorkflowStateEvent.id.asc())
        .all()
    )
    by_inspection: dict[int, list[WorkflowStateEvent]] = {}
    for e in events:
        by_inspection.setdefault(e.inspection_id, []).append(e)

    completed_minutes: list[float] = []
    open_stages: list[dict] = []
    now = datetime.now(timezone.utc)
    for inspection_id, evs in by_inspection.items():
        for i, e in enumerate(evs):
            if e.to_state != from_state:
                continue
            next_event = evs[i + 1] if i + 1 < len(evs) else None
            if next_event is not None:
                completed_minutes.append(
                    (aware_utc(next_event.created_at) - aware_utc(e.created_at)).total_seconds() / 60
                )
            else:
                open_stages.append({
                    "inspection_id": inspection_id,
                    "minutes_elapsed": round((now - aware_utc(e.created_at)).total_seconds() / 60, 1),
                })
    return completed_minutes, open_stages


def sla_monitoring(db: Session, tenant_id: str) -> dict:
    """Deliverable 6 — average turnaround per stage plus any current SLA
    breaches (a stage still open longer than its target)."""
    supervisor_minutes, supervisor_open = _stage_durations(db, tenant_id, SUPERVISOR_REVIEW)
    reclean_minutes, reclean_open = _stage_durations(db, tenant_id, RECLEAN)
    repair_minutes, repair_open = _stage_durations(db, tenant_id, REPAIR)

    completed_events = (
        db.query(WorkflowStateEvent)
        .filter(WorkflowStateEvent.tenant_id == tenant_id, WorkflowStateEvent.to_state == COMPLETED)
        .all()
    )
    insp_ids = [e.inspection_id for e in completed_events]
    inspections = (
        {i.id: i for i in db.query(models.Inspection).filter(models.Inspection.id.in_(insp_ids)).all()}
        if insp_ids else {}
    )
    overall_minutes = []
    for e in completed_events:
        insp = inspections.get(e.inspection_id)
        if insp is not None and insp.created_at:
            overall_minutes.append((aware_utc(e.created_at) - aware_utc(insp.created_at)).total_seconds() / 60)

    def _avg(values):
        return round(sum(values) / len(values), 1) if values else None

    breaches = []
    for label, target_key, open_stages in (
        ("Supervisor Review", "supervisor_review_minutes", supervisor_open),
        ("Reclean", "reclean_turnaround_minutes", reclean_open),
        ("Repair", "repair_referral_minutes", repair_open),
    ):
        target = SLA_TARGET_MINUTES[target_key]
        for stage in open_stages:
            if stage["minutes_elapsed"] > target:
                breaches.append({
                    "stage": label, "inspection_id": stage["inspection_id"],
                    "minutes_elapsed": stage["minutes_elapsed"], "target_minutes": target,
                })

    return {
        "sla_targets_minutes": SLA_TARGET_MINUTES,
        "average_supervisor_review_minutes": _avg(supervisor_minutes),
        "average_reclean_turnaround_minutes": _avg(reclean_minutes),
        "average_repair_referral_minutes": _avg(repair_minutes),
        "average_overall_turnaround_minutes": _avg(overall_minutes),
        "sla_breaches": breaches,
        "human_review_required": True,
    }
