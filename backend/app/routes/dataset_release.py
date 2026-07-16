"""Project Canvas — Sections 17 & 18: Dataset Release Builder + Export
Preview REST surface.

Split assignment and version freezing are NOT duplicated here — the
frontend calls the existing, already-routed
`POST /dataset-registry/versions/{id}/build-training-dataset` and
`POST /dataset-registry/versions/{id}/freeze` once it has reviewed this
preview.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.annotation_database import ROLES_MAY_EXPORT
from app.authz import require_roles
from app.services import dataset_export_preview_service, dataset_release_service
from app.services import annotation_export_service

router = APIRouter(tags=["dataset-release"])

_RELEASE_ROLES = tuple(ROLES_MAY_EXPORT)


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


@router.get("/dataset-release/preview")
def get_release_preview(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_RELEASE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return dataset_release_service.build_release_preview(db, tenant_id=tenant_id)


@router.get("/dataset-release/export-preview")
def get_export_preview(
    request: Request, export_format: str, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_RELEASE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    if export_format not in annotation_export_service.EXPORT_FORMATS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown export format '{export_format}'. Known: {annotation_export_service.EXPORT_FORMATS}",
        )
    return dataset_export_preview_service.preview_export(db, tenant_id=tenant_id, export_format=export_format)
