"""v1.8 — Competency Knowledge Library (Deliverable 7).

Organizes competency knowledge by instrument family / anatomy / finding /
risk / inspection technique / cleaning consideration / corrective action —
merging the existing static education_library.py reference (definition,
clinical importance, inspection tips, cleaning considerations, corrective
actions) with any approved institutional KnowledgeArticle entries tagged to
the same finding type, so supervisor-contributed guidance sits alongside
the baseline reference rather than being a second, disconnected list.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import education_library
from app.services.knowledge_repository_service import list_articles


def competency_topic(db: Session, tenant_id: str, finding_type: str) -> dict | None:
    base = education_library.get_article(finding_type)
    if base is None:
        return None
    institutional = list_articles(
        db, tenant_id, finding=finding_type, approval_status="approved",
    )
    return {**base, "institutional_knowledge": institutional}


def list_competency_topics(db: Session, tenant_id: str) -> list[dict]:
    return [
        competency_topic(db, tenant_id, category)
        for category in education_library.CATEGORIES
    ]
