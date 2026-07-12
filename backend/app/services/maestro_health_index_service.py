"""Project Maestro, Section 7: Operational Health Index.

Reuses Phoenix's already-computed platform maturity dimensions
(`phoenix_maturity_index_service.compute_platform_maturity_index`) directly
for Quality/Workflow/Education/Digital-Twins/Knowledge -- never re-derived.
"Enterprise" reuses Phoenix's executive-intelligence (audit-readiness)
dimension, the closest existing leadership-facing composite. "Equipment" is
genuinely new here: the average Vulcan Instrument Reliability Score across
recent assessments, a real measure of fleet condition Phoenix does not
track.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.maestro_orchestration import MaestroOperationalHealthSnapshot
from app.models.vulcan_reliability import VulcanReliabilityAssessment
from app.services.phoenix_maturity_index_service import compute_platform_maturity_index


def _equipment_score(db: Session, tenant_id: str) -> float | None:
    rows = (
        db.query(VulcanReliabilityAssessment)
        .filter(VulcanReliabilityAssessment.tenant_id == tenant_id)
        .order_by(VulcanReliabilityAssessment.created_at.desc())
        .limit(200)
        .all()
    )
    if not rows:
        return None
    return round(sum(r.reliability_score for r in rows) / len(rows), 1)


def compute_operational_health(db: Session, tenant_id: str) -> MaestroOperationalHealthSnapshot:
    maturity = compute_platform_maturity_index(db, tenant_id)
    scores = maturity["scores"]

    quality_score = scores.get("quality_score")
    workflow_score = scores.get("workflow_score")
    education_score = scores.get("education_score")
    digital_twin_score = scores.get("digital_twins_score")
    knowledge_score = scores.get("knowledge_score")
    enterprise_score = scores.get("executive_intelligence_score")
    equipment_score = _equipment_score(db, tenant_id)

    dimension_scores = {
        "quality_score": quality_score, "workflow_score": workflow_score, "education_score": education_score,
        "equipment_score": equipment_score, "digital_twin_score": digital_twin_score,
        "knowledge_score": knowledge_score, "enterprise_score": enterprise_score,
    }
    present = [v for v in dimension_scores.values() if v is not None]
    overall_score = round(sum(present) / len(present), 1) if present else None

    row = MaestroOperationalHealthSnapshot(
        tenant_id=tenant_id, quality_score=quality_score, workflow_score=workflow_score,
        education_score=education_score, equipment_score=equipment_score, digital_twin_score=digital_twin_score,
        knowledge_score=knowledge_score, enterprise_score=enterprise_score, overall_score=overall_score,
        breakdown_json=json.dumps({
            "source_phoenix_maturity_snapshot_id": maturity["id"], "dimension_scores": dimension_scores,
            "phoenix_factors": maturity["factors"],
        }),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: MaestroOperationalHealthSnapshot) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "quality_score": row.quality_score,
        "workflow_score": row.workflow_score,
        "education_score": row.education_score,
        "equipment_score": row.equipment_score,
        "digital_twin_score": row.digital_twin_score,
        "knowledge_score": row.knowledge_score,
        "enterprise_score": row.enterprise_score,
        "overall_score": row.overall_score,
        "breakdown": json.loads(row.breakdown_json or "{}"),
        "human_review_required": row.human_review_required,
    }
