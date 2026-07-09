"""v3.0 — Project Sentinel, Section 4: AI Health Monitor.

Reuses `ml/pilot_validation.py`'s real confusion-matrix math
(`clinical_metrics`, `confidence_calibration`) over `SupervisorReview` rows
rather than a fourth reimplementation. Model drift is a genuinely new,
real (not seeded-random) comparison: average AI confidence and supervisor
agreement rate in the most recent window vs. the prior window — unlike
`RWEMetricSnapshot.psi_score` (`app/models/validation.py`), which is still
seeded-random pending real population, this reads real `SupervisorReview`/
`Inspection` data and only ever reports "insufficient data" rather than a
fabricated number when either window is too small.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.supervisor_review import SupervisorReview
from app.services.ml.pilot_validation import clinical_metrics, confidence_calibration

_DRIFT_WINDOW_DAYS = 30
_MIN_REVIEWS_FOR_DRIFT = 10
_CONFIDENCE_DRIFT_THRESHOLD = 0.10
_AGREEMENT_DRIFT_THRESHOLD = 0.10


def _coverage_quality_pct(db: Session, tenant_id: str) -> float | None:
    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.coverage_pct.isnot(None))
        .all()
    )
    if not rows:
        return None
    complete = sum(1 for r in rows if (r.coverage_quality or "") in ("complete", "acceptable"))
    return round(100 * complete / len(rows), 1)


def _baseline_quality_pct(db: Session, tenant_id: str) -> float | None:
    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.has_image.is_(True))
        .all()
    )
    if not rows:
        return None
    approved = sum(1 for r in rows if r.baseline_status == "approved")
    return round(100 * approved / len(rows), 1)


def _detect_drift(db: Session, tenant_id: str) -> tuple[bool, str]:
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=_DRIFT_WINDOW_DAYS)
    prior_start = now - timedelta(days=2 * _DRIFT_WINDOW_DAYS)

    recent = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= recent_start)
        .all()
    )
    prior = (
        db.query(SupervisorReview)
        .filter(
            SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= prior_start,
            SupervisorReview.created_at < recent_start,
        )
        .all()
    )
    if len(recent) < _MIN_REVIEWS_FOR_DRIFT or len(prior) < _MIN_REVIEWS_FOR_DRIFT:
        return False, (
            f"Insufficient reviews to assess drift (recent: {len(recent)}, prior: {len(prior)}; "
            f"need >= {_MIN_REVIEWS_FOR_DRIFT} in each window)."
        )

    recent_conf = [r.ai_confidence for r in recent if r.ai_confidence is not None]
    prior_conf = [r.ai_confidence for r in prior if r.ai_confidence is not None]
    recent_agree = sum(1 for r in recent if r.agreement == "agree") / len(recent)
    prior_agree = sum(1 for r in prior if r.agreement == "agree") / len(prior)

    details = []
    drifted = False
    if recent_conf and prior_conf:
        recent_avg = sum(recent_conf) / len(recent_conf)
        prior_avg = sum(prior_conf) / len(prior_conf)
        delta = recent_avg - prior_avg
        if abs(delta) >= _CONFIDENCE_DRIFT_THRESHOLD:
            drifted = True
            details.append(f"Average AI confidence shifted {delta:+.2f} ({prior_avg:.2f} -> {recent_avg:.2f}).")

    agreement_delta = recent_agree - prior_agree
    if abs(agreement_delta) >= _AGREEMENT_DRIFT_THRESHOLD:
        drifted = True
        details.append(f"Supervisor agreement rate shifted {agreement_delta:+.2f} ({prior_agree:.2f} -> {recent_agree:.2f}).")

    if not details:
        return False, f"No significant shift detected over the trailing {_DRIFT_WINDOW_DAYS}-day windows."
    return drifted, " ".join(details)


def compute_ai_health(db: Session, tenant_id: str) -> dict:
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    metrics = clinical_metrics(reviews) if reviews else {}
    calibration = confidence_calibration(reviews) if reviews else {}

    insp_rows = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id, models.Inspection.ai_confidence.isnot(None)).all()
    ai_confidence_avg = round(sum(r.ai_confidence for r in insp_rows) / len(insp_rows), 3) if insp_rows else None

    drift_detected, drift_detail = _detect_drift(db, tenant_id)

    from app.services.knowledge_graph_service import learning_confidence

    kg = learning_confidence(db, tenant_id)

    return {
        "ai_confidence_avg": ai_confidence_avg,
        "supervisor_agreement_rate": metrics.get("supervisor_agreement_rate"),
        "false_positive_rate": metrics.get("false_positive_rate"),
        "false_negative_rate": metrics.get("false_negative_rate"),
        "confidence_calibration": calibration,
        "coverage_quality_pct": _coverage_quality_pct(db, tenant_id),
        "baseline_quality_pct": _baseline_quality_pct(db, tenant_id),
        "kg_confidence": kg.get("knowledge_confidence"),
        "kg_sample_size": kg.get("sample_sizes", {}).get("supervisor_reviews", 0),
        "drift_detected": drift_detected,
        "drift_detail": drift_detail,
        "sample_size": len(reviews),
        "human_review_required": True,
    }
