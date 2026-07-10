"""v4.0 — LumenAI OS (Project Genesis), Section 1: Platform Core —
Organization/Tenant Management.

Reads P16's existing enterprise hierarchy (`app/models/enterprise_hierarchy.py`
— `HealthSystem` → `EnterpriseMarket` → `EnterpriseRegion` →
`EnterpriseFacility` → `EnterpriseDepartment`) directly. Genesis adds no
second organization hierarchy — there was already no need for one
(confirmed: no separate "Organization" model exists in this codebase
beyond this hierarchy plus the `tenant_id` string every model carries).
This module is a read-only composition/tree-assembly layer only.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enterprise_hierarchy import (
    EnterpriseDepartment,
    EnterpriseFacility,
    EnterpriseMarket,
    EnterpriseRegion,
    HealthSystem,
)


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def organization_tree(db: Session) -> dict:
    systems = db.query(HealthSystem).all()
    markets = db.query(EnterpriseMarket).all()
    regions = db.query(EnterpriseRegion).all()
    facilities = db.query(EnterpriseFacility).all()
    departments = db.query(EnterpriseDepartment).all()

    return {
        "health_systems": [_row_to_dict(s) for s in systems],
        "markets": [_row_to_dict(m) for m in markets],
        "regions": [_row_to_dict(r) for r in regions],
        "facilities": [_row_to_dict(f) for f in facilities],
        "departments": [_row_to_dict(d) for d in departments],
        "counts": {
            "health_systems": len(systems), "markets": len(markets), "regions": len(regions),
            "facilities": len(facilities), "departments": len(departments),
        },
    }


def facility_for_tenant(db: Session, tenant_id: str) -> dict | None:
    facility = db.query(EnterpriseFacility).filter(EnterpriseFacility.tenant_id == tenant_id).first()
    return _row_to_dict(facility) if facility else None


def list_facilities(db: Session, *, market_id: str = "", region_id: str = "") -> list[dict]:
    q = db.query(EnterpriseFacility)
    if market_id:
        q = q.filter(EnterpriseFacility.market_id == market_id)
    if region_id:
        q = q.filter(EnterpriseFacility.region_id == region_id)
    return [_row_to_dict(f) for f in q.all()]
