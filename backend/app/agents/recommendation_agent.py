"""Phase 22 §7 — Recommendation Agent.

Produces one of: READY FOR PACKAGING, REQUIRES RECLEANING, REQUIRES
SUPERVISOR REVIEW, REQUIRES REPAIR, REMOVED FROM SERVICE, PENDING
ANALYSIS — the same six readiness states already defined in
app/services/pre_sterilization_command_center_service.py (Phase 20),
reused here rather than re-invented. Explains every recommendation using
the Clinical Reasoning Agent's interpretation.
"""
from __future__ import annotations

from app.agents.context import ClinicalReasoningContext, RecommendationContext
from app.services.pre_sterilization_command_center_service import classify_readiness


class RecommendationAgent:
    NAME = "Recommendation Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["classify_packaging_readiness", "explain_recommendation"]
    DEPENDS_ON = ["ClinicalReasoningAgent"]

    def run(self, inspection, reasoning_ctx: ClinicalReasoningContext) -> RecommendationContext:
        classified = classify_readiness(inspection)
        explanation = reasoning_ctx.interpretation or (
            f"Readiness state {classified['readiness_state']} determined from the persisted "
            f"scoring outcome; no additional findings narrative available."
        )
        return RecommendationContext(
            readiness_state=classified["readiness_state"],
            repair_candidate=classified["repair_candidate"],
            explanation=explanation,
            human_review_required=True,
        )
