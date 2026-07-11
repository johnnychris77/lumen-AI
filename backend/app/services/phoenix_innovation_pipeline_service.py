"""v4.9 — Project Phoenix, Section 8: Innovation Pipeline.

No Idea/Evidence/ROI/Clinical-Impact/Roadmap backlog concept existed
anywhere in this codebase before Phoenix (confirmed by grep) — genuinely
new. Ideas never auto-advance to `in_progress`/`completed`; every status
transition is an explicit human action.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.phoenix_intelligence import (
    CLINICAL_IMPACT_LEVELS,
    IDEA_APPROVAL_STATUSES,
    PRIORITY_LEVELS,
    TECHNICAL_COMPLEXITY_LEVELS,
    InnovationIdea,
)


class InnovationIdeaNotFoundError(ValueError):
    pass


def _to_dict(row: InnovationIdea) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "title": row.title, "description": row.description,
        "evidence": row.evidence, "estimated_roi_usd": row.estimated_roi_usd, "clinical_impact": row.clinical_impact,
        "technical_complexity": row.technical_complexity, "priority": row.priority,
        "approval_status": row.approval_status, "roadmap_assignment": row.roadmap_assignment,
        "submitted_by": row.submitted_by,
    }


def create_idea(
    db: Session, tenant_id: str, *, title: str, description: str = "", evidence: str = "",
    estimated_roi_usd: float | None = None, clinical_impact: str = "medium", technical_complexity: str = "medium",
    priority: str = "medium", submitted_by: str = "",
) -> dict:
    if clinical_impact not in CLINICAL_IMPACT_LEVELS:
        raise ValueError(f"clinical_impact must be one of {CLINICAL_IMPACT_LEVELS}")
    if technical_complexity not in TECHNICAL_COMPLEXITY_LEVELS:
        raise ValueError(f"technical_complexity must be one of {TECHNICAL_COMPLEXITY_LEVELS}")
    if priority not in PRIORITY_LEVELS:
        raise ValueError(f"priority must be one of {PRIORITY_LEVELS}")

    row = InnovationIdea(
        tenant_id=tenant_id, title=title, description=description, evidence=evidence,
        estimated_roi_usd=estimated_roi_usd, clinical_impact=clinical_impact,
        technical_complexity=technical_complexity, priority=priority, submitted_by=submitted_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_ideas(db: Session, tenant_id: str, *, approval_status: str = "") -> list[dict]:
    q = db.query(InnovationIdea).filter(InnovationIdea.tenant_id == tenant_id)
    if approval_status:
        q = q.filter(InnovationIdea.approval_status == approval_status)
    return [_to_dict(r) for r in q.order_by(InnovationIdea.created_at.desc()).all()]


def _get(db: Session, tenant_id: str, idea_id: int) -> InnovationIdea:
    row = db.query(InnovationIdea).filter(InnovationIdea.id == idea_id, InnovationIdea.tenant_id == tenant_id).first()
    if row is None:
        raise InnovationIdeaNotFoundError(f"Innovation idea {idea_id} not found for tenant {tenant_id}.")
    return row


def update_idea_status(db: Session, tenant_id: str, idea_id: int, *, approval_status: str, roadmap_assignment: str = "") -> dict:
    if approval_status not in IDEA_APPROVAL_STATUSES:
        raise ValueError(f"approval_status must be one of {IDEA_APPROVAL_STATUSES}")
    row = _get(db, tenant_id, idea_id)
    row.approval_status = approval_status
    if roadmap_assignment:
        row.roadmap_assignment = roadmap_assignment
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def get_idea(db: Session, tenant_id: str, idea_id: int) -> dict:
    return _to_dict(_get(db, tenant_id, idea_id))


def pipeline_summary(db: Session, tenant_id: str) -> dict:
    rows = db.query(InnovationIdea).filter(InnovationIdea.tenant_id == tenant_id).all()
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    total_estimated_roi = 0.0
    for r in rows:
        by_status[r.approval_status] = by_status.get(r.approval_status, 0) + 1
        by_priority[r.priority] = by_priority.get(r.priority, 0) + 1
        if r.estimated_roi_usd:
            total_estimated_roi += r.estimated_roi_usd
    return {
        "total_ideas": len(rows), "by_status": by_status, "by_priority": by_priority,
        "total_estimated_roi_usd": round(total_estimated_roi, 2) if total_estimated_roi else 0.0,
        "human_review_required": True,
    }
