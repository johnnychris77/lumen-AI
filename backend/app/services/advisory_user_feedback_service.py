"""Advisor — Phase 7 §7: User Experience feedback collection.

No existing model in this codebase collects structured technician/
supervisor trust-in-AI feedback (Sage's feedback is about learning-plan
coaching; Vulcan's is about instrument-reliability predictions) — this is
genuinely new. Averages are computed only over respondents who actually
rated a given dimension; an unrated dimension is never assumed to be
neutral or default.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.advisory_pilot import AdvisoryUserFeedback

_DIMENSIONS = ("ease_of_use", "trust", "clarity", "explainability_rating", "confidence", "perceived_value")


def record_feedback(
    db: Session, *, tenant_id: str, submitted_by: str, submitted_role: str,
    ease_of_use: int | None = None, trust: int | None = None, clarity: int | None = None,
    explainability_rating: int | None = None, confidence: int | None = None,
    perceived_value: int | None = None, suggestions: str = "",
) -> AdvisoryUserFeedback:
    row = AdvisoryUserFeedback(
        tenant_id=tenant_id, submitted_by=submitted_by, submitted_role=submitted_role,
        ease_of_use=ease_of_use, trust=trust, clarity=clarity,
        explainability_rating=explainability_rating, confidence=confidence,
        perceived_value=perceived_value, suggestions=suggestions,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _avg(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def feedback_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    rows = db.query(AdvisoryUserFeedback).filter(AdvisoryUserFeedback.tenant_id == tenant_id).all()

    overall = {
        dim: _avg([getattr(r, dim) for r in rows if getattr(r, dim) is not None])
        for dim in _DIMENSIONS
    }

    by_role: dict[str, dict[str, Any]] = defaultdict(dict)
    roles = sorted({r.submitted_role for r in rows if r.submitted_role})
    for role in roles:
        role_rows = [r for r in rows if r.submitted_role == role]
        by_role[role] = {
            dim: _avg([getattr(r, dim) for r in role_rows if getattr(r, dim) is not None])
            for dim in _DIMENSIONS
        }
        by_role[role]["n"] = len(role_rows)

    return {
        "total_responses": len(rows),
        "overall": overall,
        "by_role": dict(by_role),
        "suggestions": [r.suggestions for r in rows if r.suggestions],
        "human_review_required": True,
    }
