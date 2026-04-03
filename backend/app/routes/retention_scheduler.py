from __future__ import annotations

import os
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles
from app.services.retention_scheduler_service import retention_scheduler_running

router = APIRouter(tags=["retention-scheduler"])


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


@router.get("/retention-scheduler/status")
def retention_scheduler_status(
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return JSONResponse({
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "enabled": _truthy(os.getenv("LUMENAI_RETENTION_ENFORCEMENT_ENABLED", "false")),
        "schedule": os.getenv("LUMENAI_RETENTION_ENFORCEMENT_CRON", "0 2 * * *"),
        "notify_on_blocked": _truthy(os.getenv("LUMENAI_RETENTION_NOTIFY_ON_BLOCKED", "true")),
        "notify_on_failure": _truthy(os.getenv("LUMENAI_RETENTION_NOTIFY_ON_FAILURE", "true")),
        "notify_channel": os.getenv("LUMENAI_RETENTION_NOTIFY_CHANNEL", "slack"),
        "running": retention_scheduler_running(),
    })
