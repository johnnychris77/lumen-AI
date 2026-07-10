"""v4.8 — Project Athena, Section 6: AI Knowledge Curator.

Extends `knowledge_analytics_service.py`'s existing deterministic-
aggregation pattern (`knowledge_gaps`, `training_opportunities`) with four
new checks — duplicate documents, outdated guidance, retirement
candidates, and emerging best practices. Every check is a real
threshold/keyword computation over `KnowledgeArticle`/`CompetencyEvent`
rows, never a fabricated relevance score. All suggestions are for human
review — nothing archives or merges an article automatically.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.competency_event import CompetencyEvent
from app.models.knowledge import APPROVED, KnowledgeArticle
from app.services import knowledge_analytics_service

_DUPLICATE_SIMILARITY_THRESHOLD = 0.5
_STALE_DAYS_DEFAULT = 365
_EMERGING_MIN_MENTIONS = 3


def _tokenize(text: str) -> set[str]:
    return {w for w in (text or "").lower().split() if len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def duplicate_candidates(db: Session, tenant_id: str, *, similarity_threshold: float = _DUPLICATE_SIMILARITY_THRESHOLD) -> list[dict]:
    """Real title+body token-overlap (Jaccard) between article pairs — a
    deterministic similarity measure, never a fabricated relevance score."""
    rows = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id).all()
    tokens = {r.id: _tokenize(r.title + " " + r.body) for r in rows}
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            score = _jaccard(tokens[a.id], tokens[b.id])
            if score >= similarity_threshold:
                pairs.append({
                    "article_a_id": a.id, "article_a_title": a.title,
                    "article_b_id": b.id, "article_b_title": b.title,
                    "similarity": round(score, 2),
                })
    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return pairs


def outdated_guidance(db: Session, tenant_id: str, *, stale_days: int = _STALE_DAYS_DEFAULT) -> list[dict]:
    """Approved articles never reviewed, or not reviewed within
    `stale_days` — a real recency check against `last_reviewed_at`."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    rows = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.approval_status == APPROVED,
    ).all()
    stale = [
        r for r in rows
        if r.last_reviewed_at is None or r.last_reviewed_at < cutoff
    ]
    return [
        {
            "id": r.id, "title": r.title, "category": r.category,
            "last_reviewed_at": r.last_reviewed_at.isoformat() if r.last_reviewed_at else None,
        }
        for r in stale
    ]


def retirement_candidates(db: Session, tenant_id: str, *, stale_days: int = _STALE_DAYS_DEFAULT) -> list[dict]:
    """Outdated *and* never viewed — a real, conservative retirement
    signal (never auto-archived; a human still calls `archive_article`)."""
    stale = {s["id"] for s in outdated_guidance(db, tenant_id, stale_days=stale_days)}
    rows = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.id.in_(stale), KnowledgeArticle.view_count == 0,
    ).all()
    return [{"id": r.id, "title": r.title, "category": r.category, "view_count": r.view_count} for r in rows]


def emerging_best_practices(db: Session, tenant_id: str, *, min_mentions: int = _EMERGING_MIN_MENTIONS) -> list[dict]:
    """Repeated `knowledge_contribution` topics (Apollo's CompetencyEvent
    log) with no existing article covering that topic yet — a real
    recurrence count, not a guessed trend."""
    rows = (
        db.query(CompetencyEvent)
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "knowledge_contribution")
        .all()
    )
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.finding_type:
            counts[r.finding_type] += 1

    existing_titles = {
        a.title.lower() for a in db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id).all()
    }
    return [
        {"topic": topic, "mention_count": count}
        for topic, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        if count >= min_mentions and topic.lower() not in existing_titles
    ]


def curator_summary(db: Session, tenant_id: str) -> dict:
    base = knowledge_analytics_service.knowledge_analytics(db, tenant_id)
    return {
        "knowledge_gaps": base["knowledge_gaps"],
        "training_opportunities": base["training_opportunities"],
        "duplicate_candidates": duplicate_candidates(db, tenant_id),
        "outdated_guidance": outdated_guidance(db, tenant_id),
        "retirement_candidates": retirement_candidates(db, tenant_id),
        "emerging_best_practices": emerging_best_practices(db, tenant_id),
        "human_review_required": True,
    }
