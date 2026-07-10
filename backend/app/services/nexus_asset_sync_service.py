"""v3.2 — Project Nexus, Section 3 & 9: Instrument Data Synchronization.

Synchronizes instrument/tray/asset records a connector has actually
supplied (`external_records`) — never invents one. Each synced record is
upserted (keyed on tenant_id + connector_id + external_id, so re-running a
sync updates rather than duplicates), links to the SPD Digital Twin
(`app/models/digital_twin.py::InstrumentFlowRecord`) via a marker
"external_sync" station when a `digital_twin_instrument_id` is supplied,
and carries full source-system provenance (Section 9: Data Governance) —
`source_system`, `synced_at`, and an explicit `conflict_resolution` field
when a second connector reports different attributes for the same asset.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.digital_twin import InstrumentFlowRecord
from app.models.nexus_integration import (
    NEXUS_SYNC_RUN_TYPES,
    RUN_TYPE_INSTRUMENT,
    RUN_TYPE_TRAY,
    SYNC_STATUS_COMPLETED,
    SYNC_STATUS_FAILED,
    SYNC_STATUS_RETRYING,
    NexusConnector,
    NexusSyncedAsset,
    NexusSyncRun,
)
from app.services import nexus_health_service

_CONFLICTING_FIELDS = ("manufacturer", "model", "repair_status", "location", "service_status")


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _link_digital_twin(db: Session, tenant_id: str, facility_id: str, instrument_id: str, source_system: str) -> None:
    """Records that this instrument is known via an external system by
    logging an 'external_sync' station arrival on the SPD Digital Twin —
    never fabricates a real SPD workflow movement."""
    if not instrument_id:
        return
    db.add(InstrumentFlowRecord(
        tenant_id=tenant_id, facility_id=facility_id, instrument_name=instrument_id, instrument_id=instrument_id,
        from_station=source_system, to_station="external_sync", station_type="external_sync",
        outcome="pending", notes=f"Linked via Nexus connector sync from {source_system}.",
    ))


def sync_assets(
    db: Session, tenant_id: str, connector: NexusConnector, *, asset_type: str,
    external_records: list[dict], facility_id: str = "",
) -> dict:
    """`external_records`: list of dicts with keys external_id (required),
    manufacturer, model, repair_status, location, service_status,
    digital_twin_instrument_id (all optional). Honestly reports zero
    processed if the connector supplied nothing — never invents assets."""
    run_type = RUN_TYPE_TRAY if asset_type == "tray" else RUN_TYPE_INSTRUMENT
    if run_type not in NEXUS_SYNC_RUN_TYPES:
        raise ValueError(f"asset_type must resolve to one of {NEXUS_SYNC_RUN_TYPES}")

    run = NexusSyncRun(connector_id=connector.id, tenant_id=tenant_id, run_type=run_type, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    processed = 0
    failed = 0
    conflicts = 0
    try:
        for record in external_records:
            external_id = record.get("external_id")
            if not external_id:
                failed += 1
                continue

            existing = (
                db.query(NexusSyncedAsset)
                .filter(
                    NexusSyncedAsset.tenant_id == tenant_id, NexusSyncedAsset.connector_id == connector.id,
                    NexusSyncedAsset.external_id == external_id,
                )
                .first()
            )
            conflict_resolution = ""
            if existing is not None:
                changed = [f for f in _CONFLICTING_FIELDS if record.get(f, "") and record.get(f, "") != getattr(existing, f)]
                if changed:
                    conflicts += 1
                    conflict_resolution = "external_wins"
                    existing.last_conflict_at = datetime.now(timezone.utc)
                for field in _CONFLICTING_FIELDS:
                    if record.get(field, "") :
                        setattr(existing, field, record[field])
                existing.location = record.get("location", existing.location)
                existing.digital_twin_instrument_id = record.get("digital_twin_instrument_id", existing.digital_twin_instrument_id)
                existing.synced_at = datetime.now(timezone.utc)
                existing.conflict_resolution = conflict_resolution or existing.conflict_resolution
            else:
                db.add(NexusSyncedAsset(
                    connector_id=connector.id, tenant_id=tenant_id, external_id=external_id, asset_type=asset_type,
                    manufacturer=record.get("manufacturer", ""), model=record.get("model", ""),
                    repair_status=record.get("repair_status", ""), location=record.get("location", ""),
                    service_status=record.get("service_status", ""),
                    digital_twin_instrument_id=record.get("digital_twin_instrument_id", ""),
                    source_system=connector.connector_key,
                ))

            _link_digital_twin(db, tenant_id, facility_id, record.get("digital_twin_instrument_id", ""), connector.connector_key)
            processed += 1

        run.records_processed = processed
        run.records_failed = failed
        run.status = SYNC_STATUS_COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        nexus_health_service.record_sync_success(db, connector)
    except Exception as exc:
        run.status = SYNC_STATUS_RETRYING if run.attempt_number < run.max_attempts else SYNC_STATUS_FAILED
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        nexus_health_service.record_sync_error(db, connector, error_type="sync_error", message=str(exc), sync_run_id=run.id)
        raise

    db.refresh(run)
    return {"run": _row_to_dict(run), "processed": processed, "failed": failed, "conflicts": conflicts}


def list_synced_assets(db: Session, tenant_id: str, connector_id: int, *, asset_type: str = "") -> list[dict]:
    q = db.query(NexusSyncedAsset).filter(NexusSyncedAsset.tenant_id == tenant_id, NexusSyncedAsset.connector_id == connector_id)
    if asset_type:
        q = q.filter(NexusSyncedAsset.asset_type == asset_type)
    return [_row_to_dict(r) for r in q.order_by(NexusSyncedAsset.id.desc()).all()]
