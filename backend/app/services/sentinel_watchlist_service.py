"""v3.0 — Project Sentinel, Section 3: Clinical Watchlists.

Eight dynamic, entity-scoped watchlists. Anatomy reuses
`anatomy_risk_service.anatomy_risk_dashboard` rather than re-deriving zone
rankings; the rest apply the same count->=threshold-in-window idiom as
`capa_suggestion_service`/`sentinel_risk_monitor_service` to real,
already-tracked entities (instruments, trays, manufacturers, vendors,
service lines, facilities, instrument families) rather than a fabricated
generic risk model.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.baseline_library import BaselineLibraryEntry
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import CaseRiskAlert, RepairRequest, SurgicalCase, VendorTray
from app.models.sentinel_orchestration import (
    WATCHLIST_ANATOMY,
    WATCHLIST_FACILITY,
    WATCHLIST_INSTRUMENT,
    WATCHLIST_INSTRUMENT_FAMILY,
    WATCHLIST_MANUFACTURER,
    WATCHLIST_SERVICE_LINE,
    WATCHLIST_TRAY,
    WATCHLIST_VENDOR,
    ClinicalWatchlistEntry,
)
from app.services.anatomy_risk_service import anatomy_risk_dashboard
from app.services.instrument_anatomy import resolve_family

_THRESHOLD = 3
_LOOKBACK_DAYS = 90
_CONDITION_TYPES = {"rust", "corrosion", "pitting", "crack", "insulation_damage", "missing_component"}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _upsert(db: Session, tenant_id: str, *, entity_type: str, entity_value: str, risk_score: float, reason: str) -> ClinicalWatchlistEntry:
    existing = (
        db.query(ClinicalWatchlistEntry)
        .filter(
            ClinicalWatchlistEntry.tenant_id == tenant_id, ClinicalWatchlistEntry.entity_type == entity_type,
            ClinicalWatchlistEntry.entity_value == entity_value, ClinicalWatchlistEntry.status == "active",
        )
        .first()
    )
    if existing is not None:
        existing.risk_score = risk_score
        existing.reason = reason
        existing.updated_at = datetime.now(timezone.utc)
        return existing
    row = ClinicalWatchlistEntry(tenant_id=tenant_id, entity_type=entity_type, entity_value=entity_value, risk_score=risk_score, reason=reason)
    db.add(row)
    return row


def _normalize(count: int, ceiling: int = 15) -> float:
    return round(min(1.0, count / ceiling), 3)


def refresh_watchlists(db: Session, tenant_id: str) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    touched: list[ClinicalWatchlistEntry] = []

    # High-Risk Anatomy — reuse the existing anatomy risk dashboard.
    anatomy = anatomy_risk_dashboard(db, tenant_id, days=_LOOKBACK_DAYS)
    for zone_row in anatomy["highest_risk_anatomy_zones"]:
        if zone_row["count"] >= _THRESHOLD:
            touched.append(_upsert(
                db, tenant_id, entity_type=WATCHLIST_ANATOMY, entity_value=zone_row["zone"],
                risk_score=_normalize(zone_row["count"]),
                reason=f"{zone_row['count']} findings in {zone_row['zone']} over the past {_LOOKBACK_DAYS} days.",
            ))

    findings = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since)
        .all()
    )
    insp_by_id = {i.id: i for i in db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).all()}

    # High-Risk Instruments — condition findings by specific instrument_type.
    by_instrument_type: dict[str, int] = defaultdict(int)
    for f in findings:
        if f.finding_type in _CONDITION_TYPES:
            insp = insp_by_id.get(f.inspection_id)
            if insp is not None:
                by_instrument_type[insp.instrument_type] += 1
    for instrument_type, count in by_instrument_type.items():
        if count >= _THRESHOLD:
            touched.append(_upsert(
                db, tenant_id, entity_type=WATCHLIST_INSTRUMENT, entity_value=instrument_type,
                risk_score=_normalize(count),
                reason=f"{count} condition findings on {instrument_type} over the past {_LOOKBACK_DAYS} days.",
            ))

    # High-Risk Instrument Families.
    by_family: dict[str, int] = defaultdict(int)
    for f in findings:
        if f.finding_type in _CONDITION_TYPES:
            by_family[resolve_family(f.instrument_type)] += 1
    for family, count in by_family.items():
        if count >= _THRESHOLD:
            touched.append(_upsert(
                db, tenant_id, entity_type=WATCHLIST_INSTRUMENT_FAMILY, entity_value=family,
                risk_score=_normalize(count),
                reason=f"{count} condition findings on the {family} family over the past {_LOOKBACK_DAYS} days.",
            ))

    # High-Risk Manufacturers — deprecated baselines are a real, honest signal.
    manufacturer_deprecated: dict[str, int] = defaultdict(int)
    for entry in db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.approval_status == "deprecated").all():
        manufacturer_deprecated[entry.manufacturer_name] += 1
    for manufacturer, count in manufacturer_deprecated.items():
        if count >= 1:
            touched.append(_upsert(
                db, tenant_id, entity_type=WATCHLIST_MANUFACTURER, entity_value=manufacturer,
                risk_score=_normalize(count, ceiling=5),
                reason=f"{count} deprecated baseline(s) on record for {manufacturer}.",
            ))

    # High-Risk Vendors, Trays, Service Lines, Facilities — from OR Connect.
    repair_rows = db.query(RepairRequest).filter(RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since).all()
    by_vendor: dict[str, int] = defaultdict(int)
    for r in repair_rows:
        if r.vendor_name:
            by_vendor[r.vendor_name] += 1
    for vendor, count in by_vendor.items():
        if count >= _THRESHOLD:
            touched.append(_upsert(
                db, tenant_id, entity_type=WATCHLIST_VENDOR, entity_value=vendor,
                risk_score=_normalize(count), reason=f"{count} repair referrals for {vendor} over the past {_LOOKBACK_DAYS} days.",
            ))

    tray_rows = db.query(VendorTray).filter(VendorTray.tenant_id == tenant_id, VendorTray.created_at >= since).all()
    by_tray_name: dict[str, int] = defaultdict(int)
    for t in tray_rows:
        if t.replacement_requested:
            by_tray_name[t.tray_name] += 1
    for tray_name, count in by_tray_name.items():
        if count >= 2:
            touched.append(_upsert(
                db, tenant_id, entity_type=WATCHLIST_TRAY, entity_value=tray_name,
                risk_score=_normalize(count, ceiling=5),
                reason=f"{count} replacement requests for '{tray_name}' trays over the past {_LOOKBACK_DAYS} days.",
            ))

    case_ids_by_service_line: dict[str, set[int]] = defaultdict(set)
    case_ids_by_facility: dict[str, set[int]] = defaultdict(set)
    for c in db.query(SurgicalCase).filter(SurgicalCase.tenant_id == tenant_id, SurgicalCase.created_at >= since).all():
        if c.service_line:
            case_ids_by_service_line[c.service_line].add(c.id)
        if c.facility_name:
            case_ids_by_facility[c.facility_name].add(c.id)

    risk_alerts = (
        db.query(CaseRiskAlert)
        .filter(CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.created_at >= since, CaseRiskAlert.resolved_at.is_(None))
        .all()
    )
    alerts_by_case: dict[int, int] = defaultdict(int)
    for a in risk_alerts:
        alerts_by_case[a.case_id] += 1

    for service_line, case_ids in case_ids_by_service_line.items():
        count = sum(alerts_by_case.get(cid, 0) for cid in case_ids)
        if count >= _THRESHOLD:
            touched.append(_upsert(
                db, tenant_id, entity_type=WATCHLIST_SERVICE_LINE, entity_value=service_line,
                risk_score=_normalize(count),
                reason=f"{count} open operational risk alerts across {service_line} cases in the past {_LOOKBACK_DAYS} days.",
            ))
    for facility, case_ids in case_ids_by_facility.items():
        count = sum(alerts_by_case.get(cid, 0) for cid in case_ids)
        if count >= _THRESHOLD:
            touched.append(_upsert(
                db, tenant_id, entity_type=WATCHLIST_FACILITY, entity_value=facility,
                risk_score=_normalize(count),
                reason=f"{count} open operational risk alerts across {facility} cases in the past {_LOOKBACK_DAYS} days.",
            ))

    db.commit()
    for row in touched:
        db.refresh(row)

    return list_active_watchlist(db, tenant_id)


def list_active_watchlist(db: Session, tenant_id: str, *, entity_type: str = "") -> list[dict]:
    q = db.query(ClinicalWatchlistEntry).filter(ClinicalWatchlistEntry.tenant_id == tenant_id, ClinicalWatchlistEntry.status == "active")
    if entity_type:
        q = q.filter(ClinicalWatchlistEntry.entity_type == entity_type)
    rows = q.order_by(ClinicalWatchlistEntry.risk_score.desc()).all()
    return [_row_to_dict(r) for r in rows]


def resolve_watchlist_entry(db: Session, tenant_id: str, entry_id: int) -> dict | None:
    row = db.query(ClinicalWatchlistEntry).filter(ClinicalWatchlistEntry.id == entry_id, ClinicalWatchlistEntry.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.status = "resolved"
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
