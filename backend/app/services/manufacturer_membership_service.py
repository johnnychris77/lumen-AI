"""Manufacturer-membership lifecycle (P472-03 Batch 5 B5.2, AW-07).

``require_manufacturer_auth`` resolves a manufacturer / repair-partner identity
only from an enabled, unexpired ``ManufacturerMembership``. Until Batch 5 no
code path created or revoked one, so both happened as unaudited database edits.

This module is the ONLY writer of membership lifecycle state. It contains only
policy-independent, fail-closed plumbing; the IAM policy — who may grant or
revoke, identity proofing, the role catalogue, expiry rules, approval workflow
— is governance decision GD-9 and is NOT decided here:

* ``revoke_manufacturer_membership`` only ever REDUCES access, so it is usable
  now: it disables the membership, records who/when/why on the row, and writes a
  hash-chained audit event. It is idempotent. Effect is immediate (enforcement
  reads the table on every request).
* ``grant_manufacturer_membership`` is GATED CLOSED (``GRANTS_APPROVED = False``).
  While closed it refuses before validating or writing anything. Opening the
  gate is a code change that requires the IAM owner's signed GD-9 decision.

No HTTP route calls either function (asserted by the tests): which principals
may invoke them is part of GD-9.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ManufacturerMembership
from app.services.enterprise_audit_service import record_enterprise_audit_event

AUDIT_RESOURCE_TYPE = "manufacturer_membership"
AUDIT_GRANTED = "manufacturer_membership.granted"
AUDIT_REVOKED = "manufacturer_membership.revoked"

# GD-9 (IAM owner) has not approved a grant policy. Do not change without it.
GRANTS_APPROVED = False

# Least-privilege role catalogue for the grant path. Broader manufacturer roles
# are a GD-9 decision; until then only read access can be granted.
GRANTABLE_ROLES = frozenset({"manufacturer_viewer"})

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ORG_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$")


class ManufacturerIamGateClosed(PermissionError):
    """The grant path is disabled until the IAM owner approves a policy (GD-9)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _required(value: str | None, name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def revoke_manufacturer_membership(
    db: Session,
    *,
    membership_id: int,
    revoked_by: str,
    reason: str,
) -> dict[str, Any]:
    """Disable a membership and audit who did it and why. Idempotent."""
    actor = _required(revoked_by, "revoked_by")
    why = _required(reason, "reason")
    row = db.get(ManufacturerMembership, membership_id)
    if row is None:
        raise LookupError(f"manufacturer membership {membership_id} does not exist")
    if not row.is_enabled and row.revoked_at is not None:
        return {"membership_id": row.id, "changed": False}

    revoked_at = _now()
    row.is_enabled = False
    row.revoked_at = revoked_at
    row.revoked_by = actor
    row.revocation_reason = why[:500]
    record_enterprise_audit_event(
        db,
        action_type=AUDIT_REVOKED,
        resource_type=AUDIT_RESOURCE_TYPE,
        resource_id=str(row.id),
        actor=actor,
        actor_email=actor,
        actor_role="iam_operator",
        tenant_id=None,
        details={
            "manufacturer_id": row.manufacturer_id,
            "user_email": row.user_email,
            "role": row.role,
            "revoked_by": actor,
            "reason": why[:500],
            "revoked_at": revoked_at.isoformat(),
        },
        commit=False,
    )
    db.commit()
    return {"membership_id": row.id, "changed": True}


def grant_manufacturer_membership(
    db: Session,
    *,
    manufacturer_id: str,
    user_email: str,
    role: str,
    granted_by: str,
    grant_reference: str,
    expires_at: datetime | None = None,
) -> dict[str, Any]:
    """Grant a membership — refused while the GD-9 gate is closed."""
    if not GRANTS_APPROVED:
        raise ManufacturerIamGateClosed(
            "manufacturer-membership grants are disabled until the IAM owner approves a policy (GD-9)")

    org = _required(manufacturer_id, "manufacturer_id")
    user = _required(user_email, "user_email").lower()
    grantor = _required(granted_by, "granted_by").lower()
    reference = _required(grant_reference, "grant_reference")
    if not _ORG_ID.match(org):
        raise ValueError("manufacturer_id is malformed")
    if not _EMAIL.match(user):
        raise ValueError("user_email must be an email address")
    if role not in GRANTABLE_ROLES:
        raise ValueError(f"role {role!r} is not grantable (allowed: {sorted(GRANTABLE_ROLES)})")
    if user == grantor:
        raise ValueError("a membership cannot be self-granted")
    expiry = _aware(expires_at)
    if expiry is not None and expiry <= _now():
        raise ValueError("expires_at is in the past")

    existing = (db.query(ManufacturerMembership)
                .filter(ManufacturerMembership.user_email == user,
                        ManufacturerMembership.manufacturer_id == org)
                .first())
    if existing is not None:
        # Re-enabling a revoked membership (or changing a live one) is a distinct,
        # policy-dependent action; never do it implicitly through a grant.
        raise ValueError("a membership for this user and organization already exists")

    row = ManufacturerMembership(
        manufacturer_id=org, user_email=user, role=role, is_enabled=True,
        expires_at=expiry, granted_by=grantor, grant_reference=reference,
    )
    db.add(row)
    db.flush()
    record_enterprise_audit_event(
        db,
        action_type=AUDIT_GRANTED,
        resource_type=AUDIT_RESOURCE_TYPE,
        resource_id=str(row.id),
        actor=grantor,
        actor_email=grantor,
        actor_role="iam_operator",
        tenant_id=None,
        details={
            "manufacturer_id": org,
            "user_email": user,
            "role": role,
            "granted_by": grantor,
            "grant_reference": reference,
            "expires_at": expiry.isoformat() if expiry else None,
        },
        commit=False,
    )
    db.commit()
    return {"membership_id": row.id, "changed": True}
