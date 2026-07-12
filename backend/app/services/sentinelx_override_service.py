"""Project Sentinel-X, Sections 10 & 13: auditable supervisor override.

Sentinel-X's own risk level is always advisory. A supervisor may override
it, but the override is itself an append-only, auditable record -- never a
silent mutation of the original assessment's `risk_level`/`risk_score`.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sentinelx_risk import SentinelXRiskAssessment, SentinelXSupervisorOverride


def submit_override(
    db: Session, tenant_id: str, assessment_id: int, *, overridden_risk_level: str, rationale: str,
    submitted_by: str, submitted_role: str = "",
) -> SentinelXSupervisorOverride:
    if not rationale.strip():
        raise ValueError("rationale is required to override a Sentinel-X risk assessment")

    assessment = (
        db.query(SentinelXRiskAssessment)
        .filter(SentinelXRiskAssessment.id == assessment_id, SentinelXRiskAssessment.tenant_id == tenant_id)
        .first()
    )
    if assessment is None:
        raise ValueError("Sentinel-X risk assessment not found for this tenant")

    row = SentinelXSupervisorOverride(
        tenant_id=tenant_id, assessment_id=assessment_id, original_risk_level=assessment.risk_level,
        overridden_risk_level=overridden_risk_level, rationale=rationale, submitted_by=submitted_by,
        submitted_role=submitted_role,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: SentinelXSupervisorOverride) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "assessment_id": row.assessment_id,
        "original_risk_level": row.original_risk_level,
        "overridden_risk_level": row.overridden_risk_level,
        "rationale": row.rationale,
        "submitted_by": row.submitted_by,
        "submitted_role": row.submitted_role,
    }


def overrides_for_assessment(db: Session, tenant_id: str, assessment_id: int) -> list[dict]:
    rows = (
        db.query(SentinelXSupervisorOverride)
        .filter(SentinelXSupervisorOverride.tenant_id == tenant_id, SentinelXSupervisorOverride.assessment_id == assessment_id)
        .order_by(SentinelXSupervisorOverride.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
