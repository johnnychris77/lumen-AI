from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.branding import get_branding
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["branding"])


class BrandingPayload(BaseModel):
    display_name: str = ""
    logo_url: str = ""
    accent_color: str = "#2563eb"
    welcome_text: str = ""
    export_prefix: str = ""
    support_email: str = ""


def _branding_response(row: models.TenantBranding) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "display_name": row.display_name,
        "logo_url": row.logo_url,
        "accent_color": row.accent_color,
        "welcome_text": row.welcome_text,
        "export_prefix": row.export_prefix,
        "support_email": row.support_email,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/branding")
def branding_summary(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return get_branding(db, tenant["tenant_id"], tenant["tenant_name"])


@router.get("/branding/theme")
def branding_theme(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    branding = get_branding(db, tenant["tenant_id"], tenant["tenant_name"])
    return {
        "tenant_id": branding["tenant_id"],
        "tenant_name": branding["tenant_name"],
        "display_name": branding["display_name"],
        "logo_url": branding["logo_url"],
        "accent_color": branding["accent_color"],
        "welcome_text": branding["welcome_text"],
    }


@router.get("/branding/export-profile")
def branding_export_profile(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    branding = get_branding(db, tenant["tenant_id"], tenant["tenant_name"])
    return {
        "tenant_id": branding["tenant_id"],
        "tenant_name": branding["tenant_name"],
        "display_name": branding["display_name"],
        "export_prefix": branding["export_prefix"],
        "support_email": branding["support_email"],
    }


@router.post("/branding")
def set_branding(
    payload: BrandingPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.TenantBranding(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        display_name=payload.display_name or tenant["tenant_name"],
        logo_url=payload.logo_url,
        accent_color=payload.accent_color or "#2563eb",
        welcome_text=payload.welcome_text,
        export_prefix=payload.export_prefix or tenant["tenant_id"],
        support_email=payload.support_email,
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
        action_type="tenant_branding_set",
        resource_type="tenant_branding",
        resource_id=row.id,
        request=request,
        details=_branding_response(row),
        compliance_flag=True,
    )

    return {"item": _branding_response(row)}
