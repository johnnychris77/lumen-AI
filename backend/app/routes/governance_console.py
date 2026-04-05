from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models
from app.retention import compute_retention_metadata
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["governance-console"])


@router.get("/governance-console/summary")
def governance_console_summary(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    policy_rows = (
        db.query(models.RetentionPolicy)
        .filter(
            models.RetentionPolicy.tenant_id == tenant["tenant_id"],
            models.RetentionPolicy.is_enabled == True,
        )
        .order_by(models.RetentionPolicy.id.desc())
        .all()
    )

    subscription_rows = (
        db.query(models.DigestSubscription)
        .filter(models.DigestSubscription.is_enabled == True)
        .order_by(models.DigestSubscription.id.desc())
        .all()
    )

    scoped_subscriptions = [
        s for s in subscription_rows
        if (s.site_name in ["all", tenant["tenant_id"], tenant["tenant_name"]])
    ]

    evidence_retention = compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "evidence_pack")
    inspection_retention = compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "inspection")
    audit_retention = compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "audit_log")
    digest_retention = compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "digest_delivery")

    return JSONResponse({
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "retention": {
            "evidence_pack": evidence_retention,
            "inspection": inspection_retention,
            "audit_log": audit_retention,
            "digest_delivery": digest_retention,
        },
        "legal_hold_enabled": any(bool(p.legal_hold_enabled) for p in policy_rows),
        "retention_policy_count": len(policy_rows),
        "subscription_count": len(scoped_subscriptions),
        "compliance_exports": {
            "json": "/api/compliance-exports/evidence-pack.json",
            "csv": "/api/compliance-exports/evidence-pack.csv",
            "xlsx": "/api/compliance-exports/evidence-pack.xlsx",
            "bundle": "/api/compliance-exports/evidence-pack.bundle.zip",
        },
    })
