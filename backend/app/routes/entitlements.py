from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.entitlements import resolve_entitlements, is_feature_enabled
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["entitlements"])


class EntitlementOverridePayload(BaseModel):
    feature_key: str
    is_enabled: bool
    notes: str = ""


class FeatureFlagPayload(BaseModel):
    flag_key: str
    is_enabled: bool
    notes: str = ""


def _entitlement_row(row: models.TenantEntitlement) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "feature_key": row.feature_key,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _flag_row(row: models.FeatureFlag) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "flag_key": row.flag_key,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/entitlements")
def get_entitlements(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return resolve_entitlements(db, tenant["tenant_id"], tenant["tenant_name"])


@router.get("/feature-access/{feature_key}")
def get_feature_access(
    feature_key: str,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return is_feature_enabled(db, tenant["tenant_id"], tenant["tenant_name"], feature_key)


@router.post("/entitlements/override")
def create_entitlement_override(
    payload: EntitlementOverridePayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.TenantEntitlement(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        feature_key=payload.feature_key,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="entitlement_override_create",
        resource_type="tenant_entitlement",
        resource_id=row.id,
        request=request,
        details=_entitlement_row(row),
        compliance_flag=True,
    )

    return {"item": _entitlement_row(row)}


@router.get("/feature-flags")
def get_flags(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.FeatureFlag)
        .filter(models.FeatureFlag.tenant_id == tenant["tenant_id"])
        .order_by(models.FeatureFlag.id.desc())
        .all()
    )
    return {"items": [_flag_row(r) for r in rows]}


@router.post("/feature-flags")
def create_flag(
    payload: FeatureFlagPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.FeatureFlag(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        flag_key=payload.flag_key,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="feature_flag_create",
        resource_type="feature_flag",
        resource_id=row.id,
        request=request,
        details=_flag_row(row),
        compliance_flag=True,
    )

    return {"item": _flag_row(row)}
