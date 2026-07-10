"""v3.4 — Project Horizon, Section 6: Emerging Trend Detection.

Detects a pattern recurring across `EARLY_WARNING_K` (imported from
`global_aggregation_job.py`, never redefined) or more *unrelated*
organizations — distinct from Atlas's `ENTERPRISE_WATCHLIST_EMERGING_TREND`
(`atlas_watchlist_service.py`), which only recurs within one health
system's own facilities. Every detected trend is written to every
enrolled organization's notification feed
(`notified_tenant_ids_json`) — "Notify participating organizations" is a
literal, queryable field, not just an implicit side effect.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.federated_horizon import (
    TREND_EMERGING_INSPECTION_CHALLENGE,
    TREND_MANUFACTURER_QUALITY_TREND,
    TREND_NEW_CONTAMINATION_LOCATION,
    TREND_NEW_CORROSION_PATTERN,
    TREND_UNEXPECTED_ANATOMY_RISK,
    EmergingTrendAlert,
)
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import RepairRequest
from app.services import horizon_participation_service
from app.services.global_aggregation_job import EARLY_WARNING_K

_LOOKBACK_DAYS = 90
_CONTAMINATION_FINDING_TYPES = {"blood", "bone", "tissue", "debris", "other_organic_residue"}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _already_monitoring(db: Session, trend_type: str, description: str) -> bool:
    return (
        db.query(EmergingTrendAlert.id)
        .filter(EmergingTrendAlert.trend_type == trend_type, EmergingTrendAlert.description == description, EmergingTrendAlert.status != "resolved")
        .first()
        is not None
    )


def _notify_all_enrolled(db: Session, row: EmergingTrendAlert) -> None:
    tenant_ids = horizon_participation_service.list_enrolled_tenant_ids(db)
    row.notified_tenant_ids_json = json.dumps(tenant_ids)


def _emit(db: Session, created: list, *, trend_type: str, description: str, evidence: list[dict], tenant_count: int, severity: str) -> None:
    if _already_monitoring(db, trend_type, description):
        return
    row = EmergingTrendAlert(
        trend_type=trend_type, description=description, evidence_json=json.dumps(evidence),
        tenant_count=tenant_count, severity=severity,
    )
    _notify_all_enrolled(db, row)
    db.add(row)
    created.append(row)


def detect_emerging_trends(db: Session) -> list[dict]:
    tenant_ids = horizon_participation_service.list_enrolled_tenant_ids(db)
    created: list[EmergingTrendAlert] = []
    if len(tenant_ids) < EARLY_WARNING_K:
        db.commit()
        return list_emerging_trends(db)

    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)

    # New corrosion pattern — a specific instrument_type showing corrosion across >=K tenants.
    corrosion_by_instrument: dict[str, set[str]] = defaultdict(set)
    rows = (
        db.query(InspectionFinding.tenant_id, InspectionFinding.instrument_type)
        .filter(InspectionFinding.tenant_id.in_(tenant_ids), InspectionFinding.finding_type == "corrosion", InspectionFinding.created_at >= since)
        .all()
    )
    for tenant_id, instrument_type in rows:
        corrosion_by_instrument[instrument_type].add(tenant_id)
    for instrument_type, tenants in corrosion_by_instrument.items():
        if len(tenants) >= EARLY_WARNING_K:
            _emit(
                db, created, trend_type=TREND_NEW_CORROSION_PATTERN,
                description=f"Corrosion findings on {instrument_type} reported across {len(tenants)} organizations in the past {_LOOKBACK_DAYS} days.",
                evidence=[{"factor": "instrument_type", "value": instrument_type}, {"factor": "organization_count", "value": len(tenants)}],
                tenant_count=len(tenants), severity="high" if len(tenants) >= EARLY_WARNING_K * 2 else "medium",
            )

    # New contamination location — a contamination finding type in a zone across >=K tenants.
    contamination_by_zone: dict[tuple[str, str], set[str]] = defaultdict(set)
    rows = (
        db.query(InspectionFinding.tenant_id, InspectionFinding.finding_type, InspectionFinding.zone)
        .filter(InspectionFinding.tenant_id.in_(tenant_ids), InspectionFinding.finding_type.in_(_CONTAMINATION_FINDING_TYPES), InspectionFinding.zone != "", InspectionFinding.created_at >= since)
        .all()
    )
    for tenant_id, finding_type, zone in rows:
        contamination_by_zone[(finding_type, zone)].add(tenant_id)
    for (finding_type, zone), tenants in contamination_by_zone.items():
        if len(tenants) >= EARLY_WARNING_K:
            _emit(
                db, created, trend_type=TREND_NEW_CONTAMINATION_LOCATION,
                description=f"{finding_type.replace('_', ' ').title()} contamination in the {zone} zone reported across {len(tenants)} organizations.",
                evidence=[{"factor": "finding_type", "value": finding_type}, {"factor": "zone", "value": zone}, {"factor": "organization_count", "value": len(tenants)}],
                tenant_count=len(tenants), severity="medium",
            )

    # Unexpected anatomy risk — a zone with >=3 distinct finding types across >=K tenants.
    zone_finding_diversity: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    rows = (
        db.query(InspectionFinding.tenant_id, InspectionFinding.zone, InspectionFinding.finding_type)
        .filter(InspectionFinding.tenant_id.in_(tenant_ids), InspectionFinding.zone != "", InspectionFinding.created_at >= since)
        .all()
    )
    for tenant_id, zone, finding_type in rows:
        zone_finding_diversity[zone][finding_type].add(tenant_id)
    for zone, findings_by_type in zone_finding_diversity.items():
        tenants_involved = set().union(*findings_by_type.values()) if findings_by_type else set()
        if len(findings_by_type) >= 3 and len(tenants_involved) >= EARLY_WARNING_K:
            _emit(
                db, created, trend_type=TREND_UNEXPECTED_ANATOMY_RISK,
                description=f"The {zone} zone shows {len(findings_by_type)} distinct finding types across {len(tenants_involved)} organizations — broader risk than a single finding type would suggest.",
                evidence=[{"factor": "zone", "value": zone}, {"factor": "finding_type_count", "value": len(findings_by_type)}, {"factor": "organization_count", "value": len(tenants_involved)}],
                tenant_count=len(tenants_involved), severity="medium",
            )

    # Manufacturer-specific quality trend — a vendor with repeat repair referrals across >=K tenants.
    repairs_by_vendor: dict[str, set[str]] = defaultdict(set)
    rows = (
        db.query(RepairRequest.tenant_id, RepairRequest.vendor_name)
        .filter(RepairRequest.tenant_id.in_(tenant_ids), RepairRequest.vendor_name != "", RepairRequest.created_at >= since)
        .all()
    )
    for tenant_id, vendor_name in rows:
        repairs_by_vendor[vendor_name].add(tenant_id)
    for vendor_name, tenants in repairs_by_vendor.items():
        if len(tenants) >= EARLY_WARNING_K:
            _emit(
                db, created, trend_type=TREND_MANUFACTURER_QUALITY_TREND,
                description=f"Repair referrals associated with vendor '{vendor_name}' reported across {len(tenants)} organizations.",
                evidence=[{"factor": "vendor_name", "value": vendor_name}, {"factor": "organization_count", "value": len(tenants)}],
                tenant_count=len(tenants), severity="medium",
            )

    # Emerging inspection challenge — coverage declining across >=K tenants relative to the prior window.
    recent_since = datetime.now(timezone.utc) - timedelta(days=30)
    prior_since = recent_since - timedelta(days=30)
    declining_tenants = set()
    for tenant_id in tenant_ids:
        recent = [
            r[0] for r in db.query(Inspection.coverage_pct).filter(
                Inspection.tenant_id == tenant_id, Inspection.created_at >= recent_since, Inspection.coverage_pct.isnot(None),
            ).all()
        ]
        prior = [
            r[0] for r in db.query(Inspection.coverage_pct).filter(
                Inspection.tenant_id == tenant_id, Inspection.created_at >= prior_since, Inspection.created_at < recent_since, Inspection.coverage_pct.isnot(None),
            ).all()
        ]
        if recent and prior and (sum(recent) / len(recent)) < (sum(prior) / len(prior)) - 5:
            declining_tenants.add(tenant_id)
    if len(declining_tenants) >= EARLY_WARNING_K:
        _emit(
            db, created, trend_type=TREND_EMERGING_INSPECTION_CHALLENGE,
            description=f"Inspection coverage is declining month-over-month across {len(declining_tenants)} organizations.",
            evidence=[{"factor": "organization_count", "value": len(declining_tenants)}],
            tenant_count=len(declining_tenants), severity="medium",
        )

    db.commit()
    for row in created:
        db.refresh(row)
    return list_emerging_trends(db)


def list_emerging_trends(db: Session, *, tenant_id: str = "", status: str = "") -> list[dict]:
    q = db.query(EmergingTrendAlert)
    if status:
        q = q.filter(EmergingTrendAlert.status == status)
    rows = q.order_by(EmergingTrendAlert.id.desc()).all()
    results = [_row_to_dict(r) for r in rows]
    if tenant_id:
        results = [r for r in results if tenant_id in json.loads(r["notified_tenant_ids_json"])]
    return results


def acknowledge_trend(db: Session, tenant_id: str, trend_id: int) -> dict | None:
    row = db.query(EmergingTrendAlert).filter(EmergingTrendAlert.id == trend_id).first()
    if row is None:
        return None
    acknowledged = set(json.loads(row.acknowledged_tenant_ids_json))
    acknowledged.add(tenant_id)
    row.acknowledged_tenant_ids_json = json.dumps(sorted(acknowledged))
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
