"""Phase 22 §10 — Enterprise Intelligence Agent.

Aggregates hospital/market/manufacturer/instrument/failure-mode data for
executive dashboards, ROI, and benchmarking. Wraps
app/services/pre_sterilization_command_center_service.py and
app/services/knowledge_graph_service.py's enterprise analytics — this
agent composes existing aggregation, it does not recompute new figures.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.context import EnterpriseContext
from app.db import models
from app.services.knowledge_graph_service import enterprise_knowledge_analytics
from app.services.pre_sterilization_command_center_service import _annotate, _reviewed_ids, facility_readiness


class EnterpriseIntelligenceAgent:
    NAME = "Enterprise Intelligence Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["aggregate_facility_readiness", "aggregate_findings_by_manufacturer", "aggregate_contamination_types"]
    DEPENDS_ON = ["ContinuousLearningAgent"]

    def run(self, db: Session, tenant_id: str, facility: str | None = None) -> EnterpriseContext:
        analytics = enterprise_knowledge_analytics(db, tenant_id)

        cases = (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == tenant_id)
            .order_by(models.Inspection.created_at.desc())
            .limit(5000)
            .all()
        )
        reviewed_ids = _reviewed_ids(db, tenant_id)
        annotated = _annotate(cases, reviewed_ids)
        facilities = facility_readiness(annotated)
        facility_rate = None
        if facility:
            match = next((f for f in facilities if f["facility"] == facility), None)
            facility_rate = match["readiness_rate"] if match else None

        return EnterpriseContext(
            facility=facility,
            facility_readiness_rate=facility_rate,
            most_common_contamination_type=analytics["most_common_contamination_type"],
            highest_risk_anatomy_zone=analytics["highest_risk_anatomy_zone"],
            note="Aggregated from real Inspection/SupervisorReview/PilotValidationCase rows for this tenant.",
        )
