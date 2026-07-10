"""v4.2 — Project Pulse, Section 6: Executive Command Dashboard.

A pure composition of scores that already exist across prior sprints —
no score is recomputed here. "Enterprise Score"/"Risk Score" both read
`sentinel_dashboard_service.run_sentinel_health_snapshot`'s single
canonical `enterprise_risk_score` (confirmed: Atlas's own dashboard
already reads this same field rather than recomputing it, so Pulse
follows the same reuse path). Every score updates dynamically simply
because this function re-queries real rows on every call — there is no
stale cache to invalidate.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.predictive_insight import FORECAST_INSPECTION_WORKLOAD, HORIZON_7_DAY
from app.services import competency_service, digital_twin_engine, knowledge_graph_service, sentinel_dashboard_service
from app.services.insight_operational_forecast_service import forecast_operational
from app.services.nexus_registry_service import list_connectors


def executive_command_dashboard(db: Session, tenant_id: str, *, facility_id: str = "") -> dict:
    health_snapshot = sentinel_dashboard_service.run_sentinel_health_snapshot(db, tenant_id)
    quality_score = health_snapshot.get("risk_score_breakdown", {}).get("quality_score_used")
    education = competency_service.technician_quality_dashboard(db, tenant_id)
    knowledge = knowledge_graph_service.learning_confidence(db, tenant_id)
    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db)
    connectors = list_connectors(db, tenant_id)

    integration_health_pct = None
    if connectors:
        active = sum(1 for c in connectors if c.get("status") == "active")
        integration_health_pct = round(100 * active / len(connectors), 1)

    forecast_summary: dict | None = None
    try:
        forecast_summary = forecast_operational(db, tenant_id, forecast_type=FORECAST_INSPECTION_WORKLOAD, horizon=HORIZON_7_DAY)
    except Exception:
        forecast_summary = None

    education_scores = [t.get("training_progress_pct") for t in education.get("technicians", []) if t.get("training_progress_pct") is not None]
    education_health_pct = round(sum(education_scores) / len(education_scores), 1) if education_scores else None

    return {
        "enterprise_score": health_snapshot.get("enterprise_risk_score"),
        "quality_score": quality_score,
        "risk_score": health_snapshot.get("enterprise_risk_score"),
        "operational_health_pct": twin_dashboard.twin_state.utilization_pct,
        "education_health_pct": education_health_pct,
        "knowledge_health_pct": knowledge.get("knowledge_confidence"),
        "digital_twin_health_pct": twin_dashboard.twin_state.utilization_pct,
        "integration_health_pct": integration_health_pct,
        "forecast_summary": forecast_summary,
        "human_review_required": True,
    }
