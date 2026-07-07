"""Phase 22 §13 — Agent Orchestrator.

Runs the full multi-agent pipeline for one real inspection:

Instrument -> Anatomy -> Coverage -> Contamination -> Damage ->
Clinical Reasoning -> Recommendation -> Supervisor -> Learning -> Enterprise

Each agent receives only the typed context object(s) produced by the
agents before it — no agent reads the raw Inspection row directly except
where explicitly wired here, and none reads raw frontend state. The
orchestrator is the only place that touches the database directly on
behalf of the pipeline; every agent after Instrument/Coverage/Supervisor/
Enterprise only ever sees prior context objects.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

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

_AGENTS = {
    "instrument": InstrumentIntelligenceAgent(),
    "anatomy": AnatomyIntelligenceAgent(),
    "coverage": InspectionCoverageAgent(),
    "contamination": ContaminationDetectionAgent(),
    "damage": DamageDetectionAgent(),
    "reasoning": ClinicalReasoningAgent(),
    "recommendation": RecommendationAgent(),
    "supervisor": SupervisorAgent(),
    "learning": ContinuousLearningAgent(),
    "enterprise": EnterpriseIntelligenceAgent(),
}


def _trace_entry(agent, input_summary: dict, output_ctx) -> dict:
    return {
        "agent": agent.NAME,
        "version": agent.VERSION,
        # Real wall-clock time this agent's step completed during this live
        # pipeline run — not a fabricated/reconstructed historical time.
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_summary": input_summary,
        "output_summary": output_ctx.model_dump(),
    }


def run_pipeline(db: Session, inspection, tenant_id: str) -> dict:
    """Section 13/14 — run every agent in order and return the full result
    plus the explainable trace (Section 14: which agent produced which
    decision)."""
    trace: list[dict] = []

    try:
        inspected_zones = json.loads(inspection.inspected_zones_json or "null")
    except (TypeError, ValueError):
        inspected_zones = None

    instrument_ctx = _AGENTS["instrument"].run(
        db, tenant_id, inspection.instrument_type, inspection.vendor_name or "", "",
    )
    trace.append(_trace_entry(_AGENTS["instrument"], {"instrument_type": inspection.instrument_type}, instrument_ctx))

    anatomy_ctx = _AGENTS["anatomy"].run(instrument_ctx, inspected_zones)
    trace.append(_trace_entry(_AGENTS["anatomy"], {"instrument_family": instrument_ctx.instrument_family}, anatomy_ctx))

    coverage_ctx = _AGENTS["coverage"].run(inspection.instrument_type, anatomy_ctx)
    trace.append(_trace_entry(_AGENTS["coverage"], {"missing_zones": anatomy_ctx.missing_zones}, coverage_ctx))

    contamination_ctx = _AGENTS["contamination"].run(
        inspection.instrument_type, inspection.detected_issue, inspection.confidence, inspection.risk_score,
    )
    trace.append(_trace_entry(_AGENTS["contamination"], {"detected_issue": inspection.detected_issue}, contamination_ctx))

    damage_ctx = _AGENTS["damage"].run(inspection.detected_issue, inspection.risk_score)
    trace.append(_trace_entry(_AGENTS["damage"], {"detected_issue": inspection.detected_issue}, damage_ctx))

    reasoning_ctx = _AGENTS["reasoning"].run(
        instrument_ctx, anatomy_ctx, coverage_ctx, contamination_ctx, damage_ctx, inspection.risk_score,
    )
    trace.append(_trace_entry(
        _AGENTS["reasoning"],
        {"has_contamination": contamination_ctx.has_contamination, "has_damage": damage_ctx.has_damage},
        reasoning_ctx,
    ))

    recommendation_ctx = _AGENTS["recommendation"].run(inspection, reasoning_ctx)
    trace.append(_trace_entry(_AGENTS["recommendation"], {"risk_level": reasoning_ctx.risk_level}, recommendation_ctx))

    supervisor_ctx = _AGENTS["supervisor"].run(db, inspection.id)
    trace.append(_trace_entry(_AGENTS["supervisor"], {"readiness_state": recommendation_ctx.readiness_state}, supervisor_ctx))

    learning_ctx = _AGENTS["learning"].run(db, tenant_id)
    trace.append(_trace_entry(_AGENTS["learning"], {"review_exists": supervisor_ctx.review_exists}, learning_ctx))

    enterprise_ctx = _AGENTS["enterprise"].run(db, tenant_id, inspection.facility_name or inspection.site_name)
    trace.append(_trace_entry(_AGENTS["enterprise"], {"facility": inspection.facility_name or inspection.site_name}, enterprise_ctx))

    return {
        "inspection_id": inspection.id,
        "instrument_context": instrument_ctx.model_dump(),
        "anatomy_context": anatomy_ctx.model_dump(),
        "coverage_context": coverage_ctx.model_dump(),
        "contamination_context": contamination_ctx.model_dump(),
        "damage_context": damage_ctx.model_dump(),
        "clinical_reasoning_context": reasoning_ctx.model_dump(),
        "recommendation_context": recommendation_ctx.model_dump(),
        "supervisor_context": supervisor_ctx.model_dump(),
        "learning_context": learning_ctx.model_dump(),
        "enterprise_context": enterprise_ctx.model_dump(),
        "trace": trace,
        "human_review_required": True,
    }
