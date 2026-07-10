"""v4.2 — Project Pulse, Section 2: Live Event Stream.

Reuses Nexus's existing typed pub/sub layer
(`nexus_event_bus_service.publish`/`list_events`, `NexusEvent`,
`NEXUS_EVENT_TYPES`) directly — no second event bus. This module adds
only the enrichment Pulse's stream needs: every event published through
`publish_pulse_event` carries the seven contextual fields Section 2
names (timestamp is `NexusEvent.created_at` itself; organization is
`tenant_id`; facility/department/user role/instrument/severity/source
are folded into the event's `payload` under those exact keys) so the
frontend never has to guess which payload keys are present.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import nexus_event_bus_service


def publish_pulse_event(
    db: Session, tenant_id: str, event_type: str, *, facility: str = "", department: str = "",
    user_role: str = "", instrument: str = "", severity: str = "info", source: str = "system",
    actor: str = "system", extra: dict | None = None,
) -> dict:
    payload = {
        "facility": facility, "department": department, "user_role": user_role,
        "instrument": instrument, "severity": severity, "source": source, **(extra or {}),
    }
    return nexus_event_bus_service.publish(db, tenant_id=tenant_id, event_type=event_type, payload=payload, actor=actor)


def live_event_stream(db: Session, tenant_id: str, *, event_type: str = "", limit: int = 100) -> list[dict]:
    events = nexus_event_bus_service.list_events(db, tenant_id, event_type=event_type, limit=limit)
    for event in events:
        payload = event.get("payload_json")
        # `list_events` already returns raw rows via `_row_to_dict`, which
        # leaves `payload_json` as a JSON string — decode it here so the
        # frontend receives structured context rather than a raw string.
        if isinstance(payload, str):
            import json
            try:
                event["payload"] = json.loads(payload)
            except (ValueError, TypeError):
                event["payload"] = {}
    return events
