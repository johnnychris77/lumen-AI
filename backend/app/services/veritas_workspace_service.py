"""Project Veritas, Section 11: Veritas Workspace (`/veritas`)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.veritas_evidence import (
    BASELINE_STATUS_DRAFT,
    BASELINE_STATUS_PENDING_REVIEW,
    BASELINE_STATUS_SUPERSEDED,
    COVERAGE_INCOMPLETE,
    COVERAGE_INSUFFICIENT,
    FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE,
    IMAGE_QUALITY_INSUFFICIENT,
    MATCH_UNAVAILABLE,
    VeritasBaselineGovernanceAction,
    VeritasEvidenceConflict,
    VeritasEvidenceProvenanceRecord,
    VeritasEvidenceReadinessAssessment,
    VeritasFeedback,
)


def workspace_summary(
    db: Session, tenant_id: str, *, instrument_family: str = "", anatomy_zone: str = "", date_from=None, date_to=None,
) -> dict:
    q = db.query(VeritasEvidenceReadinessAssessment).filter(VeritasEvidenceReadinessAssessment.tenant_id == tenant_id)
    if date_from:
        q = q.filter(VeritasEvidenceReadinessAssessment.created_at >= date_from)
    if date_to:
        q = q.filter(VeritasEvidenceReadinessAssessment.created_at <= date_to)
    assessments = q.order_by(VeritasEvidenceReadinessAssessment.created_at.desc()).all()

    readiness_overview: dict[str, int] = {}
    for a in assessments:
        readiness_overview[a.readiness_category] = readiness_overview.get(a.readiness_category, 0) + 1

    missing_baseline_cases = [a for a in assessments if a.match_classification == MATCH_UNAVAILABLE]
    insufficient_image_quality_cases = [a for a in assessments if a.image_quality_status == IMAGE_QUALITY_INSUFFICIENT]
    incomplete_coverage_cases = [a for a in assessments if a.coverage_status in (COVERAGE_INCOMPLETE, COVERAGE_INSUFFICIENT)]

    governance_actions = db.query(VeritasBaselineGovernanceAction).filter(VeritasBaselineGovernanceAction.tenant_id == tenant_id).all()
    latest_by_baseline: dict[tuple, VeritasBaselineGovernanceAction] = {}
    for action in sorted(governance_actions, key=lambda a: a.created_at):
        latest_by_baseline[(action.baseline_source_type, action.baseline_source_id)] = action
    pending_baseline_reviews = [a for a in latest_by_baseline.values() if a.resulting_status in (BASELINE_STATUS_DRAFT, BASELINE_STATUS_PENDING_REVIEW, "")]
    superseded_baselines = [a for a in latest_by_baseline.values() if a.resulting_status == BASELINE_STATUS_SUPERSEDED]

    conflicts = (
        db.query(VeritasEvidenceConflict)
        .filter(VeritasEvidenceConflict.tenant_id == tenant_id, VeritasEvidenceConflict.resolved.is_(False))
        .all()
    )

    provenance_issues = (
        db.query(VeritasEvidenceProvenanceRecord)
        .filter(VeritasEvidenceProvenanceRecord.tenant_id == tenant_id, VeritasEvidenceProvenanceRecord.file_hash == "")
        .all()
    )

    overrides = (
        db.query(VeritasFeedback)
        .filter(VeritasFeedback.tenant_id == tenant_id, VeritasFeedback.action == FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE)
        .all()
    )

    recent_scores = [a.readiness_score for a in assessments[:20]]
    trend = "insufficient_data" if len(recent_scores) < 2 else (
        "improving" if recent_scores[0] > recent_scores[-1] else
        "declining" if recent_scores[0] < recent_scores[-1] else "stable"
    )

    return {
        "evidence_readiness_overview": readiness_overview,
        "pending_baseline_reviews": [
            {"baseline_source_type": a.baseline_source_type, "baseline_source_id": a.baseline_source_id, "status": a.resulting_status}
            for a in pending_baseline_reviews
        ],
        "missing_baseline_cases": [a.id for a in missing_baseline_cases],
        "insufficient_image_quality_cases": [a.id for a in insufficient_image_quality_cases],
        "incomplete_coverage_cases": [a.id for a in incomplete_coverage_cases],
        "evidence_conflicts": [
            {"id": c.id, "conflict_type": c.conflict_type, "severity": c.severity, "recommended_resolution": c.recommended_resolution}
            for c in conflicts
        ],
        "superseded_baselines": [
            {"baseline_source_type": a.baseline_source_type, "baseline_source_id": a.baseline_source_id} for a in superseded_baselines
        ],
        "unresolved_provenance_issues": [p.id for p in provenance_issues],
        "supervisor_overrides": [
            {"id": o.id, "assessment_id": o.assessment_id, "submitted_by": o.submitted_by, "override_reason": o.override_reason}
            for o in overrides
        ],
        "evidence_quality_trend": trend,
        "human_review_required": True,
    }
