"""v4.0 — LumenAI OS (Project Genesis), Section 1: Platform Core —
Licensing.

Extends `app/entitlements.py`'s existing per-tenant plan/feature-flag
resolution with a concept it never had: a per-tenant, per-*module*
license. The module concept itself (Inspect/Twin/Knowledge/...) is new
in this sprint, so there was nothing in `entitlements.py` to extend
directly for it — this is a genuinely new, small table
(`PlatformModuleLicense`), not a duplicate of the plan/feature-flag
system. A tenant with no explicit license row for a module is licensed
by default (`enabled`) — the same "opt someone out, not in" default
every other governance gate in this codebase uses for its allow-list.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.platform_core import LICENSE_ENABLED, LICENSE_STATUSES, MODULE_KEYS, PlatformModuleLicense


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def is_module_licensed(db: Session, tenant_id: str, module_key: str) -> bool:
    row = db.query(PlatformModuleLicense).filter(
        PlatformModuleLicense.tenant_id == tenant_id, PlatformModuleLicense.module_key == module_key,
    ).first()
    if row is None:
        return True  # unlicensed rows default to enabled — opt-out, not opt-in
    return row.status in (LICENSE_ENABLED, "trial")


def tenant_licenses(db: Session, tenant_id: str) -> dict[str, dict]:
    rows = {r.module_key: r for r in db.query(PlatformModuleLicense).filter(PlatformModuleLicense.tenant_id == tenant_id).all()}
    result = {}
    for key in MODULE_KEYS:
        if key in rows:
            result[key] = _row_to_dict(rows[key])
        else:
            result[key] = {"tenant_id": tenant_id, "module_key": key, "status": LICENSE_ENABLED, "implicit": True}
    return result


def set_license(db: Session, tenant_id: str, module_key: str, *, status: str, granted_by: str, notes: str = "") -> dict:
    if module_key not in MODULE_KEYS:
        raise ValueError(f"module_key must be one of {MODULE_KEYS}")
    if status not in LICENSE_STATUSES:
        raise ValueError(f"status must be one of {LICENSE_STATUSES}")

    row = db.query(PlatformModuleLicense).filter(
        PlatformModuleLicense.tenant_id == tenant_id, PlatformModuleLicense.module_key == module_key,
    ).first()
    if row is None:
        row = PlatformModuleLicense(tenant_id=tenant_id, module_key=module_key)
        db.add(row)
    row.status = status
    row.granted_by = granted_by
    row.granted_at = datetime.now(timezone.utc)
    row.notes = notes
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_licensed_module_keys(db: Session, tenant_id: str) -> list[str]:
    return [key for key in MODULE_KEYS if is_module_licensed(db, tenant_id, key)]
