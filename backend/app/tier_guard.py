"""Tier-based feature gating for P6 intelligence endpoints."""
from __future__ import annotations
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Feature matrix per tier
TIER_FEATURES = {
    "standard":     {"shared_defects", "risk_patterns"},
    "professional": {"shared_defects", "risk_patterns", "recalls", "capa"},
    "enterprise":   {"shared_defects", "risk_patterns", "recalls", "capa", "dashboard", "trends", "manufacturer_portal"},
}


def get_tenant_tier(tenant_id: str, db: Session | None = None) -> str:
    """Resolve tenant's data tier. Defaults to 'standard' if not set."""
    if db is not None:
        try:
            from app.models.tenant_plan import TenantPlan  # type: ignore
            t = db.query(TenantPlan).filter_by(tenant_id=tenant_id).first()
            if t:
                plan = getattr(t, "data_tier", None) or getattr(t, "plan_name", None) or "standard"
                # Normalize plan names to tier names
                plan_lower = plan.lower()
                if plan_lower in TIER_FEATURES:
                    return plan_lower
                if "enterprise" in plan_lower:
                    return "enterprise"
                if "professional" in plan_lower or "pro" in plan_lower:
                    return "professional"
        except Exception:
            pass
    return "standard"


def require_tier(tenant_id: str, feature: str, db: Session | None = None) -> None:
    """Raise 402 if tenant's tier does not include the requested feature.

    When db is provided and no TenantPlan record exists for the tenant,
    enforcement is skipped (permissive default for tenants not yet assigned a plan).
    When db is None, standard tier is assumed and enterprise features are denied.
    """
    if db is not None:
        # With a DB session, only enforce if there is an explicit plan record
        try:
            from app.models.tenant_plan import TenantPlan  # type: ignore
            record = db.query(TenantPlan).filter_by(tenant_id=tenant_id).first()
            if record is None:
                # No plan record → permissive default, allow access
                return
        except Exception:
            return

    tier = get_tenant_tier(tenant_id, db)
    allowed = TIER_FEATURES.get(tier, TIER_FEATURES["standard"])
    if feature not in allowed:
        upgrade_to = next(
            (t for t, feats in TIER_FEATURES.items() if feature in feats), "enterprise"
        )
        raise HTTPException(
            status_code=402,
            detail={
                "error": "tier_required",
                "message": f"Feature '{feature}' requires '{upgrade_to}' tier or above.",
                "current_tier": tier,
                "required_tier": upgrade_to,
                "upgrade_url": "/billing/upgrade",
            }
        )
