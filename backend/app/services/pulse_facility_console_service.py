"""v4.2 — Project Pulse, Section 9: Facility Command Console.

Composes what already exists, scoped to one facility's tenant: Atlas's
facility intelligence, Pulse's own KPIs/alerts/notifications/activity
feed, and Sentinel's AI health — no new per-facility store.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.services import (
    platform_activity_feed_service,
    platform_notification_service,
    pulse_alert_service,
    pulse_kpi_service,
)


def facility_console(db: Session, tenant_id: str) -> dict:
    kpis = pulse_kpi_service.live_kpis(db, tenant_id)
    alerts = pulse_alert_service.list_alerts(db, tenant_id, status="active")
    notifications = platform_notification_service.unified_notifications(db, tenant_id, limit=20)
    activity = platform_activity_feed_service.universal_activity_feed(db, tenant_id, limit=20)

    inspection_status_counts: dict[str, int] = {}
    for row in db.query(Inspection.status).filter(Inspection.tenant_id == tenant_id).all():
        inspection_status_counts[row[0]] = inspection_status_counts.get(row[0], 0) + 1

    return {
        "tenant_id": tenant_id,
        "kpis": kpis,
        "inspection_status_counts": inspection_status_counts,
        "alerts": alerts,
        "notifications": notifications,
        "recent_activity": activity,
        "human_review_required": True,
    }
