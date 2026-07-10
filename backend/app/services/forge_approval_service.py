"""v4.1 — Project Forge, Section 7: Approval Workflows.

Confirmed nothing in this codebase already models a multi-step
(Technician → Supervisor → Manager → Director → Final) approval chain —
`GovernanceApproval` is single-reviewer only, and
`approval_escalation_service.py` only re-notifies a stale single
approval, it never advances to a different role/tier. This is a
genuine gap: `WorkflowApprovalChain` (an organization-defined ordered
role list) and `WorkflowApprovalInstance` (one running instance,
tracking the current step and every step's decision) are new.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.workflow_forge import (
    APPROVAL_APPROVED,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    DEFAULT_APPROVAL_STEPS,
    WorkflowApprovalChain,
    WorkflowApprovalInstance,
)


class UnknownApprovalChainError(Exception):
    pass


class UnknownApprovalInstanceError(Exception):
    pass


class ApprovalAlreadyDecidedError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _chain_to_dict(row: WorkflowApprovalChain) -> dict:
    result = _row_to_dict(row)
    result["steps"] = json.loads(result.pop("steps_json"))
    return result


def _instance_to_dict(row: WorkflowApprovalInstance) -> dict:
    result = _row_to_dict(row)
    result["decisions"] = json.loads(result.pop("decisions_json") or "[]")
    return result


def create_chain(db: Session, tenant_id: str, *, name: str, steps: list[str] | None = None) -> dict:
    steps = steps or DEFAULT_APPROVAL_STEPS
    row = WorkflowApprovalChain(tenant_id=tenant_id, name=name, steps_json=json.dumps(steps))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _chain_to_dict(row)


def list_chains(db: Session, tenant_id: str) -> list[dict]:
    rows = db.query(WorkflowApprovalChain).filter(
        (WorkflowApprovalChain.tenant_id == tenant_id) | (WorkflowApprovalChain.tenant_id == ""),
    ).order_by(WorkflowApprovalChain.id.desc()).all()
    return [_chain_to_dict(r) for r in rows]


def _get_chain_or_404(db: Session, chain_id: int) -> WorkflowApprovalChain:
    row = db.query(WorkflowApprovalChain).filter(WorkflowApprovalChain.id == chain_id).first()
    if row is None:
        raise UnknownApprovalChainError(f"Approval chain {chain_id} not found.")
    return row


def start_instance(db: Session, tenant_id: str, chain_id: int, *, execution_id: int | None = None) -> dict:
    _get_chain_or_404(db, chain_id)
    row = WorkflowApprovalInstance(tenant_id=tenant_id, chain_id=chain_id, execution_id=execution_id, current_step_index=0, status=APPROVAL_PENDING)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _instance_to_dict(row)


def _get_instance_or_404(db: Session, instance_id: int) -> WorkflowApprovalInstance:
    row = db.query(WorkflowApprovalInstance).filter(WorkflowApprovalInstance.id == instance_id).first()
    if row is None:
        raise UnknownApprovalInstanceError(f"Approval instance {instance_id} not found.")
    return row


def decide_step(
    db: Session, instance_id: int, *, decided_by: str, decided_role: str, decision: str, notes: str = "",
) -> dict:
    """Records one step's decision. `decision == 'approved'` advances to
    the next step (or completes the instance if it was the final step);
    `decision == 'rejected'` ends the instance immediately — a rejection
    at any step never silently advances past it."""
    instance = _get_instance_or_404(db, instance_id)
    if instance.status != APPROVAL_PENDING:
        raise ApprovalAlreadyDecidedError(f"Approval instance {instance_id} is already '{instance.status}'.")

    chain = _get_chain_or_404(db, instance.chain_id)
    steps = json.loads(chain.steps_json)
    if instance.current_step_index >= len(steps):
        raise ApprovalAlreadyDecidedError(f"Approval instance {instance_id} has no remaining steps.")

    expected_role = steps[instance.current_step_index]
    decisions = json.loads(instance.decisions_json or "[]")
    decisions.append({
        "step": instance.current_step_index, "expected_role": expected_role, "decided_role": decided_role,
        "decided_by": decided_by, "decision": decision, "notes": notes,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    })
    instance.decisions_json = json.dumps(decisions)

    if decision == "rejected":
        instance.status = APPROVAL_REJECTED
        instance.completed_at = datetime.now(timezone.utc)
    else:
        instance.current_step_index += 1
        if instance.current_step_index >= len(steps):
            instance.status = APPROVAL_APPROVED
            instance.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(instance)
    return _instance_to_dict(instance)


def get_instance(db: Session, instance_id: int) -> dict | None:
    row = db.query(WorkflowApprovalInstance).filter(WorkflowApprovalInstance.id == instance_id).first()
    return _instance_to_dict(row) if row else None


def list_instances(db: Session, tenant_id: str, *, status: str = "") -> list[dict]:
    q = db.query(WorkflowApprovalInstance).filter(WorkflowApprovalInstance.tenant_id == tenant_id)
    if status:
        q = q.filter(WorkflowApprovalInstance.status == status)
    return [_instance_to_dict(r) for r in q.order_by(WorkflowApprovalInstance.id.desc()).all()]
