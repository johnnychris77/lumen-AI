"""v3.4 — Project Horizon, Section 9: Governance Center.

Composes participation status (`horizon_participation_service`), the
pending contribution approval queue (`horizon_contribution_service`), and
this platform's existing audit trail (`app/audit.py::log_audit_event` /
`AuditLog`) into one governance view — reusing every underlying system
rather than building a parallel governance store.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.federated_horizon import DISCLAIMER, PENDING_REVIEW
from app.services import horizon_contribution_service, horizon_participation_service


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def governance_overview(db: Session, tenant_id: str) -> dict:
    participation = horizon_participation_service.get_participation_status(db, tenant_id)
    pending_contributions = horizon_contribution_service.list_contributions(
        db, approval_status=PENDING_REVIEW, requesting_tenant_id=tenant_id,
    )
    audit_trail = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == tenant_id, AuditLog.action_type.like("horizon.%"))
        .order_by(AuditLog.id.desc())
        .limit(50)
        .all()
    )

    return {
        "tenant_id": tenant_id,
        "participation": participation,
        "pending_contribution_approvals": pending_contributions,
        "audit_trail": [_row_to_dict(a) for a in audit_trail],
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def list_all_pending_approvals(db: Session) -> list[dict]:
    """Governance-board-wide view (not scoped to one org) of every
    contribution awaiting approval — de-identified, per
    `horizon_contribution_service`'s own list function."""
    return horizon_contribution_service.list_contributions(db, approval_status=PENDING_REVIEW)
