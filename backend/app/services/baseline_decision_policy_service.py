"""Section 5 & 8 — Configurable Baseline Decision Policy & Governance.

CRUD + lifecycle for `BaselineDecisionPolicy` rows. Only rows with
status "active" (which requires having passed through "approved" first)
may influence a live recommendation — see `policy_resolution_service`.

Technicians (`operator`) and viewers may never create, approve, or publish
a policy — enforced both here (defense in depth) and at the route layer
via `require_roles`.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.lumen_decision_engine import (
    POLICY_SCOPES,
    ROLES_MAY_PUBLISH_POLICY,
    BaselineDecisionPolicy,
)


class PolicyGovernanceError(Exception):
    """Raised when a policy governance rule is violated."""


# Section 5 — LumenAI's recommended starting policy. Explicitly NOT a
# universal clinical standard; local organizations may adopt a stricter
# policy at any resolvable scope. Used only when no organization-specific
# policy resolves at any scope (see policy_resolution_service).
LUMENAI_DEFAULT_POLICY = {
    "policy_id": "lumenai-default-v1",
    "organization_id": "*",
    "scope": "lumenai_default",
    "scope_value": "",
    "policy_name": "LumenAI Recommended Starting Policy",
    "version": "1.0",
    "pass_threshold": 0.90,
    "technician_review_threshold": 0.70,
    "supervisor_attention_threshold": 0.70,
    "supervisor_approval_threshold": 0.0,
    "status": "active",
    "author": "LumenAI",
    "approving_role": "system",
    "rationale": (
        "LumenAI-recommended default, not a universal clinical standard. "
        "Local organizations should adopt a stricter approved threshold "
        "where their own governance requires it."
    ),
}


def _require_publisher_role(actor_role: str) -> None:
    if actor_role not in ROLES_MAY_PUBLISH_POLICY:
        raise PolicyGovernanceError(
            f"Role '{actor_role}' may not publish or modify a Baseline Decision Policy.",
        )


def create_draft_policy(
    db: Session, *, tenant_id: str, actor: str, actor_role: str, fields: dict[str, Any],
) -> BaselineDecisionPolicy:
    _require_publisher_role(actor_role)
    scope = fields.get("scope", "facility")
    if scope not in POLICY_SCOPES:
        raise PolicyGovernanceError(f"Unknown policy scope '{scope}'. Known: {POLICY_SCOPES}")

    policy = BaselineDecisionPolicy(
        policy_id=fields.get("policy_id") or f"policy-{secrets.token_hex(6)}",
        organization_id=tenant_id,
        scope=scope,
        scope_value=fields.get("scope_value", ""),
        policy_name=fields["policy_name"],
        version=fields.get("version", "1.0"),
        baseline_source_requirement=fields.get("baseline_source_requirement", "any_approved"),
        pass_threshold=fields.get("pass_threshold", 0.90),
        technician_review_threshold=fields.get("technician_review_threshold", 0.70),
        supervisor_attention_threshold=fields.get("supervisor_attention_threshold", 0.70),
        supervisor_approval_threshold=fields.get("supervisor_approval_threshold", 0.0),
        author=actor,
        approving_role=fields.get("approving_role", ""),
        rationale=fields.get("rationale", ""),
        supporting_reference=fields.get("supporting_reference", ""),
        status="draft",
        previous_version_id=fields.get("previous_version_id"),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def submit_for_approval(db: Session, policy: BaselineDecisionPolicy, *, actor_role: str) -> BaselineDecisionPolicy:
    _require_publisher_role(actor_role)
    if policy.status != "draft":
        raise PolicyGovernanceError(f"Only a draft policy can be submitted for approval (current: {policy.status}).")
    policy.status = "pending_approval"
    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return policy


def approve_policy(db: Session, policy: BaselineDecisionPolicy, *, actor: str, actor_role: str) -> BaselineDecisionPolicy:
    _require_publisher_role(actor_role)
    if policy.status != "pending_approval":
        raise PolicyGovernanceError(f"Only a pending_approval policy can be approved (current: {policy.status}).")
    policy.status = "approved"
    policy.approved_by = actor
    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return policy


def activate_policy(db: Session, policy: BaselineDecisionPolicy, *, actor_role: str) -> BaselineDecisionPolicy:
    """Section 9 — publication requires an authorized human decision. This is
    that decision: an approved draft becomes the live, active policy for its
    scope, superseding whatever was previously active in the same scope."""
    _require_publisher_role(actor_role)
    if policy.status != "approved":
        raise PolicyGovernanceError(f"Only an approved policy can be activated (current: {policy.status}).")

    prior_active = (
        db.query(BaselineDecisionPolicy)
        .filter(
            BaselineDecisionPolicy.organization_id == policy.organization_id,
            BaselineDecisionPolicy.scope == policy.scope,
            BaselineDecisionPolicy.scope_value == policy.scope_value,
            BaselineDecisionPolicy.status == "active",
            BaselineDecisionPolicy.id != policy.id,
        )
        .all()
    )
    for prior in prior_active:
        prior.status = "superseded"
        prior.updated_at = datetime.now(timezone.utc)

    policy.status = "active"
    policy.effective_date = datetime.now(timezone.utc)
    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return policy


def archive_policy(db: Session, policy: BaselineDecisionPolicy, *, actor_role: str) -> BaselineDecisionPolicy:
    _require_publisher_role(actor_role)
    policy.status = "archived"
    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return policy


def reject_policy(db: Session, policy: BaselineDecisionPolicy, *, actor_role: str) -> BaselineDecisionPolicy:
    _require_publisher_role(actor_role)
    if policy.status != "pending_approval":
        raise PolicyGovernanceError(f"Only a pending_approval policy can be rejected (current: {policy.status}).")
    policy.status = "rejected"
    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return policy


def list_policies(db: Session, *, tenant_id: str) -> list[BaselineDecisionPolicy]:
    return (
        db.query(BaselineDecisionPolicy)
        .filter(BaselineDecisionPolicy.organization_id == tenant_id)
        .order_by(BaselineDecisionPolicy.created_at.desc())
        .all()
    )
