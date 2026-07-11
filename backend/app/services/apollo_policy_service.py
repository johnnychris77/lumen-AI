"""v4.7 — Project Apollo, Section 6: Policy Intelligence.

Versioned quality policies — `QualityPolicy` (genuinely new; no clinical
policy versioning system existed before Apollo). Follows the same
`supersedes_id`/`status` self-FK chain Beacon's `StandardsPublication` and
Forge's `WorkflowDefinition` already established, including the same
version-chain walk pattern as `beacon_standards_service.version_history`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.apollo_quality import (
    DISCLAIMER,
    POLICY_DRAFT,
    POLICY_PUBLISHED,
    POLICY_SUPERSEDED,
    QualityPolicy,
)


class PolicyNotFoundError(Exception):
    pass


def _to_dict(policy: QualityPolicy) -> dict:
    return {
        "id": policy.id,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "tenant_id": policy.tenant_id,
        "title": policy.title,
        "version": policy.version,
        "status": policy.status,
        "supersedes_id": policy.supersedes_id,
        "owner": policy.owner,
        "review_date": policy.review_date.isoformat() if policy.review_date else None,
        "content": policy.content,
        "references": json.loads(policy.references_json or "[]"),
        "linked_standards": json.loads(policy.linked_standards_json or "[]"),
        "affected_workflows": json.loads(policy.affected_workflows_json or "[]"),
        "affected_competencies": json.loads(policy.affected_competencies_json or "[]"),
        "affected_ai_rules": json.loads(policy.affected_ai_rules_json or "[]"),
        "published_by": policy.published_by,
        "published_at": policy.published_at.isoformat() if policy.published_at else None,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def create_policy(
    db: Session, tenant_id: str, *, title: str, owner: str = "", review_date=None, content: str = "",
    references: list | None = None, linked_standards: list | None = None, affected_workflows: list | None = None,
    affected_competencies: list | None = None, affected_ai_rules: list | None = None,
    supersedes_id: int | None = None,
) -> dict:
    version = 1
    if supersedes_id is not None:
        prior = db.query(QualityPolicy).filter(
            QualityPolicy.id == supersedes_id, QualityPolicy.tenant_id == tenant_id,
        ).first()
        if prior is None:
            raise PolicyNotFoundError(f"Policy {supersedes_id} not found for tenant {tenant_id} to supersede.")
        version = prior.version + 1

    policy = QualityPolicy(
        tenant_id=tenant_id, title=title, version=version, status=POLICY_DRAFT, supersedes_id=supersedes_id,
        owner=owner, review_date=review_date, content=content,
        references_json=json.dumps(references or []), linked_standards_json=json.dumps(linked_standards or []),
        affected_workflows_json=json.dumps(affected_workflows or []),
        affected_competencies_json=json.dumps(affected_competencies or []),
        affected_ai_rules_json=json.dumps(affected_ai_rules or []),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return _to_dict(policy)


def get_policy(db: Session, tenant_id: str, policy_id: int) -> dict:
    policy = db.query(QualityPolicy).filter(
        QualityPolicy.id == policy_id, QualityPolicy.tenant_id == tenant_id,
    ).first()
    if policy is None:
        raise PolicyNotFoundError(f"Policy {policy_id} not found for tenant {tenant_id}.")
    return _to_dict(policy)


def list_policies(db: Session, tenant_id: str, *, status: str = "") -> list[dict]:
    q = db.query(QualityPolicy).filter(QualityPolicy.tenant_id == tenant_id)
    if status:
        q = q.filter(QualityPolicy.status == status)
    rows = q.order_by(QualityPolicy.created_at.desc()).all()
    return [_to_dict(r) for r in rows]


def publish_policy(db: Session, tenant_id: str, policy_id: int, *, published_by: str) -> dict:
    policy = db.query(QualityPolicy).filter(
        QualityPolicy.id == policy_id, QualityPolicy.tenant_id == tenant_id,
    ).first()
    if policy is None:
        raise PolicyNotFoundError(f"Policy {policy_id} not found for tenant {tenant_id}.")
    if policy.supersedes_id is not None:
        prior = db.query(QualityPolicy).filter(QualityPolicy.id == policy.supersedes_id).first()
        if prior is not None and prior.status == POLICY_PUBLISHED:
            prior.status = POLICY_SUPERSEDED
    policy.status = POLICY_PUBLISHED
    policy.published_by = published_by
    policy.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return _to_dict(policy)


def version_history(db: Session, tenant_id: str, policy_id: int) -> list[dict]:
    """Walks the `supersedes_id` chain to the root, then returns every
    version in order — mirrors Beacon's `version_history` walk."""
    row = db.query(QualityPolicy).filter(
        QualityPolicy.id == policy_id, QualityPolicy.tenant_id == tenant_id,
    ).first()
    if row is None:
        return []

    root_id = row.id
    seen = set()
    while True:
        current = db.query(QualityPolicy).filter(QualityPolicy.id == root_id).first()
        if current is None or not current.supersedes_id or current.supersedes_id in seen:
            break
        seen.add(current.supersedes_id)
        root_id = current.supersedes_id

    chain = []
    current_id = root_id
    visited = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        current = db.query(QualityPolicy).filter(QualityPolicy.id == current_id).first()
        if current is None:
            break
        chain.append(_to_dict(current))
        successor = db.query(QualityPolicy).filter(QualityPolicy.supersedes_id == current_id).first()
        current_id = successor.id if successor else None
    return chain


def policies_due_for_review(db: Session, tenant_id: str, *, within_days: int = 30) -> list[dict]:
    """Published policies whose `review_date` is within the window (or
    already past) — the basis for the Executive Quality Dashboard's
    "high-risk policies"/"upcoming reviews" tiles."""
    cutoff = datetime.now(timezone.utc) + timedelta(days=within_days)
    rows = (
        db.query(QualityPolicy)
        .filter(
            QualityPolicy.tenant_id == tenant_id, QualityPolicy.status == POLICY_PUBLISHED,
            QualityPolicy.review_date.isnot(None), QualityPolicy.review_date <= cutoff,
        )
        .order_by(QualityPolicy.review_date.asc())
        .all()
    )
    return [_to_dict(r) for r in rows]
