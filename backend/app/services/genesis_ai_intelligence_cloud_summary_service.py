"""v5.3 — Project Genesis AI: umbrella intelligence-cloud composition.

Mirrors the umbrella-summary pattern already used by
`phoenix_learning_engine_service.py` (v4.9) and
`olympus_network_summary_service.py` (v5.1) -- one read-only composition
across every Genesis AI section, never a duplicate store.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    genesis_ai_anatomy_registry_service,
    genesis_ai_evidence_cloud_service,
    genesis_ai_intelligence_exchange_service,
    genesis_ai_standards_observatory_service,
)
from app.services.instrument_registry_service import get_registry_stats


def intelligence_cloud_summary(db: Session, tenant_id: str) -> dict:
    return {
        "instrument_registry": get_registry_stats(db),
        "anatomy_registry": genesis_ai_anatomy_registry_service.anatomy_registry_summary(db),
        "evidence_cloud": genesis_ai_evidence_cloud_service.evidence_cloud_summary(db),
        "intelligence_exchange": genesis_ai_intelligence_exchange_service.intelligence_exchange_summary(db),
        "standards_observatory": genesis_ai_standards_observatory_service.observatory_summary(db, tenant_id),
    }
