"""Shadow §9 — Model Drift Monitoring.

Reuses ``app.services.sentinel_ai_health_service._detect_drift()`` for the
core confidence/agreement drift signal — the same trailing-30-day-window
comparison already relied on by several other services in this codebase
(pulse_alert_service, capa_suggestion_service, oracle_model_observatory_
service) — rather than a fourth reimplementation. This module only ADDS
the distributional breakdowns §9 additionally asks for (prediction
distribution, image-quality trend, instrument mix, facility variation),
computed over this candidate model's own ``ShadowPrediction`` rows, which
``_detect_drift`` does not report.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.services.sentinel_ai_health_service import _detect_drift


def prediction_distribution(rows: list) -> dict[str, int]:
    return dict(Counter(r.predicted_label for r in rows if r.predicted_label))


def instrument_mix(rows: list) -> dict[str, int]:
    return dict(Counter(r.instrument_family for r in rows if r.instrument_family))


def facility_variation(rows: list) -> dict[str, int]:
    return dict(Counter(r.facility_id for r in rows if r.facility_id))


def image_quality_trend(rows: list) -> dict[str, int]:
    return dict(Counter(r.image_quality for r in rows if r.image_quality))


def assess_drift(db: Session, tenant_id: str, rows: list) -> dict[str, Any]:
    """§9 — the full drift assessment: the reused confidence/agreement
    drift signal plus this model's own distributional breakdowns."""
    drift_detected, drift_detail = _detect_drift(db, tenant_id)
    return {
        "drift_detected": drift_detected,
        "drift_detail": drift_detail,
        "prediction_distribution": prediction_distribution(rows),
        "instrument_mix": instrument_mix(rows),
        "facility_variation": facility_variation(rows),
        "image_quality_trend": image_quality_trend(rows),
        "note": (
            "drift_detected/drift_detail reuse the platform's existing confidence/"
            "agreement drift detector (sentinel_ai_health_service); the "
            "distributions above are this candidate model's own shadow-prediction mix."
        ),
    }
