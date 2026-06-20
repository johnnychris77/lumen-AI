"""P7: Nightly prediction pre-compute scheduler.

Runs all 5 prediction engines for every tenant and persists results
to the prediction DB tables. API endpoints read from cache first.
"""
from __future__ import annotations

import logging
logger = logging.getLogger(__name__)


def _run_nightly_predictions(db_factory) -> dict:
    """Compute and persist predictions for all active tenants."""
    from app.models.tenant_plan import TenantPlan
    from app.models.predictions import (
        InstrumentFailurePrediction,
        ContaminationRecurrencePrediction,
        RepairForecast,
        RecallRiskAssessment,
        TrayRiskAssessment,
    )
    from app.services.prediction_engine import (
        predict_failures_for_tenant,
        predict_contamination_for_tenant,
        forecast_repairs_for_tenant,
        assess_recall_risk_all_categories,
        assess_tray_risk,
    )
    import json

    db = db_factory()
    stats = {"tenants": 0, "predictions": 0, "errors": 0}

    try:
        tenant_ids = [row[0] for row in db.query(TenantPlan.tenant_id).distinct().all()]
        if not tenant_ids:
            logger.info("No tenant plans found — skipping nightly prediction run")
            return stats

        for tenant_id in tenant_ids:
            try:
                # Failure predictions (30d and 90d)
                for horizon in [30, 90]:
                    preds = predict_failures_for_tenant(tenant_id, "", horizon, 50, db)
                    for p in preds:
                        db.add(InstrumentFailurePrediction(
                            tenant_id=p.tenant_id,
                            facility_id=p.facility_id,
                            instrument_name=p.instrument_name,
                            instrument_category=p.instrument_category,
                            horizon_days=horizon,
                            failure_probability=p.failure_probability,
                            risk_score=p.risk_score,
                            risk_category=p.risk_category,
                            confidence=p.confidence,
                            records_used=p.records_used,
                            evidence_json=json.dumps([e.model_dump() for e in p.evidence]),
                            recommended_action=p.recommended_action,
                            data_source=p.data_source,
                        ))
                        stats["predictions"] += 1

                # Contamination predictions
                contam = predict_contamination_for_tenant(tenant_id, "", 50, db)
                for p in contam:
                    db.add(ContaminationRecurrencePrediction(
                        tenant_id=p.tenant_id,
                        facility_id=p.facility_id,
                        instrument_name=p.instrument_name,
                        instrument_category=p.instrument_category,
                        recurrence_probability=p.recurrence_probability,
                        risk_score=p.risk_score,
                        risk_category=p.risk_category,
                        confidence=p.confidence,
                        dominant_contaminant=p.dominant_contaminant,
                        records_used=p.records_used,
                        evidence_json=json.dumps([e.model_dump() for e in p.evidence]),
                        recommended_action=p.recommended_action,
                        data_source=p.data_source,
                    ))
                    stats["predictions"] += 1

                # Repair forecasts
                repairs = forecast_repairs_for_tenant(tenant_id, "", 50, db)
                for p in repairs:
                    db.add(RepairForecast(
                        tenant_id=p.tenant_id,
                        facility_id=p.facility_id,
                        instrument_name=p.instrument_name,
                        instrument_category=p.instrument_category,
                        repair_probability_90d=p.repair_probability_90d,
                        replacement_probability_180d=p.replacement_probability_180d,
                        risk_score=p.risk_score,
                        risk_category=p.risk_category,
                        confidence=p.confidence,
                        estimated_repair_cost_usd=p.estimated_repair_cost_usd,
                        estimated_replacement_cost_usd=p.estimated_replacement_cost_usd,
                        recommended_action=p.recommended_action,
                        records_used=p.records_used,
                        evidence_json=json.dumps([e.model_dump() for e in p.evidence]),
                        data_source=p.data_source,
                    ))
                    stats["predictions"] += 1

                # Recall risk
                recalls = assess_recall_risk_all_categories(tenant_id, db)
                for p in recalls:
                    db.add(RecallRiskAssessment(
                        tenant_id=tenant_id,
                        instrument_category=p.instrument_category,
                        exposure_score=p.exposure_score,
                        active_recall_count=p.active_recall_count,
                        critical_recall_count=p.critical_recall_count,
                        instruments_affected_estimate=p.instruments_affected_estimate,
                        urgency_tier=p.urgency_tier,
                        evidence_json=json.dumps([e.model_dump() for e in p.evidence]),
                        recommended_action=p.recommended_action,
                        data_source=p.data_source,
                    ))
                    stats["predictions"] += 1

                # Tray risk
                tray = assess_tray_risk(tenant_id, "default-tray", "", db)
                db.add(TrayRiskAssessment(
                    tenant_id=tray.tenant_id,
                    facility_id=tray.facility_id,
                    tray_id=tray.tray_id,
                    tray_risk_score=tray.tray_risk_score,
                    risk_category=tray.risk_category,
                    instrument_count=tray.instrument_count,
                    high_risk_instrument_count=tray.high_risk_instrument_count,
                    highest_risk_instrument=tray.highest_risk_instrument,
                    worst_failure_probability=tray.worst_failure_probability,
                    recommended_action=tray.recommended_action,
                    evidence_json=json.dumps([e.model_dump() for e in tray.evidence]),
                    data_source=tray.data_source,
                ))
                stats["predictions"] += 1
                stats["tenants"] += 1

            except Exception as exc:
                logger.error("Prediction error for tenant %s: %s", tenant_id, exc)
                stats["errors"] += 1

        db.commit()
        logger.info("Nightly prediction run complete: %s", stats)

    except Exception as exc:
        logger.error("Nightly prediction scheduler failed: %s", exc)
        db.rollback()
    finally:
        db.close()

    return stats


def register_prediction_scheduler(scheduler, db_factory) -> None:
    """Register nightly prediction job with APScheduler. Call from app lifespan."""
    scheduler.add_job(
        _run_nightly_predictions,
        trigger="cron",
        hour=2,
        minute=0,
        id="nightly_predictions",
        replace_existing=True,
        kwargs={"db_factory": db_factory},
    )
    logger.info("Nightly prediction scheduler registered (runs at 02:00 UTC)")
