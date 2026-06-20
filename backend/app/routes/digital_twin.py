"""P10: Digital Twin of SPD Operations — API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.schemas.digital_twin import (
    AcknowledgeAlertRequest,
    CompleteFlowRequest,
    LogFlowRequest,
    WhatIfRequest,
)
from app.services.digital_twin_engine import (
    acknowledge_alert,
    complete_flow,
    compute_twin_dashboard,
    get_alerts,
    get_instrument_flow,
    get_stations,
    get_twin_state,
    list_whatif_scenarios,
    log_instrument_flow,
    simulate_whatif,
)
from app.tier_guard import require_tier

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])


@router.get("/state")
def twin_state(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_state", db)
    result = get_twin_state(tenant_id, facility_id, db)
    return result.model_dump()


@router.get("/stations")
def list_stations(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_state", db)
    stations = get_stations(tenant_id, facility_id, db)
    return [s.model_dump() for s in stations]


@router.get("/flow")
def list_flow(
    request: Request,
    facility_id: str = Query(default=""),
    limit: int = Query(default=20),
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_state", db)
    flows = get_instrument_flow(tenant_id, facility_id, limit, db)
    return [f.model_dump() for f in flows]


@router.post("/flow")
def log_flow(
    request: Request,
    body: LogFlowRequest,
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_state", db)
    result = log_instrument_flow(
        tenant_id=tenant_id,
        facility_id="",
        instrument_name=body.instrument_name,
        instrument_id=body.instrument_id,
        from_station=body.from_station,
        to_station=body.to_station,
        station_type=body.station_type,
        notes=body.notes,
        db=db,
    )
    return result.model_dump()


@router.post("/flow/{flow_id}/complete")
def complete_flow_endpoint(
    flow_id: int,
    request: Request,
    body: CompleteFlowRequest,
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_state", db)
    result = complete_flow(flow_id, body.outcome, body.notes, tenant_id, db)
    return result.model_dump()


@router.get("/alerts")
def list_alerts(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_alerts", db)
    alerts = get_alerts(tenant_id, facility_id, db)
    return [a.model_dump() for a in alerts]


@router.post("/alerts/{alert_id}/acknowledge")
def ack_alert(
    alert_id: int,
    request: Request,
    body: AcknowledgeAlertRequest,
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_alerts", db)
    result = acknowledge_alert(alert_id, body.acknowledged_by, tenant_id, db)
    return result.model_dump()


@router.post("/whatif")
def run_whatif(
    request: Request,
    body: WhatIfRequest,
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_whatif", db)
    result = simulate_whatif(tenant_id, body, db)
    return result.model_dump()


@router.get("/whatif")
def list_whatif(
    request: Request,
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_whatif", db)
    scenarios = list_whatif_scenarios(tenant_id, db)
    return [s.model_dump() for s in scenarios]


@router.get("/dashboard")
def twin_dashboard(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "twin_dashboard", db)
    result = compute_twin_dashboard(tenant_id, facility_id, db)
    return result.model_dump()
