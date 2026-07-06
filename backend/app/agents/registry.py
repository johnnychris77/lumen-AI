"""Phase 22 §12 — Agent Registry.

A static registry of every agent in the pipeline: status, version,
capabilities, dependencies, and health. Health is a simple self-check —
these agents are deterministic in-process Python wrapping existing
services, not external calls, so "ok" reflects that the agent's
dependencies (the services/modules it wraps) import successfully, not a
fabricated uptime/latency metric.
"""
from __future__ import annotations

import importlib

from app.agents.anatomy_agent import AnatomyIntelligenceAgent
from app.agents.clinical_reasoning_agent import ClinicalReasoningAgent
from app.agents.contamination_agent import ContaminationDetectionAgent
from app.agents.coverage_agent import InspectionCoverageAgent
from app.agents.damage_agent import DamageDetectionAgent
from app.agents.enterprise_agent import EnterpriseIntelligenceAgent
from app.agents.instrument_agent import InstrumentIntelligenceAgent
from app.agents.learning_agent import ContinuousLearningAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.supervisor_agent import SupervisorAgent

PIPELINE_ORDER = [
    InstrumentIntelligenceAgent,
    AnatomyIntelligenceAgent,
    InspectionCoverageAgent,
    ContaminationDetectionAgent,
    DamageDetectionAgent,
    ClinicalReasoningAgent,
    RecommendationAgent,
    SupervisorAgent,
    ContinuousLearningAgent,
    EnterpriseIntelligenceAgent,
]

# Modules each agent wraps — used for the registry's health self-check.
_WRAPPED_MODULES = {
    "Instrument Intelligence Agent": "app.services.instrument_anatomy",
    "Anatomy Intelligence Agent": "app.services.instrument_anatomy",
    "Inspection Coverage Agent": "app.services.inspection_coverage",
    "Contamination Detection Agent": "app.services.clinical_mentor",
    "Damage Detection Agent": "app.services.pre_sterilization_command_center_service",
    "Clinical Reasoning Agent": "app.services.knowledge_graph_service",
    "Recommendation Agent": "app.services.pre_sterilization_command_center_service",
    "Supervisor Agent": "app.models.supervisor_review",
    "Continuous Learning Agent": "app.services.knowledge_graph_service",
    "Enterprise Intelligence Agent": "app.services.knowledge_graph_service",
}


def _health(agent_name: str) -> str:
    module_path = _WRAPPED_MODULES.get(agent_name)
    if not module_path:
        return "unknown"
    try:
        importlib.import_module(module_path)
        return "ok"
    except Exception:
        return "degraded"


def get_registry() -> list[dict]:
    entries = []
    for i, agent_cls in enumerate(PIPELINE_ORDER):
        entries.append({
            "name": agent_cls.NAME,
            "version": agent_cls.VERSION,
            "capabilities": agent_cls.CAPABILITIES,
            "depends_on": agent_cls.DEPENDS_ON,
            "pipeline_position": i + 1,
            "status": "active",
            "health": _health(agent_cls.NAME),
        })
    return entries
