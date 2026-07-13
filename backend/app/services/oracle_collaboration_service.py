"""Project Oracle, Section 12: Research Collaboration.

Co-researcher reassignment and discussion comments -- both are auditable
events, recorded via the same `OracleStageTransition` trail the validation
pipeline uses (with `from_stage == to_stage`, mirroring how Steward records
non-status-changing events like owner assignment) so a hypothesis's full
collaboration history stays in one place alongside its pipeline history.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.oracle_discovery import OracleHypothesis, OracleStageTransition
from app.services import oracle_hypothesis_service


def reassign_research_owner(
    db: Session, tenant_id: str, hypothesis_id: int, *, new_owner: str, changed_by: str, changed_by_role: str,
) -> OracleHypothesis:
    row = oracle_hypothesis_service.get_hypothesis(db, tenant_id, hypothesis_id)
    if row is None:
        raise ValueError("Hypothesis not found")
    if not new_owner.strip():
        raise ValueError("A research owner reassignment requires a non-empty owner.")
    previous_owner = row.research_owner
    row.research_owner = new_owner
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    db.add(OracleStageTransition(
        tenant_id=tenant_id, hypothesis_id=row.id, from_stage=row.current_stage, to_stage=row.current_stage,
        changed_by=changed_by, changed_by_role=changed_by_role,
        reason=f"Research owner reassigned from '{previous_owner}' to '{new_owner}'.",
    ))
    db.commit()
    return row


def add_discussion_comment(
    db: Session, tenant_id: str, hypothesis_id: int, *, comment: str, submitted_by: str,
) -> OracleHypothesis:
    """A collaboration comment is stored as append-only evidence -- it
    never edits or removes a prior comment or evidence entry."""
    return oracle_hypothesis_service.add_evidence(
        db, tenant_id, hypothesis_id, evidence_summary=comment, submitted_by=submitted_by,
        evidence_type="discussion_comment",
    )
