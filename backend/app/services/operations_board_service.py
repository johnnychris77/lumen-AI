"""v1.7 — Supervisor Operations Board (Deliverable 5).

A single rollup of the queue + workload data supervisors need to run the
shift — nothing here is a new analysis, just an operations-focused view of
work_queue_service and technician_workload_service.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.technician_workload_service import technician_workload
from app.services.work_queue_service import build_work_queue


def operations_board(db: Session, tenant_id: str) -> dict:
    queue = build_work_queue(db, tenant_id)
    workload = technician_workload(db, tenant_id)

    return {
        "technician_workload": workload["technicians"],
        "supervisor_queue": queue["supervisor_reviews"],
        "pending_approvals": queue["supervisor_reviews"],
        "high_risk_findings": queue["high_risk_inspections"],
        "repair_queue": queue["repair_holds"],
        "or_urgent_items": queue["or_priority_instruments"],
        "vendor_instruments": queue["vendor_trays"],
        "human_review_required": True,
    }
