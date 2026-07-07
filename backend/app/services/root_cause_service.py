"""v1.5 — Root Cause Intelligence (Deliverable 7).

Findings are categorized by probable root cause only by a human (a
supervisor) — never inferred automatically, since guessing "why" a finding
occurred without a human judgment call would be a fabricated causal claim.
This module records that categorization and trends recurring causes.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.root_cause import ROOT_CAUSES, RootCauseAssignment


def assign_root_cause(
    db: Session, *, tenant_id: str, inspection_id: int, finding_type: str,
    root_cause: str, assigned_by: str,
) -> RootCauseAssignment:
    if root_cause not in ROOT_CAUSES:
        raise ValueError(f"root_cause must be one of {ROOT_CAUSES}")
    assignment = RootCauseAssignment(
        tenant_id=tenant_id,
        inspection_id=inspection_id,
        finding_type=finding_type,
        root_cause=root_cause,
        assigned_by=assigned_by,
    )
    db.add(assignment)
    return assignment


def root_cause_trends(db: Session, tenant_id: str) -> dict:
    """Recurring root causes, overall and per finding type."""
    rows = (
        db.query(RootCauseAssignment)
        .filter(RootCauseAssignment.tenant_id == tenant_id)
        .all()
    )

    overall: dict[str, int] = defaultdict(int)
    by_finding_type: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        overall[r.root_cause] += 1
        by_finding_type[r.finding_type][r.root_cause] += 1

    return {
        "total_assignments": len(rows),
        "overall": dict(sorted(overall.items(), key=lambda kv: kv[1], reverse=True)),
        "by_finding_type": {ft: dict(counts) for ft, counts in by_finding_type.items()},
        "human_review_required": True,
    }
