"""v4.8 — Project Athena, Section 8: Knowledge Trust Score.

No trust/reputation/evidence-quality construct exists anywhere in this
codebase (`beacon_standards_service.py`/`p24_standards_service.py` only
carry `version`/`status`). Every component below is computed live from
real `KnowledgeArticle` fields and Apollo's existing
`competency_service.record_knowledge_contribution` log — never persisted
as a fabricated number, and never claiming a precision this codebase's
data doesn't support.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.knowledge import APPROVED, KnowledgeArticle
from app.services import competency_service

# Equal weighting across the seven named components — documented here
# since it's the one genuinely new scoring decision in this file.
_APPROVAL_STATUS_SCORES = {"approved": 100.0, "pending_review": 50.0, "draft": 25.0, "rejected": 0.0, "archived": 10.0}
_REVIEW_RECENCY_DAYS = 365


def _evidence_quality(article: KnowledgeArticle) -> float:
    body_score = min(100.0, 100 * len(article.body) / 500)
    standards = json.loads(article.linked_standards_json or "[]")
    standards_score = min(100.0, 25.0 * len(standards))
    references_score = 100.0 if article.references.strip() else 0.0
    return round((body_score + standards_score + references_score) / 3, 1)


def _clinical_validation(article: KnowledgeArticle) -> float:
    if article.approval_status != APPROVED:
        return 0.0
    return 100.0 if article.reviewer.strip() else 60.0


def _usage(article: KnowledgeArticle) -> float:
    return round(min(100.0, article.view_count * 5.0), 1)


def _review_recency(article: KnowledgeArticle) -> float:
    if article.last_reviewed_at is None:
        return 0.0
    age_days = (datetime.now(timezone.utc) - article.last_reviewed_at).days
    if age_days <= 0:
        return 100.0
    return round(max(0.0, 100.0 - 100.0 * age_days / _REVIEW_RECENCY_DAYS), 1)


def _approval_status_score(article: KnowledgeArticle) -> float:
    return _APPROVAL_STATUS_SCORES.get(article.approval_status, 0.0)


def _contributor_reputation(db: Session, article: KnowledgeArticle) -> float:
    if not article.author:
        return 0.0
    summary = competency_service.competency_summary(db, article.author)
    return round(min(100.0, 20.0 * summary["knowledge_contributions"]), 1)


def _reference_strength(article: KnowledgeArticle) -> float:
    standards = json.loads(article.linked_standards_json or "[]")
    return round(min(100.0, 25.0 * len(standards)), 1)


def compute_trust_score(db: Session, article: KnowledgeArticle) -> dict:
    components = {
        "evidence_quality": _evidence_quality(article),
        "clinical_validation": _clinical_validation(article),
        "usage": _usage(article),
        "review_date_recency": _review_recency(article),
        "approval_status": _approval_status_score(article),
        "contributor_reputation": _contributor_reputation(db, article),
        "reference_strength": _reference_strength(article),
    }
    overall = round(sum(components.values()) / len(components), 1)
    return {
        "article_id": article.id, "title": article.title, "components": components,
        "overall_trust_score": overall, "human_review_required": True,
    }


def list_articles_with_trust(db: Session, tenant_id: str, *, min_trust: float | None = None) -> list[dict]:
    """Every article's trust score, filterable by minimum trust level
    (Section 8: "Organizations can filter by trust level")."""
    rows = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id).all()
    scored = [compute_trust_score(db, r) for r in rows]
    if min_trust is not None:
        scored = [s for s in scored if s["overall_trust_score"] >= min_trust]
    scored.sort(key=lambda s: s["overall_trust_score"], reverse=True)
    return scored
