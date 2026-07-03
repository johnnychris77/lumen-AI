"""Phase 23 §6 — Enterprise Event Bus.

A synchronous, in-process event bus: `emit()` persists a real event row
(app/models/cios_event.py::CIOSEvent) whenever the CIOS orchestrator
observes something clinically significant. No event is emitted unless the
underlying condition it names is actually true in the current context —
e.g. `BloodDetected` only fires when a contamination finding of type
"blood" was really present.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.cios_event import CIOSEvent

EVENT_TYPES = [
    "InspectionStarted",
    "BaselineLoaded",
    "CoverageIncomplete",
    "BloodDetected",
    "CorrosionDetected",
    "RecommendationGenerated",
    "SupervisorApproved",
    "InstrumentRemovedFromService",
    "KnowledgeUpdated",
    "ModelFeedbackCaptured",
]


def emit(db: Session, tenant_id: str, event_type: str, inspection_id: int | None = None, payload: dict | None = None) -> CIOSEvent:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type '{event_type}'. Known types: {EVENT_TYPES}")
    event = CIOSEvent(
        tenant_id=tenant_id,
        inspection_id=inspection_id,
        event_type=event_type,
        payload_json=json.dumps(payload or {}, default=str),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, tenant_id: str, inspection_id: int | None = None, limit: int = 100) -> list[dict]:
    q = db.query(CIOSEvent).filter(CIOSEvent.tenant_id == tenant_id)
    if inspection_id is not None:
        q = q.filter(CIOSEvent.inspection_id == inspection_id)
    rows = q.order_by(CIOSEvent.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "event_type": r.event_type,
            "inspection_id": r.inspection_id,
            "payload": json.loads(r.payload_json or "{}"),
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
