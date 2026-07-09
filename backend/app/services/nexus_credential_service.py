"""v3.2 — Project Nexus, Section 10: Integration Security — API credentials.

Reuses the exact `secrets.token_urlsafe(40)` + SHA-256-hash-only pattern
already established twice in this codebase (`routes/capture.py`'s device
registration, `routes/p25_infrastructure.py::issue_api_credential`) — the
raw key is returned exactly once at issuance and is never stored or
retrievable again. Only the hash is persisted.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.nexus_integration import NexusConnectorCredential

DEFAULT_CREDENTIAL_LIFETIME_DAYS = 365


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        if col.name == "key_hash":
            continue  # never returned after issuance
        result[col.name] = val
    return result


def issue_credential(
    db: Session, tenant_id: str, connector_id: int, *, scopes: list[str] | None = None, issued_by: str = "system",
    lifetime_days: int = DEFAULT_CREDENTIAL_LIFETIME_DAYS,
) -> dict:
    raw_key = secrets.token_urlsafe(40)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    row = NexusConnectorCredential(
        connector_id=connector_id, tenant_id=tenant_id, key_hash=key_hash,
        scopes_json=json.dumps(scopes or []), issued_by=issued_by,
        expires_at=datetime.now(timezone.utc) + timedelta(days=lifetime_days),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _row_to_dict(row)
    result["api_key"] = raw_key  # shown ONCE — never retrievable again
    return result


def list_credentials(db: Session, tenant_id: str, connector_id: int) -> list[dict]:
    rows = (
        db.query(NexusConnectorCredential)
        .filter(NexusConnectorCredential.tenant_id == tenant_id, NexusConnectorCredential.connector_id == connector_id)
        .order_by(NexusConnectorCredential.id.desc())
        .all()
    )
    return [_row_to_dict(r) for r in rows]


def revoke_credential(db: Session, tenant_id: str, credential_id: int) -> dict | None:
    row = (
        db.query(NexusConnectorCredential)
        .filter(NexusConnectorCredential.id == credential_id, NexusConnectorCredential.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        return None
    row.revoked = True
    row.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def _as_naive_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes even for DateTime(timezone=True)
    columns, while Postgres returns tz-aware ones — normalize to naive UTC
    so expiry comparisons work identically on both backends."""
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def authenticate_key(db: Session, raw_key: str) -> NexusConnectorCredential | None:
    """Least-privilege gateway auth: hash the presented key and match an
    active, unrevoked, unexpired credential. Never compares raw keys."""
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    row = db.query(NexusConnectorCredential).filter(NexusConnectorCredential.key_hash == key_hash).first()
    if row is None or row.revoked:
        return None
    expires_at = _as_naive_utc(row.expires_at)
    if expires_at is not None and expires_at < datetime.utcnow():
        return None
    return row
