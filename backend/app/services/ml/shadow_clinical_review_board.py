"""Shadow §8 — Clinical Review Board.

A periodic, structured review record — who reviewed (SPD leadership,
quality, clinical advisors, AI engineering, product management),
performance/failure-mode/operational-impact/readiness narratives, and an
explicit readiness recommendation for one candidate model. Feeds the
Validated Candidate promotion gate
(``app.services.ml.candidate_promotion``) as one of its required items —
never defaulted to approved.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.shadow_validation import ClinicalReviewBoardSession


def record_review_session(
    db: Session, *, tenant_id: str, model_id: str, model_version: str = "",
    reviewers: list[dict[str, str]], performance_summary: str = "",
    failure_modes_summary: str = "", operational_impact: str = "",
    readiness_assessment: str = "", recommendations: str = "",
    review_period_start: datetime | None = None, review_period_end: datetime | None = None,
    approved: bool | None = None, decided_by: str = "",
) -> ClinicalReviewBoardSession:
    row = ClinicalReviewBoardSession(
        tenant_id=tenant_id, model_id=model_id, model_version=model_version,
        reviewers_json=json.dumps(reviewers),
        performance_summary=performance_summary,
        failure_modes_summary=failure_modes_summary,
        operational_impact=operational_impact,
        readiness_assessment=readiness_assessment,
        recommendations=recommendations,
        review_period_start=review_period_start,
        review_period_end=review_period_end,
        approved=approved,
        decided_by=decided_by,
        decided_at=datetime.now(timezone.utc) if approved is not None else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def latest_session(db: Session, *, tenant_id: str, model_id: str, model_version: str = "") -> ClinicalReviewBoardSession | None:
    q = db.query(ClinicalReviewBoardSession).filter(
        ClinicalReviewBoardSession.tenant_id == tenant_id,
        ClinicalReviewBoardSession.model_id == model_id,
    )
    if model_version:
        q = q.filter(ClinicalReviewBoardSession.model_version == model_version)
    return q.order_by(ClinicalReviewBoardSession.id.desc()).first()


def board_approved(db: Session, *, tenant_id: str, model_id: str, model_version: str = "") -> bool:
    session = latest_session(db, tenant_id=tenant_id, model_id=model_id, model_version=model_version)
    return bool(session and session.approved is True)


def as_dict(row: ClinicalReviewBoardSession) -> dict[str, Any]:
    return {
        "id": row.id,
        "model_id": row.model_id,
        "model_version": row.model_version,
        "reviewers": json.loads(row.reviewers_json or "[]"),
        "performance_summary": row.performance_summary,
        "failure_modes_summary": row.failure_modes_summary,
        "operational_impact": row.operational_impact,
        "readiness_assessment": row.readiness_assessment,
        "recommendations": row.recommendations,
        "review_period_start": row.review_period_start.isoformat() if row.review_period_start else None,
        "review_period_end": row.review_period_end.isoformat() if row.review_period_end else None,
        "approved": row.approved,
        "decided_by": row.decided_by,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
    }
