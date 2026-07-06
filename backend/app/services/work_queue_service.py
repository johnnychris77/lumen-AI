"""v1.7 — Smart Inspection Queue (Deliverable 1).

Groups every not-yet-finished inspection into the queue sections SPD asks
for, ranked by the prioritization engine's score — a rollup of the already
real-computed readiness/disposition/risk/priority signals per inspection,
never a separate analysis.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.supervisor_review import SupervisorReview
from app.models.workflow import CANCELLED, COMPLETED, REPAIR, SUPERVISOR_REVIEW
from app.services.disposition_engine import recommend_disposition
from app.services.prioritization_engine import compute_priority, has_repeat_findings, is_vendor_tray
from app.services.readiness_engine import compute_readiness, get_primary_finding_type
from app.services.risk_stratification_service import stratify_risk
from app.services.workflow_state_service import aware_utc, current_state, latest_assignment


def _queue_item(db: Session, tenant_id: str, insp) -> dict:
    confirmed = (
        db.query(SupervisorReview.id).filter(SupervisorReview.inspection_id == insp.id).first() is not None
    )
    readiness = compute_readiness(db, tenant_id, insp, confirmed=confirmed)
    primary_finding_type = get_primary_finding_type(db, insp)
    disposition = recommend_disposition(
        readiness, insp, coverage_pct=insp.coverage_pct, primary_finding_type=primary_finding_type,
    )
    risk = stratify_risk(insp, primary_finding_type=primary_finding_type)
    priority = compute_priority(
        db, tenant_id, insp, readiness=readiness, disposition=disposition,
        repair_history=readiness.get("repair_history", False),
    )
    state = current_state(db, insp)
    assignment = latest_assignment(db, insp.id)
    minutes_waiting = (
        int((datetime.now(timezone.utc) - aware_utc(insp.created_at)).total_seconds() / 60)
        if insp.created_at else None
    )

    return {
        "inspection_id": insp.id,
        "instrument_type": insp.instrument_type,
        "facility_name": insp.facility_name or insp.site_name,
        "procedure_priority": insp.procedure_priority,
        "workflow_state": state,
        "risk_tier": risk["risk_tier"],
        "priority_score": priority["priority_score"],
        "priority_tier": priority["priority_tier"],
        "priority_reasons": priority["reasons"],
        "disposition": disposition["disposition"],
        "coverage_pct": insp.coverage_pct,
        "minutes_waiting": minutes_waiting,
        "assigned_technician": assignment.technician if assignment else None,
        "is_vendor_tray": is_vendor_tray(insp),
        "is_loaner_instrument": bool(insp.is_loaner_instrument),
        "has_repeat_findings": has_repeat_findings(db, tenant_id, insp),
        "supervisor_review_confirmed": confirmed,
    }


def build_work_queue(db: Session, tenant_id: str) -> dict:
    """Deliverable 1 — the Smart Inspection Queue, grouped into the sections
    SPD asks for and ranked by priority score."""
    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id)
        .order_by(models.Inspection.created_at.asc())
        .all()
    )

    items = []
    for insp in rows:
        item = _queue_item(db, tenant_id, insp)
        if item["workflow_state"] in (COMPLETED, CANCELLED):
            continue
        items.append(item)

    items.sort(key=lambda i: i["priority_score"], reverse=True)

    def _bucket(pred):
        return [i for i in items if pred(i)]

    return {
        "pending_inspections": items,
        "high_risk_inspections": _bucket(lambda i: i["risk_tier"] in ("High Risk", "Critical")),
        "or_priority_instruments": _bucket(lambda i: i["procedure_priority"] in ("emergency", "trauma", "first_case")),
        "vendor_trays": _bucket(lambda i: i["is_vendor_tray"]),
        "loaner_instruments": _bucket(lambda i: i["is_loaner_instrument"]),
        "repeat_inspections": _bucket(lambda i: i["has_repeat_findings"]),
        "supervisor_reviews": _bucket(lambda i: i["workflow_state"] == SUPERVISOR_REVIEW),
        "repair_holds": _bucket(lambda i: i["workflow_state"] == REPAIR),
        "total_pending": len(items),
        "human_review_required": True,
    }
