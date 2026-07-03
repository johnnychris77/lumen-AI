"""Phase 22 §2 — Anatomy Intelligence Agent.

Consumes the Instrument Context and determines anatomy zones, required
image views, high-retention areas, and which zones were actually inspected
vs. missing. Wraps app/services/instrument_zones.py's high-retention
taxonomy — introduces no new zone-assignment logic.
"""
from __future__ import annotations

from app.agents.context import AnatomyContext, InstrumentContext
from app.services.instrument_anatomy import get_anatomy


class AnatomyIntelligenceAgent:
    NAME = "Anatomy Intelligence Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["resolve_required_zones", "determine_missing_zones", "score_inspection_completeness"]
    DEPENDS_ON = ["InstrumentIntelligenceAgent"]

    def run(self, instrument_ctx: InstrumentContext, inspected_zones: list[str] | None) -> AnatomyContext:
        anatomy = get_anatomy(instrument_ctx.instrument_type)
        required = anatomy["required_images"]

        if inspected_zones is None:
            return AnatomyContext(
                instrument_family=instrument_ctx.instrument_family,
                anatomy_zones=anatomy["zone_names"],
                required_zones=required,
                high_retention_zones=instrument_ctx.high_risk_zones,
                inspected_zones=None,
                missing_zones=required,
                inspection_completeness=None,
            )

        inspected_norm = {z.strip().lower() for z in inspected_zones}
        missing = [z for z in required if z.lower() not in inspected_norm]
        completeness = round(100 * (len(required) - len(missing)) / len(required)) if required else 100

        return AnatomyContext(
            instrument_family=instrument_ctx.instrument_family,
            anatomy_zones=anatomy["zone_names"],
            required_zones=required,
            high_retention_zones=instrument_ctx.high_risk_zones,
            inspected_zones=inspected_zones,
            missing_zones=missing,
            inspection_completeness=completeness,
        )
