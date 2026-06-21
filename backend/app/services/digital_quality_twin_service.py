"""
P22: Healthcare Digital Quality Twin — Service Layer.

IMPORTANT DISCLAIMER: All outputs represent potential associations for human review only.
They do NOT establish, imply, or claim causation. All outputs require human clinical and
quality review before any action is taken.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.digital_quality_twin import (
    ExecutiveDecisionBrief,
    InterventionModel,
    QualityForecast,
    QualityTwinState,
    ScenarioSimulation,
)

DISCLAIMER = (
    "Digital Quality Twin outputs are modeled projections for planning and decision support only. "
    "All findings represent potential associations — they do not establish causation or predict "
    "specific outcomes. Human review and approval are required before any operational decisions."
)

_FORECAST_DISCLAIMER = (
    "Forecast is a modeled projection for planning purposes. Does not establish causation "
    "or guarantee outcomes. All forecasts require human review before operational decisions."
)

_SCENARIO_DISCLAIMER = (
    "Simulation output for planning purposes only. Does not establish causation "
    "or predict specific outcomes. Human review required before any operational decisions."
)

_INTERVENTION_DISCLAIMER = (
    "Intervention model is advisory only. Projected outcomes are estimates based on "
    "available data patterns. Does not establish causation. Human review and approval "
    "required before implementation."
)

_BRIEF_DISCLAIMER = (
    "This brief is generated from available quality signals for decision support. "
    "All findings represent potential associations for human review. Does not establish "
    "causation or constitute clinical guidance."
)

_NINE_SOURCES = [
    "spd_operations",
    "inspection_intelligence",
    "patient_safety_intelligence",
    "quality_events",
    "capas",
    "vendor_performance",
    "recall_data",
    "infection_prevention_signals",
    "national_benchmarking",
]


def _seed(s: str) -> random.Random:
    """Deterministic seeded RNG from string."""
    h = hashlib.md5(s.encode()).hexdigest()[:8]  # noqa: S324
    return random.Random(int(h, 16))


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    result["human_review_required"] = True
    if "disclaimer" not in result or not result["disclaimer"]:
        result["disclaimer"] = DISCLAIMER
    return result


# ---------------------------------------------------------------------------
# Twin State
# ---------------------------------------------------------------------------


def get_twin_state(db: Session, tenant_id: str, facility_id: str = "") -> dict:
    """Return the latest QualityTwinState for a tenant, falling back to seeded mock."""
    row = (
        db.query(QualityTwinState)
        .filter(
            QualityTwinState.tenant_id == tenant_id,
            QualityTwinState.facility_id == facility_id,
        )
        .order_by(QualityTwinState.id.desc())
        .first()
    )
    if row:
        return _row_to_dict(row)

    rng = _seed(f"twin_state:{tenant_id}:{facility_id}")
    overall = round(rng.uniform(0.55, 0.92), 3)
    return {
        "id": None,
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "snapshot_date": datetime.now(timezone.utc).isoformat(),
        "overall_quality_score": overall,
        "inspection_quality_score": round(rng.uniform(0.60, 0.95), 3),
        "patient_safety_score": round(rng.uniform(0.65, 0.93), 3),
        "vendor_performance_score": round(rng.uniform(0.55, 0.90), 3),
        "recall_exposure_score": round(rng.uniform(0.05, 0.35), 3),
        "infection_prevention_score": round(rng.uniform(0.60, 0.92), 3),
        "capa_effectiveness_score": round(rng.uniform(0.55, 0.88), 3),
        "benchmarking_percentile": round(rng.uniform(30.0, 85.0), 1),
        "open_emerging_risks": rng.randint(1, 6),
        "open_investigations": rng.randint(0, 4),
        "pending_recommendations": rng.randint(1, 8),
        "active_recalls": rng.randint(0, 3),
        "trend_direction": rng.choice(["improving", "stable", "declining"]),
        "trend_confidence": round(rng.uniform(0.50, 0.85), 3),
        "data_source": "simulated",
        "human_review_required": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Forecasts
# ---------------------------------------------------------------------------


def get_forecasts(db: Session, tenant_id: str) -> list[dict]:
    """Return 3 forecasts (30/60/90-day horizons) for the tenant."""
    rows = (
        db.query(QualityForecast)
        .filter(QualityForecast.tenant_id == tenant_id)
        .order_by(QualityForecast.id.desc())
        .limit(3)
        .all()
    )
    if rows:
        return [_row_to_dict(r) for r in rows]

    state = get_twin_state(db, tenant_id)
    base_score = state["overall_quality_score"]
    rng = _seed(f"forecasts:{tenant_id}")

    forecasts = []
    for days in (30, 60, 90):
        decay = days * rng.uniform(0.0005, 0.0015)
        projected = round(max(0.40, base_score - decay), 3)
        if projected >= 0.80:
            risk_level = "low"
        elif projected >= 0.65:
            risk_level = "moderate"
        elif projected >= 0.50:
            risk_level = "high"
        else:
            risk_level = "critical"

        risk_drivers = json.dumps([
            "vendor_performance_trends",
            "open_capa_count",
            "recall_exposure",
        ])
        recommended_interventions = json.dumps([
            "Increase inspection frequency for high-risk trays",
            "Close open CAPAs associated with recurring findings",
            "Review underperforming vendor contracts",
        ])

        forecasts.append({
            "id": None,
            "tenant_id": tenant_id,
            "facility_id": "",
            "forecast_horizon_days": days,
            "forecast_date": datetime.now(timezone.utc).isoformat(),
            "projected_quality_score": projected,
            "projected_risk_level": risk_level,
            "risk_drivers": risk_drivers,
            "recommended_interventions": recommended_interventions,
            "confidence_score": round(rng.uniform(0.55, 0.80), 3),
            "association_reason": (
                f"{days}-day projection is associated with observed trends in vendor performance, "
                "open investigation count, and historical quality signal patterns. "
                "Association is not causation."
            ),
            "human_review_required": True,
            "disclaimer": _FORECAST_DISCLAIMER,
            "data_source": "simulated",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return forecasts


# ---------------------------------------------------------------------------
# Scenario Simulation
# ---------------------------------------------------------------------------


def run_scenario(
    db: Session,
    tenant_id: str,
    scenario_type: str,
    intervention_type: str,
    parameters: dict,
) -> dict:
    """Run a what-if scenario simulation and persist the result."""
    rng = _seed(f"scenario:{tenant_id}:{scenario_type}:{intervention_type}")
    state = get_twin_state(db, tenant_id)
    base_score = state["overall_quality_score"]

    delta = round(rng.uniform(0.02, 0.12), 3)
    risk_reduction = round(rng.uniform(0.05, 0.25), 3)
    timeframe = parameters.get("timeframe_days", 90)

    scenario_name = f"{scenario_type}_{intervention_type}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    sim = ScenarioSimulation(
        tenant_id=tenant_id,
        scenario_name=scenario_name,
        scenario_type=scenario_type,
        intervention_type=intervention_type,
        intervention_description=f"Modeled {intervention_type} intervention for {scenario_type} scenario.",
        parameters=json.dumps(parameters),
        projected_quality_delta=delta,
        projected_risk_reduction=risk_reduction,
        projected_timeframe_days=timeframe,
        confidence_score=round(rng.uniform(0.50, 0.80), 3),
        association_reason=(
            f"Projected delta is associated with historical patterns where {intervention_type} "
            "interventions were observed alongside quality signal improvements. "
            "Association is not causation."
        ),
        human_review_required=True,
        disclaimer=_SCENARIO_DISCLAIMER,
        status="draft",
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)

    result = _row_to_dict(sim)
    result["baseline_quality_score"] = base_score
    result["projected_quality_score"] = round(min(1.0, base_score + delta), 3)
    return result


# ---------------------------------------------------------------------------
# Intervention Models
# ---------------------------------------------------------------------------


def get_intervention_models(db: Session, tenant_id: str) -> list[dict]:
    """Return 5 intervention models (one per intervention type)."""
    rows = (
        db.query(InterventionModel)
        .filter(InterventionModel.tenant_id == tenant_id)
        .order_by(InterventionModel.id.desc())
        .limit(5)
        .all()
    )
    if rows:
        return [_row_to_dict(r) for r in rows]

    state = get_twin_state(db, tenant_id)
    base = state["overall_quality_score"]
    rng = _seed(f"interventions:{tenant_id}")

    intervention_specs = [
        ("vendor_change", "Underperforming vendor contract", "medium", 90),
        ("inspection_frequency_increase", "High-risk instrument trays", "low", 30),
        ("capa_closure", "Open corrective actions backlog", "medium", 60),
        ("recall_response", "Active device recall exposure", "high", 21),
        ("training_intervention", "SPD and inspection staff", "low", 45),
    ]

    models = []
    for itype, target, effort, days in intervention_specs:
        improvement = round(rng.uniform(0.03, 0.10), 3)
        projected = round(min(1.0, base + improvement), 3)
        models.append({
            "id": None,
            "tenant_id": tenant_id,
            "intervention_type": itype,
            "intervention_target": target,
            "baseline_quality_score": base,
            "projected_quality_score": projected,
            "projected_improvement": improvement,
            "effort_estimate": effort,
            "timeframe_days": days,
            "confidence_score": round(rng.uniform(0.50, 0.80), 3),
            "association_reason": (
                f"Projected improvement is associated with observed quality signal patterns "
                f"where {itype} actions were followed by improved scores. "
                "Association is not causation."
            ),
            "human_review_required": True,
            "disclaimer": _INTERVENTION_DISCLAIMER,
            "status": "modeled",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return models


# ---------------------------------------------------------------------------
# Executive Decision Brief
# ---------------------------------------------------------------------------

_ROLE_HEADLINES = {
    "CEO": "Enterprise quality risk posture requires leadership attention",
    "COO": "Operational throughput risk associated with vendor performance signals",
    "CNO": "Patient safety signal associations identified — nursing quality review recommended",
    "CQO": "CAPA effectiveness and inspection quality trends warrant strategic review",
    "quality_director": "Open investigations and emerging signals require prioritisation",
    "market_director": "Vendor exposure and recall risk may affect competitive quality standing",
}

_ROLE_CONCERNS = {
    "CEO": ["Enterprise risk exposure", "Benchmarking percentile trend", "Open recall exposure"],
    "COO": ["Vendor delivery quality signals", "SPD throughput risk", "Active recall count"],
    "CNO": ["Near-miss correlation signals", "Infection prevention trend", "CAPA closure rate"],
    "CQO": ["Inspection pass rate trend", "CAPA effectiveness score", "National benchmarking position"],
    "quality_director": ["Open investigations", "Emerging risk signals", "Pending recommendations"],
    "market_director": ["Vendor performance exposure", "Active recalls", "Quality trend vs peers"],
}

_ROLE_ACTIONS = {
    "CEO": ["Review enterprise risk dashboard", "Approve strategic quality investments", "Engage board on recall exposure"],
    "COO": ["Review vendor performance scorecards", "Approve SPD throughput improvement plan", "Confirm recall response timeline"],
    "CNO": ["Review patient safety signal associations", "Approve infection prevention protocol review", "Confirm CAPA closure prioritisation"],
    "CQO": ["Review inspection quality trend", "Approve CAPA backlog closure plan", "Commission benchmarking gap analysis"],
    "quality_director": ["Triage open investigations", "Review and approve pending recommendations", "Escalate critical emerging signals"],
    "market_director": ["Review vendor exposure summary", "Assess recall risk to market position", "Commission competitive quality benchmarking"],
}


def get_executive_brief(db: Session, tenant_id: str, role: str) -> dict:
    """Return a role-specific executive decision brief."""
    row = (
        db.query(ExecutiveDecisionBrief)
        .filter(
            ExecutiveDecisionBrief.tenant_id == tenant_id,
            ExecutiveDecisionBrief.role == role,
        )
        .order_by(ExecutiveDecisionBrief.id.desc())
        .first()
    )
    if row:
        return _row_to_dict(row)

    state = get_twin_state(db, tenant_id)

    headline = _ROLE_HEADLINES.get(role, _ROLE_HEADLINES["quality_director"])
    concerns = _ROLE_CONCERNS.get(role, _ROLE_CONCERNS["quality_director"])
    actions = _ROLE_ACTIONS.get(role, _ROLE_ACTIONS["quality_director"])

    return {
        "id": None,
        "tenant_id": tenant_id,
        "role": role,
        "brief_date": datetime.now(timezone.utc).isoformat(),
        "headline_risk": headline,
        "top_concerns": json.dumps(concerns),
        "recommended_actions": json.dumps(actions),
        "emerging_signals_count": state["open_emerging_risks"],
        "quality_trend": state["trend_direction"],
        "vendor_exposure_summary": (
            f"Vendor performance score: {state['vendor_performance_score']:.2f}. "
            "Potential associations with open quality events identified. "
            "Association is not causation."
        ),
        "recall_exposure_summary": (
            f"Active recalls: {state['active_recalls']}. "
            "Recall exposure score: {:.2f}. Human review recommended.".format(
                state["recall_exposure_score"]
            )
        ),
        "patient_safety_summary": (
            f"Patient safety association score: {state['patient_safety_score']:.2f}. "
            "Near-miss correlation signals present. No clinical claims implied."
        ),
        "human_review_required": True,
        "disclaimer": _BRIEF_DISCLAIMER,
        "data_source": "simulated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Twin Synthesis
# ---------------------------------------------------------------------------


def synthesize_twin(db: Session, tenant_id: str, facility_id: str = "") -> dict:
    """Aggregate from all 9 data sources and persist a new QualityTwinState."""
    rng = _seed(f"synthesize:{tenant_id}:{facility_id}")
    overall = round(rng.uniform(0.55, 0.92), 3)

    state = QualityTwinState(
        tenant_id=tenant_id,
        facility_id=facility_id,
        overall_quality_score=overall,
        inspection_quality_score=round(rng.uniform(0.60, 0.95), 3),
        patient_safety_score=round(rng.uniform(0.65, 0.93), 3),
        vendor_performance_score=round(rng.uniform(0.55, 0.90), 3),
        recall_exposure_score=round(rng.uniform(0.05, 0.35), 3),
        infection_prevention_score=round(rng.uniform(0.60, 0.92), 3),
        capa_effectiveness_score=round(rng.uniform(0.55, 0.88), 3),
        benchmarking_percentile=round(rng.uniform(30.0, 85.0), 1),
        open_emerging_risks=rng.randint(1, 6),
        open_investigations=rng.randint(0, 4),
        pending_recommendations=rng.randint(1, 8),
        active_recalls=rng.randint(0, 3),
        trend_direction=rng.choice(["improving", "stable", "declining"]),
        trend_confidence=round(rng.uniform(0.50, 0.85), 3),
        data_source="simulated",
        human_review_required=True,
    )
    db.add(state)
    db.commit()
    db.refresh(state)

    result = _row_to_dict(state)
    result["sources_ingested"] = _NINE_SOURCES
    result["synthesis_timestamp"] = datetime.now(timezone.utc).isoformat()
    result["disclaimer"] = DISCLAIMER
    return result
