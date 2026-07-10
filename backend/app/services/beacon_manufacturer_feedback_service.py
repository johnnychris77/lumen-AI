"""v3.5 — Project Beacon, Section 6: Manufacturer Feedback Loop.

Reuses Horizon's `horizon_contribution_service.py` / `KnowledgeContribution`
directly — already true cross-organization, de-identified (never exposes
`source_tenant_id` to another org), and approval-gated (`pending_review`
until a governance reviewer approves). Beacon adds no new contribution
table: the sprint's five feedback categories (emerging anatomy risks,
recurring corrosion patterns, failure modes, inspection observations,
educational opportunities) are represented using
`KnowledgeContribution`'s existing `contribution_type` buckets
(`anatomy_guidance`, `failure_pattern`, `educational_content`) plus its
free-text `category` field for the more specific label — the reuse path
established by `category` already being free-form rather than a new enum.

"Only governance-approved, de-identified intelligence is shared" —
`manufacturer_feed` below returns only `approval_status == APPROVED`
contributions, identical to Horizon's own de-identification guarantee.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.federated_horizon import (
    APPROVED,
    CONTRIBUTION_ANATOMY_GUIDANCE,
    CONTRIBUTION_EDUCATIONAL_CONTENT,
    CONTRIBUTION_FAILURE_PATTERN,
    DISCLAIMER,
)
from app.services import horizon_contribution_service

# Beacon-specific free-text categories layered onto Horizon's contribution_type buckets
CATEGORY_ANATOMY_RISK = "emerging_anatomy_risk"
CATEGORY_CORROSION_PATTERN = "recurring_corrosion_pattern"
CATEGORY_FAILURE_MODE = "failure_mode"
CATEGORY_INSPECTION_OBSERVATION = "inspection_observation"
CATEGORY_EDUCATIONAL_OPPORTUNITY = "educational_opportunity"

_CATEGORY_TO_CONTRIBUTION_TYPE = {
    CATEGORY_ANATOMY_RISK: CONTRIBUTION_ANATOMY_GUIDANCE,
    CATEGORY_CORROSION_PATTERN: CONTRIBUTION_FAILURE_PATTERN,
    CATEGORY_FAILURE_MODE: CONTRIBUTION_FAILURE_PATTERN,
    CATEGORY_INSPECTION_OBSERVATION: CONTRIBUTION_ANATOMY_GUIDANCE,
    CATEGORY_EDUCATIONAL_OPPORTUNITY: CONTRIBUTION_EDUCATIONAL_CONTENT,
}


def submit_feedback(db: Session, source_tenant_id: str, *, category: str, title: str, body: str, submitted_by: str) -> dict:
    if category not in _CATEGORY_TO_CONTRIBUTION_TYPE:
        raise ValueError(f"category must be one of {sorted(_CATEGORY_TO_CONTRIBUTION_TYPE)}")
    return horizon_contribution_service.submit_contribution(
        db, source_tenant_id, contribution_type=_CATEGORY_TO_CONTRIBUTION_TYPE[category],
        category=category, title=title, body=body, submitted_by=submitted_by,
    )


def manufacturer_feed(db: Session, *, category: str = "") -> dict:
    """Only governance-approved, de-identified feedback — never a pending
    or rejected submission, never the contributing organization's identity."""
    approved = horizon_contribution_service.list_contributions(db, approval_status=APPROVED)
    if category:
        approved = [c for c in approved if c.get("category") == category]
    return {
        "feedback": approved,
        "categories": sorted(_CATEGORY_TO_CONTRIBUTION_TYPE),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
