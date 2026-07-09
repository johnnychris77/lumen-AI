"""v3.2 — Project Nexus, Section 1 & 2: Connector Registry & Versioning.

`NEXUS_CONNECTOR_CATALOG` (in `app/models/nexus_integration.py`) is the
static list of connector *types* this platform can build an adapter for.
A `NexusConnector` row is one tenant's registered, versioned instance of a
catalog entry — enabling future connectors never requires touching this
service or the core routing/scheduling architecture, only adding a new
catalog entry and adapter class (`app/services/nexus_connectors/adapters.py`).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.nexus_integration import (
    NEXUS_CONNECTOR_CATALOG,
    NEXUS_CONNECTOR_KEYS,
    NEXUS_CONNECTOR_STATUSES,
    STATUS_DISABLED,
    NexusConnector,
)


class UnknownConnectorKeyError(Exception):
    pass


def to_dict(obj) -> dict:
    return _row_to_dict(obj)


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _catalog_entry(connector_key: str) -> dict:
    for entry in NEXUS_CONNECTOR_CATALOG:
        if entry["connector_key"] == connector_key:
            return entry
    raise UnknownConnectorKeyError(f"connector_key must be one of {NEXUS_CONNECTOR_KEYS}")


def list_catalog() -> list[dict]:
    return list(NEXUS_CONNECTOR_CATALOG)


def register_connector(db: Session, tenant_id: str, *, connector_key: str, config_json: str = "{}") -> dict:
    """Register (or return the existing) tenant instance of a catalog connector."""
    existing = (
        db.query(NexusConnector)
        .filter(NexusConnector.tenant_id == tenant_id, NexusConnector.connector_key == connector_key)
        .first()
    )
    if existing is not None:
        return _row_to_dict(existing)

    entry = _catalog_entry(connector_key)
    row = NexusConnector(
        tenant_id=tenant_id, connector_key=connector_key, display_name=entry["display_name"],
        category=entry["category"], version=entry["default_version"], auth_type=entry["default_auth_type"],
        status=STATUS_DISABLED, config_json=config_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_connectors(db: Session, tenant_id: str, *, category: str = "") -> list[dict]:
    q = db.query(NexusConnector).filter(NexusConnector.tenant_id == tenant_id)
    if category:
        q = q.filter(NexusConnector.category == category)
    return [_row_to_dict(r) for r in q.order_by(NexusConnector.id.asc()).all()]


def get_connector(db: Session, tenant_id: str, connector_id: int) -> NexusConnector | None:
    return db.query(NexusConnector).filter(NexusConnector.id == connector_id, NexusConnector.tenant_id == tenant_id).first()


def set_connector_status(db: Session, tenant_id: str, connector_id: int, *, status: str) -> dict | None:
    if status not in NEXUS_CONNECTOR_STATUSES:
        raise ValueError(f"status must be one of {NEXUS_CONNECTOR_STATUSES}")
    row = get_connector(db, tenant_id, connector_id)
    if row is None:
        return None
    row.status = status
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def set_connector_version(db: Session, tenant_id: str, connector_id: int, *, version: str) -> dict | None:
    row = get_connector(db, tenant_id, connector_id)
    if row is None:
        return None
    row.version = version
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
