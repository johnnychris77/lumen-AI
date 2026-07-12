"""Project Council, Section 9: Council Workspace (`/council`).

Composes the workspace dashboard entirely from already-persisted Council
tables -- active cases, urgent cases, cases awaiting evidence, cases
awaiting a human decision, safety dissent, split decisions, recently
resolved cases, outcome effectiveness, specialist participation, and
recurring decision themes.
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.models.council_leadership import (
    CASE_STATUS_AWAITING_DECISION,
    CASE_STATUS_AWAITING_EVIDENCE,
    CASE_STATUS_RESOLVED,
    CONSENSUS_SAFETY_DISSENT,
    CONSENSUS_SPLIT,
    CouncilCase,
    CouncilOutcomeReview,
    CouncilSpecialistAssessment,
)
from app.services.council_orchestration_service import to_dict as case_to_dict


def workspace_summary(db: Session, tenant_id: str) -> dict:
    cases = db.query(CouncilCase).filter(CouncilCase.tenant_id == tenant_id).order_by(CouncilCase.created_at.desc()).all()

    active_cases = [c for c in cases if c.status != CASE_STATUS_RESOLVED]
    urgent_cases = [c for c in active_cases if c.urgency == "urgent"]
    awaiting_evidence = [c for c in active_cases if c.status == CASE_STATUS_AWAITING_EVIDENCE]
    awaiting_decision = [c for c in active_cases if c.status == CASE_STATUS_AWAITING_DECISION]
    safety_dissent_cases = [c for c in active_cases if c.consensus_status == CONSENSUS_SAFETY_DISSENT]
    split_decision_cases = [c for c in active_cases if c.consensus_status == CONSENSUS_SPLIT]
    recently_resolved = [c for c in cases if c.status == CASE_STATUS_RESOLVED][:10]

    outcomes = db.query(CouncilOutcomeReview).filter(CouncilOutcomeReview.tenant_id == tenant_id).all()
    outcome_effectiveness = dict(Counter(o.classification for o in outcomes))

    assessment_rows = db.query(CouncilSpecialistAssessment).filter(CouncilSpecialistAssessment.tenant_id == tenant_id).all()
    specialist_participation = dict(Counter(a.specialist_key for a in assessment_rows))

    recurring_decision_themes = dict(Counter(c.case_type for c in cases).most_common(10))

    return {
        "active_case_count": len(active_cases),
        "active_cases": [case_to_dict(c) for c in active_cases],
        "urgent_cases": [case_to_dict(c) for c in urgent_cases],
        "awaiting_evidence": [case_to_dict(c) for c in awaiting_evidence],
        "awaiting_decision": [case_to_dict(c) for c in awaiting_decision],
        "safety_dissent_cases": [case_to_dict(c) for c in safety_dissent_cases],
        "split_decision_cases": [case_to_dict(c) for c in split_decision_cases],
        "recently_resolved": [case_to_dict(c) for c in recently_resolved],
        "outcome_effectiveness": outcome_effectiveness,
        "specialist_participation": specialist_participation,
        "recurring_decision_themes": recurring_decision_themes,
        "human_review_required": True,
    }
