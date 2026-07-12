"""Project Sage: persistence + retrieval for detected knowledge gaps
(Section 3), separate from the pure-detection logic in
`sage_gap_detection_service.py` so gaps can be re-listed/filtered without
re-scanning source data every time.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.sage_education import SageKnowledgeGap
from app.services.sage_gap_detection_service import detect_all_gaps_for_technician


def _to_dict(row: SageKnowledgeGap) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "competency_domain": row.competency_domain,
        "scope_type": row.scope_type,
        "scope_value": row.scope_value,
        "instrument_family": row.instrument_family,
        "anatomy_zone": row.anatomy_zone,
        "finding_category": row.finding_category,
        "occurrence_count": row.occurrence_count,
        "confidence": row.confidence,
        "evidence": json.loads(row.evidence_json or "{}"),
        "narrative": row.narrative,
        "recommended_education": row.recommended_education,
        "status": row.status,
        "human_review_required": row.human_review_required,
        "agent_version": row.agent_version,
        "disclaimer": row.disclaimer,
    }


def run_gap_detection_for_technician(db: Session, tenant_id: str, technician: str, window_days: int = 90) -> list[dict]:
    """Detect and persist gaps for one technician. Idempotent-ish: re-running
    creates a fresh snapshot row per call (each is a point-in-time detection,
    same pattern as Vulcan's assessments)."""
    detected = detect_all_gaps_for_technician(db, tenant_id, technician, window_days)
    rows = []
    for gap in detected:
        row = SageKnowledgeGap(
            tenant_id=tenant_id,
            competency_domain=gap["competency_domain"],
            scope_type=gap["scope_type"],
            scope_value=gap["scope_value"],
            instrument_family=gap.get("instrument_family", ""),
            anatomy_zone=gap.get("anatomy_zone", ""),
            finding_category=gap.get("finding_category", ""),
            occurrence_count=gap["occurrence_count"],
            confidence=gap["confidence"],
            evidence_json=json.dumps(gap["evidence"]),
            narrative=gap["narrative"],
            recommended_education=gap["recommended_education"],
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return [_to_dict(row) for row in rows]


def list_gaps(
    db: Session, tenant_id: str, *, competency_domain: str = "", scope_type: str = "", scope_value: str = "",
    instrument_family: str = "", anatomy_zone: str = "", status: str = "",
) -> list[dict]:
    q = db.query(SageKnowledgeGap).filter(SageKnowledgeGap.tenant_id == tenant_id)
    if competency_domain:
        q = q.filter(SageKnowledgeGap.competency_domain == competency_domain)
    if scope_type:
        q = q.filter(SageKnowledgeGap.scope_type == scope_type)
    if scope_value:
        q = q.filter(SageKnowledgeGap.scope_value == scope_value)
    if instrument_family:
        q = q.filter(SageKnowledgeGap.instrument_family == instrument_family)
    if anatomy_zone:
        q = q.filter(SageKnowledgeGap.anatomy_zone == anatomy_zone)
    if status:
        q = q.filter(SageKnowledgeGap.status == status)
    return [_to_dict(r) for r in q.order_by(SageKnowledgeGap.created_at.desc()).all()]


def get_gap(db: Session, tenant_id: str, gap_id: int) -> dict | None:
    row = db.query(SageKnowledgeGap).filter(SageKnowledgeGap.id == gap_id, SageKnowledgeGap.tenant_id == tenant_id).first()
    return _to_dict(row) if row else None
