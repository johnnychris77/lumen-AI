"""P17: Healthcare Quality & Safety Ecosystem Integration routes."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
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
    IntegrationErrorRecord,
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

# ---------------------------------------------------------------------------
# Connector catalog
# ---------------------------------------------------------------------------

CONNECTOR_CATALOG = [
    {"system_name": "censitrac", "display_name": "CensiTrac", "category": "spd_tracking", "connector_types": ["csv", "api_pull"], "status": "available", "description": "Instrument tracking, tray management, sterilization cycles"},
    {"system_name": "spm", "display_name": "SPM", "category": "spd_tracking", "connector_types": ["csv", "api_pull"], "status": "available"},
    {"system_name": "readyset", "display_name": "ReadySet Surgical", "category": "spd_tracking", "connector_types": ["csv"], "status": "available"},
    {"system_name": "abacus", "display_name": "Abacus", "category": "spd_tracking", "connector_types": ["csv"], "status": "available"},
    {"system_name": "vendormade", "display_name": "VendorMade", "category": "vendor", "connector_types": ["api_pull", "webhook"], "status": "available"},
    {"system_name": "safecare", "display_name": "SafeCare", "category": "quality_safety", "connector_types": ["api_pull", "webhook"], "status": "available", "baa_required": True},
    {"system_name": "rldatix", "display_name": "RLDatix", "category": "quality_safety", "connector_types": ["api_pull", "webhook"], "status": "available", "baa_required": True},
    {"system_name": "midas", "display_name": "MIDAS", "category": "quality_safety", "connector_types": ["api_pull", "csv"], "status": "available", "baa_required": True},
    {"system_name": "verge", "display_name": "Verge Health", "category": "quality_safety", "connector_types": ["api_pull"], "status": "beta", "baa_required": True},
    {"system_name": "icnet", "display_name": "ICNet", "category": "infection_prevention", "connector_types": ["api_pull", "webhook"], "status": "available", "baa_required": True},
    {"system_name": "vigilanz", "display_name": "VigiLanz", "category": "infection_prevention", "connector_types": ["api_pull", "webhook"], "status": "available", "baa_required": True},
    {"system_name": "theradoc", "display_name": "Theradoc", "category": "infection_prevention", "connector_types": ["api_pull"], "status": "available", "baa_required": True},
    {"system_name": "epic", "display_name": "Epic (SMART on FHIR)", "category": "ehr", "connector_types": ["api_pull"], "status": "roadmap", "baa_required": True},
    {"system_name": "cerner", "display_name": "Oracle Health / Cerner", "category": "ehr", "connector_types": ["api_pull"], "status": "roadmap", "baa_required": True},
    {"system_name": "meditech", "display_name": "Meditech", "category": "ehr", "connector_types": ["csv"], "status": "roadmap", "baa_required": True},
]

_BAA_REQUIRED_CATEGORIES = {"quality_safety", "infection_prevention", "ehr"}

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

    # BAA gate: quality/IP/EHR systems require a signed BAA
    if body.system_category in _BAA_REQUIRED_CATEGORIES:
        try:
            from app.models.tenant_subscription_p14 import TenantSubscriptionP14
            sub = db.query(TenantSubscriptionP14).filter(
                TenantSubscriptionP14.tenant_id == tenant_id
            ).first()
            if not sub or not sub.hipaa_baa_signed_at:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "hipaa_baa_required",
                        "message": "A signed HIPAA Business Associate Agreement is required before connecting quality, infection prevention, or EHR systems.",
                        "action": "POST /api/tenant/hipaa-baa to record your BAA",
                    },
                )
        except HTTPException:
            raise
        except Exception:
            pass  # If subscription model not available, allow through

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


# ---------------------------------------------------------------------------
# Connector catalog (public)
# ---------------------------------------------------------------------------


@router.get("/catalog")
def get_connector_catalog():
    """Public catalog of all supported connectors — no auth required."""
    return {"status": "success", "connectors": CONNECTOR_CATALOG, "count": len(CONNECTOR_CATALOG)}


# ---------------------------------------------------------------------------
# Per-connection health endpoint
# ---------------------------------------------------------------------------


def _compute_health_status(conn: ExternalSystemConnection) -> str:
    if conn.last_import_at is None:
        return "unknown"
    if conn.connection_status == "error":
        return "error"
    errors = conn.consecutive_errors or 0
    now = datetime.utcnow()
    last = conn.last_import_at
    hours_since = (now - last).total_seconds() / 3600 if last else 9999
    if errors >= 3 or hours_since > 72:
        return "error"
    if errors >= 1 or hours_since > 26:
        return "degraded"
    return "healthy"


@router.get("/systems/{system_id}/health")
def get_system_health(system_id: int, request: Request, db: Session = Depends(get_db)):
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

    last_10_runs = (
        db.query(IntegrationImportRun)
        .filter(
            IntegrationImportRun.connection_id == system_id,
            IntegrationImportRun.tenant_id == tenant_id,
        )
        .order_by(IntegrationImportRun.started_at.desc())
        .limit(10)
        .all()
    )

    health_status = _compute_health_status(conn)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.systems.health",
        resource_type="external_system_connections",
        resource_id=str(system_id),
        details={"health_status": health_status},
    )
    return {
        "status": "success",
        "system_id": conn.id,
        "system_name": conn.system_name,
        "connection_status": conn.connection_status,
        "last_import_at": conn.last_import_at.isoformat() if conn.last_import_at else None,
        "consecutive_errors": conn.consecutive_errors or 0,
        "total_records_imported": conn.total_records_imported or 0,
        "last_10_runs": [_to_dict(r) for r in last_10_runs],
        "health_status": health_status,
    }


# ---------------------------------------------------------------------------
# Import dry-run
# ---------------------------------------------------------------------------


class DryRunRequest(BaseModel):
    csv_content: str
    limit: int = 50


@router.post("/systems/{system_id}/dry-run")
def dry_run_import(system_id: int, request: Request, body: DryRunRequest, db: Session = Depends(get_db)):
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

    # Try CSV connector for this system
    from app.services.connectors.csv_connector import CensiTracCSVConnector, SPMCSVConnector
    csv_connectors = {
        "censitrac": CensiTracCSVConnector,
        "spm": SPMCSVConnector,
    }
    cls = csv_connectors.get(conn.system_name.lower())
    if cls is None:
        raise HTTPException(status_code=400, detail=f"System '{conn.system_name}' does not support CSV dry-run.")

    config = json.loads(conn.config_json or "{}")
    connector = cls(tenant_id, conn.facility_id or "", config)
    result = connector.parse_csv_content(body.csv_content, tenant_id, conn.facility_id or "")

    records = result["records"][: body.limit]

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.systems.dry_run",
        resource_type="external_system_connections",
        resource_id=str(system_id),
        details={"would_create": len(result["records"]), "would_fail": result["failed"]},
    )
    return {
        "status": "success",
        "would_create": len(result["records"]),
        "would_fail": result["failed"],
        "errors": result["errors"],
        "sample_records": records[:5],
        "db_unchanged": True,
    }


# ---------------------------------------------------------------------------
# Webhook receiver (HMAC auth)
# ---------------------------------------------------------------------------


@router.post("/webhook/{system_name}")
async def webhook_ingest(system_name: str, request: Request, db: Session = Depends(get_db)):
    """
    Webhook receiver for push-based integrations.
    Validates HMAC signature if WEBHOOK_SECRET_{SYSTEM_NAME_UPPER} env var is set.
    No Authorization header required — authentication is via HMAC.
    """
    body = await request.body()
    system_upper = system_name.upper().replace("-", "_")
    secret = os.getenv(f"WEBHOOK_SECRET_{system_upper}", "")

    if secret:
        sig_header = request.headers.get("X-Webhook-Signature", "")
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse body
    try:
        payload = json.loads(body) if body else {}
        events = payload if isinstance(payload, list) else payload.get("events", [payload])
    except Exception:
        events = []

    # Determine category
    spd_systems = {"censitrac", "spm", "readyset", "abacus", "vendormade"}
    ip_systems = {"icnet", "vigilanz", "theradoc"}
    if system_name in spd_systems:
        system_category = "spd_tracking"
    elif system_name in ip_systems:
        system_category = "infection_prevention"
    else:
        system_category = "quality_safety"

    # Determine tenant from first event or header
    tenant_id = request.headers.get("X-Tenant-Id") or request.headers.get("X-LumenAI-Tenant-Id") or "webhook"

    imported = 0
    errors = []

    _PHI = {"patient_id", "mrn", "dob", "patient_name", "name", "ssn"}
    for raw_event in events:
        if not isinstance(raw_event, dict):
            continue
        for phi_key in _PHI:
            raw_event.pop(phi_key, None)
        try:
            payload_str = str(sorted(raw_event.items()))
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
            ts_raw = raw_event.get("event_timestamp")
            event_ts = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else datetime.utcnow()

            if system_category == "quality_safety":
                rec = QualitySafetyEventRecord(
                    tenant_id=tenant_id,
                    facility_id=raw_event.get("facility_id"),
                    source_system=system_name,
                    source_record_id=raw_event.get("source_record_id"),
                    source_event_type=raw_event.get("source_event_type", "webhook_event"),
                    event_timestamp=event_ts,
                    event_category=raw_event.get("event_category"),
                    event_severity=raw_event.get("event_severity"),
                    instrument_reference=raw_event.get("instrument_reference"),
                    tray_reference=raw_event.get("tray_reference"),
                    de_identified=True,
                    raw_payload_hash=payload_hash,
                )
            elif system_category == "infection_prevention":
                rec = InfectionPreventionEventRecord(
                    tenant_id=tenant_id,
                    facility_id=raw_event.get("facility_id"),
                    source_system=system_name,
                    source_record_id=raw_event.get("source_record_id"),
                    source_event_type=raw_event.get("source_event_type", "webhook_event"),
                    event_timestamp=event_ts,
                    pathogen=raw_event.get("pathogen"),
                    procedure_type=raw_event.get("procedure_type"),
                    service_line=raw_event.get("service_line"),
                    instrument_reference=raw_event.get("instrument_reference"),
                    de_identified=True,
                    raw_payload_hash=payload_hash,
                )
            else:
                rec = InstrumentTrackingRecord(
                    tenant_id=tenant_id,
                    facility_id=raw_event.get("facility_id"),
                    source_system=system_name,
                    source_record_id=raw_event.get("source_record_id"),
                    source_event_type=raw_event.get("source_event_type", "webhook_event"),
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
        except Exception as e:
            errors.append(str(e))

    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="webhook",
        actor_role="",
        action_type=f"integrations.webhook.{system_name}",
        resource_type="external_events",
        resource_id="",
        details={"system_name": system_name, "events_received": len(events), "imported": imported},
    )
    return {"received": True, "system": system_name, "events_processed": imported, "errors": errors}


# ---------------------------------------------------------------------------
# Error quarantine
# ---------------------------------------------------------------------------


@router.get("/errors")
def list_integration_errors(
    request: Request,
    system_name: str = Query(default=""),
    resolution_status: str = Query(default=""),
    import_run_id: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    q = db.query(IntegrationErrorRecord).filter(IntegrationErrorRecord.tenant_id == tenant_id)
    if system_name:
        q = q.filter(IntegrationErrorRecord.system_name == system_name)
    if resolution_status:
        q = q.filter(IntegrationErrorRecord.resolution_status == resolution_status)
    if import_run_id:
        q = q.filter(IntegrationErrorRecord.import_run_id == import_run_id)
    error_records = q.order_by(IntegrationErrorRecord.created_at.desc()).limit(limit).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="integrations.errors.list",
        resource_type="integration_error_records",
        resource_id="all",
        details={"count": len(error_records)},
    )
    return {"status": "success", "errors": [_to_dict(r) for r in error_records], "count": len(error_records)}
