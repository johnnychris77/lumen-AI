"""v1.7 — Shift Handoff Report (Deliverable 9)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services.escalation_engine import escalation_queue
from app.services.work_queue_service import build_work_queue


def shift_handoff_report(db: Session, tenant_id: str, *, shift_actor: str = "") -> dict:
    """Deliverable 9 — a real-time snapshot of what the next shift needs to
    know, built entirely from the same queue/escalation data already shown
    on the work queue and operations board."""
    queue = build_work_queue(db, tenant_id)
    escalations = escalation_queue(db, tenant_id)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": shift_actor,
        "outstanding_inspections": queue["pending_inspections"],
        "critical_instruments": queue["high_risk_inspections"],
        "pending_supervisor_reviews": queue["supervisor_reviews"],
        "repair_holds": queue["repair_holds"],
        "escalations": escalations["escalations"],
        "or_priorities": queue["or_priority_instruments"],
        "human_review_required": True,
    }
