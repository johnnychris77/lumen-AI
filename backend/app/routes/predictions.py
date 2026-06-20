"""P7: Predictive Instrument Failure Analytics API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
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

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


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
    predictions = predict_failures_for_tenant(tenant_id, facility_id, horizon_days, limit, db)
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
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    prediction = predict_instrument_failure(tenant_id, instrument_id, facility_id, horizon_days, db)
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
    predictions = predict_contamination_for_tenant(tenant_id, facility_id, limit, db)
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
    prediction = predict_contamination_recurrence(tenant_id, instrument_id, facility_id, db)
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
    forecasts = forecast_repairs_for_tenant(tenant_id, facility_id, limit, db)
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
    forecast = forecast_repair(tenant_id, instrument_id, facility_id, db)
    return {"status": "success", "forecast": forecast.model_dump()}


@router.get("/recall-risk")
def list_recall_risks(
    request: Request,
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    risks = assess_recall_risk_all_categories(tenant_id, db)
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
    risk = assess_recall_risk(tenant_id, instrument_category, db)
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
    assessment = assess_tray_risk(tenant_id, tray_id, facility_id, db)
    return {"status": "success", "tray_risk": assessment.model_dump()}


@router.get("/dashboard")
def predictive_dashboard(
    request: Request,
    tenant_id: str = Query(...),
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    require_enterprise_auth(request)
    dashboard = compute_predictive_dashboard(tenant_id, facility_id, db)
    return {"status": "success", "dashboard": dashboard.model_dump()}
