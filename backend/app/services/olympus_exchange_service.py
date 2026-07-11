"""v5.1 — Project Olympus, Sections 3 & 4: Global Intelligence Exchange &
Healthcare Intelligence Exchange (HIX).

`HIXExchangePackage` never copies content -- it references an existing row
by `content_ref_type`/`content_ref_id` (a `KnowledgeArticle`, a
`WorkflowDefinition`, a Digital Twin model, ...) and only carries the
exchange's own governance/de-identification state. Every contribution
requires governance approval (Section 3) before it can be published
network-wide (Section 4's "secure exchange mechanism").

De-identification follows the exact pattern Horizon's
`horizon_contribution_service.py` already established:
`source_tenant_id` is included in a package's public representation only
when the requesting tenant *is* the source -- every other reader sees a
de-identified package with no hospital identity attached.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.olympus_network import (
    HIX_APPROVED,
    HIX_PACKAGE_TYPES,
    HIX_PENDING_GOVERNANCE_REVIEW,
    HIX_PUBLISHED,
    HIX_REJECTED,
    HIXExchangePackage,
)
from app.services.enterprise_audit_service import record_enterprise_audit_event


class UnknownExchangePackageError(Exception):
    pass


class InvalidPackageStateError(Exception):
    pass


def _to_dict(pkg: HIXExchangePackage, *, include_source_tenant: bool) -> dict:
    result = {
        "id": pkg.id,
        "package_type": pkg.package_type,
        "title": pkg.title,
        "description": pkg.description,
        "content_ref_type": pkg.content_ref_type,
        "content_ref_id": pkg.content_ref_id,
        "status": pkg.status,
        "no_phi_confirmed": pkg.no_phi_confirmed,
        "no_identifiable_customer_data_confirmed": pkg.no_identifiable_customer_data_confirmed,
        "governance_case_id": pkg.governance_case_id,
        "reviewed_by": pkg.reviewed_by,
        "reviewed_at": pkg.reviewed_at.isoformat() if pkg.reviewed_at else None,
        "human_review_required": pkg.human_review_required,
        "disclaimer": pkg.disclaimer,
        "created_at": pkg.created_at.isoformat(),
    }
    if include_source_tenant:
        result["source_tenant_id"] = pkg.source_tenant_id
        result["submitted_by"] = pkg.submitted_by
    return result


def _get_or_404(db: Session, package_id: int) -> HIXExchangePackage:
    row = db.query(HIXExchangePackage).filter(HIXExchangePackage.id == package_id).first()
    if row is None:
        raise UnknownExchangePackageError(f"Exchange package {package_id} not found.")
    return row


def submit_package(
    db: Session, source_tenant_id: str, *, package_type: str, title: str, description: str,
    content_ref_type: str, content_ref_id: int | None, no_phi_confirmed: bool,
    no_identifiable_customer_data_confirmed: bool, submitted_by: str,
) -> dict:
    if package_type not in HIX_PACKAGE_TYPES:
        raise ValueError(f"package_type must be one of {HIX_PACKAGE_TYPES}")
    if not (no_phi_confirmed and no_identifiable_customer_data_confirmed):
        raise InvalidPackageStateError(
            "Both no_phi_confirmed and no_identifiable_customer_data_confirmed must be true to submit a package."
        )
    row = HIXExchangePackage(
        source_tenant_id=source_tenant_id, package_type=package_type, title=title, description=description,
        content_ref_type=content_ref_type, content_ref_id=content_ref_id, status=HIX_PENDING_GOVERNANCE_REVIEW,
        no_phi_confirmed=no_phi_confirmed,
        no_identifiable_customer_data_confirmed=no_identifiable_customer_data_confirmed,
        submitted_by=submitted_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    record_enterprise_audit_event(
        db, action_type="olympus.hix_package_submitted", resource_type="hix_exchange_package",
        resource_id=str(row.id), actor=submitted_by, actor_email=submitted_by,
        tenant_id=source_tenant_id, tenant_name=source_tenant_id,
        details={"package_type": package_type, "title": title},
    )
    return _to_dict(row, include_source_tenant=True)


def governance_review_package(
    db: Session, package_id: int, *, decision: str, reviewed_by: str, governance_case_id: int | None = None,
) -> dict:
    """Section 3: "All contributions require governance approval." A
    package cannot move past `pending_governance_review` any other way."""
    row = _get_or_404(db, package_id)
    if row.status != HIX_PENDING_GOVERNANCE_REVIEW:
        raise InvalidPackageStateError(f"Package {package_id} is '{row.status}', not pending governance review.")
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")

    row.status = HIX_APPROVED if decision == "approved" else HIX_REJECTED
    row.reviewed_by = reviewed_by
    row.reviewed_at = datetime.now(timezone.utc)
    if governance_case_id is not None:
        row.governance_case_id = governance_case_id
    db.commit()
    db.refresh(row)

    record_enterprise_audit_event(
        db, action_type="olympus.hix_package_governance_reviewed", resource_type="hix_exchange_package",
        resource_id=str(row.id), actor=reviewed_by, actor_email=reviewed_by,
        tenant_id=row.source_tenant_id, tenant_name=row.source_tenant_id,
        details={"decision": decision},
    )
    return _to_dict(row, include_source_tenant=True)


def publish_package(db: Session, package_id: int, *, published_by: str) -> dict:
    """Section 4: publication into the secure exchange -- only reachable
    after governance approval, never directly from draft/pending."""
    row = _get_or_404(db, package_id)
    if row.status != HIX_APPROVED:
        raise InvalidPackageStateError(f"Package {package_id} must be 'approved' before publishing (is '{row.status}').")
    row.status = HIX_PUBLISHED
    db.commit()
    db.refresh(row)

    record_enterprise_audit_event(
        db, action_type="olympus.hix_package_published", resource_type="hix_exchange_package",
        resource_id=str(row.id), actor=published_by, actor_email=published_by,
        tenant_id=row.source_tenant_id, tenant_name=row.source_tenant_id,
        details={"package_type": row.package_type},
    )
    return _to_dict(row, include_source_tenant=True)


def get_package(db: Session, package_id: int, *, requesting_tenant_id: str = "") -> dict:
    row = _get_or_404(db, package_id)
    return _to_dict(row, include_source_tenant=(requesting_tenant_id == row.source_tenant_id))


def list_published_packages(db: Session, *, package_type: str = "", requesting_tenant_id: str = "") -> list[dict]:
    """The network-wide exchange view (Section 4) -- only `published`
    packages appear here, always de-identified unless the requester is
    the package's own source."""
    query = db.query(HIXExchangePackage).filter(HIXExchangePackage.status == HIX_PUBLISHED)
    if package_type:
        if package_type not in HIX_PACKAGE_TYPES:
            raise ValueError(f"package_type must be one of {HIX_PACKAGE_TYPES}")
        query = query.filter(HIXExchangePackage.package_type == package_type)
    rows = query.order_by(HIXExchangePackage.created_at.desc()).all()
    return [_to_dict(r, include_source_tenant=(requesting_tenant_id == r.source_tenant_id)) for r in rows]


def list_organization_packages(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(HIXExchangePackage)
        .filter(HIXExchangePackage.source_tenant_id == tenant_id)
        .order_by(HIXExchangePackage.created_at.desc())
        .all()
    )
    return [_to_dict(r, include_source_tenant=True) for r in rows]
