from __future__ import annotations

import os
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.authz import require_roles

router = APIRouter(tags=["digest-scheduler"])


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


@router.get("/digest-scheduler/status")
def digest_scheduler_status(current_user=Depends(require_roles("admin", "spd_manager"))):
    return JSONResponse({
        "enabled": _truthy(os.getenv("LUMENAI_DIGEST_AUTOMATION_ENABLED", "false")),
        "schedule": os.getenv("LUMENAI_DIGEST_AUTOMATION_CRON", "0 7 * * MON"),
        "delivery_channel": os.getenv("LUMENAI_DIGEST_AUTOMATION_CHANNEL", "download-only"),
        "notes": "This endpoint reports automation readiness. Full scheduled execution can be connected next."
    })
