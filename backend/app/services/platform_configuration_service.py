"""v4.0 — LumenAI OS (Project Genesis), Section 1: Platform Core —
Configuration.

No generic per-tenant or global configuration store existed before
Genesis — only narrow, single-purpose config tables
(`app/models/sso_config.py::TenantSSOConfig`,
`app/models/pilot_config.py::PilotSiteConfig`). `PlatformConfiguration`
is a genuinely new key/value store: `tenant_id == ""` rows are global
defaults, a specific `tenant_id` row overrides the global default for
that tenant only.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.platform_core import PlatformConfiguration


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def get_config(db: Session, tenant_id: str, config_key: str) -> dict | None:
    """A tenant-specific row wins over the global (`tenant_id == ""`) default."""
    row = db.query(PlatformConfiguration).filter(
        PlatformConfiguration.tenant_id == tenant_id, PlatformConfiguration.config_key == config_key,
    ).first()
    if row is None and tenant_id:
        row = db.query(PlatformConfiguration).filter(
            PlatformConfiguration.tenant_id == "", PlatformConfiguration.config_key == config_key,
        ).first()
    return _row_to_dict(row) if row else None


def set_config(db: Session, tenant_id: str, config_key: str, config_value: str, *, updated_by: str) -> dict:
    row = db.query(PlatformConfiguration).filter(
        PlatformConfiguration.tenant_id == tenant_id, PlatformConfiguration.config_key == config_key,
    ).first()
    if row is None:
        row = PlatformConfiguration(tenant_id=tenant_id, config_key=config_key)
        db.add(row)
    row.config_value = config_value
    row.updated_by = updated_by
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_configs(db: Session, tenant_id: str) -> list[dict]:
    global_rows = {r.config_key: r for r in db.query(PlatformConfiguration).filter(PlatformConfiguration.tenant_id == "").all()}
    tenant_rows = {r.config_key: r for r in db.query(PlatformConfiguration).filter(PlatformConfiguration.tenant_id == tenant_id).all()} if tenant_id else {}
    merged = {**global_rows, **tenant_rows}
    return [_row_to_dict(r) for r in merged.values()]
