"""v1.8 — Organization Standards (Deliverable 6).

Per-tenant local policy — inspection standards, photography standards,
coverage requirements, supervisor approval thresholds, competency
requirements. These supplement, never replace, manufacturer IFUs; nothing
here overrides the AI's clinical engines.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge import OrganizationStandard


def create_standard(
    db: Session, tenant_id: str, *, standard_type: str, title: str, description: str, created_by: str,
) -> OrganizationStandard:
    row = OrganizationStandard(
        tenant_id=tenant_id, standard_type=standard_type, title=title.strip(),
        description=description.strip(), created_by=created_by,
    )
    db.add(row)
    return row


def standard_to_dict(row: OrganizationStandard) -> dict:
    return {
        "id": row.id, "standard_type": row.standard_type, "title": row.title,
        "description": row.description, "created_by": row.created_by, "active": row.active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_standards(db: Session, tenant_id: str, *, standard_type: str = "", active_only: bool = True) -> list[dict]:
    q = db.query(OrganizationStandard).filter(OrganizationStandard.tenant_id == tenant_id)
    if standard_type:
        q = q.filter(OrganizationStandard.standard_type == standard_type)
    if active_only:
        q = q.filter(OrganizationStandard.active.is_(True))
    rows = q.order_by(OrganizationStandard.id.desc()).all()
    return [standard_to_dict(r) for r in rows]


def deactivate_standard(db: Session, tenant_id: str, standard_id: int) -> OrganizationStandard | None:
    row = (
        db.query(OrganizationStandard)
        .filter(OrganizationStandard.tenant_id == tenant_id, OrganizationStandard.id == standard_id)
        .first()
    )
    if row is None:
        return None
    row.active = False
    return row
