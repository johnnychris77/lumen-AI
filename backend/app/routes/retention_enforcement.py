from __future__ import annotations

from io import StringIO, BytesIO
import csv
import json
import zipfile

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.services.retention_enforcement import enforce_retention_once, build_retention_exception_report
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["retention-enforcement"])


def _csv_text(items: list[dict]) -> str:
    output = StringIO()
    if items:
        writer = csv.DictWriter(output, fieldnames=list(items[0].keys()))
        writer.writeheader()
        writer.writerows(items)
    return output.getvalue()


def _xlsx_bytes(report: dict) -> bytes:
    wb = Workbook()

    ws = wb.active
    ws.title = "Summary"
    ws.append(["scope", "count"])
    for item in report.get("summary", []):
        ws.append([item.get("scope", ""), item.get("count", 0)])

    ws2 = wb.create_sheet("Exceptions")
    items = report.get("items", [])
    if items:
        headers = list(items[0].keys())
        ws2.append(headers)
        for item in items:
            ws2.append([item.get(h, "") for h in headers])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.getvalue()


@router.post("/retention-enforcement/run")
def run_retention_enforcement(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = enforce_retention_once(db)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="retention_enforcement_run",
        resource_type="retention_enforcement",
        request=request,
        details=result,
        compliance_flag=True,
    )

    return JSONResponse(result)


@router.get("/retention-enforcement/exceptions")
def retention_exception_report(
    limit: int = Query(default=200, ge=1, le=2000),
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    report = build_retention_exception_report(db, limit=limit)
    filtered_items = [
        item for item in report["items"]
        if item["tenant_id"] == tenant["tenant_id"]
    ]
    filtered_summary = {}
    for item in filtered_items:
        key = f"{item['tenant_id']}::{item['artifact_type']}"
        filtered_summary[key] = filtered_summary.get(key, 0) + 1

    return JSONResponse({
        "generated_at": report["generated_at"],
        "summary": [{"scope": k, "count": v} for k, v in filtered_summary.items()],
        "items": filtered_items,
    })


@router.get("/retention-enforcement/exceptions.csv")
def retention_exception_report_csv(
    limit: int = Query(default=200, ge=1, le=2000),
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    report = build_retention_exception_report(db, limit=limit)
    items = [item for item in report["items"] if item["tenant_id"] == tenant["tenant_id"]]
    return StreamingResponse(
        iter([_csv_text(items)]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=lumenai_{tenant['tenant_id']}_retention_exceptions.csv"},
    )


@router.get("/retention-enforcement/exceptions.bundle.zip")
def retention_exception_report_bundle(
    limit: int = Query(default=200, ge=1, le=2000),
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    report = build_retention_exception_report(db, limit=limit)
    items = [item for item in report["items"] if item["tenant_id"] == tenant["tenant_id"]]
    filtered = {
        "generated_at": report["generated_at"],
        "summary": report["summary"],
        "items": items,
    }

    bio = BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"lumenai_{tenant['tenant_id']}_retention_exceptions.json", json.dumps(filtered, indent=2))
        zf.writestr(f"lumenai_{tenant['tenant_id']}_retention_exceptions.csv", _csv_text(items))
        zf.writestr(f"lumenai_{tenant['tenant_id']}_retention_exceptions.xlsx", _xlsx_bytes(filtered))
    bio.seek(0)

    return StreamingResponse(
        bio,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=lumenai_{tenant['tenant_id']}_retention_exceptions_bundle.zip"},
    )
