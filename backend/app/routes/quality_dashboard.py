"""v1.5 — Quality Intelligence & Continuous Improvement API surface.

- GET  /api/quality/dashboard                — Deliverable 1: KPI dashboard
- GET  /api/quality/finding-trends           — Deliverable 2: finding trend intelligence
- GET  /api/quality/anatomy-risk             — Deliverable 3: anatomy risk dashboard
- GET  /api/quality/instrument-performance   — Deliverable 4: instrument family performance
- GET  /api/quality/technician-quality       — Deliverable 5: technician quality (leadership only)
- GET  /api/quality/supervisor-quality       — Deliverable 6: supervisor quality
- POST /api/quality/root-cause               — Deliverable 7: assign a root cause
- GET  /api/quality/root-cause-trends        — Deliverable 7: root cause trends
- GET  /api/quality/capa-suggestions         — Deliverable 8: CAPA suggestions
- POST /api/quality/capa-suggestions/create  — Deliverable 8: materialize a suggestion into a real CAPA
- GET  /api/quality/benchmark                — Deliverable 9: period-over-period benchmarking
- GET  /api/quality/executive-score          — Deliverable 10: executive quality score
- GET/POST/PATCH /api/quality/improvement-initiatives — Deliverable 11: continuous improvement tracker
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.root_cause import ROOT_CAUSES
from app.services.anatomy_risk_service import anatomy_risk_dashboard
from app.services.capa_suggestion_service import create_capa_from_suggestion, generate_capa_suggestions
from app.services.competency_service import technician_quality_dashboard
from app.services.continuous_improvement_service import (
    create_initiative, list_initiatives, update_initiative,
)
from app.services.finding_trend_service import finding_trends
from app.services.instrument_performance_service import instrument_family_performance
from app.services.quality_dashboard_service import benchmark, dashboard_summary, executive_quality_score
from app.services.root_cause_service import assign_root_cause, root_cause_trends
from app.services.supervisor_quality_service import supervisor_quality_dashboard

router = APIRouter(prefix="/api/quality", tags=["quality-intelligence"])

_LEADERSHIP_ROLES = ("admin", "spd_manager")
_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


@router.get("/dashboard")
def get_dashboard(
    request: Request,
    period: str = "all_time",
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return dashboard_summary(db, _tenant(current_user, request), period)


@router.get("/finding-trends")
def get_finding_trends(
    request: Request,
    granularity: str = "monthly",
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return finding_trends(db, _tenant(current_user, request), granularity)


@router.get("/anatomy-risk")
def get_anatomy_risk(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return anatomy_risk_dashboard(db, _tenant(current_user, request))


@router.get("/instrument-performance")
def get_instrument_performance(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return instrument_family_performance(db, _tenant(current_user, request))


@router.get("/technician-quality")
def get_technician_quality(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    """Only visible to authorized leadership (admin/spd_manager)."""
    return technician_quality_dashboard(db, _tenant(current_user, request))


@router.get("/supervisor-quality")
def get_supervisor_quality(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return supervisor_quality_dashboard(db, _tenant(current_user, request))


class RootCauseIn(BaseModel):
    inspection_id: int
    finding_type: str = Field(..., max_length=40)
    root_cause: str = Field(..., max_length=40)


@router.post("/root-cause", status_code=201)
def post_root_cause(
    body: RootCauseIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    if body.root_cause not in ROOT_CAUSES:
        raise HTTPException(status_code=422, detail=f"root_cause must be one of {ROOT_CAUSES}")
    row = assign_root_cause(
        db, tenant_id=_tenant(current_user, request), inspection_id=body.inspection_id,
        finding_type=body.finding_type, root_cause=body.root_cause, assigned_by=_actor(current_user),
    )
    db.commit()
    db.refresh(row)
    return {"id": row.id, "root_cause": row.root_cause, "finding_type": row.finding_type}


@router.get("/root-cause-trends")
def get_root_cause_trends(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return root_cause_trends(db, _tenant(current_user, request))


@router.get("/capa-suggestions")
def get_capa_suggestions(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return {"suggestions": generate_capa_suggestions(db, _tenant(current_user, request))}


class CapaSuggestionIn(BaseModel):
    trigger: str
    occurrences: int
    recommendation: str
    suggested_title: str
    corrective_action: str
    preventive_action: str


@router.post("/capa-suggestions/create", status_code=201)
def post_capa_from_suggestion(
    body: CapaSuggestionIn,
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    capa = create_capa_from_suggestion(body.model_dump(), owner=_actor(current_user))
    return capa


@router.get("/benchmark")
def get_benchmark(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return benchmark(db, _tenant(current_user, request))


@router.get("/executive-score")
def get_executive_score(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return executive_quality_score(db, _tenant(current_user, request))


class InitiativeIn(BaseModel):
    initiative: str = Field(..., max_length=500)
    owner: str = Field("", max_length=255)
    target_date: date | None = None
    expected_impact: str = Field("", max_length=2000)


class InitiativeUpdateIn(BaseModel):
    status: str | None = Field(None, max_length=20)
    actual_impact: str | None = Field(None, max_length=2000)


@router.get("/improvement-initiatives")
def get_initiatives(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    rows = list_initiatives(db, _tenant(current_user, request))
    return {
        "initiatives": [
            {
                "id": r.id, "initiative": r.initiative, "owner": r.owner,
                "target_date": r.target_date.isoformat() if r.target_date else None,
                "status": r.status, "expected_impact": r.expected_impact,
                "actual_impact": r.actual_impact,
            }
            for r in rows
        ],
    }


@router.post("/improvement-initiatives", status_code=201)
def post_initiative(
    body: InitiativeIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    row = create_initiative(
        db, tenant_id=_tenant(current_user, request), initiative=body.initiative,
        owner=body.owner, target_date=body.target_date, expected_impact=body.expected_impact,
    )
    db.commit()
    db.refresh(row)
    return {"id": row.id, "initiative": row.initiative, "status": row.status}


@router.patch("/improvement-initiatives/{initiative_id}")
def patch_initiative(
    initiative_id: int,
    body: InitiativeUpdateIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    row = update_initiative(
        db, initiative_id=initiative_id, tenant_id=_tenant(current_user, request),
        status=body.status, actual_impact=body.actual_impact,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Initiative not found.")
    db.commit()
    return {"id": row.id, "status": row.status, "actual_impact": row.actual_impact}
