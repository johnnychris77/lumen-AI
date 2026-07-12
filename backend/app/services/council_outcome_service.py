"""Project Council, Section 14: Outcome Effectiveness Review.

Closes the learning loop by linking back to the original Council Case and
its recommendation. Council learns from outcomes (`knowledge_update_
recommended` is a signal, nothing more) but never automatically rewrites
a clinical rule -- that always remains a separate, human-triggered change
elsewhere in the platform.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.council_leadership import (
    OUTCOME_EFFECTIVE,
    OUTCOME_INEFFECTIVE,
    OUTCOME_INSUFFICIENT_FOLLOW_UP,
    OUTCOME_PARTIALLY_EFFECTIVE,
    OUTCOME_UNINTENDED_CONSEQUENCE,
    CouncilOutcomeReview,
)


def classify_outcome(
    *, issue_resolved: bool | None, recurred: bool | None = None, risk_decreased: bool | None = None,
    operational_performance_improved: bool | None = None, unintended_consequence: bool = False,
) -> str:
    if issue_resolved is None:
        return OUTCOME_INSUFFICIENT_FOLLOW_UP
    if unintended_consequence:
        return OUTCOME_UNINTENDED_CONSEQUENCE
    if issue_resolved and not recurred:
        return OUTCOME_EFFECTIVE
    if issue_resolved and recurred:
        return OUTCOME_PARTIALLY_EFFECTIVE
    if not issue_resolved and (risk_decreased or operational_performance_improved):
        return OUTCOME_PARTIALLY_EFFECTIVE
    return OUTCOME_INEFFECTIVE


def to_dict(row: CouncilOutcomeReview) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "council_case_id": row.council_case_id,
        "issue_resolved": row.issue_resolved,
        "recurred": row.recurred,
        "risk_decreased": row.risk_decreased,
        "operational_performance_improved": row.operational_performance_improved,
        "recommendation_followed": row.recommendation_followed,
        "dissent_valid": row.dissent_valid,
        "additional_evidence_changed_decision": row.additional_evidence_changed_decision,
        "knowledge_update_recommended": row.knowledge_update_recommended,
        "classification": row.classification,
        "notes": row.notes,
    }


def record_outcome_review(
    db: Session, tenant_id: str, council_case_id: int, *, issue_resolved: bool | None = None,
    recurred: bool | None = None, risk_decreased: bool | None = None,
    operational_performance_improved: bool | None = None, recommendation_followed: bool | None = None,
    dissent_valid: bool | None = None, additional_evidence_changed_decision: bool | None = None,
    unintended_consequence: bool = False, notes: str = "",
) -> CouncilOutcomeReview:
    classification = classify_outcome(
        issue_resolved=issue_resolved, recurred=recurred, risk_decreased=risk_decreased,
        operational_performance_improved=operational_performance_improved,
        unintended_consequence=unintended_consequence,
    )
    knowledge_update_recommended = classification in (OUTCOME_INEFFECTIVE, OUTCOME_UNINTENDED_CONSEQUENCE) or bool(dissent_valid)

    row = CouncilOutcomeReview(
        tenant_id=tenant_id,
        council_case_id=council_case_id,
        issue_resolved=issue_resolved,
        recurred=recurred,
        risk_decreased=risk_decreased,
        operational_performance_improved=operational_performance_improved,
        recommendation_followed=recommendation_followed,
        dissent_valid=dissent_valid,
        additional_evidence_changed_decision=additional_evidence_changed_decision,
        knowledge_update_recommended=knowledge_update_recommended,
        classification=classification,
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def outcome_reviews_for_case(db: Session, tenant_id: str, council_case_id: int) -> list[dict]:
    rows = (
        db.query(CouncilOutcomeReview)
        .filter(CouncilOutcomeReview.tenant_id == tenant_id, CouncilOutcomeReview.council_case_id == council_case_id)
        .order_by(CouncilOutcomeReview.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
