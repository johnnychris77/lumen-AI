"""Phase 22 §6 — Clinical Reasoning Agent.

Consumes Instrument, Anatomy, Coverage, and Findings (Contamination +
Damage) context, plus the knowledge graph, and produces a clinical
interpretation, a traceable reasoning chain, and a risk assessment. Wraps
app/services/knowledge_graph_service.py — introduces no new reasoning
logic of its own.
"""
from __future__ import annotations

from app.agents.context import (
    AnatomyContext,
    ClinicalReasoningContext,
    ContaminationContext,
    CoverageContext,
    DamageContext,
    InstrumentContext,
)
from app.services.knowledge_graph_service import reasoning_chain


class ClinicalReasoningAgent:
    NAME = "Clinical Reasoning Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["synthesize_clinical_interpretation", "build_reasoning_chain", "assess_risk"]
    DEPENDS_ON = [
        "InstrumentIntelligenceAgent", "AnatomyIntelligenceAgent", "InspectionCoverageAgent",
        "ContaminationDetectionAgent", "DamageDetectionAgent",
    ]

    def run(
        self,
        instrument_ctx: InstrumentContext,
        anatomy_ctx: AnatomyContext,
        coverage_ctx: CoverageContext,
        contamination_ctx: ContaminationContext,
        damage_ctx: DamageContext,
        risk_score: int,
    ) -> ClinicalReasoningContext:
        if not contamination_ctx.findings and not damage_ctx.findings:
            interpretation = (
                f"No contamination or damage findings on this {instrument_ctx.instrument_type}. "
                f"Coverage: {coverage_ctx.coverage_quality}."
            )
            chain: list[dict] = []
        else:
            primary = contamination_ctx.findings[0] if contamination_ctx.findings else None
            chain_result = reasoning_chain(
                instrument_ctx.instrument_type,
                primary.finding_type if primary else damage_ctx.findings[0].finding_type,
                manufacturer=instrument_ctx.manufacturer,
                model=instrument_ctx.model,
            )
            chain = chain_result["chain"]
            interpretation = chain_result["narrative"]

        risk_level = "low"
        if risk_score >= 85:
            risk_level = "critical"
        elif risk_score >= 70:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"

        return ClinicalReasoningContext(
            interpretation=interpretation,
            reasoning_chain=chain,
            risk_level=risk_level,
            risk_score=risk_score,
        )
