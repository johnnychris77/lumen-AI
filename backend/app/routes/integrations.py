"""P17: Healthcare Quality & Safety Ecosystem Integration routes."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.integrations import (
    ExternalSystemConnection,
    InfectionPreventionEventRecord,
    IntegrationImportRun,
    InstrumentTrackingRecord,
    PatientImpactCorrelationCandidate,
    QualitySafetyEventRecord,
)
from app.services.integration_correlation_service import (
    DISCLAIMER,
    _get_connector,
    get_integration_dashboard,
    run_correlation,
)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def _tenant(request: Request) -> str:
    return get_request_tenant_id(request)


def _actor(request: Request) -> str:
    return get_request_actor(request) or "unknown"


def _to_dict(obj: Any) -> dict:
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CreateConnectionRequest(BaseModel):
    system_name: str
    system_category: str
    connector_type: str = "api_pull"
    endpoint_url: Optional[str] = None
    auth_type: Optional[str] = None
    config_json: Optional[str] = None
    facility_id: Optional[str] = None


class ImportEventsRequest(BaseModel):
    source_system: str
    system_category: str
    events: List[dict] = []


class CorrelateRequest(BaseModel):
    facility_id: str = ""
    days_back: int = 30


# ---------------------------------------------------------------------------
# System connections
# ---------------------------------------------------------------------------


@router.get("/systems")
def list_systems(request: Request, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    connections = (
        db.query(ExternalSystemConnection)
        .filter(ExternalSystemConnection.tenant_id == tenant_id)
        .order_by(ExternalSystemConnection.created_at.desc())
        .all()
    )

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.systems.list",
        resource_type="external_system_connections",
        resource_id="all",
        details={"count": len(connections)},
    )
    return {"status": "success", "systems": [_to_dict(c) for c in connections], "count": len(connections)}


@router.post("/systems")
def create_system(request: Request, body: CreateConnectionRequest, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    conn = ExternalSystemConnection(
        tenant_id=tenant_id,
        facility_id=body.facility_id,
        system_name=body.system_name,
        system_category=body.system_category,
        connector_type=body.connector_type,
        endpoint_url=body.endpoint_url,
        auth_type=body.auth_type,
        config_json=body.config_json,
        connection_status="configured",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.systems.create",
        resource_type="external_system_connections",
        resource_id=str(conn.id),
        details={"system_name": body.system_name, "system_category": body.system_category},
    )
    return {"status": "success", "system": _to_dict(conn)}


@router.post("/systems/{system_id}/test")
def test_system_connection(system_id: int, request: Request, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    conn = (
        db.query(ExternalSystemConnection)
        .filter(
            ExternalSystemConnection.id == system_id,
            ExternalSystemConnection.tenant_id == tenant_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="System connection not found.")

    connector = _get_connector(conn.system_name, tenant_id, conn.facility_id or "", {})
    result = connector.test_connection()

    conn.last_test_at = datetime.utcnow()
    conn.last_test_status = "success" if result.get("success") else "failure"
    if result.get("success"):
        conn.consecutive_errors = 0
    else:
        conn.consecutive_errors = (conn.consecutive_errors or 0) + 1
    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.systems.test",
        resource_type="external_system_connections",
        resource_id=str(system_id),
        details=result,
    )
    return {"status": "success", "test_result": result}


@router.post("/systems/{system_id}/preview-import")
def preview_import(system_id: int, request: Request, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    conn = (
        db.query(ExternalSystemConnection)
        .filter(
            ExternalSystemConnection.id == system_id,
            ExternalSystemConnection.tenant_id == tenant_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="System connection not found.")

    connector = _get_connector(conn.system_name, tenant_id, conn.facility_id or "", {})
    result = connector.preview_import()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.systems.preview_import",
        resource_type="external_system_connections",
        resource_id=str(system_id),
        details={"total_available": result.get("total_available"), "sample_count": len(result.get("records", []))},
    )
    return {"status": "success", **result}


@router.post("/systems/{system_id}/run-import")
def run_import(system_id: int, request: Request, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    conn = (
        db.query(ExternalSystemConnection)
        .filter(
            ExternalSystemConnection.id == system_id,
            ExternalSystemConnection.tenant_id == tenant_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="System connection not found.")

    import_run = IntegrationImportRun(
        tenant_id=tenant_id,
        connection_id=conn.id,
        system_name=conn.system_name,
        import_type="full",
        status="running",
    )
    db.add(import_run)
    db.commit()
    db.refresh(import_run)

    connector = _get_connector(conn.system_name, tenant_id, conn.facility_id or "", {})
    result = connector.run_import()

    import_run.status = "completed"
    import_run.records_attempted = result.get("imported", 0) + result.get("failed", 0)
    import_run.records_imported = result.get("imported", 0)
    import_run.records_failed = result.get("failed", 0)
    import_run.completed_at = datetime.utcnow()
    conn.last_import_at = datetime.utcnow()
    conn.total_records_imported = (conn.total_records_imported or 0) + result.get("imported", 0)
    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.systems.run_import",
        resource_type="integration_import_runs",
        resource_id=import_run.import_id,
        details=result,
    )
    return {"status": "success", "import_id": import_run.import_id, **result}


# ---------------------------------------------------------------------------
# Import runs
# ---------------------------------------------------------------------------


@router.get("/imports")
def list_imports(
    request: Request,
    status: str = Query(default=""),
    system_name: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    q = db.query(IntegrationImportRun).filter(IntegrationImportRun.tenant_id == tenant_id)
    if status:
        q = q.filter(IntegrationImportRun.status == status)
    if system_name:
        q = q.filter(IntegrationImportRun.system_name == system_name)
    runs = q.order_by(IntegrationImportRun.started_at.desc()).limit(limit).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.imports.list",
        resource_type="integration_import_runs",
        resource_id="all",
        details={"count": len(runs)},
    )
    return {"status": "success", "imports": [_to_dict(r) for r in runs], "count": len(runs)}


@router.get("/imports/{import_id}")
def get_import(import_id: str, request: Request, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    run = (
        db.query(IntegrationImportRun)
        .filter(
            IntegrationImportRun.import_id == import_id,
            IntegrationImportRun.tenant_id == tenant_id,
        )
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Import run not found.")

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.imports.detail",
        resource_type="integration_import_runs",
        resource_id=import_id,
    )
    return {"status": "success", "import_run": _to_dict(run)}


# ---------------------------------------------------------------------------
# External events
# ---------------------------------------------------------------------------


@router.get("/external-events")
def list_external_events(
    request: Request,
    facility_id: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    qs_q = db.query(QualitySafetyEventRecord).filter(QualitySafetyEventRecord.tenant_id == tenant_id)
    ip_q = db.query(InfectionPreventionEventRecord).filter(InfectionPreventionEventRecord.tenant_id == tenant_id)
    spd_q = db.query(InstrumentTrackingRecord).filter(InstrumentTrackingRecord.tenant_id == tenant_id)

    if facility_id:
        qs_q = qs_q.filter(QualitySafetyEventRecord.facility_id == facility_id)
        ip_q = ip_q.filter(InfectionPreventionEventRecord.facility_id == facility_id)
        spd_q = spd_q.filter(InstrumentTrackingRecord.facility_id == facility_id)

    qs_events = [dict(record_type="quality_safety", **_to_dict(r)) for r in qs_q.limit(limit).all()]
    ip_events = [dict(record_type="infection_prevention", **_to_dict(r)) for r in ip_q.limit(limit).all()]
    spd_events = [dict(record_type="spd_tracking", **_to_dict(r)) for r in spd_q.limit(limit).all()]

    all_events = qs_events + ip_events + spd_events

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.external_events.list",
        resource_type="external_events",
        resource_id="all",
        details={"count": len(all_events)},
    )
    return {"status": "success", "events": all_events, "count": len(all_events)}


_PHI_FORBIDDEN = {"patient_id", "mrn", "dob", "patient_name", "name", "ssn"}


@router.post("/external-events/import")
def import_external_events(request: Request, body: ImportEventsRequest, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    imported = 0
    errors = []

    for raw_event in body.events:
        # Strip any PHI fields that shouldn't be here
        for phi_key in _PHI_FORBIDDEN:
            raw_event.pop(phi_key, None)

        payload_str = str(sorted(raw_event.items()))
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        try:
            ts_raw = raw_event.get("event_timestamp")
            if isinstance(ts_raw, str):
                event_ts = datetime.fromisoformat(ts_raw)
            else:
                event_ts = datetime.utcnow()

            if body.system_category == "quality_safety":
                rec = QualitySafetyEventRecord(
                    tenant_id=tenant_id,
                    facility_id=raw_event.get("facility_id"),
                    source_system=body.source_system,
                    source_record_id=raw_event.get("source_record_id"),
                    source_event_type=raw_event.get("source_event_type", "adverse_event"),
                    event_timestamp=event_ts,
                    event_category=raw_event.get("event_category"),
                    event_severity=raw_event.get("event_severity"),
                    instrument_reference=raw_event.get("instrument_reference"),
                    tray_reference=raw_event.get("tray_reference"),
                    de_identified=True,
                    capa_id=raw_event.get("capa_id"),
                    rca_status=raw_event.get("rca_status"),
                    raw_payload_hash=payload_hash,
                )
                db.add(rec)
            elif body.system_category == "infection_prevention":
                rec = InfectionPreventionEventRecord(
                    tenant_id=tenant_id,
                    facility_id=raw_event.get("facility_id"),
                    source_system=body.source_system,
                    source_record_id=raw_event.get("source_record_id"),
                    source_event_type=raw_event.get("source_event_type", "hai_alert"),
                    event_timestamp=event_ts,
                    pathogen=raw_event.get("pathogen"),
                    procedure_type=raw_event.get("procedure_type"),
                    service_line=raw_event.get("service_line"),
                    instrument_reference=raw_event.get("instrument_reference"),
                    de_identified=True,
                    raw_payload_hash=payload_hash,
                )
                db.add(rec)
            else:
                rec = InstrumentTrackingRecord(
                    tenant_id=tenant_id,
                    facility_id=raw_event.get("facility_id"),
                    source_system=body.source_system,
                    source_record_id=raw_event.get("source_record_id"),
                    source_event_type=raw_event.get("source_event_type", "checkout"),
                    event_timestamp=event_ts,
                    instrument_id=raw_event.get("instrument_id"),
                    udi=raw_event.get("udi"),
                    barcode=raw_event.get("barcode"),
                    tray_id=raw_event.get("tray_id"),
                    sterilization_status=raw_event.get("sterilization_status"),
                    vendor_id=raw_event.get("vendor_id"),
                    raw_payload_hash=payload_hash,
                )
                db.add(rec)
            imported += 1
        except Exception as exc:
            errors.append(str(exc))

    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.external_events.import",
        resource_type="external_events",
        resource_id="",
        details={"source_system": body.source_system, "imported": imported, "errors": len(errors)},
    )
    return {
        "status": "success",
        "imported": imported,
        "failed": len(errors),
        "errors": errors,
        "source_system": body.source_system,
    }


# ---------------------------------------------------------------------------
# Correlation candidates
# ---------------------------------------------------------------------------


@router.get("/correlation-candidates")
def list_correlation_candidates(
    request: Request,
    status: str = Query(default=""),
    min_score: float = Query(default=0.0),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    q = db.query(PatientImpactCorrelationCandidate).filter(
        PatientImpactCorrelationCandidate.tenant_id == tenant_id
    )
    if status:
        q = q.filter(PatientImpactCorrelationCandidate.human_review_status == status)
    if min_score > 0:
        q = q.filter(PatientImpactCorrelationCandidate.association_score >= min_score)
    candidates = q.order_by(PatientImpactCorrelationCandidate.created_at.desc()).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.correlation.list",
        resource_type="patient_impact_correlation_candidates",
        resource_id="all",
        details={"count": len(candidates)},
    )
    return {
        "status": "success",
        "candidates": [_to_dict(c) for c in candidates],
        "count": len(candidates),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


@router.post("/correlation-candidates/run")
def run_correlation_endpoint(
    request: Request,
    body: CorrelateRequest,
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    result = run_correlation(
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
        action_type="integrations.correlation.run",
        resource_type="patient_impact_correlation_candidates",
        resource_id="",
        details=result,
    )
    return {
        "status": "success",
        "human_review_required": True,
        **result,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard")
def integration_dashboard(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    dashboard = get_integration_dashboard(db, tenant_id, facility_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.dashboard.view",
        resource_type="integrations_dashboard",
        resource_id="",
        details={"data_source": dashboard.get("data_source")},
    )
    return {"status": "success", **dashboard}
