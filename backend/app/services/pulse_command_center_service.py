"""v4.2 — Project Pulse, Section 1: Pulse Command Center.

Composes the fourteen named live widgets entirely from services that
already exist across prior sprints (Sentinel, Atlas, Genesis, Forge) or
from this sprint's own new modules (`pulse_kpi_service`,
`pulse_alert_service`, `pulse_ai_ops_service`) — no widget here
recomputes a score another module already owns.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    digital_twin_engine,
    knowledge_graph_service,
    platform_activity_feed_service,
    platform_module_registry_service,
    platform_notification_service,
    platform_org_service,
    pulse_ai_ops_service,
    pulse_alert_service,
    pulse_kpi_service,
    sentinel_dashboard_service,
)
from app.services.nexus_registry_service import list_connectors


def pulse_command_center(db: Session, tenant_id: str, *, role: str = "") -> dict:
    kpis = pulse_kpi_service.live_kpis(db, tenant_id)
    health_snapshot = sentinel_dashboard_service.run_sentinel_health_snapshot(db, tenant_id)
    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, "", db)
    kg = knowledge_graph_service.learning_confidence(db, tenant_id)
    ai_ops = pulse_ai_ops_service.ai_operations_monitor(db, tenant_id)
    active_alerts = pulse_alert_service.list_alerts(db, tenant_id, status="active")
    connectors = list_connectors(db, tenant_id)
    modules = platform_module_registry_service.list_modules(db)
    notifications = platform_notification_service.unified_notifications(db, tenant_id, recipient_role=role, limit=15)
    activity = platform_activity_feed_service.universal_activity_feed(db, tenant_id, limit=15)
    facility = platform_org_service.facility_for_tenant(db, tenant_id)

    return {
        "enterprise_health": {
            "enterprise_risk_score": health_snapshot.get("enterprise_risk_score"),
            "drift_detected": health_snapshot.get("drift_detected"),
        },
        "facility_health": facility,
        "inspection_queue": {"pending": kpis["ai_analysis_queue_length"], "throughput_24h": kpis["inspection_throughput"]},
        "ai_analysis_queue": {"pending": kpis["ai_analysis_queue_length"], "avg_inference_time_ms": ai_ops["avg_inference_time_ms"]},
        "supervisor_queue": {"backlog": kpis["supervisor_backlog"], "avg_review_time_minutes": kpis["avg_review_time_minutes"]},
        "repair_queue": {"open": kpis["repair_queue_length"]},
        "enterprise_alerts": active_alerts[:10],
        "digital_twin_health": {"utilization_pct": twin_dashboard.twin_state.utilization_pct, "bottleneck_station": twin_dashboard.twin_state.bottleneck_station},
        "knowledge_growth": {"knowledge_confidence": kg.get("knowledge_confidence"), "recent_contributions": kpis["knowledge_contributions_recent"]},
        "ai_model_health": ai_ops,
        "system_status": {"modules_registered": len(modules), "modules": [m["module_key"] for m in modules]},
        "integrations": connectors,
        "notifications": notifications,
        "recent_activity": activity,
        "human_review_required": True,
    }
