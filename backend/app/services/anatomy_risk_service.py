"""v1.5 — Anatomy Risk Dashboard (Deliverable 3).

Highest-risk anatomy zones, most frequent contamination/damage by zone, and
most-missed inspection zones — derived from real InspectionFinding rows (what
was actually detected, where) and Inspection Coverage Engine data (what was
actually missing), not a generic anatomy taxonomy guess.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.inspection_finding import InspectionFinding


def _contamination_types() -> set[str]:
    from app.services.baseline_comparison_scoring_service import CLEANING_KPIS
    return set(CLEANING_KPIS)


def anatomy_risk_dashboard(db: Session, tenant_id: str, days: int = 180) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    findings = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since)
        .all()
    )
    contamination = _contamination_types()

    zone_counts: dict[str, int] = defaultdict(int)
    zone_contamination: dict[str, int] = defaultdict(int)
    zone_damage: dict[str, int] = defaultdict(int)
    for f in findings:
        zone = f.zone or "unspecified region"
        zone_counts[zone] += 1
        if f.finding_type in contamination:
            zone_contamination[zone] += 1
        else:
            zone_damage[zone] += 1

    def _top(counter: dict[str, int], n: int = 10) -> list[dict]:
        return [
            {"zone": z, "count": c}
            for z, c in sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:n]
        ]

    # Most-missed zones: inspections where the coverage engine recorded a
    # required zone as missing (persisted nowhere per-zone today — derived
    # from the guidance list computed at analysis time isn't stored either,
    # so this reports on the honestly-available signal: inspections with an
    # assessed-but-incomplete coverage_quality).
    incomplete = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            models.Inspection.created_at >= since,
            models.Inspection.coverage_quality.in_(["incomplete", "insufficient"]),
        )
        .count()
    )
    assessed = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            models.Inspection.created_at >= since,
            models.Inspection.coverage_pct.isnot(None),
        )
        .count()
    )

    return {
        "highest_risk_anatomy_zones": _top(zone_counts),
        "most_frequent_contamination_zones": _top(zone_contamination),
        "most_frequent_damage_zones": _top(zone_damage),
        "coverage_incomplete_inspections": incomplete,
        "coverage_assessed_inspections": assessed,
        "coverage_incomplete_pct": round(100 * incomplete / assessed, 1) if assessed else None,
        "human_review_required": True,
    }
