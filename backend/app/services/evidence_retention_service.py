from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.enterprise_audit_service import record_enterprise_audit_event


def calculate_retention_expiration(
    *,
    created_at: datetime,
    retention_days: int,
) -> datetime:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    return created_at + timedelta(days=retention_days)


def evaluate_retention_status(
    *,
    created_at: datetime,
    retention_days: int,
    legal_hold_enabled: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = now or datetime.now(UTC)

    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    expires_at = calculate_retention_expiration(
        created_at=created_at,
        retention_days=retention_days,
    )

    expired = current_time >= expires_at

    return {
        "retention_days": retention_days,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "expired": expired,
        "legal_hold_enabled": legal_hold_enabled,
        "deletion_allowed": expired and not legal_hold_enabled,
        "deletion_blocked_reason": "legal_hold" if expired and legal_hold_enabled else "",
    }


def enforce_retention_deletion_allowed(
    *,
    retention_status: dict[str, Any],
) -> bool:
    if retention_status.get("legal_hold_enabled"):
        raise HTTPException(
            status_code=423,
            detail="Deletion blocked because legal hold is enabled.",
        )

    if not retention_status.get("expired"):
        raise HTTPException(
            status_code=409,
            detail="Deletion blocked because retention period has not expired.",
        )

    return True


def record_retention_decision(
    db: Session,
    *,
    resource_type: str,
    resource_id: str | int,
    actor: str,
    actor_role: str,
    retention_status: dict[str, Any],
    decision: str,
) -> object:
    return record_enterprise_audit_event(
        db,
        action_type="evidence_retention_decision_recorded",
        resource_type=resource_type,
        resource_id=resource_id,
        actor=actor,
        actor_role=actor_role,
        details={
            "decision": decision,
            "retention_days": retention_status.get("retention_days"),
            "expires_at": retention_status.get("expires_at"),
            "expired": retention_status.get("expired"),
            "legal_hold_enabled": retention_status.get("legal_hold_enabled"),
            "deletion_allowed": retention_status.get("deletion_allowed"),
            "deletion_blocked_reason": retention_status.get("deletion_blocked_reason"),
        },
    )
