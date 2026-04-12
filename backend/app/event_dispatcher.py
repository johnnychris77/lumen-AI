from __future__ import annotations

from sqlalchemy.orm import Session

from app.automation_engine import process_trigger


def dispatch_event(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    trigger_type: str,
    payload: dict,
) -> dict:
    return process_trigger(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        trigger_type=trigger_type,
        payload=payload,
    )
