"""Project Veritas, Section 18: Alerts and Watchlists.

Every watchlist is a live query over already-persisted Veritas rows -- zero
new tables. Each entry identifies an owner (responsible role) and a
recommended next action, per the brief's explicit requirement.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.veritas_evidence import (
    BASELINE_STATUS_DRAFT,
    BASELINE_STATUS_PENDING_REVIEW,
    BASELINE_STATUS_SUPERSEDED,
    COVERAGE_INCOMPLETE,
    COVERAGE_INSUFFICIENT,
    DATASET_APPROVED_FOR_TRAINING,
    FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE,
    IMAGE_QUALITY_INSUFFICIENT,
    MATCH_MISMATCH,
    MATCH_UNAVAILABLE,
    VeritasBaselineGovernanceAction,
    VeritasEvidenceConflict,
    VeritasEvidenceProvenanceRecord,
    VeritasEvidenceReadinessAssessment,
    VeritasFeedback,
    VeritasTrainingDatasetEntry,
)

_MIN_REPEAT = 2


def _entry(item: str, *, owner: str, next_action: str) -> dict:
    return {"item": item, "owner": owner, "recommended_next_action": next_action}


def no_approved_baseline(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(VeritasEvidenceReadinessAssessment)
        .filter(VeritasEvidenceReadinessAssessment.tenant_id == tenant_id, VeritasEvidenceReadinessAssessment.match_classification == MATCH_UNAVAILABLE)
        .all()
    )
    return [_entry(f"assessment:{r.id} ({r.instrument_identity})", owner="baseline_reviewer", next_action="Submit or approve a baseline for this instrument.") for r in rows]


def _latest_governance_by_baseline(db: Session, tenant_id: str) -> dict[tuple, VeritasBaselineGovernanceAction]:
    actions = db.query(VeritasBaselineGovernanceAction).filter(VeritasBaselineGovernanceAction.tenant_id == tenant_id).all()
    latest: dict[tuple, VeritasBaselineGovernanceAction] = {}
    for a in sorted(actions, key=lambda a: a.created_at):
        latest[(a.baseline_source_type, a.baseline_source_id)] = a
    return latest


def baseline_review_overdue(db: Session, tenant_id: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    latest = _latest_governance_by_baseline(db, tenant_id)
    return [
        _entry(f"{t}:{sid}", owner="baseline_reviewer", next_action="Complete the overdue baseline review.")
        for (t, sid), a in latest.items()
        if a.review_date and a.review_date < now and a.resulting_status in (BASELINE_STATUS_DRAFT, BASELINE_STATUS_PENDING_REVIEW, "")
    ]


def baseline_superseded(db: Session, tenant_id: str) -> list[dict]:
    latest = _latest_governance_by_baseline(db, tenant_id)
    return [
        _entry(f"{t}:{sid}", owner="baseline_reviewer", next_action="Confirm the replacement baseline is in active use.")
        for (t, sid), a in latest.items() if a.resulting_status == BASELINE_STATUS_SUPERSEDED
    ]


def repeated_poor_image_quality(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(VeritasEvidenceReadinessAssessment)
        .filter(VeritasEvidenceReadinessAssessment.tenant_id == tenant_id, VeritasEvidenceReadinessAssessment.image_quality_status == IMAGE_QUALITY_INSUFFICIENT)
        .all()
    )
    by_instrument: dict[str, int] = defaultdict(int)
    for r in rows:
        by_instrument[r.instrument_identity] += 1
    return [
        _entry(instrument, owner="technician", next_action="Recapture images meeting quality requirements.")
        for instrument, count in by_instrument.items() if count >= _MIN_REPEAT
    ]


def repeated_incomplete_coverage(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(VeritasEvidenceReadinessAssessment)
        .filter(VeritasEvidenceReadinessAssessment.tenant_id == tenant_id, VeritasEvidenceReadinessAssessment.coverage_status.in_([COVERAGE_INCOMPLETE, COVERAGE_INSUFFICIENT]))
        .all()
    )
    by_instrument: dict[str, int] = defaultdict(int)
    for r in rows:
        by_instrument[r.instrument_identity] += 1
    return [
        _entry(instrument, owner="technician", next_action="Capture the missing required anatomy zones.")
        for instrument, count in by_instrument.items() if count >= _MIN_REPEAT
    ]


def high_baseline_mismatch(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(VeritasEvidenceReadinessAssessment)
        .filter(VeritasEvidenceReadinessAssessment.tenant_id == tenant_id, VeritasEvidenceReadinessAssessment.match_classification == MATCH_MISMATCH)
        .all()
    )
    by_instrument: dict[str, int] = defaultdict(int)
    for r in rows:
        by_instrument[r.instrument_identity] += 1
    return [
        _entry(instrument, owner="baseline_reviewer", next_action="Resolve a correctly matched baseline for this instrument family.")
        for instrument, count in by_instrument.items() if count >= _MIN_REPEAT
    ]


def conflicting_evidence(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(VeritasEvidenceConflict)
        .filter(VeritasEvidenceConflict.tenant_id == tenant_id, VeritasEvidenceConflict.resolved.is_(False))
        .all()
    )
    return [_entry(f"conflict:{c.id} ({c.conflict_type})", owner=c.responsible_reviewer_role or "supervisor", next_action=c.recommended_resolution) for c in rows]


def unapproved_training_candidates(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(VeritasTrainingDatasetEntry)
        .filter(VeritasTrainingDatasetEntry.tenant_id == tenant_id, VeritasTrainingDatasetEntry.dataset_status != DATASET_APPROVED_FOR_TRAINING)
        .all()
    )
    return [_entry(f"training_entry:{e.id}", owner="dataset_reviewer", next_action=e.status_reason) for e in rows]


def missing_provenance(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(VeritasEvidenceProvenanceRecord)
        .filter(VeritasEvidenceProvenanceRecord.tenant_id == tenant_id, VeritasEvidenceProvenanceRecord.file_hash == "")
        .all()
    )
    return [_entry(f"provenance:{p.id} ({p.evidence_type})", owner="evidence_reviewer", next_action="Record the missing file hash/storage location.") for p in rows]


def repeated_evidence_gate_override(db: Session, tenant_id: str) -> list[dict]:
    overrides = (
        db.query(VeritasFeedback)
        .filter(VeritasFeedback.tenant_id == tenant_id, VeritasFeedback.action == FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE)
        .all()
    )
    by_submitter: dict[str, int] = defaultdict(int)
    for o in overrides:
        by_submitter[o.submitted_by] += 1
    return [
        _entry(submitter, owner="quality_leadership", next_action="Review override pattern for this reviewer.")
        for submitter, count in by_submitter.items() if count >= _MIN_REPEAT
    ]


WATCHLISTS = {
    "no_approved_baseline": no_approved_baseline,
    "baseline_review_overdue": baseline_review_overdue,
    "baseline_superseded": baseline_superseded,
    "repeated_poor_image_quality": repeated_poor_image_quality,
    "repeated_incomplete_coverage": repeated_incomplete_coverage,
    "high_baseline_mismatch": high_baseline_mismatch,
    "conflicting_evidence": conflicting_evidence,
    "unapproved_training_candidates": unapproved_training_candidates,
    "missing_provenance": missing_provenance,
    "repeated_evidence_gate_override": repeated_evidence_gate_override,
}


def run_watchlist(db: Session, tenant_id: str, name: str) -> list[dict] | None:
    fn = WATCHLISTS.get(name)
    return fn(db, tenant_id) if fn else None
