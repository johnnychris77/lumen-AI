"""Project Steward, Section 4: Implementation Plan Generator.

Generates a draft plan directly from a Governed Action's own already-
validated fields plus deterministic, category-level defaults (never
LLM-generated or per-instance fabricated) for the parts the action
record doesn't itself carry a column for (affected workflows/roles,
communication plan, training requirements, rollback plan). Human
approval -- moving the action to APPROVED via `steward_action_service.
transition_status` -- is required before the plan is activated; this
module never changes an action's status itself.
"""
from __future__ import annotations

from app.models.governed_action import CATEGORY_CLINICAL_QUALITY, CATEGORY_EDUCATION, CATEGORY_GOVERNANCE, CATEGORY_OPERATIONAL, CATEGORY_RELIABILITY
from app.services import steward_action_service

_AFFECTED_ROLES_BY_CATEGORY = {
    CATEGORY_CLINICAL_QUALITY: ["technician", "supervisor", "spd_manager"],
    CATEGORY_OPERATIONAL: ["technician", "supervisor", "spd_manager"],
    CATEGORY_EDUCATION: ["technician", "supervisor", "education_lead"],
    CATEGORY_RELIABILITY: ["technician", "supervisor", "biomed", "spd_manager"],
    CATEGORY_GOVERNANCE: ["spd_manager", "director", "quality"],
}

_TRAINING_REQUIRED_CATEGORIES = {CATEGORY_CLINICAL_QUALITY, CATEGORY_EDUCATION, CATEGORY_RELIABILITY}

_REVERSIBLE_ACTION_TYPES = {
    "queue_priority_change", "workload_reassignment", "supervisor_review_threshold_change",
    "increased_inspection_frequency", "shift_based_education",
}


def _communication_plan_for(action: dict) -> list[str]:
    return [
        f"Notify {action['owner'] or 'the assigned owner'} and {action['accountable_leader'] or 'the accountable leader'} of the approved action.",
        "Brief affected stakeholders before implementation begins.",
        "Confirm change readiness with affected staff prior to go-live.",
    ]


def _rollback_plan_for(action: dict) -> str:
    if action["action_type"] in _REVERSIBLE_ACTION_TYPES:
        return "Revert the configuration/threshold/assignment change; no residual clinical exposure expected."
    if action["category"] == CATEGORY_GOVERNANCE:
        return "Revert to the prior approved policy/rule/workflow version pending director-tier authorization."
    return "Rollback plan must be defined by the owner and accountable leader before implementation begins for this action type."


def generate_draft_plan(db, tenant_id: str, action_id: int) -> dict:
    """Section 4: for each approved decision, generate a draft plan.
    Returns a plan dict; does not persist a separate row or change the
    action's status -- the action's own fields (updated via
    `steward_action_service`) remain the single source of truth."""
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    data = steward_action_service.to_dict(action)

    return {
        "governed_action_id": data["id"],
        "objective": data["action_title"],
        "rationale": data["source_decision"],
        "owner": data["owner"],
        "accountable_leader": data["accountable_leader"],
        "affected_workflows": [data["action_type"]],
        "affected_facilities": [data["facility_id"]] if data["facility_id"] else [],
        "affected_roles": _AFFECTED_ROLES_BY_CATEGORY.get(data["category"], []),
        "required_resources": data["stakeholders"],
        "milestones": data["milestones"],
        "due_date": data["due_date"],
        "evidence_required": data["evidence_requirements"],
        "success_metrics": data["success_metrics"],
        "communication_plan": _communication_plan_for(data),
        "training_requirements": data["category"] in _TRAINING_REQUIRED_CATEGORIES,
        "rollback_plan": _rollback_plan_for(data),
        "review_date": data["due_date"],
        "human_review_required": True,
        "activation_note": "Human approval (moving this action to APPROVED) is required before this plan is activated.",
    }
