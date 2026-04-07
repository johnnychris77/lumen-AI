from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models
from app.retention import compute_retention_metadata
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["trust-center"])


def _approval_item(row: models.GovernanceApproval) -> dict:
    return {
        "id": row.id,
        "request_type": row.request_type,
        "target_resource": row.target_resource,
        "target_resource_id": row.target_resource_id,
        "status": row.status,
        "execution_status": getattr(row, "execution_status", ""),
        "requested_by": row.requested_by,
        "reviewed_by": row.reviewed_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "executed_at": row.executed_at.isoformat() if getattr(row, "executed_at", None) else None,
    }


def _rollback_item(row: models.GovernanceRollback) -> dict:
    return {
        "id": row.id,
        "approval_id": row.approval_id,
        "request_type": row.request_type,
        "target_resource": row.target_resource,
        "target_resource_id": row.target_resource_id,
        "rollback_status": row.rollback_status,
        "rolled_back_by": row.rolled_back_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "rolled_back_at": row.rolled_back_at.isoformat() if row.rolled_back_at else None,
    }


def _audit_item(row: models.AuditLog) -> dict:
    return {
        "id": row.id,
        "actor_email": row.actor_email,
        "actor_role": row.actor_role,
        "action_type": row.action_type,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "status": row.status,
        "compliance_flag": row.compliance_flag,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/trust-center/summary")
def trust_center_summary(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    approvals = (
        db.query(models.GovernanceApproval)
        .filter(models.GovernanceApproval.tenant_id == tenant["tenant_id"])
        .order_by(models.GovernanceApproval.id.desc())
        .limit(25)
        .all()
    )

    rollbacks = (
        db.query(models.GovernanceRollback)
        .filter(models.GovernanceRollback.tenant_id == tenant["tenant_id"])
        .order_by(models.GovernanceRollback.id.desc())
        .limit(25)
        .all()
    )

    audits = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.tenant_id == tenant["tenant_id"])
        .order_by(models.AuditLog.id.desc())
        .limit(50)
        .all()
    )

    retention = {
        "evidence_pack": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "evidence_pack"),
        "inspection": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "inspection"),
        "audit_log": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "audit_log"),
        "digest_delivery": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "digest_delivery"),
    }

    attestations = [
        {
            "control": "Dual-control governance approvals",
            "status": "active",
            "description": "High-risk governance changes require request and separate approval.",
        },
        {
            "control": "Tenant-scoped audit logging",
            "status": "active",
            "description": "Administrative and governance actions are recorded per tenant.",
        },
        {
            "control": "Signed evidence manifests",
            "status": "active",
            "description": "Evidence packs support tamper-evident verification metadata.",
        },
        {
            "control": "Retention and legal hold governance",
            "status": "active",
            "description": "Artifacts can be governed by retention policies and legal hold protections.",
        },
    ]

    return JSONResponse({
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "attestations": attestations,
        "retention": retention,
        "governance_history": {
            "approvals": [_approval_item(x) for x in approvals],
            "rollbacks": [_rollback_item(x) for x in rollbacks],
        },
        "audit_activity": [_audit_item(x) for x in audits],
        "verification": {
            "verify_endpoint": "/api/compliance-exports/verify",
            "evidence_json_endpoint": "/api/compliance-exports/evidence-pack.json",
            "evidence_bundle_endpoint": "/api/compliance-exports/evidence-pack.bundle.zip",
        },
    })
