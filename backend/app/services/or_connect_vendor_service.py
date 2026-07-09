"""v2.8 — LumenAI OR Connect: Vendor Collaboration Portal (Section 7).

Distinct from `manufacturer_portal.py`'s scorecard endpoints, which label a
mock scorecard with the caller's `manufacturer_id` but never actually filter
any query by it. Every function here filters real rows by `vendor_name`
so a vendor can only ever see their own trays, cases, and repair requests —
"restricted to their own trays and organizations" is enforced at the query,
not just claimed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.or_connect import DISCLAIMER, RepairRequest, SurgicalCase, VendorTray
from app.services.or_connect_service import CaseNotFoundError, _row_to_dict


def vendor_portal_view(db: Session, tenant_id: str, vendor_id: str) -> dict:
    trays = (
        db.query(VendorTray)
        .filter(VendorTray.tenant_id == tenant_id, VendorTray.vendor_name == vendor_id)
        .order_by(VendorTray.id.desc())
        .all()
    )
    case_ids = sorted({t.case_id for t in trays})
    cases = (
        db.query(SurgicalCase)
        .filter(SurgicalCase.tenant_id == tenant_id, SurgicalCase.id.in_(case_ids))
        .all()
    ) if case_ids else []
    repairs = (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.vendor_name == vendor_id)
        .order_by(RepairRequest.id.desc())
        .all()
    )

    return {
        "vendor_id": vendor_id,
        "assigned_cases": [_row_to_dict(c) for c in cases],
        "requested_trays": [_row_to_dict(t) for t in trays],
        "replacement_requests": [_row_to_dict(t) for t in trays if t.replacement_requested],
        "delivery_confirmations": [_row_to_dict(t) for t in trays if t.delivery_confirmed_at is not None],
        "repair_requests": [_row_to_dict(r) for r in repairs],
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def _own_tray_or_raise(db: Session, tenant_id: str, vendor_id: str, tray_id: int) -> VendorTray:
    tray = db.query(VendorTray).filter(VendorTray.id == tray_id, VendorTray.tenant_id == tenant_id).first()
    if tray is None:
        raise CaseNotFoundError(f"Vendor tray {tray_id} not found for tenant {tenant_id}.")
    if tray.vendor_name != vendor_id:
        raise PermissionError(f"Vendor {vendor_id} is not authorized for tray {tray_id}.")
    return tray


def confirm_delivery(db: Session, tenant_id: str, vendor_id: str, tray_id: int, *, confirmed_by: str) -> dict:
    tray = _own_tray_or_raise(db, tenant_id, vendor_id, tray_id)
    tray.delivery_confirmed_by = confirmed_by
    tray.delivery_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tray)
    return _row_to_dict(tray)


def request_replacement(db: Session, tenant_id: str, vendor_id: str, tray_id: int, *, notes: str = "") -> dict:
    tray = _own_tray_or_raise(db, tenant_id, vendor_id, tray_id)
    tray.replacement_requested = True
    tray.replacement_notes = notes
    db.commit()
    db.refresh(tray)
    return _row_to_dict(tray)
