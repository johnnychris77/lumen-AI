"""v5.4 — Project Nova, Section 4: Core Agent invocation.

Dispatches an `invoke_agent` call to the real, pre-existing service each
Core Agent wraps (see `nova_agent_registry_service._CORE_AGENT_SPECS`).
For agents that are already implemented as real Phase 22 pipeline
classes (anatomy, clinical reasoning, enterprise) or that require inputs
this generic endpoint can't reasonably supply (inspection pipeline runs
need a real inspection id; vision inference needs real image bytes;
simulation needs a real inspection id), this honestly returns a
reference to where that agent is actually invoked, rather than
fabricating a result.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    apollo_capa_engine_service,
    apollo_executive_quality_service,
    athena_memory_service,
    audit_chain_verification_service,
    forge_workflow_service,
    genesis_ai_research_hub_service,
    nova_communication_bus_service,
    vanguard_executive_intelligence_service,
)
from app.services.digital_twin_engine import compute_twin_dashboard


class UnknownAgentInvocationError(Exception):
    pass


def _reference_only(agent_key: str, where: str) -> dict:
    return {
        "agent_key": agent_key, "invoked": False,
        "note": f"'{agent_key}' is invoked via {where}, not through this generic endpoint.",
    }


def invoke_agent(db: Session, agent_key: str, tenant_id: str, *, kwargs: dict | None = None) -> dict:
    kwargs = kwargs or {}
    logged_target = agent_key

    if agent_key == "digital_twin_agent":
        result = compute_twin_dashboard(tenant_id, kwargs.get("facility_id", ""), db).model_dump()
    elif agent_key == "knowledge_agent":
        result = athena_memory_service.memory_summary(db, tenant_id)
    elif agent_key == "workflow_agent":
        result = {"workflows": forge_workflow_service.list_workflows(db, tenant_id)}
    elif agent_key == "quality_agent":
        result = apollo_executive_quality_service.executive_quality_dashboard(db, tenant_id)
    elif agent_key == "capa_agent":
        result = apollo_capa_engine_service.capa_engine_summary(db, tenant_id)
    elif agent_key == "executive_agent":
        result = vanguard_executive_intelligence_service.executive_intelligence_center(db, tenant_id)
    elif agent_key == "research_agent":
        result = genesis_ai_research_hub_service.research_hub_summary(db)
    elif agent_key == "audit_agent":
        resource_type = kwargs.get("resource_type", "")
        resource_id = kwargs.get("resource_id", "")
        if not resource_type or not resource_id:
            raise UnknownAgentInvocationError("audit_agent requires resource_type and resource_id kwargs.")
        result = audit_chain_verification_service.verify_audit_chain(db, resource_type=resource_type, resource_id=resource_id)
    elif agent_key == "inspection_agent":
        result = _reference_only(agent_key, "/api/agents/run/{inspection_id} (Phase 22 orchestrator)")
    elif agent_key == "vision_agent":
        result = _reference_only(agent_key, "app.ai.inference.LumenAIModel.predict (requires real image bytes)")
    elif agent_key == "simulation_agent":
        result = _reference_only(agent_key, "app.services.simulation_engine_service (requires a real inspection id)")
    elif agent_key == "anatomy_agent":
        result = _reference_only(agent_key, "app.agents.anatomy_agent (Phase 22 pipeline)")
    elif agent_key == "clinical_reasoning_agent":
        result = _reference_only(agent_key, "app.agents.clinical_reasoning_agent (Phase 22 pipeline)")
    elif agent_key == "enterprise_agent":
        result = _reference_only(agent_key, "app.agents.enterprise_agent (Phase 22 pipeline)")
    else:
        raise UnknownAgentInvocationError(f"'{agent_key}' is not a known Core Agent.")

    nova_communication_bus_service.log_message(
        db, tenant_id, source_agent_key="human_request", target_agent_key=logged_target,
        payload={"kwargs": kwargs, "invoked": result.get("invoked", True)},
    )
    return result
