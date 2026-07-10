"""v3.4 — Project Horizon, Section 3: Knowledge Contribution Workflow.

True cross-organization contribution — distinct from Atlas's
`atlas_knowledge_sharing_service.py`, which shares an already-approved
`KnowledgeArticle` only *within one health system's own facilities*
(`system_id`-scoped). This module shares validated content *across
unrelated organizations* (tenants with no Atlas relationship to each
other), so de-identification here means hiding the contributing
organization's identity from every other organization, not just
formatting a copy.

Every contribution requires approval (`PENDING_REVIEW` on submission,
never auto-published) and is versioned — a revision to an already-decided
contribution creates a new row and links the chain via
`supersedes_ref`/`superseded_by_ref` rather than mutating history.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.federated_horizon import (
    APPROVED,
    CONTRIBUTION_APPROVAL_STATES,
    CONTRIBUTION_TYPES,
    PENDING_REVIEW,
    REJECTED,
    KnowledgeContribution,
)


class UnknownContributionError(Exception):
    pass


class InvalidContributionStateError(Exception):
    pass


def _row_to_dict(obj, *, include_source_tenant: bool) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    if not include_source_tenant:
        result.pop("source_tenant_id", None)
    return result


def _new_ref() -> str:
    return f"KC-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:8].upper()}"


def submit_contribution(
    db: Session, source_tenant_id: str, *, contribution_type: str, category: str, title: str, body: str, submitted_by: str,
) -> dict:
    if contribution_type not in CONTRIBUTION_TYPES:
        raise ValueError(f"contribution_type must be one of {CONTRIBUTION_TYPES}")

    row = KnowledgeContribution(
        contribution_ref=_new_ref(), source_tenant_id=source_tenant_id, contribution_type=contribution_type,
        category=category, title=title, body=body, version=1, approval_status=PENDING_REVIEW, submitted_by=submitted_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row, include_source_tenant=True)


def _get_or_404(db: Session, contribution_id: int) -> KnowledgeContribution:
    row = db.query(KnowledgeContribution).filter(KnowledgeContribution.id == contribution_id).first()
    if row is None:
        raise UnknownContributionError(f"Contribution {contribution_id} not found.")
    return row


def approve_contribution(db: Session, contribution_id: int, *, approved_by: str) -> dict:
    row = _get_or_404(db, contribution_id)
    if row.approval_status != PENDING_REVIEW:
        raise InvalidContributionStateError(f"Contribution {contribution_id} is '{row.approval_status}', not pending review.")
    row.approval_status = APPROVED
    row.approved_by = approved_by
    row.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row, include_source_tenant=True)


def reject_contribution(db: Session, contribution_id: int, *, rejected_by: str, reason: str) -> dict:
    row = _get_or_404(db, contribution_id)
    if row.approval_status != PENDING_REVIEW:
        raise InvalidContributionStateError(f"Contribution {contribution_id} is '{row.approval_status}', not pending review.")
    row.approval_status = REJECTED
    row.approved_by = rejected_by
    row.approved_at = datetime.now(timezone.utc)
    row.rejection_reason = reason
    db.commit()
    db.refresh(row)
    return _row_to_dict(row, include_source_tenant=True)


def revise_contribution(db: Session, contribution_id: int, *, updated_by: str, title: str | None = None, body: str | None = None) -> dict:
    """Section 12 'knowledge versioning': only a decided (approved/rejected)
    contribution can be revised — a revision creates a new row (new
    version, new ref) and links the chain; it never edits history."""
    original = _get_or_404(db, contribution_id)
    if original.approval_status not in (APPROVED, REJECTED):
        raise InvalidContributionStateError(
            f"Contribution {contribution_id} is '{original.approval_status}' — only an approved or rejected "
            "contribution can be revised (a pending one should simply be edited before decision).",
        )

    new_row = KnowledgeContribution(
        contribution_ref=_new_ref(), source_tenant_id=original.source_tenant_id, contribution_type=original.contribution_type,
        category=original.category, title=title if title is not None else original.title,
        body=body if body is not None else original.body, version=original.version + 1,
        supersedes_ref=original.contribution_ref, approval_status=PENDING_REVIEW, submitted_by=updated_by,
    )
    original.superseded_by_ref = new_row.contribution_ref
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return _row_to_dict(new_row, include_source_tenant=True)


def list_contributions(
    db: Session, *, approval_status: str = "", contribution_type: str = "", requesting_tenant_id: str = "",
) -> list[dict]:
    """De-identified by default: `source_tenant_id` is included only when
    `requesting_tenant_id` matches the contribution's own source (an org
    can always see its own submissions) — never for any other org."""
    if approval_status and approval_status not in CONTRIBUTION_APPROVAL_STATES:
        raise ValueError(f"approval_status must be one of {CONTRIBUTION_APPROVAL_STATES}")

    q = db.query(KnowledgeContribution)
    if approval_status:
        q = q.filter(KnowledgeContribution.approval_status == approval_status)
    if contribution_type:
        q = q.filter(KnowledgeContribution.contribution_type == contribution_type)
    rows = q.order_by(KnowledgeContribution.id.desc()).all()
    return [_row_to_dict(r, include_source_tenant=(requesting_tenant_id == r.source_tenant_id)) for r in rows]


def get_version_history(db: Session, contribution_ref: str) -> list[dict]:
    """Walks the supersedes/superseded_by chain to the root, then returns
    every version in order — never exposing which org authored any of it."""
    row = db.query(KnowledgeContribution).filter(KnowledgeContribution.contribution_ref == contribution_ref).first()
    if row is None:
        raise UnknownContributionError(f"Contribution '{contribution_ref}' not found.")

    root_ref = row.contribution_ref
    seen_refs = set()
    while True:
        current = db.query(KnowledgeContribution).filter(KnowledgeContribution.contribution_ref == root_ref).first()
        if current is None or not current.supersedes_ref or current.supersedes_ref in seen_refs:
            break
        seen_refs.add(current.supersedes_ref)
        root_ref = current.supersedes_ref

    chain = []
    ref = root_ref
    visited = set()
    while ref and ref not in visited:
        visited.add(ref)
        current = db.query(KnowledgeContribution).filter(KnowledgeContribution.contribution_ref == ref).first()
        if current is None:
            break
        chain.append(_row_to_dict(current, include_source_tenant=False))
        ref = current.superseded_by_ref

    return chain
