"""P16: Patient Safety Intelligence Integration — API routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.patient_safety import (
    CAPAEffectivenessSignal,
    ExecutiveRiskSignal,
    InfectionPreventionSignal,
    InstrumentQualitySignal,
    NearMissCorrelation,
    QualityInvestigation,
)
from app.services.patient_safety_engine import (
    DISCLAIMER,
    correlate_signals,
    get_dashboard_rollup,
    import_external_events,
)
from app.tier_guard import require_tier

router = APIRouter(prefix="/api/patient-safety", tags=["patient-safety"])

_NO_CAUSATION_DISCLAIMER = DISCLAIMER


def _tenant(request: Request) -> str:
    return get_request_tenant_id(request)


def _actor(request: Request) -> str:
    return get_request_actor(request) or "unknown"


def _to_dict(obj: Any) -> dict:
    """Serialize a SQLAlchemy model to a plain dict."""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CorrelateRequest(BaseModel):
    facility_id: str = ""
    days_back: int = 90


class ImportEventsRequest(BaseModel):
    facility_id: str = ""
    source_system: str = "safecare"
    events: list[dict] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/signals")
def list_signals(
    request: Request,
    facility_id: str = Query(default=""),
    risk_tier: str = Query(default=""),
    event_source: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List InstrumentQualitySignals for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    q = db.query(InstrumentQualitySignal).filter(
        InstrumentQualitySignal.tenant_id == tenant_id
    )
    if facility_id:
        q = q.filter(InstrumentQualitySignal.facility_id == facility_id)
    if risk_tier:
        q = q.filter(InstrumentQualitySignal.risk_tier == risk_tier)
    if event_source:
        q = q.filter(InstrumentQualitySignal.event_source == event_source)

    signals = q.order_by(InstrumentQualitySignal.created_at.desc()).offset(offset).limit(limit).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.signals.list",
        resource_type="instrument_quality_signals",
        resource_id="all",
        details={"count": len(signals)},
    )

    return {
        "status": "success",
        "signals": [_to_dict(s) for s in signals],
        "count": len(signals),
        "human_review_required": True,
        "disclaimer": _NO_CAUSATION_DISCLAIMER,
    }


@router.get("/signals/{signal_id}")
def get_signal(
    signal_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Return a single InstrumentQualitySignal."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    sig = (
        db.query(InstrumentQualitySignal)
        .filter(
            InstrumentQualitySignal.signal_id == signal_id,
            InstrumentQualitySignal.tenant_id == tenant_id,
        )
        .first()
    )
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found.")

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.signals.detail",
        resource_type="instrument_quality_signals",
        resource_id=signal_id,
    )

    return {
        "status": "success",
        "signal": _to_dict(sig),
        "human_review_required": True,
        "disclaimer": _NO_CAUSATION_DISCLAIMER,
    }


@router.post("/correlate")
def correlate(
    request: Request,
    body: CorrelateRequest,
    db: Session = Depends(get_db),
):
    """Run the correlation engine for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    result = correlate_signals(
        db=db,
        tenant_id=tenant_id,
        facility_id=body.facility_id,
        days_back=body.days_back,
    )

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.correlate",
        resource_type="correlation_engine",
        resource_id="",
        details=result,
    )

    return {"status": "success", **result}


@router.get("/near-misses")
def list_near_misses(
    request: Request,
    facility_id: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List NearMissCorrelations for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    q = db.query(NearMissCorrelation).filter(NearMissCorrelation.tenant_id == tenant_id)
    if facility_id:
        q = q.filter(NearMissCorrelation.facility_id == facility_id)

    items = q.order_by(NearMissCorrelation.created_at.desc()).limit(limit).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.near_misses.list",
        resource_type="near_miss_correlations",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "near_misses": [_to_dict(i) for i in items],
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _NO_CAUSATION_DISCLAIMER,
    }


@router.get("/quality-investigations")
def list_quality_investigations(
    request: Request,
    status: str = Query(default=""),
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """List QualityInvestigations for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    q = db.query(QualityInvestigation).filter(QualityInvestigation.tenant_id == tenant_id)
    if status:
        q = q.filter(QualityInvestigation.investigation_status == status)
    if facility_id:
        q = q.filter(QualityInvestigation.facility_id == facility_id)

    items = q.order_by(QualityInvestigation.created_at.desc()).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.quality_investigations.list",
        resource_type="quality_investigations",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "investigations": [_to_dict(i) for i in items],
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _NO_CAUSATION_DISCLAIMER,
    }


@router.get("/executive-risk")
def list_executive_risk(
    request: Request,
    risk_tier: str = Query(default=""),
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """List ExecutiveRiskSignals for this tenant (enterprise tier required)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)
    require_tier(tenant_id, "executive_risk", db)

    q = db.query(ExecutiveRiskSignal).filter(ExecutiveRiskSignal.tenant_id == tenant_id)
    if risk_tier:
        q = q.filter(ExecutiveRiskSignal.risk_tier == risk_tier)
    if facility_id:
        q = q.filter(ExecutiveRiskSignal.facility_id == facility_id)

    items = q.order_by(ExecutiveRiskSignal.created_at.desc()).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.executive_risk.list",
        resource_type="executive_risk_signals",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "executive_risks": [_to_dict(i) for i in items],
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _NO_CAUSATION_DISCLAIMER,
    }


@router.post("/events/import")
def import_events(
    request: Request,
    body: ImportEventsRequest,
    db: Session = Depends(get_db),
):
    """Import external safety events and generate quality signals."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    # Tag each event with the source system
    for ev in body.events:
        ev.setdefault("source_system", body.source_system)

    result = import_external_events(
        db=db,
        tenant_id=tenant_id,
        facility_id=body.facility_id,
        events=body.events,
    )

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.events.import",
        resource_type="external_event_imports",
        resource_id="",
        details={
            "source_system": body.source_system,
            "imported": result["imported"],
            "signals_generated": result["signals_generated"],
        },
    )

    return {"status": "success", **result}


@router.get("/dashboard")
def dashboard(
    request: Request,
    facility_id: str = Query(default=""),
    period_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Patient safety KPI dashboard rollup."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    rollup = get_dashboard_rollup(
        db=db,
        tenant_id=tenant_id,
        facility_id=facility_id,
        period_days=period_days,
    )

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.dashboard.view",
        resource_type="patient_safety_dashboard",
        resource_id="",
    )

    return {"status": "success", **rollup}


@router.get("/infection-prevention")
def list_infection_prevention(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """List InfectionPreventionSignals for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    q = db.query(InfectionPreventionSignal).filter(
        InfectionPreventionSignal.tenant_id == tenant_id
    )
    if facility_id:
        q = q.filter(InfectionPreventionSignal.facility_id == facility_id)

    items = q.order_by(InfectionPreventionSignal.created_at.desc()).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.infection_prevention.list",
        resource_type="infection_prevention_signals",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "signals": [_to_dict(i) for i in items],
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _NO_CAUSATION_DISCLAIMER,
    }


@router.get("/capa-effectiveness")
def list_capa_effectiveness(
    request: Request,
    capa_status: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """List CAPAEffectivenessSignals for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    q = db.query(CAPAEffectivenessSignal).filter(
        CAPAEffectivenessSignal.tenant_id == tenant_id
    )
    if capa_status:
        q = q.filter(CAPAEffectivenessSignal.capa_status == capa_status)

    items = q.order_by(CAPAEffectivenessSignal.created_at.desc()).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="patient_safety.capa_effectiveness.list",
        resource_type="capa_effectiveness_signals",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "capa_signals": [_to_dict(i) for i in items],
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _NO_CAUSATION_DISCLAIMER,
    }
