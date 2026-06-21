"""P6: Intelligence Sharing Consent — HIPAA/BAA compliant per-hospital opt-in."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.schemas.vendor_intelligence import ConsentCreateRequest, ConsentResult

router = APIRouter(prefix="/api/intelligence/consent", tags=["intelligence-consent"])


def _consent_to_result(row) -> ConsentResult:
    modules = json.loads(row.modules or "[]")
    return ConsentResult(
        id=row.id,
        tenant_id=row.tenant_id,
        facility_id=row.facility_id,
        consented_by=row.consented_by,
        consent_version=row.consent_version,
        is_active=row.is_active,
        modules=modules,
        consented_at=row.consented_at.isoformat(),
        revoked_at=row.revoked_at.isoformat() if row.revoked_at else None,
        revoked_by=row.revoked_by,
    )


@router.post("")
def create_consent(
    body: ConsentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create or update intelligence sharing consent for a facility (HIPAA/BAA opt-in)."""
    require_enterprise_auth(request)

    from app.models.vendor_intelligence import IntelligenceSharingConsent

    now = datetime.now(timezone.utc)
    audit_entry = {
        "action": "consent_created",
        "by": body.consented_by,
        "at": now.isoformat(),
        "modules": body.modules,
    }

    # Check if existing consent for this facility
    existing = (
        db.query(IntelligenceSharingConsent)
        .filter(
            IntelligenceSharingConsent.tenant_id == body.tenant_id,
            IntelligenceSharingConsent.facility_id == body.facility_id,
        )
        .first()
    )

    if existing:
        # Update existing: reactivate if previously revoked
        audit_log = json.loads(existing.audit_log or "[]")
        audit_log.append(audit_entry)
        existing.is_active = True
        existing.consented_by = body.consented_by
        existing.consent_version = body.consent_version
        existing.modules = json.dumps(body.modules)
        existing.consented_at = now
        existing.revoked_at = None
        existing.revoked_by = None
        existing.audit_log = json.dumps(audit_log)
        db.commit()
        db.refresh(existing)
        return {"status": "success", "action": "updated", "consent": _consent_to_result(existing).model_dump()}

    # Create new consent record
    row = IntelligenceSharingConsent(
        tenant_id=body.tenant_id,
        facility_id=body.facility_id,
        consented_by=body.consented_by,
        consent_version=body.consent_version,
        is_active=True,
        modules=json.dumps(body.modules),
        consented_at=now,
        audit_log=json.dumps([audit_entry]),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "success", "action": "created", "consent": _consent_to_result(row).model_dump()}


@router.delete("/{facility_id}")
def revoke_consent(
    facility_id: str,
    revoked_by: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Revoke intelligence sharing consent for a facility."""
    require_enterprise_auth(request)

    from app.models.vendor_intelligence import IntelligenceSharingConsent

    # Get tenant_id from auth context (or from header as fallback)
    auth_ctx = require_enterprise_auth(request)
    tenant_id = auth_ctx.tenant_id

    row = (
        db.query(IntelligenceSharingConsent)
        .filter(
            IntelligenceSharingConsent.tenant_id == tenant_id,
            IntelligenceSharingConsent.facility_id == facility_id,
        )
        .first()
    )

    if row is None:
        raise HTTPException(status_code=404, detail="Consent record not found for this facility.")

    now = datetime.now(timezone.utc)
    audit_log = json.loads(row.audit_log or "[]")
    audit_log.append({
        "action": "consent_revoked",
        "by": revoked_by,
        "at": now.isoformat(),
    })
    row.is_active = False
    row.revoked_at = now
    row.revoked_by = revoked_by
    row.audit_log = json.dumps(audit_log)
    db.commit()
    db.refresh(row)
    return {"status": "success", "action": "revoked", "consent": _consent_to_result(row).model_dump()}


@router.get("/{facility_id}")
def get_consent_status(
    facility_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get current consent status for a facility."""
    auth_ctx = require_enterprise_auth(request)
    tenant_id = auth_ctx.tenant_id

    from app.models.vendor_intelligence import IntelligenceSharingConsent

    row = (
        db.query(IntelligenceSharingConsent)
        .filter(
            IntelligenceSharingConsent.tenant_id == tenant_id,
            IntelligenceSharingConsent.facility_id == facility_id,
        )
        .first()
    )

    if row is None:
        return {
            "status": "success",
            "consent_exists": False,
            "facility_id": facility_id,
            "is_active": False,
        }

    return {
        "status": "success",
        "consent_exists": True,
        "facility_id": facility_id,
        "is_active": row.is_active,
        "consent": _consent_to_result(row).model_dump(),
    }
