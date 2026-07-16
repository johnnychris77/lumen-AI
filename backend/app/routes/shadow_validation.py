"""Shadow — Phase 6: Prospective Shadow-Mode Clinical Validation API.

Pilot site configuration, ground-truth collection, the error review queue,
failure analysis, model drift, validation metrics, safety monitoring, the
clinical review board, and the seven validation reports. Nothing here
drives or influences a clinical decision — every read is advisory
evidence for the human-owned Validated Candidate promotion decision (see
``app.services.ml.candidate_promotion``).
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.model_registry import ModelRegistryEntry
from app.models.pilot import PilotStatus
from app.models.shadow_prediction import ShadowPrediction
from app.models.shadow_validation import ClinicalReviewBoardSession, ShadowErrorReviewItem, ShadowGroundTruth
from app.services import pilot_service
from app.services.enterprise_audit_service import record_enterprise_audit_event
from app.services.ml import (
    shadow_clinical_review_board as board_service,
    shadow_drift_monitor,
    shadow_error_review_queue,
    shadow_failure_analysis,
    shadow_ground_truth,
    shadow_reports,
    shadow_safety_monitor,
    shadow_validation_metrics,
)
from app.services.ml.candidate_training import CANDIDATE_CLASSES
from app.services.ml.shadow_dashboard import performance_dashboard

router = APIRouter(tags=["shadow-validation"])


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _shadow_rows(db: Session, tenant_id: str, model_id: str | None) -> list[ShadowPrediction]:
    q = db.query(ShadowPrediction).filter(ShadowPrediction.tenant_id == tenant_id)
    if model_id:
        q = q.filter(ShadowPrediction.model_id == model_id)
    return q.order_by(ShadowPrediction.id.desc()).all()


def _sample_from_review_item(item: ShadowErrorReviewItem) -> dict:
    """Adapts a queued review item into the plain-dict sample shape
    ``error_analysis``/``shadow_failure_analysis`` expect."""
    return {
        "id": item.id,
        "true_label": item.human_decision,
        "predicted_label": item.ai_prediction,
        "confidence": item.ai_confidence,
        "date": item.created_at.date().isoformat() if item.created_at else None,
    }


# ── §2 — Pilot Site Configuration ───────────────────────────────────────────

class PilotSiteIn(BaseModel):
    facility_id: str = Field(..., min_length=1, max_length=100)
    organization: str = Field("", max_length=255)
    department: str = Field("", max_length=255)
    clinical_lead: str = Field("", max_length=255)
    technical_lead: str = Field("", max_length=255)
    quality_lead: str = Field("", max_length=255)
    validation_coordinator: str = Field("", max_length=255)
    agreed_kpis: dict = Field(default_factory=dict)
    pilot_end_date: datetime | None = None


def _pilot_view(row: PilotStatus) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "facility_id": row.facility_id,
        "organization": row.organization,
        "department": row.department,
        "clinical_lead": row.clinical_lead,
        "technical_lead": row.technical_lead,
        "quality_lead": row.quality_lead,
        "validation_coordinator": row.validation_coordinator,
        "pilot_start_date": row.pilot_start_date.isoformat() if row.pilot_start_date else None,
        "pilot_end_date": row.pilot_end_date.isoformat() if row.pilot_end_date else None,
        "conversion_ready": row.conversion_ready,
    }


@router.post("/shadow-validation/pilot-sites", status_code=201)
def create_pilot_site(
    body: PilotSiteIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    row = pilot_service.start_pilot(
        db, tenant_id, body.facility_id, body.agreed_kpis,
        organization=body.organization, department=body.department,
        clinical_lead=body.clinical_lead, technical_lead=body.technical_lead,
        quality_lead=body.quality_lead, validation_coordinator=body.validation_coordinator,
        pilot_end_date=body.pilot_end_date,
    )
    record_enterprise_audit_event(
        db, action_type="shadow_pilot_site_registered", resource_type="pilot_site",
        resource_id=f"{tenant_id}:{body.facility_id}", actor=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), tenant_id=tenant_id,
    )
    return _pilot_view(row)


@router.get("/shadow-validation/pilot-sites/{facility_id}")
def get_pilot_site(
    facility_id: str, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    row = (
        db.query(PilotStatus)
        .filter(PilotStatus.tenant_id == tenant_id, PilotStatus.facility_id == facility_id)
        .order_by(PilotStatus.id.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No pilot site registered for this facility.")
    return _pilot_view(row)


# ── §3 — Ground Truth Collection ────────────────────────────────────────────

class GroundTruthIn(BaseModel):
    inspection_id: int
    model_id: str = Field("", max_length=100)
    model_version: str = Field("", max_length=50)
    facility_id: str = Field("", max_length=100)
    technician_finding: str = Field(..., max_length=100)
    technician_name: str = Field(..., max_length=255)


class SupervisorFindingIn(BaseModel):
    supervisor_finding: str = Field(..., max_length=100)
    supervisor_name: str = Field(..., max_length=255)


class AdjudicationIn(BaseModel):
    final_adjudicated_finding: str = Field(..., max_length=100)
    adjudicator_name: str = Field(..., max_length=255)
    reason_for_correction: str = ""
    supporting_evidence: str = ""


def _ground_truth_view(row: ShadowGroundTruth) -> dict:
    return {
        "id": row.id,
        "inspection_id": row.inspection_id,
        "facility_id": row.facility_id,
        "technician_finding": row.technician_finding,
        "technician_name": row.technician_name,
        "technician_reviewed_at": row.technician_reviewed_at.isoformat() if row.technician_reviewed_at else None,
        "supervisor_finding": row.supervisor_finding,
        "supervisor_name": row.supervisor_name,
        "supervisor_reviewed_at": row.supervisor_reviewed_at.isoformat() if row.supervisor_reviewed_at else None,
        "final_adjudicated_finding": row.final_adjudicated_finding,
        "adjudicator_name": row.adjudicator_name,
        "adjudicated_at": row.adjudicated_at.isoformat() if row.adjudicated_at else None,
        "reason_for_correction": row.reason_for_correction,
        "supporting_evidence": row.supporting_evidence,
        "final_finding": shadow_ground_truth.final_finding(row),
    }


@router.post("/shadow-validation/ground-truth", status_code=201)
def record_technician_finding(
    body: GroundTruthIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator")),
):
    tenant_id = _tenant(current_user, request)
    row = shadow_ground_truth.record_technician_finding(
        db, tenant_id=tenant_id, inspection_id=body.inspection_id, model_id=body.model_id,
        model_version=body.model_version, facility_id=body.facility_id,
        technician_finding=body.technician_finding, technician_name=body.technician_name,
    )
    return _ground_truth_view(row)


def _get_ground_truth_or_404(db: Session, tenant_id: str, gt_id: int) -> ShadowGroundTruth:
    row = (
        db.query(ShadowGroundTruth)
        .filter(ShadowGroundTruth.id == gt_id, ShadowGroundTruth.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Ground truth record not found.")
    return row


@router.patch("/shadow-validation/ground-truth/{gt_id}/supervisor-finding")
def record_supervisor_finding(
    gt_id: int, body: SupervisorFindingIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    row = _get_ground_truth_or_404(db, tenant_id, gt_id)
    row = shadow_ground_truth.record_supervisor_finding(
        db, row, supervisor_finding=body.supervisor_finding, supervisor_name=body.supervisor_name,
    )
    return _ground_truth_view(row)


@router.patch("/shadow-validation/ground-truth/{gt_id}/adjudication")
def record_adjudication(
    gt_id: int, body: AdjudicationIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    row = _get_ground_truth_or_404(db, tenant_id, gt_id)
    row = shadow_ground_truth.record_adjudication(
        db, row, final_adjudicated_finding=body.final_adjudicated_finding,
        adjudicator_name=body.adjudicator_name, reason_for_correction=body.reason_for_correction,
        supporting_evidence=body.supporting_evidence,
    )
    record_enterprise_audit_event(
        db, action_type="shadow_ground_truth_adjudicated", resource_type="shadow_ground_truth",
        resource_id=gt_id, actor=_actor(current_user), actor_role=getattr(current_user, "role", ""),
        tenant_id=tenant_id,
    )
    return _ground_truth_view(row)


@router.get("/shadow-validation/ground-truth")
def list_ground_truth(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    rows = (
        db.query(ShadowGroundTruth)
        .filter(ShadowGroundTruth.tenant_id == tenant_id)
        .order_by(ShadowGroundTruth.id.desc())
        .all()
    )
    return {"count": len(rows), "records": [_ground_truth_view(r) for r in rows]}


# ── §5 — Performance Dashboard ───────────────────────────────────────────────

@router.get("/shadow-validation/dashboard")
def dashboard(
    request: Request, model_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    return performance_dashboard(_shadow_rows(db, tenant_id, model_id or None))


# ── §6 — Error Review Queue ──────────────────────────────────────────────────

def _review_item_view(item: ShadowErrorReviewItem) -> dict:
    return {
        "id": item.id,
        "shadow_prediction_id": item.shadow_prediction_id,
        "inspection_id": item.inspection_id,
        "model_id": item.model_id,
        "human_decision": item.human_decision,
        "ai_prediction": item.ai_prediction,
        "ai_confidence": item.ai_confidence,
        "comparison_category": item.comparison_category,
        "failure_classification": item.failure_classification,
        "reviewer_comments": item.reviewer_comments,
        "status": item.status,
        "resolved_by": item.resolved_by,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
    }


@router.get("/shadow-validation/error-review-queue")
def error_review_queue(
    request: Request, status: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    items = shadow_error_review_queue.list_queue(db, tenant_id, status=status or None)
    return {"count": len(items), "queue": [_review_item_view(i) for i in items]}


class ResolveReviewItemIn(BaseModel):
    reviewer_comments: str = ""
    failure_classification: str = ""


@router.post("/shadow-validation/error-review-queue/{item_id}/resolve")
def resolve_review_item(
    item_id: int, body: ResolveReviewItemIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    item = (
        db.query(ShadowErrorReviewItem)
        .filter(ShadowErrorReviewItem.id == item_id, ShadowErrorReviewItem.tenant_id == tenant_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found.")
    item = shadow_error_review_queue.resolve_item(
        db, item, resolved_by=_actor(current_user), reviewer_comments=body.reviewer_comments,
        failure_classification=body.failure_classification,
    )
    return _review_item_view(item)


# ── §7 — Failure Analysis ────────────────────────────────────────────────────

@router.get("/shadow-validation/failure-analysis")
def failure_analysis(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    items = shadow_error_review_queue.list_queue(db, tenant_id)
    samples = [_sample_from_review_item(i) for i in items]
    return shadow_failure_analysis.analyze_failures(samples)


# ── §8 — Clinical Review Board ──────────────────────────────────────────────

class ReviewBoardSessionIn(BaseModel):
    model_id: str = Field(..., max_length=100)
    model_version: str = Field("", max_length=50)
    reviewers: list[dict] = Field(default_factory=list)
    performance_summary: str = ""
    failure_modes_summary: str = ""
    operational_impact: str = ""
    readiness_assessment: str = ""
    recommendations: str = ""
    review_period_start: datetime | None = None
    review_period_end: datetime | None = None
    approved: bool | None = None


@router.post("/shadow-validation/clinical-review-board", status_code=201)
def record_review_board_session(
    body: ReviewBoardSessionIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    row = board_service.record_review_session(
        db, tenant_id=tenant_id, model_id=body.model_id, model_version=body.model_version,
        reviewers=body.reviewers, performance_summary=body.performance_summary,
        failure_modes_summary=body.failure_modes_summary, operational_impact=body.operational_impact,
        readiness_assessment=body.readiness_assessment, recommendations=body.recommendations,
        review_period_start=body.review_period_start, review_period_end=body.review_period_end,
        approved=body.approved, decided_by=_actor(current_user) if body.approved is not None else "",
    )
    record_enterprise_audit_event(
        db, action_type="shadow_clinical_review_board_session_recorded",
        resource_type="clinical_review_board_session", resource_id=row.id,
        actor=_actor(current_user), actor_role=getattr(current_user, "role", ""), tenant_id=tenant_id,
    )
    return board_service.as_dict(row)


@router.get("/shadow-validation/clinical-review-board/latest")
def latest_review_board_session(
    request: Request, model_id: str, model_version: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    row = board_service.latest_session(db, tenant_id=tenant_id, model_id=model_id, model_version=model_version)
    if row is None:
        raise HTTPException(status_code=404, detail="No clinical review board session recorded for this model.")
    return board_service.as_dict(row)


# ── §9 — Model Drift Monitoring ──────────────────────────────────────────────

@router.get("/shadow-validation/drift")
def drift(
    request: Request, model_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    rows = _shadow_rows(db, tenant_id, model_id or None)
    return shadow_drift_monitor.assess_drift(db, tenant_id, rows)


# ── §10 — Validation Metrics ─────────────────────────────────────────────────

@router.get("/shadow-validation/validation-metrics")
def validation_metrics(
    request: Request, model_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    rows = _shadow_rows(db, tenant_id, model_id or None)
    metrics = shadow_validation_metrics.validated_metrics(rows)
    gt_rows = (
        db.query(ShadowGroundTruth).filter(ShadowGroundTruth.tenant_id == tenant_id).all()
    )
    metrics["inter_reviewer_agreement"] = shadow_validation_metrics.inter_reviewer_agreement(gt_rows)
    return metrics


# ── §11 — Safety Monitoring ──────────────────────────────────────────────────

@router.get("/shadow-validation/safety-monitor")
def safety_monitor(
    request: Request, model_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    rows = _shadow_rows(db, tenant_id, model_id or None)
    items = shadow_error_review_queue.list_queue(db, tenant_id)
    samples = [_sample_from_review_item(i) for i in items]
    reg = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.tenant_id == tenant_id, ModelRegistryEntry.model_id == model_id)
        .order_by(ModelRegistryEntry.id.desc())
        .first()
    ) if model_id else None
    if reg:
        eval_metrics = json.loads(reg.evaluation_metrics or "{}")
        supported = sorted((eval_metrics.get("per_class") or {}).keys()) or list(CANDIDATE_CLASSES)
    else:
        supported = list(CANDIDATE_CLASSES)
    return shadow_safety_monitor.safety_monitor_report(
        rows, candidate_classes=CANDIDATE_CLASSES, supported_classes=supported or CANDIDATE_CLASSES,
        samples=samples,
    )


# ── §12 — Validation Reports ─────────────────────────────────────────────────

_REPORT_TYPES = (
    "weekly", "monthly", "performance-summary", "error-analysis",
    "failure-trend", "pilot-progress", "clinical-review-summary",
)


@router.get("/shadow-validation/reports/{report_type}")
def get_report(
    report_type: str, request: Request, model_id: str = "", facility_id: str = "",
    period_start: datetime | None = None, period_end: datetime | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    if report_type not in _REPORT_TYPES:
        raise HTTPException(status_code=404, detail=f"Unknown report type. Known: {list(_REPORT_TYPES)}")
    tenant_id = _tenant(current_user, request)
    rows = _shadow_rows(db, tenant_id, model_id or None)

    if report_type in ("weekly", "monthly"):
        if period_start is None or period_end is None:
            raise HTTPException(status_code=422, detail="period_start and period_end are required for this report.")
        fn = shadow_reports.weekly_report if report_type == "weekly" else shadow_reports.monthly_report
        return fn(rows, period_start=period_start, period_end=period_end)

    if report_type == "performance-summary":
        return shadow_reports.performance_summary(rows, period_start=period_start, period_end=period_end)

    items = shadow_error_review_queue.list_queue(db, tenant_id)
    samples = [_sample_from_review_item(i) for i in items]
    if report_type == "error-analysis":
        return shadow_reports.error_analysis_report(samples, period_start=period_start, period_end=period_end)
    if report_type == "failure-trend":
        return shadow_reports.failure_trend_report(samples, period_start=period_start, period_end=period_end)

    if report_type == "pilot-progress":
        pilot_status = pilot_service.get_pilot_status(db, tenant_id, facility_id) if facility_id else None
        return shadow_reports.pilot_progress_report(pilot_status, rows, period_start=period_start, period_end=period_end)

    sessions = (
        db.query(ClinicalReviewBoardSession)
        .filter(ClinicalReviewBoardSession.tenant_id == tenant_id)
        .order_by(ClinicalReviewBoardSession.id.desc())
        .all()
    )
    return shadow_reports.clinical_review_summary(sessions, period_start=period_start, period_end=period_end)
