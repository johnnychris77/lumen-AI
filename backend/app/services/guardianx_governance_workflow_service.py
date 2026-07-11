"""v5.2 — Project GuardianX, Section 6: Governance Workflow.

Reuses Forge's `WorkflowApprovalChain`/`WorkflowApprovalInstance`
(`forge_approval_service.py`) a **fifth** time -- after Athena, Phoenix,
Infinity, and Olympus -- with the five named gates (Clinical Review
Board, AI Governance Committee, Quality Leadership, Security,
Compliance) as its ordered steps. Mirrors
`olympus_certification_registry_service.py`'s exact chain/instance
mechanics, but drives a distinct `governance_*` linkage on
`AIModelRegistryEntry` rather than the pre-existing `certification_*`
fields -- a model can be certified and not yet governance-approved, or
vice versa.

"Every production model requires documented approval": nothing in this
module marks a model's `governance_status` as `approved` without every
one of the five gates recording an `approved` decision first.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import GOVERNANCE_APPROVED, GOVERNANCE_GATES, GOVERNANCE_IN_PROGRESS, GOVERNANCE_REJECTED
from app.services import forge_approval_service
from app.services.olympus_model_registry_service import get_model_or_404

_GLOBAL_TENANT = ""


def start_governance_review(db: Session, model_id: int) -> dict:
    model = get_model_or_404(db, model_id)
    chain = forge_approval_service.create_chain(
        db, _GLOBAL_TENANT, name=f"Governance Review: {model.name} v{model.version}", steps=GOVERNANCE_GATES,
    )
    instance = forge_approval_service.start_instance(db, _GLOBAL_TENANT, chain["id"])

    model.governance_chain_id = chain["id"]
    model.governance_instance_id = instance["id"]
    model.governance_status = GOVERNANCE_IN_PROGRESS
    db.commit()
    db.refresh(model)
    return {"model_id": model.id, "chain": chain, "instance": instance}


def advance_governance_review(
    db: Session, model_id: int, *, decided_by: str, decided_role: str, decision: str, notes: str = "",
) -> dict:
    model = get_model_or_404(db, model_id)
    if model.governance_instance_id is None:
        raise ValueError(f"Model {model_id} has not started governance review yet.")

    instance = forge_approval_service.decide_step(
        db, model.governance_instance_id, decided_by=decided_by, decided_role=decided_role,
        decision=decision, notes=notes,
    )

    if decision == "rejected":
        model.governance_status = GOVERNANCE_REJECTED
    elif instance["status"] == "approved":
        model.governance_status = GOVERNANCE_APPROVED
    db.commit()
    db.refresh(model)
    return {"model_id": model.id, "governance_status": model.governance_status, "instance": instance}


def get_governance_review_status(db: Session, model_id: int) -> dict:
    model = get_model_or_404(db, model_id)
    instance = (
        forge_approval_service.get_instance(db, model.governance_instance_id)
        if model.governance_instance_id else None
    )
    return {
        "model_id": model.id, "governance_status": model.governance_status,
        "gates": GOVERNANCE_GATES, "instance": instance,
    }


def is_production_ready(db: Session, model_id: int) -> bool:
    """Section 6: 'Every production model requires documented approval.'"""
    model = get_model_or_404(db, model_id)
    return model.governance_status == GOVERNANCE_APPROVED
