"""v3.5 — Project Beacon, Section 1: Industry Collaboration Hub.

Reuses P24's `AdvisoryConsortiumMember` (`app/models/p24_standards.py`)
directly as the participant roster for all seven collaboration types the
sprint names (hospitals, manufacturers, repair vendors, academic
institutions, standards organizations, regulatory teams, research
partners) rather than a second membership model. Enrollment itself
already exists at `POST /api/standards/consortium/enroll`
(`app/routes/p24_standards.py::enroll_consortium`), whose
`organization_type` vocabulary was extended with `"repair_vendor"` and
`"research_partner"` for this sprint. This module composes that roster
into a governance-ruled collaboration hub view.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.p24_standards import AdvisoryConsortiumMember
from app.services.p24_standards_service import DISCLAIMER, _to_dict

PARTICIPANT_TYPES = (
    "hospital", "manufacturer", "repair_vendor", "academic", "standards_body", "regulator", "research_partner",
    # "partner" / "consultant" / "educator" added for Project Olympus (v5.1).
    "partner", "consultant", "educator",
)


def collaboration_hub_summary(db: Session) -> dict:
    """Governance-ruled: only `membership_status == 'active'` members
    appear in the participant directory — a pending/suspended/resigned
    member is never listed as an active collaborator."""
    members = db.query(AdvisoryConsortiumMember).filter(AdvisoryConsortiumMember.membership_status == "active").all()
    by_type: dict[str, list[dict]] = {t: [] for t in PARTICIPANT_TYPES}
    for m in members:
        by_type.setdefault(m.organization_type, []).append(_to_dict(m))

    return {
        "participants_by_type": by_type,
        "total_active_participants": len(members),
        "participant_types": PARTICIPANT_TYPES,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def participants_of_type(db: Session, organization_type: str) -> list[dict]:
    if organization_type not in PARTICIPANT_TYPES:
        raise ValueError(f"organization_type must be one of {PARTICIPANT_TYPES}")
    rows = db.query(AdvisoryConsortiumMember).filter(
        AdvisoryConsortiumMember.organization_type == organization_type,
        AdvisoryConsortiumMember.membership_status == "active",
    ).all()
    return [_to_dict(r) for r in rows]


def participant_status(db: Session, tenant_id: str) -> dict | None:
    member = db.query(AdvisoryConsortiumMember).filter(AdvisoryConsortiumMember.tenant_id == tenant_id).first()
    return _to_dict(member) if member else None
