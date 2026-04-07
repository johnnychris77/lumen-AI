from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.services.governance_reconciliation import record_rollback_entry


def _now():
    return datetime.now(timezone.utc)


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


def execute_approved_change(db: Session, approval: models.GovernanceApproval) -> dict:
    payload_wrapper = json.loads(approval.requested_payload or "{}")
    payload = payload_wrapper.get("payload", {})

    request_type = (approval.request_type or "").strip().lower()

    if request_type == "legal_hold_change":
        artifact_type = payload.get("artifact_type", approval.target_resource_id or "evidence_pack")
        legal_hold_enabled = bool(payload.get("legal_hold_enabled", False))
        notes = payload_wrapper.get("justification", "") or payload.get("notes", "") or "Applied from approved governance request"

        row = (
            db.query(models.RetentionPolicy)
            .filter(
                models.RetentionPolicy.tenant_id == approval.tenant_id,
                models.RetentionPolicy.artifact_type == artifact_type,
            )
            .order_by(models.RetentionPolicy.id.desc())
            .first()
        )

        before_state = _policy_state(row)

        if row:
            row.legal_hold_enabled = legal_hold_enabled
            row.notes = notes
            db.add(row)
            db.commit()
            db.refresh(row)
        else:
            row = models.RetentionPolicy(
                tenant_id=approval.tenant_id,
                tenant_name=approval.tenant_name,
                artifact_type=artifact_type,
                retention_days=365,
                legal_hold_enabled=legal_hold_enabled,
                notes=notes,
                is_enabled=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)

        after_state = _policy_state(row)
        rollback = record_rollback_entry(db, approval=approval, before_state=before_state, after_state=after_state)

        return {
            "resource_type": "retention_policy",
            "resource_id": row.id,
            "rollback_id": rollback.id,
            "message": f"Legal hold updated for {artifact_type}",
        }

    if request_type == "retention_change":
        artifact_type = payload.get("artifact_type", approval.target_resource_id or "evidence_pack")
        retention_days = int(payload.get("retention_days", 365))
        notes = payload_wrapper.get("justification", "") or payload.get("notes", "") or "Applied from approved governance request"

        row = (
            db.query(models.RetentionPolicy)
            .filter(
                models.RetentionPolicy.tenant_id == approval.tenant_id,
                models.RetentionPolicy.artifact_type == artifact_type,
            )
            .order_by(models.RetentionPolicy.id.desc())
            .first()
        )

        before_state = _policy_state(row)

        if row:
            row.retention_days = retention_days
            row.notes = notes or row.notes
            db.add(row)
            db.commit()
            db.refresh(row)
        else:
            row = models.RetentionPolicy(
                tenant_id=approval.tenant_id,
                tenant_name=approval.tenant_name,
                artifact_type=artifact_type,
                retention_days=retention_days,
                legal_hold_enabled=False,
                notes=notes,
                is_enabled=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)

        after_state = _policy_state(row)
        rollback = record_rollback_entry(db, approval=approval, before_state=before_state, after_state=after_state)

        return {
            "resource_type": "retention_policy",
            "resource_id": row.id,
            "rollback_id": rollback.id,
            "message": f"Retention updated for {artifact_type}",
        }

    if request_type == "tenant_role_change":
        user_email = str(payload.get("user_email", "")).strip().lower()
        role_name = str(payload.get("role_name", "viewer")).strip()

        if not user_email:
            raise ValueError("tenant_role_change requires user_email")

        row = (
            db.query(models.TenantMembership)
            .filter(
                models.TenantMembership.user_email == user_email,
                models.TenantMembership.tenant_id == approval.tenant_id,
            )
            .order_by(models.TenantMembership.id.desc())
            .first()
        )

        before_state = _membership_state(row)

        if row:
            row.role_name = role_name
            row.is_enabled = True
            db.add(row)
            db.commit()
            db.refresh(row)
        else:
            row = models.TenantMembership(
                user_email=user_email,
                tenant_id=approval.tenant_id,
                tenant_name=approval.tenant_name,
                role_name=role_name,
                is_enabled=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)

        after_state = _membership_state(row)
        rollback = record_rollback_entry(db, approval=approval, before_state=before_state, after_state=after_state)

        return {
            "resource_type": "tenant_membership",
            "resource_id": row.id,
            "rollback_id": rollback.id,
            "message": f"Tenant role updated for {user_email}",
        }

    raise ValueError(f"Unsupported request_type: {approval.request_type}")


def mark_execution_result(
    db: Session,
    approval: models.GovernanceApproval,
    *,
    status: str,
    notes: str,
):
    approval.execution_status = status
    approval.execution_notes = notes[:2000]
    approval.executed_at = _now()
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval
