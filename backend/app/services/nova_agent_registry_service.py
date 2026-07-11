"""v5.4 — Project Nova, Sections 1, 2, 4: Agent Framework, Agent Registry,
Core Agents.

`AgentDefinition` is a persisted, queryable registry -- the existing
`app.agents.registry.get_registry()` (Phase 22) is static/in-memory.
`list_all_agents` merges both: Nova's own 14 named Core Agents plus
Phase 22's 10 pipeline agents, so `/api/nova/agents` is the complete
picture. `wrapped_module` on each Nova entry documents the real,
pre-existing module/service it composes -- never a second
implementation of that logic. Health uses the exact same "does the
wrapped module import successfully" check Phase 22's own registry
established, never a fabricated uptime/latency metric.
"""
from __future__ import annotations

import importlib
import json

from sqlalchemy.orm import Session

from app.models.nova_agent_platform import (
    AGENT_CATEGORY_CORE,
    AGENT_HEALTH_DEGRADED,
    AGENT_HEALTH_OK,
    AGENT_STATUSES,
    CORE_AGENT_KEYS,
    AgentDefinition,
)

# agent_key -> (name, role, capabilities, wrapped_module, dependencies)
_CORE_AGENT_SPECS: dict[str, dict] = {
    "inspection_agent": {
        "name": "Inspection Agent", "role": "Coordinates the full inspection reasoning pipeline.",
        "capabilities": ["run_inspection_pipeline", "explain_trace"], "wrapped_module": "app.agents.orchestrator",
        "dependencies": ["vision_agent", "anatomy_agent", "knowledge_agent"],
    },
    "vision_agent": {
        "name": "Vision Agent", "role": "Image-based instrument condition inference.",
        "capabilities": ["predict_from_image"], "wrapped_module": "app.ai.inference", "dependencies": [],
    },
    "anatomy_agent": {
        "name": "Anatomy Agent", "role": "Instrument anatomy zone identification and coverage assessment.",
        "capabilities": ["identify_zones", "assess_coverage"], "wrapped_module": "app.agents.anatomy_agent",
        "dependencies": ["vision_agent"],
    },
    "digital_twin_agent": {
        "name": "Digital Twin Agent", "role": "Digital Twin state and risk context.",
        "capabilities": ["compute_twin_dashboard"], "wrapped_module": "app.services.digital_twin_engine",
        "dependencies": [],
    },
    "knowledge_agent": {
        "name": "Knowledge Agent", "role": "Institutional knowledge and memory retrieval.",
        "capabilities": ["memory_summary"], "wrapped_module": "app.services.athena_memory_service", "dependencies": [],
    },
    "clinical_reasoning_agent": {
        "name": "Clinical Reasoning Agent", "role": "Clinical interpretation and risk-level reasoning.",
        "capabilities": ["reason_about_findings"], "wrapped_module": "app.agents.clinical_reasoning_agent",
        "dependencies": ["anatomy_agent", "knowledge_agent"],
    },
    "workflow_agent": {
        "name": "Workflow Agent", "role": "Workflow definition and execution composition.",
        "capabilities": ["list_workflows"], "wrapped_module": "app.services.forge_workflow_service", "dependencies": [],
    },
    "simulation_agent": {
        "name": "Simulation Agent", "role": "Scenario simulation and outcome prediction.",
        "capabilities": ["get_latest_run"], "wrapped_module": "app.services.simulation_engine_service", "dependencies": [],
    },
    "quality_agent": {
        "name": "Quality Agent", "role": "Executive quality dashboard and maturity index.",
        "capabilities": ["executive_quality_dashboard"], "wrapped_module": "app.services.apollo_executive_quality_service",
        "dependencies": [],
    },
    "capa_agent": {
        "name": "CAPA Agent", "role": "Corrective and Preventive Action tracking.",
        "capabilities": ["capa_engine_summary"], "wrapped_module": "app.services.apollo_capa_engine_service", "dependencies": [],
    },
    "audit_agent": {
        "name": "Audit Agent", "role": "Tamper-evident audit trail verification.",
        "capabilities": ["verify_audit_chain"], "wrapped_module": "app.services.audit_chain_verification_service",
        "dependencies": [],
    },
    "executive_agent": {
        "name": "Executive Agent", "role": "Board-level executive intelligence.",
        "capabilities": ["executive_intelligence_center"], "wrapped_module": "app.services.vanguard_executive_intelligence_service",
        "dependencies": [],
    },
    "research_agent": {
        "name": "Research Agent", "role": "Research collaboration hub composition.",
        "capabilities": ["research_hub_summary"], "wrapped_module": "app.services.genesis_ai_research_hub_service",
        "dependencies": [],
    },
    "enterprise_agent": {
        "name": "Enterprise Agent", "role": "Cross-facility enterprise intelligence.",
        "capabilities": ["facility_readiness_summary"], "wrapped_module": "app.agents.enterprise_agent", "dependencies": [],
    },
}


def _check_health(wrapped_module: str) -> str:
    if not wrapped_module:
        return AGENT_HEALTH_DEGRADED
    try:
        importlib.import_module(wrapped_module)
        return AGENT_HEALTH_OK
    except Exception:
        return AGENT_HEALTH_DEGRADED


def _to_dict(row: AgentDefinition) -> dict:
    return {
        "id": row.id,
        "agent_key": row.agent_key,
        "name": row.name,
        "role": row.role,
        "agent_category": row.agent_category,
        "capabilities": json.loads(row.capabilities_json or "[]"),
        "permissions": json.loads(row.permissions_json or "[]"),
        "goals": json.loads(row.goals_json or "[]"),
        "dependencies": json.loads(row.dependencies_json or "[]"),
        "wrapped_module": row.wrapped_module,
        "version": row.version,
        "status": row.status,
        "health": row.health,
        "developer_account_id": row.developer_account_id,
        "registered_by": row.registered_by,
        "created_at": row.created_at.isoformat(),
    }


def seed_core_agents(db: Session, *, registered_by: str = "system") -> list[dict]:
    """Idempotent -- registers each of the 14 named Core Agents exactly
    once (by `agent_key`), re-checking health on every call."""
    results = []
    for agent_key in CORE_AGENT_KEYS:
        spec = _CORE_AGENT_SPECS[agent_key]
        row = db.query(AgentDefinition).filter(AgentDefinition.agent_key == agent_key).first()
        health = _check_health(spec["wrapped_module"])
        if row is None:
            row = AgentDefinition(
                agent_key=agent_key, name=spec["name"], role=spec["role"], agent_category=AGENT_CATEGORY_CORE,
                capabilities_json=json.dumps(spec["capabilities"]), permissions_json=json.dumps(["read", "advise"]),
                goals_json=json.dumps([spec["role"]]), dependencies_json=json.dumps(spec["dependencies"]),
                wrapped_module=spec["wrapped_module"], health=health, registered_by=registered_by,
            )
            db.add(row)
        else:
            row.health = health
        db.commit()
        db.refresh(row)
        results.append(_to_dict(row))
    return results


class UnknownAgentError(Exception):
    pass


def _get_or_404(db: Session, agent_key: str) -> AgentDefinition:
    row = db.query(AgentDefinition).filter(AgentDefinition.agent_key == agent_key).first()
    if row is None:
        raise UnknownAgentError(f"Agent '{agent_key}' not found.")
    return row


def get_agent(db: Session, agent_key: str) -> dict:
    return _to_dict(_get_or_404(db, agent_key))


def set_agent_status(db: Session, agent_key: str, *, status: str) -> dict:
    if status not in AGENT_STATUSES:
        raise ValueError(f"status must be one of {AGENT_STATUSES}")
    row = _get_or_404(db, agent_key)
    row.status = status
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_nova_agents(db: Session, *, agent_category: str = "") -> list[dict]:
    query = db.query(AgentDefinition)
    if agent_category:
        query = query.filter(AgentDefinition.agent_category == agent_category)
    return [_to_dict(r) for r in query.order_by(AgentDefinition.agent_key.asc()).all()]


def list_all_agents(db: Session) -> dict:
    """Section 2: the complete Agent Registry -- Nova's own agents plus
    Phase 22's 10 live pipeline agents, never one without the other."""
    from app.agents.registry import get_registry as get_phase22_registry

    return {
        "nova_agents": list_nova_agents(db),
        "phase22_pipeline_agents": get_phase22_registry(),
    }
