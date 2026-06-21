"""P21: Autonomous Healthcare Quality Intelligence Network — API routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.quality_intelligence import (
    PreventiveActionRecommendation,
    QualityInvestigationP21,
)
from app.services.quality_intelligence_service import (
    DISCLAIMER,
    get_dashboard_rollup,
    get_emerging_risk_signals,
    get_executive_summary,
    get_investigations,
    get_recommendations,
    get_risk_graph,
    run_risk_analysis,
)

router = APIRouter(tags=["quality_intelligence"])

_DISCLAIMER = DISCLAIMER


def _tenant(request: Request) -> str:
    return get_request_tenant_id(request)


def _actor(request: Request) -> str:
    return get_request_actor(request) or "unknown"


def _to_dict(obj: Any) -> dict:
    """Serialize a SQLAlchemy model to a plain dict."""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class RunAnalysisRequest(BaseModel):
    facility_id: str = ""


class CreateInvestigationRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    assigned_to: str = ""
    signal_id: int | None = None
    evidence_notes: str = ""


class UpdateInvestigationRequest(BaseModel):
    status: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    evidence_notes: str | None = None
    resolution_notes: str | None = None


class ReviewRecommendationRequest(BaseModel):
    action: str  # accepted/rejected
    reviewed_by: str = ""


# ---------------------------------------------------------------------------
# Emerging risk signals
# ---------------------------------------------------------------------------


@router.get("/api/intelligence/signals")
def list_signals(
    request: Request,
    db: Session = Depends(get_db),
):
    """List emerging risk signals for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    signals = get_emerging_risk_signals(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.signals.list",
        resource_type="emerging_risk_signals",
        resource_id="all",
        details={"count": len(signals)},
    )

    return {
        "status": "success",
        "signals": signals,
        "count": len(signals),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/api/intelligence/emerging-risks")
def list_emerging_risks(
    request: Request,
    db: Session = Depends(get_db),
):
    """Alias for /signals — list emerging risk signals for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    signals = get_emerging_risk_signals(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.emerging_risks.list",
        resource_type="emerging_risk_signals",
        resource_id="all",
        details={"count": len(signals)},
    )

    return {
        "status": "success",
        "signals": signals,
        "count": len(signals),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------


@router.get("/api/intelligence/investigations")
def list_investigations(
    request: Request,
    status: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """List quality investigations for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    items = get_investigations(db, tenant_id, status=status)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.investigations.list",
        resource_type="quality_investigations_p21",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "investigations": items,
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/api/intelligence/investigations")
def create_investigation(
    request: Request,
    body: CreateInvestigationRequest,
    db: Session = Depends(get_db),
):
    """Create a new quality investigation."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    inv = QualityInvestigationP21(
        tenant_id=tenant_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        assigned_to=body.assigned_to,
        signal_id=body.signal_id,
        evidence_notes=body.evidence_notes,
        human_review_required=True,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.investigations.create",
        resource_type="quality_investigations_p21",
        resource_id=str(inv.id),
        details={"title": body.title, "priority": body.priority},
    )

    return {
        "status": "success",
        "investigation": _to_dict(inv),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.patch("/api/intelligence/investigations/{investigation_id}")
def update_investigation(
    investigation_id: int,
    request: Request,
    body: UpdateInvestigationRequest,
    db: Session = Depends(get_db),
):
    """Update investigation status or fields."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    inv = (
        db.query(QualityInvestigationP21)
        .filter(
            QualityInvestigationP21.id == investigation_id,
            QualityInvestigationP21.tenant_id == tenant_id,
        )
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found.")

    if body.status is not None:
        inv.status = body.status
    if body.priority is not None:
        inv.priority = body.priority
    if body.assigned_to is not None:
        inv.assigned_to = body.assigned_to
    if body.evidence_notes is not None:
        inv.evidence_notes = body.evidence_notes
    if body.resolution_notes is not None:
        inv.resolution_notes = body.resolution_notes

    db.commit()
    db.refresh(inv)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.investigations.update",
        resource_type="quality_investigations_p21",
        resource_id=str(investigation_id),
    )

    return {
        "status": "success",
        "investigation": _to_dict(inv),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


@router.get("/api/intelligence/recommendations")
def list_recommendations(
    request: Request,
    db: Session = Depends(get_db),
):
    """List preventive action recommendations for this tenant."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    items = get_recommendations(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.recommendations.list",
        resource_type="preventive_action_recommendations",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "recommendations": items,
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/api/intelligence/recommendations/{recommendation_id}/review")
def review_recommendation(
    recommendation_id: int,
    request: Request,
    body: ReviewRecommendationRequest,
    db: Session = Depends(get_db),
):
    """Accept or reject a preventive action recommendation."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    if body.action not in ("accepted", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="action must be 'accepted' or 'rejected'",
        )

    rec = (
        db.query(PreventiveActionRecommendation)
        .filter(
            PreventiveActionRecommendation.id == recommendation_id,
            PreventiveActionRecommendation.tenant_id == tenant_id,
        )
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    from datetime import datetime, timezone

    rec.status = body.action
    rec.reviewed_by = body.reviewed_by or _actor(request)
    rec.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type=f"intelligence.recommendations.{body.action}",
        resource_type="preventive_action_recommendations",
        resource_id=str(recommendation_id),
        details={"action": body.action, "reviewed_by": rec.reviewed_by},
    )

    return {
        "status": "success",
        "recommendation": _to_dict(rec),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------


@router.get("/api/intelligence/executive-summary")
def executive_summary(
    request: Request,
    role: str = Query(default="quality_director"),
    db: Session = Depends(get_db),
):
    """Executive intelligence summary for role."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    summary = get_executive_summary(db, tenant_id, role=role)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.executive_summary.view",
        resource_type="executive_intelligence_summary",
        resource_id="",
        details={"role": role},
    )

    return {"status": "success", **summary}


# ---------------------------------------------------------------------------
# Run analysis
# ---------------------------------------------------------------------------


@router.post("/api/intelligence/run-analysis")
def trigger_analysis(
    request: Request,
    body: RunAnalysisRequest,
    db: Session = Depends(get_db),
):
    """Trigger an emerging risk analysis run."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    result = run_risk_analysis(db, tenant_id, facility_id=body.facility_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.analysis.run",
        resource_type="risk_analysis",
        resource_id="",
        details={
            "facility_id": body.facility_id,
            "signals_analyzed": result["signals_analyzed"],
            "risks_identified": result["risks_identified"],
        },
    )

    return {"status": "success", **result}


# ---------------------------------------------------------------------------
# Risk graph
# ---------------------------------------------------------------------------


@router.get("/api/intelligence/risk-graph")
def risk_graph(
    request: Request,
    db: Session = Depends(get_db),
):
    """Enterprise risk graph nodes and edges."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    graph = get_risk_graph(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.risk_graph.view",
        resource_type="enterprise_risk_graph",
        resource_id="",
    )

    return {"status": "success", **graph}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/api/intelligence/quality-dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    """Consolidated quality intelligence dashboard KPIs (P21)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    rollup = get_dashboard_rollup(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="intelligence.dashboard.view",
        resource_type="intelligence_dashboard",
        resource_id="",
    )

    return {"status": "success", **rollup}
