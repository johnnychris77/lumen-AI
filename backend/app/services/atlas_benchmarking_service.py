"""v3.1 — Project Atlas, Section 3: Cross-Facility Benchmarking.

Distinct from `benchmark_engine.py`'s `compute_hospital_benchmarks` (which
groups `CVInferenceRecord` by a sub-tenant `facility_id` field *within one
tenant_id*) — Atlas benchmarks across distinct `tenant_id`s (one per
hospital) under a health system, per this module's tenant==hospital
convention. Every metric here is a count or rate; nothing patient-
identifying is ever aggregated or returned.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.atlas_enterprise import DISCLAIMER
from app.models.disposition_override import DispositionOverride
from app.models.inspection_finding import InspectionFinding
from app.models.knowledge import KnowledgeArticle
from app.models.supervisor_review import SupervisorReview
from app.services.competency_service import technician_quality_dashboard

_LOOKBACK_DAYS = 90
_CONDITION_FINDING_TYPES = {"rust", "corrosion", "pitting", "crack", "insulation_damage", "missing_component"}


def _facilities_for_system(db: Session, system_id: str) -> list:
    return (
        db.query(models.EnterpriseFacility)
        .filter(models.EnterpriseFacility.system_id == system_id, models.EnterpriseFacility.is_active.is_(True))
        .all()
    )


def _finding_counts(db: Session, tenant_id: str, since: datetime) -> dict[str, int]:
    rows = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since)
        .all()
    )
    counts = {"blood": 0, "bone": 0, "corrosion": 0, "damage": 0}
    zone_finding_counter: dict[tuple[str, str], int] = {}
    for f in rows:
        if f.finding_type == "blood":
            counts["blood"] += 1
        elif f.finding_type == "bone":
            counts["bone"] += 1
        elif f.finding_type == "corrosion":
            counts["corrosion"] += 1
        elif f.finding_type in _CONDITION_FINDING_TYPES:
            counts["damage"] += 1
        key = (f.finding_type, f.zone or "")
        zone_finding_counter[key] = zone_finding_counter.get(key, 0) + 1
    counts["repeat_findings"] = sum(1 for c in zone_finding_counter.values() if c >= 3)
    counts["total_findings"] = len(rows)
    return counts


def compute_facility_benchmark(db: Session, tenant_id: str) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)

    finding_counts = _finding_counts(db, tenant_id, since)

    overrides = (
        db.query(DispositionOverride)
        .filter(DispositionOverride.tenant_id == tenant_id, DispositionOverride.created_at >= since)
        .count()
    )
    total_inspections = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.created_at >= since)
        .count()
    )
    override_rate_pct = round(100 * overrides / total_inspections, 1) if total_inspections else None

    coverage_rows = (
        db.query(models.Inspection.coverage_pct)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.created_at >= since, models.Inspection.coverage_pct.isnot(None))
        .all()
    )
    coverage_pct = round(sum(r[0] for r in coverage_rows) / len(coverage_rows), 1) if coverage_rows else None

    scored = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id, models.Inspection.created_at >= since,
            models.Inspection.score_status.in_(["scored", "scored_after_override"]),
        )
        .all()
    )
    inspection_quality_pct = round(100 * sum(1 for r in scored if r.disposition == "PASS") / len(scored), 1) if scored else None

    knowledge_contributions = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id).count()

    training = technician_quality_dashboard(db, tenant_id)
    progress_values = [t["training_progress_pct"] for t in training["technicians"] if t.get("training_progress_pct") is not None]
    training_progress_pct = round(sum(progress_values) / len(progress_values), 1) if progress_values else None

    review_count = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= since).count()

    return {
        "tenant_id": tenant_id,
        "period_days": _LOOKBACK_DAYS,
        "inspection_quality_pct": inspection_quality_pct,
        "coverage_pct": coverage_pct,
        "blood_finding_count": finding_counts["blood"],
        "bone_finding_count": finding_counts["bone"],
        "corrosion_finding_count": finding_counts["corrosion"],
        "damage_finding_count": finding_counts["damage"],
        "repeat_finding_count": finding_counts["repeat_findings"],
        "total_findings": finding_counts["total_findings"],
        "supervisor_override_count": overrides,
        "supervisor_override_rate_pct": override_rate_pct,
        "supervisor_review_count": review_count,
        "knowledge_contributions": knowledge_contributions,
        "training_progress_pct": training_progress_pct,
    }


def cross_facility_benchmark(db: Session, system_id: str) -> dict:
    facilities = _facilities_for_system(db, system_id)
    results = []
    for f in facilities:
        benchmark = compute_facility_benchmark(db, f.tenant_id)
        benchmark["facility_id"] = f.facility_id
        benchmark["facility_name"] = f.facility_name
        benchmark["market_id"] = f.market_id
        results.append(benchmark)

    return {
        "system_id": system_id,
        "facility_count": len(results),
        "facilities": sorted(results, key=lambda r: r["inspection_quality_pct"] or 0, reverse=True),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
