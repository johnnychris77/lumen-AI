"""v3.0 — Project Sentinel, Section 9: Enterprise Alert Center.

No unified alert feed existed before this module — `SPDAlert` (digital
twin workflow), `AlertEvent` (external Slack/Teams/email dispatch),
`WorkflowNotification` (in-app SPD queue), and `CaseRiskAlert` (OR Connect)
are each siloed to their own subsystem. `SentinelAlert` aggregates
Sentinel's own findings (risk signals, watchlist entries, digital twin
flags, AI health drift) into one explainable feed, each with a plain-
language narrative and a concrete recommendation — never a bare number.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.sentinel_orchestration import (
    SIGNAL_REPEATED_BLOOD,
    SIGNAL_REPEATED_BONE,
    SIGNAL_REPEATED_CORROSION,
    SIGNAL_REPEATED_DAMAGE,
    SIGNAL_REPEATED_LOW_CONFIDENCE,
    SIGNAL_REPEATED_MISSING_COVERAGE,
    SIGNAL_REPEATED_REPAIR_REFERRALS,
    SIGNAL_REPEATED_RUST,
    SIGNAL_REPEATED_SUPERVISOR_OVERRIDES,
    TWIN_TIER_CRITICAL,
    TWIN_TIER_ESCALATION,
    SentinelAlert,
)

_RECOMMENDATION_BY_SIGNAL = {
    SIGNAL_REPEATED_BLOOD: "Review manual cleaning competency for this anatomy zone.",
    SIGNAL_REPEATED_RUST: "Evaluate storage and drying practices for affected instruments.",
    SIGNAL_REPEATED_BONE: "Review manual cleaning competency for this anatomy zone.",
    SIGNAL_REPEATED_CORROSION: "Evaluate storage conditions and consider a manufacturer material review.",
    SIGNAL_REPEATED_DAMAGE: "Evaluate handling and maintenance practices for this instrument family.",
    SIGNAL_REPEATED_LOW_CONFIDENCE: "Schedule an image-capture refresher for the affected technician.",
    SIGNAL_REPEATED_MISSING_COVERAGE: "Reinforce guided-capture required-zone checklist compliance.",
    SIGNAL_REPEATED_SUPERVISOR_OVERRIDES: "Review AI model calibration and clinical reasoning for this instrument type.",
    SIGNAL_REPEATED_REPAIR_REFERRALS: "Evaluate instrument/vendor reliability; consider replacement or vendor review.",
}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _already_alerted(db: Session, tenant_id: str, source: str, related_signal_id: int) -> bool:
    return (
        db.query(SentinelAlert.id)
        .filter(
            SentinelAlert.tenant_id == tenant_id, SentinelAlert.source == source,
            SentinelAlert.related_signal_id == related_signal_id, SentinelAlert.resolved_at.is_(None),
        )
        .first()
        is not None
    )


def _new_ref() -> str:
    return f"SA-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"


def generate_enterprise_alerts(db: Session, tenant_id: str) -> list[dict]:
    from app.models.sentinel_orchestration import ClinicalWatchlistEntry, DigitalTwinFlag, SentinelRiskSignal

    created: list[SentinelAlert] = []

    def _emit(alert: SentinelAlert) -> None:
        db.add(alert)
        created.append(alert)

    for signal in db.query(SentinelRiskSignal).filter(SentinelRiskSignal.tenant_id == tenant_id, SentinelRiskSignal.resolved_at.is_(None)).all():
        if _already_alerted(db, tenant_id, "risk_monitor", signal.id):
            continue
        _emit(SentinelAlert(
            tenant_id=tenant_id, alert_ref=_new_ref(), source="risk_monitor", related_signal_id=signal.id,
            title=f"{signal.signal_type.replace('_', ' ').title()} — {signal.scope}",
            narrative=signal.detail, recommendation=_RECOMMENDATION_BY_SIGNAL.get(signal.signal_type, "Review this recurring pattern."),
            severity=signal.severity,
        ))

    for entry in db.query(ClinicalWatchlistEntry).filter(ClinicalWatchlistEntry.tenant_id == tenant_id, ClinicalWatchlistEntry.status == "active").all():
        if _already_alerted(db, tenant_id, "watchlist", entry.id):
            continue
        severity = "critical" if entry.risk_score >= 0.8 else "high" if entry.risk_score >= 0.5 else "medium"
        _emit(SentinelAlert(
            tenant_id=tenant_id, alert_ref=_new_ref(), source="watchlist", related_signal_id=entry.id,
            title=f"{entry.entity_type.replace('_', ' ').title()} watchlist: {entry.entity_value}",
            narrative=entry.reason, recommendation=f"Review {entry.entity_value} for sustained risk before its next use.",
            severity=severity,
        ))

    for flag in db.query(DigitalTwinFlag).filter(
        DigitalTwinFlag.tenant_id == tenant_id, DigitalTwinFlag.resolved_at.is_(None),
        DigitalTwinFlag.tier.in_([TWIN_TIER_CRITICAL, TWIN_TIER_ESCALATION]),
    ).all():
        if _already_alerted(db, tenant_id, "digital_twin", flag.id):
            continue
        _emit(SentinelAlert(
            tenant_id=tenant_id, alert_ref=_new_ref(), source="digital_twin", related_signal_id=flag.id,
            title=f"Digital Twin {flag.tier} — {flag.instrument_type}",
            narrative=flag.reason,
            recommendation="Review this instrument's Digital Twin before its next scheduled use."
                           if flag.tier == TWIN_TIER_CRITICAL else "Escalate for supervisor/clinical engineering review before further use.",
            severity="high" if flag.tier == TWIN_TIER_CRITICAL else "critical",
        ))

    db.commit()
    for row in created:
        db.refresh(row)

    return list_alerts(db, tenant_id)


def list_alerts(db: Session, tenant_id: str, *, severity: str = "", unresolved_only: bool = True) -> list[dict]:
    q = db.query(SentinelAlert).filter(SentinelAlert.tenant_id == tenant_id)
    if unresolved_only:
        q = q.filter(SentinelAlert.resolved_at.is_(None))
    if severity:
        q = q.filter(SentinelAlert.severity == severity)
    rows = q.order_by(SentinelAlert.created_at.desc()).all()
    return [_row_to_dict(r) for r in rows]


def acknowledge_alert(db: Session, tenant_id: str, alert_id: int, *, acknowledged_by: str) -> dict | None:
    row = db.query(SentinelAlert).filter(SentinelAlert.id == alert_id, SentinelAlert.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.acknowledged = True
    row.acknowledged_by = acknowledged_by
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def resolve_alert(db: Session, tenant_id: str, alert_id: int) -> dict | None:
    row = db.query(SentinelAlert).filter(SentinelAlert.id == alert_id, SentinelAlert.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
