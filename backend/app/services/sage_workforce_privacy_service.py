"""Project Sage, Section 16: Workforce Privacy and Fairness.

Sage must not: rank employees publicly, assign disciplinary action, infer
protected characteristics, use unvalidated AI findings for performance
action, expose individual performance to unauthorized users, or make
employment decisions. This module provides the access-control predicate
routes call before returning individual-level data, plus an access-log
helper that reuses the platform's existing hash-chained, tamper-evident
audit trail (`enterprise_audit_service.record_enterprise_audit_event`)
rather than a new, weaker log table.
"""
from __future__ import annotations

from app.services.enterprise_audit_service import record_enterprise_audit_event

# Roles authorized to view any individual technician's competency/learning
# data (educators/supervisors/admins) -- "operator" and "viewer" may only
# ever see their own data (enforced by identity match below), never a peer's.
_INDIVIDUAL_DATA_ROLES = ("admin", "spd_manager")

PROHIBITED_ACTIONS = (
    "public_employee_ranking",
    "disciplinary_action",
    "protected_characteristic_inference",
    "unvalidated_ai_performance_action",
    "unauthorized_individual_exposure",
    "employment_decision",
)


class UnauthorizedIndividualAccessError(PermissionError):
    pass


def can_view_individual_competency(role: str, viewer_identity: str, subject_identity: str) -> bool:
    """True if `viewer_identity` may see `subject_identity`'s individual
    competency/learning data -- either they are the same person (self-view,
    Section 11) or the viewer holds an authorized leadership/educator role."""
    if viewer_identity == subject_identity:
        return True
    return role in _INDIVIDUAL_DATA_ROLES


def assert_can_view_individual(role: str, viewer_identity: str, subject_identity: str) -> None:
    if not can_view_individual_competency(role, viewer_identity, subject_identity):
        raise UnauthorizedIndividualAccessError(
            f"'{viewer_identity}' (role={role}) is not authorized to view {subject_identity}'s individual competency data"
        )


def log_individual_access(db, tenant_id: str, *, viewer: str, viewer_role: str, subject: str, resource_type: str) -> None:
    """Section 16/17 access log -- routed through the platform's existing
    tamper-evident audit trail rather than a separate, weaker log."""
    record_enterprise_audit_event(
        db, action_type="sage_individual_competency_access", resource_type=resource_type,
        resource_id=subject, actor=viewer, actor_role=viewer_role, tenant_id=tenant_id,
    )
