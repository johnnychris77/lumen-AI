"""v3.5 — Project Beacon, Section 4: Standards Collaboration Center.

Reuses P24's `StandardsPublication`/`AdvisoryConsortiumMember` directly
(`app/models/p24_standards.py`, `app/services/p24_standards_service.py`)
rather than a second versioned-publication model — Beacon only adds the
version-chain walk (`supersedes_id`, a new nullable column on the same
table) and a governance gate restricting who may publish.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.p24_standards import AdvisoryConsortiumMember, StandardsPublication
from app.services.p24_standards_service import DISCLAIMER, _to_dict, get_publications

# Organization types recognized as "approved standards bodies" for Section 4
# — AAMI/AORN/AST/other approved bodies, per the sprint's naming; represented
# here by P24's existing `organization_type` vocabulary rather than a new one.
APPROVED_PUBLISHER_TYPES = {"standards_body", "regulator", "academic"}


class NotAuthorizedPublisherError(Exception):
    pass


def _is_approved_publisher(db: Session, tenant_id: str) -> bool:
    member = db.query(AdvisoryConsortiumMember).filter(
        AdvisoryConsortiumMember.tenant_id == tenant_id, AdvisoryConsortiumMember.membership_status == "active",
    ).first()
    return member is not None and member.organization_type in APPROVED_PUBLISHER_TYPES


def publish_guidance(
    db: Session, tenant_id: str, *, title: str, publication_type: str, abstract: str,
    authors: list[str], regulatory_bodies_aligned: list[str], supersedes_id: int | None = None,
) -> dict:
    if not _is_approved_publisher(db, tenant_id):
        raise NotAuthorizedPublisherError(
            f"Tenant {tenant_id} is not an active standards_body/regulator/academic consortium member.",
        )

    version = "1.0"
    if supersedes_id is not None:
        prior = db.query(StandardsPublication).filter(StandardsPublication.id == supersedes_id).first()
        if prior is None:
            raise ValueError(f"Publication {supersedes_id} not found to supersede.")
        try:
            version = f"{float(prior.version) + 1.0:.1f}"
        except (TypeError, ValueError):
            version = prior.version or "1.0"
        prior.status = "superseded"

    row = StandardsPublication(
        title=title, publication_type=publication_type, version=version, status="consortium_review",
        abstract=abstract, authors=json.dumps(authors), regulatory_bodies_aligned=json.dumps(regulatory_bodies_aligned),
        supersedes_id=supersedes_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def version_history(db: Session, publication_id: int) -> list[dict]:
    """Walks the `supersedes_id` chain to the root, then returns every
    version in order — mirrors Horizon's `get_version_history` walk."""
    row = db.query(StandardsPublication).filter(StandardsPublication.id == publication_id).first()
    if row is None:
        return []

    root_id = row.id
    seen = set()
    while True:
        current = db.query(StandardsPublication).filter(StandardsPublication.id == root_id).first()
        if current is None or not current.supersedes_id or current.supersedes_id in seen:
            break
        seen.add(current.supersedes_id)
        root_id = current.supersedes_id

    chain = []
    current_id = root_id
    visited = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        current = db.query(StandardsPublication).filter(StandardsPublication.id == current_id).first()
        if current is None:
            break
        chain.append(_to_dict(current))
        successor = db.query(StandardsPublication).filter(StandardsPublication.supersedes_id == current_id).first()
        current_id = successor.id if successor else None
    return chain


def educational_content(db: Session) -> list[dict]:
    return get_publications(db, pub_type="guidance") + get_publications(db, pub_type="technical_note")


def standards_center_summary(db: Session) -> dict:
    return {
        "guidance": get_publications(db, pub_type="guidance"),
        "recommended_practices": get_publications(db, pub_type="standard"),
        "educational_content": educational_content(db),
        "reference_materials": get_publications(db, pub_type="technical_note"),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
