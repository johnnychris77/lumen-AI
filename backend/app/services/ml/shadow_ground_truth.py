"""Shadow §3 — Ground Truth Collection.

Records the full technician -> supervisor -> adjudicator finding chain for
one inspection, with reviewer identities and per-stage timestamps. Ground
truth is always the final human-reviewed outcome: the adjudicated finding
when one has been recorded, otherwise the supervisor finding, never the
AI's own prediction.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.shadow_validation import ShadowGroundTruth


def record_technician_finding(
    db: Session, *, tenant_id: str, inspection_id: int, model_id: str = "",
    model_version: str = "", facility_id: str = "",
    technician_finding: str, technician_name: str,
) -> ShadowGroundTruth:
    """Create (or update, if one already exists for this inspection) the
    ground-truth row with the original technician finding."""
    row = (
        db.query(ShadowGroundTruth)
        .filter(ShadowGroundTruth.tenant_id == tenant_id, ShadowGroundTruth.inspection_id == inspection_id)
        .first()
    )
    if row is None:
        row = ShadowGroundTruth(
            tenant_id=tenant_id, inspection_id=inspection_id, model_id=model_id,
            model_version=model_version, facility_id=facility_id,
        )
        db.add(row)
    row.technician_finding = technician_finding
    row.technician_name = technician_name
    row.technician_reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def record_supervisor_finding(
    db: Session, row: ShadowGroundTruth, *, supervisor_finding: str, supervisor_name: str,
) -> ShadowGroundTruth:
    row.supervisor_finding = supervisor_finding
    row.supervisor_name = supervisor_name
    row.supervisor_reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def record_adjudication(
    db: Session, row: ShadowGroundTruth, *, final_adjudicated_finding: str, adjudicator_name: str,
    reason_for_correction: str = "", supporting_evidence: str = "",
) -> ShadowGroundTruth:
    """Only needed when the adjudicated finding differs from the
    supervisor's — ``reason_for_correction`` should explain why."""
    row.final_adjudicated_finding = final_adjudicated_finding
    row.adjudicator_name = adjudicator_name
    row.adjudicated_at = datetime.now(timezone.utc)
    row.reason_for_correction = reason_for_correction
    row.supporting_evidence = supporting_evidence
    db.commit()
    db.refresh(row)
    return row


def final_finding(row: ShadowGroundTruth) -> str:
    """The ground truth: the adjudicated finding when one exists, otherwise
    the supervisor's finding — never the AI's prediction."""
    return row.final_adjudicated_finding or row.supervisor_finding


def is_locked(row: ShadowGroundTruth) -> bool:
    """Ground truth is locked once a supervisor finding has been recorded
    (the human decision this program measures the AI against)."""
    return bool(row.supervisor_finding)
