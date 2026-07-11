"""v5.1 — Project Olympus: umbrella `/network` composition.

Mirrors the umbrella-summary pattern already used by
`phoenix_learning_engine_service.py` (v4.9) -- one read-only composition
across every Olympus section, never a duplicate store.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    olympus_certification_registry_service,
    olympus_governance_council_service,
    olympus_marketplace_service,
    olympus_network_identity_service,
    olympus_observatory_service,
)


def network_summary(db: Session) -> dict:
    return {
        "network_identity": olympus_network_identity_service.network_directory_summary(db),
        "research_observatory": olympus_observatory_service.observatory_summary(db),
        "certification_registry": olympus_certification_registry_service.certification_registry(db),
        "innovation_marketplace": olympus_marketplace_service.innovation_marketplace_summary(db),
        "governance_council": olympus_governance_council_service.council_summary(db),
    }
