"""v5.4 — Project Nova: umbrella agent-platform composition.

Mirrors the umbrella-summary pattern already used by
`phoenix_learning_engine_service.py` (v4.9), `olympus_network_summary_service.py`
(v5.1), and `genesis_ai_intelligence_cloud_summary_service.py` (v5.3) --
one read-only composition across every Nova section, never a duplicate
store.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    nova_agent_registry_service,
    nova_marketplace_service,
    nova_observability_service,
)


def platform_summary(db: Session, tenant_id: str) -> dict:
    return {
        "agent_registry": nova_agent_registry_service.list_all_agents(db),
        "observability": nova_observability_service.observability_summary(db, tenant_id),
        "agent_marketplace": nova_marketplace_service.agent_marketplace_summary(db),
    }
