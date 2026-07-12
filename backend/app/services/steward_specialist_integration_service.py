"""Project Steward, Sections 16-18: Aegis, Vulcan, and Sage integrations.

Each function is a thin, read-only wrapper over that specialist's own
already-built service -- Steward never re-derives process variation,
reliability, or competency judgments itself.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import steward_action_service


def get_aegis_process_outcome(db: Session, tenant_id: str, instrument_identity: str) -> dict:
    """Section 16: Aegis measures whether process behavior changes after
    implementation. Its finding is returned as-is and stays separately
    traceable -- Steward never merges it into its own outcome-review
    record, only references it."""
    from app.services.vulcan_aegis_integration_service import compute_process_variation_signal

    return compute_process_variation_signal(db, tenant_id, instrument_identity)


def get_vulcan_reliability_outcome(db: Session, tenant_id: str, instrument_identity: str, *, instrument_type: str = "") -> dict:
    """Section 17: Vulcan evaluates reliability outcomes (e.g. whether
    repeat corrosion or repair recurrence changes after a reliability
    action)."""
    from app.services.vulcan_reliability_agent_service import run_reliability_assessment, to_dict

    row = run_reliability_assessment(db, tenant_id, instrument_identity, instrument_type=instrument_type)
    return to_dict(row)


def update_action_effectiveness_from_vulcan(
    db: Session, tenant_id: str, action_id: int, *, instrument_identity: str, instrument_type: str = "",
) -> dict:
    """Section 17: Vulcan repair outcome updates action effectiveness."""
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    result = get_vulcan_reliability_outcome(db, tenant_id, instrument_identity, instrument_type=instrument_type)
    action.actual_outcomes = (
        f"Vulcan reliability outcome: {result['reliability_category']} ({result['reliability_score']}/100), "
        f"recommended disposition: {result['recommended_disposition']}."
    )
    db.commit()
    db.refresh(action)
    return steward_action_service.to_dict(action)


def check_sage_training_dependency_satisfied(db: Session, tenant_id: str, learner_or_group: str) -> bool:
    """Section 18: Sage competency completion can satisfy a training
    dependency. Steward never independently determines competency -- it
    only reads Sage's own completion status."""
    from app.services.sage_learning_plan_service import list_plans

    if not learner_or_group:
        return False
    plans = list_plans(db, tenant_id, learner_or_group=learner_or_group, completion_status="completed")
    return bool(plans)
