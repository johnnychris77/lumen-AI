from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db import models
from app.governance_sla import sla_dashboard
from app.governance_sla_scanner import scanner_recommendations, run_scanner_once
from app.release_governance_dashboard import dashboard_summary, exceptions, packet_status


def _now():
    return datetime.now(timezone.utc).isoformat()


def recommended_action(item: dict) -> str:
    state = item.get("readiness_state", "")
    release_status = item.get("release_status", "")
    delivery_status = item.get("delivery_status", "")

    if item.get("holds"):
        return "Review active hold. Clear hold or create emergency override if release is urgent."
    if item.get("override"):
        return "Emergency override is active. Confirm documentation and monitor delivery."
    if release_status == "missing":
        return "Request packet release approval."
    if release_status == "pending":
        return "Approve, reject, or request correction for the pending release."
    if release_status == "rejected":
        return "Regenerate or revise packet, then request release again."
    if delivery_status == "failed":
        return "Check delivery channel, target recipients, and notification configuration."
    if delivery_status == "blocked":
        return "Review release governance and distribution list approval requirements."
    if state == "ready":
        return "Packet is ready for approved delivery."
    return "Review packet governance status."


def build_work_items(db: Session, tenant_id: str, tenant_name: str) -> dict:
    release_exceptions = exceptions(db, tenant_id)
    sla_recs = scanner_recommendations(tenant_id, tenant_name)

    items = []

    for item in release_exceptions.get("items", []):
        items.append({
            "source": "release_governance",
            "resource_type": "leadership_packet",
            "resource_id": item.get("packet_id"),
            "title": item.get("title"),
            "severity": "critical" if item.get("holds") else "warning",
            "status": item.get("readiness_state"),
            "reason": item.get("reason"),
            "recommended_action": recommended_action(item),
            "details": item,
        })

    for item in sla_recs.get("items", []):
        items.append({
            "source": "governance_sla",
            "resource_type": item.get("resource_type"),
            "resource_id": item.get("resource_id"),
            "title": f"SLA: {item.get('policy_key')}",
            "severity": item.get("severity"),
            "status": "open",
            "reason": f"Open SLA event aged {item.get('age_hours')} hours",
            "recommended_action": item.get("recommendation"),
            "details": item,
        })

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "generated_at": _now(),
        "count": len(items),
        "items": items,
    }


def command_center_summary(db: Session, tenant_id: str, tenant_name: str) -> dict:
    release = dashboard_summary(db, tenant_id, tenant_name)
    sla = sla_dashboard(db, tenant_id, tenant_name)
    work = build_work_items(db, tenant_id, tenant_name)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "generated_at": _now(),
        "release_governance": {
            "exception_count": release.get("exception_count", 0),
            "readiness_counts": release.get("readiness_counts", {}),
        },
        "sla": {
            "open_count": sla.get("open_count", 0),
            "counts": sla.get("counts", {}),
        },
        "work_items": {
            "count": work["count"],
            "critical_count": sum(1 for x in work["items"] if x.get("severity") == "critical"),
            "warning_count": sum(1 for x in work["items"] if x.get("severity") == "warning"),
            "items": work["items"][:20],
        },
    }


def resolve_sla_event(db: Session, tenant_id: str, event_id: int, notes: str) -> dict:
    row = (
        db.query(models.GovernanceSlaEvent)
        .filter(
            models.GovernanceSlaEvent.id == event_id,
            models.GovernanceSlaEvent.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        return {"resolved": False, "reason": "SLA event not found"}

    row.status = "resolved"
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "resolved": True,
        "event_id": row.id,
        "status": row.status,
        "notes": notes,
    }


def run_command_center_scan() -> dict:
    return run_scanner_once()
