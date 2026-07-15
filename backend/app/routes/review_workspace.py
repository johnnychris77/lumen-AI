"""Project Canvas — Sections 10 & 14: Blind Secondary Review + Baseline
Comparison REST surface.

Digital Twin timeline (Section 15) is already served by the pre-existing
`GET /dataset-registry/digital-twin/{digital_twin_id}/history` route
(`app.routes.dataset_registry`), extended in this sprint with a `timeline`
field rather than duplicated here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.annotation_database import ROLES_MAY_REVIEW, ROLES_MAY_VIEW
from app.services import annotation_blind_review_service, baseline_comparison_service

router = APIRouter(tags=["review-workspace"])


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


@router.get("/annotations/{annotation_id}/review/secondary/blind-view")
def get_blind_secondary_view(
    annotation_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_REVIEW)),
):
    tenant_id = _tenant(current_user, request)
    view = annotation_blind_review_service.get_blind_secondary_view(
        db, tenant_id=tenant_id, annotation_id=annotation_id, actor=_actor(current_user),
    )
    if view is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return view


@router.get("/dataset-registry/images/{entry_id}/baseline-comparison")
def get_baseline_comparison(
    entry_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_VIEW)),
):
    tenant_id = _tenant(current_user, request)
    result = baseline_comparison_service.compare_to_baselines(db, tenant_id=tenant_id, entry_id=entry_id)
    if not result["found"]:
        raise HTTPException(status_code=404, detail=result["reason"])
    return result
