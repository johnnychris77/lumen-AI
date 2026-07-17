"""Project Foundation (GPAE) — persistence monitoring REST surface.

Complements (does not replace) the existing unauthenticated probes in
``app.main``: ``/health`` liveness, ``/ready`` DB readiness, ``/metrics``.
The deep check exposes internal persistence detail, so it is RBAC-gated.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.services.gpae_monitoring_service import deep_health_check, run_monitoring_sweep

router = APIRouter(tags=["gpae-monitoring"])

_OPS_ROLES = ("admin", "spd_manager")


@router.get("/api/gpae/health/deep")
def gpae_deep_health(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_OPS_ROLES)),
):
    return deep_health_check(db)


@router.post("/api/gpae/monitoring/sweep")
def gpae_monitoring_sweep(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_OPS_ROLES)),
):
    """Run one monitoring pass; raises an audited platform alert per
    failed component (delivery outcome reported truthfully)."""
    return run_monitoring_sweep(db)
