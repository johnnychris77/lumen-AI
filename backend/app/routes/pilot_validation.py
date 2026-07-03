"""Phase 18 — Real-World Pilot Validation & Clinical Performance Study routes.

Ground-truth case capture (supervisor review → confusion-matrix label),
clinical/zone performance metrics, the safety review queue, the validation
report generator, and the go/no-go readiness gate.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.pilot_validation import PilotValidationCase
from app.schemas.pilot_validation import PilotValidationCaseCreate
from app.services.pilot_validation_service import (
    build_safety_queue,
    compute_clinical_metrics,
    compute_critical_safety_metrics,
    compute_dashboard,
    compute_zone_performance,
    create_case,
    evaluate_go_no_go,
    generate_validation_report,
    list_cases,
)

router = APIRouter(prefix="/api/pilot-validation", tags=["pilot-validation"])


def _serialize(c: PilotValidationCase) -> dict:
    return {
        "id": c.id,
        "tenant_id": c.tenant_id,
        "inspection_id": c.inspection_id,
        "instrument_family": c.instrument_family,
        "manufacturer": c.manufacturer,
        "model": c.model,
        "anatomy_zone": c.anatomy_zone,
        "baseline_source": c.baseline_source,
        "has_baseline": c.has_baseline,
        "finding_type": c.finding_type,
        "severity": c.severity,
        "disposition": c.disposition,
        "ai_prediction": c.ai_prediction,
        "ai_confidence": c.ai_confidence,
        "supervisor_finding": c.supervisor_finding,
        "supervisor_zone_correction": c.supervisor_zone_correction,
        "reviewer_name": c.reviewer_name,
        "reviewer_rationale": c.reviewer_rationale,
        "ground_truth_label": c.ground_truth_label,
        "is_critical_finding": c.is_critical_finding,
        "dataset_version": c.dataset_version,
        "model_version": c.model_version,
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }


@router.post("/cases", status_code=201)
def submit_ground_truth_case(
    payload: PilotValidationCaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Record a supervisor-reviewed pilot case. The ground-truth label
    (TP/TN/FP/FN/inconclusive) is always derived server-side."""
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    case = create_case(db, tenant_id, payload)

    log_audit_event(
        db,
        tenant_id=tenant_id, tenant_name=tenant_id,
        actor_email=getattr(current_user, "email", None) or "unknown",
        actor_role=getattr(current_user, "role", "spd_manager"),
        action_type="pilot_validation_case_reviewed",
        resource_type="pilot_validation_case",
        resource_id=str(case.id),
        details={"ground_truth_label": case.ground_truth_label, "is_critical_finding": case.is_critical_finding},
        compliance_flag=True,
    )
    return _serialize(case)


@router.get("/cases")
def get_ground_truth_cases(
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    cases = list_cases(db, tenant_id, limit=limit)
    return {"tenant_id": tenant_id, "count": len(cases), "cases": [_serialize(c) for c in cases]}


@router.get("/metrics")
def get_clinical_metrics(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    """Section 4 — clinical performance metrics + critical safety metrics."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    cases = list_cases(db, tenant_id, limit=5000)
    return {
        "tenant_id": tenant_id,
        "clinical_metrics": compute_clinical_metrics(cases),
        "critical_safety_metrics": compute_critical_safety_metrics(cases),
    }


@router.get("/zone-performance")
def get_zone_performance(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    """Section 5 — per-zone performance metrics."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    cases = list_cases(db, tenant_id, limit=5000)
    return {"tenant_id": tenant_id, "zone_performance": compute_zone_performance(cases)}


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    """Section 6 — pilot performance dashboard (/pilot-validation route)."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    cases = list_cases(db, tenant_id, limit=5000)
    return {"tenant_id": tenant_id, **compute_dashboard(cases)}


@router.get("/safety-queue")
def get_safety_queue(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Section 7 — safety review queue."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    cases = list_cases(db, tenant_id, limit=5000)
    return {"tenant_id": tenant_id, **build_safety_queue(cases)}


@router.get("/report")
def get_validation_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Section 8 — pilot validation report generator."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    cases = list_cases(db, tenant_id, limit=5000)
    return {"tenant_id": tenant_id, **generate_validation_report(cases)}


@router.get("/go-no-go")
def get_go_no_go(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Section 9 — go/no-go readiness gate."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    cases = list_cases(db, tenant_id, limit=5000)
    return {"tenant_id": tenant_id, **evaluate_go_no_go(cases)}
