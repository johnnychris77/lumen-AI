from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.subscription_lifecycle import get_active_subscription


PLAN_ENTITLEMENTS = {
    "starter": {
        "evidence_pack_bundle": False,
        "trust_center_bundle": False,
        "finance_bundle_export": False,
        "governance_automation": False,
        "site_benchmarking": False,
        "advanced_analytics": False,
    },
    "growth": {
        "evidence_pack_bundle": True,
        "trust_center_bundle": True,
        "finance_bundle_export": True,
        "governance_automation": False,
        "site_benchmarking": True,
        "advanced_analytics": True,
    },
    "enterprise": {
        "evidence_pack_bundle": True,
        "trust_center_bundle": True,
        "finance_bundle_export": True,
        "governance_automation": True,
        "site_benchmarking": True,
        "advanced_analytics": True,
    },
}


def get_plan_name(db: Session, tenant_id: str) -> str:
    sub = get_active_subscription(db, tenant_id)
    if sub and sub.plan_name:
        return sub.plan_name
    return "starter"


def get_plan_entitlements(plan_name: str) -> dict[str, bool]:
    return PLAN_ENTITLEMENTS.get(plan_name, PLAN_ENTITLEMENTS["starter"]).copy()


def get_entitlement_overrides(db: Session, tenant_id: str) -> dict[str, bool]:
    rows = (
        db.query(models.TenantEntitlement)
        .filter(models.TenantEntitlement.tenant_id == tenant_id)
        .order_by(models.TenantEntitlement.id.desc())
        .all()
    )
    result: dict[str, bool] = {}
    for row in rows:
        if row.feature_key not in result:
            result[row.feature_key] = bool(row.is_enabled)
    return result


def get_feature_flags(db: Session, tenant_id: str) -> dict[str, bool]:
    rows = (
        db.query(models.FeatureFlag)
        .filter(models.FeatureFlag.tenant_id == tenant_id)
        .order_by(models.FeatureFlag.id.desc())
        .all()
    )
    result: dict[str, bool] = {}
    for row in rows:
        if row.flag_key not in result:
            result[row.flag_key] = bool(row.is_enabled)
    return result


def resolve_entitlements(db: Session, tenant_id: str, tenant_name: str) -> dict:
    plan_name = get_plan_name(db, tenant_id)
    base = get_plan_entitlements(plan_name)
    overrides = get_entitlement_overrides(db, tenant_id)
    flags = get_feature_flags(db, tenant_id)

    effective = base.copy()
    effective.update(overrides)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "plan_name": plan_name,
        "base_entitlements": base,
        "overrides": overrides,
        "effective_entitlements": effective,
        "feature_flags": flags,
    }


def is_feature_enabled(db: Session, tenant_id: str, tenant_name: str, feature_key: str) -> dict:
    resolved = resolve_entitlements(db, tenant_id, tenant_name)
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "feature_key": feature_key,
        "plan_name": resolved["plan_name"],
        "enabled": bool(resolved["effective_entitlements"].get(feature_key, False)),
        "feature_flag": bool(resolved["feature_flags"].get(feature_key, False)),
    }
