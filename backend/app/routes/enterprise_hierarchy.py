"""P16 Phase 1-3: Enterprise hierarchy, site onboarding, baseline distribution."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]$")
_ALLOWED_FACILITY_TYPES = {"hospital", "asc", "clinic", "long_term_care", "specialty_center"}
_ALLOWED_CONTRACT_TIERS = {"pilot", "standard", "enterprise", "enterprise_plus"}
_ALLOWED_DEPT_TYPES = {"spd", "or", "icu", "cssd", "endoscopy", "cath_lab", "other"}
_WORKFLOW_STEPS = {
    "site": ["initiated", "documents_collected", "tenant_provisioned", "users_invited",
             "baseline_assigned", "training_complete", "go_live", "completed"],
    "user": ["initiated", "account_created", "role_assigned", "training_assigned",
             "training_complete", "activated", "completed"],
    "vendor": ["initiated", "nda_executed", "portal_access_granted",
               "baseline_submitted", "baseline_approved", "completed"],
    "baseline": ["initiated", "draft_created", "review_requested",
                 "approved", "published", "completed"],
}


def _new_id() -> str:
    return str(uuid.uuid4())


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or "unknown"


def _role(current_user) -> str:
    return getattr(current_user, "role", "admin")


# ---------------------------------------------------------------------------
# PHASE 1: Enterprise Hierarchy — HealthSystem
# ---------------------------------------------------------------------------

class HealthSystemCreate(BaseModel):
    system_id: str = Field(..., min_length=3, max_length=100)
    system_name: str = Field(..., min_length=2, max_length=255)
    hq_region: str = Field(default="north_america", max_length=100)
    contract_tier: str = Field(default="enterprise")
    admin_email: str
    notes: str = Field(default="", max_length=2000)

    @field_validator("system_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("system_id must be lowercase alphanumeric with hyphens")
        return v

    @field_validator("contract_tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v not in _ALLOWED_CONTRACT_TIERS:
            raise ValueError(f"contract_tier must be one of {sorted(_ALLOWED_CONTRACT_TIERS)}")
        return v


@router.post("/systems", status_code=201)
def create_health_system(
    payload: HealthSystemCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    existing = db.query(models.HealthSystem).filter(
        models.HealthSystem.system_id == payload.system_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Health system '{payload.system_id}' already exists")

    hs = models.HealthSystem(
        system_id=payload.system_id,
        system_name=payload.system_name,
        hq_region=payload.hq_region,
        contract_tier=payload.contract_tier,
        admin_email=str(payload.admin_email),
        notes=payload.notes,
    )
    db.add(hs)
    db.commit()
    db.refresh(hs)

    log_audit_event(db, tenant_id=payload.system_id, tenant_name=payload.system_name,
                    actor_email=_actor(current_user), actor_role=_role(current_user),
                    action_type="health_system_created", resource_type="enterprise_hierarchy",
                    compliance_flag=True)

    return {"id": hs.id, "system_id": hs.system_id, "system_name": hs.system_name,
            "contract_tier": hs.contract_tier, "status": "created"}


@router.get("/systems")
def list_health_systems(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    rows = db.query(models.HealthSystem).filter(models.HealthSystem.is_active == True).all()  # noqa: E712
    return [{"system_id": r.system_id, "system_name": r.system_name,
             "hq_region": r.hq_region, "contract_tier": r.contract_tier,
             "admin_email": r.admin_email, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/systems/{system_id}")
def get_health_system(
    system_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    hs = db.query(models.HealthSystem).filter(models.HealthSystem.system_id == system_id).first()
    if not hs:
        raise HTTPException(status_code=404, detail="Health system not found")

    markets = db.query(models.EnterpriseMarket).filter(
        models.EnterpriseMarket.system_id == system_id,
        models.EnterpriseMarket.is_active == True,  # noqa: E712
    ).all()
    facilities = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.system_id == system_id,
        models.EnterpriseFacility.is_active == True,  # noqa: E712
    ).all()

    return {
        "system_id": hs.system_id, "system_name": hs.system_name,
        "hq_region": hs.hq_region, "contract_tier": hs.contract_tier,
        "admin_email": hs.admin_email, "is_active": hs.is_active,
        "market_count": len(markets), "facility_count": len(facilities),
        "created_at": hs.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------------

class MarketCreate(BaseModel):
    market_id: str = Field(..., min_length=3, max_length=100)
    market_name: str = Field(..., min_length=2, max_length=255)
    system_id: str
    region: str = Field(default="north_america")
    director_email: str = Field(default="")

    @field_validator("market_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("market_id must be lowercase alphanumeric with hyphens")
        return v


@router.post("/markets", status_code=201)
def create_market(
    payload: MarketCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    hs = db.query(models.HealthSystem).filter(models.HealthSystem.system_id == payload.system_id).first()
    if not hs:
        raise HTTPException(status_code=404, detail=f"Health system '{payload.system_id}' not found")

    if db.query(models.EnterpriseMarket).filter(models.EnterpriseMarket.market_id == payload.market_id).first():
        raise HTTPException(status_code=409, detail="Market already exists")

    m = models.EnterpriseMarket(
        market_id=payload.market_id, market_name=payload.market_name,
        system_id=payload.system_id, region=payload.region,
        director_email=payload.director_email,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id, "market_id": m.market_id, "market_name": m.market_name,
            "system_id": m.system_id, "status": "created"}


@router.get("/systems/{system_id}/markets")
def list_markets(
    system_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    rows = db.query(models.EnterpriseMarket).filter(
        models.EnterpriseMarket.system_id == system_id,
        models.EnterpriseMarket.is_active == True,  # noqa: E712
    ).all()
    return [{"market_id": r.market_id, "market_name": r.market_name,
             "region": r.region, "director_email": r.director_email} for r in rows]


# ---------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------

class RegionCreate(BaseModel):
    region_id: str = Field(..., min_length=3, max_length=100)
    region_name: str = Field(..., min_length=2, max_length=255)
    market_id: str
    system_id: str

    @field_validator("region_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("region_id must be lowercase alphanumeric with hyphens")
        return v


@router.post("/regions", status_code=201)
def create_region(
    payload: RegionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    if not db.query(models.EnterpriseMarket).filter(models.EnterpriseMarket.market_id == payload.market_id).first():
        raise HTTPException(status_code=404, detail=f"Market '{payload.market_id}' not found")

    if db.query(models.EnterpriseRegion).filter(models.EnterpriseRegion.region_id == payload.region_id).first():
        raise HTTPException(status_code=409, detail="Region already exists")

    r = models.EnterpriseRegion(
        region_id=payload.region_id, region_name=payload.region_name,
        market_id=payload.market_id, system_id=payload.system_id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "region_id": r.region_id, "region_name": r.region_name,
            "market_id": r.market_id, "status": "created"}


# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------

class FacilityCreate(BaseModel):
    facility_id: str = Field(..., min_length=3, max_length=100)
    facility_name: str = Field(..., min_length=2, max_length=255)
    region_id: str
    market_id: str
    system_id: str
    tenant_id: str
    facility_type: str = Field(default="hospital")
    bed_count: int = Field(default=0, ge=0)

    @field_validator("facility_id", "tenant_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("ID must be lowercase alphanumeric with hyphens")
        return v

    @field_validator("facility_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in _ALLOWED_FACILITY_TYPES:
            raise ValueError(f"facility_type must be one of {sorted(_ALLOWED_FACILITY_TYPES)}")
        return v


@router.post("/facilities", status_code=201)
def create_facility(
    payload: FacilityCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    if db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.facility_id == payload.facility_id
    ).first():
        raise HTTPException(status_code=409, detail="Facility already exists")

    f = models.EnterpriseFacility(
        facility_id=payload.facility_id, facility_name=payload.facility_name,
        region_id=payload.region_id, market_id=payload.market_id,
        system_id=payload.system_id, tenant_id=payload.tenant_id,
        facility_type=payload.facility_type, bed_count=payload.bed_count,
    )
    db.add(f)
    db.commit()
    db.refresh(f)

    log_audit_event(db, tenant_id=payload.system_id, tenant_name=payload.facility_name,
                    actor_email=_actor(current_user), actor_role=_role(current_user),
                    action_type="facility_created", resource_type="enterprise_hierarchy")

    return {"id": f.id, "facility_id": f.facility_id, "facility_name": f.facility_name,
            "system_id": f.system_id, "onboarding_status": f.onboarding_status, "status": "created"}


@router.get("/systems/{system_id}/facilities")
def list_facilities(
    system_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    rows = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.system_id == system_id,
        models.EnterpriseFacility.is_active == True,  # noqa: E712
    ).all()
    return [{"facility_id": r.facility_id, "facility_name": r.facility_name,
             "region_id": r.region_id, "market_id": r.market_id,
             "facility_type": r.facility_type, "bed_count": r.bed_count,
             "onboarding_status": r.onboarding_status,
             "go_live_date": r.go_live_date.isoformat() if r.go_live_date else None} for r in rows]


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

class DepartmentCreate(BaseModel):
    department_id: str = Field(..., min_length=3, max_length=100)
    department_name: str = Field(..., min_length=2, max_length=255)
    facility_id: str
    department_type: str = Field(default="spd")
    manager_email: str = Field(default="")

    @field_validator("department_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("department_id must be lowercase alphanumeric with hyphens")
        return v

    @field_validator("department_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in _ALLOWED_DEPT_TYPES:
            raise ValueError(f"department_type must be one of {sorted(_ALLOWED_DEPT_TYPES)}")
        return v


@router.post("/departments", status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    if not db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.facility_id == payload.facility_id
    ).first():
        raise HTTPException(status_code=404, detail=f"Facility '{payload.facility_id}' not found")

    if db.query(models.EnterpriseDepartment).filter(
        models.EnterpriseDepartment.department_id == payload.department_id
    ).first():
        raise HTTPException(status_code=409, detail="Department already exists")

    d = models.EnterpriseDepartment(
        department_id=payload.department_id, department_name=payload.department_name,
        facility_id=payload.facility_id, department_type=payload.department_type,
        manager_email=payload.manager_email,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "department_id": d.department_id, "facility_id": d.facility_id,
            "department_type": d.department_type, "status": "created"}


# ---------------------------------------------------------------------------
# PHASE 2: Onboarding Workflows
# ---------------------------------------------------------------------------

class OnboardingStart(BaseModel):
    workflow_type: str = Field(..., description="site | user | vendor | baseline")
    target_id: str = Field(..., min_length=1, max_length=255)
    system_id: str = Field(..., min_length=1)
    facility_id: str = Field(default="")
    assigned_to: str = Field(default="")
    notes: str = Field(default="")

    @field_validator("workflow_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in _WORKFLOW_STEPS:
            raise ValueError(f"workflow_type must be one of {list(_WORKFLOW_STEPS.keys())}")
        return v


@router.post("/onboarding", status_code=201)
def start_onboarding(
    payload: OnboardingStart,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    wf_id = f"wf-{payload.workflow_type}-{uuid.uuid4().hex[:8]}"
    steps = _WORKFLOW_STEPS[payload.workflow_type]
    wf = models.OnboardingWorkflow(
        workflow_id=wf_id,
        workflow_type=payload.workflow_type,
        target_id=payload.target_id,
        system_id=payload.system_id,
        facility_id=payload.facility_id,
        status="in_progress",
        current_step=steps[0],
        steps_completed=json.dumps([]),
        assigned_to=payload.assigned_to,
        notes=payload.notes,
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)

    log_audit_event(db, tenant_id=payload.system_id, tenant_name=payload.target_id,
                    actor_email=_actor(current_user), actor_role=_role(current_user),
                    action_type=f"onboarding_{payload.workflow_type}_started",
                    resource_type="onboarding_workflow")

    return {"workflow_id": wf_id, "workflow_type": payload.workflow_type,
            "target_id": payload.target_id, "current_step": wf.current_step,
            "total_steps": len(steps), "status": "in_progress"}


class OnboardingAdvance(BaseModel):
    completed_step: str
    notes: str = Field(default="")


@router.patch("/onboarding/{workflow_id}/advance")
def advance_onboarding(
    workflow_id: str,
    payload: OnboardingAdvance,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    wf = db.query(models.OnboardingWorkflow).filter(
        models.OnboardingWorkflow.workflow_id == workflow_id
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.status == "completed":
        raise HTTPException(status_code=409, detail="Workflow already completed")

    steps = _WORKFLOW_STEPS[wf.workflow_type]
    completed = json.loads(wf.steps_completed)
    if payload.completed_step not in steps:
        raise HTTPException(status_code=422, detail=f"Invalid step '{payload.completed_step}' for workflow type '{wf.workflow_type}'")

    if payload.completed_step not in completed:
        completed.append(payload.completed_step)
    wf.steps_completed = json.dumps(completed)

    remaining = [s for s in steps if s not in completed]
    if remaining:
        wf.current_step = remaining[0]
    else:
        wf.current_step = "completed"
        wf.status = "completed"
        wf.completed_at = datetime.now(timezone.utc)

    if payload.notes:
        wf.notes = (wf.notes + f"\n[{payload.completed_step}] {payload.notes}").strip()

    db.commit()
    db.refresh(wf)

    return {"workflow_id": workflow_id, "current_step": wf.current_step,
            "steps_completed": completed, "status": wf.status,
            "remaining_steps": remaining if remaining else []}


@router.get("/onboarding/{workflow_id}")
def get_onboarding(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    wf = db.query(models.OnboardingWorkflow).filter(
        models.OnboardingWorkflow.workflow_id == workflow_id
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps = _WORKFLOW_STEPS[wf.workflow_type]
    completed = json.loads(wf.steps_completed)
    return {"workflow_id": wf.workflow_id, "workflow_type": wf.workflow_type,
            "target_id": wf.target_id, "system_id": wf.system_id,
            "status": wf.status, "current_step": wf.current_step,
            "steps_completed": completed,
            "steps_remaining": [s for s in steps if s not in completed],
            "progress_pct": round(len(completed) / len(steps) * 100),
            "assigned_to": wf.assigned_to, "notes": wf.notes,
            "created_at": wf.created_at.isoformat(),
            "completed_at": wf.completed_at.isoformat() if wf.completed_at else None}


@router.get("/systems/{system_id}/onboarding")
def list_onboarding(
    system_id: str,
    workflow_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    q = db.query(models.OnboardingWorkflow).filter(
        models.OnboardingWorkflow.system_id == system_id
    )
    if workflow_type:
        q = q.filter(models.OnboardingWorkflow.workflow_type == workflow_type)
    if status:
        q = q.filter(models.OnboardingWorkflow.status == status)
    rows = q.order_by(models.OnboardingWorkflow.created_at.desc()).limit(200).all()
    return [{"workflow_id": r.workflow_id, "workflow_type": r.workflow_type,
             "target_id": r.target_id, "status": r.status,
             "current_step": r.current_step, "assigned_to": r.assigned_to,
             "created_at": r.created_at.isoformat()} for r in rows]


# ---------------------------------------------------------------------------
# PHASE 3: Enterprise Baseline Distribution
# ---------------------------------------------------------------------------

class BaselineCreate(BaseModel):
    baseline_id: str = Field(..., min_length=3, max_length=100)
    system_id: str
    instrument_type: str = Field(..., min_length=1)
    material_type: str = Field(..., min_length=1)
    acceptance_criteria: dict = Field(default_factory=dict)
    created_by: str = Field(..., min_length=1)
    change_summary: str = Field(default="Initial version")
    version: str = Field(default="1.0.0")

    @field_validator("baseline_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("baseline_id must be lowercase alphanumeric with hyphens")
        return v


@router.post("/baselines", status_code=201)
def create_enterprise_baseline(
    payload: BaselineCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    # Check for existing active baseline with same id + version
    existing = db.query(models.EnterpriseBaseline).filter(
        models.EnterpriseBaseline.baseline_id == payload.baseline_id,
        models.EnterpriseBaseline.version == payload.version,
        models.EnterpriseBaseline.is_active == True,  # noqa: E712
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Baseline '{payload.baseline_id}' v{payload.version} already exists")

    b = models.EnterpriseBaseline(
        baseline_id=payload.baseline_id,
        version=payload.version,
        system_id=payload.system_id,
        instrument_type=payload.instrument_type,
        material_type=payload.material_type,
        acceptance_criteria=json.dumps(payload.acceptance_criteria),
        created_by=payload.created_by,
        change_summary=payload.change_summary,
        approval_status="draft",
        published_to=json.dumps([]),
    )
    db.add(b)
    db.commit()
    db.refresh(b)

    log_audit_event(db, tenant_id=payload.system_id, tenant_name=payload.baseline_id,
                    actor_email=_actor(current_user), actor_role=_role(current_user),
                    action_type="enterprise_baseline_created", resource_type="enterprise_baseline")

    return {"id": b.id, "baseline_id": b.baseline_id, "version": b.version,
            "approval_status": b.approval_status, "status": "created"}


@router.post("/baselines/{baseline_id}/approve")
def approve_baseline(
    baseline_id: str,
    version: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    b = db.query(models.EnterpriseBaseline).filter(
        models.EnterpriseBaseline.baseline_id == baseline_id,
        models.EnterpriseBaseline.version == version,
        models.EnterpriseBaseline.is_active == True,  # noqa: E712
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="Baseline not found")
    if b.approval_status == "approved":
        raise HTTPException(status_code=409, detail="Already approved")

    b.approval_status = "approved"
    b.approved_by = _actor(current_user)
    b.approved_at = datetime.now(timezone.utc)
    db.commit()

    log_audit_event(db, tenant_id=b.system_id, tenant_name=baseline_id,
                    actor_email=_actor(current_user), actor_role=_role(current_user),
                    action_type="enterprise_baseline_approved", resource_type="enterprise_baseline",
                    compliance_flag=True)

    return {"baseline_id": baseline_id, "version": version, "approval_status": "approved",
            "approved_by": b.approved_by, "approved_at": b.approved_at.isoformat()}


@router.post("/baselines/{baseline_id}/publish")
def publish_baseline(
    baseline_id: str,
    version: str = Query(...),
    facility_ids: List[str] = Query(..., description="Target facility IDs"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    b = db.query(models.EnterpriseBaseline).filter(
        models.EnterpriseBaseline.baseline_id == baseline_id,
        models.EnterpriseBaseline.version == version,
        models.EnterpriseBaseline.is_active == True,  # noqa: E712
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="Baseline not found")
    if b.approval_status != "approved":
        raise HTTPException(status_code=422, detail="Baseline must be approved before publishing")

    existing = json.loads(b.published_to)
    merged = list(set(existing + facility_ids))
    b.published_to = json.dumps(merged)
    db.commit()

    log_audit_event(db, tenant_id=b.system_id, tenant_name=baseline_id,
                    actor_email=_actor(current_user), actor_role=_role(current_user),
                    action_type="enterprise_baseline_published", resource_type="enterprise_baseline",
                    details={"facility_count": len(merged)}, compliance_flag=True)

    return {"baseline_id": baseline_id, "version": version,
            "published_to_count": len(merged), "facility_ids": merged}


@router.get("/baselines")
def list_enterprise_baselines(
    system_id: Optional[str] = Query(default=None),
    approval_status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    q = db.query(models.EnterpriseBaseline).filter(models.EnterpriseBaseline.is_active == True)  # noqa: E712
    if system_id:
        q = q.filter(models.EnterpriseBaseline.system_id == system_id)
    if approval_status:
        q = q.filter(models.EnterpriseBaseline.approval_status == approval_status)
    rows = q.order_by(models.EnterpriseBaseline.created_at.desc()).limit(200).all()
    return [{
        "id": r.id, "baseline_id": r.baseline_id, "version": r.version,
        "system_id": r.system_id, "instrument_type": r.instrument_type,
        "material_type": r.material_type, "approval_status": r.approval_status,
        "approved_by": r.approved_by,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "published_to_count": len(json.loads(r.published_to)),
        "created_by": r.created_by, "change_summary": r.change_summary,
        "created_at": r.created_at.isoformat(),
    } for r in rows]


@router.get("/baselines/{baseline_id}/history")
def baseline_version_history(
    baseline_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    rows = db.query(models.EnterpriseBaseline).filter(
        models.EnterpriseBaseline.baseline_id == baseline_id
    ).order_by(models.EnterpriseBaseline.created_at.desc()).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return {
        "baseline_id": baseline_id,
        "version_count": len(rows),
        "versions": [{
            "version": r.version, "approval_status": r.approval_status,
            "created_by": r.created_by, "change_summary": r.change_summary,
            "approved_by": r.approved_by,
            "published_to_count": len(json.loads(r.published_to)),
            "created_at": r.created_at.isoformat(),
            "is_active": r.is_active,
        } for r in rows],
    }
