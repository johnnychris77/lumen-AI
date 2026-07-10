"""v4.6 — Project Vanguard, Section 8: Enterprise Benchmarking.

`atlas_benchmarking_service.cross_facility_benchmark`/`compute_facility_
benchmark` already compute a real per-facility rollup (inspection
quality, coverage, findings, supervisor overrides, knowledge
contributions, training progress) across every facility in a system —
every benchmark dimension below re-slices that same real data (or
composes one additional real signal per facility, e.g. Digital Twin
utilization) rather than re-querying `Inspection`/`SupervisorReview`
a second time.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.enterprise_hierarchy import EnterpriseFacility
from app.models.or_connect import CaseReadinessScoreRecord, SurgicalCase
from app.models.vanguard_intelligence import (
    BENCHMARK_FACILITIES,
    BENCHMARK_INSPECTION_PROGRAMS,
    BENCHMARK_INSTRUMENT_HEALTH,
    BENCHMARK_KNOWLEDGE_MATURITY,
    BENCHMARK_MARKETS,
    BENCHMARK_SERVICE_LINES,
    BENCHMARK_TYPES,
    EnterpriseBenchmarkSnapshot,
)
from app.services import atlas_benchmarking_service, digital_twin_engine


class UnknownBenchmarkTypeError(Exception):
    pass


def _facilities(db: Session, system_id: str) -> list[EnterpriseFacility]:
    return db.query(EnterpriseFacility).filter(EnterpriseFacility.system_id == system_id).all()


def _benchmark_facilities(db: Session, system_id: str) -> dict:
    return atlas_benchmarking_service.cross_facility_benchmark(db, system_id)


def _benchmark_markets(db: Session, system_id: str) -> dict:
    cross = atlas_benchmarking_service.cross_facility_benchmark(db, system_id)
    by_market: dict[str, list[dict]] = {}
    for f in cross["facilities"]:
        by_market.setdefault(f.get("market_id") or "unspecified", []).append(f)
    markets = [
        {
            "market_id": market_id, "facility_count": len(facilities),
            "avg_inspection_quality_pct": round(
                sum(f["inspection_quality_pct"] or 0 for f in facilities) / len(facilities), 1,
            ) if facilities else None,
        }
        for market_id, facilities in by_market.items()
    ]
    return {"system_id": system_id, "markets": sorted(markets, key=lambda m: m["avg_inspection_quality_pct"] or 0, reverse=True)}


def _benchmark_service_lines(db: Session, system_id: str) -> dict:
    facilities = _facilities(db, system_id)
    by_line: dict[str, dict] = {}
    for f in facilities:
        cases = db.query(SurgicalCase).filter(SurgicalCase.tenant_id == f.tenant_id).all()
        for case in cases:
            key = case.service_line or "unspecified"
            entry = by_line.setdefault(key, {"service_line": key, "case_count": 0, "scores": []})
            entry["case_count"] += 1
            score = (
                db.query(CaseReadinessScoreRecord)
                .filter(CaseReadinessScoreRecord.tenant_id == f.tenant_id, CaseReadinessScoreRecord.case_id == case.id)
                .order_by(CaseReadinessScoreRecord.id.desc())
                .first()
            )
            if score is not None:
                entry["scores"].append(score.score)
    service_lines = [
        {
            "service_line": v["service_line"], "case_count": v["case_count"],
            "avg_readiness_score": round(sum(v["scores"]) / len(v["scores"]), 1) if v["scores"] else None,
        }
        for v in by_line.values()
    ]
    return {"system_id": system_id, "service_lines": sorted(service_lines, key=lambda s: s["case_count"], reverse=True)}


def _benchmark_inspection_programs(db: Session, system_id: str) -> dict:
    cross = atlas_benchmarking_service.cross_facility_benchmark(db, system_id)
    programs = [
        {
            "facility_id": f["facility_id"], "facility_name": f["facility_name"],
            "inspection_quality_pct": f["inspection_quality_pct"], "coverage_pct": f["coverage_pct"],
            "supervisor_override_rate_pct": f["supervisor_override_rate_pct"],
        }
        for f in cross["facilities"]
    ]
    return {"system_id": system_id, "inspection_programs": programs}


def _benchmark_instrument_health(db: Session, system_id: str) -> dict:
    facilities = _facilities(db, system_id)
    results = []
    for f in facilities:
        twin = digital_twin_engine.compute_twin_dashboard(f.tenant_id, f.facility_id, db)
        results.append({
            "facility_id": f.facility_id, "facility_name": f.facility_name,
            "utilization_pct": twin.twin_state.utilization_pct, "open_alert_count": len(twin.open_alerts),
        })
    return {"system_id": system_id, "instrument_health": sorted(results, key=lambda r: r["utilization_pct"] or 0, reverse=True)}


def _benchmark_knowledge_maturity(db: Session, system_id: str) -> dict:
    cross = atlas_benchmarking_service.cross_facility_benchmark(db, system_id)
    maturity = [
        {
            "facility_id": f["facility_id"], "facility_name": f["facility_name"],
            "knowledge_contributions": f["knowledge_contributions"], "training_progress_pct": f["training_progress_pct"],
        }
        for f in cross["facilities"]
    ]
    return {"system_id": system_id, "knowledge_maturity": sorted(maturity, key=lambda m: m["knowledge_contributions"], reverse=True)}


_BENCHMARK_FUNCS = {
    BENCHMARK_FACILITIES: _benchmark_facilities,
    BENCHMARK_MARKETS: _benchmark_markets,
    BENCHMARK_SERVICE_LINES: _benchmark_service_lines,
    BENCHMARK_INSPECTION_PROGRAMS: _benchmark_inspection_programs,
    BENCHMARK_INSTRUMENT_HEALTH: _benchmark_instrument_health,
    BENCHMARK_KNOWLEDGE_MATURITY: _benchmark_knowledge_maturity,
}

assert set(_BENCHMARK_FUNCS) == set(BENCHMARK_TYPES)


def compute_benchmark(db: Session, tenant_id: str, system_id: str, benchmark_type: str) -> dict:
    if benchmark_type not in BENCHMARK_TYPES:
        raise UnknownBenchmarkTypeError(f"benchmark_type must be one of {BENCHMARK_TYPES}")

    results = _BENCHMARK_FUNCS[benchmark_type](db, system_id)

    snapshot = EnterpriseBenchmarkSnapshot(tenant_id=tenant_id, benchmark_type=benchmark_type, results_json=json.dumps(results, default=str))
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {"id": snapshot.id, "benchmark_type": benchmark_type, "results": results, "human_review_required": True}
