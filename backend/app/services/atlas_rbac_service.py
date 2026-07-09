"""v3.1 — Project Atlas, Section 10: Enterprise Governance / RBAC.

There is no central role registry anywhere in this codebase today — four
independent auth modules (`authz.py`, `enterprise_auth.py`,
`tenant_authz.py`, `portfolio_authz.py`) each declare their own ad hoc role
strings, checked per-route with no shared enum. This module doesn't
replace that (out of scope for this sprint), but it does the one thing
none of the four already do: scope a role to a specific node in the
existing organization hierarchy (system/market/facility) so "Market
Director for market X" is a real, checkable fact — not just a flat role
string with no notion of which market.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.atlas_enterprise import (
    ENTERPRISE_ROLES,
    ROLE_SCOPES,
    SCOPE_FACILITY,
    SCOPE_MARKET,
    SCOPE_SYSTEM,
    EnterpriseRoleAssignment,
)


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def grant_role(db: Session, *, user_email: str, role: str, scope_type: str, scope_id: str, granted_by: str) -> dict:
    if role not in ENTERPRISE_ROLES:
        raise ValueError(f"role must be one of {ENTERPRISE_ROLES}")
    if scope_type not in ROLE_SCOPES:
        raise ValueError(f"scope_type must be one of {ROLE_SCOPES}")

    row = EnterpriseRoleAssignment(user_email=user_email, role=role, scope_type=scope_type, scope_id=scope_id, granted_by=granted_by)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_roles_for_user(db: Session, user_email: str) -> list[dict]:
    rows = (
        db.query(EnterpriseRoleAssignment)
        .filter(EnterpriseRoleAssignment.user_email == user_email, EnterpriseRoleAssignment.active.is_(True))
        .order_by(EnterpriseRoleAssignment.id.desc())
        .all()
    )
    return [_row_to_dict(r) for r in rows]


def revoke_role(db: Session, assignment_id: int) -> dict | None:
    row = db.query(EnterpriseRoleAssignment).filter(EnterpriseRoleAssignment.id == assignment_id).first()
    if row is None:
        return None
    row.active = False
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def _facility_lineage(db: Session, facility_id: str) -> tuple[str | None, str | None]:
    """Returns (market_id, system_id) for a facility, or (None, None) if unknown."""
    facility = db.query(models.EnterpriseFacility).filter(models.EnterpriseFacility.facility_id == facility_id).first()
    if facility is None:
        return None, None
    return facility.market_id, facility.system_id


def _market_lineage(db: Session, market_id: str) -> str | None:
    market = db.query(models.EnterpriseMarket).filter(models.EnterpriseMarket.market_id == market_id).first()
    return market.system_id if market is not None else None


def user_has_scope_access(db: Session, user_email: str, *, scope_type: str, scope_id: str) -> bool:
    """A role granted at a higher level in the hierarchy implies access at
    every level below it — a System-scoped role sees every market and
    facility under that system; a Market-scoped role sees every facility
    in that market."""
    assignments = (
        db.query(EnterpriseRoleAssignment)
        .filter(EnterpriseRoleAssignment.user_email == user_email, EnterpriseRoleAssignment.active.is_(True))
        .all()
    )
    if not assignments:
        return False

    if scope_type == SCOPE_SYSTEM:
        candidate_scopes = {(SCOPE_SYSTEM, scope_id)}
    elif scope_type == SCOPE_MARKET:
        system_id = _market_lineage(db, scope_id)
        candidate_scopes = {(SCOPE_MARKET, scope_id)}
        if system_id:
            candidate_scopes.add((SCOPE_SYSTEM, system_id))
    else:  # SCOPE_FACILITY
        market_id, system_id = _facility_lineage(db, scope_id)
        candidate_scopes = {(SCOPE_FACILITY, scope_id)}
        if market_id:
            candidate_scopes.add((SCOPE_MARKET, market_id))
        if system_id:
            candidate_scopes.add((SCOPE_SYSTEM, system_id))

    return any((a.scope_type, a.scope_id) in candidate_scopes for a in assignments)
