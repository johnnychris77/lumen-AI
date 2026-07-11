"""v5.2 — Project GuardianX, Section 1: AI Assurance Center.

Umbrella `/ai-assurance` composition, mirroring the umbrella-summary
pattern already used by `phoenix_learning_engine_service.py` (v4.9) and
`olympus_network_summary_service.py` (v5.1) -- one read-only view across
every model's status/validation/certification/approvals/evidence/risk
rating/version history, never a duplicate store.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.olympus_network import AIModelRegistryEntry
from app.services import guardianx_model_governance_service, guardianx_risk_registry_service
from app.services.olympus_model_registry_service import version_chain


def model_assurance_summary(db: Session, model_id: int) -> dict:
    governance = guardianx_model_governance_service.get_governance_record(db, model_id)
    return {
        "model": governance,
        "risk_rating": guardianx_risk_registry_service.list_risks_for_model(db, model_id),
        "version_history": version_chain(db, model_id),
    }


def assurance_center_summary(db: Session) -> dict:
    models = db.query(AIModelRegistryEntry).all()
    return {
        "total_models": len(models),
        "by_validation_status": _count_by(models, "validation_status"),
        "by_certification_status": _count_by(models, "certification_status"),
        "by_governance_status": _count_by(models, "governance_status"),
        "risk_registry": guardianx_risk_registry_service.risk_registry_summary(db),
    }


def _count_by(models: list[AIModelRegistryEntry], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in models:
        value = getattr(m, attr)
        counts[value] = counts.get(value, 0) + 1
    return counts
