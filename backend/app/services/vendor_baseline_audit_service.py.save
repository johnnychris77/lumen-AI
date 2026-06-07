from typing import Optional
from sqlalchemy.orm import Session

from app.models.vendor_baseline_audit import VendorBaselineAuditEvent


def log_vendor_baseline_audit_event(
    db: Session,
    baseline_id: int,
    event_type: str,
    actor: Optional[str] = None,
    actor_role: Optional[str] = None,
    decision: Optional[str] = None,
    notes: Optional[str] = None,
    evidence_source: Optional[str] = None,
    finding_id: Optional[int] = None,
    inspection_id: Optional[int] = None,
    matched_identifier_type: Optional[str] = None,
    matched_identifier_value: Optional[str] = None,
    previous_status: Optional[str] = None,
    new_status: Optional[str] = None,
):
    event = VendorBaselineAuditEvent(
        baseline_id=baseline_id,
        event_type=event_type,
        actor=actor,
        actor_role=actor_role,
        decision=decision,
        notes=notes,
        evidence_source=evidence_source,
        finding_id=finding_id,
        inspection_id=inspection_id,
        matched_identifier_type=matched_identifier_type,
        matched_identifier_value=matched_identifier_value,
        previous_status=previous_status,
        new_status=new_status,
    )

    db.add(event)
    return event
