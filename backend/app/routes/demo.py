"""P14: Demo tenant mode routes."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.deps import get_db

router = APIRouter(prefix="/api/demo", tags=["demo"])

DEMO_TOKEN = "demo-token"


def _is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "0").strip() == "1"


def _require_demo_auth(request: Request) -> None:
    """Allow dev-token OR demo-token when DEMO_MODE=1."""
    if not _is_demo_mode():
        raise HTTPException(status_code=403, detail="Demo mode is not enabled.")
    auth_header = request.headers.get("Authorization", "")
    if auth_header in (f"Bearer {DEMO_TOKEN}", "Bearer dev-token"):
        return
    raise HTTPException(status_code=401, detail="Authentication required.")


@router.get("/reset")
def demo_reset(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Reset demo tenant data. Only works when DEMO_MODE=1."""
    _require_demo_auth(request)

    cleared: dict = {}

    # Clear pilot status rows for demo tenant
    try:
        from app.models.pilot import PilotStatus
        deleted = db.query(PilotStatus).filter(
            PilotStatus.tenant_id.in_(["demo", "default-tenant"])
        ).delete(synchronize_session=False)
        cleared["pilot_status"] = deleted
        db.commit()
    except Exception:
        cleared["pilot_status"] = 0

    # Clear usage counters for demo tenant
    try:
        from app.models.usage import TenantUsageCounter
        deleted = db.query(TenantUsageCounter).filter(
            TenantUsageCounter.tenant_id.in_(["demo", "default-tenant"])
        ).delete(synchronize_session=False)
        cleared["usage_counters"] = deleted
        db.commit()
    except Exception:
        cleared["usage_counters"] = 0

    return {"status": "reset", "cleared": cleared}
