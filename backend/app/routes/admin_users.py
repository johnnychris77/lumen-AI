"""Founder/admin user-management: bootstrap the first admin and assign roles.

- POST /api/admin/bootstrap  — one-time elevation of an account to admin,
  gated by the ADMIN_BOOTSTRAP_TOKEN env secret (inert if the secret is unset).
- GET  /api/admin/users      — list role assignments (admin only).
- POST /api/admin/users/role — assign a role to a user (admin only).

Roles: admin, spd_manager (Manager), supervisor, viewer.
"""
from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.models.user_role_assignment import UserRoleAssignment

router = APIRouter(prefix="/api/admin", tags=["admin-users"])

ASSIGNABLE_ROLES = {"admin", "spd_manager", "supervisor", "operator", "viewer", "vendor_user"}


def _upsert_role(db: Session, username: str, role: str, assigned_by: str) -> UserRoleAssignment:
    from sqlalchemy import func

    row = (
        db.query(UserRoleAssignment)
        .filter(func.lower(UserRoleAssignment.username) == username.strip().lower())
        .first()
    )
    now = datetime.now(timezone.utc)
    if row:
        row.role = role
        row.assigned_by = assigned_by
        row.updated_at = now
    else:
        row = UserRoleAssignment(username=username, role=role, assigned_by=assigned_by)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


class BootstrapRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255, description="Email/username to elevate")
    password: str | None = Field(
        default=None, min_length=8, max_length=200,
        description="Optional: set/replace a password so this account can log in as admin.",
    )


@router.post("/bootstrap")
def bootstrap_admin(
    body: BootstrapRequest,
    db: Session = Depends(get_db),
    x_bootstrap_token: str | None = Header(default=None),
):
    """Grant admin to an account using the server-side ADMIN_BOOTSTRAP_TOKEN.

    The deployment owner sets ADMIN_BOOTSTRAP_TOKEN in the environment, then
    calls this once with the matching X-Bootstrap-Token header. Inert (404)
    when the secret is not configured so it can't be abused by default.

    If a `password` is supplied, a real, login-capable admin credential is
    created/updated so the founder can sign in even though there is no
    registration flow.
    """
    secret = os.getenv("ADMIN_BOOTSTRAP_TOKEN", "").strip()
    if not secret:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_bootstrap_token or not hmac.compare_digest(x_bootstrap_token, secret):
        raise HTTPException(status_code=403, detail="Invalid bootstrap token")

    row = _upsert_role(db, body.username, "admin", assigned_by="bootstrap")

    credential_set = False
    if body.password:
        from datetime import datetime, timezone
        from passlib.hash import bcrypt
        from sqlalchemy import func
        from app.models.admin_credential import AdminCredential

        cred = (
            db.query(AdminCredential)
            .filter(func.lower(AdminCredential.username) == body.username.strip().lower())
            .first()
        )
        pw_hash = bcrypt.hash(body.password)
        if cred:
            cred.password_hash = pw_hash
            cred.role = "admin"
            cred.updated_at = datetime.now(timezone.utc)
        else:
            cred = AdminCredential(username=body.username, password_hash=pw_hash, role="admin")
            db.add(cred)
        db.commit()
        credential_set = True

    log_audit_event(
        db,
        tenant_id="platform",
        tenant_name="platform",
        actor_email=body.username,
        actor_role="admin",
        action_type="admin_bootstrap_granted",
        resource_type="user_role_assignment",
        resource_id=str(row.id),
        compliance_flag=True,
    )
    return {
        "username": row.username,
        "role": row.role,
        "status": "admin granted",
        "login_password_set": credential_set,
    }


@router.get("/users")
def list_user_roles(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    rows = db.query(UserRoleAssignment).order_by(UserRoleAssignment.username).all()
    return {
        "users": [
            {
                "username": r.username,
                "role": r.role,
                "assigned_by": r.assigned_by,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
        "assignable_roles": sorted(ASSIGNABLE_ROLES),
    }


class RoleAssignment(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    role: str = Field(...)


@router.post("/users/role")
def assign_role(
    body: RoleAssignment,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    if body.role not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"role must be one of {sorted(ASSIGNABLE_ROLES)}",
        )
    actor = getattr(current_user, "email", None) or getattr(current_user, "username", "admin")
    row = _upsert_role(db, body.username, body.role, assigned_by=actor)

    log_audit_event(
        db,
        tenant_id=getattr(current_user, "tenant_id", "") or "platform",
        tenant_name="platform",
        actor_email=actor,
        actor_role="admin",
        action_type="user_role_assigned",
        resource_type="user_role_assignment",
        resource_id=str(row.id),
        details={"username": row.username, "role": row.role},
        compliance_flag=True,
    )
    return {"username": row.username, "role": row.role, "assigned_by": row.assigned_by}
