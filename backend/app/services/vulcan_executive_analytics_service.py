"""Project Vulcan, Section 14: Executive Reliability Analytics.

Every metric here is a live aggregation over real `VulcanReliabilityAssessment`
and `RepairRequest` rows (plus real `Inspection.facility_name` and
`SurgicalCase.service_line` joins where those fields exist). Presents
observations, never unsupported causation -- no metric claims a cause, only
counts/rates/averages of what was actually recorded.

"Reliability by manufacturer/model" is reported by manufacturer only:
`VulcanReliabilityAssessment` does not carry a per-instrument model field
(no module in this codebase tracks model at the per-physical-instrument
level, only at the `InstrumentKnowledge` manufacturer+family reference-data
level) -- rather than fabricate a model breakdown, this is left as a known
gap and documented as such.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.db import models
from app.models.or_connect import REPAIR_REPLACED, REPAIR_RETURNED, RepairRequest, SurgicalCase
from app.models.vulcan_reliability import (
    DISPOSITION_REMOVE_FROM_SERVICE,
    REPAIR_OUTCOME_EFFECTIVE,
    REPAIR_OUTCOME_FAILURE_RECURRED,
)
from app.services.vulcan_repair_effectiveness_service import classify_repair_outcome
from app.services.vulcan_watchlist_service import _latest_per_instrument, retirement_candidates


def most_failure_prone_instrument_families(db: Session, tenant_id: str) -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for row in _latest_per_instrument(db, tenant_id):
        counts[row.instrument_family or "unspecified"] += 1
    return sorted(({"instrument_family": k, "instrument_count": v} for k, v in counts.items()), key=lambda r: r["instrument_count"], reverse=True)


def most_common_failure_zones(db: Session, tenant_id: str) -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for row in _latest_per_instrument(db, tenant_id):
        if row.anatomy_zone:
            counts[row.anatomy_zone] += 1
    return sorted(({"anatomy_zone": k, "instrument_count": v} for k, v in counts.items()), key=lambda r: r["instrument_count"], reverse=True)


def repeat_repair_rate(db: Session, tenant_id: str) -> dict:
    counts: dict[str, int] = defaultdict(int)
    for r in db.query(RepairRequest).filter(RepairRequest.tenant_id == tenant_id):
        counts[r.instrument_identity] += 1
    total = len(counts)
    repeat = sum(1 for c in counts.values() if c >= 2)
    return {"instruments_with_repairs": total, "instruments_with_repeat_repairs": repeat,
            "repeat_repair_rate_pct": round(100.0 * repeat / total, 1) if total else 0.0}


def repair_recurrence_rate(db: Session, tenant_id: str) -> dict:
    repairs = (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.status.in_([REPAIR_RETURNED, REPAIR_REPLACED]))
        .all()
    )
    outcomes = [classify_repair_outcome(db, tenant_id, r)["repair_outcome"] for r in repairs]
    total = len(outcomes)
    recurred = sum(1 for o in outcomes if o == REPAIR_OUTCOME_FAILURE_RECURRED)
    return {"completed_repairs_evaluated": total, "repairs_with_recurrence": recurred,
            "repair_recurrence_rate_pct": round(100.0 * recurred / total, 1) if total else 0.0}


def corrosion_progression_summary(db: Session, tenant_id: str) -> dict:
    counts: dict[str, int] = defaultdict(int)
    for row in _latest_per_instrument(db, tenant_id):
        if row.failure_category == "corrosion":
            counts[row.progression] += 1
    return dict(counts)


def instruments_removed_from_service(db: Session, tenant_id: str) -> list[dict]:
    from app.services.vulcan_reliability_agent_service import to_dict
    return [
        to_dict(r) for r in _latest_per_instrument(db, tenant_id)
        if r.recommended_disposition == DISPOSITION_REMOVE_FROM_SERVICE or r.final_disposition == DISPOSITION_REMOVE_FROM_SERVICE
    ]


def reliability_by_manufacturer(db: Session, tenant_id: str) -> list[dict]:
    scores: dict[str, list[float]] = defaultdict(list)
    for row in _latest_per_instrument(db, tenant_id):
        scores[row.manufacturer_name or "unspecified"].append(row.reliability_score)
    return sorted(
        ({"manufacturer_name": k, "average_reliability_score": round(sum(v) / len(v), 1), "instrument_count": len(v)}
         for k, v in scores.items()),
        key=lambda r: r["average_reliability_score"],
    )


def reliability_by_facility(db: Session, tenant_id: str) -> list[dict]:
    facility_by_identity: dict[str, str] = {}
    for i in db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id):
        identity = (
            f"barcode:{i.instrument_barcode}" if i.instrument_barcode
            else f"udi:{i.instrument_udi}" if i.instrument_udi else None
        )
        if identity and identity not in facility_by_identity and i.facility_name:
            facility_by_identity[identity] = i.facility_name

    scores: dict[str, list[float]] = defaultdict(list)
    for row in _latest_per_instrument(db, tenant_id):
        facility = facility_by_identity.get(row.instrument_identity, "unspecified")
        scores[facility].append(row.reliability_score)
    return sorted(
        ({"facility_name": k, "average_reliability_score": round(sum(v) / len(v), 1), "instrument_count": len(v)}
         for k, v in scores.items()),
        key=lambda r: r["average_reliability_score"],
    )


def reliability_by_service_line(db: Session, tenant_id: str) -> list[dict]:
    case_service_line = {
        c.id: c.service_line for c in db.query(SurgicalCase).filter(SurgicalCase.tenant_id == tenant_id)
    }
    service_line_by_identity: dict[str, str] = {}
    for i in db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id):
        identity = (
            f"barcode:{i.instrument_barcode}" if i.instrument_barcode
            else f"udi:{i.instrument_udi}" if i.instrument_udi else None
        )
        if identity and identity not in service_line_by_identity and i.case_id:
            line = case_service_line.get(i.case_id)
            if line:
                service_line_by_identity[identity] = line

    scores: dict[str, list[float]] = defaultdict(list)
    for row in _latest_per_instrument(db, tenant_id):
        line = service_line_by_identity.get(row.instrument_identity, "unspecified")
        scores[line].append(row.reliability_score)
    return sorted(
        ({"service_line": k, "average_reliability_score": round(sum(v) / len(v), 1), "instrument_count": len(v)}
         for k, v in scores.items()),
        key=lambda r: r["average_reliability_score"],
    )


def avoided_repeat_repair_opportunities(db: Session, tenant_id: str) -> dict:
    """Repairs classified `effective` -- evidence a repeat repair was not needed."""
    repairs = (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.status.in_([REPAIR_RETURNED, REPAIR_REPLACED]))
        .all()
    )
    outcomes = [classify_repair_outcome(db, tenant_id, r)["repair_outcome"] for r in repairs]
    effective = sum(1 for o in outcomes if o == REPAIR_OUTCOME_EFFECTIVE)
    return {"completed_repairs_evaluated": len(outcomes), "effective_repairs": effective}


def executive_summary(db: Session, tenant_id: str) -> dict:
    return {
        "most_failure_prone_instrument_families": most_failure_prone_instrument_families(db, tenant_id),
        "most_common_failure_zones": most_common_failure_zones(db, tenant_id),
        "repeat_repair_rate": repeat_repair_rate(db, tenant_id),
        "repair_recurrence_rate": repair_recurrence_rate(db, tenant_id),
        "corrosion_progression": corrosion_progression_summary(db, tenant_id),
        "instruments_removed_from_service": instruments_removed_from_service(db, tenant_id),
        "reliability_by_manufacturer": reliability_by_manufacturer(db, tenant_id),
        "reliability_by_facility": reliability_by_facility(db, tenant_id),
        "reliability_by_service_line": reliability_by_service_line(db, tenant_id),
        "retirement_candidates": retirement_candidates(db, tenant_id),
        "avoided_repeat_repair_opportunities": avoided_repeat_repair_opportunities(db, tenant_id),
        "human_review_required": True,
    }
