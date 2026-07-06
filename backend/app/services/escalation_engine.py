"""v1.7 — Escalation Rules Engine (Deliverable 7).

Evaluates real, already-computed signals (readiness/risk, AI confidence,
baseline status, prior override history) against fixed thresholds and
returns which inspections should escalate, with the specific rule(s) that
fired — never a generic "flagged" verdict.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.disposition_override import DispositionOverride
from app.models.workflow import CANCELLED, COMPLETED

_LOW_CONFIDENCE_THRESHOLD = 0.60
_REPEATED_OVERRIDE_THRESHOLD = 2


def _repeated_supervisor_overrides(db: Session, tenant_id: str, insp) -> int:
    return (
        db.query(DispositionOverride)
        .filter(
            DispositionOverride.tenant_id == tenant_id,
            DispositionOverride.inspection_id == insp.id,
            DispositionOverride.action != "approve",
        )
        .count()
    )


def evaluate_escalation(db: Session, tenant_id: str, insp, *, readiness: dict, risk_tier: str) -> dict:
    """Deliverable 7 — which escalation rule(s), if any, fire for this
    inspection. `escalated` is only true when at least one real rule fires."""
    reasons: list[str] = []

    if risk_tier == "Critical":
        reasons.append("Critical contamination/risk finding.")

    if insp.has_image and insp.ai_confidence is not None and insp.ai_confidence < _LOW_CONFIDENCE_THRESHOLD:
        reasons.append(f"Low AI confidence ({round(insp.ai_confidence * 100)}%).")

    if insp.has_image and insp.baseline_status != "approved_baseline_found":
        reasons.append("No approved baseline available for this instrument.")

    override_count = _repeated_supervisor_overrides(db, tenant_id, insp)
    if override_count >= _REPEATED_OVERRIDE_THRESHOLD:
        reasons.append(f"Repeated supervisor overrides on record ({override_count}).")

    if (insp.procedure_priority or "").strip().lower() in ("emergency", "trauma"):
        reasons.append(f"High-priority OR instrument ({insp.procedure_priority}).")

    if readiness.get("repair_history") and readiness.get("is_critical_finding"):
        reasons.append("Repeated failure history on this instrument.")

    return {
        "inspection_id": insp.id,
        "instrument_type": insp.instrument_type,
        "escalated": len(reasons) > 0,
        "reasons": reasons,
        "human_review_required": True,
    }


def escalation_queue(db: Session, tenant_id: str) -> dict:
    """All currently-open inspections that meet at least one escalation rule."""
    from app.models.supervisor_review import SupervisorReview
    from app.services.readiness_engine import compute_readiness, get_primary_finding_type
    from app.services.risk_stratification_service import stratify_risk
    from app.services.workflow_state_service import current_state

    rows = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).all()
    escalations = []
    for insp in rows:
        state = current_state(db, insp)
        if state in (COMPLETED, CANCELLED):
            continue
        confirmed = (
            db.query(SupervisorReview.id).filter(SupervisorReview.inspection_id == insp.id).first() is not None
        )
        readiness = compute_readiness(db, tenant_id, insp, confirmed=confirmed)
        primary_finding_type = get_primary_finding_type(db, insp)
        risk = stratify_risk(insp, primary_finding_type=primary_finding_type)
        result = evaluate_escalation(db, tenant_id, insp, readiness=readiness, risk_tier=risk["risk_tier"])
        if result["escalated"]:
            escalations.append(result)

    return {"escalations": escalations, "total_escalated": len(escalations), "human_review_required": True}
