"""v5.1 — Project Olympus, Section 7: Certification Registry.

Not a new certification engine -- a read-only index across two surfaces
that already certify things through Forge's `WorkflowApprovalChain`
(`forge_approval_service.py`, reused here for the fourth time after
Athena, Phoenix, and Infinity): Infinity's `MarketplaceListing`
(workflows/knowledge/education published as marketplace listings, using
Infinity's own 7-gate `CERTIFICATION_GATES`) and this sprint's new
`AIModelRegistryEntry` (AI models, using the same gate list for
consistency). AI model certification itself mirrors
`infinity_certification_service.py`'s exact chain/instance mechanics.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.infinity_platform import CERTIFICATION_GATES, MarketplaceListing
from app.models.infinity_platform import CERT_CERTIFIED as LISTING_CERT_CERTIFIED
from app.models.infinity_platform import CERT_IN_PROGRESS as LISTING_CERT_IN_PROGRESS
from app.models.infinity_platform import CERT_REJECTED as LISTING_CERT_REJECTED
from app.models.olympus_network import MODEL_CERT_CERTIFIED, MODEL_CERT_IN_PROGRESS, MODEL_CERT_REJECTED, AIModelRegistryEntry
from app.services import forge_approval_service
from app.services.olympus_model_registry_service import get_model_or_404

_GLOBAL_TENANT = ""


def start_model_certification(db: Session, model_id: int) -> dict:
    model = get_model_or_404(db, model_id)
    chain = forge_approval_service.create_chain(
        db, _GLOBAL_TENANT, name=f"AI Model Certification: {model.name} v{model.version}", steps=CERTIFICATION_GATES,
    )
    instance = forge_approval_service.start_instance(db, _GLOBAL_TENANT, chain["id"])

    model.certification_chain_id = chain["id"]
    model.certification_instance_id = instance["id"]
    model.certification_status = MODEL_CERT_IN_PROGRESS
    db.commit()
    db.refresh(model)
    return {"model_id": model.id, "chain": chain, "instance": instance}


def advance_model_certification(
    db: Session, model_id: int, *, decided_by: str, decided_role: str, decision: str, notes: str = "",
) -> dict:
    model = get_model_or_404(db, model_id)
    if model.certification_instance_id is None:
        raise ValueError(f"Model {model_id} has not started certification yet.")

    instance = forge_approval_service.decide_step(
        db, model.certification_instance_id, decided_by=decided_by, decided_role=decided_role,
        decision=decision, notes=notes,
    )

    if decision == "rejected":
        model.certification_status = MODEL_CERT_REJECTED
    elif instance["status"] == "approved":
        model.certification_status = MODEL_CERT_CERTIFIED
    db.commit()
    db.refresh(model)
    return {"model_id": model.id, "certification_status": model.certification_status, "instance": instance}


def get_model_certification_status(db: Session, model_id: int) -> dict:
    model = get_model_or_404(db, model_id)
    instance = (
        forge_approval_service.get_instance(db, model.certification_instance_id)
        if model.certification_instance_id else None
    )
    return {
        "model_id": model.id, "certification_status": model.certification_status,
        "gates": CERTIFICATION_GATES, "instance": instance,
    }


def certification_registry(db: Session) -> dict:
    """Section 7: "Certification status is visible to participants" --
    one read-only view across both certified-thing surfaces."""
    listings = db.query(MarketplaceListing).filter(MarketplaceListing.certification_status != "not_started").all()
    models = db.query(AIModelRegistryEntry).filter(AIModelRegistryEntry.certification_status != "not_started").all()

    def _listing_summary(listing: MarketplaceListing) -> dict:
        return {
            "kind": "marketplace_listing", "id": listing.id, "name": listing.name,
            "listing_type": listing.listing_type, "version": listing.version,
            "certification_status": listing.certification_status,
        }

    def _model_summary(model: AIModelRegistryEntry) -> dict:
        return {
            "kind": "ai_model", "id": model.id, "name": model.name,
            "model_type": model.model_type, "version": model.version,
            "certification_status": model.certification_status,
        }

    entries = [_listing_summary(listing) for listing in listings] + [_model_summary(model) for model in models]
    return {
        "gates": CERTIFICATION_GATES,
        "total_certified": sum(
            1 for e in entries if e["certification_status"] in (LISTING_CERT_CERTIFIED, MODEL_CERT_CERTIFIED)
        ),
        "total_in_progress": sum(
            1 for e in entries if e["certification_status"] in (LISTING_CERT_IN_PROGRESS, MODEL_CERT_IN_PROGRESS)
        ),
        "total_rejected": sum(
            1 for e in entries if e["certification_status"] in (LISTING_CERT_REJECTED, MODEL_CERT_REJECTED)
        ),
        "entries": entries,
    }
