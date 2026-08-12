from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models

router = APIRouter(tags=["tenant-admin"])


class TenantMembershipPayload(BaseModel):
    user_email: str
    tenant_id: str
    # `role` is the live model's column. `role_name` is accepted as a
    # backward-compatible alias (older callers/docs used it). `tenant_name` is
    # accepted-and-ignored for the same reason (the live model has no such column).
    role: str = Field("viewer", validation_alias="role", serialization_alias="role")
    role_name: str | None = None
    tenant_name: str | None = None
    is_enabled: bool = True

    def effective_role(self) -> str:
        return (self.role_name or self.role or "viewer").strip() or "viewer"


def _membership_response(row: models.TenantMembership) -> dict:
    # Read defensively so a schema variant can't 500 the endpoint. The live
    # model exposes `role`; `role_name`/`tenant_name` are surfaced as aliases for
    # any client that still expects them.
    role = getattr(row, "role", None) or getattr(row, "role_name", None) or "viewer"
    return {
        "id": row.id,
        "user_email": row.user_email,
        "tenant_id": row.tenant_id,
        "tenant_name": getattr(row, "tenant_name", None) or row.tenant_id,
        "role": role,
        "role_name": role,
        "is_enabled": row.is_enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/tenant-admin/memberships")
def list_tenant_memberships(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    # Scope to the caller's verified tenant(s) unless they are a platform admin.
    # Use the principal's own membership-verified authority (never a client
    # header or a brittle email-suffix heuristic).
    is_platform_admin = bool(getattr(current_user, "is_platform_admin", False))
    query = db.query(models.TenantMembership)
    if not is_platform_admin:
        verified = getattr(current_user, "verified_tenant_ids", lambda: frozenset())()
        if verified:
            query = query.filter(models.TenantMembership.tenant_id.in_(list(verified)))
        else:
            # No verified tenant → nothing to show (fail closed, never list all).
            query = query.filter(models.TenantMembership.id.is_(None))
    rows = query.order_by(models.TenantMembership.id.desc()).all()

    actor_email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "unknown"
    log_audit_event(
        db,
        tenant_id="platform",
        tenant_name="Platform Admin",
        actor_email=actor_email,
        actor_role="admin",
        action_type="tenant_memberships_list",
        resource_type="tenant_membership",
        request=request,
        details={"count": len(rows)},
        compliance_flag=True,
    )

    return {"items": [_membership_response(r) for r in rows]}


@router.post("/tenant-admin/memberships")
def create_tenant_membership(
    payload: TenantMembershipPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    row = models.TenantMembership(
        user_email=payload.user_email.strip().lower(),
        tenant_id=payload.tenant_id.strip(),
        role=payload.effective_role(),
        is_enabled=payload.is_enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    actor_email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "unknown"
    log_audit_event(
        db,
        tenant_id=payload.tenant_id,
        tenant_name=payload.tenant_id,
        actor_email=actor_email,
        actor_role="admin",
        action_type="tenant_membership_create",
        resource_type="tenant_membership",
        resource_id=row.id,
        request=request,
        details=_membership_response(row),
        compliance_flag=True,
    )

    return {"item": _membership_response(row)}


@router.post("/tenant-admin/memberships/{membership_id}/toggle")
def toggle_tenant_membership(
    membership_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    row = db.query(models.TenantMembership).filter(models.TenantMembership.id == membership_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant membership not found")

    row.is_enabled = not bool(row.is_enabled)
    db.add(row)
    db.commit()
    db.refresh(row)

    actor_email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "unknown"
    log_audit_event(
        db,
        tenant_id=row.tenant_id,
        tenant_name=row.tenant_id,
        actor_email=actor_email,
        actor_role="admin",
        action_type="tenant_membership_toggle",
        resource_type="tenant_membership",
        resource_id=row.id,
        request=request,
        details={"is_enabled": row.is_enabled, "user_email": row.user_email, "role": getattr(row, "role", None)},
        compliance_flag=True,
    )

    return {"item": _membership_response(row)}


# ---------------------------------------------------------------------------
# Pilot tenant provisioning (admin only)
# ---------------------------------------------------------------------------

_TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]$")


class ProvisionTenantRequest(BaseModel):
    tenant_id: str = Field(..., min_length=3, max_length=64)
    tenant_name: str = Field(..., min_length=1, max_length=255)
    admin_email: str = Field(..., description="Email for initial admin user of this tenant")
    region: str = Field("north_america", description="Tenant data region")

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        if not _TENANT_ID_RE.match(v):
            raise ValueError("tenant_id must be lowercase alphanumeric with hyphens, 3–64 chars")
        return v

    @field_validator("admin_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or len(v) > 254:
            raise ValueError("admin_email must be a valid email address")
        return v.strip().lower()

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        allowed = {"north_america", "eu", "apac", "uk", "canada", "australia"}
        if v not in allowed:
            raise ValueError(f"region must be one of: {sorted(allowed)}")
        return v


@router.post("/admin/tenants", status_code=201)
def provision_pilot_tenant(
    payload: ProvisionTenantRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Provision a new pilot tenant with an initial admin membership. Admin role only."""
    existing = db.query(models.TenantMembership).filter(
        models.TenantMembership.tenant_id == payload.tenant_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Tenant '{payload.tenant_id}' already exists")

    row = models.TenantMembership(
        user_email=payload.admin_email,
        tenant_id=payload.tenant_id,
        role="spd_manager",
        is_enabled=True,
        tenant_region=payload.region,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    actor_email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "unknown"
    log_audit_event(
        db,
        tenant_id=payload.tenant_id,
        tenant_name=payload.tenant_name,
        actor_email=actor_email,
        actor_role="admin",
        action_type="pilot_tenant_provisioned",
        resource_type="tenant",
        resource_id=payload.tenant_id,
        request=request,
        details={
            "admin_email": payload.admin_email,
            "region": payload.region,
        },
        compliance_flag=True,
    )

    return {
        "tenant_id": payload.tenant_id,
        "tenant_name": payload.tenant_name,
        "admin_email": payload.admin_email,
        "region": payload.region,
        "status": "provisioned",
        "membership_id": row.id,
    }
