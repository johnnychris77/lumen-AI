"""Phase 18 — Real-World Pilot Validation & Clinical Performance Study API.

Serves the pilot performance dashboard, the safety review queue, the go/no-go
readiness gate, and the structured validation report — all computed from real
supervisor reviews (ground-truth labels). Nothing is fabricated.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.model_registry import ModelRegistryEntry
from app.models.supervisor_review import SupervisorReview
from app.services.ml import pilot_validation as pv

router = APIRouter(tags=["pilot-validation"])


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _rows(db: Session, tenant_id: str) -> list[SupervisorReview]:
    return (
        db.query(SupervisorReview)
        .filter(SupervisorReview.tenant_id == tenant_id)
        .order_by(SupervisorReview.id.desc())
        .all()
    )


@router.get("/pilot-validation/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """§6 — pilot performance dashboard (agreement, FP/FN, high-risk detected,
    inconclusive, confidence calibration, zone + family performance)."""
    tenant_id = _tenant(current_user, request)
    return pv.dashboard(_rows(db, tenant_id))


@router.get("/pilot-validation/safety-queue")
def safety_queue(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """§7 — inspections needing a human safety look (false negatives, high-conf
    disagreements, low-conf critical findings)."""
    tenant_id = _tenant(current_user, request)
    queue = pv.safety_review_queue(_rows(db, tenant_id))
    return {"count": len(queue), "queue": queue, "human_review_required": True}


@router.get("/pilot-validation/go-no-go")
def go_no_go(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """§9 — readiness gate from current pilot evidence."""
    tenant_id = _tenant(current_user, request)
    return pv.go_no_go(_rows(db, tenant_id))


@router.get("/pilot-validation/report")
def report(
    request: Request,
    dataset_version: str = "",
    model_version: str = "",
    model_id: str = "",
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """§8 — structured Pilot Validation Report, pinned to a dataset + model
    version. When not supplied, the latest registered model version is used."""
    tenant_id = _tenant(current_user, request)
    if not model_version or not model_id:
        latest = (
            db.query(ModelRegistryEntry)
            .filter(ModelRegistryEntry.tenant_id == tenant_id)
            .order_by(ModelRegistryEntry.id.desc())
            .first()
        )
        if latest is not None:
            model_id = model_id or latest.model_id
            model_version = model_version or latest.model_version
            dataset_version = dataset_version or latest.dataset_version
    return pv.validation_report(
        _rows(db, tenant_id),
        dataset_version=dataset_version or "unversioned",
        model_version=model_version or "none",
        model_id=model_id,
    )
