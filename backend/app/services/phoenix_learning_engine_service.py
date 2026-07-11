"""v4.9 — Project Phoenix, Section 1: Phoenix Learning Engine.

The `/phoenix` dashboard's umbrella composition — continuously analyzes
inspection outcomes, AI confidence, supervisor overrides, knowledge
usage, workflow efficiency, Digital Twin health, enterprise trends, and
education effectiveness by composing the real outputs of every other
Phoenix engine plus `quality_command_center_service` (Guardian, v2.9) and
`vanguard_executive_intelligence_service` (v4.6) — nothing here is
re-derived, and nothing here modifies production; it only reads.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.phoenix_intelligence import DISCLAIMER
from app.services import (
    phoenix_ai_observatory_service,
    phoenix_platform_health_service,
    phoenix_workflow_optimization_service,
    quality_command_center_service,
    vanguard_executive_intelligence_service,
)
from app.services.knowledge_analytics_service import knowledge_analytics


def learning_engine_summary(db: Session, tenant_id: str) -> dict:
    command_center = quality_command_center_service.quality_command_center_summary(db, tenant_id)
    ai_observatory = phoenix_ai_observatory_service.observatory_summary(db, tenant_id)
    knowledge = knowledge_analytics(db, tenant_id)
    workflow = phoenix_workflow_optimization_service.workflow_optimization_summary(db, tenant_id)
    digital_twin = phoenix_platform_health_service.compute_digital_twin_health_score(db, tenant_id)
    enterprise = vanguard_executive_intelligence_service.executive_intelligence_center(db, tenant_id)

    return {
        "inspection_outcomes": {
            "quality_events": command_center["quality_events"],
            "recurring_findings": command_center["recurring_findings"],
            "capas": command_center["capas"],
        },
        "ai_confidence": {
            "ai_confidence_avg": ai_observatory["ai_confidence_avg"],
            "confidence_calibration": ai_observatory["confidence_calibration"],
            "model_drift_detected": ai_observatory["model_drift_detected"],
        },
        "supervisor_overrides": {
            "supervisor_override_rate": ai_observatory["supervisor_override_rate"],
            "human_agreement_rate": ai_observatory["human_agreement_rate"],
        },
        "knowledge_usage": {
            "most_viewed_articles": knowledge["most_viewed_articles"],
            "most_common_questions": knowledge["most_common_questions"],
            "knowledge_gaps": knowledge["knowledge_gaps"],
        },
        "workflow_efficiency": workflow["duration_analysis"],
        "digital_twin_health": digital_twin,
        "enterprise_trends": {
            "enterprise_readiness": enterprise.get("enterprise_readiness"),
            "enterprise_risk": enterprise.get("enterprise_risk"),
            "knowledge_growth": enterprise.get("knowledge_growth"),
        },
        "education_effectiveness": {
            "education_impact_avg_pct": command_center["education_impact_avg_pct"],
            "technician_trends": command_center["technician_trends"],
        },
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
