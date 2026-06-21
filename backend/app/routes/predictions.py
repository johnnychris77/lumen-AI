"""P7: Predictive Instrument Failure Analytics API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.tier_guard import require_tier
from app.services.prediction_engine import (
    assess_recall_risk,
    assess_recall_risk_all_categories,
    assess_tray_risk,
    compute_predictive_dashboard,
    forecast_repair,
    forecast_repairs_for_tenant,
    predict_contamination_for_tenant,
    predict_failures_for_tenant,
    predict_instrument_failure,
    predict_contamination_recurrence,
)
from app.schemas.predictions import PredictionOutcomeCreate, PredictionAccuracyResult

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


def _log_prediction_access(tenant_id: str, action: str, request: Request, db) -> None:
    """Write prediction access event to audit log."""
    try:
        from app.models.audit_log import AuditLog
        role = request.headers.get("X-LumenAI-Role", "unknown")
        db.add(AuditLog(
            tenant_id=tenant_id,
            action_type=action,
            actor_role=role,
            resource_type="prediction",
            resource_id=tenant_id,
            request_method=request.method,
            request_path=str(request.url.path),
            client_ip=request.client.host if request.client else "",
        ))
        db.commit()
    except Exception:
        pass  # audit failure must never break prediction response


@router.get("/failures")
def list_failure_predictions(
    request: Request,
    tenant_id: str = Query(...),
    facility_id: str = Query(default=""),
    horizon_days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "failure_prediction_basic", db)
    predictions = predict_failures_for_tenant(tenant_id, facility_id, horizon_days, limit, db)
    _log_prediction_access(tenant_id, "prediction:failures_list", request, db)
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "horizon_days": horizon_days,
        "predictions": [p.model_dump() for p in predictions],
    }


@router.get("/failures/{instrument_id}")
def get_failure_prediction(
    instrument_id: str,
    request: Request,
    tenant_id: str = Query(...),
    facility_id: str = Query(default=""),
    horizon_days: int = Query(default=30, ge=1, le=365),
    barcode_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "failure_prediction_full", db)
    prediction = predict_instrument_failure(tenant_id, instrument_id, facility_id, horizon_days, db)
    _log_prediction_access(tenant_id, "prediction:failure_detail", request, db)
    return {"status": "success", "prediction": prediction.model_dump()}


@router.get("/contamination")
def list_contamination_predictions(
    request: Request,
    tenant_id: str = Query(...),
    facility_id: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "contamination_prediction", db)
    predictions = predict_contamination_for_tenant(tenant_id, facility_id, limit, db)
    _log_prediction_access(tenant_id, "prediction:contamination_list", request, db)
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "predictions": [p.model_dump() for p in predictions],
    }


@router.get("/contamination/{instrument_id}")
def get_contamination_prediction(
    instrument_id: str,
    request: Request,
    tenant_id: str = Query(...),
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "contamination_prediction", db)
    prediction = predict_contamination_recurrence(tenant_id, instrument_id, facility_id, db)
    _log_prediction_access(tenant_id, "prediction:contamination_list", request, db)
    return {"status": "success", "prediction": prediction.model_dump()}


@router.get("/repairs")
def list_repair_forecasts(
    request: Request,
    tenant_id: str = Query(...),
    facility_id: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "repair_forecasting", db)
    forecasts = forecast_repairs_for_tenant(tenant_id, facility_id, limit, db)
    _log_prediction_access(tenant_id, "prediction:repairs_list", request, db)
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "forecasts": [f.model_dump() for f in forecasts],
    }


@router.get("/repairs/{instrument_id}")
def get_repair_forecast(
    instrument_id: str,
    request: Request,
    tenant_id: str = Query(...),
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "repair_forecasting", db)
    forecast = forecast_repair(tenant_id, instrument_id, facility_id, db)
    _log_prediction_access(tenant_id, "prediction:repairs_list", request, db)
    return {"status": "success", "forecast": forecast.model_dump()}


@router.get("/recall-risk")
def list_recall_risks(
    request: Request,
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "recall_risk", db)
    risks = assess_recall_risk_all_categories(tenant_id, db)
    _log_prediction_access(tenant_id, "prediction:recall_risk", request, db)
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "recall_risks": [r.model_dump() for r in risks],
    }


@router.get("/recall-risk/{instrument_category}")
def get_recall_risk(
    instrument_category: str,
    request: Request,
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "recall_risk", db)
    risk = assess_recall_risk(tenant_id, instrument_category, db)
    _log_prediction_access(tenant_id, "prediction:recall_risk", request, db)
    return {"status": "success", "recall_risk": risk.model_dump()}


@router.get("/tray-risk")
def get_tray_risk(
    request: Request,
    tenant_id: str = Query(...),
    tray_id: str = Query(default="default-tray"),
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "tray_risk", db)
    assessment = assess_tray_risk(tenant_id, tray_id, facility_id, db)
    _log_prediction_access(tenant_id, "prediction:tray_risk", request, db)
    return {"status": "success", "tray_risk": assessment.model_dump()}


@router.get("/dashboard")
def predictive_dashboard(
    request: Request,
    tenant_id: str = Query(...),
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    require_tier(tenant_id, "predictive_dashboard", db)
    dashboard = compute_predictive_dashboard(tenant_id, facility_id, db)
    _log_prediction_access(tenant_id, "prediction:dashboard", request, db)
    return {"status": "success", "dashboard": dashboard.model_dump()}


@router.post("/outcomes")
def record_outcome(
    request: Request,
    body: PredictionOutcomeCreate,
    db: Session = Depends(get_db),
):
    """Record actual outcome against a prior prediction (for accuracy tracking)."""
    require_enterprise_auth(request)
    from app.models.predictions import PredictionOutcome
    from datetime import datetime, timezone
    record = PredictionOutcome(
        tenant_id=body.tenant_id,
        instrument_name=body.instrument_name,
        instrument_id=body.instrument_id,
        facility_id=body.facility_id,
        prediction_date=datetime.fromisoformat(body.prediction_date),
        predicted_risk_category=body.predicted_risk_category,
        predicted_failure_probability=body.predicted_failure_probability,
        actual_outcome=body.actual_outcome,
        outcome_notes=body.outcome_notes,
        recorded_by=body.recorded_by,
        outcome_date=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "success", "id": record.id}


@router.get("/accuracy")
def prediction_accuracy(
    request: Request,
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """Return prediction accuracy metrics for a tenant (clinical validation story)."""
    require_enterprise_auth(request)
    from app.models.predictions import PredictionOutcome
    rows = db.query(PredictionOutcome).filter(
        PredictionOutcome.tenant_id == tenant_id,
        PredictionOutcome.actual_outcome.in_(["failed", "repaired", "no_event"]),
    ).all()

    if not rows:
        return {"status": "success", "accuracy": PredictionAccuracyResult(
            tenant_id=tenant_id, data_source="insufficient"
        ).model_dump()}

    total = len(rows)
    tp = sum(1 for r in rows if r.predicted_risk_category in ("high", "critical")
             and r.actual_outcome in ("failed", "repaired"))
    fp = sum(1 for r in rows if r.predicted_risk_category in ("high", "critical")
             and r.actual_outcome == "no_event")
    fn = sum(1 for r in rows if r.predicted_risk_category in ("low", "medium")
             and r.actual_outcome == "failed")
    tn = sum(1 for r in rows if r.predicted_risk_category in ("low", "medium")
             and r.actual_outcome == "no_event")

    precision = round(tp / max(tp + fp, 1) * 100, 1)
    recall = round(tp / max(tp + fn, 1) * 100, 1)
    f1 = round(2 * precision * recall / max(precision + recall, 1), 1)
    accuracy = round((tp + tn) / total * 100, 1)

    return {"status": "success", "accuracy": PredictionAccuracyResult(
        tenant_id=tenant_id,
        total_outcomes=total,
        correct_predictions=tp + tn,
        precision=precision,
        recall=recall,
        f1_score=f1,
        accuracy_pct=accuracy,
        data_source="real",
    ).model_dump()}
