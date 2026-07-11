"""v5.3 — Project Genesis AI, Section 9: Global Standards Observatory.

Zero new tables. Composes four real change feeds:

  * Manufacturer guidance -- `ManufacturerKnowledgeUpdate` (this sprint,
    Section 4), filtered to `published`.
  * Internal policies -- Apollo's `QualityPolicy` version chain
    (`apollo_policy_service.py`, v4.7), returned only for the requesting
    organization's own `tenant_id` -- an org's internal policies are its
    own data, never surfaced cross-organization, consistent with this
    sprint's "organizations retain ownership of their data" mission.
  * Industry standards -- P24's `StandardsPublication`
    (`p24_standards.py`), filtered to `published`.
  * Scientific publications -- Horizon's `ClinicalEvidenceReference`
    with `evidence_type == "peer_reviewed"`.

"Notify participating organizations of relevant updates" is implemented
honestly as a queryable recent-changes feed scoped to
`AdvisoryConsortiumMember.observatory_opt_in` participants (Olympus's
existing flag, reused rather than a second opt-in column) -- there is no
email/push notification system anywhere in this codebase, so this
module never claims to deliver one.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.federated_horizon import ClinicalEvidenceReference
from app.models.genesis_ai_intelligence_cloud import MFR_UPDATE_PUBLISHED, ManufacturerKnowledgeUpdate
from app.models.p24_standards import AdvisoryConsortiumMember, StandardsPublication
from app.services import apollo_policy_service


def _opted_in_tenant_ids(db: Session) -> set[str]:
    rows = (
        db.query(AdvisoryConsortiumMember.tenant_id)
        .filter(AdvisoryConsortiumMember.observatory_opt_in.is_(True), AdvisoryConsortiumMember.membership_status == "active")
        .all()
    )
    return {r[0] for r in rows}


def recent_manufacturer_guidance(db: Session, *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(ManufacturerKnowledgeUpdate)
        .filter(ManufacturerKnowledgeUpdate.status == MFR_UPDATE_PUBLISHED)
        .order_by(ManufacturerKnowledgeUpdate.reviewed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "manufacturer_tenant_id": r.manufacturer_tenant_id, "update_type": r.update_type,
            "title": r.title, "version": r.version, "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        }
        for r in rows
    ]


def recent_industry_standards(db: Session, *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(StandardsPublication)
        .filter(StandardsPublication.status == "published")
        .order_by(StandardsPublication.id.desc())
        .limit(limit)
        .all()
    )
    return [{"id": r.id, "title": r.title, "publication_type": r.publication_type, "version": r.version} for r in rows]


def recent_scientific_publications(db: Session, *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(ClinicalEvidenceReference)
        .filter(ClinicalEvidenceReference.evidence_type == "peer_reviewed")
        .order_by(ClinicalEvidenceReference.created_at.desc())
        .limit(limit)
        .all()
    )
    return [{"id": r.id, "title": r.title, "source": r.source, "citation_text": r.citation_text} for r in rows]


def recent_internal_policy_changes(db: Session, tenant_id: str, *, limit: int = 20) -> list[dict]:
    """The requesting organization's own policies only -- never another
    organization's, regardless of observatory opt-in status."""
    return apollo_policy_service.list_policies(db, tenant_id, status="published")[:limit]


def observatory_summary(db: Session, tenant_id: str) -> dict:
    return {
        "opted_in_participant_count": len(_opted_in_tenant_ids(db)),
        "manufacturer_guidance": recent_manufacturer_guidance(db, limit=10),
        "internal_policy_changes": recent_internal_policy_changes(db, tenant_id, limit=10),
        "industry_standards": recent_industry_standards(db, limit=10),
        "scientific_publications": recent_scientific_publications(db, limit=10),
    }
