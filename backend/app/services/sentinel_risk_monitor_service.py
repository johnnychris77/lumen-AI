"""v3.0 — Project Sentinel, Section 2: Continuous Risk Monitor.

Reuses `capa_suggestion_service`'s recurrence idiom (count >= threshold
within a lookback window) rather than inventing a fourth "is this
recurring?" algorithm — the same `_REPEAT_THRESHOLD`/`_LOOKBACK_DAYS`
constants, applied to the sprint's specific named signal types.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.disposition_override import DispositionOverride
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import RepairRequest
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
    SentinelRiskSignal,
)
from app.services.instrument_anatomy import resolve_family

_REPEAT_THRESHOLD = 3
_LOOKBACK_DAYS = 90

_DAMAGE_TYPES = {"pitting", "crack", "wear", "insulation_damage", "missing_component"}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _severity_for(count: int) -> str:
    if count >= _REPEAT_THRESHOLD * 3:
        return "critical"
    if count >= _REPEAT_THRESHOLD * 2:
        return "high"
    return "medium"


def _already_open(db: Session, tenant_id: str, signal_type: str, scope: str) -> SentinelRiskSignal | None:
    return (
        db.query(SentinelRiskSignal)
        .filter(
            SentinelRiskSignal.tenant_id == tenant_id, SentinelRiskSignal.signal_type == signal_type,
            SentinelRiskSignal.scope == scope, SentinelRiskSignal.resolved_at.is_(None),
        )
        .first()
    )


def _upsert_signal(db: Session, tenant_id: str, *, signal_type: str, scope: str, occurrences: int, detail: str) -> SentinelRiskSignal:
    existing = _already_open(db, tenant_id, signal_type, scope)
    if existing is not None:
        existing.occurrences = occurrences
        existing.severity = _severity_for(occurrences)
        existing.detail = detail
        return existing
    row = SentinelRiskSignal(
        tenant_id=tenant_id, signal_type=signal_type, scope=scope, occurrences=occurrences,
        window_days=_LOOKBACK_DAYS, severity=_severity_for(occurrences), detail=detail,
    )
    db.add(row)
    return row


def detect_risk_signals(db: Session, tenant_id: str) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    findings = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since)
        .all()
    )

    touched: list[SentinelRiskSignal] = []

    def _emit_finding_signal(signal_type: str, finding_type: str) -> None:
        by_zone: dict[str, int] = defaultdict(int)
        for f in findings:
            if f.finding_type == finding_type:
                by_zone[f.zone or "unspecified region"] += 1
        for zone, count in by_zone.items():
            if count >= _REPEAT_THRESHOLD:
                touched.append(_upsert_signal(
                    db, tenant_id, signal_type=signal_type, scope=zone, occurrences=count,
                    detail=f"{count} {finding_type} findings in {zone} over the past {_LOOKBACK_DAYS} days.",
                ))

    _emit_finding_signal(SIGNAL_REPEATED_BLOOD, "blood")
    _emit_finding_signal(SIGNAL_REPEATED_RUST, "rust")
    _emit_finding_signal(SIGNAL_REPEATED_BONE, "bone")
    _emit_finding_signal(SIGNAL_REPEATED_CORROSION, "corrosion")

    damage_by_family: dict[str, int] = defaultdict(int)
    for f in findings:
        if f.finding_type in _DAMAGE_TYPES:
            damage_by_family[resolve_family(f.instrument_type)] += 1
    for family, count in damage_by_family.items():
        if count >= _REPEAT_THRESHOLD:
            touched.append(_upsert_signal(
                db, tenant_id, signal_type=SIGNAL_REPEATED_DAMAGE, scope=family, occurrences=count,
                detail=f"{count} structural damage findings on {family} over the past {_LOOKBACK_DAYS} days.",
            ))

    insp_rows = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id, models.Inspection.created_at >= since,
            models.Inspection.has_image.is_(True), models.Inspection.technician.isnot(None),
        )
        .all()
    )
    low_confidence_by_tech: dict[str, int] = defaultdict(int)
    missing_coverage_by_tech: dict[str, int] = defaultdict(int)
    for r in insp_rows:
        if r.confidence is not None and r.confidence < 0.7:
            low_confidence_by_tech[r.technician] += 1
        if r.coverage_pct is not None and r.coverage_pct < 75:
            missing_coverage_by_tech[r.technician] += 1
    for technician, count in low_confidence_by_tech.items():
        if count >= _REPEAT_THRESHOLD:
            touched.append(_upsert_signal(
                db, tenant_id, signal_type=SIGNAL_REPEATED_LOW_CONFIDENCE, scope=technician, occurrences=count,
                detail=f"{count} low-confidence inspections by {technician} over the past {_LOOKBACK_DAYS} days.",
            ))
    for technician, count in missing_coverage_by_tech.items():
        if count >= _REPEAT_THRESHOLD:
            touched.append(_upsert_signal(
                db, tenant_id, signal_type=SIGNAL_REPEATED_MISSING_COVERAGE, scope=technician, occurrences=count,
                detail=f"{count} incomplete-coverage inspections by {technician} over the past {_LOOKBACK_DAYS} days.",
            ))

    override_rows = (
        db.query(DispositionOverride)
        .filter(DispositionOverride.tenant_id == tenant_id, DispositionOverride.created_at >= since)
        .all()
    )
    insp_by_id = {i.id: i for i in db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).all()}
    overrides_by_instrument_type: dict[str, int] = defaultdict(int)
    for o in override_rows:
        insp = insp_by_id.get(o.inspection_id)
        if insp is not None:
            overrides_by_instrument_type[insp.instrument_type] += 1
    for instrument_type, count in overrides_by_instrument_type.items():
        if count >= _REPEAT_THRESHOLD:
            touched.append(_upsert_signal(
                db, tenant_id, signal_type=SIGNAL_REPEATED_SUPERVISOR_OVERRIDES, scope=instrument_type, occurrences=count,
                detail=f"{count} supervisor overrides on {instrument_type} over the past {_LOOKBACK_DAYS} days.",
            ))

    repair_rows = (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since)
        .all()
    )
    repairs_by_instrument: dict[str, int] = defaultdict(int)
    for r in repair_rows:
        insp = insp_by_id.get(r.inspection_id)
        key = insp.instrument_type if insp is not None else (r.instrument_identity or "unknown")
        repairs_by_instrument[key] += 1
    for instrument, count in repairs_by_instrument.items():
        if count >= _REPEAT_THRESHOLD:
            touched.append(_upsert_signal(
                db, tenant_id, signal_type=SIGNAL_REPEATED_REPAIR_REFERRALS, scope=instrument, occurrences=count,
                detail=f"{count} repair referrals for {instrument} over the past {_LOOKBACK_DAYS} days.",
            ))

    db.commit()
    for row in touched:
        db.refresh(row)

    return list_open_signals(db, tenant_id)


def list_open_signals(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(SentinelRiskSignal)
        .filter(SentinelRiskSignal.tenant_id == tenant_id, SentinelRiskSignal.resolved_at.is_(None))
        .order_by(SentinelRiskSignal.occurrences.desc())
        .all()
    )
    return [_row_to_dict(r) for r in rows]


def resolve_signal(db: Session, tenant_id: str, signal_id: int) -> dict | None:
    row = db.query(SentinelRiskSignal).filter(SentinelRiskSignal.id == signal_id, SentinelRiskSignal.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
