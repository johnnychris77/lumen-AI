"""Project Canvas — Section 16: Dataset Eligibility REST surface.

Thin HTTP layer over `app.services.dataset_eligibility_service` — every
state returned is computed, never a UI-settable override.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.annotation_database import ROLES_MAY_VIEW
from app.services import dataset_eligibility_service

router = APIRouter(tags=["dataset-eligibility"])


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


@router.get("/dataset-eligibility")
def get_dataset_eligibility(
    request: Request, dataset_version_id: int | None = None, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_VIEW)),
):
    tenant_id = _tenant(current_user, request)
    return dataset_eligibility_service.compute_registry_eligibility(
        db, tenant_id=tenant_id, dataset_version_id=dataset_version_id,
    )
