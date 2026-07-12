"""Project Maestro, Sections 1 & 9: Operational Orchestrator & Leadership
Workspace.

This is the single top-level entry point that composes every other
Maestro service (priority engine, recommendation engine, health index,
timeline) plus a handful of specialists' own summaries (Sentinel-X,
Pulse) into the one leadership view the brief calls for: "What should I do
first today, and why?" Nothing here is computed fresh -- it is a pure
read-and-synthesize layer, exactly like every other Maestro module.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.maestro_orchestration import BRIEF_MORNING, DECISION_STATUS_PENDING, DISCLAIMER, TIMELINE_TODAY
from app.services import (
    maestro_daily_brief_service,
    maestro_priority_engine_service,
    maestro_recommendation_engine_service,
)
from app.services.maestro_health_index_service import compute_operational_health, to_dict as health_to_dict
from app.services.sentinelx_dashboard_service import risk_dashboard_summary
from app.services.sentinelx_patient_safety_watch_service import list_alerts
from app.services.sentinelx_supervisor_workspace_service import supervisor_workspace_summary


def run_daily_orchestration(db: Session, tenant_id: str) -> dict:
    """Section 1: the Operational Orchestrator's main run -- ranks
    priorities, derives leadership recommendations (both specific and
    strategic), refreshes the Operational Health Index, and generates the
    morning brief. Intended to be triggered once per day (or on demand)
    per tenant; every downstream artifact this produces is independently
    queryable afterward."""
    priority_items = maestro_priority_engine_service.compute_priorities(db, tenant_id)
    specific_recommendations = maestro_recommendation_engine_service.generate_recommendations(db, tenant_id)
    strategic_recommendations = maestro_recommendation_engine_service.generate_strategic_recommendations(db, tenant_id)
    health = compute_operational_health(db, tenant_id)
    brief = maestro_daily_brief_service.generate_brief(db, tenant_id, BRIEF_MORNING)

    return {
        "priority_item_count": len(priority_items),
        "recommendation_count": len(specific_recommendations) + len(strategic_recommendations),
        "operational_health": health_to_dict(health),
        "daily_brief": maestro_daily_brief_service.to_dict(brief),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def leadership_workspace_summary(db: Session, tenant_id: str) -> dict:
    """Section 9: the `/maestro` Leadership Workspace payload -- Top
    Priorities, Operational Health, Open Risks, Today's Recommendations,
    Pending Executive Decisions, Shift Readiness, and Enterprise Status."""
    top_priorities = maestro_priority_engine_service.latest_priorities(db, tenant_id)

    health = health_to_dict(compute_operational_health(db, tenant_id))

    dashboard = risk_dashboard_summary(db, tenant_id)
    open_risks = {
        "enterprise_risk": dashboard["enterprise_risk"],
        "top_facility_risk": (dashboard["facility_risk"][:3]),
        "top_anatomy_risk": (dashboard["anatomy_risk"][:3]),
    }

    todays_recommendations = maestro_recommendation_engine_service.list_recommendations(
        db, tenant_id, status=DECISION_STATUS_PENDING, timeline_horizon=TIMELINE_TODAY,
    )
    pending_executive_decisions = maestro_recommendation_engine_service.list_recommendations(
        db, tenant_id, status=DECISION_STATUS_PENDING,
    )

    workspace = supervisor_workspace_summary(db, tenant_id, limit=10)
    open_alerts = list_alerts(db, tenant_id, acknowledged=False)
    shift_readiness = {
        "pending_reviews": len(workspace["pending_reviews"]),
        "open_patient_safety_alerts": len(open_alerts),
        "escalating_trends": workspace["escalating_trends"],
    }

    enterprise_status = {
        "overall_operational_health": health.get("overall_score"),
        "average_risk_score": dashboard["enterprise_risk"].get("average_risk_score"),
        "high_or_critical_risk_pct": dashboard["enterprise_risk"].get("high_or_critical_pct"),
    }

    return {
        "top_priorities": top_priorities[:9],
        "operational_health": health,
        "open_risks": open_risks,
        "todays_recommendations": todays_recommendations,
        "pending_executive_decisions": pending_executive_decisions[:20],
        "shift_readiness": shift_readiness,
        "enterprise_status": enterprise_status,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
