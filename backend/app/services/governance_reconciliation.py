from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models


def _now():
    return datetime.now(timezone.utc)


def _compact(data: dict) -> str:
    return json.dumps(data, default=str)[:4000]


def _policy_state(row: models.RetentionPolicy | None) -> dict:
    if not row:
        return {}
    return {
        "id": row.id,
        "artifact_type": row.artifact_type,
        "retention_days": row.retention_days,
        "legal_hold_enabled": row.legal_hold_enabled,
        "notes": row.notes,
        "is_enabled": row.is_enabled,
    }


def _membership_state(row: models.TenantMembership | None) -> dict:
    if not row:
        return {}
    return {
        "id": row.id,
        "user_email": row.user_email,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "role_name": row.role_name,
        "is_enabled": row.is_enabled,
    }


def record_rollback_entry(
    db: Session,
    *,
    approval: models.GovernanceApproval,
    before_state: dict,
    after_state: dict,
):
    row = models.GovernanceRollback(
        approval_id=approval.id,
        tenant_id=approval.tenant_id,
        tenant_name=approval.tenant_name,
        request_type=approval.request_type,
        target_resource=approval.target_resource,
        target_resource_id=approval.target_resource_id,
        before_state=_compact(before_state),
        after_state=_compact(after_state),
        rollback_status="available",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def reconcile_execution(
    db: Session,
    *,
    approval: models.GovernanceApproval,
) -> dict:
    payload_wrapper = json.loads(approval.requested_payload or "{}")
    payload = payload_wrapper.get("payload", {})
    request_type = (approval.request_type or "").strip().lower()

    if request_type in {"legal_hold_change", "retention_change"}:
        artifact_type = payload.get("artifact_type", approval.target_resource_id or "evidence_pack")
        row = (
            db.query(models.RetentionPolicy)
            .filter(
                models.RetentionPolicy.tenant_id == approval.tenant_id,
                models.RetentionPolicy.artifact_type == artifact_type,
            )
            .order_by(models.RetentionPolicy.id.desc())
            .first()
        )
        state = _policy_state(row)

        if request_type == "legal_hold_change":
            expected = bool(payload.get("legal_hold_enabled", False))
            actual = bool(state.get("legal_hold_enabled", False))
            return {
                "resource_type": "retention_policy",
                "resource_id": state.get("id", ""),
                "expected": {"legal_hold_enabled": expected},
                "actual": {"legal_hold_enabled": actual},
                "match": expected == actual,
            }

        expected = int(payload.get("retention_days", 365))
        actual = int(state.get("retention_days", 0) or 0)
        return {
            "resource_type": "retention_policy",
            "resource_id": state.get("id", ""),
            "expected": {"retention_days": expected},
            "actual": {"retention_days": actual},
            "match": expected == actual,
        }

    if request_type == "tenant_role_change":
        user_email = str(payload.get("user_email", "")).strip().lower()
        expected_role = str(payload.get("role_name", "viewer")).strip()
        row = (
            db.query(models.TenantMembership)
            .filter(
                models.TenantMembership.user_email == user_email,
                models.TenantMembership.tenant_id == approval.tenant_id,
            )
            .order_by(models.TenantMembership.id.desc())
            .first()
        )
        state = _membership_state(row)
        actual = str(state.get("role_name", "")).strip()
        return {
            "resource_type": "tenant_membership",
            "resource_id": state.get("id", ""),
            "expected": {"role_name": expected_role},
            "actual": {"role_name": actual},
            "match": expected_role == actual,
        }

    return {
        "resource_type": approval.target_resource,
        "resource_id": approval.target_resource_id,
        "expected": {},
        "actual": {},
        "match": False,
        "reason": f"Unsupported request_type: {approval.request_type}",
    }


def execute_rollback(
    db: Session,
    *,
    rollback: models.GovernanceRollback,
    actor_email: str,
) -> dict:
    before_state = json.loads(rollback.before_state or "{}")
    request_type = (rollback.request_type or "").strip().lower()

    if rollback.rollback_status != "available":
        raise ValueError("Rollback is not available")

    if request_type in {"legal_hold_change", "retention_change"}:
        artifact_type = before_state.get("artifact_type") or rollback.target_resource_id or "evidence_pack"
        row = (
            db.query(models.RetentionPolicy)
            .filter(
                models.RetentionPolicy.tenant_id == rollback.tenant_id,
                models.RetentionPolicy.artifact_type == artifact_type,
            )
            .order_by(models.RetentionPolicy.id.desc())
            .first()
        )
        if not row:
            raise ValueError("Retention policy not found for rollback")

        if "retention_days" in before_state:
            row.retention_days = int(before_state.get("retention_days", row.retention_days))
        if "legal_hold_enabled" in before_state:
            row.legal_hold_enabled = bool(before_state.get("legal_hold_enabled", row.legal_hold_enabled))
        if "notes" in before_state:
            row.notes = str(before_state.get("notes", row.notes))
        if "is_enabled" in before_state:
            row.is_enabled = bool(before_state.get("is_enabled", row.is_enabled))

        db.add(row)
        db.commit()
        db.refresh(row)

        rollback.rollback_status = "rolled_back"
        rollback.rollback_notes = "Rollback executed successfully"
        rollback.rolled_back_by = actor_email
        rollback.rolled_back_at = _now()
        db.add(rollback)
        db.commit()
        db.refresh(rollback)

        return {
            "resource_type": "retention_policy",
            "resource_id": row.id,
            "message": f"Rollback applied for {artifact_type}",
        }

    if request_type == "tenant_role_change":
        user_email = str(before_state.get("user_email", "")).strip().lower()
        row = (
            db.query(models.TenantMembership)
            .filter(
                models.TenantMembership.user_email == user_email,
                models.TenantMembership.tenant_id == rollback.tenant_id,
            )
            .order_by(models.TenantMembership.id.desc())
            .first()
        )
        if not row:
            raise ValueError("Tenant membership not found for rollback")

        row.role_name = str(before_state.get("role_name", row.role_name))
        row.is_enabled = bool(before_state.get("is_enabled", row.is_enabled))
        db.add(row)
        db.commit()
        db.refresh(row)

        rollback.rollback_status = "rolled_back"
        rollback.rollback_notes = "Rollback executed successfully"
        rollback.rolled_back_by = actor_email
        rollback.rolled_back_at = _now()
        db.add(rollback)
        db.commit()
        db.refresh(rollback)

        return {
            "resource_type": "tenant_membership",
            "resource_id": row.id,
            "message": f"Rollback applied for {user_email}",
        }

    raise ValueError(f"Unsupported rollback request_type: {rollback.request_type}")
