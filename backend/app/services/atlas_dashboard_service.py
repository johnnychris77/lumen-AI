"""v3.1 — Project Atlas, Sections 2 & 5: Enterprise Dashboard + Facility Intelligence.

"Facility" == a distinct `tenant_id` (see `models/atlas_enterprise.py`'s
module docstring for why). Every score here composes an existing,
already-real, per-tenant engine rather than re-deriving it:

| Facility Intelligence field | Source |
|---|---|
| quality_score | `quality_dashboard_service.executive_quality_score` |
| risk_score | `sentinel_dashboard_service.run_sentinel_health_snapshot` |
| digital_twin_health_pct | `sentinel_digital_twin_monitor_service.list_open_flags` |
| supervisor_agreement_rate | `sentinel_ai_health_service.compute_ai_health` |
| training_index | `competency_service.technician_quality_dashboard` |
| knowledge_index | `knowledge_graph_service.learning_confidence` |

The Enterprise Dashboard (Section 2) is the system-wide rollup of these
same per-facility snapshots — never a re-derivation of `quality_dashboard_
service`'s or `sentinel_dashboard_service`'s math a second time.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.atlas_enterprise import DISCLAIMER, FacilityIntelligenceSnapshot
from app.services.competency_service import technician_quality_dashboard
from app.services.knowledge_graph_service import learning_confidence
from app.services.quality_dashboard_service import executive_quality_score
from app.services.sentinel_ai_health_service import compute_ai_health
from app.services.sentinel_dashboard_service import run_sentinel_health_snapshot
from app.services.sentinel_digital_twin_monitor_service import list_open_flags


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


def compute_facility_intelligence(db: Session, system_id: str, facility_id: str) -> dict:
    facility = (
        db.query(models.EnterpriseFacility)
        .filter(models.EnterpriseFacility.facility_id == facility_id, models.EnterpriseFacility.system_id == system_id)
        .first()
    )
    if facility is None:
        return None

    tenant_id = facility.tenant_id
    quality = executive_quality_score(db, tenant_id)
    health_snapshot = run_sentinel_health_snapshot(db, tenant_id)
    ai_health = compute_ai_health(db, tenant_id)
    twin_flags = list_open_flags(db, tenant_id)
    training = technician_quality_dashboard(db, tenant_id)
    kg = learning_confidence(db, tenant_id)

    total_flags = len(twin_flags)
    critical_escalation = sum(1 for f in twin_flags if f["tier"] in ("critical", "escalation"))
    digital_twin_health_pct = round(100 * (1 - critical_escalation / total_flags), 1) if total_flags else 100.0

    training_rows = training.get("technicians", []) if isinstance(training, dict) else []
    training_progress_values = [t["training_progress_pct"] for t in training_rows if t.get("training_progress_pct") is not None]
    training_index = round(sum(training_progress_values) / len(training_progress_values), 1) if training_progress_values else None

    quality_score = quality.get("score")
    risk_score = health_snapshot.get("enterprise_risk_score")
    health_score = (
        round((quality_score + (100 - risk_score)) / 2, 1)
        if quality_score is not None and risk_score is not None else None
    )

    snapshot = FacilityIntelligenceSnapshot(
        system_id=system_id, facility_id=facility_id, tenant_id=tenant_id,
        quality_score=quality_score, risk_score=risk_score, health_score=health_score,
        digital_twin_health_pct=digital_twin_health_pct,
        supervisor_agreement_rate=ai_health.get("supervisor_agreement_rate"),
        training_index=training_index, knowledge_index=kg.get("knowledge_confidence"),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    result = _row_to_dict(snapshot)
    result["facility_name"] = facility.facility_name
    result["market_id"] = facility.market_id
    return result


def refresh_all_facility_intelligence(db: Session, system_id: str) -> list[dict]:
    facilities = _facilities_for_system(db, system_id)
    return [r for r in (compute_facility_intelligence(db, system_id, f.facility_id) for f in facilities) if r is not None]


def enterprise_dashboard(db: Session, system_id: str) -> dict:
    facility_snapshots = refresh_all_facility_intelligence(db, system_id)

    def _avg(key: str) -> float | None:
        values = [f[key] for f in facility_snapshots if f.get(key) is not None]
        return round(sum(values) / len(values), 1) if values else None

    inspection_volume = 0
    pass_rates = []
    coverage_pcts = []
    for f in facility_snapshots:
        rows = db.query(models.Inspection).filter(models.Inspection.tenant_id == f["tenant_id"]).all()
        inspection_volume += len(rows)
        scored = [r for r in rows if r.score_status in ("scored", "scored_after_override")]
        if scored:
            pass_rates.append(100 * sum(1 for r in scored if r.disposition == "PASS") / len(scored))
        coverage_assessed = [r.coverage_pct for r in rows if r.coverage_pct is not None]
        if coverage_assessed:
            coverage_pcts.append(sum(coverage_assessed) / len(coverage_assessed))

    return {
        "system_id": system_id,
        "facility_count": len(facility_snapshots),
        "enterprise_quality_score": _avg("quality_score"),
        "enterprise_risk_score": _avg("risk_score"),
        "inspection_volume": inspection_volume,
        "pass_rate_pct": round(sum(pass_rates) / len(pass_rates), 1) if pass_rates else None,
        "coverage_quality_pct": round(sum(coverage_pcts) / len(coverage_pcts), 1) if coverage_pcts else None,
        "ai_confidence_avg": _avg("knowledge_index"),
        "supervisor_agreement_rate": _avg("supervisor_agreement_rate"),
        "digital_twin_health_pct": _avg("digital_twin_health_pct"),
        "knowledge_growth": _avg("knowledge_index"),
        "facility_comparison": sorted(facility_snapshots, key=lambda f: (f["risk_score"] or 0), reverse=True),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def get_latest_facility_intelligence(db: Session, system_id: str, facility_id: str) -> dict | None:
    row = (
        db.query(FacilityIntelligenceSnapshot)
        .filter(FacilityIntelligenceSnapshot.system_id == system_id, FacilityIntelligenceSnapshot.facility_id == facility_id)
        .order_by(FacilityIntelligenceSnapshot.id.desc())
        .first()
    )
    return _row_to_dict(row) if row else None
