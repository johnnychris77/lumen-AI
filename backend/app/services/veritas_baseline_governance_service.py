"""Project Veritas, Sections 3 & 13: Baseline Governance Rules + Baseline
Review Workspace.

`VeritasBaselineGovernanceAction` is append-only -- a baseline's effective
canonical status is the `resulting_status` of its latest action row, never a
mutation of the real `BaselineLibraryEntry`/`EnterpriseVendorBaselineSubscription`
tables those actions govern. Every action IS its own audit event by
construction (a new row, never edited or deleted).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.veritas_evidence import (
    BASELINE_STATUS_PENDING_REVIEW,
    BASELINE_STATUSES_USABLE_FOR_SCORING,
    GOVERNANCE_ACTIONS,
    VeritasBaselineGovernanceAction,
    status_for_action,
)


def record_governance_action(
    db: Session, tenant_id: str, *, baseline_source_type: str, baseline_source_id: int, action: str,
    performed_by: str, performed_role: str = "", owner: str = "", review_date=None,
    known_limitations: str = "", usage_rights: str = "", rationale: str = "",
) -> VeritasBaselineGovernanceAction:
    if action not in GOVERNANCE_ACTIONS:
        raise ValueError(f"Unknown governance action '{action}'")
    row = VeritasBaselineGovernanceAction(
        tenant_id=tenant_id, baseline_source_type=baseline_source_type, baseline_source_id=baseline_source_id,
        action=action, resulting_status=status_for_action(action), owner=owner, review_date=review_date,
        known_limitations=known_limitations, usage_rights=usage_rights, rationale=rationale,
        performed_by=performed_by, performed_role=performed_role,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _to_dict(row: VeritasBaselineGovernanceAction) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "baseline_source_type": row.baseline_source_type,
        "baseline_source_id": row.baseline_source_id,
        "action": row.action,
        "resulting_status": row.resulting_status,
        "owner": row.owner,
        "review_date": row.review_date.isoformat() if row.review_date else None,
        "known_limitations": row.known_limitations,
        "usage_rights": row.usage_rights,
        "rationale": row.rationale,
        "performed_by": row.performed_by,
        "performed_role": row.performed_role,
    }


def governance_history(db: Session, tenant_id: str, baseline_source_type: str, baseline_source_id: int) -> list[dict]:
    rows = (
        db.query(VeritasBaselineGovernanceAction)
        .filter(
            VeritasBaselineGovernanceAction.tenant_id == tenant_id,
            VeritasBaselineGovernanceAction.baseline_source_type == baseline_source_type,
            VeritasBaselineGovernanceAction.baseline_source_id == baseline_source_id,
        )
        .order_by(VeritasBaselineGovernanceAction.created_at.asc())
        .all()
    )
    return [_to_dict(r) for r in rows]


def effective_status(db: Session, tenant_id: str, baseline_source_type: str, baseline_source_id: int) -> str:
    """The canonical Veritas status for a real baseline -- the latest
    status-changing action, or `pending_review` if none has been recorded
    yet (Section 3's default lifecycle entry point)."""
    history = governance_history(db, tenant_id, baseline_source_type, baseline_source_id)
    for entry in reversed(history):
        if entry["resulting_status"]:
            return entry["resulting_status"]
    return BASELINE_STATUS_PENDING_REVIEW


def is_usable_for_scoring(status: str) -> bool:
    """Section 3: only approved or conditionally approved baselines may
    influence a clinical recommendation."""
    return status in BASELINE_STATUSES_USABLE_FOR_SCORING


def compare_candidates(db: Session, tenant_id: str, candidates: list[tuple[str, int]]) -> list[dict]:
    """Section 13: compare baseline candidates side by side, each identified
    by (baseline_source_type, baseline_source_id)."""
    return [
        {
            "baseline_source_type": source_type, "baseline_source_id": source_id,
            "effective_status": effective_status(db, tenant_id, source_type, source_id),
            "governance_history": governance_history(db, tenant_id, source_type, source_id),
        }
        for source_type, source_id in candidates
    ]
