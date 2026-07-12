"""Project Vulcan, Section 13: Supervisor and Repair Feedback.

`VulcanFeedback` is a new table (distinct from the pipeline's own
`SupervisorReview` -- see `app.models.vulcan_reliability` module docstring)
because Vulcan's checklist needs progression/repair-effectiveness/probable-
contributor correctness fields and repair-vendor/manufacturer response text
`SupervisorReview` was never built for.

This is the ONLY place `final_disposition` is ever set -- on both the new
`VulcanFeedback` row and, when provided, back onto the originating
`VulcanReliabilityAssessment.final_disposition`/`finalized_by`/`finalized_at`.
Vulcan's own orchestrator (`vulcan_reliability_agent_service`) never writes to
these fields -- this is the structural enforcement of "Vulcan cannot
independently finalize irreversible disposition."
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.vulcan_reliability import VulcanFeedback, VulcanReliabilityAssessment


def submit_feedback(
    db: Session, tenant_id: str, assessment_id: int, *, submitted_by: str, submitted_role: str = "",
    failure_classification_correct: bool | None = None, anatomy_zone_correct: bool | None = None,
    progression_correct: bool | None = None, repair_effectiveness_correct: bool | None = None,
    probable_contributor_correct: bool | None = None, final_disposition: str = "",
    supervisor_rationale: str = "", repair_vendor_response: str = "", manufacturer_response: str = "",
) -> VulcanFeedback:
    assessment = (
        db.query(VulcanReliabilityAssessment)
        .filter(VulcanReliabilityAssessment.id == assessment_id, VulcanReliabilityAssessment.tenant_id == tenant_id)
        .first()
    )
    if assessment is None:
        raise ValueError("Vulcan reliability assessment not found for this tenant")

    feedback = VulcanFeedback(
        assessment_id=assessment_id,
        tenant_id=tenant_id,
        failure_classification_correct=failure_classification_correct,
        anatomy_zone_correct=anatomy_zone_correct,
        progression_correct=progression_correct,
        repair_effectiveness_correct=repair_effectiveness_correct,
        probable_contributor_correct=probable_contributor_correct,
        final_disposition=final_disposition,
        supervisor_rationale=supervisor_rationale,
        repair_vendor_response=repair_vendor_response,
        manufacturer_response=manufacturer_response,
        submitted_by=submitted_by,
        submitted_role=submitted_role,
    )
    db.add(feedback)

    if final_disposition:
        assessment.final_disposition = final_disposition
        assessment.finalized_by = submitted_by
        assessment.finalized_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(feedback)
    return feedback


def _feedback_to_dict(row: VulcanFeedback) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "assessment_id": row.assessment_id,
        "tenant_id": row.tenant_id,
        "failure_classification_correct": row.failure_classification_correct,
        "anatomy_zone_correct": row.anatomy_zone_correct,
        "progression_correct": row.progression_correct,
        "repair_effectiveness_correct": row.repair_effectiveness_correct,
        "probable_contributor_correct": row.probable_contributor_correct,
        "final_disposition": row.final_disposition,
        "supervisor_rationale": row.supervisor_rationale,
        "repair_vendor_response": row.repair_vendor_response,
        "manufacturer_response": row.manufacturer_response,
        "submitted_by": row.submitted_by,
        "submitted_role": row.submitted_role,
    }


def feedback_for_assessment(db: Session, tenant_id: str, assessment_id: int) -> list[dict]:
    rows = (
        db.query(VulcanFeedback)
        .filter(VulcanFeedback.tenant_id == tenant_id, VulcanFeedback.assessment_id == assessment_id)
        .order_by(VulcanFeedback.created_at.asc())
        .all()
    )
    return [_feedback_to_dict(r) for r in rows]
