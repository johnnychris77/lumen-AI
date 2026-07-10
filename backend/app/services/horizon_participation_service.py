"""v3.4 — Project Horizon, Section 1: Federated Knowledge Framework —
organization participation & opt-in governance.

A federated network participant needs two things this codebase already
models separately: GSIN's technical enrollment gate
(`GSINParticipant` — participant type, region, BAA/DPA, contribution
categories) and P20's opt-in sharing agreement (`IntelligenceSharingAgreement`
— agreement version, sharing scope, reversible withdrawal). Rather than
adding a third org-participation table, this module composes the two into
one enrollment/withdrawal action.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.global_intelligence import GSINParticipant
from app.models.p20_network_intelligence import IntelligenceSharingAgreement


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def enroll_organization(
    db: Session, tenant_id: str, *, participant_type: str, region: str, contribution_categories: list[str],
    agreed_by: str, sharing_scope: str = "benchmark",
) -> dict:
    participant = db.query(GSINParticipant).filter(GSINParticipant.tenant_id == tenant_id).first()
    if participant is None:
        participant = GSINParticipant(
            tenant_id=tenant_id, participant_type=participant_type, region=region,
            contribution_categories=json.dumps(contribution_categories), enrollment_status="pending",
        )
        db.add(participant)

    agreement = (
        db.query(IntelligenceSharingAgreement)
        .filter(IntelligenceSharingAgreement.tenant_id == tenant_id, IntelligenceSharingAgreement.status == "active")
        .first()
    )
    if agreement is None:
        agreement = IntelligenceSharingAgreement(tenant_id=tenant_id, agreed_by=agreed_by, sharing_scope=sharing_scope, status="active")
        db.add(agreement)

    db.commit()
    db.refresh(participant)
    db.refresh(agreement)

    return {
        "tenant_id": tenant_id,
        "participant": _row_to_dict(participant),
        "sharing_agreement": _row_to_dict(agreement),
    }


def get_participation_status(db: Session, tenant_id: str) -> dict:
    participant = db.query(GSINParticipant).filter(GSINParticipant.tenant_id == tenant_id).first()
    agreement = (
        db.query(IntelligenceSharingAgreement)
        .filter(IntelligenceSharingAgreement.tenant_id == tenant_id)
        .order_by(IntelligenceSharingAgreement.id.desc())
        .first()
    )
    return {
        "tenant_id": tenant_id,
        "enrolled": participant is not None,
        "participant": _row_to_dict(participant) if participant else None,
        "sharing_agreement": _row_to_dict(agreement) if agreement else None,
    }


def withdraw_organization(db: Session, tenant_id: str, *, withdrawn_by: str) -> dict:
    participant = db.query(GSINParticipant).filter(GSINParticipant.tenant_id == tenant_id).first()
    if participant is not None:
        participant.enrollment_status = "withdrawn"

    agreement = (
        db.query(IntelligenceSharingAgreement)
        .filter(IntelligenceSharingAgreement.tenant_id == tenant_id, IntelligenceSharingAgreement.status == "active")
        .first()
    )
    if agreement is not None:
        agreement.status = "withdrawn"
        agreement.withdrawn_at = datetime.now(timezone.utc)
        agreement.withdrawn_by = withdrawn_by

    db.commit()
    return get_participation_status(db, tenant_id)


def update_contribution_categories(db: Session, tenant_id: str, categories: list[str]) -> dict | None:
    """Section 9: data sharing preferences — which federated learning
    signal/benchmark categories this organization opts into."""
    participant = db.query(GSINParticipant).filter(GSINParticipant.tenant_id == tenant_id).first()
    if participant is None:
        return None
    participant.contribution_categories = json.dumps(categories)
    db.commit()
    db.refresh(participant)
    return _row_to_dict(participant)


def list_active_participants(db: Session) -> list[GSINParticipant]:
    return db.query(GSINParticipant).filter(GSINParticipant.enrollment_status == "active").all()


def list_enrolled_tenant_ids(db: Session) -> list[str]:
    """Any tenant with a participant record (pending or active) and an
    active sharing agreement — used to determine who gets notified of
    emerging trends (Section 6)."""
    agreements = db.query(IntelligenceSharingAgreement.tenant_id).filter(IntelligenceSharingAgreement.status == "active").all()
    return [a[0] for a in agreements]
