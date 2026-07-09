"""v3.0 — Project Sentinel, Section 1: Sentinel Intelligence Engine.

The orchestration entry point — one call that runs every monitor in
sequence and returns a summary. Each monitor is independently callable
(and independently tested); this just sequences them the way a scheduled
job would: detect risk -> refresh watchlists -> monitor digital twins ->
compute AI health -> generate alerts -> generate recommendations.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    sentinel_alert_service,
    sentinel_dashboard_service,
    sentinel_digital_twin_monitor_service,
    sentinel_recommendation_service,
    sentinel_risk_monitor_service,
    sentinel_watchlist_service,
)


def run_sentinel_scan(db: Session, tenant_id: str) -> dict:
    """Monitors: inspection workflows (via risk signals), Digital Twins,
    Knowledge Graph/AI confidence (via the health snapshot), supervisor
    overrides and recurring findings (via risk signals), anatomy trends
    (via watchlists), and enterprise KPIs (via the health snapshot)."""
    risk_signals = sentinel_risk_monitor_service.detect_risk_signals(db, tenant_id)
    watchlist = sentinel_watchlist_service.refresh_watchlists(db, tenant_id)
    twin_flags = sentinel_digital_twin_monitor_service.monitor_digital_twins(db, tenant_id)
    health_snapshot = sentinel_dashboard_service.run_sentinel_health_snapshot(db, tenant_id)
    alerts = sentinel_alert_service.generate_enterprise_alerts(db, tenant_id)
    recommendations = sentinel_recommendation_service.generate_recommendations(db, tenant_id)

    return {
        "risk_signals_count": len(risk_signals),
        "watchlist_count": len(watchlist),
        "digital_twin_flags_count": len(twin_flags),
        "alerts_count": len(alerts),
        "recommendations_count": len(recommendations),
        "enterprise_risk_score": health_snapshot["enterprise_risk_score"],
        "human_review_required": True,
    }
