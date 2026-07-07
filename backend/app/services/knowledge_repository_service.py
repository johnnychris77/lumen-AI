"""v1.8 — Institutional Knowledge Repository (Deliverable 1).

CRUD + faceted search over KnowledgeArticle. Search facets are matched
against real, stored data only — an article with no `applicable_findings`
declared simply never matches a finding-facet search, it is never guessed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.knowledge import DRAFT, PENDING_REVIEW, KnowledgeArticle


def _dump(values: list[str] | None) -> str:
    return json.dumps(list(values or []))


def _load(text: str) -> list[str]:
    try:
        return json.loads(text or "[]")
    except (TypeError, ValueError):
        return []


def create_article(
    db: Session, *, tenant_id: str, category: str, title: str, body: str, author: str,
    applicable_instruments: list[str] | None = None, applicable_findings: list[str] | None = None,
    applicable_manufacturers: list[str] | None = None, anatomy_zone: str = "", procedure: str = "",
    specialty: str = "", common_mistake: str = "", prevention_tip: str = "", references: str = "",
    source_inspection_id: int | None = None, approval_status: str = DRAFT,
) -> KnowledgeArticle:
    row = KnowledgeArticle(
        tenant_id=tenant_id, category=category, title=title.strip(), body=body.strip(), author=author,
        applicable_instruments=_dump(applicable_instruments), applicable_findings=_dump(applicable_findings),
        applicable_manufacturers=_dump(applicable_manufacturers), anatomy_zone=anatomy_zone.strip(),
        procedure=procedure.strip(), specialty=specialty.strip(), common_mistake=common_mistake.strip(),
        prevention_tip=prevention_tip.strip(), references=references.strip(),
        source_inspection_id=source_inspection_id, approval_status=approval_status,
    )
    db.add(row)
    return row


def update_article(db: Session, tenant_id: str, article_id: int, *, title: str | None = None, body: str | None = None) -> KnowledgeArticle | None:
    """Editing an approved article's substance bumps the version and sends it
    back to pending_review — an edit is never silently applied to knowledge
    staff are already relying on as approved."""
    row = (
        db.query(KnowledgeArticle)
        .filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.id == article_id)
        .first()
    )
    if row is None:
        return None
    changed = False
    if title is not None and title.strip() != row.title:
        row.title = title.strip()
        changed = True
    if body is not None and body.strip() != row.body:
        row.body = body.strip()
        changed = True
    if changed:
        row.version += 1
        row.updated_at = datetime.now(timezone.utc)
        if row.approval_status == "approved":
            row.approval_status = PENDING_REVIEW
    return row


def get_article(db: Session, tenant_id: str, article_id: int) -> KnowledgeArticle | None:
    return (
        db.query(KnowledgeArticle)
        .filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.id == article_id)
        .first()
    )


def record_view(db: Session, tenant_id: str, article_id: int) -> KnowledgeArticle | None:
    row = get_article(db, tenant_id, article_id)
    if row is None:
        return None
    row.view_count += 1
    return row


def article_to_dict(row: KnowledgeArticle) -> dict:
    return {
        "id": row.id, "category": row.category, "title": row.title, "body": row.body,
        "author": row.author, "reviewer": row.reviewer, "approval_status": row.approval_status,
        "version": row.version, "last_reviewed_at": row.last_reviewed_at.isoformat() if row.last_reviewed_at else None,
        "applicable_instruments": _load(row.applicable_instruments),
        "applicable_findings": _load(row.applicable_findings),
        "applicable_manufacturers": _load(row.applicable_manufacturers),
        "anatomy_zone": row.anatomy_zone, "procedure": row.procedure, "specialty": row.specialty,
        "common_mistake": row.common_mistake, "prevention_tip": row.prevention_tip, "references": row.references,
        "source_inspection_id": row.source_inspection_id, "view_count": row.view_count,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_articles(
    db: Session, tenant_id: str, *, category: str = "", instrument: str = "", manufacturer: str = "",
    anatomy_zone: str = "", finding: str = "", procedure: str = "", specialty: str = "",
    approval_status: str = "", include_archived: bool = False,
) -> list[dict]:
    """Deliverable 1 — faceted institutional-knowledge search."""
    q = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id)
    if category:
        q = q.filter(KnowledgeArticle.category == category)
    if approval_status:
        q = q.filter(KnowledgeArticle.approval_status == approval_status)
    if anatomy_zone:
        q = q.filter(KnowledgeArticle.anatomy_zone == anatomy_zone)
    if procedure:
        q = q.filter(KnowledgeArticle.procedure.ilike(f"%{procedure}%"))
    if specialty:
        q = q.filter(KnowledgeArticle.specialty == specialty)
    rows = q.order_by(KnowledgeArticle.id.desc()).all()

    if not include_archived:
        rows = [r for r in rows if r.approval_status != "archived"]

    results = [article_to_dict(r) for r in rows]

    if instrument:
        needle = instrument.strip().lower()
        results = [r for r in results if any(needle in i.lower() for i in r["applicable_instruments"])]
    if manufacturer:
        needle = manufacturer.strip().lower()
        results = [r for r in results if any(needle in m.lower() for m in r["applicable_manufacturers"])]
    if finding:
        needle = finding.strip().lower()
        results = [r for r in results if any(needle in f.lower() for f in r["applicable_findings"])]

    return results
