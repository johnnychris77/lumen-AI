"""v5.0 — Project Infinity, Section 8: Billing & Licensing.

"Module Licensing" composes Genesis's existing `platform_licensing_
service.py` (`PlatformModuleLicense`) directly — no second per-module
license table. Enterprise/Partner licensing and marketplace revenue
sharing have no existing home anywhere in P14's inspection-volume billing
infrastructure, so `PartnerLicense`/`MarketplaceRevenueEvent` are
genuinely new, additive constructs.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.infinity_platform import (
    PARTNER_LICENSE_STATUSES,
    PARTNER_LICENSE_TYPES,
    REVENUE_EVENT_TYPES,
    MarketplaceRevenueEvent,
    PartnerLicense,
)
from app.services import platform_licensing_service

_DEFAULT_REVENUE_SHARE_PCT = 70.0  # developer's share, absent a PartnerLicense override


def module_licensing_summary(db: Session, tenant_id: str) -> dict:
    """Composes Genesis's existing module-licensing state directly."""
    return {"tenant_id": tenant_id, "licenses": platform_licensing_service.tenant_licenses(db, tenant_id)}


def _license_to_dict(row: PartnerLicense) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "developer_account_id": row.developer_account_id,
        "tenant_id": row.tenant_id, "license_type": row.license_type,
        "licensed_module_keys": json.loads(row.licensed_module_keys_json or "[]"), "terms": row.terms,
        "revenue_share_pct": row.revenue_share_pct, "status": row.status,
        "effective_date": row.effective_date.isoformat() if row.effective_date else None,
        "expiration_date": row.expiration_date.isoformat() if row.expiration_date else None,
    }


def create_partner_license(
    db: Session, *, license_type: str, developer_account_id: int | None = None, tenant_id: str = "",
    licensed_module_keys: list[str] | None = None, terms: str = "", revenue_share_pct: float | None = None,
    effective_date: datetime | None = None, expiration_date: datetime | None = None,
) -> dict:
    if license_type not in PARTNER_LICENSE_TYPES:
        raise ValueError(f"license_type must be one of {PARTNER_LICENSE_TYPES}")
    row = PartnerLicense(
        developer_account_id=developer_account_id, tenant_id=tenant_id, license_type=license_type,
        licensed_module_keys_json=json.dumps(licensed_module_keys or []), terms=terms,
        revenue_share_pct=revenue_share_pct, effective_date=effective_date, expiration_date=expiration_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _license_to_dict(row)


def list_partner_licenses(db: Session, *, developer_account_id: int | None = None, tenant_id: str = "", status: str = "") -> list[dict]:
    q = db.query(PartnerLicense)
    if developer_account_id is not None:
        q = q.filter(PartnerLicense.developer_account_id == developer_account_id)
    if tenant_id:
        q = q.filter(PartnerLicense.tenant_id == tenant_id)
    if status:
        q = q.filter(PartnerLicense.status == status)
    return [_license_to_dict(r) for r in q.order_by(PartnerLicense.created_at.desc()).all()]


def revoke_partner_license(db: Session, license_id: int) -> dict | None:
    row = db.query(PartnerLicense).filter(PartnerLicense.id == license_id).first()
    if row is None:
        return None
    if row.status not in PARTNER_LICENSE_STATUSES:
        raise ValueError(f"status must be one of {PARTNER_LICENSE_STATUSES}")
    row.status = "revoked"
    db.commit()
    db.refresh(row)
    return _license_to_dict(row)


def record_revenue_event(
    db: Session, listing_id: int, tenant_id: str, *, event_type: str, gross_amount_cents: int,
    developer_share_pct: float | None = None,
) -> dict:
    if event_type not in REVENUE_EVENT_TYPES:
        raise ValueError(f"event_type must be one of {REVENUE_EVENT_TYPES}")
    share_pct = developer_share_pct if developer_share_pct is not None else _DEFAULT_REVENUE_SHARE_PCT
    developer_share_cents = round(gross_amount_cents * share_pct / 100)
    platform_share_cents = gross_amount_cents - developer_share_cents

    row = MarketplaceRevenueEvent(
        listing_id=listing_id, tenant_id=tenant_id, event_type=event_type, gross_amount_cents=gross_amount_cents,
        developer_share_cents=developer_share_cents, platform_share_cents=platform_share_cents,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id, "listing_id": row.listing_id, "tenant_id": row.tenant_id, "event_type": row.event_type,
        "gross_amount_cents": row.gross_amount_cents, "developer_share_cents": row.developer_share_cents,
        "platform_share_cents": row.platform_share_cents,
    }


def revenue_summary_for_listing(db: Session, listing_id: int) -> dict:
    rows = db.query(MarketplaceRevenueEvent).filter(MarketplaceRevenueEvent.listing_id == listing_id).all()
    return {
        "listing_id": listing_id, "event_count": len(rows),
        "total_gross_cents": sum(r.gross_amount_cents for r in rows),
        "total_developer_share_cents": sum(r.developer_share_cents for r in rows),
        "total_platform_share_cents": sum(r.platform_share_cents for r in rows),
    }
