"""v4.7 — Project Apollo, Section 2: CAPA Engine.

Composes the pre-existing CAPA stack — `capa_suggestion_service` (now
extended with Apollo's 5 new detectors), `capa_lifecycle_service` (the real
open->assigned->in_progress->verified->closed state machine), and Apollo's
new `CustomerComplaint` intake — into one CAPA Engine view. This module adds
no new CAPA store; every CAPA still lives in `capa_service`'s single `capas`
table.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.apollo_quality import (
    COMPLAINT_CLOSED,
    COMPLAINT_LINKED_TO_CAPA,
    COMPLAINT_OPEN,
    CustomerComplaint,
)
from app.services import capa_lifecycle_service
from app.services.capa_suggestion_service import create_capa_from_suggestion, generate_capa_suggestions


def capa_engine_summary(db: Session, tenant_id: str) -> dict:
    """Owner/root-cause/actions/verification/closure rollup for the CAPA
    Engine tab — the lifecycle state machine plus current auto-trigger
    suggestions, nothing re-derived."""
    lifecycle_counts = capa_lifecycle_service.lifecycle_summary(tenant_id)
    suggestions = generate_capa_suggestions(db, tenant_id)
    open_complaints = (
        db.query(CustomerComplaint)
        .filter(CustomerComplaint.tenant_id == tenant_id, CustomerComplaint.status == COMPLAINT_OPEN)
        .count()
    )
    return {
        "lifecycle_counts": lifecycle_counts,
        "total_open_or_active": sum(
            v for k, v in lifecycle_counts.items() if k != capa_lifecycle_service.LIFECYCLE_CLOSED
        ),
        "pending_suggestions": suggestions,
        "pending_suggestion_count": len(suggestions),
        "open_complaint_count": open_complaints,
        "human_review_required": True,
    }


def create_capa_from_suggestion_reviewed(suggestion: dict, *, owner: str) -> dict:
    """Human-review materialization step — unchanged from the pre-existing
    `capa_suggestion_service.create_capa_from_suggestion`, exposed here so
    Apollo's routes have one CAPA Engine entry point."""
    return create_capa_from_suggestion(suggestion, owner=owner)


# ── Customer complaint intake (Section 2 CAPA trigger source) ───────────────

def create_complaint(
    db: Session, tenant_id: str, *, source: str, description: str, severity: str = "medium",
    instrument_type: str = "", reported_by: str = "",
) -> CustomerComplaint:
    complaint = CustomerComplaint(
        tenant_id=tenant_id, source=source, description=description, severity=severity,
        instrument_type=instrument_type, reported_by=reported_by,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def list_complaints(db: Session, tenant_id: str, *, status: str = "") -> list[CustomerComplaint]:
    q = db.query(CustomerComplaint).filter(CustomerComplaint.tenant_id == tenant_id)
    if status:
        q = q.filter(CustomerComplaint.status == status)
    return q.order_by(CustomerComplaint.created_at.desc()).all()


class ComplaintNotFoundError(Exception):
    pass


def link_complaint_to_capa(db: Session, tenant_id: str, complaint_id: int, *, capa_id: str) -> CustomerComplaint:
    complaint = (
        db.query(CustomerComplaint)
        .filter(CustomerComplaint.id == complaint_id, CustomerComplaint.tenant_id == tenant_id)
        .first()
    )
    if complaint is None:
        raise ComplaintNotFoundError(f"Complaint {complaint_id} not found for tenant {tenant_id}.")
    complaint.linked_capa_id = capa_id
    complaint.status = COMPLAINT_LINKED_TO_CAPA
    db.commit()
    db.refresh(complaint)
    return complaint


def close_complaint(db: Session, tenant_id: str, complaint_id: int) -> CustomerComplaint:
    complaint = (
        db.query(CustomerComplaint)
        .filter(CustomerComplaint.id == complaint_id, CustomerComplaint.tenant_id == tenant_id)
        .first()
    )
    if complaint is None:
        raise ComplaintNotFoundError(f"Complaint {complaint_id} not found for tenant {tenant_id}.")
    complaint.status = COMPLAINT_CLOSED
    db.commit()
    db.refresh(complaint)
    return complaint
