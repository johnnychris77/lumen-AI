"""v3.2 — Project Nexus, Section 1 & 8: Connection Health & Monitoring.

Health is derived from what's already tracked on `NexusConnector`
(consecutive_errors, last_sync_at) plus a fresh probe latency — never a
fabricated score. Thresholds mirror the same idiom P17's
`ExternalSystemConnection` health check already uses (consecutive-error
count + staleness), applied at the connector-registry level instead of
per-connection.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.nexus_integration import (
    HEALTH_DEGRADED,
    HEALTH_ERROR,
    HEALTH_HEALTHY,
    HEALTH_UNKNOWN,
    NexusConnector,
    NexusConnectorErrorLog,
    NexusSyncRun,
)

_STALE_AFTER = timedelta(hours=24)
_DEGRADED_ERROR_THRESHOLD = 1
_ERROR_THRESHOLD = 4


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _as_naive_utc(dt):
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def compute_health_status(connector: NexusConnector) -> str:
    if connector.last_sync_at is None and connector.consecutive_errors == 0:
        return HEALTH_UNKNOWN
    if connector.consecutive_errors >= _ERROR_THRESHOLD:
        return HEALTH_ERROR

    last_sync = _as_naive_utc(connector.last_sync_at)
    stale = last_sync is not None and (datetime.utcnow() - last_sync) > _STALE_AFTER
    if connector.consecutive_errors >= _DEGRADED_ERROR_THRESHOLD or stale:
        return HEALTH_DEGRADED
    return HEALTH_HEALTHY


def record_health_check(db: Session, tenant_id: str, connector: NexusConnector, *, latency_ms: int) -> dict:
    connector.latency_ms = latency_ms
    connector.last_health_check_at = datetime.now(timezone.utc)
    connector.health_status = compute_health_status(connector)
    db.commit()
    db.refresh(connector)
    return _row_to_dict(connector)


def record_sync_success(db: Session, connector: NexusConnector) -> None:
    connector.consecutive_errors = 0
    connector.last_sync_at = datetime.now(timezone.utc)
    connector.health_status = compute_health_status(connector)
    db.commit()


def record_sync_error(db: Session, connector: NexusConnector, *, error_type: str, message: str, sync_run_id: int | None = None) -> None:
    connector.consecutive_errors = (connector.consecutive_errors or 0) + 1
    connector.health_status = compute_health_status(connector)
    db.add(NexusConnectorErrorLog(
        connector_id=connector.id, tenant_id=connector.tenant_id, sync_run_id=sync_run_id,
        error_type=error_type, message=message,
    ))
    db.commit()


def list_errors(db: Session, tenant_id: str, connector_id: int) -> list[dict]:
    rows = (
        db.query(NexusConnectorErrorLog)
        .filter(NexusConnectorErrorLog.tenant_id == tenant_id, NexusConnectorErrorLog.connector_id == connector_id)
        .order_by(NexusConnectorErrorLog.id.desc())
        .all()
    )
    return [_row_to_dict(r) for r in rows]


def list_sync_runs(db: Session, tenant_id: str, connector_id: int, *, run_type: str = "") -> list[dict]:
    q = db.query(NexusSyncRun).filter(NexusSyncRun.tenant_id == tenant_id, NexusSyncRun.connector_id == connector_id)
    if run_type:
        q = q.filter(NexusSyncRun.run_type == run_type)
    rows = q.order_by(NexusSyncRun.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def integration_monitoring_dashboard(db: Session, tenant_id: str) -> dict:
    """Section 8: /integrations — one row per connector with everything the
    monitoring dashboard asks for (status, last sync, health, errors,
    retries, latency, version, authentication status)."""
    connectors = db.query(NexusConnector).filter(NexusConnector.tenant_id == tenant_id).order_by(NexusConnector.id.asc()).all()

    rows = []
    for c in connectors:
        error_count = db.query(NexusConnectorErrorLog.id).filter(NexusConnectorErrorLog.connector_id == c.id).count()
        retry_count = (
            db.query(NexusSyncRun.id)
            .filter(NexusSyncRun.connector_id == c.id, NexusSyncRun.attempt_number > 1)
            .count()
        )
        from app.services.nexus_credential_service import list_credentials
        credentials = list_credentials(db, tenant_id, c.id)
        auth_status = "configured" if any(not cred["revoked"] for cred in credentials) else "not_configured"

        rows.append({
            "connector_id": c.id, "connector_key": c.connector_key, "display_name": c.display_name,
            "category": c.category, "status": c.status, "version": c.version, "auth_type": c.auth_type,
            "health_status": c.health_status, "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "last_health_check_at": c.last_health_check_at.isoformat() if c.last_health_check_at else None,
            "consecutive_errors": c.consecutive_errors, "total_errors": error_count, "retry_count": retry_count,
            "latency_ms": c.latency_ms, "authentication_status": auth_status,
        })

    return {"tenant_id": tenant_id, "connector_count": len(rows), "connectors": rows}
