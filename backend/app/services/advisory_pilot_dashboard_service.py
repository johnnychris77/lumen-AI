"""Advisor — Phase 7 §9: Pilot Dashboard.

Composes the other Advisor services rather than recomputing any of their
metrics — the same composition-not-duplication pattern Shadow's
``shadow_reports.py`` established.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import advisory_recommendation_service, advisory_safety_service, advisory_workflow_impact_service
from app.services import pilot_service


def pilot_dashboard(db: Session, tenant_id: str, *, model_id: str | None = None, facility_id: str = "") -> dict[str, Any]:
    """§9 — the full pilot dashboard payload."""
    interactions = advisory_recommendation_service.list_interactions(db, tenant_id, model_id=model_id)
    impact = advisory_workflow_impact_service.impact_summary(db, tenant_id, interactions, model_id=model_id)
    return {
        "pilot_status": pilot_service.get_pilot_status(db, tenant_id, facility_id) if facility_id else None,
        "inspection_volume": impact["adoption"]["total_eligible_inspections"],
        "adoption": impact["adoption"],
        "acceptance_rate": impact["acceptance_and_override"]["acceptance_rate"],
        "override_rate": impact["acceptance_and_override"]["override_rate"],
        "performance_trends": impact["quality_dashboard"],
        "safety_events": advisory_safety_service.safety_summary(db, tenant_id),
        "operational_impact": impact["turnaround"],
        "human_review_required": True,
    }
