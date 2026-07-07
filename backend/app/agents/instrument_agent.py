"""Phase 22 §1 — Instrument Intelligence Agent.

Identifies manufacturer/family/model/category and loads the anatomy
profile, inspection requirements, high-risk zones, IFU reference, and
digital-twin availability. Wraps existing structured knowledge
(instrument_anatomy.py) and real DB rows — introduces no new detection
logic.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.context import InstrumentContext
from app.services.instrument_anatomy import anatomy_profile


class InstrumentIntelligenceAgent:
    NAME = "Instrument Intelligence Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["resolve_instrument_family", "load_anatomy_profile", "check_digital_twin_availability"]
    DEPENDS_ON: list[str] = []

    def run(self, db: Session, tenant_id: str, instrument_type: str, manufacturer: str = "", model: str = "") -> InstrumentContext:
        from app.models.digital_quality_twin import QualityTwinState
        from app.models.instrument_knowledge import InstrumentKnowledge

        profile = anatomy_profile(instrument_type, manufacturer=manufacturer, model=model)
        has_twin = db.query(QualityTwinState.id).filter(QualityTwinState.tenant_id == tenant_id).first() is not None

        ifu_reference = ""
        if manufacturer and model:
            knowledge = (
                db.query(InstrumentKnowledge)
                .filter(
                    InstrumentKnowledge.tenant_id == tenant_id,
                    InstrumentKnowledge.manufacturer == manufacturer,
                    InstrumentKnowledge.model == model,
                )
                .first()
            )
            if knowledge:
                ifu_reference = knowledge.ifu_reference

        return InstrumentContext(
            instrument_type=instrument_type,
            manufacturer=manufacturer,
            model=model,
            instrument_family=profile["instrument_family"],
            instrument_category=profile["category"],
            anatomy_zones=profile["anatomy_zones"],
            high_risk_zones=profile["high_risk_zones"],
            ifu_reference=ifu_reference,
            digital_twin_available=has_twin,
            profile_found=profile["profile_found"],
            warning=profile["warning"],
        )
