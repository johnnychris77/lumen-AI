"""v5.0 — Project Infinity, Section 1: Developer accounts & API keys.

`DeveloperAccount` is a deliberately new, first-class identity — distinct
from `TenantMembership` — since a third-party developer building an app
is not tenant staff. Account creation/approval is gated to internal
platform admins (never fully open self-service), matching the brief's
"trusted third parties" framing. `DeveloperApiKey` issuance reuses the
exact `secrets.token_urlsafe(40)` + SHA-256-hash-only pattern already
established in `nexus_credential_service.py` — the raw key is returned
exactly once and never stored or retrievable again.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.infinity_platform import (
    DEVELOPER_ACTIVE,
    DEVELOPER_STATUSES,
    DEVELOPER_TYPES,
    DeveloperAccount,
    DeveloperApiKey,
)

DEFAULT_KEY_LIFETIME_DAYS = 365


class DeveloperAccountNotFoundError(ValueError):
    pass


def _account_to_dict(row: DeveloperAccount) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "email": row.email,
        "organization_name": row.organization_name, "developer_type": row.developer_type,
        "status": row.status, "sandbox_only": row.sandbox_only, "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }


def create_developer_account(
    db: Session, *, email: str, organization_name: str, developer_type: str, approved_by: str, sandbox_only: bool = True,
) -> dict:
    if developer_type not in DEVELOPER_TYPES:
        raise ValueError(f"developer_type must be one of {DEVELOPER_TYPES}")
    row = DeveloperAccount(
        email=email, organization_name=organization_name, developer_type=developer_type,
        sandbox_only=sandbox_only, approved_by=approved_by, approved_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _account_to_dict(row)


def _get_account(db: Session, developer_account_id: int) -> DeveloperAccount:
    row = db.query(DeveloperAccount).filter(DeveloperAccount.id == developer_account_id).first()
    if row is None:
        raise DeveloperAccountNotFoundError(f"Developer account {developer_account_id} not found.")
    return row


def get_developer_account(db: Session, developer_account_id: int) -> dict:
    return _account_to_dict(_get_account(db, developer_account_id))


def list_developer_accounts(db: Session, *, status: str = "") -> list[dict]:
    q = db.query(DeveloperAccount)
    if status:
        q = q.filter(DeveloperAccount.status == status)
    return [_account_to_dict(r) for r in q.order_by(DeveloperAccount.created_at.desc()).all()]


def set_developer_account_status(db: Session, developer_account_id: int, *, status: str) -> dict:
    if status not in DEVELOPER_STATUSES:
        raise ValueError(f"status must be one of {DEVELOPER_STATUSES}")
    row = _get_account(db, developer_account_id)
    row.status = status
    db.commit()
    db.refresh(row)
    return _account_to_dict(row)


def _key_to_dict(row: DeveloperApiKey) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "developer_account_id": row.developer_account_id,
        "scopes": json.loads(row.scopes_json or "[]"), "sandbox_only": row.sandbox_only,
        "revoked": row.revoked, "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


def issue_api_key(
    db: Session, developer_account_id: int, *, scopes: list[str] | None = None, sandbox_only: bool = True,
    lifetime_days: int = DEFAULT_KEY_LIFETIME_DAYS,
) -> dict:
    account = _get_account(db, developer_account_id)
    if account.status != DEVELOPER_ACTIVE:
        raise ValueError(f"Developer account {developer_account_id} is not active ({account.status}).")

    raw_key = secrets.token_urlsafe(40)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    row = DeveloperApiKey(
        developer_account_id=developer_account_id, key_hash=key_hash, scopes_json=json.dumps(scopes or []),
        sandbox_only=sandbox_only, expires_at=datetime.now(timezone.utc) + timedelta(days=lifetime_days),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _key_to_dict(row)
    result["api_key"] = raw_key  # shown ONCE — never retrievable again
    return result


def list_api_keys(db: Session, developer_account_id: int) -> list[dict]:
    rows = (
        db.query(DeveloperApiKey)
        .filter(DeveloperApiKey.developer_account_id == developer_account_id)
        .order_by(DeveloperApiKey.id.desc())
        .all()
    )
    return [_key_to_dict(r) for r in rows]


def revoke_api_key(db: Session, developer_account_id: int, key_id: int) -> dict | None:
    row = (
        db.query(DeveloperApiKey)
        .filter(DeveloperApiKey.id == key_id, DeveloperApiKey.developer_account_id == developer_account_id)
        .first()
    )
    if row is None:
        return None
    row.revoked = True
    row.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _key_to_dict(row)


def _as_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def authenticate_api_key(db: Session, raw_key: str) -> DeveloperApiKey | None:
    """Least-privilege auth: hash the presented key and match an active,
    unrevoked, unexpired key against a non-suspended developer account —
    never compares raw keys."""
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    row = db.query(DeveloperApiKey).filter(DeveloperApiKey.key_hash == key_hash).first()
    if row is None or row.revoked:
        return None
    expires_at = _as_naive_utc(row.expires_at)
    if expires_at is not None and expires_at < datetime.utcnow():
        return None
    account = db.query(DeveloperAccount).filter(DeveloperAccount.id == row.developer_account_id).first()
    if account is None or account.status != DEVELOPER_ACTIVE:
        return None
    return row
