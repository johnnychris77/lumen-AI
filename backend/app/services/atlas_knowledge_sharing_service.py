"""v3.1 — Project Atlas, Section 6: Enterprise Knowledge Sharing.

A publish-a-copy pattern — the source `KnowledgeArticle` (tenant-scoped,
`app/models/knowledge.py`) is never mutated or exposed cross-tenant
directly. Only `approved` articles can be shared. Unlike the k-anonymity/
differential-privacy machinery `global_intelligence.py`/
`instrument_registry.py` apply to aggregated clinical *metrics* (where
re-identifying a facility could expose competitively sensitive
performance data), shared knowledge content — best practices, anatomy
guidance, educational material — is authored text, not a facility's
clinical performance, so no k-anonymity suppression applies here. What
does still apply, per this platform's audit rule, is that every share is
its own audited event.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.models.atlas_enterprise import SHARE_SCOPES, SharedKnowledgeArticle
from app.models.knowledge import APPROVED, KnowledgeArticle


class ArticleNotApprovedError(Exception):
    pass


class ArticleNotFoundError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def share_article(
    db: Session, system_id: str, *, source_tenant_id: str, source_article_id: int, owner: str,
    approver: str = "", sharing_scope: str = "system_wide", effective_date: datetime | None = None,
) -> dict:
    if sharing_scope not in SHARE_SCOPES:
        raise ValueError(f"sharing_scope must be one of {SHARE_SCOPES}")

    article = (
        db.query(KnowledgeArticle)
        .filter(KnowledgeArticle.id == source_article_id, KnowledgeArticle.tenant_id == source_tenant_id)
        .first()
    )
    if article is None:
        raise ArticleNotFoundError(f"Knowledge article {source_article_id} not found for tenant {source_tenant_id}.")
    if article.approval_status != APPROVED:
        raise ArticleNotApprovedError(
            f"Article {source_article_id} is '{article.approval_status}', not approved — only approved articles can be shared.",
        )

    row = SharedKnowledgeArticle(
        system_id=system_id, source_tenant_id=source_tenant_id, source_article_id=source_article_id,
        category=article.category, title=article.title, body=article.body, owner=owner, approver=approver,
        version=article.version, effective_date=effective_date or datetime.now(timezone.utc), sharing_scope=sharing_scope,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db, tenant_id=source_tenant_id, tenant_name=source_tenant_id, actor_email=owner, actor_role="",
        action_type="atlas.knowledge_article_shared", resource_type="shared_knowledge_article", resource_id=str(row.id),
        details={"system_id": system_id, "source_article_id": source_article_id, "sharing_scope": sharing_scope},
    )
    return _row_to_dict(row)


def list_shared_articles(db: Session, system_id: str, *, sharing_scope: str = "", category: str = "") -> list[dict]:
    q = db.query(SharedKnowledgeArticle).filter(SharedKnowledgeArticle.system_id == system_id, SharedKnowledgeArticle.active.is_(True))
    if sharing_scope:
        q = q.filter(SharedKnowledgeArticle.sharing_scope == sharing_scope)
    if category:
        q = q.filter(SharedKnowledgeArticle.category == category)
    rows = q.order_by(SharedKnowledgeArticle.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def get_shared_article(db: Session, system_id: str, article_id: int) -> dict | None:
    row = db.query(SharedKnowledgeArticle).filter(SharedKnowledgeArticle.id == article_id, SharedKnowledgeArticle.system_id == system_id).first()
    return _row_to_dict(row) if row else None


def retract_shared_article(db: Session, system_id: str, article_id: int, *, retracted_by: str) -> dict | None:
    row = db.query(SharedKnowledgeArticle).filter(SharedKnowledgeArticle.id == article_id, SharedKnowledgeArticle.system_id == system_id).first()
    if row is None:
        return None
    row.active = False
    db.commit()
    db.refresh(row)
    log_audit_event(
        db, tenant_id=row.source_tenant_id, tenant_name=row.source_tenant_id, actor_email=retracted_by, actor_role="",
        action_type="atlas.knowledge_article_retracted", resource_type="shared_knowledge_article", resource_id=str(article_id),
        details={"system_id": system_id},
    )
    return _row_to_dict(row)
