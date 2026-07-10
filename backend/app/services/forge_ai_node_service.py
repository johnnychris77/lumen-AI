"""v4.1 — Project Forge, Section 5: AI Decision Nodes.

Every AI Decision Node dispatches through Genesis's
`platform_intelligence_gateway.py` registry rather than importing each
shared engine ad hoc — this is exactly the discovery mechanism that
gateway was built for ("LumenAI OS integrates with all platform
services, including Inspect, Digital Twin, Knowledge Graph, Sentinel,
Analytics" — Forge's Definition of Done). No engine's logic is
reimplemented here; this module only maps a node's configured
`ai_run_type` to the correct existing engine call.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.workflow_forge import (
    AI_RUN_ANATOMY_MODEL,
    AI_RUN_DETECTION,
    AI_RUN_DIGITAL_TWIN_UPDATE,
    AI_RUN_KNOWLEDGE_GRAPH,
    AI_RUN_PREDICTION_MODEL,
    AI_RUN_RECOMMENDATION_ENGINE,
    AI_RUN_RISK_MODEL,
    AI_RUN_SENTINEL,
    AI_RUN_TYPES,
)
from app.services import platform_intelligence_gateway


class UnknownAIRunTypeError(Exception):
    pass


def run_ai_node(db: Session, tenant_id: str, ai_run_type: str, config: dict) -> dict:
    """Runs one AI Decision Node. `config` carries node-specific
    parameters (e.g. `instrument_type` for a lifecycle forecast). Every
    branch below calls a real, already-existing engine function — never
    a fabricated result."""
    if ai_run_type not in AI_RUN_TYPES:
        raise UnknownAIRunTypeError(f"ai_run_type must be one of {AI_RUN_TYPES}")

    if ai_run_type == AI_RUN_DETECTION:
        # The CV inference gateway (app.cv.pipeline) operates on an uploaded
        # image at capture time, not from a workflow node's own config —
        # a workflow node references the CV result already attached to the
        # inspection rather than re-running inference here.
        return {"ai_run_type": ai_run_type, "note": "Detection runs at capture time via app.cv.pipeline; this node references that result.", "result": config.get("cv_result")}

    if ai_run_type == AI_RUN_ANATOMY_MODEL:
        anatomy_engine = platform_intelligence_gateway.get_shared_service("anatomy_engine")
        return {"ai_run_type": ai_run_type, "result": anatomy_engine.anatomy_risk_dashboard(db, tenant_id)}

    if ai_run_type == AI_RUN_RISK_MODEL:
        spd_risk_engine = platform_intelligence_gateway.get_shared_service("spd_risk_engine")
        instrument_type = config.get("instrument_type", "")
        finding_type = config.get("finding_type", "")
        return {"ai_run_type": ai_run_type, "result": spd_risk_engine.reasoning_chain(instrument_type, finding_type)}

    if ai_run_type == AI_RUN_KNOWLEDGE_GRAPH:
        knowledge_graph = platform_intelligence_gateway.get_shared_service("knowledge_graph")
        category = config.get("category", "instrument")
        query = config.get("query", "")
        return {"ai_run_type": ai_run_type, "result": knowledge_graph.explore(db, tenant_id, category, query=query)}

    if ai_run_type == AI_RUN_RECOMMENDATION_ENGINE:
        engine_name = config.get("engine", "insight")
        recommendation_engine = platform_intelligence_gateway.get_recommendation_engine(engine_name)
        return {"ai_run_type": ai_run_type, "result": recommendation_engine.generate_recommendations(db, tenant_id)}

    if ai_run_type == AI_RUN_PREDICTION_MODEL:
        from app.services import insight_instrument_forecast_service
        instrument_type = config.get("instrument_type", "")
        return {"ai_run_type": ai_run_type, "result": insight_instrument_forecast_service.forecast_instrument_lifecycle(db, tenant_id, instrument_type)}

    if ai_run_type == AI_RUN_SENTINEL:
        sentinel_engine = platform_intelligence_gateway.get_shared_service("sentinel_engine")
        return {"ai_run_type": ai_run_type, "result": sentinel_engine.run_sentinel_scan(db, tenant_id)}

    if ai_run_type == AI_RUN_DIGITAL_TWIN_UPDATE:
        digital_twin_engine = platform_intelligence_gateway.get_shared_service("digital_twin_engine")
        flow = digital_twin_engine.log_instrument_flow(
            tenant_id, config.get("facility_id", ""), config.get("instrument_name", ""),
            config.get("instrument_id", ""), config.get("from_station", ""), config.get("to_station", "inspection"),
            config.get("station_type", "inspection"), config.get("notes", "workflow-triggered update"), db,
        )
        return {"ai_run_type": ai_run_type, "result": {"flow_id": flow.id, "outcome": flow.outcome}}

    raise UnknownAIRunTypeError(f"ai_run_type '{ai_run_type}' is not implemented.")
