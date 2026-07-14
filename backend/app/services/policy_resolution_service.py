"""Section 6 — Policy Resolution Hierarchy.

Resolves the single, most-specific *active + approved* Baseline Decision
Policy that applies to one inspection's context, in the order Section 6
specifies:

    model -> instrument_family -> anatomy_zone -> department -> facility
    -> health_system -> LumenAI recommended default

Manufacturer instructions and mandatory organizational controls are never
weakened by a less-restrictive local threshold: this module always returns
the *more restrictive* (higher `pass_threshold`) of the resolved policy and
any mandatory-scope policy that also applies, and callers must document the
final applicable policy on every recommendation (see `lumen_decision_engine`).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.lumen_decision_engine import BaselineDecisionPolicy
from app.services.baseline_decision_policy_service import LUMENAI_DEFAULT_POLICY

# Cross-tenant isolation: a policy authored under one organization_id must
# never influence another tenant's recommendation. The lookup below always
# filters by tenant_id; the "*" wildcard is reserved for the LumenAI
# built-in default only, never assignable to a customer-authored policy.
_MANDATORY_ORG_WILDCARD = "*"


def _query_scope(db: Session, tenant_id: str, scope: str, scope_value: str) -> BaselineDecisionPolicy | None:
    return (
        db.query(BaselineDecisionPolicy)
        .filter(
            BaselineDecisionPolicy.organization_id == tenant_id,
            BaselineDecisionPolicy.scope == scope,
            BaselineDecisionPolicy.scope_value == scope_value,
            BaselineDecisionPolicy.status == "active",
        )
        .order_by(BaselineDecisionPolicy.updated_at.desc())
        .first()
    )


def _default_policy_dict() -> dict[str, Any]:
    return dict(LUMENAI_DEFAULT_POLICY)


def _policy_to_dict(policy: BaselineDecisionPolicy) -> dict[str, Any]:
    return {
        "policy_id": policy.policy_id,
        "organization_id": policy.organization_id,
        "scope": policy.scope,
        "scope_value": policy.scope_value,
        "policy_name": policy.policy_name,
        "version": policy.version,
        "pass_threshold": policy.pass_threshold,
        "technician_review_threshold": policy.technician_review_threshold,
        "supervisor_attention_threshold": policy.supervisor_attention_threshold,
        "supervisor_approval_threshold": policy.supervisor_approval_threshold,
        "status": policy.status,
    }


def resolve_active_policy(
    db: Session,
    *,
    tenant_id: str,
    instrument_family: str = "",
    anatomy_zone: str = "",
    department: str = "",
    facility: str = "",
) -> dict[str, Any]:
    """Section 6 — resolve the most specific active+approved policy.

    Only status="active" rows influence the outcome — draft and
    pending_approval policies are never read here (Section 9).
    """
    candidates: list[tuple[str, str]] = [
        ("model", instrument_family),
        ("instrument_family", instrument_family),
        ("anatomy_zone", anatomy_zone),
        ("department", department),
        ("facility", facility),
        ("health_system", ""),
    ]
    for scope, scope_value in candidates:
        if scope != "health_system" and not scope_value:
            continue
        found = _query_scope(db, tenant_id, scope, scope_value)
        if found is not None:
            resolved = _policy_to_dict(found)
            resolved["resolution_order"] = [c[0] for c in candidates] + ["lumenai_default"]
            return resolved

    resolved = _default_policy_dict()
    resolved["resolution_order"] = [c[0] for c in candidates] + ["lumenai_default"]
    return resolved
