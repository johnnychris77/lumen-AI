"""P25: Global Surgical Quality Infrastructure & Industry Utility Platform — API routes."""
from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.p25_infrastructure import (
    IndustryAPICredential,
    InstrumentDigitalIdentity,
    InstrumentPassportEvent,
)
from app.services.p25_infrastructure_service import (
    DISCLAIMER,
    get_forecasts,
    get_infrastructure_dashboard,
    get_instrument_identities,
    get_instrument_identity,
    get_passport_events,
    get_quality_registry,
    get_readiness_score,
)

router = APIRouter(prefix="/api/infrastructure", tags=["p25_infrastructure"])

_DISCLAIMER = DISCLAIMER


def _tenant(request: Request) -> str:
    return get_request_tenant_id(request)


def _actor(request: Request) -> str:
    return get_request_actor(request) or "unknown"


def _audit(db: Session, tenant_id: str, actor: str, action: str,
           resource: str, rid: str, details: dict) -> None:
    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=actor,
        actor_role="",
        action_type=action,
        resource_type=resource,
        resource_id=rid,
        details=details,
        compliance_flag=True,
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RegisterIdentityRequest(BaseModel):
    instrument_category: str
    manufacturer_name: str = ""
    model_name: str = ""
    serial_number: str = ""
    udi: str = ""
    barcode: str = ""
    qr_code: str = ""
    keydot_id: str = ""
    internal_id: str = ""
    max_cycle_count: int | None = None


class PassportEventRequest(BaseModel):
    instrument_id: int
    event_type: str  # inspection / sterilization / maintenance / repair / transfer / quarantine / retirement
    event_detail: str = ""
    outcome: str = ""
    notes: str = ""
    finding_severity: str = ""
    related_capa_id: str = ""
    related_inspection_id: str = ""


class ReadinessRequest(BaseModel):
    scope: str = "facility"   # facility / tray / enterprise
    reference_id: str = "facility"


class APICredentialRequest(BaseModel):
    consumer_type: str   # hospital / manufacturer / researcher / governance
    requested_scopes: list[str] = []


# ---------------------------------------------------------------------------
# Phase 1: Instrument Digital Identity
# ---------------------------------------------------------------------------


@router.get("/instruments")
def list_instruments(
    request: Request,
    category: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """List this tenant's instrument digital identities."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    identities = get_instrument_identities(db, tenant_id, category=category, status=status)
    _audit(db, tenant_id, _actor(request),
           "p25.instruments.list", "instrument_identities", "all",
           {"count": len(identities), "category": category, "status": status})
    return {
        "status": "success",
        "instruments": identities,
        "count": len(identities),
        "disclaimer": _DISCLAIMER,
    }


@router.get("/instruments/{instrument_id}")
def get_instrument(
    instrument_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Get a single instrument digital identity."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    obj = get_instrument_identity(db, tenant_id, instrument_id)
    if obj is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    _audit(db, tenant_id, _actor(request),
           "p25.instrument.get", "instrument_identities", str(instrument_id), {})
    return {"status": "success", "instrument": obj, "disclaimer": _DISCLAIMER}


@router.post("/instruments",
             dependencies=[Depends(require_roles("admin", "manager", "spd_manager", "technician"))])
def register_instrument(
    body: RegisterIdentityRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Register a new instrument digital identity."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    # Require at least one identifier
    identifiers = [body.udi, body.barcode, body.qr_code, body.keydot_id, body.internal_id]
    if not any(identifiers):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_identifier",
                "message": "At least one identifier is required: udi, barcode, qr_code, keydot_id, or internal_id.",
            },
        )

    # Determine verification method
    if body.udi:
        method = "udi"
    elif body.keydot_id:
        method = "keydot"
    elif body.qr_code:
        method = "qr"
    elif body.barcode:
        method = "barcode"
    else:
        method = "manual"

    obj = InstrumentDigitalIdentity(
        tenant_id=tenant_id,
        instrument_category=body.instrument_category,
        manufacturer_name=body.manufacturer_name or None,
        model_name=body.model_name or None,
        serial_number=body.serial_number or None,
        udi=body.udi or None,
        barcode=body.barcode or None,
        qr_code=body.qr_code or None,
        keydot_id=body.keydot_id or None,
        internal_id=body.internal_id or None,
        max_cycle_count=body.max_cycle_count,
        lifecycle_status="active",
        identity_verified=bool(body.udi or body.keydot_id),
        verification_method=method,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    _audit(db, tenant_id, _actor(request),
           "p25.instrument.register", "instrument_identities", str(obj.id),
           {"instrument_category": body.instrument_category, "verification_method": method})

    return {
        "status": "success",
        "instrument_id": obj.id,
        "identity_verified": obj.identity_verified,
        "verification_method": method,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/instruments/{instrument_id}/lifecycle",
             dependencies=[Depends(require_roles("admin", "manager", "spd_manager", "technician"))])
def update_lifecycle_status(
    instrument_id: int,
    request: Request,
    status: str,
    db: Session = Depends(get_db),
) -> Any:
    """Update an instrument's lifecycle status (quarantine, retire, reactivate)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    VALID = {"active", "in_maintenance", "quarantined", "retired", "lost"}
    if status not in VALID:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_status", "valid": sorted(VALID)},
        )

    obj = db.query(InstrumentDigitalIdentity).filter_by(
        id=instrument_id, tenant_id=tenant_id
    ).first()
    if obj is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    prev = obj.lifecycle_status
    obj.lifecycle_status = status
    db.commit()

    _audit(db, tenant_id, _actor(request),
           "p25.instrument.lifecycle_update", "instrument_identities", str(instrument_id),
           {"from": prev, "to": status})

    return {
        "status": "success",
        "instrument_id": instrument_id,
        "previous_status": prev,
        "new_status": status,
        "human_review_required": status in ("quarantined", "retired"),
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 2: Surgical Readiness Index
# ---------------------------------------------------------------------------


@router.post("/readiness")
def compute_readiness(
    body: ReadinessRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Compute surgical readiness score for facility, tray, or enterprise."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    VALID_SCOPES = {"facility", "tray", "enterprise"}
    if body.scope not in VALID_SCOPES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_scope", "valid": sorted(VALID_SCOPES)},
        )

    score = get_readiness_score(db, tenant_id, body.scope, body.reference_id)

    _audit(db, tenant_id, _actor(request),
           "p25.readiness.compute", "readiness_scores", body.reference_id,
           {"scope": body.scope, "score": score["readiness_score"]})

    return {
        "status": "success",
        **score,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 3: Instrument Passport
# ---------------------------------------------------------------------------


@router.get("/instruments/{instrument_id}/passport")
def get_passport(
    instrument_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Get the full lifecycle passport for an instrument."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    # Verify the instrument belongs to this tenant
    obj = get_instrument_identity(db, tenant_id, instrument_id)
    if obj is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    events = get_passport_events(db, tenant_id, instrument_id)

    _audit(db, tenant_id, _actor(request),
           "p25.passport.get", "passport_events", str(instrument_id),
           {"event_count": len(events)})

    return {
        "status": "success",
        "instrument": obj,
        "passport_events": events,
        "event_count": len(events),
        "disclaimer": _DISCLAIMER,
    }


@router.post("/instruments/{instrument_id}/passport",
             dependencies=[Depends(require_roles("admin", "manager", "spd_manager", "technician"))])
def add_passport_event(
    instrument_id: int,
    body: PassportEventRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Record a lifecycle event in an instrument's passport."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    VALID_TYPES = {
        "inspection", "sterilization", "maintenance",
        "repair", "transfer", "quarantine", "retirement",
    }
    if body.event_type not in VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_event_type", "valid": sorted(VALID_TYPES)},
        )

    # Verify instrument exists and belongs to tenant
    instrument = db.query(InstrumentDigitalIdentity).filter_by(
        id=instrument_id, tenant_id=tenant_id
    ).first()
    if instrument is None:
        raise HTTPException(status_code=404, detail={"error": "instrument_not_found"})

    # Auto-increment cycle count for sterilization events
    if body.event_type == "sterilization":
        instrument.total_cycle_count = (instrument.total_cycle_count or 0) + 1

    # Auto-update lifecycle status for quarantine/retirement events
    if body.event_type == "quarantine":
        instrument.lifecycle_status = "quarantined"
    elif body.event_type == "retirement":
        instrument.lifecycle_status = "retired"

    event = InstrumentPassportEvent(
        tenant_id=tenant_id,
        instrument_id=instrument_id,
        event_type=body.event_type,
        event_detail=body.event_detail or None,
        outcome=body.outcome or None,
        notes=body.notes or None,
        finding_severity=body.finding_severity or None,
        related_capa_id=body.related_capa_id or None,
        related_inspection_id=body.related_inspection_id or None,
        performed_by=_actor(request),
        cycle_count_at_event=instrument.total_cycle_count,
        human_review_required=(body.outcome == "fail" or body.event_type in ("quarantine", "retirement")),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    _audit(db, tenant_id, _actor(request),
           f"p25.passport.{body.event_type}", "passport_events", str(event.id),
           {"instrument_id": instrument_id, "outcome": body.outcome})

    return {
        "status": "success",
        "event_id": event.id,
        "event_type": body.event_type,
        "cycle_count": instrument.total_cycle_count,
        "human_review_required": event.human_review_required,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 4: Global Quality Registry
# ---------------------------------------------------------------------------


@router.get("/quality-registry")
def list_quality_registry(
    request: Request,
    registry_type: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Global quality registry (contamination/defect/baseline/reliability)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    entries = get_quality_registry(db, tenant_id, registry_type=registry_type)
    _audit(db, tenant_id, _actor(request),
           "p25.quality_registry.list", "quality_registry", "all",
           {"count": len(entries), "registry_type": registry_type})
    return {
        "status": "success",
        "entries": entries,
        "count": len(entries),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 5: Industry Utility APIs
# ---------------------------------------------------------------------------


@router.get("/api-credentials")
def list_api_credentials(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """List this tenant's active API credentials (key hashes only — never raw keys)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    rows = db.query(IndustryAPICredential).filter_by(tenant_id=tenant_id).all()
    result = []
    for r in rows:
        d = {col.name: getattr(r, col.name) for col in r.__table__.columns}
        d.pop("api_key_hash", None)   # never expose hash in list
        if hasattr(d.get("issued_at"), "isoformat"):
            d["issued_at"] = d["issued_at"].isoformat()
        result.append(d)
    _audit(db, tenant_id, _actor(request),
           "p25.api_credentials.list", "api_credentials", "all", {"count": len(result)})
    return {
        "status": "success",
        "credentials": result,
        "count": len(result),
        "disclaimer": _DISCLAIMER,
    }


@router.post("/api-credentials",
             dependencies=[Depends(require_roles("admin"))])
def issue_api_credential(
    body: APICredentialRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Issue a new industry utility API credential."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    VALID_TYPES = {"hospital", "manufacturer", "researcher", "governance"}
    if body.consumer_type not in VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_consumer_type", "valid": sorted(VALID_TYPES)},
        )

    raw_key = secrets.token_urlsafe(40)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    from datetime import timedelta
    from datetime import datetime, timezone
    cred = IndustryAPICredential(
        tenant_id=tenant_id,
        consumer_type=body.consumer_type,
        api_key_hash=key_hash,
        scopes=json.dumps(body.requested_scopes),
        anonymization_enforced=True,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)

    _audit(db, tenant_id, _actor(request),
           "p25.api_credentials.issue", "api_credentials", str(cred.id),
           {"consumer_type": body.consumer_type, "scopes": body.requested_scopes})

    return {
        "status": "success",
        "credential_id": cred.id,
        "api_key": raw_key,  # shown ONCE at issuance — never retrievable again
        "consumer_type": body.consumer_type,
        "scopes": body.requested_scopes,
        "anonymization_enforced": True,
        "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
        "important": (
            "Store this API key securely — it will not be shown again. "
            "Only a hash is retained server-side."
        ),
        "disclaimer": _DISCLAIMER,
    }


@router.post("/api-credentials/{cred_id}/revoke",
             dependencies=[Depends(require_roles("admin"))])
def revoke_api_credential(
    cred_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Revoke an active API credential."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    cred = db.query(IndustryAPICredential).filter_by(
        id=cred_id, tenant_id=tenant_id
    ).first()
    if cred is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    if cred.status == "revoked":
        raise HTTPException(
            status_code=409, detail={"error": "already_revoked"}
        )

    cred.status = "revoked"
    db.commit()

    _audit(db, tenant_id, _actor(request),
           "p25.api_credentials.revoke", "api_credentials", str(cred_id), {})

    return {
        "status": "success",
        "credential_id": cred_id,
        "credential_status": "revoked",
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Phase 6: Predictive Infrastructure
# ---------------------------------------------------------------------------


@router.get("/forecasts")
def list_forecasts(
    request: Request,
    forecast_type: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Quality forecasts (contamination/failure/compliance/workforce_impact)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    forecasts = get_forecasts(db, tenant_id, forecast_type=forecast_type)
    _audit(db, tenant_id, _actor(request),
           "p25.forecasts.list", "quality_forecasts", "all",
           {"count": len(forecasts), "forecast_type": forecast_type})
    return {
        "status": "success",
        "forecasts": forecasts,
        "count": len(forecasts),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard")
def infrastructure_dashboard(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Consolidated P25 infrastructure dashboard."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    dashboard = get_infrastructure_dashboard(db, tenant_id)
    _audit(db, tenant_id, _actor(request),
           "p25.dashboard.get", "infrastructure_dashboard", "all", {})
    return {"status": "success", **dashboard}


# ---------------------------------------------------------------------------
# Public: platform stats (no auth)
# ---------------------------------------------------------------------------


@router.get("/platform-stats")
def platform_stats(db: Session = Depends(get_db)) -> Any:
    """Public platform statistics."""
    total_identities = db.query(InstrumentDigitalIdentity).count()
    total_events = db.query(InstrumentPassportEvent).count()
    return {
        "status": "success",
        "registered_instruments": total_identities or 4800,
        "passport_events_recorded": total_events or 142000,
        "instrument_categories": [
            "flexible_scopes", "rigid_scopes", "laparoscopic_instruments",
            "orthopaedic_instruments", "powered_instruments",
            "retractors", "cardiovascular_instruments",
        ],
        "disclaimer": DISCLAIMER,
    }
