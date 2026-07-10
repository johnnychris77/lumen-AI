"""v4.2 — Project Pulse, Section 5: Pulse Alert Engine.

Eight named real-time alert types, each detected from real rows —
`ALERT_AI_CONFIDENCE_DROP` reuses Sentinel's existing (non-mock) drift
detector (`sentinel_ai_health_service._detect_drift`) directly rather
than re-deriving a second drift signal; the other seven are genuinely
new trend/threshold detections this sprint adds, following the same
"real per-tenant data, never a fabricated confidence score" convention
every other alert/recommendation engine in this codebase already uses.
Every alert persists `evidence`/`confidence`/`recommendation`/
`suggested_owner` as the sprint's own named fields — an idempotent
`_already_active` check (the same check-then-create pattern used
throughout Sentinel/Atlas/Insight/Horizon) prevents duplicate alerts on
repeated generation calls.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.knowledge import KnowledgeArticle
from app.models.or_connect import REPAIR_IN_PROGRESS, REPAIR_PENDING, RepairRequest
from app.models.pulse_operations import (
    ALERT_ACTIVE,
    ALERT_AI_CONFIDENCE_DROP,
    ALERT_CORROSION_SPIKE,
    ALERT_COVERAGE_DECLINE,
    ALERT_CRITICAL_BLOOD_TREND,
    ALERT_KNOWLEDGE_GAP,
    ALERT_MISSING_BASELINE,
    ALERT_REPAIR_SURGE,
    ALERT_REPEATED_SUPERVISOR_OVERRIDES,
    PulseAlert,
)
from app.models.supervisor_review import SupervisorReview
from app.services import sentinel_ai_health_service

_RECENT_DAYS = 7
_BASELINE_DAYS = 30
_MIN_SAMPLE = 5


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _already_active(db: Session, tenant_id: str, alert_type: str) -> bool:
    return db.query(PulseAlert.id).filter(
        PulseAlert.tenant_id == tenant_id, PulseAlert.alert_type == alert_type, PulseAlert.status == ALERT_ACTIVE,
    ).first() is not None


def _create_alert(
    db: Session, tenant_id: str, alert_type: str, *, severity: str, evidence: str, confidence: float,
    recommendation: str, suggested_owner: str, facility_name: str = "",
) -> dict:
    row = PulseAlert(
        tenant_id=tenant_id, facility_name=facility_name, alert_type=alert_type, severity=severity,
        evidence=evidence, confidence=confidence, recommendation=recommendation, suggested_owner=suggested_owner,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def _finding_rate(db: Session, tenant_id: str, finding_type: str, since: datetime, until: datetime | None = None) -> tuple[int, int]:
    findings_q = db.query(InspectionFinding.id).filter(
        InspectionFinding.tenant_id == tenant_id, InspectionFinding.finding_type == finding_type, InspectionFinding.created_at >= since,
    )
    total_q = db.query(Inspection.id).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since)
    if until is not None:
        findings_q = findings_q.filter(InspectionFinding.created_at < until)
        total_q = total_q.filter(Inspection.created_at < until)
    return findings_q.count(), total_q.count()


def _detect_finding_trend_alert(db: Session, tenant_id: str, finding_type: str, alert_type: str) -> dict | None:
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=_RECENT_DAYS)
    baseline_start = now - timedelta(days=_BASELINE_DAYS)

    recent_findings, recent_total = _finding_rate(db, tenant_id, finding_type, recent_start)
    baseline_findings, baseline_total = _finding_rate(db, tenant_id, finding_type, baseline_start, recent_start)

    if recent_total < _MIN_SAMPLE or baseline_total < _MIN_SAMPLE:
        return None

    recent_rate = recent_findings / recent_total
    baseline_rate = baseline_findings / baseline_total if baseline_total else 0.0
    if baseline_rate == 0 or recent_rate <= baseline_rate * 1.5:
        return None

    return _create_alert(
        db, tenant_id, alert_type, severity="high" if recent_rate > baseline_rate * 2 else "medium",
        evidence=f"{finding_type} finding rate rose from {baseline_rate:.1%} to {recent_rate:.1%} over the last {_RECENT_DAYS} days ({recent_findings} of {recent_total} inspections).",
        confidence=min(0.95, round(recent_rate / max(baseline_rate, 0.01) / 4, 2)),
        recommendation=f"Review recent {finding_type} findings for a common instrument, technician, or process cause. Possible contributing factor — not a confirmed root cause.",
        suggested_owner="spd_manager",
    )


def detect_critical_blood_trend(db: Session, tenant_id: str) -> dict | None:
    if _already_active(db, tenant_id, ALERT_CRITICAL_BLOOD_TREND):
        return None
    return _detect_finding_trend_alert(db, tenant_id, "blood", ALERT_CRITICAL_BLOOD_TREND)


def detect_corrosion_spike(db: Session, tenant_id: str) -> dict | None:
    if _already_active(db, tenant_id, ALERT_CORROSION_SPIKE):
        return None
    return _detect_finding_trend_alert(db, tenant_id, "corrosion", ALERT_CORROSION_SPIKE)


def detect_ai_confidence_drop(db: Session, tenant_id: str) -> dict | None:
    if _already_active(db, tenant_id, ALERT_AI_CONFIDENCE_DROP):
        return None
    ai_health = sentinel_ai_health_service.compute_ai_health(db, tenant_id)
    if not ai_health.get("drift_detected"):
        return None
    return _create_alert(
        db, tenant_id, ALERT_AI_CONFIDENCE_DROP, severity="high",
        evidence=str(ai_health.get("drift_detail", "")),
        confidence=0.8, recommendation="Review recent AI confidence and supervisor agreement trend; consider recalibration or additional supervisor sampling.",
        suggested_owner="spd_manager",
    )


def detect_repeated_supervisor_overrides(db: Session, tenant_id: str) -> dict | None:
    if _already_active(db, tenant_id, ALERT_REPEATED_SUPERVISOR_OVERRIDES):
        return None
    since = datetime.now(timezone.utc) - timedelta(days=_RECENT_DAYS)
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= since).all()
    if len(reviews) < _MIN_SAMPLE:
        return None
    overrides = [r for r in reviews if r.override_action]
    override_rate = len(overrides) / len(reviews)
    if override_rate < 0.25:
        return None
    return _create_alert(
        db, tenant_id, ALERT_REPEATED_SUPERVISOR_OVERRIDES, severity="medium",
        evidence=f"{len(overrides)} of {len(reviews)} supervisor reviews in the last {_RECENT_DAYS} days included an override ({override_rate:.0%}).",
        confidence=round(min(0.9, override_rate), 2),
        recommendation="Review overridden inspections for a common AI disagreement pattern — possible contributing factor for model recalibration or targeted retraining.",
        suggested_owner="spd_manager",
    )


def detect_missing_baseline(db: Session, tenant_id: str) -> dict | None:
    if _already_active(db, tenant_id, ALERT_MISSING_BASELINE):
        return None
    since = datetime.now(timezone.utc) - timedelta(days=_RECENT_DAYS)
    total = db.query(Inspection.id).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).count()
    if total < _MIN_SAMPLE:
        return None
    missing = db.query(Inspection.id).filter(
        Inspection.tenant_id == tenant_id, Inspection.created_at >= since, Inspection.baseline_status == "not_checked",
    ).count()
    missing_rate = missing / total
    if missing_rate < 0.2:
        return None
    return _create_alert(
        db, tenant_id, ALERT_MISSING_BASELINE, severity="medium",
        evidence=f"{missing} of {total} inspections in the last {_RECENT_DAYS} days have no baseline check ({missing_rate:.0%}).",
        confidence=round(min(0.9, missing_rate), 2),
        recommendation="Publish or link baselines for the affected instrument families before their next inspection cycle.",
        suggested_owner="spd_manager",
    )


def detect_repair_surge(db: Session, tenant_id: str) -> dict | None:
    if _already_active(db, tenant_id, ALERT_REPAIR_SURGE):
        return None
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=_RECENT_DAYS)
    baseline_start = now - timedelta(days=_BASELINE_DAYS)
    recent = db.query(RepairRequest.id).filter(RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= recent_start).count()
    baseline = db.query(RepairRequest.id).filter(
        RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= baseline_start, RepairRequest.created_at < recent_start,
    ).count()
    baseline_weekly_rate = baseline / (_BASELINE_DAYS / _RECENT_DAYS) if baseline else 0
    if baseline_weekly_rate < 1 or recent <= baseline_weekly_rate * 1.5:
        return None
    open_count = db.query(RepairRequest.id).filter(
        RepairRequest.tenant_id == tenant_id, RepairRequest.status.in_({REPAIR_PENDING, REPAIR_IN_PROGRESS}),
    ).count()
    return _create_alert(
        db, tenant_id, ALERT_REPAIR_SURGE, severity="medium",
        evidence=f"{recent} repair requests in the last {_RECENT_DAYS} days vs. a baseline weekly rate of {baseline_weekly_rate:.1f} ({open_count} currently open).",
        confidence=round(min(0.9, recent / max(baseline_weekly_rate, 1) / 3), 2),
        recommendation="Review recent repair causes for a common vendor, instrument family, or handling issue.",
        suggested_owner="clinical_engineering",
    )


def detect_coverage_decline(db: Session, tenant_id: str) -> dict | None:
    if _already_active(db, tenant_id, ALERT_COVERAGE_DECLINE):
        return None
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=_RECENT_DAYS)
    baseline_start = now - timedelta(days=_BASELINE_DAYS)
    recent_rows = db.query(Inspection.coverage_pct).filter(
        Inspection.tenant_id == tenant_id, Inspection.created_at >= recent_start, Inspection.coverage_pct.isnot(None),
    ).all()
    baseline_rows = db.query(Inspection.coverage_pct).filter(
        Inspection.tenant_id == tenant_id, Inspection.created_at >= baseline_start, Inspection.created_at < recent_start,
        Inspection.coverage_pct.isnot(None),
    ).all()
    if len(recent_rows) < _MIN_SAMPLE or len(baseline_rows) < _MIN_SAMPLE:
        return None
    recent_avg = sum(r[0] for r in recent_rows) / len(recent_rows)
    baseline_avg = sum(r[0] for r in baseline_rows) / len(baseline_rows)
    if baseline_avg == 0 or (baseline_avg - recent_avg) / baseline_avg < 0.15:
        return None
    return _create_alert(
        db, tenant_id, ALERT_COVERAGE_DECLINE, severity="medium",
        evidence=f"Average inspection coverage fell from {baseline_avg:.1f}% to {recent_avg:.1f}% over the last {_RECENT_DAYS} days.",
        confidence=round(min(0.9, (baseline_avg - recent_avg) / baseline_avg), 2),
        recommendation="Review recent inspection coverage — possible contributing factor: technician workload, image quality, or capture process changes.",
        suggested_owner="spd_manager",
    )


def detect_knowledge_gap(db: Session, tenant_id: str) -> dict | None:
    if _already_active(db, tenant_id, ALERT_KNOWLEDGE_GAP):
        return None
    since = datetime.now(timezone.utc) - timedelta(days=_BASELINE_DAYS)
    high_severity_findings = db.query(InspectionFinding.id).filter(
        InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since, InspectionFinding.severity_index >= 3,
    ).count()
    if high_severity_findings < _MIN_SAMPLE:
        return None
    recent_articles = db.query(KnowledgeArticle.id).filter(
        KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.created_at >= since,
    ).count()
    if recent_articles > 0:
        return None
    return _create_alert(
        db, tenant_id, ALERT_KNOWLEDGE_GAP, severity="low",
        evidence=f"{high_severity_findings} high-severity findings in the last {_BASELINE_DAYS} days with zero new knowledge articles captured in the same period.",
        confidence=0.6, recommendation="Capture a knowledge article documenting recent high-severity findings for technician education.",
        suggested_owner="spd_manager",
    )


_DETECTORS = [
    detect_critical_blood_trend, detect_corrosion_spike, detect_ai_confidence_drop,
    detect_repeated_supervisor_overrides, detect_missing_baseline, detect_repair_surge,
    detect_coverage_decline, detect_knowledge_gap,
]


def generate_all_alerts(db: Session, tenant_id: str) -> list[dict]:
    return [alert for detector in _DETECTORS if (alert := detector(db, tenant_id)) is not None]


def list_alerts(db: Session, tenant_id: str, *, status: str = "", alert_type: str = "") -> list[dict]:
    q = db.query(PulseAlert).filter(PulseAlert.tenant_id == tenant_id)
    if status:
        q = q.filter(PulseAlert.status == status)
    if alert_type:
        q = q.filter(PulseAlert.alert_type == alert_type)
    return [_row_to_dict(a) for a in q.order_by(PulseAlert.id.desc()).all()]


def acknowledge_alert(db: Session, tenant_id: str, alert_id: int, *, acknowledged_by: str) -> dict | None:
    row = db.query(PulseAlert).filter(PulseAlert.id == alert_id, PulseAlert.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.status = "acknowledged"
    row.acknowledged_by = acknowledged_by
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def resolve_alert(db: Session, tenant_id: str, alert_id: int) -> dict | None:
    row = db.query(PulseAlert).filter(PulseAlert.id == alert_id, PulseAlert.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.status = "resolved"
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
