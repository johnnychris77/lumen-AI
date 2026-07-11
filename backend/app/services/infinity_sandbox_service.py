"""v5.0 — Project Infinity, Section 9: Developer Sandbox.

No sandbox/isolated-dev-environment concept existed anywhere in this
codebase before Infinity (`pilot_config.py`/`pilot_error_log.py`, v1.9,
are a different, older "pilot" concept — per-tenant sales-pilot
configuration, not a developer sandbox). Every sandbox session is scoped
to a synthetic `sandbox_tenant_id` with a fixed, unmistakable prefix so
it can never collide with, or be confused for, a real production tenant.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.infinity_platform import SANDBOX_ACTIVE, SANDBOX_EXPIRED, SANDBOX_PURPOSES, SANDBOX_TERMINATED, DeveloperSandboxSession

_SANDBOX_TENANT_PREFIX = "sandbox-"
DEFAULT_SESSION_LIFETIME_HOURS = 24


class SandboxSessionNotFoundError(ValueError):
    pass


def _to_dict(row: DeveloperSandboxSession) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "developer_account_id": row.developer_account_id,
        "listing_id": row.listing_id, "sandbox_tenant_id": row.sandbox_tenant_id, "purpose": row.purpose,
        "status": row.status, "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


def create_sandbox_session(
    db: Session, developer_account_id: int, *, purpose: str, listing_id: int | None = None,
    lifetime_hours: int = DEFAULT_SESSION_LIFETIME_HOURS,
) -> dict:
    if purpose not in SANDBOX_PURPOSES:
        raise ValueError(f"purpose must be one of {SANDBOX_PURPOSES}")
    sandbox_tenant_id = f"{_SANDBOX_TENANT_PREFIX}{developer_account_id}-{uuid.uuid4().hex[:12]}"
    row = DeveloperSandboxSession(
        developer_account_id=developer_account_id, listing_id=listing_id, sandbox_tenant_id=sandbox_tenant_id,
        purpose=purpose, expires_at=datetime.now(timezone.utc) + timedelta(hours=lifetime_hours),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get(db: Session, session_id: int) -> DeveloperSandboxSession:
    row = db.query(DeveloperSandboxSession).filter(DeveloperSandboxSession.id == session_id).first()
    if row is None:
        raise SandboxSessionNotFoundError(f"Sandbox session {session_id} not found.")
    return row


def get_sandbox_session(db: Session, session_id: int) -> dict:
    return _to_dict(_get(db, session_id))


def list_sandbox_sessions(db: Session, developer_account_id: int, *, status: str = "") -> list[dict]:
    q = db.query(DeveloperSandboxSession).filter(DeveloperSandboxSession.developer_account_id == developer_account_id)
    if status:
        q = q.filter(DeveloperSandboxSession.status == status)
    return [_to_dict(r) for r in q.order_by(DeveloperSandboxSession.created_at.desc()).all()]


def terminate_sandbox_session(db: Session, session_id: int) -> dict:
    row = _get(db, session_id)
    row.status = SANDBOX_TERMINATED
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def expire_stale_sessions(db: Session) -> list[dict]:
    """Marks sessions past `expires_at` as expired — never silently
    treated as still active."""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(DeveloperSandboxSession)
        .filter(DeveloperSandboxSession.status == SANDBOX_ACTIVE, DeveloperSandboxSession.expires_at < now)
        .all()
    )
    for row in rows:
        row.status = SANDBOX_EXPIRED
    db.commit()
    for row in rows:
        db.refresh(row)
    return [_to_dict(r) for r in rows]


def is_sandbox_tenant(tenant_id: str) -> bool:
    """Distinguishes a real production tenant_id from a synthetic sandbox
    one — used anywhere a caller must guarantee no production impact."""
    return tenant_id.startswith(_SANDBOX_TENANT_PREFIX)
