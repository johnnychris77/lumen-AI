"""v2.4 — Clinical Memory & Predictive Intelligence API (Project Insight).

- GET /api/clinical-memory                 — Sections 1-5, 7, 9 for one
  instrument (?instrument_identity=barcode:.../udi:...)
- GET /api/clinical-memory/learning-dashboard — Section 8, tenant-wide.

Read-only, informational — mirrors the existing `/api/clinical-readiness/
instrument-condition` convention (`instrument_identity` as a query param,
since it's a colon-delimited compound key, not a clean path segment).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services.clinical_memory_service import get_clinical_memory
from app.services.learning_dashboard_service import learning_dashboard

router = APIRouter(tags=["clinical-memory"])

_ALL_ROLES = ("admin", "spd_manager", "supervisor", "operator", "viewer")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


@router.get("/api/clinical-memory")
def get_clinical_memory_endpoint(
    request: Request,
    instrument_identity: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    memory = get_clinical_memory(db, _tenant(current_user, request), instrument_identity)
    if memory is None:
        raise HTTPException(status_code=404, detail="No inspection history found for this instrument identity.")
    return memory


@router.get("/api/clinical-memory/learning-dashboard")
def get_learning_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return learning_dashboard(db, _tenant(current_user, request))
