"""Project Veritas, Section 14: Data Quality Monitoring.

Every rate below is computed from real, already-persisted Veritas rows --
no fabricated trend lines. A rate is `None` (not 0%) when there is no
denominator activity yet.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.veritas_evidence import (
    BASELINE_STATUS_SUPERSEDED,
    CONFLICT_DUPLICATE_IMAGE_DIFFERENT_ZONES,
    CONFLICT_IMAGE_TAG_DIFFERS,
    COVERAGE_INCOMPLETE,
    COVERAGE_INSUFFICIENT,
    DATASET_APPROVED_FOR_TRAINING,
    FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE,
    IMAGE_QUALITY_INSUFFICIENT,
    MATCH_MISMATCH,
    VeritasBaselineGovernanceAction,
    VeritasEvidenceConflict,
    VeritasEvidenceProvenanceRecord,
    VeritasEvidenceReadinessAssessment,
    VeritasFeedback,
    VeritasTrainingDatasetEntry,
)


def _rate(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 1) if denominator else None


def data_quality_summary(db: Session, tenant_id: str) -> dict:
    assessments = db.query(VeritasEvidenceReadinessAssessment).filter(VeritasEvidenceReadinessAssessment.tenant_id == tenant_id).all()
    total = len(assessments)

    conflicts = db.query(VeritasEvidenceConflict).filter(VeritasEvidenceConflict.tenant_id == tenant_id).all()
    duplicate_conflicts = sum(1 for c in conflicts if c.conflict_type == CONFLICT_DUPLICATE_IMAGE_DIFFERENT_ZONES)
    tag_conflicts = sum(1 for c in conflicts if c.conflict_type == CONFLICT_IMAGE_TAG_DIFFERS)

    overrides = (
        db.query(VeritasFeedback)
        .filter(VeritasFeedback.tenant_id == tenant_id, VeritasFeedback.action == FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE)
        .count()
    )

    governance_actions = db.query(VeritasBaselineGovernanceAction).filter(VeritasBaselineGovernanceAction.tenant_id == tenant_id).all()
    baseline_keys = {(a.baseline_source_type, a.baseline_source_id) for a in governance_actions}
    latest_by_baseline = {}
    for action in sorted(governance_actions, key=lambda a: a.created_at):
        latest_by_baseline[(action.baseline_source_type, action.baseline_source_id)] = action
    superseded = sum(1 for a in latest_by_baseline.values() if a.resulting_status == BASELINE_STATUS_SUPERSEDED)

    provenance = db.query(VeritasEvidenceProvenanceRecord).filter(VeritasEvidenceProvenanceRecord.tenant_id == tenant_id).all()
    provenance_complete = sum(1 for p in provenance if p.file_hash and p.storage_location)

    dataset_entries = db.query(VeritasTrainingDatasetEntry).filter(VeritasTrainingDatasetEntry.tenant_id == tenant_id).all()
    approved_for_training = sum(1 for e in dataset_entries if e.dataset_status == DATASET_APPROVED_FOR_TRAINING)

    return {
        "duplicate_image_rate_pct": _rate(duplicate_conflicts, total),
        "incorrect_anatomy_tag_rate_pct": _rate(tag_conflicts, total),
        "baseline_mismatch_rate_pct": _rate(sum(1 for a in assessments if a.match_classification == MATCH_MISMATCH), total),
        "incomplete_coverage_rate_pct": _rate(sum(1 for a in assessments if a.coverage_status in (COVERAGE_INCOMPLETE, COVERAGE_INSUFFICIENT)), total),
        "insufficient_image_quality_rate_pct": _rate(sum(1 for a in assessments if a.image_quality_status == IMAGE_QUALITY_INSUFFICIENT), total),
        "supervisor_override_rate_pct": _rate(overrides, total),
        "stale_baseline_rate_pct": _rate(superseded, len(baseline_keys)),
        "provenance_completeness_pct": _rate(provenance_complete, len(provenance)),
        "dataset_readiness_pct": _rate(approved_for_training, len(dataset_entries)),
        "total_assessments": total,
    }
