"""Phase 22 §3 — Inspection Coverage Agent.

Consumes the Anatomy Context and produces coverage %, missing images, and
capture guidance ("Upload O-ring image.", "Capture hinge close-up.").
Wraps app/services/inspection_coverage.py — introduces no new coverage
logic of its own.
"""
from __future__ import annotations

from app.agents.context import AnatomyContext, CoverageContext
from app.services.inspection_coverage import compute_coverage, missing_image_guidance


class InspectionCoverageAgent:
    NAME = "Inspection Coverage Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["compute_coverage_percent", "generate_capture_guidance"]
    DEPENDS_ON = ["AnatomyIntelligenceAgent"]

    def run(self, instrument_type: str, anatomy_ctx: AnatomyContext) -> CoverageContext:
        coverage = compute_coverage(instrument_type, anatomy_ctx.inspected_zones)
        guidance = missing_image_guidance(instrument_type, anatomy_ctx.inspected_zones)

        return CoverageContext(
            coverage_pct=coverage["overall_coverage"],
            required_images=coverage["required_zones"],
            missing_images=coverage["missing"],
            coverage_quality=coverage["quality"],
            capture_guidance=guidance,
        )
