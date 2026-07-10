"""v4.2 — Project Pulse, Section 12: Command Widgets.

`PulseWidget` is a seeded catalog of the nine named reusable widgets;
`PulseDashboardLayout` follows the exact per-user personalization idiom
Genesis's `PlatformFavoriteModule`/`PlatformRecentModule` already
established, applied to widget arrangement instead of module favorites.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.pulse_operations import WIDGET_TYPES, PulseDashboardLayout, PulseWidget

_SEED = {
    "inspection_counter": {"name": "Inspection Counter", "category": "throughput", "data_source": "pulse_kpi_service.live_kpis"},
    "queue_heatmap": {"name": "Queue Heatmap", "category": "throughput", "data_source": "pulse_kpi_service.live_kpis"},
    "facility_status": {"name": "Facility Status", "category": "enterprise", "data_source": "pulse_map_service.command_map"},
    "ai_health": {"name": "AI Health", "category": "ai_ops", "data_source": "pulse_ai_ops_service.ai_operations_monitor"},
    "knowledge_growth": {"name": "Knowledge Growth", "category": "knowledge", "data_source": "sentinel_dashboard_service.knowledge_growth_trend"},
    "digital_twin_status": {"name": "Digital Twin Status", "category": "digital_twin", "data_source": "digital_twin_engine.compute_twin_dashboard"},
    "enterprise_alerts": {"name": "Enterprise Alerts", "category": "alerts", "data_source": "pulse_alert_service.list_alerts"},
    "trend_chart": {"name": "Trend Chart", "category": "analytics", "data_source": "pulse_kpi_service.live_kpis"},
    "forecast_widget": {"name": "Forecast Widget", "category": "analytics", "data_source": "insight_operational_forecast_service.forecast_operational"},
}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _seed_widgets(db: Session) -> None:
    for key in WIDGET_TYPES:
        if db.query(PulseWidget).filter(PulseWidget.widget_key == key).first() is not None:
            continue
        spec = _SEED[key]
        db.add(PulseWidget(widget_key=key, name=spec["name"], category=spec["category"], data_source=spec["data_source"]))
    db.commit()


def list_widgets(db: Session) -> list[dict]:
    _seed_widgets(db)
    return [_row_to_dict(r) for r in db.query(PulseWidget).order_by(PulseWidget.widget_key.asc()).all()]


def get_layout(db: Session, tenant_id: str, actor_email: str, *, is_mobile: bool = False) -> dict:
    row = db.query(PulseDashboardLayout).filter(
        PulseDashboardLayout.tenant_id == tenant_id, PulseDashboardLayout.actor_email == actor_email,
        PulseDashboardLayout.is_mobile_layout == is_mobile,
    ).first()
    if row is None:
        return {"layout": [{"widget_key": key, "x": i % 3, "y": i // 3, "w": 1, "h": 1} for i, key in enumerate(WIDGET_TYPES)], "is_default": True}
    return {"layout": json.loads(row.layout_json), "is_default": False}


def save_layout(db: Session, tenant_id: str, actor_email: str, layout: list[dict], *, is_mobile: bool = False) -> dict:
    for item in layout:
        if item.get("widget_key") not in WIDGET_TYPES:
            raise ValueError(f"widget_key must be one of {WIDGET_TYPES}")

    row = db.query(PulseDashboardLayout).filter(
        PulseDashboardLayout.tenant_id == tenant_id, PulseDashboardLayout.actor_email == actor_email,
        PulseDashboardLayout.is_mobile_layout == is_mobile,
    ).first()
    if row is None:
        row = PulseDashboardLayout(tenant_id=tenant_id, actor_email=actor_email, is_mobile_layout=is_mobile)
        db.add(row)
    row.layout_json = json.dumps(layout)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {"layout": layout, "is_default": False}
