"""v5.0 — Project Infinity, Section 7: Certification Program.

Reuses Project Forge's `WorkflowApprovalChain`/`WorkflowApprovalInstance`
(`forge_approval_service.py`, v4.1) a third time — already reused by
Athena (v4.8) and Phoenix's Continuous Validation (v4.9) — with the seven
named gates (Security/Performance/Clinical Safety/Explainability/
Accessibility/Documentation/Governance) as its ordered steps. No second
approval-chain model. Marketplace listings are platform-global, not
tenant-scoped, so certification chains use `tenant_id=""` — the same
"global" convention Forge's own workflow templates already use.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.infinity_platform import CERT_CERTIFIED, CERT_IN_PROGRESS, CERT_REJECTED, CERTIFICATION_GATES
from app.services import forge_approval_service
from app.services.infinity_marketplace_service import get_listing_or_404

_GLOBAL_TENANT = ""


def start_certification(db: Session, listing_id: int) -> dict:
    listing = get_listing_or_404(db, listing_id)
    chain = forge_approval_service.create_chain(
        db, _GLOBAL_TENANT, name=f"Certification: {listing.name} v{listing.version}", steps=CERTIFICATION_GATES,
    )
    instance = forge_approval_service.start_instance(db, _GLOBAL_TENANT, chain["id"])

    listing.certification_chain_id = chain["id"]
    listing.certification_instance_id = instance["id"]
    listing.certification_status = CERT_IN_PROGRESS
    db.commit()
    db.refresh(listing)
    return {"listing_id": listing.id, "chain": chain, "instance": instance}


def advance_certification(
    db: Session, listing_id: int, *, decided_by: str, decided_role: str, decision: str, notes: str = "",
) -> dict:
    listing = get_listing_or_404(db, listing_id)
    if listing.certification_instance_id is None:
        raise ValueError(f"Listing {listing_id} has not started certification yet.")

    instance = forge_approval_service.decide_step(
        db, listing.certification_instance_id, decided_by=decided_by, decided_role=decided_role,
        decision=decision, notes=notes,
    )

    if decision == "rejected":
        listing.certification_status = CERT_REJECTED
    elif instance["status"] == "approved":
        listing.certification_status = CERT_CERTIFIED
    db.commit()
    db.refresh(listing)
    return {"listing_id": listing.id, "certification_status": listing.certification_status, "instance": instance}


def get_certification_status(db: Session, listing_id: int) -> dict:
    listing = get_listing_or_404(db, listing_id)
    instance = (
        forge_approval_service.get_instance(db, listing.certification_instance_id)
        if listing.certification_instance_id else None
    )
    return {
        "listing_id": listing.id, "certification_status": listing.certification_status,
        "gates": CERTIFICATION_GATES, "instance": instance,
    }
