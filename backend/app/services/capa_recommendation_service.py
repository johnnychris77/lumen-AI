"""v2.9 — LumenAI Quality (Project Guardian), Section 6: CAPA Recommendation
Engine.

Suggests a typed corrective/preventive action from an approved RCA draft or
classified quality event. A suggestion is only a `CAPARecommendation` row
until a human accepts it — acceptance is what materializes a real CAPA via
`capa_lifecycle_service`, never automatic.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.quality_guardian import (
    RECOMMEND_COMPETENCY_REVIEW,
    RECOMMEND_EDUCATION,
    RECOMMEND_EQUIPMENT_EVALUATION,
    RECOMMEND_FOLLOW_UP_INSPECTION,
    RECOMMEND_OBSERVATION,
    RECOMMEND_PROCESS_AUDIT,
    RECOMMEND_REPAIR_REFERRAL,
    CAPARecommendation,
    QualityEvent,
    RCADraft,
)
from app.services import capa_lifecycle_service

_RECOMMENDATIONS_BY_CATEGORY: dict[str, list[tuple[str, str]]] = {
    "organic_residue": [
        (RECOMMEND_EDUCATION, "Recurring organic residue findings typically respond to a manual-cleaning refresher."),
        (RECOMMEND_COMPETENCY_REVIEW, "Review the responsible technician's cleaning competency."),
    ],
    "instrument_condition": [
        (RECOMMEND_EQUIPMENT_EVALUATION, "Instrument condition findings warrant an equipment/instrument evaluation."),
        (RECOMMEND_REPAIR_REFERRAL, "Refer the instrument for repair evaluation."),
    ],
    "assembly": [
        (RECOMMEND_PROCESS_AUDIT, "Assembly errors suggest a tray-assembly process audit is warranted."),
        (RECOMMEND_OBSERVATION, "Direct observation of the assembly step may surface a process gap."),
    ],
    "packaging": [
        (RECOMMEND_PROCESS_AUDIT, "Packaging failures warrant a packaging/wrapping process audit."),
    ],
    "sterilization_indicators": [
        (RECOMMEND_EQUIPMENT_EVALUATION, "Indicator failures warrant a sterilizer equipment evaluation."),
        (RECOMMEND_FOLLOW_UP_INSPECTION, "A follow-up inspection is warranted for affected loads."),
    ],
    "unknown": [
        (RECOMMEND_OBSERVATION, "Insufficient classification to recommend a specific action — direct observation is a safe first step."),
    ],
}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


class RecommendationNotFoundError(Exception):
    pass


def generate_recommendations(db: Session, tenant_id: str, *, event_id: int | None = None, rca_draft_id: int | None = None) -> list[dict]:
    category = "unknown"
    inspection_id = None
    if rca_draft_id is not None:
        draft = db.query(RCADraft).filter(RCADraft.id == rca_draft_id, RCADraft.tenant_id == tenant_id).first()
        if draft is not None:
            inspection_id = draft.inspection_id
            event = db.query(QualityEvent).filter(QualityEvent.id == draft.event_id).first()
            category = (event.spd_category if event else None) or "unknown"
    elif event_id is not None:
        event = db.query(QualityEvent).filter(QualityEvent.id == event_id, QualityEvent.tenant_id == tenant_id).first()
        category = (event.spd_category if event else None) or "unknown"

    created = []
    for recommendation_type, rationale in _RECOMMENDATIONS_BY_CATEGORY.get(category, _RECOMMENDATIONS_BY_CATEGORY["unknown"]):
        row = CAPARecommendation(
            tenant_id=tenant_id, event_id=event_id, rca_draft_id=rca_draft_id, inspection_id=inspection_id,
            recommendation_type=recommendation_type, rationale=rationale,
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return [_row_to_dict(r) for r in created]


def list_recommendations(db: Session, tenant_id: str, *, status: str = "") -> list[dict]:
    q = db.query(CAPARecommendation).filter(CAPARecommendation.tenant_id == tenant_id)
    if status:
        q = q.filter(CAPARecommendation.status == status)
    rows = q.order_by(CAPARecommendation.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def _get_recommendation(db: Session, tenant_id: str, recommendation_id: int) -> CAPARecommendation:
    row = (
        db.query(CAPARecommendation)
        .filter(CAPARecommendation.id == recommendation_id, CAPARecommendation.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise RecommendationNotFoundError(f"CAPA recommendation {recommendation_id} not found for tenant {tenant_id}.")
    return row


def accept_recommendation(
    db: Session, tenant_id: str, recommendation_id: int, *, title: str, owner: str, due_date: str | None = None,
    decided_by: str = "",
) -> dict:
    row = _get_recommendation(db, tenant_id, recommendation_id)
    if row.status != "suggested":
        raise ValueError(f"Recommendation {recommendation_id} is already {row.status}.")

    capa = capa_lifecycle_service.create_capa_with_recommendation(
        tenant_id, recommendation_type=row.recommendation_type, title=title, description=row.rationale,
        owner=owner, due_date=due_date, linked_event_id=row.event_id, linked_inspection_id=row.inspection_id,
    )
    row.status = "accepted"
    row.created_capa_id = capa["id"]
    row.decided_by = decided_by
    row.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    result = _row_to_dict(row)
    result["capa"] = capa
    return result


def dismiss_recommendation(db: Session, tenant_id: str, recommendation_id: int, *, decided_by: str) -> dict:
    row = _get_recommendation(db, tenant_id, recommendation_id)
    if row.status != "suggested":
        raise ValueError(f"Recommendation {recommendation_id} is already {row.status}.")
    row.status = "dismissed"
    row.decided_by = decided_by
    row.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
