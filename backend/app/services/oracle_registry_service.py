"""Project Oracle, Section 13: Research Registry.

A queryable index over every `OracleHypothesis` a tenant has -- filtered
search plus a stage/category/confidence/outcome rollup. Composes
`oracle_hypothesis_service.list_hypotheses`'s filters rather than
re-implementing the query.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.oracle_discovery import (
    CONFIDENCE_LEVELS,
    DISCOVERY_CATEGORIES,
    HYPOTHESIS_OUTCOMES,
    STAGE_REJECTED,
    VALIDATION_STAGES,
    OracleHypothesis,
)
from app.services import oracle_hypothesis_service


def search_registry(
    db: Session, tenant_id: str, *, query: str = "", discovery_category: str = "", confidence_level: str = "",
    current_stage: str = "", outcome: str = "",
) -> list[dict]:
    results = oracle_hypothesis_service.list_hypotheses(
        db, tenant_id, discovery_category=discovery_category, confidence_level=confidence_level,
        current_stage=current_stage, outcome=outcome,
    )
    if not query.strip():
        return results
    needle = query.strip().lower()
    return [
        r for r in results
        if needle in r["title"].lower() or needle in r["observation_summary"].lower()
        or needle in r["hypothesis_statement"].lower()
    ]


def registry_summary(db: Session, tenant_id: str) -> dict:
    rows = db.query(OracleHypothesis).filter(OracleHypothesis.tenant_id == tenant_id).all()
    by_category = {c: 0 for c in DISCOVERY_CATEGORIES}
    by_stage = {s: 0 for s in VALIDATION_STAGES}
    by_stage[STAGE_REJECTED] = 0
    by_confidence = {c: 0 for c in CONFIDENCE_LEVELS}
    by_outcome = {o or "pending": 0 for o in HYPOTHESIS_OUTCOMES}
    for r in rows:
        by_category[r.discovery_category] = by_category.get(r.discovery_category, 0) + 1
        by_stage[r.current_stage] = by_stage.get(r.current_stage, 0) + 1
        by_confidence[r.confidence_level] = by_confidence.get(r.confidence_level, 0) + 1
        key = r.outcome or "pending"
        by_outcome[key] = by_outcome.get(key, 0) + 1
    return {
        "total_hypotheses": len(rows),
        "by_category": by_category,
        "by_stage": by_stage,
        "by_confidence": by_confidence,
        "by_outcome": by_outcome,
    }
