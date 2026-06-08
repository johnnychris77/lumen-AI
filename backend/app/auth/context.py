from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuthContext:
    actor: str
    role: str
    tenant_id: str = "default-tenant"
    tenant_name: str = "default-tenant"
    subject: str = ""
    permissions: tuple[str, ...] = field(default_factory=tuple)
    auth_provider: str = "dev"
    issuer: str = ""
    raw_claims: dict[str, Any] = field(default_factory=dict)

    def has_role(self, allowed_roles: set[str]) -> bool:
        return self.role in allowed_roles

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def to_audit_details(self) -> dict[str, Any]:
        return {
            "actor": self.actor,
            "actor_role": self.role,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "subject": self.subject,
            "auth_provider": self.auth_provider,
            "issuer": self.issuer,
            "permissions": list(self.permissions),
        }


def build_dev_auth_context(
    *,
    actor: str = "unknown",
    role: str = "",
    tenant_id: str = "default-tenant",
    tenant_name: str | None = None,
) -> AuthContext:
    resolved_tenant_name = tenant_name or tenant_id or "default-tenant"

    return AuthContext(
        actor=actor or "unknown",
        role=role or "",
        tenant_id=tenant_id or "default-tenant",
        tenant_name=resolved_tenant_name,
        auth_provider="dev",
        permissions=role_to_permissions(role or ""),
    )


def role_to_permissions(role: str) -> tuple[str, ...]:
    permissions_by_role = {
        "enterprise_admin": (
            "governance_packet:export",
            "governance_packet:verify",
            "governance_packet:certificate",
            "vendor_baseline:approve",
            "vendor_baseline:audit_read",
            "vendor_baseline:library_read",
            "audit:verify_chain",
            "retention:evaluate",
            "tenant:admin",
        ),
        "hospital_admin": (
            "governance_packet:export",
            "governance_packet:verify",
            "governance_packet:certificate",
            "vendor_baseline:approve",
            "vendor_baseline:audit_read",
            "vendor_baseline:library_read",
            "audit:verify_chain",
            "retention:evaluate",
        ),
        "vendor": (
            "vendor_baseline:submit",
        ),
        "viewer": (
            "governance_packet:verify",
        ),
    }

    return permissions_by_role.get(role, tuple())
