"""Project Veritas, Section 17: Supervisor Feedback.

Also the ONLY place an evidence-gate override is recorded (action
`override_evidence_gate`, requires `override_reason`) -- mirrors Vulcan's
`final_disposition`-via-feedback-only pattern. Veritas's own orchestrator
never sets `VeritasEvidenceReadinessAssessment.final_gate_override`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.veritas_evidence import FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE, VeritasEvidenceReadinessAssessment, VeritasFeedback


class OverrideReasonRequiredError(ValueError):
    pass


def submit_feedback(
    db: Session, tenant_id: str, *, action: str, submitted_by: str, submitted_role: str = "",
    assessment_id: int | None = None, baseline_match_correct: bool | None = None,
    image_quality_assessment_correct: bool | None = None, anatomy_zone_tag_correct: bool | None = None,
    coverage_determination_correct: bool | None = None, evidence_conflict_valid: bool | None = None,
    corrected_baseline: str = "", corrected_zone: str = "", final_evidence_status: str = "",
    reviewer_rationale: str = "", override_reason: str = "", limitations_acknowledged: str = "",
    final_disposition: str = "",
) -> VeritasFeedback:
    if action == FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE and not override_reason.strip():
        raise OverrideReasonRequiredError("override_reason is required to override an evidence gate")

    row = VeritasFeedback(
        tenant_id=tenant_id, assessment_id=assessment_id, action=action,
        baseline_match_correct=baseline_match_correct, image_quality_assessment_correct=image_quality_assessment_correct,
        anatomy_zone_tag_correct=anatomy_zone_tag_correct, coverage_determination_correct=coverage_determination_correct,
        evidence_conflict_valid=evidence_conflict_valid, corrected_baseline=corrected_baseline,
        corrected_zone=corrected_zone, final_evidence_status=final_evidence_status,
        reviewer_rationale=reviewer_rationale, override_reason=override_reason,
        limitations_acknowledged=limitations_acknowledged, final_disposition=final_disposition,
        submitted_by=submitted_by, submitted_role=submitted_role,
    )
    db.add(row)

    if action == FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE and assessment_id is not None:
        assessment = (
            db.query(VeritasEvidenceReadinessAssessment)
            .filter(VeritasEvidenceReadinessAssessment.id == assessment_id, VeritasEvidenceReadinessAssessment.tenant_id == tenant_id)
            .first()
        )
        if assessment is not None:
            assessment.final_gate_override = final_evidence_status or assessment.recommended_gate
            assessment.overridden_by = submitted_by
            assessment.overridden_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return row


def to_dict(row: VeritasFeedback) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "assessment_id": row.assessment_id,
        "action": row.action,
        "baseline_match_correct": row.baseline_match_correct,
        "image_quality_assessment_correct": row.image_quality_assessment_correct,
        "anatomy_zone_tag_correct": row.anatomy_zone_tag_correct,
        "coverage_determination_correct": row.coverage_determination_correct,
        "evidence_conflict_valid": row.evidence_conflict_valid,
        "corrected_baseline": row.corrected_baseline,
        "corrected_zone": row.corrected_zone,
        "final_evidence_status": row.final_evidence_status,
        "reviewer_rationale": row.reviewer_rationale,
        "override_reason": row.override_reason,
        "limitations_acknowledged": row.limitations_acknowledged,
        "final_disposition": row.final_disposition,
        "submitted_by": row.submitted_by,
        "submitted_role": row.submitted_role,
    }


def feedback_for_assessment(db: Session, tenant_id: str, assessment_id: int) -> list[dict]:
    rows = (
        db.query(VeritasFeedback)
        .filter(VeritasFeedback.tenant_id == tenant_id, VeritasFeedback.assessment_id == assessment_id)
        .order_by(VeritasFeedback.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
