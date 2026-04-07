from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["tenant-setup"])


@router.get("/tenant-setup/readiness")
def tenant_setup_readiness(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    memberships = db.query(models.TenantMembership).filter(models.TenantMembership.tenant_id == tenant["tenant_id"]).count()
    policies = db.query(models.RetentionPolicy).filter(models.RetentionPolicy.tenant_id == tenant["tenant_id"]).count()
    subscriptions = db.query(models.DigestSubscription).filter(models.DigestSubscription.site_name.in_(["all", tenant["tenant_id"], tenant["tenant_name"]])).count()
    onboarding = (
        db.query(models.TenantOnboarding)
        .filter(models.TenantOnboarding.tenant_id == tenant["tenant_id"])
        .order_by(models.TenantOnboarding.id.desc())
        .first()
    )

    return JSONResponse({
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "onboarded": onboarding is not None,
        "checks": {
            "tenant_admin_membership": memberships > 0,
            "retention_policies_present": policies > 0,
            "digest_subscriptions_present": subscriptions > 0,
        },
        "counts": {
            "memberships": memberships,
            "retention_policies": policies,
            "digest_subscriptions": subscriptions,
        },
    })
