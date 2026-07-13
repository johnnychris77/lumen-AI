"""Project Oracle, Section 6: Knowledge Evolution.

A promoted `OracleKnowledgeSuggestion` never writes `KnowledgeArticle`
directly. It first creates a `GovernanceApproval` row (the same generic
governance-approval table Steward and the pre-existing
`app/routes/governance_approvals.py` use) with the modern 4-role RBAC
(never the legacy `"tenant_admin"`/`"site_admin"` roles that one
pre-existing route uses). Only once that `GovernanceApproval` is granted
does this module create the real `KnowledgeArticle` -- as a
`pending_review` draft, so it still flows through the existing
`knowledge_governance_service` editorial-review workflow rather than
Oracle bypassing it.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.knowledge import ARTICLE_CATEGORIES, PENDING_REVIEW
from app.models.oracle_discovery import (
    ROLE_AUTHORITY_TIER,
    SUGGESTION_APPROVED,
    SUGGESTION_PENDING,
    SUGGESTION_PUBLISHED,
    SUGGESTION_REJECTED,
    TIER_APPROVE_KNOWLEDGE_SUGGESTION,
    OracleKnowledgeSuggestion,
)
from app.services import knowledge_repository_service

REQUEST_TYPE_KNOWLEDGE_EVOLUTION = "oracle_knowledge_evolution"


def to_dict(row: OracleKnowledgeSuggestion) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "hypothesis_id": row.hypothesis_id,
        "suggested_article_title": row.suggested_article_title,
        "suggested_article_body": row.suggested_article_body,
        "rationale": row.rationale,
        "governance_approval_id": row.governance_approval_id,
        "knowledge_article_id": row.knowledge_article_id,
        "status": row.status,
        "submitted_by": row.submitted_by,
    }


def create_suggestion(
    db: Session, tenant_id: str, tenant_name: str, *, hypothesis_id: int | None, suggested_article_title: str,
    suggested_article_body: str, rationale: str, submitted_by: str,
) -> OracleKnowledgeSuggestion:
    if not suggested_article_title.strip() or not suggested_article_body.strip():
        raise ValueError("A knowledge suggestion requires both a title and a body.")

    row = OracleKnowledgeSuggestion(
        tenant_id=tenant_id, hypothesis_id=hypothesis_id, suggested_article_title=suggested_article_title.strip(),
        suggested_article_body=suggested_article_body.strip(), rationale=rationale, submitted_by=submitted_by,
        status=SUGGESTION_PENDING,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    approval = models.GovernanceApproval(
        tenant_id=tenant_id, tenant_name=tenant_name, request_type=REQUEST_TYPE_KNOWLEDGE_EVOLUTION,
        target_resource="oracle_knowledge_suggestion", target_resource_id=str(row.id), requested_by=submitted_by,
        requested_payload=json.dumps({
            "title": suggested_article_title, "rationale": rationale, "hypothesis_id": hypothesis_id,
        })[:4000],
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    row.governance_approval_id = approval.id
    db.commit()
    db.refresh(row)
    return row


def list_suggestions(db: Session, tenant_id: str, *, status: str = "", hypothesis_id: int | None = None) -> list[dict]:
    q = db.query(OracleKnowledgeSuggestion).filter(OracleKnowledgeSuggestion.tenant_id == tenant_id)
    if status:
        q = q.filter(OracleKnowledgeSuggestion.status == status)
    if hypothesis_id is not None:
        q = q.filter(OracleKnowledgeSuggestion.hypothesis_id == hypothesis_id)
    return [to_dict(r) for r in q.order_by(OracleKnowledgeSuggestion.created_at.desc()).all()]


def approve_suggestion(
    db: Session, tenant_id: str, suggestion_id: int, *, reviewer: str, reviewer_role: str, article_category: str,
) -> OracleKnowledgeSuggestion:
    """Requires manager-tier-or-above authorization (Section 27's
    convention). Creates the real `KnowledgeArticle` as `pending_review` --
    it still needs a knowledge editor's separate review before it is
    `approved`, exactly as any other article does."""
    if ROLE_AUTHORITY_TIER.get(reviewer_role, 0) < TIER_APPROVE_KNOWLEDGE_SUGGESTION:
        raise ValueError(
            f"Role '{reviewer_role}' is not authorized to approve a knowledge suggestion; requires "
            f"tier {TIER_APPROVE_KNOWLEDGE_SUGGESTION} or higher."
        )
    if article_category not in ARTICLE_CATEGORIES:
        raise ValueError(f"Unknown article category: {article_category}")

    row = db.query(OracleKnowledgeSuggestion).filter(
        OracleKnowledgeSuggestion.tenant_id == tenant_id, OracleKnowledgeSuggestion.id == suggestion_id,
    ).first()
    if row is None:
        raise ValueError("Knowledge suggestion not found")
    if row.status != SUGGESTION_PENDING:
        raise ValueError(f"Only a pending suggestion can be approved; this one is {row.status}.")

    article = knowledge_repository_service.create_article(
        db, tenant_id=tenant_id, category=article_category, title=row.suggested_article_title,
        body=row.suggested_article_body, author="oracle", approval_status=PENDING_REVIEW,
    )
    db.commit()
    db.refresh(article)

    if row.governance_approval_id:
        approval = db.query(models.GovernanceApproval).filter(models.GovernanceApproval.id == row.governance_approval_id).first()
        if approval is not None:
            approval.status = "approved"
            approval.reviewed_by = reviewer
            approval.reviewed_at = datetime.now(timezone.utc)

    row.status = SUGGESTION_APPROVED
    row.knowledge_article_id = article.id
    db.commit()
    db.refresh(row)
    return row


def reject_suggestion(
    db: Session, tenant_id: str, suggestion_id: int, *, reviewer: str, reviewer_role: str, reason: str,
) -> OracleKnowledgeSuggestion:
    if ROLE_AUTHORITY_TIER.get(reviewer_role, 0) < TIER_APPROVE_KNOWLEDGE_SUGGESTION:
        raise ValueError(
            f"Role '{reviewer_role}' is not authorized to reject a knowledge suggestion; requires "
            f"tier {TIER_APPROVE_KNOWLEDGE_SUGGESTION} or higher."
        )
    row = db.query(OracleKnowledgeSuggestion).filter(
        OracleKnowledgeSuggestion.tenant_id == tenant_id, OracleKnowledgeSuggestion.id == suggestion_id,
    ).first()
    if row is None:
        raise ValueError("Knowledge suggestion not found")
    if row.status != SUGGESTION_PENDING:
        raise ValueError(f"Only a pending suggestion can be rejected; this one is {row.status}.")

    if row.governance_approval_id:
        approval = db.query(models.GovernanceApproval).filter(models.GovernanceApproval.id == row.governance_approval_id).first()
        if approval is not None:
            approval.status = "rejected"
            approval.reviewed_by = reviewer
            approval.review_notes = reason
            approval.reviewed_at = datetime.now(timezone.utc)

    row.status = SUGGESTION_REJECTED
    db.commit()
    db.refresh(row)
    return row


def mark_published(db: Session, tenant_id: str, suggestion_id: int) -> OracleKnowledgeSuggestion:
    """Called once the linked `KnowledgeArticle` completes the existing
    editorial review and reaches `approval_status="approved"` -- Oracle
    only observes that transition, it never sets `approval_status` itself."""
    row = db.query(OracleKnowledgeSuggestion).filter(
        OracleKnowledgeSuggestion.tenant_id == tenant_id, OracleKnowledgeSuggestion.id == suggestion_id,
    ).first()
    if row is None:
        raise ValueError("Knowledge suggestion not found")
    if row.status != SUGGESTION_APPROVED or not row.knowledge_article_id:
        raise ValueError("Only an approved suggestion with a linked knowledge article can be marked published.")
    article = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.id == row.knowledge_article_id).first()
    if article is None or article.approval_status != "approved":
        raise ValueError("The linked knowledge article has not yet completed editorial review.")
    row.status = SUGGESTION_PUBLISHED
    db.commit()
    db.refresh(row)
    return row
