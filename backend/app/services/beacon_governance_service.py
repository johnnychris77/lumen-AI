"""v3.5 — Project Beacon, Section 9: Collaboration Governance.

Composes what already exists rather than building a parallel governance
store, mirroring Horizon's `horizon_governance_service.py`:

  * **Participation agreements** — P24's `AdvisoryConsortiumMember`
    (`beacon_collaboration_hub_service.participant_status`).
  * **Knowledge approval** — Horizon's `horizon_contribution_service`
    pending queue (manufacturer feedback contributions).
  * **Evidence review** — `horizon_evidence_service.list_evidence`.
  * **Contribution history** — a tenant's own submitted contributions
    (`horizon_contribution_service.list_contributions`, which already
    includes `source_tenant_id` for the tenant's own submissions).
  * **Version management** — `beacon_standards_service.version_history`.
  * **Audit trail** — this platform's existing `AuditLog` table, filtered
    to `beacon.*` action types, the same mechanism every prior sprint's
    governance center uses. No second audit store.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.federated_horizon import DISCLAIMER, PENDING_REVIEW
from app.services import beacon_collaboration_hub_service, horizon_contribution_service


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def governance_overview(db: Session, tenant_id: str) -> dict:
    participation = beacon_collaboration_hub_service.participant_status(db, tenant_id)
    own_contributions = horizon_contribution_service.list_contributions(db, requesting_tenant_id=tenant_id)
    own_pending = [c for c in own_contributions if c.get("source_tenant_id") == tenant_id and c["approval_status"] == PENDING_REVIEW]
    audit_trail = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == tenant_id, AuditLog.action_type.like("beacon.%"))
        .order_by(AuditLog.id.desc())
        .limit(50)
        .all()
    )

    return {
        "tenant_id": tenant_id,
        "participation": participation,
        "own_contribution_history": [c for c in own_contributions if c.get("source_tenant_id") == tenant_id],
        "own_pending_approvals": own_pending,
        "audit_trail": [_row_to_dict(a) for a in audit_trail],
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def pending_knowledge_approvals(db: Session) -> list[dict]:
    """Governance-board-wide (not scoped to one org) pending queue —
    de-identified per `horizon_contribution_service`'s own list function."""
    return horizon_contribution_service.list_contributions(db, approval_status=PENDING_REVIEW)
