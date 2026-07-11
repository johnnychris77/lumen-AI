"""v4.9 — Project Phoenix, Section 3: AI Performance Observatory.

`ml/pilot_validation.py`'s `clinical_metrics`/`confidence_calibration` and
`sentinel_ai_health_service.compute_ai_health` already compute precision,
recall, F1, false-positive/negative rates, human agreement, and model
drift from real `SupervisorReview` rows — composed here directly, never
re-derived. The two genuinely new metrics are Inference Latency (nothing
anywhere measures AI-scoring wall-clock time) and Coverage as "% of
inspections that received a real AI confidence score" — a different
concept from `inspection_coverage.py`'s image/zone-capture-completeness
"coverage" of the same name.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.phoenix_intelligence import DISCLAIMER, LATENCY_STAGES, AIInferenceLatencySample
from app.models.supervisor_review import SupervisorReview
from app.services import sentinel_ai_health_service
from app.services.ml.pilot_validation import clinical_metrics


def record_latency_sample(db: Session, tenant_id: str, *, stage: str, latency_ms: float, inspection_id: int | None = None) -> dict:
    if stage not in LATENCY_STAGES:
        raise ValueError(f"stage must be one of {LATENCY_STAGES}")
    row = AIInferenceLatencySample(tenant_id=tenant_id, stage=stage, latency_ms=latency_ms, inspection_id=inspection_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "stage": row.stage, "latency_ms": row.latency_ms}


def latency_summary(db: Session, tenant_id: str, *, stage: str = "") -> dict:
    """Average/min/max real recorded latency — "insufficient data" (never
    a fabricated typical value) when no samples exist for a stage."""
    result: dict = {}
    stages = [stage] if stage else LATENCY_STAGES
    for s in stages:
        rows = (
            db.query(AIInferenceLatencySample)
            .filter(AIInferenceLatencySample.tenant_id == tenant_id, AIInferenceLatencySample.stage == s)
            .all()
        )
        if not rows:
            result[s] = {"sample_size": 0, "note": "insufficient data — no latency samples recorded yet"}
            continue
        values = sorted(r.latency_ms for r in rows)
        result[s] = {
            "sample_size": len(values), "avg_ms": round(sum(values) / len(values), 2),
            "min_ms": round(values[0], 2), "max_ms": round(values[-1], 2),
        }
    return result


def coverage_summary(db: Session, tenant_id: str) -> dict:
    """% of inspections that received a real AI confidence score — a
    different "coverage" concept from image/zone capture completeness."""
    total = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).count()
    ai_scored = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.ai_confidence.isnot(None))
        .count()
    )
    return {
        "total_inspections": total, "ai_scored_inspections": ai_scored,
        "ai_participation_coverage_pct": round(100 * ai_scored / total, 1) if total else None,
    }


def observatory_summary(db: Session, tenant_id: str) -> dict:
    """Composes real clinical metrics (precision/recall/F1/FP-FN/
    agreement/calibration), `sentinel_ai_health_service`'s drift
    detection, and Phoenix's two new metrics (latency, AI coverage)."""
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    metrics = clinical_metrics(reviews) if reviews else {}
    ai_health = sentinel_ai_health_service.compute_ai_health(db, tenant_id)

    return {
        "precision": metrics.get("precision"),
        "recall": metrics.get("recall"),
        "f1": metrics.get("f1"),
        "false_positive_rate": metrics.get("false_positive_rate"),
        "false_negative_rate": metrics.get("false_negative_rate"),
        "human_agreement_rate": metrics.get("supervisor_agreement_rate"),
        "supervisor_override_rate": metrics.get("override_rate"),
        "confidence_calibration": metrics.get("confidence_calibration"),
        "model_drift_detected": ai_health.get("drift_detected"),
        "model_drift_detail": ai_health.get("drift_detail"),
        "ai_confidence_avg": ai_health.get("ai_confidence_avg"),
        "sample_size": len(reviews),
        "inference_latency": latency_summary(db, tenant_id),
        "coverage": coverage_summary(db, tenant_id),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
