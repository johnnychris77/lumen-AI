"""v4.0 — LumenAI OS (Project Genesis), Section 9: Platform
Administration.

Composes what already exists into one admin console view rather than
building parallel stores for anything that already has one:

  * **Organizations** — `platform_org_service.organization_tree` (P16's
    existing enterprise hierarchy).
  * **Licenses** — `platform_licensing_service` (new — the module concept
    itself is new this sprint, see `app/models/platform_core.py`).
  * **Modules** — `platform_module_registry_service`.
  * **Roles** — `platform_identity_service.list_known_roles`.
  * **Feature Flags** — reads `app.models.feature_flag.FeatureFlag`
    directly (the same table `app/entitlements.py` and
    `app/routes/entitlements.py::create_flag`/`get_flags` already use —
    no second flag store).
  * **API Keys** — reads `app.models.p25_infrastructure.
    IndustryAPICredential` directly (the existing hash-only credential
    store; `api_key_hash` is never included in the admin view).
  * **Integrations** — `app.services.nexus_registry_service.list_connectors`.
  * **Audit Logs** — `app.models.audit_log.AuditLog`.
  * **Users** — reads `app.models.user.User` directly (id/email/role
    only — `hashed_password` is never included).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.feature_flag import FeatureFlag
from app.models.p25_infrastructure import IndustryAPICredential
from app.models.user import User
from app.services import (
    nexus_registry_service,
    platform_identity_service,
    platform_licensing_service,
    platform_module_registry_service,
    platform_org_service,
    platform_plugin_service,
)


def _row_to_dict(obj, *, exclude: tuple[str, ...] = ()) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def list_users(db: Session, *, limit: int = 100) -> list[dict]:
    rows = db.query(User).order_by(User.id.asc()).limit(limit).all()
    return [_row_to_dict(u, exclude=("hashed_password",)) for u in rows]


def list_feature_flags(db: Session, tenant_id: str = "") -> list[dict]:
    q = db.query(FeatureFlag)
    if tenant_id:
        q = q.filter(FeatureFlag.tenant_id == tenant_id)
    return [_row_to_dict(f) for f in q.order_by(FeatureFlag.id.desc()).all()]


def list_api_keys(db: Session, tenant_id: str = "") -> list[dict]:
    q = db.query(IndustryAPICredential)
    if tenant_id:
        q = q.filter(IndustryAPICredential.tenant_id == tenant_id)
    return [_row_to_dict(k, exclude=("api_key_hash",)) for k in q.order_by(IndustryAPICredential.id.desc()).all()]


def list_integrations(db: Session, tenant_id: str) -> list[dict]:
    return nexus_registry_service.list_connectors(db, tenant_id)


def list_audit_logs(db: Session, tenant_id: str = "", *, limit: int = 100) -> list[dict]:
    q = db.query(AuditLog)
    if tenant_id:
        q = q.filter(AuditLog.tenant_id == tenant_id)
    return [_row_to_dict(a) for a in q.order_by(AuditLog.id.desc()).limit(limit).all()]


def admin_dashboard(db: Session, tenant_id: str) -> dict:
    return {
        "organizations": platform_org_service.organization_tree(db),
        "modules": platform_module_registry_service.list_modules(db),
        "licenses": platform_licensing_service.tenant_licenses(db, tenant_id),
        "roles": platform_identity_service.list_known_roles(),
        "feature_flags": list_feature_flags(db, tenant_id),
        "api_keys": list_api_keys(db, tenant_id),
        "integrations": list_integrations(db, tenant_id),
        "plugins": platform_plugin_service.list_plugins(db),
        "recent_audit_logs": list_audit_logs(db, tenant_id, limit=20),
    }
