"""v4.2 — Project Pulse, Section 8: AI Operations Monitor.

Reuses `sentinel_ai_health_service.compute_ai_health` for confidence,
supervisor agreement, false positive/negative rate, and drift directly
— those already exist and are not recomputed here. This module adds
only what genuinely didn't exist before Pulse: model version
distribution and inference latency (both computed from real
`Inspection.model_version`/`inference_timestamp` columns), and a
confidence histogram (real `Inspection.ai_confidence` values bucketed,
never fabricated). GPU/CPU utilization is honestly reported as
`not_applicable` — confirmed nowhere in this codebase does any runtime
hardware metric exist; the CV pipeline (`app/cv/pipeline.py`) is a
deterministic, non-GPU inference gateway by default (`CV_PROVIDER=mock`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.services import sentinel_ai_health_service

_LOOKBACK_DAYS = 30
_CONFIDENCE_BUCKETS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.01)]


def _confidence_distribution(confidences: list[float]) -> dict:
    distribution = {}
    for low, high in _CONFIDENCE_BUCKETS:
        label = f"{low:.2f}-{high:.2f}"
        distribution[label] = sum(1 for c in confidences if low <= c < high)
    return distribution


def ai_operations_monitor(db: Session, tenant_id: str) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    inspections = db.query(Inspection).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).all()

    ai_health = sentinel_ai_health_service.compute_ai_health(db, tenant_id)

    version_counts: dict[str, int] = {}
    for i in inspections:
        version_counts[i.model_version] = version_counts.get(i.model_version, 0) + 1

    inference_times_ms = [
        (i.inference_timestamp - i.created_at).total_seconds() * 1000
        for i in inspections if i.inference_timestamp is not None
    ]
    avg_inference_time_ms = round(sum(inference_times_ms) / len(inference_times_ms), 1) if inference_times_ms else None

    confidences = [i.ai_confidence for i in inspections if i.ai_confidence is not None]
    confidence_distribution = _confidence_distribution(confidences) if confidences else {}

    processing_queue = db.query(Inspection.id).filter(Inspection.tenant_id == tenant_id, Inspection.score_status == "pending").count()
    total_recent = len(inspections)
    errored = sum(1 for i in inspections if i.status == "error")
    model_availability_pct = round(100 * (1 - errored / total_recent), 1) if total_recent else None

    return {
        "lookback_days": _LOOKBACK_DAYS,
        "model_version_distribution": version_counts,
        "avg_inference_time_ms": avg_inference_time_ms,
        "confidence_distribution": confidence_distribution,
        "ai_confidence_avg": ai_health.get("ai_confidence_avg"),
        "false_positive_rate": ai_health.get("false_positive_rate"),
        "false_negative_rate": ai_health.get("false_negative_rate"),
        "model_drift_detected": ai_health.get("drift_detected", False),
        "model_drift_detail": ai_health.get("drift_detail", ""),
        "processing_queue_length": processing_queue,
        "model_availability_pct": model_availability_pct,
        "gpu_utilization": "not_applicable",
        "cpu_utilization": "not_applicable",
        "hardware_note": "This system runs deterministic CV inference (CV_PROVIDER=mock by default) — no GPU/CPU runtime metrics are collected anywhere in this codebase.",
        "human_review_required": True,
    }
