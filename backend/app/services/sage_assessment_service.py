"""Project Sage, Section 7: Competency Assessment Builder.

Results remain advisory (`result_status = "advisory"`) until an authorized
evaluator validates them -- mirrors Vulcan's `recommended_disposition` vs
`final_disposition` split: Sage's own scoring is never treated as a final
competency determination.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.sage_education import ASSESSMENT_FORMATS, SageAssessment


def create_assessment(
    db: Session, tenant_id: str, *, assessment_format: str, target_learner: str,
    competency_domain: str = "", content: dict | None = None, learning_plan_id: int | None = None,
) -> SageAssessment:
    if assessment_format not in ASSESSMENT_FORMATS:
        raise ValueError(f"Unknown assessment_format '{assessment_format}'")
    row = SageAssessment(
        tenant_id=tenant_id, learning_plan_id=learning_plan_id, assessment_format=assessment_format,
        target_learner=target_learner, competency_domain=competency_domain, content_json=json.dumps(content or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def record_result(db: Session, tenant_id: str, assessment_id: int, *, result: dict) -> SageAssessment | None:
    row = db.query(SageAssessment).filter(SageAssessment.id == assessment_id, SageAssessment.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.result_json = json.dumps(result)
    row.result_status = "advisory"
    db.commit()
    db.refresh(row)
    return row


def validate_result(db: Session, tenant_id: str, assessment_id: int, *, validated_by: str) -> SageAssessment | None:
    row = db.query(SageAssessment).filter(SageAssessment.id == assessment_id, SageAssessment.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.result_status = "validated"
    row.validated_by = validated_by
    row.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: SageAssessment) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "learning_plan_id": row.learning_plan_id,
        "assessment_format": row.assessment_format,
        "target_learner": row.target_learner,
        "competency_domain": row.competency_domain,
        "content": json.loads(row.content_json or "{}"),
        "result": json.loads(row.result_json or "{}"),
        "result_status": row.result_status,
        "validated_by": row.validated_by,
        "validated_at": row.validated_at.isoformat() if row.validated_at else None,
    }


def list_assessments(db: Session, tenant_id: str, *, target_learner: str = "") -> list[dict]:
    q = db.query(SageAssessment).filter(SageAssessment.tenant_id == tenant_id)
    if target_learner:
        q = q.filter(SageAssessment.target_learner == target_learner)
    return [to_dict(r) for r in q.order_by(SageAssessment.created_at.desc()).all()]
