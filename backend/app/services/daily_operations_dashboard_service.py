"""v1.7 — Daily Operations Dashboard (Deliverable 8)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.workflow import COMPLETED, WorkflowStateEvent
from app.services.sla_monitoring_service import sla_monitoring
from app.services.work_queue_service import build_work_queue


def daily_operations_dashboard(db: Session, tenant_id: str) -> dict:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    completed_today = (
        db.query(WorkflowStateEvent)
        .filter(
            WorkflowStateEvent.tenant_id == tenant_id, WorkflowStateEvent.to_state == COMPLETED,
            WorkflowStateEvent.created_at >= day_start,
        )
        .count()
    )
    created_today = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.created_at >= day_start)
        .count()
    )

    queue = build_work_queue(db, tenant_id)
    sla = sla_monitoring(db, tenant_id)

    return {
        "date": day_start.date().isoformat(),
        "inspections_created_today": created_today,
        "inspections_completed_today": completed_today,
        "pending_inspections": queue["total_pending"],
        "high_risk_findings": len(queue["high_risk_inspections"]),
        "average_inspection_time_minutes": sla["average_overall_turnaround_minutes"],
        "supervisor_backlog": len(queue["supervisor_reviews"]),
        "repair_backlog": len(queue["repair_holds"]),
        "ready_for_packaging": sum(
            1 for i in queue["pending_inspections"] if i["disposition"] == "Proceed to Packaging"
        ),
        "human_review_required": True,
    }
