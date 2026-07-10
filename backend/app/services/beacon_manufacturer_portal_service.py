"""v3.5 — Project Beacon, Section 2: Manufacturer Intelligence Portal.

`app/routes/manufacturer_portal.py`'s existing `/my-scorecard` etc.
endpoints label a seeded/mock scorecard with the caller's
`X-Manufacturer-ID` but never actually filter any real inspection row by
manufacturer identity (confirmed by reading `vendor_intelligence_engine`
before writing this module). This module is the real-data-filtered
counterpart: every function here resolves a manufacturer's real
instrument population via `RegistryInstrument.manufacturer_name -> udi`
(P15's national instrument registry, `app/models/instrument_registry.py`)
and then joins that UDI set into real `Inspection`/`InspectionFinding`
rows across every tenant — never a fabricated distribution.

Every aggregate here is a network-wide count/rate; no `tenant_id` is ever
included in any response, and any breakdown computed from fewer than
`MIN_FACILITIES` (imported from `network_benchmark_service`, the same
floor P15/Horizon already use) contributing hospitals is suppressed —
consistent with every other cross-tenant intelligence system in this
codebase.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.baseline_library import BaselineLibraryEntry
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.instrument_registry import RegistryInstrument
from app.services.network_benchmark_service import MIN_FACILITIES

_LOOKBACK_DAYS = 90

DISCLAIMER = (
    "LumenAI Manufacturer Intelligence Portal shows only anonymized, aggregate quality "
    "intelligence for a manufacturer's own instrument family. No hospital, patient, or "
    "individual instrument identity is ever disclosed. Findings describe potential "
    "associations only, never causation, and require human review before any action."
)


def _manufacturer_udis(db: Session, manufacturer_id: str) -> list[str]:
    rows = db.query(RegistryInstrument.udi).filter(
        RegistryInstrument.manufacturer_name == manufacturer_id, RegistryInstrument.udi.isnot(None),
    ).all()
    return [r[0] for r in rows if r[0]]


def _manufacturer_inspections(db: Session, manufacturer_id: str):
    udis = _manufacturer_udis(db, manufacturer_id)
    if not udis:
        return []
    return db.query(Inspection).filter(Inspection.instrument_udi.in_(udis)).all()


def approved_baseline_performance(db: Session, manufacturer_id: str) -> list[dict]:
    rows = (
        db.query(BaselineLibraryEntry)
        .filter(BaselineLibraryEntry.manufacturer_name == manufacturer_id, BaselineLibraryEntry.approval_status == "approved")
        .all()
    )
    return [
        {
            "instrument_category": r.instrument_category,
            "model_name": r.model_name,
            "baseline_version": r.baseline_version,
            "baseline_type": r.baseline_type,
            "contributing_facilities": r.contributing_facilities,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        }
        for r in rows
    ]


def anonymized_quality_trends(db: Session, manufacturer_id: str) -> dict:
    """Section 2: 'anonymized quality trends' — network-wide finding-type
    distribution for this manufacturer's instruments, suppressed below
    `MIN_FACILITIES` contributing hospitals."""
    inspections = _manufacturer_inspections(db, manufacturer_id)
    facility_count = len({i.tenant_id for i in inspections})
    if facility_count < MIN_FACILITIES:
        return {"suppressed": True, "reason": "insufficient_contributing_facilities", "facility_count": facility_count}

    insp_ids = [i.id for i in inspections]
    findings = db.query(InspectionFinding).filter(InspectionFinding.inspection_id.in_(insp_ids)).all() if insp_ids else []
    by_type: dict[str, int] = {}
    for f in findings:
        by_type[f.finding_type] = by_type.get(f.finding_type, 0) + 1

    return {
        "suppressed": False,
        "facility_count": facility_count,
        "total_inspections": len(inspections),
        "finding_type_counts": by_type,
    }


def instrument_family_performance(db: Session, manufacturer_id: str) -> dict:
    inspections = _manufacturer_inspections(db, manufacturer_id)
    facility_count = len({i.tenant_id for i in inspections})
    if facility_count < MIN_FACILITIES:
        return {"suppressed": True, "reason": "insufficient_contributing_facilities", "facility_count": facility_count}

    by_family: dict[str, dict] = {}
    for insp in inspections:
        fam = by_family.setdefault(insp.instrument_type, {"total": 0, "stain_detected_count": 0, "risk_scores": []})
        fam["total"] += 1
        if insp.stain_detected:
            fam["stain_detected_count"] += 1
        fam["risk_scores"].append(insp.risk_score)

    result = {}
    for fam, data in by_family.items():
        avg_risk = round(sum(data["risk_scores"]) / len(data["risk_scores"]), 2) if data["risk_scores"] else None
        result[fam] = {
            "total_inspections": data["total"],
            "stain_detected_rate": round(data["stain_detected_count"] / data["total"], 4) if data["total"] else None,
            "avg_risk_score": avg_risk,
        }
    return {"suppressed": False, "facility_count": facility_count, "instrument_families": result}


def common_anatomy_findings(db: Session, manufacturer_id: str) -> dict:
    inspections = _manufacturer_inspections(db, manufacturer_id)
    facility_count = len({i.tenant_id for i in inspections})
    if facility_count < MIN_FACILITIES:
        return {"suppressed": True, "reason": "insufficient_contributing_facilities", "facility_count": facility_count}

    insp_ids = [i.id for i in inspections]
    findings = db.query(InspectionFinding).filter(InspectionFinding.inspection_id.in_(insp_ids)).all() if insp_ids else []
    by_zone: dict[str, int] = {}
    for f in findings:
        if f.zone:
            by_zone[f.zone] = by_zone.get(f.zone, 0) + 1
    return {"suppressed": False, "facility_count": facility_count, "anatomy_zone_finding_counts": by_zone}


def corrosion_trend(db: Session, manufacturer_id: str) -> dict:
    inspections = _manufacturer_inspections(db, manufacturer_id)
    facility_count = len({i.tenant_id for i in inspections})
    if facility_count < MIN_FACILITIES:
        return {"suppressed": True, "reason": "insufficient_contributing_facilities", "facility_count": facility_count}

    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    insp_ids = [i.id for i in inspections]
    total = db.query(InspectionFinding.id).filter(
        InspectionFinding.inspection_id.in_(insp_ids), InspectionFinding.created_at >= since,
    ).count() if insp_ids else 0
    corrosion = db.query(InspectionFinding.id).filter(
        InspectionFinding.inspection_id.in_(insp_ids), InspectionFinding.finding_type == "corrosion",
        InspectionFinding.created_at >= since,
    ).count() if insp_ids else 0

    return {
        "suppressed": False,
        "facility_count": facility_count,
        "lookback_days": _LOOKBACK_DAYS,
        "corrosion_finding_rate": round(corrosion / total, 4) if total else None,
    }


def damage_patterns(db: Session, manufacturer_id: str) -> dict:
    """Every non-corrosion finding type observed for this manufacturer's
    instruments, ranked by frequency."""
    trends = anonymized_quality_trends(db, manufacturer_id)
    if trends.get("suppressed"):
        return trends
    counts = {k: v for k, v in trends["finding_type_counts"].items() if k != "corrosion"}
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "suppressed": False,
        "facility_count": trends["facility_count"],
        "damage_patterns": [{"finding_type": k, "count": v} for k, v in ranked],
    }


def repair_recommendations(db: Session, manufacturer_id: str) -> dict:
    """Advisory quality-improvement recommendation derived from this
    manufacturer's real finding distribution — never a fabricated
    confidence score, always human-review-gated."""
    trends = anonymized_quality_trends(db, manufacturer_id)
    if trends.get("suppressed"):
        return {**trends, "recommendations": []}

    counts = trends["finding_type_counts"]
    if not counts:
        return {"suppressed": False, "facility_count": trends["facility_count"], "recommendations": []}

    top_finding = max(counts.items(), key=lambda kv: kv[1])
    recommendation = (
        f"'{top_finding[0]}' is the most frequently observed finding type across "
        f"{trends['facility_count']} contributing facilities for this instrument family "
        f"({top_finding[1]} of {sum(counts.values())} findings). Potential association with "
        "instrument design or IFU compliance — not a confirmed root cause. Quality review recommended."
    )
    return {
        "suppressed": False,
        "facility_count": trends["facility_count"],
        "recommendations": [recommendation],
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def manufacturer_portal_dashboard(db: Session, manufacturer_id: str) -> dict:
    return {
        "manufacturer_id": manufacturer_id,
        "approved_baselines": approved_baseline_performance(db, manufacturer_id),
        "quality_trends": anonymized_quality_trends(db, manufacturer_id),
        "instrument_family_performance": instrument_family_performance(db, manufacturer_id),
        "common_anatomy_findings": common_anatomy_findings(db, manufacturer_id),
        "corrosion_trend": corrosion_trend(db, manufacturer_id),
        "damage_patterns": damage_patterns(db, manufacturer_id),
        "repair_recommendations": repair_recommendations(db, manufacturer_id)["recommendations"],
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
