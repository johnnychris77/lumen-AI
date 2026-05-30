import csv
import io
from typing import Dict, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from fastapi.responses import Response

from app.services.capa_service import (
    capa_summary,
    build_capa_powerbi_rows,
    capa_escalation_summary,
    capa_governance_scorecard,
    create_capa,
    create_capa_from_audit_signal,
    list_capas,
    get_capa,
    update_capa,
)


router = APIRouter()


class CapaCreateRequest(BaseModel):
    title: str
    source: Optional[str] = "manual"
    description: Optional[str] = None
    risk_level: Optional[str] = "medium"
    owner: Optional[str] = None
    due_date: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    status: Optional[str] = "open"


class CapaUpdateRequest(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    risk_level: Optional[str] = None
    description: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None


class AuditSignalCapaRequest(BaseModel):
    event_type: Optional[str] = "Audit Signal"
    event_summary: Optional[str] = None
    description: Optional[str] = None
    risk_level: Optional[str] = "medium"
    owner: Optional[str] = None
    due_date: Optional[str] = None
    metadata: Optional[Dict] = None


@router.get("/capa/health")
def capa_health():
    return {
        "status": "healthy",
        "module": "capa_workflow",
        "version": "1.0.0",
        "capabilities": {
            "create_capa": "ready",
            "list_capas": "ready",
            "audit_signal_to_capa": "ready",
            "governance_summary": "ready",
        },
        "summary": capa_summary(),
    }


@router.get("/capa")
def get_capas(limit: int = Query(default=50, ge=1, le=500)):
    items = list_capas(limit=limit)

    return {
        "status": "success",
        "module": "capa_workflow",
        "limit": limit,
        "total_returned": len(items),
        "summary": capa_summary(),
        "items": items,
    }


@router.post("/capa")
def post_capa(payload: CapaCreateRequest):
    capa = create_capa(**payload.model_dump())

    return {
        "status": "success",
        "module": "capa_workflow",
        "message": "CAPA created successfully.",
        "capa": capa,
    }


@router.post("/capa/from-audit-signal")
def post_capa_from_audit_signal(payload: AuditSignalCapaRequest):
    capa = create_capa_from_audit_signal(payload.model_dump())

    return {
        "status": "success",
        "module": "capa_workflow",
        "message": "CAPA created from audit signal.",
        "capa": capa,
    }




@router.get("/capa/escalation-summary")
def get_capa_escalation_summary(days_until_due: int = Query(default=7, ge=0, le=90)):
    return capa_escalation_summary(days_until_due=days_until_due)



@router.get("/capa/powerbi-csv")
def get_capa_powerbi_csv(limit: int = Query(default=500, ge=1, le=5000)):
    rows = build_capa_powerbi_rows(limit=limit)

    fieldnames = [
        "capa_id",
        "title",
        "source",
        "risk_level",
        "status",
        "owner",
        "due_date",
        "created_at",
        "updated_at",
        "days_to_due",
        "is_overdue",
        "is_high_risk",
        "is_open",
        "corrective_action",
        "preventive_action",
        "description",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    csv_content = output.getvalue()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-capa-powerbi.csv"
        },
    )



@router.get("/capa/governance-scorecard")
def get_capa_governance_scorecard(days_until_due: int = Query(default=7, ge=0, le=90)):
    return capa_governance_scorecard(days_until_due=days_until_due)

@router.get("/capa/{capa_id}")
def get_capa_by_id(capa_id: str):
    capa = get_capa(capa_id)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return {
        "status": "success",
        "module": "capa_workflow",
        "capa": capa,
    }


@router.patch("/capa/{capa_id}")
def patch_capa(capa_id: str, payload: CapaUpdateRequest):
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No update fields provided")

    capa = update_capa(capa_id=capa_id, **updates)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return {
        "status": "success",
        "module": "capa_workflow",
        "message": "CAPA updated successfully.",
        "capa": capa,
    }
