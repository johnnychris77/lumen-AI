"""v5.1 — Project Olympus, Section 9: Network Governance Council.

Beacon's `AdvisoryBoardMeeting`/`AdvisoryBoardActionItem`/
`AdvisoryBoardRecommendation` triplet (`industry_collaboration.py`, v3.5)
already covers meeting-based product-roadmap governance for one industry
board; Vanguard's governance is internal, single-org executive governance.
Neither covers cross-organization case work -- dispute resolution, ethics
review, version approval. `NetworkGovernanceCase` is genuinely new: one
generic case model with a `case_type` discriminator rather than six
separate tables. `meeting_id` optionally links a case to the Beacon
meeting where it was discussed, without requiring one.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.industry_collaboration import AdvisoryBoardMeeting
from app.models.olympus_network import CASE_DISMISSED, CASE_OPEN, CASE_RESOLVED, GOVERNANCE_CASE_TYPES, NetworkGovernanceCase
from app.services.enterprise_audit_service import record_enterprise_audit_event


class UnknownGovernanceCaseError(Exception):
    pass


def _to_dict(case: NetworkGovernanceCase) -> dict:
    return {
        "id": case.id,
        "case_type": case.case_type,
        "title": case.title,
        "description": case.description,
        "filed_by": case.filed_by,
        "involved_tenant_ids": json.loads(case.involved_tenant_ids_json or "[]"),
        "status": case.status,
        "meeting_id": case.meeting_id,
        "resolution": case.resolution,
        "resolved_by": case.resolved_by,
        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
        "human_review_required": case.human_review_required,
        "created_at": case.created_at.isoformat(),
    }


def _get_or_404(db: Session, case_id: int) -> NetworkGovernanceCase:
    row = db.query(NetworkGovernanceCase).filter(NetworkGovernanceCase.id == case_id).first()
    if row is None:
        raise UnknownGovernanceCaseError(f"Governance case {case_id} not found.")
    return row


def file_case(
    db: Session, *, case_type: str, title: str, description: str, filed_by: str,
    involved_tenant_ids: list[str] | None = None, meeting_id: int | None = None,
) -> dict:
    if case_type not in GOVERNANCE_CASE_TYPES:
        raise ValueError(f"case_type must be one of {GOVERNANCE_CASE_TYPES}")
    if meeting_id is not None:
        meeting = db.query(AdvisoryBoardMeeting).filter(AdvisoryBoardMeeting.id == meeting_id).first()
        if meeting is None:
            raise ValueError(f"Advisory Board meeting {meeting_id} not found.")
    row = NetworkGovernanceCase(
        case_type=case_type, title=title, description=description, filed_by=filed_by,
        involved_tenant_ids_json=json.dumps(involved_tenant_ids or []), meeting_id=meeting_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    record_enterprise_audit_event(
        db, action_type="olympus.governance_case_filed", resource_type="network_governance_case",
        resource_id=str(row.id), actor=filed_by, actor_email=filed_by,
        tenant_id="", tenant_name="",
        details={"case_type": case_type, "involved_tenant_ids": involved_tenant_ids or []},
    )
    return _to_dict(row)


def decide_case(db: Session, case_id: int, *, decision: str, resolution: str, resolved_by: str) -> dict:
    row = _get_or_404(db, case_id)
    if row.status in (CASE_RESOLVED, CASE_DISMISSED):
        raise ValueError(f"Case {case_id} is already '{row.status}'.")
    if decision not in ("resolved", "dismissed"):
        raise ValueError("decision must be 'resolved' or 'dismissed'")

    row.status = CASE_RESOLVED if decision == "resolved" else CASE_DISMISSED
    row.resolution = resolution
    row.resolved_by = resolved_by
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)

    record_enterprise_audit_event(
        db, action_type="olympus.governance_case_decided", resource_type="network_governance_case",
        resource_id=str(row.id), actor=resolved_by, actor_email=resolved_by,
        tenant_id="", tenant_name="",
        details={"decision": decision},
    )
    return _to_dict(row)


def get_case(db: Session, case_id: int) -> dict:
    return _to_dict(_get_or_404(db, case_id))


def list_cases(db: Session, *, case_type: str = "", status: str = "") -> list[dict]:
    query = db.query(NetworkGovernanceCase)
    if case_type:
        if case_type not in GOVERNANCE_CASE_TYPES:
            raise ValueError(f"case_type must be one of {GOVERNANCE_CASE_TYPES}")
        query = query.filter(NetworkGovernanceCase.case_type == case_type)
    if status:
        query = query.filter(NetworkGovernanceCase.status == status)
    rows = query.order_by(NetworkGovernanceCase.created_at.desc()).all()
    return [_to_dict(r) for r in rows]


def council_summary(db: Session) -> dict:
    open_cases = db.query(NetworkGovernanceCase).filter(NetworkGovernanceCase.status == CASE_OPEN).all()
    by_type: dict[str, int] = {}
    for c in open_cases:
        by_type[c.case_type] = by_type.get(c.case_type, 0) + 1
    return {
        "case_types": GOVERNANCE_CASE_TYPES,
        "open_case_count": len(open_cases),
        "open_by_case_type": by_type,
    }
