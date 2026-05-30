from typing import Dict, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.capa_service import (
    capa_summary,
    create_capa,
    create_capa_from_audit_signal,
    list_capas,
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
