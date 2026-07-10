"""v3.4 — Project Horizon, Section 2: Global Knowledge Graph.

Local -> Enterprise -> Global, each layer built from what already exists:

  * **Local** — the existing, strictly per-tenant Knowledge Graph
    (`knowledge_graph_service.py`, "Phase 21" — there is no prior
    "Project Cortex" anywhere in this codebase; this module extends that
    existing reasoning engine, the closest real system to what the sprint
    brief calls "Cortex"). `local_graph_summary` calls its `explore()`/
    `learning_confidence()` directly — nothing recomputed.
  * **Enterprise** — Atlas's existing per-health-system rollups
    (`atlas_dashboard_service.py`) already aggregate a system's own
    facilities; no new code is needed for that layer, exactly as Atlas's
    own Section 1 found for the organization hierarchy.
  * **Global** — genuinely new: `compute_global_knowledge_graph`
    aggregates real `InspectionFinding` observations (instrument type ->
    zone -> finding type, following the existing `NODE_TYPES`/
    `RELATIONSHIP_TYPES` taxonomy from `knowledge_graph_service.py` rather
    than inventing a parallel vocabulary) across every organization with
    an active federated sharing agreement, gated by the same
    `GLOBAL_K_THRESHOLD` used everywhere else in this module.

Every organization retains ownership of its own local knowledge graph —
this module only ever aggregates counts, never a tenant's underlying
inspection records.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.federated_horizon import GlobalKnowledgeGraphEdge
from app.models.inspection_finding import InspectionFinding
from app.services import horizon_participation_service
from app.services.global_aggregation_job import GLOBAL_K_THRESHOLD
from app.services.knowledge_graph_service import explore, learning_confidence

_LOOKBACK_DAYS = 90
_RELATIONSHIP_TYPE = "Zone HAS Common Findings"


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def local_graph_summary(db: Session, tenant_id: str, *, category: str = "instrument", query: str = "") -> dict:
    return {
        "layer": "local", "tenant_id": tenant_id,
        "explore": explore(db, tenant_id, category, query),
        "learning_confidence": learning_confidence(db, tenant_id),
    }


def enterprise_graph_reference() -> dict:
    """No new code needed for this layer — Atlas's existing
    `atlas_dashboard_service.enterprise_dashboard` already rolls up a
    health system's own facilities, the same finding Atlas's own Section
    1 reached for the organization hierarchy."""
    return {
        "layer": "enterprise",
        "note": "Served by the existing Atlas enterprise rollup (atlas_dashboard_service.enterprise_dashboard) — no separate Horizon code needed for this layer.",
    }


def compute_global_knowledge_graph(db: Session) -> list[dict]:
    tenant_ids = horizon_participation_service.list_enrolled_tenant_ids(db)
    if not tenant_ids:
        return []

    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    rows = (
        db.query(InspectionFinding.tenant_id, InspectionFinding.instrument_type, InspectionFinding.zone, InspectionFinding.finding_type)
        .filter(InspectionFinding.tenant_id.in_(tenant_ids), InspectionFinding.created_at >= since, InspectionFinding.zone != "")
        .all()
    )

    edges: dict[tuple[str, str, str], dict] = defaultdict(lambda: {"tenants": set(), "count": 0})
    for tenant_id, instrument_type, zone, finding_type in rows:
        key = (instrument_type, zone, finding_type)
        edges[key]["tenants"].add(tenant_id)
        edges[key]["count"] += 1

    created = []
    for (instrument_type, zone, finding_type), agg in edges.items():
        tenant_count = len(agg["tenants"])
        published = tenant_count >= GLOBAL_K_THRESHOLD
        confidence = round(min(0.95, tenant_count / (GLOBAL_K_THRESHOLD * 2)), 3) if published else 0.0

        row = GlobalKnowledgeGraphEdge(
            source_node_type="Instrument", source_node_value=f"{instrument_type}:{zone}",
            relationship_type=_RELATIONSHIP_TYPE, target_node_type="Finding", target_node_value=finding_type,
            tenant_count=tenant_count, observation_count=agg["count"], confidence=confidence,
            k_anonymity_verified=published, published=published,
        )
        db.add(row)
        created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)
    return list_global_graph(db)


def list_global_graph(db: Session, *, source_node_type: str = "", published_only: bool = True) -> list[dict]:
    q = db.query(GlobalKnowledgeGraphEdge)
    if source_node_type:
        q = q.filter(GlobalKnowledgeGraphEdge.source_node_type == source_node_type)
    if published_only:
        q = q.filter(GlobalKnowledgeGraphEdge.published.is_(True))
    rows = q.order_by(GlobalKnowledgeGraphEdge.id.desc()).limit(200).all()
    return [_row_to_dict(r) for r in rows]
