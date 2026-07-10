"""v3.2 — Project Nexus, Section 6: Event Bus.

The first typed publish/subscribe layer in this codebase. `app/audit.py`'s
`log_audit_event` is a direct DB insert at each call site — not pub/sub.
`app/automation_engine.py`'s `AutomationRule`/`process_trigger` is a
synchronous, per-tenant-rule condition engine polled at each trigger call —
closer to a rules engine than an event bus, with no typed event catalog or
subscriber registry. This module adds both without replacing either:
`publish()` persists a `NexusEvent` row, best-effort forwards to the
existing automation engine via `app/event_dispatcher.py::dispatch_event`
(so existing `AutomationRule`s keep firing on these same triggers), and
separately delivers to any active `NexusEventSubscription` for the event
type. A webhook subscriber delivery failure never blocks publishing or
the automation-engine dispatch — those are best-effort side effects of an
event that has already been durably persisted.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.event_dispatcher import dispatch_event
from app.models.nexus_integration import (
    NEXUS_EVENT_TYPES,
    NEXUS_SUBSCRIPTION_TARGET_TYPES,
    SUBSCRIPTION_TARGET_WEBHOOK,
    NexusEvent,
    NexusEventSubscription,
)


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _deliver_webhook(target: str, event: dict) -> bool:
    """Best-effort outbound delivery. Never raises — a subscriber's
    endpoint being down must not affect the publisher or other subscribers."""
    try:
        import requests
        response = requests.post(target, json=event, timeout=5)
        return response.status_code < 400
    except Exception:
        return False


def publish(
    db: Session, *, tenant_id: str, event_type: str, payload: dict, actor: str = "system", tenant_name: str = "",
) -> dict:
    if event_type not in NEXUS_EVENT_TYPES:
        raise ValueError(f"event_type must be one of {NEXUS_EVENT_TYPES}")

    event_row = NexusEvent(tenant_id=tenant_id, event_type=event_type, payload_json=json.dumps(payload, default=str), actor=actor)
    db.add(event_row)
    db.commit()
    db.refresh(event_row)

    # Best-effort: existing AutomationRules subscribed to this trigger_type
    # still fire. A rule-engine failure never rolls back the published event.
    try:
        dispatch_event(db, tenant_id=tenant_id, tenant_name=tenant_name or tenant_id, trigger_type=event_type, payload=payload)
    except Exception:
        pass

    subscriptions = (
        db.query(NexusEventSubscription)
        .filter(
            NexusEventSubscription.tenant_id == tenant_id, NexusEventSubscription.event_type == event_type,
            NexusEventSubscription.active.is_(True),
        )
        .all()
    )
    delivered = 0
    for sub in subscriptions:
        if sub.target_type == SUBSCRIPTION_TARGET_WEBHOOK:
            if _deliver_webhook(sub.target, {"event_type": event_type, "tenant_id": tenant_id, "payload": payload}):
                delivered += 1
        else:
            delivered += 1  # internal subscribers are notified by presence of the persisted event itself

    event_row.subscriber_delivery_count = delivered
    db.commit()
    db.refresh(event_row)
    return _row_to_dict(event_row)


def list_events(db: Session, tenant_id: str, *, event_type: str = "", limit: int = 50) -> list[dict]:
    q = db.query(NexusEvent).filter(NexusEvent.tenant_id == tenant_id)
    if event_type:
        q = q.filter(NexusEvent.event_type == event_type)
    rows = q.order_by(NexusEvent.id.desc()).limit(limit).all()
    return [_row_to_dict(r) for r in rows]


def create_subscription(
    db: Session, tenant_id: str, *, event_type: str, target_type: str, target: str, connector_id: int | None = None,
) -> dict:
    if event_type not in NEXUS_EVENT_TYPES:
        raise ValueError(f"event_type must be one of {NEXUS_EVENT_TYPES}")
    if target_type not in NEXUS_SUBSCRIPTION_TARGET_TYPES:
        raise ValueError(f"target_type must be one of {NEXUS_SUBSCRIPTION_TARGET_TYPES}")

    row = NexusEventSubscription(
        tenant_id=tenant_id, connector_id=connector_id, event_type=event_type, target_type=target_type, target=target,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_subscriptions(db: Session, tenant_id: str, *, event_type: str = "") -> list[dict]:
    q = db.query(NexusEventSubscription).filter(NexusEventSubscription.tenant_id == tenant_id)
    if event_type:
        q = q.filter(NexusEventSubscription.event_type == event_type)
    return [_row_to_dict(r) for r in q.order_by(NexusEventSubscription.id.asc()).all()]


def deactivate_subscription(db: Session, tenant_id: str, subscription_id: int) -> dict | None:
    row = (
        db.query(NexusEventSubscription)
        .filter(NexusEventSubscription.id == subscription_id, NexusEventSubscription.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        return None
    row.active = False
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
