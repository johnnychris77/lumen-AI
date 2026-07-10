"""v4.6 — Project Vanguard, Section 5: Strategic Planning Workspace.

Every generator below composes an already-real signal into a draft
`StrategicInitiative` — none of them projects a number this codebase
can't actually support:

  * Capital planning — `vanguard_financial_service`'s real
    capital-replacement priority list (from `prediction_engine`).
  * Quality initiatives — `finding_trend_service.finding_trends`'s real
    recurring-finding-type totals.
  * Service-line expansion — real `SurgicalCase.service_line` volume,
    comparing the last 30 days to the prior 30 days.
  * Capacity planning — Digital Twin utilization plus
    `insight_operational_forecast_service.forecast_operational`'s real
    inspection-workload projection.
  * Scenario planning — a captured snapshot of the current Executive
    Intelligence Center state alongside a free-text scenario
    description, for a planning discussion — not a fabricated
    enterprise-wide what-if simulator (Orbit's `orbit_simulation_service`
    already owns case-scoped what-if simulation; this does not duplicate
    it at enterprise scope).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.or_connect import SurgicalCase
from app.models.predictive_insight import FORECAST_INSPECTION_WORKLOAD, HORIZON_7_DAY
from app.models.vanguard_intelligence import (
    INITIATIVE_CAPACITY_PLANNING,
    INITIATIVE_CAPITAL_PLANNING,
    INITIATIVE_QUALITY,
    INITIATIVE_SCENARIO_PLANNING,
    INITIATIVE_SERVICE_LINE_EXPANSION,
    STRATEGIC_INITIATIVE_TYPES,
    StrategicInitiative,
)
from app.services import (
    digital_twin_engine,
    finding_trend_service,
    insight_operational_forecast_service,
    vanguard_executive_intelligence_service,
    vanguard_financial_service,
)


class UnknownInitiativeTypeError(Exception):
    pass


class InitiativeNotFoundError(Exception):
    pass


def _row_to_dict(row: StrategicInitiative) -> dict:
    return {
        "id": row.id, "initiative_type": row.initiative_type, "title": row.title, "status": row.status,
        "details": json.loads(row.details_json), "rationale": row.rationale, "created_by": row.created_by,
        "created_at": row.created_at.isoformat(), "human_review_required": row.human_review_required,
    }


def _create(db: Session, tenant_id: str, *, initiative_type: str, title: str, details: dict, rationale: str, created_by: str) -> dict:
    row = StrategicInitiative(
        tenant_id=tenant_id, initiative_type=initiative_type, title=title, details_json=json.dumps(details, default=str),
        rationale=rationale, created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_initiatives(db: Session, tenant_id: str, *, initiative_type: str = "") -> list[dict]:
    q = db.query(StrategicInitiative).filter(StrategicInitiative.tenant_id == tenant_id)
    if initiative_type:
        q = q.filter(StrategicInitiative.initiative_type == initiative_type)
    return [_row_to_dict(r) for r in q.order_by(StrategicInitiative.id.desc()).all()]


def get_initiative(db: Session, tenant_id: str, initiative_id: int) -> dict:
    row = db.query(StrategicInitiative).filter(StrategicInitiative.id == initiative_id, StrategicInitiative.tenant_id == tenant_id).first()
    if row is None:
        raise InitiativeNotFoundError(f"Strategic initiative {initiative_id} not found for tenant {tenant_id}.")
    return _row_to_dict(row)


def update_initiative_status(db: Session, tenant_id: str, initiative_id: int, *, status: str) -> dict:
    row = db.query(StrategicInitiative).filter(StrategicInitiative.id == initiative_id, StrategicInitiative.tenant_id == tenant_id).first()
    if row is None:
        raise InitiativeNotFoundError(f"Strategic initiative {initiative_id} not found for tenant {tenant_id}.")
    row.status = status
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def generate_capital_planning(db: Session, tenant_id: str, *, created_by: str = "system") -> dict:
    financial = vanguard_financial_service.financial_intelligence(db, tenant_id)
    priorities = financial["capital_replacement_priorities"]
    return _create(
        db, tenant_id, initiative_type=INITIATIVE_CAPITAL_PLANNING, title="Capital replacement priority list",
        details={"priorities": priorities, "data_source": financial["data_source"]},
        rationale=f"{len(priorities)} instrument(s) flagged by prediction_engine as highest replacement-risk priority.",
        created_by=created_by,
    )


def generate_quality_initiative(db: Session, tenant_id: str, *, created_by: str = "system") -> dict:
    trends = finding_trend_service.finding_trends(db, tenant_id)
    top_findings = sorted(trends["totals"].items(), key=lambda kv: kv[1], reverse=True)[:3]
    return _create(
        db, tenant_id, initiative_type=INITIATIVE_QUALITY, title="Recurring finding-type quality initiative",
        details={"top_findings": [{"finding_type": k, "count": v} for k, v in top_findings], "trend": trends["series"]},
        rationale=f"Top recurring finding types over the {trends['granularity']} lookback: " + ", ".join(k for k, _ in top_findings) + ".",
        created_by=created_by,
    )


def generate_service_line_expansion(db: Session, tenant_id: str, *, created_by: str = "system") -> dict:
    now = datetime.now(timezone.utc)
    recent_start, prior_start = now - timedelta(days=30), now - timedelta(days=60)

    recent = db.query(SurgicalCase).filter(SurgicalCase.tenant_id == tenant_id, SurgicalCase.created_at >= recent_start).all()
    prior = db.query(SurgicalCase).filter(
        SurgicalCase.tenant_id == tenant_id, SurgicalCase.created_at >= prior_start, SurgicalCase.created_at < recent_start,
    ).all()

    def _counts(cases: list[SurgicalCase]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in cases:
            key = c.service_line or "unspecified"
            counts[key] = counts.get(key, 0) + 1
        return counts

    recent_counts, prior_counts = _counts(recent), _counts(prior)
    growth = sorted(
        [
            {"service_line": k, "recent_30d": v, "prior_30d": prior_counts.get(k, 0), "growth": v - prior_counts.get(k, 0)}
            for k, v in recent_counts.items()
        ],
        key=lambda x: x["growth"], reverse=True,
    )
    return _create(
        db, tenant_id, initiative_type=INITIATIVE_SERVICE_LINE_EXPANSION, title="Service-line expansion candidates",
        details={"service_line_growth": growth},
        rationale="Ranked by real case-volume growth (last 30 days vs. the prior 30 days).",
        created_by=created_by,
    )


def generate_capacity_planning(db: Session, tenant_id: str, *, facility_id: str = "", created_by: str = "system") -> dict:
    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db)
    forecast = insight_operational_forecast_service.forecast_operational(
        db, tenant_id, forecast_type=FORECAST_INSPECTION_WORKLOAD, horizon=HORIZON_7_DAY,
    )
    return _create(
        db, tenant_id, initiative_type=INITIATIVE_CAPACITY_PLANNING, title="Capacity planning snapshot",
        details={"utilization_pct": twin_dashboard.twin_state.utilization_pct, "bottleneck_station": twin_dashboard.twin_state.bottleneck_station, "workload_forecast": forecast},
        rationale=f"Current utilization {twin_dashboard.twin_state.utilization_pct}%, bottleneck at {twin_dashboard.twin_state.bottleneck_station}.",
        created_by=created_by,
    )


def generate_scenario_planning(db: Session, tenant_id: str, *, scenario_description: str, created_by: str = "system") -> dict:
    snapshot = vanguard_executive_intelligence_service.executive_intelligence_center(db, tenant_id)
    return _create(
        db, tenant_id, initiative_type=INITIATIVE_SCENARIO_PLANNING, title=scenario_description[:120],
        details={"scenario_description": scenario_description, "executive_intelligence_snapshot": snapshot},
        rationale="Captures the current Executive Intelligence Center state alongside the scenario for planning discussion.",
        created_by=created_by,
    )


_GENERATORS = {
    INITIATIVE_CAPITAL_PLANNING: generate_capital_planning,
    INITIATIVE_QUALITY: generate_quality_initiative,
    INITIATIVE_SERVICE_LINE_EXPANSION: generate_service_line_expansion,
    INITIATIVE_CAPACITY_PLANNING: generate_capacity_planning,
}

assert set(_GENERATORS) | {INITIATIVE_SCENARIO_PLANNING} == set(STRATEGIC_INITIATIVE_TYPES)
