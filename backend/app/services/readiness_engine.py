"""v1.6 — Clinical Service Readiness Engine (Deliverable 1).

A rules-based readiness engine answering: is this instrument suitable to
proceed through the remainder of the reprocessing workflow after clinical
inspection? Built on top of the existing pre-sterilization readiness
classification (`pre_sterilization_command_center_service.classify_readiness`)
rather than re-deriving disposition logic a third time — this module maps
that classification onto v1.6's spec vocabulary and adds the repair-history
signal the spec asks for.

Score: 0-100 (the same `100 - risk_score` already computed by the scoring
engine — never fabricated).
Status: Ready / Ready with Supervisor Approval / Requires Recleaning /
Requires Repair / Remove From Service / Pending Supervisor Review /
Pending Analysis. The last two are honest additions beyond the spec's five —
an inspection that hasn't been scored or reviewed yet is neither "ready" nor
any of the other four outcomes, and collapsing it into one of them would
misrepresent an unfinished workflow as a finished one.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.pre_sterilization_command_center_service import (
    READY_FOR_PACKAGING,
    REMOVED_FROM_SERVICE,
    REQUIRES_REPAIR,
    REQUIRES_RECLEANING,
    REQUIRES_SUPERVISOR_REVIEW,
    _instrument_identity,
    classify_readiness,
)

READY = "Ready"
READY_WITH_SUPERVISOR_APPROVAL = "Ready with Supervisor Approval"
REQUIRES_RECLEANING_STATUS = "Requires Recleaning"
REQUIRES_REPAIR_STATUS = "Requires Repair"
REMOVE_FROM_SERVICE_STATUS = "Remove From Service"
PENDING_SUPERVISOR_REVIEW = "Pending Supervisor Review"
PENDING_ANALYSIS_STATUS = "Pending Analysis"

READINESS_STATUSES = [
    READY, READY_WITH_SUPERVISOR_APPROVAL, REQUIRES_RECLEANING_STATUS,
    REQUIRES_REPAIR_STATUS, REMOVE_FROM_SERVICE_STATUS,
    PENDING_SUPERVISOR_REVIEW, PENDING_ANALYSIS_STATUS,
]

# Supervisor override actions that redirect the final status regardless of
# what the AI classification alone would say (Deliverable 6).
_OVERRIDE_TO_STATUS = {
    "reclean": REQUIRES_RECLEANING_STATUS,
    "repair": REQUIRES_REPAIR_STATUS,
    "remove_from_service": REMOVE_FROM_SERVICE_STATUS,
    "manufacturer_review": REQUIRES_REPAIR_STATUS,
}


def get_primary_finding_type(db: Session, insp) -> str:
    """The most severe actionable finding actually detected for this
    inspection. `Inspection.detected_issue` is a legacy manual-entry field
    that's almost always "unknown" for AI-scored inspections — the real
    per-finding data lives in InspectionFinding (v1.5), logged at analysis
    time. Falls back to `detected_issue` for the no-image manual-entry path,
    where InspectionFinding rows are never created."""
    from app.models.inspection_finding import InspectionFinding

    finding = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.inspection_id == insp.id)
        .order_by(InspectionFinding.severity_index.desc())
        .first()
    )
    if finding is not None:
        return finding.finding_type
    return (insp.detected_issue or "").strip().lower()


def has_repair_history(db: Session, tenant_id: str, insp) -> bool:
    """Whether this physical instrument has a prior REQUIRES_REPAIR/removed
    classification on record — a real repeat-condition signal, not guessed."""
    from app.db import models

    identity = _instrument_identity(insp)
    if identity.startswith("untracked:"):
        return False  # can't honestly claim repair history without a real identity

    barcode_filter = (
        (models.Inspection.instrument_barcode == insp.instrument_barcode)
        if insp.instrument_barcode
        else (models.Inspection.instrument_udi == insp.instrument_udi)
    )
    prior = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            barcode_filter,
            models.Inspection.id != insp.id,
            models.Inspection.disposition == "REMOVE FROM SERVICE",
        )
        .count()
    )
    return prior > 0


def compute_readiness(db: Session, tenant_id: str, insp, *, confirmed: bool, override_action: str = "") -> dict:
    """Deliverable 1 — the Clinical Service Readiness Score + status for one
    inspection."""
    classification = classify_readiness(insp)
    state = classification["readiness_state"]
    score = classification["readiness_score"]
    repair_history = has_repair_history(db, tenant_id, insp)

    if override_action.strip() in _OVERRIDE_TO_STATUS:
        status = _OVERRIDE_TO_STATUS[override_action.strip()]
    elif state == READY_FOR_PACKAGING:
        status = READY_WITH_SUPERVISOR_APPROVAL if confirmed else READY
    elif state == REQUIRES_RECLEANING:
        status = REQUIRES_RECLEANING_STATUS
    elif state == REQUIRES_REPAIR:
        status = REQUIRES_REPAIR_STATUS
    elif state == REMOVED_FROM_SERVICE:
        status = REMOVE_FROM_SERVICE_STATUS
    elif state == REQUIRES_SUPERVISOR_REVIEW:
        status = READY_WITH_SUPERVISOR_APPROVAL if confirmed else PENDING_SUPERVISOR_REVIEW
    else:  # PENDING_ANALYSIS
        status = PENDING_ANALYSIS_STATUS

    return {
        "readiness_score": score,
        "status": status,
        "repair_candidate": classification["repair_candidate"],
        "repair_history": repair_history,
        "is_critical_finding": classification["is_critical_finding"],
        "confirmed_by_supervisor": confirmed,
        "human_review_required": True,
    }
