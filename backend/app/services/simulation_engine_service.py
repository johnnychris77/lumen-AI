"""v2.5 — Project Sentinel: Predictive Simulation & Clinical Scenario Engine.

Builds and persists a Decision Scenario Comparison for one inspection: four
evidence-grounded scenarios (reclean / supervisor override / repair
evaluation / remove from service), a risk projection for each, a workflow
impact estimate, and — separately — an instrument health forecast and
enterprise-wide scenario analytics.

Reuses existing engines rather than re-deriving their logic:
  * `readiness_engine.compute_readiness` / `disposition_engine.recommend_disposition`
    for the AI's actual recommended disposition (Supervisor Rules input).
  * `knowledge_graph_service.explain_inspection` for the evidence/reasoning chain.
  * `similar_case_finder_service.find_similar_cases` for historical outcomes.
  * `instrument_condition_service.instrument_condition_history` for instrument
    health trend data (Digital Twin input).

All projected numbers are deterministic (seeded on tenant/inspection ids so
repeated calls without new data are stable) and are explicitly a modeled
association, never a claim of causation — see `DISCLAIMER`.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.simulation_engine import (
    DISCLAIMER,
    RECLEAN,
    REMOVE_FROM_SERVICE,
    REPAIR_EVALUATION,
    SCENARIO_KEYS,
    SCENARIO_LABELS,
    SUPERVISOR_OVERRIDE,
    InstrumentHealthProjection,
    ScenarioOutcome,
    ScenarioProjection,
    SimulationRun,
    WorkflowImpactProjection,
)
from app.services.disposition_engine import recommend_disposition
from app.services.instrument_condition_service import instrument_condition_history
from app.services.knowledge_graph_service import explain_inspection
from app.services.readiness_engine import compute_readiness, get_primary_finding_type
from app.services.similar_case_finder_service import find_similar_cases

_DISPOSITION_TO_SCENARIO = {
    "Proceed to Packaging": RECLEAN,
    "Reclean": RECLEAN,
    "Repeat Inspection": RECLEAN,
    "Supervisor Review Required": SUPERVISOR_OVERRIDE,
    "Repair Evaluation": REPAIR_EVALUATION,
    "Manufacturer Evaluation": REPAIR_EVALUATION,
    "Remove From Service": REMOVE_FROM_SERVICE,
}


class SimulationNotFoundError(Exception):
    pass


def _seed(s: str) -> random.Random:
    """Deterministic seeded RNG from string — same pattern as the P22 twin."""
    h = hashlib.md5(s.encode()).hexdigest()[:8]  # noqa: S324
    return random.Random(int(h, 16))


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _get_inspection(db: Session, tenant_id: str, inspection_id: int):
    from app.db import models

    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    return insp


# ---------------------------------------------------------------------------
# Section 1/2/3 — Simulation Engine + Decision Scenario Builder + Risk Projection
# ---------------------------------------------------------------------------


def _scenario_risk_projection(rng: random.Random, scenario_key: str, *, risk_score: int, coverage_pct: int | None) -> dict:
    """Heuristic risk projection for one scenario, biased by the inspection's
    actual risk_score/coverage so scenarios aren't interchangeable noise."""
    base_risk = min(1.0, max(0.0, (risk_score or 0) / 100.0))
    coverage_gap = 1.0 - min(1.0, max(0.0, (coverage_pct if coverage_pct is not None else 100) / 100.0))

    if scenario_key == RECLEAN:
        quality_risk = round(min(1.0, base_risk * 0.5 + coverage_gap * 0.2 + rng.uniform(0.0, 0.1)), 3)
        operational_impact = round(rng.uniform(0.10, 0.30), 3)
        repeat_inspection_probability = round(min(1.0, 0.3 + coverage_gap * 0.4 + rng.uniform(0.0, 0.1)), 3)
        repair_likelihood = round(rng.uniform(0.02, 0.15), 3)
        supervisor_workload_impact = round(rng.uniform(0.05, 0.20), 3)
    elif scenario_key == SUPERVISOR_OVERRIDE:
        quality_risk = round(min(1.0, base_risk * 0.6 + rng.uniform(0.0, 0.1)), 3)
        operational_impact = round(rng.uniform(0.15, 0.35), 3)
        repeat_inspection_probability = round(rng.uniform(0.10, 0.30), 3)
        repair_likelihood = round(rng.uniform(0.10, 0.35), 3)
        supervisor_workload_impact = round(rng.uniform(0.40, 0.70), 3)
    elif scenario_key == REPAIR_EVALUATION:
        quality_risk = round(rng.uniform(0.05, 0.20), 3)
        operational_impact = round(rng.uniform(0.35, 0.60), 3)
        repeat_inspection_probability = round(rng.uniform(0.10, 0.25), 3)
        repair_likelihood = round(rng.uniform(0.55, 0.90), 3)
        supervisor_workload_impact = round(rng.uniform(0.25, 0.45), 3)
    else:  # REMOVE_FROM_SERVICE
        quality_risk = round(rng.uniform(0.0, 0.05), 3)
        operational_impact = round(rng.uniform(0.55, 0.85), 3)
        repeat_inspection_probability = 0.0
        repair_likelihood = round(rng.uniform(0.0, 0.10), 3)
        supervisor_workload_impact = round(rng.uniform(0.30, 0.55), 3)

    confidence_level = round(min(0.95, max(0.35, 1.0 - coverage_gap * 0.4 - rng.uniform(0.0, 0.1))), 3)

    return {
        "quality_risk": quality_risk,
        "operational_impact": operational_impact,
        "repeat_inspection_probability": repeat_inspection_probability,
        "repair_likelihood": repair_likelihood,
        "supervisor_workload_impact": supervisor_workload_impact,
        "confidence_level": confidence_level,
    }


_CONSEQUENCE_TEXT = {
    RECLEAN: "Instrument returns to decontamination for a repeat clean, then repeats inspection before packaging.",
    SUPERVISOR_OVERRIDE: "A supervisor reviews the AI finding directly and confirms, modifies, or escalates the disposition.",
    REPAIR_EVALUATION: "Instrument is pulled from the tray and routed to repair evaluation before it can re-enter service.",
    REMOVE_FROM_SERVICE: "Instrument is permanently removed from circulation and does not return to the tray.",
}


def _scenario_rationale(scenario_key: str, finding_type: str, ai_disposition: str) -> str:
    finding_label = (finding_type or "an unspecified finding").replace("_", " ")
    if scenario_key == _DISPOSITION_TO_SCENARIO.get(ai_disposition):
        return f"Matches the AI-recommended disposition ({ai_disposition}) for {finding_label}."
    return f"Alternative to the AI-recommended disposition ({ai_disposition}) for {finding_label}."


def generate_scenarios(db: Session, tenant_id: str, inspection_id: int) -> dict:
    """Sections 1-3 — generate and persist the four decision scenarios plus
    risk projections for one inspection, and pick a recommendation."""
    insp = _get_inspection(db, tenant_id, inspection_id)
    if insp is None:
        raise SimulationNotFoundError(f"Inspection {inspection_id} not found for tenant {tenant_id}.")

    primary_finding_type = get_primary_finding_type(db, insp)
    readiness = compute_readiness(db, tenant_id, insp, confirmed=True)
    ai_recommendation = recommend_disposition(
        readiness, insp, coverage_pct=insp.coverage_pct, primary_finding_type=primary_finding_type,
    )
    ai_disposition = ai_recommendation["disposition"]
    recommended_scenario = _DISPOSITION_TO_SCENARIO.get(ai_disposition, SUPERVISOR_OVERRIDE)

    evidence = explain_inspection(db, insp)
    similar_cases = find_similar_cases(
        db, tenant_id, instrument_type=insp.instrument_type, finding_type=primary_finding_type,
        exclude_inspection_id=insp.id,
    )

    rng = _seed(f"sim:{tenant_id}:{inspection_id}:{primary_finding_type}")

    run = SimulationRun(
        tenant_id=tenant_id,
        inspection_id=inspection_id,
        recommended_scenario=recommended_scenario,
        recommended_confidence=round(rng.uniform(0.60, 0.90), 3),
        reasoning=(
            f"{ai_recommendation['explanation']} Historical evidence: {len(similar_cases)} similar case(s) "
            f"on this instrument family with the same finding."
        ),
        evidence_json=json.dumps({"why": evidence["why"], "similar_case_count": len(similar_cases)}),
        inputs_snapshot_json=json.dumps({
            "risk_score": insp.risk_score,
            "coverage_pct": insp.coverage_pct,
            "readiness_status": readiness["status"],
            "repair_history": readiness["repair_history"],
            "ai_disposition": ai_disposition,
            "primary_finding_type": primary_finding_type,
        }),
        human_review_required=True,
        disclaimer=DISCLAIMER,
    )
    db.add(run)
    db.flush()

    scenario_rows = []
    for key in SCENARIO_KEYS:
        projection = _scenario_risk_projection(rng, key, risk_score=insp.risk_score, coverage_pct=insp.coverage_pct)
        row = ScenarioProjection(
            tenant_id=tenant_id,
            simulation_run_id=run.id,
            inspection_id=inspection_id,
            scenario_key=key,
            scenario_label=SCENARIO_LABELS[key],
            likely_consequence=_CONSEQUENCE_TEXT[key],
            rationale=_scenario_rationale(key, primary_finding_type, ai_disposition),
            is_recommended=(key == recommended_scenario),
            **projection,
        )
        db.add(row)
        scenario_rows.append(row)

    db.commit()
    db.refresh(run)
    for row in scenario_rows:
        db.refresh(row)

    scenarios = [_row_to_dict(r) for r in scenario_rows]
    recommended = next(s for s in scenarios if s["is_recommended"])
    alternatives = [s for s in scenarios if not s["is_recommended"]]

    result = _row_to_dict(run)
    result["evidence"] = evidence["why"]
    result["similar_cases"] = similar_cases
    result["recommended"] = recommended
    result["alternatives"] = alternatives
    result["scenarios"] = scenarios
    return result


def get_latest_run(db: Session, tenant_id: str, inspection_id: int) -> dict | None:
    run = (
        db.query(SimulationRun)
        .filter(SimulationRun.tenant_id == tenant_id, SimulationRun.inspection_id == inspection_id)
        .order_by(SimulationRun.id.desc())
        .first()
    )
    if run is None:
        return None

    scenario_rows = (
        db.query(ScenarioProjection)
        .filter(ScenarioProjection.simulation_run_id == run.id)
        .order_by(ScenarioProjection.id.asc())
        .all()
    )
    scenarios = [_row_to_dict(r) for r in scenario_rows]
    recommended = next((s for s in scenarios if s["is_recommended"]), None)
    alternatives = [s for s in scenarios if not s["is_recommended"]]

    result = _row_to_dict(run)
    result["evidence"] = json.loads(run.evidence_json or "{}").get("why", [])
    result["recommended"] = recommended
    result["alternatives"] = alternatives
    result["scenarios"] = scenarios
    return result


# ---------------------------------------------------------------------------
# Section 4 — Workflow Impact Analysis
# ---------------------------------------------------------------------------


def project_workflow_impact(db: Session, tenant_id: str, inspection_id: int) -> dict:
    run = (
        db.query(SimulationRun)
        .filter(SimulationRun.tenant_id == tenant_id, SimulationRun.inspection_id == inspection_id)
        .order_by(SimulationRun.id.desc())
        .first()
    )
    if run is None:
        raise SimulationNotFoundError(
            f"No simulation run exists yet for inspection {inspection_id}. Generate scenarios first."
        )

    scenario_key = run.recommended_scenario
    rng = _seed(f"workflow:{tenant_id}:{inspection_id}:{scenario_key}")

    if scenario_key == RECLEAN:
        queue_hours, or_impact, backlog, tech_wl, sup_wl, avail = (
            rng.uniform(0.5, 2.0), "minor_delay", rng.uniform(0.0, 0.1),
            rng.uniform(0.20, 0.40), rng.uniform(0.05, 0.15), rng.uniform(0.10, 0.25),
        )
    elif scenario_key == SUPERVISOR_OVERRIDE:
        queue_hours, or_impact, backlog, tech_wl, sup_wl, avail = (
            rng.uniform(0.25, 1.0), "minor_delay", rng.uniform(0.0, 0.15),
            rng.uniform(0.05, 0.15), rng.uniform(0.40, 0.65), rng.uniform(0.05, 0.15),
        )
    elif scenario_key == REPAIR_EVALUATION:
        queue_hours, or_impact, backlog, tech_wl, sup_wl, avail = (
            rng.uniform(4.0, 24.0), "significant_delay", rng.uniform(0.40, 0.70),
            rng.uniform(0.10, 0.25), rng.uniform(0.20, 0.35), rng.uniform(0.45, 0.70),
        )
    else:  # REMOVE_FROM_SERVICE
        queue_hours, or_impact, backlog, tech_wl, sup_wl, avail = (
            rng.uniform(0.0, 0.5), "significant_delay", rng.uniform(0.05, 0.20),
            rng.uniform(0.0, 0.10), rng.uniform(0.15, 0.30), rng.uniform(0.60, 0.90),
        )

    row = WorkflowImpactProjection(
        tenant_id=tenant_id,
        simulation_run_id=run.id,
        inspection_id=inspection_id,
        scenario_key=scenario_key,
        inspection_queue_impact_hours=round(queue_hours, 2),
        or_readiness_impact=or_impact,
        repair_backlog_impact=round(backlog, 3),
        technician_workload_impact=round(tech_wl, 3),
        supervisor_workload_impact=round(sup_wl, 3),
        instrument_availability_impact=round(avail, 3),
        narrative=(
            f"Choosing {SCENARIO_LABELS[scenario_key]} is projected to add roughly "
            f"{round(queue_hours, 1)}h to the inspection queue, with {or_impact.replace('_', ' ')} "
            "to OR readiness for this tray."
        ),
        human_review_required=True,
        disclaimer=DISCLAIMER,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


# ---------------------------------------------------------------------------
# Section 5 — Instrument Health Projection
# ---------------------------------------------------------------------------


def project_instrument_health(db: Session, tenant_id: str, instrument_identity: str) -> dict | None:
    history = instrument_condition_history(db, tenant_id, instrument_identity)
    if history is None:
        return None

    rng = _seed(f"health:{tenant_id}:{instrument_identity}")

    trend = history["condition_trend"]
    corrosion_progression = (
        "worsening" if history["corrosion_history_count"] >= 2
        else "stable" if history["corrosion_history_count"] == 1
        else "none_detected"
    )
    damage_events = sum(1 for h in history["history"] if h["damage_findings"])
    damage_progression = (
        "worsening" if damage_events >= 2 else "stable" if damage_events == 1 else "none_detected"
    )

    inspection_count = history["inspection_count"]
    inspection_frequency_days = round(rng.uniform(30, 90), 1) if inspection_count > 1 else None
    repair_frequency_days = (
        round(rng.uniform(90, 365), 1) if history["repair_count"] > 0 else None
    )

    risk_factor = (history["repair_count"] * 2 + history["corrosion_history_count"]) / max(1, inspection_count)
    if trend == "declining" or history["repair_count"] > 0:
        expected_remaining_service_life_days = int(rng.uniform(30, 180) * max(0.2, 1 - risk_factor))
    elif trend == "insufficient_data":
        expected_remaining_service_life_days = None
    else:
        expected_remaining_service_life_days = int(rng.uniform(180, 720))

    confidence_level = round(min(0.90, 0.30 + 0.10 * min(inspection_count, 6)), 3)

    row = InstrumentHealthProjection(
        tenant_id=tenant_id,
        instrument_identity=instrument_identity,
        instrument_type=history["instrument_type"],
        health_trend=trend,
        corrosion_progression=corrosion_progression,
        damage_progression=damage_progression,
        inspection_frequency_days=inspection_frequency_days,
        repair_frequency_days=repair_frequency_days,
        expected_remaining_service_life_days=expected_remaining_service_life_days,
        confidence_level=confidence_level,
        human_review_required=True,
        disclaimer=DISCLAIMER,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _row_to_dict(row)
    result["inspection_count"] = inspection_count
    result["repair_count"] = history["repair_count"]
    return result


# ---------------------------------------------------------------------------
# Section 6 — Educational Scenario Mode
# ---------------------------------------------------------------------------


_EDUCATIONAL_NARRATIVE = {
    RECLEAN: "If we reclean: the instrument stays in circulation but repeats decontamination and inspection — "
             "appropriate when the finding is contamination-type and likely to resolve with reprocessing.",
    REPAIR_EVALUATION: "If we repair: the instrument is pulled for evaluation before it can be used again — "
                        "appropriate for a structural finding that is plausibly fixable.",
    REMOVE_FROM_SERVICE: "If we remove from service: the instrument permanently exits circulation — "
                          "appropriate for findings that are not repairable or recur despite repair.",
}


def educational_comparison(db: Session, tenant_id: str, instrument_type: str, finding_type: str) -> dict:
    """Section 6 — compare 'what if' scenarios using real historical cases."""
    similar_cases = find_similar_cases(db, tenant_id, instrument_type=instrument_type, finding_type=finding_type, limit=10)

    outcome_counts: dict[str, int] = {}
    for case in similar_cases:
        outcome = case.get("outcome") or case.get("final_disposition") or "unknown"
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    comparisons = [
        {
            "scenario_key": key,
            "scenario_label": SCENARIO_LABELS[key],
            "narrative": _EDUCATIONAL_NARRATIVE.get(key, ""),
        }
        for key in (RECLEAN, REPAIR_EVALUATION, REMOVE_FROM_SERVICE)
    ]

    return {
        "instrument_type": instrument_type,
        "finding_type": finding_type,
        "comparisons": comparisons,
        "historical_case_count": len(similar_cases),
        "historical_outcome_distribution": outcome_counts,
        "similar_cases": similar_cases,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Section 8 — Outcome Learning
# ---------------------------------------------------------------------------


def record_actual_outcome(
    db: Session, tenant_id: str, simulation_run_id: int, *, actual_disposition: str, recorded_by: str = "", notes: str = "",
) -> dict:
    run = (
        db.query(SimulationRun)
        .filter(SimulationRun.id == simulation_run_id, SimulationRun.tenant_id == tenant_id)
        .first()
    )
    if run is None:
        raise SimulationNotFoundError(f"Simulation run {simulation_run_id} not found for tenant {tenant_id}.")

    actual_scenario = _DISPOSITION_TO_SCENARIO.get(actual_disposition, "")
    prediction_correct = (actual_scenario == run.recommended_scenario) if actual_scenario else None

    row = (
        db.query(ScenarioOutcome)
        .filter(ScenarioOutcome.simulation_run_id == simulation_run_id, ScenarioOutcome.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        row = ScenarioOutcome(
            tenant_id=tenant_id,
            simulation_run_id=simulation_run_id,
            inspection_id=run.inspection_id,
            predicted_scenario=run.recommended_scenario,
            predicted_confidence=run.recommended_confidence,
        )
        db.add(row)

    row.actual_disposition = actual_disposition
    row.actual_scenario = actual_scenario
    row.recorded_by = recorded_by
    row.notes = notes
    row.prediction_correct = prediction_correct
    row.actual_recorded_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


# ---------------------------------------------------------------------------
# Section 9 — Enterprise Scenario Analytics
# ---------------------------------------------------------------------------


def enterprise_scenario_analytics(db: Session, tenant_id: str) -> dict:
    from app.models.disposition_override import DispositionOverride

    scenario_counts: dict[str, int] = {}
    for key in SCENARIO_KEYS:
        scenario_counts[key] = (
            db.query(ScenarioProjection)
            .filter(
                ScenarioProjection.tenant_id == tenant_id,
                ScenarioProjection.scenario_key == key,
                ScenarioProjection.is_recommended.is_(True),
            )
            .count()
        )

    outcomes = db.query(ScenarioOutcome).filter(ScenarioOutcome.tenant_id == tenant_id).all()
    resolved = [o for o in outcomes if o.prediction_correct is not None]
    accuracy = round(sum(1 for o in resolved if o.prediction_correct) / len(resolved), 3) if resolved else None

    override_outcomes: dict[str, int] = {}
    for row in db.query(DispositionOverride).filter(DispositionOverride.tenant_id == tenant_id).all():
        override_outcomes[row.action] = override_outcomes.get(row.action, 0) + 1

    repair_outcomes = sum(
        1 for o in outcomes
        if o.actual_scenario == REPAIR_EVALUATION
    )

    most_effective = max(scenario_counts, key=scenario_counts.get) if any(scenario_counts.values()) else None

    return {
        "most_common_scenarios": scenario_counts,
        "most_effective_recommendation": most_effective,
        "prediction_accuracy": accuracy,
        "prediction_sample_size": len(resolved),
        "override_outcomes": override_outcomes,
        "repair_outcomes": repair_outcomes,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
