from __future__ import annotations

from fastapi import APIRouter, Request

from app.auth import get_current_user
from app.config import get_settings


router = APIRouter(prefix="/production-readiness", tags=["production-readiness"])


@router.get("/config")
def production_config_check(
    request: Request,
):
    get_current_user(request)

    settings = get_settings()
    issues = settings.validate()

    return {
        "status": "ready" if not issues else "needs_attention",
        "app_env": settings.app_env,
        "is_production": settings.is_production,
        "public_base_url": settings.public_base_url,
        "api_prefix": settings.api_prefix,
        "enterprise_audit_enabled": settings.enable_enterprise_audit,
        "enterprise_rbac_enabled": settings.enable_enterprise_rbac,
        "portfolio_briefing_scheduler_seconds": settings.portfolio_briefing_scheduler_seconds,
        "executive_kpi_scheduler_hours": settings.executive_kpi_scheduler_hours,
        "smtp_configured": bool(settings.smtp_host),
        "webhook_default_configured": bool(settings.default_webhook_url),
        "allowed_origins": settings.allowed_origins,
        "issues": issues,
    }
