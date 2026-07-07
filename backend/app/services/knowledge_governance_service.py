"""v1.8 — Knowledge Governance (Deliverable 9).

Tracks author, reviewer, approval status, version, and last-review date on
every KnowledgeArticle, and archives outdated knowledge — governance is
enforced here, not left to convention.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.knowledge import APPROVED, ARCHIVED, PENDING_REVIEW, REJECTED, KnowledgeArticle


class ArticleNotFoundError(ValueError):
    pass


def _get(db: Session, tenant_id: str, article_id: int) -> KnowledgeArticle:
    row = (
        db.query(KnowledgeArticle)
        .filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.id == article_id)
        .first()
    )
    if row is None:
        raise ArticleNotFoundError(f"Knowledge article {article_id} not found.")
    return row


def submit_for_review(db: Session, tenant_id: str, article_id: int) -> KnowledgeArticle:
    row = _get(db, tenant_id, article_id)
    row.approval_status = PENDING_REVIEW
    return row


def approve_article(db: Session, tenant_id: str, article_id: int, *, reviewer: str) -> KnowledgeArticle:
    row = _get(db, tenant_id, article_id)
    row.approval_status = APPROVED
    row.reviewer = reviewer
    row.last_reviewed_at = datetime.now(timezone.utc)
    return row


def reject_article(db: Session, tenant_id: str, article_id: int, *, reviewer: str) -> KnowledgeArticle:
    row = _get(db, tenant_id, article_id)
    row.approval_status = REJECTED
    row.reviewer = reviewer
    row.last_reviewed_at = datetime.now(timezone.utc)
    return row


def archive_article(db: Session, tenant_id: str, article_id: int, *, reviewer: str) -> KnowledgeArticle:
    """Outdated knowledge is archived, never deleted — it stays available
    for audit but drops out of default search/list results."""
    row = _get(db, tenant_id, article_id)
    row.approval_status = ARCHIVED
    row.reviewer = reviewer
    row.last_reviewed_at = datetime.now(timezone.utc)
    return row


def governance_summary(db: Session, tenant_id: str) -> dict:
    rows = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id).all()
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r.approval_status] = by_status.get(r.approval_status, 0) + 1
    return {
        "total_articles": len(rows),
        "by_approval_status": by_status,
        "pending_review_count": by_status.get(PENDING_REVIEW, 0),
        "human_review_required": True,
    }
