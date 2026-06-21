"""P9: Autonomous Inspection Copilot — API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.schemas.copilot import (
    ResolveEscalationRequest,
    StartSessionRequest,
    StepResponseRequest,
)
from app.services.copilot_engine import (
    complete_session,
    compute_copilot_dashboard,
    get_active_sessions,
    get_escalations,
    get_protocols,
    get_session,
    resolve_escalation,
    respond_to_step,
    start_inspection_session,
)
from app.tier_guard import require_tier

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


@router.post("/sessions")
def create_session(
    request: Request,
    body: StartSessionRequest,
    db: Session = Depends(get_db),
):
    """Start a new copilot-guided inspection session."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_basic", db)
    result = start_inspection_session(
        tenant_id=tenant_id,
        facility_id=body.facility_id,
        technician_id=body.technician_id,
        instrument_name=body.instrument_name,
        instrument_id=body.instrument_id,
        copilot_mode=body.copilot_mode,
        db=db,
    )
    return result.model_dump()


@router.get("/sessions")
def list_sessions(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """List all active sessions for this tenant."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_basic", db)
    results = get_active_sessions(tenant_id, facility_id, db)
    return {"status": "success", "sessions": [r.model_dump() for r in results]}


@router.get("/sessions/{session_id}")
def get_session_detail(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get full session detail including steps and recommendations."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_basic", db)
    result = get_session(session_id, tenant_id, db)
    return result.model_dump()


@router.post("/sessions/{session_id}/steps/{step_id}/respond")
def respond_step(
    session_id: int,
    step_id: int,
    request: Request,
    body: StepResponseRequest,
    db: Session = Depends(get_db),
):
    """Record a technician's response to an inspection step."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_basic", db)
    result = respond_to_step(
        session_id=session_id,
        step_id=step_id,
        technician_response=body.technician_response,
        finding_category=body.finding_category,
        notes=body.notes,
        tenant_id=tenant_id,
        db=db,
    )
    return result.model_dump()


@router.post("/sessions/{session_id}/complete")
def complete_session_route(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Manually mark a session as completed."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_basic", db)
    result = complete_session(session_id, tenant_id, db)
    return result.model_dump()


@router.get("/escalations")
def list_escalations(
    request: Request,
    db: Session = Depends(get_db),
):
    """List all open escalation events for this tenant."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_escalations", db)
    results = get_escalations(tenant_id, db)
    return {"status": "success", "escalations": [r.model_dump() for r in results]}


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation_route(
    escalation_id: int,
    request: Request,
    body: ResolveEscalationRequest,
    db: Session = Depends(get_db),
):
    """Resolve an open escalation event."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_escalations", db)
    result = resolve_escalation(escalation_id, body.resolved_by, body.notes, tenant_id, db)
    return result.model_dump()


@router.get("/protocols")
def list_protocols(
    request: Request,
    db: Session = Depends(get_db),
):
    """List all inspection protocols (DB + built-in templates)."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_basic", db)
    results = get_protocols(tenant_id, db)
    return {"status": "success", "protocols": [r.model_dump() for r in results]}


@router.get("/dashboard")
def copilot_dashboard(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """Copilot dashboard with aggregated KPIs."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_dashboard", db)
    result = compute_copilot_dashboard(tenant_id, facility_id, db)
    return result.model_dump()


@router.post("/sessions/{session_id}/pdf")
def session_pdf(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Generate a PDF report for a completed inspection session."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    require_tier(tenant_id, "copilot_basic", db)
    session_result = get_session(session_id, tenant_id, db)
    from app.services.report_pdf import build_copilot_session_pdf
    pdf_bytes = build_copilot_session_pdf(session_result.model_dump())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=copilot-session-{session_id}.pdf"},
    )
