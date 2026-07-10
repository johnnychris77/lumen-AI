"""v4.0 — LumenAI OS (Project Genesis), Section 6: Universal Activity Feed.

Composes this platform's existing single `AuditLog` table
(`app/audit.py::log_audit_event`, already written to by every sprint) and
Nexus's existing `NexusEvent` bus into one time-ordered activity feed.
No new event-of-record table is added — every item already had a durable
row before Genesis; this module only aggregates and tags each item with
the module it belongs to (via its `action_type`/`event_type` prefix) so
the frontend can link back to the right application.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.nexus_integration import NexusEvent

# Maps an action_type/event_type prefix to the module it belongs to, so
# every activity item links back to its own application (Section 6).
_ACTION_PREFIX_TO_MODULE = {
    "sentinel.": "command", "atlas.": "connect", "nexus.": "connect", "horizon.": "research",
    "beacon.": "connect", "insight.": "analytics", "p24.": "research", "p20.": "research",
    "quality_guardian.": "command", "or_connect.": "inspect", "capa.": "command",
    "genesis.": "developer", "platform.": "developer",
}
_EVENT_TYPE_TO_MODULE = {
    "InspectionCompleted": "inspect", "SupervisorApproved": "inspect", "RepairRecommended": "connect",
    "KnowledgeUpdated": "knowledge", "BaselinePublished": "knowledge", "DigitalTwinUpdated": "twin",
    "EnterpriseAlertCreated": "command", "ModuleLicenseChanged": "developer", "PluginRegistered": "developer",
}


def _module_for_action(action_type: str) -> str:
    for prefix, module in _ACTION_PREFIX_TO_MODULE.items():
        if action_type.startswith(prefix):
            return module
    return "inspect"


def universal_activity_feed(db: Session, tenant_id: str, *, limit: int = 50) -> list[dict]:
    items: list[dict] = []

    audit_rows = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    for a in audit_rows:
        items.append({
            "source": "audit", "id": a.id,
            "created_at": a.created_at.isoformat() if getattr(a, "created_at", None) else None,
            "action_type": a.action_type, "actor": a.actor_email, "resource_type": a.resource_type,
            "resource_id": a.resource_id, "module": _module_for_action(a.action_type or ""),
        })

    event_rows = (
        db.query(NexusEvent)
        .filter(NexusEvent.tenant_id == tenant_id)
        .order_by(NexusEvent.id.desc())
        .limit(limit)
        .all()
    )
    for e in event_rows:
        items.append({
            "source": "event_bus", "id": e.id,
            "created_at": e.created_at.isoformat() if getattr(e, "created_at", None) else None,
            "action_type": e.event_type, "actor": e.actor, "resource_type": "nexus_event",
            "resource_id": str(e.id), "module": _EVENT_TYPE_TO_MODULE.get(e.event_type, "connect"),
        })

    items.sort(key=lambda i: i["created_at"] or "", reverse=True)
    return items[:limit]
