"""Project Steward, Section 9 & 19: Verification of Implementation, with
Veritas integration.

A checkbox alone is not sufficient evidence for a high-risk action: for
GovernedAction rows at `risk_level` high/critical, `sufficient` can only
become True when a real Veritas evidence assessment supports it (a
"strong_evidence" or "moderate_evidence" readiness category with no open
limitations) -- a caller-supplied `sufficient=True` with no
`inspection_id` is silently overridden to False and explained in
`insufficiency_reason`. Standard-risk actions may record evidence
sufficiency directly, since Steward is not the clinical evidence
authority for actions Veritas has no assessment for.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import GovernedActionVerification
from app.services import steward_action_service

_SUFFICIENT_READINESS_CATEGORIES = {"strong_evidence", "moderate_evidence"}


def to_dict(row: GovernedActionVerification) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "governed_action_id": row.governed_action_id,
        "evidence_type": row.evidence_type,
        "evidence_description": row.evidence_description,
        "verified_by": row.verified_by,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "sufficient": row.sufficient,
        "insufficiency_reason": row.insufficiency_reason,
    }


def check_veritas_evidence_sufficiency(db: Session, tenant_id: str, inspection_id: int) -> dict:
    """Section 19: Veritas may return evidence complete / limited /
    conflicting / additional evidence required."""
    from app.services.veritas_evidence_agent_service import run_evidence_assessment, to_dict as veritas_to_dict

    try:
        row = run_evidence_assessment(db, tenant_id, inspection_id)
    except ValueError as exc:
        return {"sufficient": False, "reason": str(exc), "readiness_category": "insufficient_evidence"}
    result = veritas_to_dict(row)
    sufficient = result["readiness_category"] in _SUFFICIENT_READINESS_CATEGORIES and not result["limitations"]
    reason = "" if sufficient else (
        f"Veritas evidence readiness is {result['readiness_category']}"
        + (f"; limitations: {'; '.join(result['limitations'])}" if result["limitations"] else "")
    )
    return {"sufficient": sufficient, "reason": reason, "readiness_category": result["readiness_category"]}


def record_verification(
    db: Session, tenant_id: str, action_id: int, *, evidence_type: str, evidence_description: str = "",
    verified_by: str = "", sufficient: bool | None = None, inspection_id: int | None = None,
) -> GovernedActionVerification:
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")

    is_high_risk = action.risk_level in ("high", "critical")
    insufficiency_reason = ""
    resolved_sufficient = bool(sufficient)

    if is_high_risk:
        if inspection_id is not None:
            veritas_result = check_veritas_evidence_sufficiency(db, tenant_id, inspection_id)
            resolved_sufficient = veritas_result["sufficient"]
            insufficiency_reason = veritas_result["reason"]
        else:
            resolved_sufficient = False
            insufficiency_reason = (
                "High-risk actions require a Veritas evidence assessment (inspection_id) -- "
                "a self-declared checkbox alone is not sufficient evidence."
            )

    row = GovernedActionVerification(
        tenant_id=tenant_id, governed_action_id=action_id, evidence_type=evidence_type,
        evidence_description=evidence_description, verified_by=verified_by,
        verified_at=datetime.now(timezone.utc) if verified_by else None,
        sufficient=resolved_sufficient, insufficiency_reason=insufficiency_reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_verifications(db: Session, tenant_id: str, action_id: int) -> list[dict]:
    rows = (
        db.query(GovernedActionVerification)
        .filter(GovernedActionVerification.tenant_id == tenant_id, GovernedActionVerification.governed_action_id == action_id)
        .order_by(GovernedActionVerification.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]


def has_sufficient_evidence(db: Session, tenant_id: str, action_id: int) -> bool:
    """Section 9/24: whether every recorded verification for this action
    is sufficient (and at least one exists)."""
    rows = list_verifications(db, tenant_id, action_id)
    return bool(rows) and all(r["sufficient"] for r in rows)
