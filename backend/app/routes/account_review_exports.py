from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.account_review_exports import build_account_review_export
from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["account-review-exports"])


class AccountReviewExportPayload(BaseModel):
    account_review_id: int


def _row(row: models.AccountReviewExport) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "account_review_id": row.account_review_id,
        "export_type": row.export_type,
        "title": row.title,
        "docx_path": row.docx_path,
        "pptx_path": row.pptx_path,
        "pdf_path": row.pdf_path,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _export_or_404(db: Session, tenant_id: str, export_id: int) -> models.AccountReviewExport:
    row = (
        db.query(models.AccountReviewExport)
        .filter(
            models.AccountReviewExport.id == export_id,
            models.AccountReviewExport.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Account review export not found")
    return row


@router.post("/account-review-exports/generate")
def generate_export(
    payload: AccountReviewExportPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = build_account_review_export(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        account_review_id=payload.account_review_id,
    )

    result = _row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="account_review_export_generate",
        resource_type="account_review_export",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.get("/account-review-exports")
def list_exports(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.AccountReviewExport)
        .filter(models.AccountReviewExport.tenant_id == tenant["tenant_id"])
        .order_by(models.AccountReviewExport.id.desc())
        .limit(100)
        .all()
    )
    return {"items": [_row(r) for r in rows]}


@router.get("/account-review-exports/{export_id}")
def get_export(
    export_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = _export_or_404(db, tenant["tenant_id"], export_id)
    return _row(row)


@router.get("/account-review-exports/{export_id}/docx")
def download_docx(
    export_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = _export_or_404(db, tenant["tenant_id"], export_id)
    path = Path(row.docx_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="DOCX file not found")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=path.name)


@router.get("/account-review-exports/{export_id}/pptx")
def download_pptx(
    export_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = _export_or_404(db, tenant["tenant_id"], export_id)
    path = Path(row.pptx_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PPTX file not found")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename=path.name)


@router.get("/account-review-exports/{export_id}/pdf")
def download_pdf(
    export_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = _export_or_404(db, tenant["tenant_id"], export_id)
    path = Path(row.pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
