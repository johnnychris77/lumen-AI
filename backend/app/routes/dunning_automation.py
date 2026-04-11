from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.audit import log_audit_event
from app.services.dunning_automation import (
    run_dunning_automation_once,
    run_recovery_action_once,
    dunning_scheduler_running,
)
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["dunning-automation"])


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


@router.get("/dunning-automation/status")
def dunning_automation_status(
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return JSONResponse({
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "enabled": _truthy(os.getenv("LUMENAI_DUNNING_AUTOMATION_ENABLED", "false")),
        "cron": os.getenv("LUMENAI_DUNNING_CHECK_CRON", "0 */6 * * *"),
        "grace_days": int(os.getenv("LUMENAI_DUNNING_GRACE_DAYS", "7") or 7),
        "recovery_actions_enabled": _truthy(os.getenv("LUMENAI_DUNNING_RECOVERY_ACTIONS_ENABLED", "true")),
        "scheduler_running": dunning_scheduler_running(),
    })


@router.post("/dunning-automation/run")
def run_dunning_automation(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = run_dunning_automation_once()
    return JSONResponse(result)


@router.post("/dunning-automation/recover")
def run_dunning_recovery(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = run_recovery_action_once(tenant["tenant_id"])
    return JSONResponse(result)
