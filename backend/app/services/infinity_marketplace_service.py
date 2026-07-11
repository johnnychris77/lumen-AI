"""v5.0 — Project Infinity, Sections 4 & 5: AI Skills Marketplace &
Application Marketplace.

`MarketplaceListing` is a generic model for both AI Skills and
Applications — distinct from Forge's workflow-only marketplace
(`workflow_forge.py`'s `marketplace_status`), which this reuses only for
its exact state-machine naming (`private/pending_review/published`), not
its table. A listing can only reach `published` after its linked
Certification Program chain (Section 7) reports `certified` — this is
enforced here, not left to convention.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.infinity_platform import (
    CERT_CERTIFIED,
    INSTALLATION_DISABLED,
    LISTING_PENDING_REVIEW,
    LISTING_PRIVATE,
    LISTING_PUBLISHED,
    LISTING_TYPES,
    PRICING_MODELS,
    MarketplaceInstallation,
    MarketplaceListing,
)


class ListingNotFoundError(ValueError):
    pass


class ListingNotCertifiedError(ValueError):
    pass


class InstallationNotFoundError(ValueError):
    pass


def _listing_to_dict(row: MarketplaceListing) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "developer_account_id": row.developer_account_id,
        "listing_type": row.listing_type, "category": row.category, "name": row.name, "description": row.description,
        "version": row.version, "status": row.status, "pricing_model": row.pricing_model, "price_cents": row.price_cents,
        "certification_status": row.certification_status, "certification_chain_id": row.certification_chain_id,
        "certification_instance_id": row.certification_instance_id, "manifest": json.loads(row.manifest_json or "{}"),
    }


def create_listing(
    db: Session, developer_account_id: int, *, listing_type: str, name: str, category: str = "",
    description: str = "", pricing_model: str = "free", price_cents: int | None = None, manifest: dict | None = None,
) -> dict:
    if listing_type not in LISTING_TYPES:
        raise ValueError(f"listing_type must be one of {LISTING_TYPES}")
    if pricing_model not in PRICING_MODELS:
        raise ValueError(f"pricing_model must be one of {PRICING_MODELS}")
    row = MarketplaceListing(
        developer_account_id=developer_account_id, listing_type=listing_type, category=category, name=name,
        description=description, pricing_model=pricing_model, price_cents=price_cents,
        manifest_json=json.dumps(manifest or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _listing_to_dict(row)


def get_listing_or_404(db: Session, listing_id: int) -> MarketplaceListing:
    row = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if row is None:
        raise ListingNotFoundError(f"Listing {listing_id} not found.")
    return row


def get_listing(db: Session, listing_id: int) -> dict:
    return _listing_to_dict(get_listing_or_404(db, listing_id))


def list_listings(db: Session, *, listing_type: str = "", category: str = "", status: str = "") -> list[dict]:
    q = db.query(MarketplaceListing)
    if listing_type:
        q = q.filter(MarketplaceListing.listing_type == listing_type)
    if category:
        q = q.filter(MarketplaceListing.category == category)
    if status:
        q = q.filter(MarketplaceListing.status == status)
    return [_listing_to_dict(r) for r in q.order_by(MarketplaceListing.created_at.desc()).all()]


def submit_for_review(db: Session, listing_id: int) -> dict:
    row = get_listing_or_404(db, listing_id)
    row.status = LISTING_PENDING_REVIEW
    db.commit()
    db.refresh(row)
    return _listing_to_dict(row)


def publish_listing(db: Session, listing_id: int) -> dict:
    """A listing can only be published once its Certification Program
    chain (Section 7) reports `certified` — every gate must have passed."""
    row = get_listing_or_404(db, listing_id)
    if row.certification_status != CERT_CERTIFIED:
        raise ListingNotCertifiedError(
            f"Listing {listing_id} cannot be published — certification_status is "
            f"'{row.certification_status}', not 'certified'.",
        )
    row.status = LISTING_PUBLISHED
    db.commit()
    db.refresh(row)
    return _listing_to_dict(row)


def unpublish_listing(db: Session, listing_id: int) -> dict:
    row = get_listing_or_404(db, listing_id)
    row.status = LISTING_PRIVATE
    db.commit()
    db.refresh(row)
    return _listing_to_dict(row)


def _installation_to_dict(row: MarketplaceInstallation) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "tenant_id": row.tenant_id, "listing_id": row.listing_id,
        "installed_version": row.installed_version, "status": row.status, "installed_by": row.installed_by,
    }


def install_listing(db: Session, tenant_id: str, listing_id: int, *, installed_by: str) -> dict:
    listing = get_listing_or_404(db, listing_id)
    if listing.status != LISTING_PUBLISHED:
        raise ValueError(f"Listing {listing_id} is not published (status: {listing.status}).")
    row = MarketplaceInstallation(
        tenant_id=tenant_id, listing_id=listing_id, installed_version=listing.version, installed_by=installed_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _installation_to_dict(row)


def list_installations(db: Session, tenant_id: str, *, status: str = "") -> list[dict]:
    q = db.query(MarketplaceInstallation).filter(MarketplaceInstallation.tenant_id == tenant_id)
    if status:
        q = q.filter(MarketplaceInstallation.status == status)
    return [_installation_to_dict(r) for r in q.order_by(MarketplaceInstallation.created_at.desc()).all()]


def uninstall(db: Session, tenant_id: str, installation_id: int) -> dict:
    row = (
        db.query(MarketplaceInstallation)
        .filter(MarketplaceInstallation.id == installation_id, MarketplaceInstallation.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise InstallationNotFoundError(f"Installation {installation_id} not found for tenant {tenant_id}.")
    row.status = INSTALLATION_DISABLED
    db.commit()
    db.refresh(row)
    return _installation_to_dict(row)
