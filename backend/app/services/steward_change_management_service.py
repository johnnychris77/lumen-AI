"""Project Steward, Sections 6 & 7: Dependency/Impact Analysis and Change
Management Plan.

Both are read-time analyses over a Governed Action's own stored fields
(dependencies, category, action type, risk level) -- neither is a
separately persisted table. Publication of a workflow/rule-changing
action is blocked until its dependencies have been reviewed at least
once (Section 6); this module also recommends a phased rollout (never
called "pilot" in code -- see `governed_action.py`'s naming
disambiguation) when enterprise-wide deployment would create avoidable
risk.
"""
from __future__ import annotations

from app.models.governed_action import (
    CATEGORY_GOVERNANCE,
    CHANGE_READINESS_STATES,
    ROLLOUT_ENTERPRISE,
    ROLLOUT_FACILITY,
)
from app.services import steward_action_service

_WORKFLOW_OR_RULE_CHANGING_TYPES = {
    "recleaning_workflow_revision", "supervisor_review_threshold_change", "workflow_redesign",
    "policy_revision", "rule_revision", "workflow_approval",
}

_CHANGE_STEPS = [
    "stakeholder_identification", "leadership_sponsorship", "communication", "readiness_assessment",
    "training", "pilot", "implementation", "reinforcement", "effectiveness_review", "sustainment",
]


def analyze_dependencies(db, tenant_id: str, action_id: int) -> dict:
    """Section 6: identify affected workflows/rules/policies, required
    education, integration dependencies, staffing impact, operational
    risk, possible disruption, rollback requirements, and data/reporting
    impact -- as a dependency graph the caller can display."""
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    data = steward_action_service.to_dict(action)
    is_workflow_or_rule_change = data["action_type"] in _WORKFLOW_OR_RULE_CHANGING_TYPES

    return {
        "governed_action_id": data["id"],
        "affected_workflows": [data["action_type"]] if is_workflow_or_rule_change else [],
        "affected_clinical_rules": [data["action_type"]] if data["category"] == "clinical_quality" and is_workflow_or_rule_change else [],
        "affected_policies": [data["action_type"]] if data["category"] == CATEGORY_GOVERNANCE else [],
        "required_education": data["category"] == "education" or bool(data["evidence_requirements"]),
        "integration_dependencies": data["dependencies"],
        "staffing_impact": data["category"] == "operational",
        "operational_risk": data["risk_level"],
        "possible_service_disruption": data["risk_level"] in ("high", "critical") and is_workflow_or_rule_change,
        "rollback_requirements": is_workflow_or_rule_change,
        "data_and_reporting_impact": is_workflow_or_rule_change,
        "requires_dependency_review_before_publication": is_workflow_or_rule_change,
    }


def assert_dependencies_reviewed_for_publication(db, tenant_id: str, action_id: int, *, reviewed: bool) -> None:
    """Section 6: do not permit publication of a workflow or rule change
    without reviewing its dependencies."""
    analysis = analyze_dependencies(db, tenant_id, action_id)
    if analysis["requires_dependency_review_before_publication"] and not reviewed:
        raise ValueError(
            "This action changes a workflow or clinical rule and cannot be published until its "
            "dependencies have been reviewed."
        )


def recommend_rollout_scope(db, tenant_id: str, action_id: int) -> str:
    """Section 7: Steward may recommend a phased rollout where
    enterprise-wide deployment would create avoidable risk."""
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    if action.risk_level in ("high", "critical"):
        return ROLLOUT_FACILITY
    return ROLLOUT_ENTERPRISE


def generate_change_management_plan(db, tenant_id: str, action_id: int) -> dict:
    """Section 7: configurable change-management steps plus a change-
    readiness classification."""
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    return {
        "governed_action_id": action.id,
        "steps": _CHANGE_STEPS,
        "change_readiness": action.change_readiness,
        "recommended_rollout_scope": recommend_rollout_scope(db, tenant_id, action_id),
    }


def set_change_readiness(db, tenant_id: str, action_id: int, *, change_readiness: str) -> dict:
    if change_readiness not in CHANGE_READINESS_STATES:
        raise ValueError(f"Unknown change readiness state: {change_readiness}")
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    action.change_readiness = change_readiness
    db.commit()
    db.refresh(action)
    return steward_action_service.to_dict(action)
