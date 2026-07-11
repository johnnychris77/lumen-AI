"""v5.1 — Project Olympus, Section 1: Network Identity.

Composes P24's `AdvisoryConsortiumMember` roster (identity, participation
level via `membership_tier`, governance profile via `governance_roles`/
`voting_rights`) with the latest `NetworkTrustSnapshot` (trust score) and a
live contribution-history rollup across Horizon's `KnowledgeContribution`
and Beacon's `RepairIntelligenceSnapshot`/Advisory Board activity — no new
participant table.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.federated_horizon import KnowledgeContribution
from app.models.industry_collaboration import AdvisoryBoardActionItem
from app.models.olympus_network import NetworkTrustSnapshot
from app.models.p24_standards import AdvisoryConsortiumMember

NETWORK_PARTICIPANT_TYPES = (
    "hospital", "manufacturer", "regulator", "academic", "standards_body",
    "repair_vendor", "research_partner", "partner", "consultant", "educator",
)


def _member_to_dict(member: AdvisoryConsortiumMember) -> dict:
    return {
        "tenant_id": member.tenant_id,
        "organization_type": member.organization_type,
        "region": member.region,
        "participation_level": member.membership_tier,
        "membership_status": member.membership_status,
        "governance_profile": {
            "roles": json.loads(member.governance_roles or "[]"),
            "standards_review_active": bool(member.standards_review_active),
            "voting_rights": bool(member.voting_rights),
        },
        "observatory_opt_in": bool(member.observatory_opt_in),
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
    }


def _latest_trust_snapshot(db: Session, tenant_id: str) -> dict | None:
    row = (
        db.query(NetworkTrustSnapshot)
        .filter(NetworkTrustSnapshot.tenant_id == tenant_id)
        .order_by(NetworkTrustSnapshot.computed_at.desc())
        .first()
    )
    if row is None:
        return None
    return {
        "overall_trust_score": row.overall_trust_score,
        "components": json.loads(row.components_json or "{}"),
        "computed_at": row.computed_at.isoformat(),
    }


def contribution_history(db: Session, tenant_id: str) -> dict:
    """A live rollup, never a duplicated log — counts real rows from
    Horizon's contributions and Beacon's Advisory Board action items."""
    contributions = (
        db.query(KnowledgeContribution)
        .filter(KnowledgeContribution.source_tenant_id == tenant_id)
        .all()
    )
    action_items = (
        db.query(AdvisoryBoardActionItem)
        .filter(AdvisoryBoardActionItem.owner == tenant_id)
        .all()
    )
    return {
        "knowledge_contributions_total": len(contributions),
        "knowledge_contributions_approved": sum(1 for c in contributions if c.approval_status == "approved"),
        "advisory_action_items_total": len(action_items),
        "advisory_action_items_done": sum(1 for a in action_items if a.status == "done"),
    }


def get_participant(db: Session, tenant_id: str) -> dict | None:
    member = db.query(AdvisoryConsortiumMember).filter(AdvisoryConsortiumMember.tenant_id == tenant_id).first()
    if member is None:
        return None
    result = _member_to_dict(member)
    result["trust"] = _latest_trust_snapshot(db, tenant_id)
    result["contribution_history"] = contribution_history(db, tenant_id)
    return result


def list_participants(db: Session, *, organization_type: str = "", active_only: bool = True) -> list[dict]:
    query = db.query(AdvisoryConsortiumMember)
    if organization_type:
        if organization_type not in NETWORK_PARTICIPANT_TYPES:
            raise ValueError(f"organization_type must be one of {NETWORK_PARTICIPANT_TYPES}")
        query = query.filter(AdvisoryConsortiumMember.organization_type == organization_type)
    if active_only:
        query = query.filter(AdvisoryConsortiumMember.membership_status == "active")
    members = query.all()
    return [
        {**_member_to_dict(m), "trust": _latest_trust_snapshot(db, m.tenant_id)}
        for m in members
    ]


def network_directory_summary(db: Session) -> dict:
    members = db.query(AdvisoryConsortiumMember).filter(AdvisoryConsortiumMember.membership_status == "active").all()
    by_type: dict[str, int] = {}
    for m in members:
        by_type[m.organization_type] = by_type.get(m.organization_type, 0) + 1
    return {
        "total_active_participants": len(members),
        "by_organization_type": by_type,
        "participant_types": list(NETWORK_PARTICIPANT_TYPES),
    }
