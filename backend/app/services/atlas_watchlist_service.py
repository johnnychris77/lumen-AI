"""v3.1 — Project Atlas, Section 4: Enterprise Watchlists.

`EnterpriseWatchlistEntry` is system_id-scoped (spans tenant_ids), distinct
from Sentinel's tenant-scoped `ClinicalWatchlistEntry`. Risk-direction
entries (hospitals, instrument families, manufacturers, repair/reclean
facilities) reuse the same count-based idiom Sentinel already established;
improvement-direction entries (knowledge growth, fastest improvement) are
a genuinely new, positive-trend semantic this codebase didn't have before —
kept in the same table via an explicit `direction` field rather than
conflated into a risk score.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.atlas_enterprise import (
    DIRECTION_IMPROVEMENT,
    DIRECTION_RISK,
    ENTERPRISE_WATCHLIST_EMERGING_TREND,
    ENTERPRISE_WATCHLIST_FACILITY_RECLEAN,
    ENTERPRISE_WATCHLIST_FACILITY_REPAIR,
    ENTERPRISE_WATCHLIST_FASTEST_IMPROVEMENT,
    ENTERPRISE_WATCHLIST_HOSPITAL,
    ENTERPRISE_WATCHLIST_INSTRUMENT_FAMILY,
    ENTERPRISE_WATCHLIST_KNOWLEDGE_GROWTH,
    ENTERPRISE_WATCHLIST_MANUFACTURER,
    EnterpriseWatchlistEntry,
    FacilityIntelligenceSnapshot,
)
from app.models.baseline_library import BaselineLibraryEntry
from app.models.inspection_finding import InspectionFinding
from app.models.knowledge import KnowledgeArticle
from app.models.or_connect import RepairRequest
from app.services.instrument_anatomy import resolve_family
from app.services.sentinel_risk_monitor_service import list_open_signals

_LOOKBACK_DAYS = 90
_CONDITION_FINDING_TYPES = {"rust", "corrosion", "pitting", "crack", "insulation_damage", "missing_component"}
_THRESHOLD = 3


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _facilities_for_system(db: Session, system_id: str) -> list:
    return (
        db.query(models.EnterpriseFacility)
        .filter(models.EnterpriseFacility.system_id == system_id, models.EnterpriseFacility.is_active.is_(True))
        .all()
    )


def _upsert(db: Session, system_id: str, *, entity_type: str, entity_value: str, direction: str, score: float, reason: str) -> EnterpriseWatchlistEntry:
    existing = (
        db.query(EnterpriseWatchlistEntry)
        .filter(
            EnterpriseWatchlistEntry.system_id == system_id, EnterpriseWatchlistEntry.entity_type == entity_type,
            EnterpriseWatchlistEntry.entity_value == entity_value, EnterpriseWatchlistEntry.status == "active",
        )
        .first()
    )
    if existing is not None:
        existing.score = score
        existing.reason = reason
        existing.direction = direction
        existing.updated_at = datetime.now(timezone.utc)
        return existing
    row = EnterpriseWatchlistEntry(system_id=system_id, entity_type=entity_type, entity_value=entity_value, direction=direction, score=score, reason=reason)
    db.add(row)
    return row


def refresh_enterprise_watchlists(db: Session, system_id: str) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    facilities = _facilities_for_system(db, system_id)
    touched: list[EnterpriseWatchlistEntry] = []

    # Highest-Risk Hospitals — from the latest persisted FacilityIntelligenceSnapshot.
    for f in facilities:
        snapshot = (
            db.query(FacilityIntelligenceSnapshot)
            .filter(FacilityIntelligenceSnapshot.system_id == system_id, FacilityIntelligenceSnapshot.facility_id == f.facility_id)
            .order_by(FacilityIntelligenceSnapshot.id.desc())
            .first()
        )
        if snapshot is not None and snapshot.risk_score is not None and snapshot.risk_score >= 60:
            touched.append(_upsert(
                db, system_id, entity_type=ENTERPRISE_WATCHLIST_HOSPITAL, entity_value=f.facility_name, direction=DIRECTION_RISK,
                score=snapshot.risk_score / 100, reason=f"Enterprise risk score {snapshot.risk_score}/100.",
            ))

    # Highest-Risk Instrument Families and Manufacturers — cross-tenant aggregation.
    family_counts: dict[str, int] = defaultdict(int)
    for f in facilities:
        findings = (
            db.query(InspectionFinding)
            .filter(InspectionFinding.tenant_id == f.tenant_id, InspectionFinding.created_at >= since)
            .all()
        )
        for finding in findings:
            if finding.finding_type in _CONDITION_FINDING_TYPES:
                family_counts[resolve_family(finding.instrument_type)] += 1
    for family, count in family_counts.items():
        if count >= _THRESHOLD:
            touched.append(_upsert(
                db, system_id, entity_type=ENTERPRISE_WATCHLIST_INSTRUMENT_FAMILY, entity_value=family, direction=DIRECTION_RISK,
                score=round(min(1.0, count / 30), 3), reason=f"{count} condition findings on {family} across the system in the past {_LOOKBACK_DAYS} days.",
            ))

    manufacturer_deprecated: dict[str, int] = defaultdict(int)
    for entry in db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.approval_status == "deprecated").all():
        manufacturer_deprecated[entry.manufacturer_name] += 1
    for manufacturer, count in manufacturer_deprecated.items():
        touched.append(_upsert(
            db, system_id, entity_type=ENTERPRISE_WATCHLIST_MANUFACTURER, entity_value=manufacturer, direction=DIRECTION_RISK,
            score=round(min(1.0, count / 5), 3), reason=f"{count} deprecated baseline(s) on record for {manufacturer}.",
        ))

    # High Repair / High Reclean Facilities.
    for f in facilities:
        repair_count = db.query(RepairRequest).filter(RepairRequest.tenant_id == f.tenant_id, RepairRequest.created_at >= since).count()
        if repair_count >= _THRESHOLD:
            touched.append(_upsert(
                db, system_id, entity_type=ENTERPRISE_WATCHLIST_FACILITY_REPAIR, entity_value=f.facility_name, direction=DIRECTION_RISK,
                score=round(min(1.0, repair_count / 15), 3), reason=f"{repair_count} repair referrals in the past {_LOOKBACK_DAYS} days.",
            ))
        reclean_count = (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == f.tenant_id, models.Inspection.created_at >= since, models.Inspection.disposition == "REPROCESS")
            .count()
        )
        if reclean_count >= _THRESHOLD:
            touched.append(_upsert(
                db, system_id, entity_type=ENTERPRISE_WATCHLIST_FACILITY_RECLEAN, entity_value=f.facility_name, direction=DIRECTION_RISK,
                score=round(min(1.0, reclean_count / 15), 3), reason=f"{reclean_count} reprocess dispositions in the past {_LOOKBACK_DAYS} days.",
            ))

    # Highest Knowledge Growth (improvement direction).
    for f in facilities:
        article_count = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == f.tenant_id, KnowledgeArticle.created_at >= since).count()
        if article_count >= 1:
            touched.append(_upsert(
                db, system_id, entity_type=ENTERPRISE_WATCHLIST_KNOWLEDGE_GROWTH, entity_value=f.facility_name, direction=DIRECTION_IMPROVEMENT,
                score=round(min(1.0, article_count / 10), 3), reason=f"{article_count} new knowledge articles authored in the past {_LOOKBACK_DAYS} days.",
            ))

    # Fastest Improvement — quality_score delta between the two most recent snapshots.
    for f in facilities:
        snapshots = (
            db.query(FacilityIntelligenceSnapshot)
            .filter(FacilityIntelligenceSnapshot.system_id == system_id, FacilityIntelligenceSnapshot.facility_id == f.facility_id)
            .order_by(FacilityIntelligenceSnapshot.id.desc())
            .limit(2)
            .all()
        )
        if len(snapshots) == 2 and snapshots[0].quality_score is not None and snapshots[1].quality_score is not None:
            delta = snapshots[0].quality_score - snapshots[1].quality_score
            if delta >= 5:
                touched.append(_upsert(
                    db, system_id, entity_type=ENTERPRISE_WATCHLIST_FASTEST_IMPROVEMENT, entity_value=f.facility_name, direction=DIRECTION_IMPROVEMENT,
                    score=round(min(1.0, delta / 30), 3), reason=f"Quality score improved by {round(delta, 1)} points since the prior snapshot.",
                ))

    # Emerging Trends — a Sentinel risk signal type recurring across >=2 facilities.
    signal_type_facilities: dict[str, set[str]] = defaultdict(set)
    for f in facilities:
        for signal in list_open_signals(db, f.tenant_id):
            signal_type_facilities[signal["signal_type"]].add(f.facility_name)
    for signal_type, facility_names in signal_type_facilities.items():
        if len(facility_names) >= 2:
            touched.append(_upsert(
                db, system_id, entity_type=ENTERPRISE_WATCHLIST_EMERGING_TREND, entity_value=signal_type, direction=DIRECTION_RISK,
                score=round(min(1.0, len(facility_names) / len(facilities)), 3) if facilities else 0.0,
                reason=f"{signal_type.replace('_', ' ')} detected across {len(facility_names)} facilities: {', '.join(sorted(facility_names))}.",
            ))

    db.commit()
    for row in touched:
        db.refresh(row)

    return list_active_watchlist(db, system_id)


def list_active_watchlist(db: Session, system_id: str, *, entity_type: str = "") -> list[dict]:
    q = db.query(EnterpriseWatchlistEntry).filter(EnterpriseWatchlistEntry.system_id == system_id, EnterpriseWatchlistEntry.status == "active")
    if entity_type:
        q = q.filter(EnterpriseWatchlistEntry.entity_type == entity_type)
    rows = q.order_by(EnterpriseWatchlistEntry.score.desc()).all()
    return [_row_to_dict(r) for r in rows]


def resolve_watchlist_entry(db: Session, system_id: str, entry_id: int) -> dict | None:
    row = db.query(EnterpriseWatchlistEntry).filter(EnterpriseWatchlistEntry.id == entry_id, EnterpriseWatchlistEntry.system_id == system_id).first()
    if row is None:
        return None
    row.status = "resolved"
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
