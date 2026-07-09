"""v3.2 — Project Nexus, Section 7: API Gateway.

The first genuinely versioned API prefix in this codebase — every existing
route is an unversioned flat prefix (`/api/sentinel`, `/api/atlas`,
`/api/integrations`, ...); a handful of unrelated routes use a `/api/v1-2/`
naming scheme that is not real API versioning. `/api/v1/*` here is the
stable, documented, external-facing surface Nexus connectors and other
integrations are meant to call — it composes existing services rather
than re-deriving their logic.

Auth accepts either of two schemes (Section 10): a standard bearer session
token (`require_roles`, for internal/browser use) or a Nexus connector API
key via the `X-Nexus-Api-Key` header (for machine-to-machine connector
calls), matched by SHA-256 hash against `NexusConnectorCredential` — the
same never-store-the-raw-key pattern used at issuance
(`nexus_credential_service.py`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db import models
from app.deps import get_current_user, get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.knowledge import APPROVED, KnowledgeArticle
from app.services import atlas_dashboard_service, nexus_credential_service
from app.services.digital_twin_engine import compute_twin_dashboard

router = APIRouter(tags=["nexus-api-gateway-v1"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")


def _tenant_from_request(request: Request, current_user) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def require_gateway_auth(request: Request, db: Session = Depends(get_db)) -> dict:
    """API-key auth first (machine-to-machine connector calls); falls back
    to standard bearer-token auth for internal/browser callers. Returns a
    dict identifying the resolved tenant and auth mode."""
    api_key = request.headers.get("X-Nexus-Api-Key", "")
    if api_key:
        credential = nexus_credential_service.authenticate_key(db, api_key)
        if credential is None:
            raise HTTPException(status_code=401, detail="Invalid or expired Nexus API key.")
        return {"tenant_id": credential.tenant_id, "auth_mode": "api_key"}

    # get_current_user raises 401 itself on a missing/invalid bearer token —
    # calling it directly (it only needs the raw header + db, both already
    # in scope) reuses the exact same auth check every other route uses,
    # rather than re-deriving it.
    current_user = get_current_user(authorization=request.headers.get("authorization"), db=db)
    role = getattr(current_user, "role", "viewer")
    if role not in _ALL_ROLES:
        raise HTTPException(status_code=403, detail=f"Role '{role}' is not permitted for this resource.")

    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    return {"tenant_id": tenant_id, "auth_mode": "bearer"}


@router.get("/api/v1/instruments")
def get_v1_instruments(
    request: Request, limit: int = Query(50), db: Session = Depends(get_db), auth=Depends(require_gateway_auth),
):
    tenant_id = auth["tenant_id"]
    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id)
        .order_by(models.Inspection.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "api_version": "v1", "tenant_id": tenant_id,
        "instruments": [
            {"inspection_id": r.id, "instrument_type": r.instrument_type, "disposition": r.disposition, "technician": r.technician}
            for r in rows
        ],
    }


@router.get("/api/v1/inspections")
def get_v1_inspections(
    request: Request, limit: int = Query(50), db: Session = Depends(get_db), auth=Depends(require_gateway_auth),
):
    tenant_id = auth["tenant_id"]
    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id)
        .order_by(models.Inspection.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "api_version": "v1", "tenant_id": tenant_id,
        "inspections": [
            {"id": r.id, "instrument_type": r.instrument_type, "disposition": r.disposition, "status": r.status, "coverage_pct": r.coverage_pct}
            for r in rows
        ],
    }


@router.get("/api/v1/digital-twins")
def get_v1_digital_twins(
    request: Request, facility_id: str = Query(""), db: Session = Depends(get_db), auth=Depends(require_gateway_auth),
):
    tenant_id = auth["tenant_id"]
    dashboard = compute_twin_dashboard(tenant_id, facility_id, db)
    return {"api_version": "v1", "tenant_id": tenant_id, "digital_twin": dashboard.model_dump()}


@router.get("/api/v1/knowledge")
def get_v1_knowledge(
    request: Request, limit: int = Query(50), db: Session = Depends(get_db), auth=Depends(require_gateway_auth),
):
    tenant_id = auth["tenant_id"]
    rows = (
        db.query(KnowledgeArticle)
        .filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.approval_status == APPROVED)
        .order_by(KnowledgeArticle.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "api_version": "v1", "tenant_id": tenant_id,
        "knowledge": [{"id": r.id, "title": r.title, "category": r.category, "version": r.version} for r in rows],
    }


@router.get("/api/v1/enterprise")
def get_v1_enterprise(
    request: Request, system_id: str = Query(...), db: Session = Depends(get_db), auth=Depends(require_gateway_auth),
):
    return {"api_version": "v1", "enterprise": atlas_dashboard_service.enterprise_dashboard(db, system_id)}
