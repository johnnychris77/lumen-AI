"""v3.2 — Project Nexus, Section 5: User Identity Integration.

Maps external directory/SSO groups (LDAP, Azure AD, Entra ID, OIDC, SAML)
to LumenAI roles. Resolution is least-privilege by construction: if none
of a user's external groups have a mapping on file, they resolve to
`viewer` (`DEFAULT_IDENTITY_ROLE`) rather than any elevated default —
Section 10's "least privilege" requirement applied directly to
provisioning, not just to route gating.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.nexus_integration import (
    DEFAULT_IDENTITY_ROLE,
    NEXUS_IDENTITY_ROLES,
    NexusIdentityMapping,
)


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def create_mapping(
    db: Session, tenant_id: str, connector_id: int, *, external_group: str, mapped_role: str, auto_provision: bool = False,
) -> dict:
    if mapped_role not in NEXUS_IDENTITY_ROLES:
        raise ValueError(f"mapped_role must be one of {NEXUS_IDENTITY_ROLES}")

    existing = (
        db.query(NexusIdentityMapping)
        .filter(
            NexusIdentityMapping.tenant_id == tenant_id, NexusIdentityMapping.connector_id == connector_id,
            NexusIdentityMapping.external_group == external_group,
        )
        .first()
    )
    if existing is not None:
        existing.mapped_role = mapped_role
        existing.auto_provision = auto_provision
        db.commit()
        db.refresh(existing)
        return _row_to_dict(existing)

    row = NexusIdentityMapping(
        connector_id=connector_id, tenant_id=tenant_id, external_group=external_group,
        mapped_role=mapped_role, auto_provision=auto_provision,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_mappings(db: Session, tenant_id: str, connector_id: int) -> list[dict]:
    rows = (
        db.query(NexusIdentityMapping)
        .filter(NexusIdentityMapping.tenant_id == tenant_id, NexusIdentityMapping.connector_id == connector_id)
        .order_by(NexusIdentityMapping.id.asc())
        .all()
    )
    return [_row_to_dict(r) for r in rows]


# Highest-privilege-first — if a user belongs to multiple mapped groups,
# resolution picks the most privileged role they qualify for, not the first
# match in arbitrary order.
_ROLE_PRECEDENCE = ["administrator", "director", "manager", "supervisor", "technician", "viewer"]


def resolve_role_for_groups(db: Session, tenant_id: str, connector_id: int, external_groups: list[str]) -> dict:
    mappings = (
        db.query(NexusIdentityMapping)
        .filter(
            NexusIdentityMapping.tenant_id == tenant_id, NexusIdentityMapping.connector_id == connector_id,
            NexusIdentityMapping.external_group.in_(external_groups),
        )
        .all()
    )
    if not mappings:
        return {"mapped_role": DEFAULT_IDENTITY_ROLE, "matched_groups": [], "auto_provision": False}

    matched_roles = {m.mapped_role for m in mappings}
    best_role = next((r for r in _ROLE_PRECEDENCE if r in matched_roles), DEFAULT_IDENTITY_ROLE)
    matched = [m.external_group for m in mappings if m.mapped_role == best_role]
    auto_provision = any(m.auto_provision for m in mappings if m.mapped_role == best_role)
    return {"mapped_role": best_role, "matched_groups": matched, "auto_provision": auto_provision}
