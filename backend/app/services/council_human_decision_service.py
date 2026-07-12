"""Project Council, Section 8: Human Decision Authority.

Enforces the brief's five-tier approval scale (technician / supervisor /
spd_manager / director / clinical_quality_governance) on top of
LumenAI's actual four-role RBAC, via `ROLE_AUTHORITY_TIER`. A technician
(mapped from `viewer`/`operator`) can view a Council recommendation but
can never finalize a decision -- `finalize_decision` raises
`PermissionError` if the deciding user's role tier is below the case's
`required_approval_tier`.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.council_leadership import CASE_STATUS_RESOLVED, ROLE_AUTHORITY_TIER, CouncilCase, CouncilHumanDecision


def can_approve(role: str, required_tier: int) -> bool:
    return ROLE_AUTHORITY_TIER.get(role, 0) >= required_tier


def to_dict(row: CouncilHumanDecision) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "council_case_id": row.council_case_id,
        "approver": row.approver,
        "approver_role": row.approver_role,
        "decision": row.decision,
        "rationale": row.rationale,
        "conditions": row.conditions,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
    }


def finalize_decision(
    db: Session, tenant_id: str, council_case_id: int, *, approver: str, approver_role: str, decision: str,
    rationale: str = "", conditions: str = "",
) -> CouncilHumanDecision:
    case = (
        db.query(CouncilCase)
        .filter(CouncilCase.tenant_id == tenant_id, CouncilCase.id == council_case_id)
        .first()
    )
    if case is None:
        raise ValueError(f"Council Case {council_case_id} not found for this tenant")
    if not decision.strip():
        raise ValueError("decision is required for an auditable Council decision")
    if not can_approve(approver_role, case.required_approval_tier):
        raise PermissionError(
            f"Role '{approver_role}' does not have sufficient authority to finalize this Council Case "
            f"(requires '{case.required_human_approver}' or higher).",
        )

    row = CouncilHumanDecision(
        tenant_id=tenant_id,
        council_case_id=council_case_id,
        approver=approver,
        approver_role=approver_role,
        decision=decision,
        rationale=rationale,
        conditions=conditions,
    )
    db.add(row)
    case.status = CASE_STATUS_RESOLVED
    db.commit()
    db.refresh(row)
    return row


def decisions_for_case(db: Session, tenant_id: str, council_case_id: int) -> list[dict]:
    rows = (
        db.query(CouncilHumanDecision)
        .filter(CouncilHumanDecision.tenant_id == tenant_id, CouncilHumanDecision.council_case_id == council_case_id)
        .order_by(CouncilHumanDecision.decided_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
