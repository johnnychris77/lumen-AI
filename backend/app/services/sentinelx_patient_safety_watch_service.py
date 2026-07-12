"""Project Sentinel-X, Section 5: Patient Safety Watch.

Proactive alerts fired from real, repeated patterns across already-
persisted `SentinelXRiskAssessment` rows -- never a single event, and
never the pre-existing `SentinelAlert` table (Project Sentinel v3.0, a
different system).
"""
from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.sentinelx_risk import RISK_LEVEL_CRITICAL, RISK_LEVEL_HIGH, SentinelXPatientSafetyAlert, SentinelXRiskAssessment

_MIN_REPEAT = 2
_CONTAMINATION_FINDINGS = {"blood", "bone", "tissue", "other_organic_residue", "debris"}


def _create_alert(db: Session, tenant_id: str, *, alert_type: str, instrument_identity: str, severity: str, narrative: str, evidence: dict) -> SentinelXPatientSafetyAlert:
    row = SentinelXPatientSafetyAlert(
        tenant_id=tenant_id, alert_type=alert_type, instrument_identity=instrument_identity,
        severity=severity, narrative=narrative, evidence_json=json.dumps(evidence),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def scan_for_alerts(db: Session, tenant_id: str) -> list[SentinelXPatientSafetyAlert]:
    """Section 5: scan real assessment history and fire (persist) any newly
    qualifying proactive alert. Idempotent-ish per call -- callers should
    run this periodically, not on every read."""
    assessments = db.query(SentinelXRiskAssessment).filter(SentinelXRiskAssessment.tenant_id == tenant_id).all()

    by_instrument_finding: dict[tuple, int] = defaultdict(int)
    by_instrument: dict[str, list[SentinelXRiskAssessment]] = defaultdict(list)
    for a in assessments:
        by_instrument_finding[(a.instrument_identity, a.finding_type)] += 1
        by_instrument[a.instrument_identity].append(a)

    fired: list[SentinelXPatientSafetyAlert] = []

    for (instrument, finding_type), count in by_instrument_finding.items():
        if count < _MIN_REPEAT or not finding_type:
            continue
        if finding_type in _CONTAMINATION_FINDINGS:
            fired.append(_create_alert(
                db, tenant_id, alert_type="repeat_contamination", instrument_identity=instrument, severity="high",
                narrative=f"Repeated {finding_type} findings ({count}) detected for this instrument.",
                evidence={"finding_type": finding_type, "occurrence_count": count},
            ))
        elif finding_type in ("corrosion", "rust"):
            fired.append(_create_alert(
                db, tenant_id, alert_type="repeat_corrosion", instrument_identity=instrument, severity="high",
                narrative=f"Repeated {finding_type} findings ({count}) detected for this instrument.",
                evidence={"finding_type": finding_type, "occurrence_count": count},
            ))

    for instrument, rows in by_instrument.items():
        anatomy_zones = {r.anatomy_zone for r in rows if r.anatomy_zone}
        for zone in anatomy_zones:
            zone_count = sum(1 for r in rows if r.anatomy_zone == zone)
            if zone_count >= _MIN_REPEAT:
                fired.append(_create_alert(
                    db, tenant_id, alert_type="repeat_anatomy_failure", instrument_identity=instrument, severity="moderate",
                    narrative=f"Repeated findings ({zone_count}) at anatomy zone '{zone}' for this instrument.",
                    evidence={"anatomy_zone": zone, "occurrence_count": zone_count},
                ))

        high_risk_count = sum(1 for r in rows if r.risk_level in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL))
        if high_risk_count >= _MIN_REPEAT:
            fired.append(_create_alert(
                db, tenant_id, alert_type="high_risk_instrument", instrument_identity=instrument, severity="critical",
                narrative=f"This instrument has been assessed as high or critical risk {high_risk_count} times.",
                evidence={"high_risk_assessment_count": high_risk_count},
            ))

        declining = [r for r in rows if r.digital_twin_condition_trend == "declining"]
        if len(declining) >= _MIN_REPEAT:
            fired.append(_create_alert(
                db, tenant_id, alert_type="escalating_digital_twin", instrument_identity=instrument, severity="high",
                narrative="This instrument's Digital Twin has shown a declining condition trend across multiple assessments.",
                evidence={"declining_assessment_count": len(declining)},
            ))

    repair_recurrence_instruments = [
        a.instrument_identity for a in assessments if "repair_recurrence" in json.loads(a.score_breakdown_json or "{}")
    ]
    for instrument, count in {i: repair_recurrence_instruments.count(i) for i in set(repair_recurrence_instruments)}.items():
        if count >= _MIN_REPEAT:
            fired.append(_create_alert(
                db, tenant_id, alert_type="repeat_repair", instrument_identity=instrument, severity="high",
                narrative=f"Repair recurrence contributed to risk scoring {count} times for this instrument.",
                evidence={"occurrence_count": count},
            ))

    return fired


def to_dict(row: SentinelXPatientSafetyAlert) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "alert_type": row.alert_type,
        "instrument_identity": row.instrument_identity,
        "severity": row.severity,
        "narrative": row.narrative,
        "evidence": json.loads(row.evidence_json or "{}"),
        "acknowledged": row.acknowledged,
        "acknowledged_by": row.acknowledged_by,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
    }


def list_alerts(db: Session, tenant_id: str, *, acknowledged: bool | None = None) -> list[dict]:
    q = db.query(SentinelXPatientSafetyAlert).filter(SentinelXPatientSafetyAlert.tenant_id == tenant_id)
    if acknowledged is not None:
        q = q.filter(SentinelXPatientSafetyAlert.acknowledged == acknowledged)
    return [to_dict(r) for r in q.order_by(SentinelXPatientSafetyAlert.created_at.desc()).all()]


def acknowledge_alert(db: Session, tenant_id: str, alert_id: int, *, acknowledged_by: str) -> SentinelXPatientSafetyAlert | None:
    row = db.query(SentinelXPatientSafetyAlert).filter(SentinelXPatientSafetyAlert.id == alert_id, SentinelXPatientSafetyAlert.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.acknowledged = True
    row.acknowledged_by = acknowledged_by
    from datetime import datetime, timezone
    row.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
