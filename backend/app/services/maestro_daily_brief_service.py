"""Project Maestro, Section 4: Daily Operational Brief.

Five brief types (morning/afternoon/end-of-day/weekend-readiness/shift-
handoff) all compose the same real underlying signals -- current
priorities, pending recommendations, operational health, and open patient
safety alerts -- varying only in emphasis and narrative framing per the
moment in the day they're read.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.maestro_orchestration import (
    BRIEF_AFTERNOON,
    BRIEF_END_OF_DAY,
    BRIEF_MORNING,
    BRIEF_SHIFT_HANDOFF,
    BRIEF_WEEKEND_READINESS,
    DECISION_STATUS_PENDING,
    MaestroDailyBrief,
)
from app.services import maestro_priority_engine_service, maestro_recommendation_engine_service
from app.services.maestro_health_index_service import compute_operational_health, to_dict as health_to_dict
from app.services.sentinelx_patient_safety_watch_service import list_alerts


def _compose_content(db: Session, tenant_id: str) -> dict:
    priorities = maestro_priority_engine_service.latest_priorities(db, tenant_id)
    if not priorities:
        priorities = [
            maestro_priority_engine_service.to_dict(r)
            for r in maestro_priority_engine_service.compute_priorities(db, tenant_id)
        ]

    pending_recommendations = maestro_recommendation_engine_service.list_recommendations(
        db, tenant_id, status=DECISION_STATUS_PENDING,
    )
    health = health_to_dict(compute_operational_health(db, tenant_id))
    open_alerts = list_alerts(db, tenant_id, acknowledged=False)

    return {
        "top_priorities": priorities[:5],
        "pending_recommendations": pending_recommendations[:10],
        "operational_health": health,
        "open_patient_safety_alerts": open_alerts,
    }


def _narrative(brief_type: str, content: dict) -> str:
    top = content["top_priorities"][0] if content["top_priorities"] else None
    lead = f"Top priority: {top['subject']} ({top['category']})." if top else "No active priorities to report."
    alerts = len(content["open_patient_safety_alerts"])
    overall = content["operational_health"].get("overall_score")
    health_line = f"Operational health index: {overall}." if overall is not None else "Operational health index: insufficient data."

    if brief_type == BRIEF_MORNING:
        return f"Morning Brief -- {lead} {health_line} {alerts} open patient safety alert(s) require attention today."
    if brief_type == BRIEF_AFTERNOON:
        return f"Afternoon Update -- {lead} {alerts} open patient safety alert(s) remain outstanding."
    if brief_type == BRIEF_END_OF_DAY:
        return f"End-of-Day Summary -- {lead} {health_line} {len(content['pending_recommendations'])} recommendation(s) still pending leadership decision."
    if brief_type == BRIEF_WEEKEND_READINESS:
        return f"Weekend Readiness -- {lead} {alerts} open patient safety alert(s); confirm on-call coverage before the weekend."
    if brief_type == BRIEF_SHIFT_HANDOFF:
        return f"Shift Handoff -- {lead} {alerts} open patient safety alert(s) and {len(content['pending_recommendations'])} pending recommendation(s) carry into the next shift."
    return lead


def generate_brief(db: Session, tenant_id: str, brief_type: str) -> MaestroDailyBrief:
    content = _compose_content(db, tenant_id)
    narrative = _narrative(brief_type, content)

    row = MaestroDailyBrief(
        tenant_id=tenant_id, brief_type=brief_type, content_json=json.dumps(content), narrative=narrative,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: MaestroDailyBrief) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "brief_type": row.brief_type,
        "content": json.loads(row.content_json or "{}"),
        "narrative": row.narrative,
    }


def latest_brief(db: Session, tenant_id: str, brief_type: str) -> dict | None:
    row = (
        db.query(MaestroDailyBrief)
        .filter(MaestroDailyBrief.tenant_id == tenant_id, MaestroDailyBrief.brief_type == brief_type)
        .order_by(MaestroDailyBrief.created_at.desc())
        .first()
    )
    return to_dict(row) if row else None
